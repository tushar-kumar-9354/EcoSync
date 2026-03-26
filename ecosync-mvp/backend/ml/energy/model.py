"""
EcoSync Energy Optimization Engine
Hybrid LSTM + Transformer with Attention Mechanism for Energy Demand Forecasting

Architecture:
- Temporal encoding via LSTM layers for sequential patterns
- Multi-head self-attention for long-range dependencies
- Feed-forward networks for non-linear transformations
- Multi-output heads for demand + uncertainty estimation
"""

import torch
import torch.nn as nn
import math
from typing import Optional, Tuple


class PositionalEncoding(nn.Module):
    """Sinusoidal positional encoding for transformer."""

    def __init__(self, d_model: int, max_len: int = 5000, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))
        pe = torch.zeros(max_len, d_model)
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # [1, max_len, d_model]
        self.register_buffer('pe', pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)


class MultiHeadAttention(nn.Module):
    """Multi-head self-attention mechanism."""

    def __init__(self, d_model: int, num_heads: int = 8, dropout: float = 0.1):
        super().__init__()
        assert d_model % num_heads == 0, "d_model must be divisible by num_heads"

        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads

        self.q_linear = nn.Linear(d_model, d_model)
        self.k_linear = nn.Linear(d_model, d_model)
        self.v_linear = nn.Linear(d_model, d_model)
        self.out_linear = nn.Linear(d_model, d_model)

        self.dropout = nn.Dropout(dropout)
        self.scale = math.sqrt(self.d_k)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        batch_size, seq_len, _ = x.shape

        # Linear projections and reshape to multi-head
        q = self.q_linear(x).view(batch_size, seq_len, self.num_heads, self.d_k).transpose(1, 2)
        k = self.k_linear(x).view(batch_size, seq_len, self.num_heads, self.d_k).transpose(1, 2)
        v = self.v_linear(x).view(batch_size, seq_len, self.num_heads, self.d_k).transpose(1, 2)

        # Attention scores
        scores = torch.matmul(q, k.transpose(-2, -1)) / self.scale

        if mask is not None:
            scores = scores.masked_fill(mask == 0, -1e9)

        attn_weights = torch.softmax(scores, dim=-1)
        attn_weights = self.dropout(attn_weights)

        # Apply attention to values
        context = torch.matmul(attn_weights, v)
        context = context.transpose(1, 2).contiguous().view(batch_size, seq_len, self.d_model)

        output = self.out_linear(context)
        return output, attn_weights


class TransformerEncoderLayer(nn.Module):
    """Single transformer encoder layer with pre-norm architecture."""

    def __init__(self, d_model: int, num_heads: int = 8, d_ff: int = 2048, dropout: float = 0.1):
        super().__init__()

        self.norm1 = nn.LayerNorm(d_model)
        self.attn = MultiHeadAttention(d_model, num_heads, dropout)

        self.norm2 = nn.LayerNorm(d_model)
        self.ff = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout)
        )

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        # Pre-norm architecture
        x_norm = self.norm1(x)
        attn_out, attn_weights = self.attn(x_norm, mask)
        x = x + attn_out

        x_norm = self.norm2(x)
        ff_out = self.ff(x_norm)
        x = x + ff_out

        return x, attn_weights


class LSTMTemporalEncoder(nn.Module):
    """Bidirectional LSTM for temporal pattern extraction."""

    def __init__(self, input_size: int, hidden_size: int, num_layers: int = 2, dropout: float = 0.1):
        super().__init__()

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0
        )

        self.layer_norm = nn.LayerNorm(hidden_size * 2)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        lstm_out, (hidden, cell) = self.lstm(x)
        lstm_out = self.layer_norm(lstm_out)
        return lstm_out, (hidden, cell)


class EnergyForecastingModel(nn.Module):
    """
    Hybrid LSTM-Transformer model for energy demand forecasting.

    Architecture:
    1. Input embedding + temporal features
    2. Bidirectional LSTM for sequential pattern encoding
    3. Multi-layer Transformer encoder for long-range dependencies
    4. Multi-output prediction heads

    Outputs:
    - point预测: Single-point demand forecast
    - uncertainty: Aleatoric uncertainty estimation
    - attention_weights: For interpretability
    """

    def __init__(
        self,
        input_dim: int,
        lstm_hidden: int = 128,
        lstm_layers: int = 2,
        d_model: int = 256,
        num_heads: int = 8,
        num_transformer_layers: int = 4,
        d_ff: int = 512,
        dropout: float = 0.1,
        forecast_horizons: list = [1, 6, 12, 24]
    ):
        super().__init__()

        self.input_dim = input_dim
        self.forecast_horizons = forecast_horizons
        self.d_model = d_model

        # Input projection to d_model dimensions
        self.input_projection = nn.Sequential(
            nn.Linear(input_dim, d_model),
            nn.LayerNorm(d_model),
            nn.GELU(),
            nn.Dropout(dropout)
        )

        # Learnable temporal embeddings for hour, day of week, month
        self.hour_embedding = nn.Embedding(24, 16)
        self.day_embedding = nn.Embedding(7, 16)
        self.month_embedding = nn.Embedding(13, 16)  # 0-12 (0 unused)
        self.embedding_projection = nn.Linear(48, d_model)

        # Positional encoding for transformer
        self.positional_encoding = PositionalEncoding(d_model, max_len=500, dropout=dropout)

        # LSTM temporal encoder
        self.lstm_encoder = LSTMTemporalEncoder(
            input_size=d_model,
            hidden_size=lstm_hidden,
            num_layers=lstm_layers,
            dropout=dropout
        )

        # Transformer encoder layers
        self.transformer_layers = nn.ModuleList([
            TransformerEncoderLayer(d_model, num_heads, d_ff, dropout)
            for _ in range(num_transformer_layers)
        ])

        # Output projections
        # 1. Main forecast head (predicts demand at each horizon)
        num_horizons = len(forecast_horizons)
        self.forecast_head = nn.Sequential(
            nn.Linear(d_model * 2, d_model),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, num_horizons)
        )

        # 2. Uncertainty head (log variance for heteroscedastic uncertainty)
        self.uncertainty_head = nn.Sequential(
            nn.Linear(d_model * 2, d_model // 2),
            nn.GELU(),
            nn.Linear(d_model // 2, num_horizons)
        )

        # 3. Peak detection head
        self.peak_head = nn.Sequential(
            nn.Linear(d_model * 2, d_model // 2),
            nn.GELU(),
            nn.Linear(d_model // 2, 1),
            nn.Sigmoid()
        )

        # 4. Attention aggregation for interpretability
        self.attention_aggregation = nn.Linear(d_model, 1)

        self._init_weights()

    def _init_weights(self):
        """Initialize weights with Xavier/Glorot initialization."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def forward(
        self,
        x: torch.Tensor,
        hour: torch.Tensor,
        day_of_week: torch.Tensor,
        month: torch.Tensor,
        return_attention: bool = False
    ) -> dict:
        """
        Forward pass.

        Args:
            x: Input features [batch, seq_len, input_dim]
            hour: Hour of day [batch]
            day_of_week: Day of week [batch]
            month: Month [batch]
            return_attention: Whether to return attention weights

        Returns:
            dict with:
                - forecasts: [batch, num_horizons] demand predictions
                - uncertainty: [batch, num_horizons] log variance
                - peak_prob: [batch, 1] probability of peak demand
                - attention_weights: list of attention weight tensors (optional)
        """
        batch_size = x.size(0)
        seq_len = x.size(1)

        # Project input to d_model
        x = self.input_projection(x)

        # Add temporal embeddings
        hour_emb = self.hour_embedding(hour).unsqueeze(1).expand(-1, seq_len, -1)
        day_emb = self.day_embedding(day_of_week).unsqueeze(1).expand(-1, seq_len, -1)
        month_emb = self.month_embedding(month).unsqueeze(1).expand(-1, seq_len, -1)

        temporal_emb = torch.cat([hour_emb, day_emb, month_emb], dim=-1)
        temporal_emb = self.embedding_projection(temporal_emb)

        x = x + temporal_emb

        # LSTM encoding
        lstm_out, _ = self.lstm_encoder(x)
        lstm_out = lstm_out + x  # Residual connection

        # Transformer encoding
        all_attention_weights = []
        for layer in self.transformer_layers:
            lstm_out, attn_weights = layer(lstm_out)
            if return_attention:
                all_attention_weights.append(attn_weights)

        # Aggregate sequence to single representation
        # Use attention-weighted aggregation
        attn_scores = self.attention_aggregation(lstm_out)  # [batch, seq, 1]
        attn_weights_soft = torch.softmax(attn_scores, dim=1)
        context = torch.sum(lstm_out * attn_weights_soft, dim=1)  # [batch, d_model]

        # Also use LSTM final hidden state (concatenate bidirectional)
        lstm_final = lstm_out[:, -1, :]  # [batch, d_model * 2] (bi-LSTM)

        # Combine aggregation methods
        combined_repr = torch.cat([context, lstm_final], dim=-1)

        # Output predictions
        forecasts = self.forecast_head(combined_repr)  # [batch, num_horizons]
        uncertainty = self.uncertainty_head(combined_repr)  # [batch, num_horizons]
        peak_prob = self.peak_head(combined_repr)  # [batch, 1]

        outputs = {
            'forecasts': forecasts,
            'uncertainty': uncertainty,
            'peak_probability': peak_prob
        }

        if return_attention:
            outputs['attention_weights'] = all_attention_weights

        return outputs

    def get_forecast_with_confidence(
        self,
        x: torch.Tensor,
        hour: torch.Tensor,
        day_of_week: torch.Tensor,
        month: torch.Tensor,
        num_samples: int = 100
    ) -> dict:
        """
        Generate forecasts with confidence intervals using Monte Carlo dropout.

        Args:
            x: Input features
            hour: Hour of day
            day_of_week: Day of week
            month: Month
            num_samples: Number of MC samples

        Returns:
            dict with mean, std, and confidence intervals
        """
        self.train()  # Enable dropout for MC sampling

        all_forecasts = []
        for _ in range(num_samples):
            with torch.no_grad():
                output = self.forward(x, hour, day_of_week, month, return_attention=False)
                all_forecasts.append(output['forecasts'])

        all_forecasts = torch.stack(all_forecasts, dim=0)  # [num_samples, batch, horizons]

        mean = torch.mean(all_forecasts, dim=0)
        std = torch.std(all_forecasts, dim=0)

        # 95% confidence interval
        lower_95 = mean - 1.96 * std
        upper_95 = mean + 1.96 * std

        return {
            'mean': mean,
            'std': std,
            'lower_95': lower_95,
            'upper_95': upper_95,
            'all_samples': all_forecasts
        }


class ResidualBlock(nn.Module):
    """Simple residual block for skip connections."""

    def __init__(self, d_model: int, dropout: float = 0.1):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.LayerNorm(d_model),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, d_model),
            nn.LayerNorm(d_model)
        )
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.dropout(self.layers(x))
