"""
Inference module for Energy Forecasting Model

Handles:
- Loading trained models
- Batch and real-time inference
- Confidence interval generation via Monte Carlo dropout
- Integration with FastAPI backend
"""

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import json

from .model import EnergyForecastingModel


class EnergyInference:
    """
    Inference engine for energy demand forecasting.

    Features:
    - Loads trained models from checkpoint
    - Supports batch and single-sample inference
    - Monte Carlo dropout for uncertainty estimation
    - Integration with feature engineering pipeline
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = 'auto',
        mc_samples: int = 100
    ):
        self.device = self._get_device(device)
        self.mc_samples = mc_samples
        self.model: Optional[EnergyForecastingModel] = None
        self.model_config: Optional[Dict] = None

        if model_path:
            self.load_model(model_path)

    def _get_device(self, device: str) -> torch.device:
        if device == 'auto':
            return torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        return torch.device(device)

    def load_model(self, model_path: str) -> bool:
        """
        Load trained model from checkpoint.

        Args:
            model_path: Path to checkpoint file

        Returns:
            True if successful, False otherwise
        """
        try:
            checkpoint = torch.load(model_path, map_location=self.device)

            # Get model configuration from checkpoint
            config = checkpoint.get('config', {})
            if not config:
                # Infer from checkpoint
                config = self._infer_model_config(checkpoint)

            self.model_config = config

            # Create model instance
            self.model = EnergyForecastingModel(
                input_dim=config.get('input_dim', 50),
                lstm_hidden=config.get('lstm_hidden', 128),
                lstm_layers=config.get('lstm_layers', 2),
                d_model=config.get('d_model', 256),
                num_heads=config.get('num_heads', 8),
                num_transformer_layers=config.get('num_transformer_layers', 4),
                d_ff=config.get('d_ff', 512),
                dropout=0.0,  # No dropout at inference
                forecast_horizons=config.get('forecast_horizons', [1, 6, 12, 24])
            )

            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.model.to(self.device)
            self.model.eval()

            # Store normalization parameters
            self.feature_mean = checkpoint.get('feature_mean')
            self.feature_std = checkpoint.get('feature_std')
            self.target_mean = checkpoint.get('target_mean')
            self.target_std = checkpoint.get('target_std')

            print(f"Loaded model from {model_path}")
            print(f"  - Forecast horizons: {config.get('forecast_horizons')}")
            print(f"  - Target mean: {self.target_mean:.2f}, std: {self.target_std:.2f}")

            return True

        except Exception as e:
            print(f"Error loading model: {e}")
            return False

    def _infer_model_config(self, checkpoint: Dict) -> Dict:
        """Infer model configuration from checkpoint keys."""
        config = {}

        # Try to infer from layer names
        state_dict = checkpoint.get('model_state_dict', {})

        if any('lstm' in k for k in state_dict.keys()):
            config['lstm_hidden'] = 128
            config['lstm_layers'] = 2

        if any('transformer_layers' in k for k in state_dict.keys()):
            config['num_transformer_layers'] = 4

        config['input_dim'] = 50  # Default
        config['forecast_horizons'] = [1, 6, 12, 24]

        return config

    @torch.no_grad()
    def predict(
        self,
        features: np.ndarray,
        hours: np.ndarray,
        days: np.ndarray,
        months: np.ndarray,
        return_uncertainty: bool = True
    ) -> Dict[str, np.ndarray]:
        """
        Make predictions for a batch of samples.

        Args:
            features: Input features [batch, seq_len, input_dim]
            hours: Hour of day for prediction [batch]
            days: Day of week for prediction [batch]
            months: Month for prediction [batch]
            return_uncertainty: Whether to return uncertainty estimates

        Returns:
            Dictionary with predictions and optional uncertainty
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        self.model.eval()

        # Normalize features
        if self.feature_mean is not None and self.feature_std is not None:
            features = (features - self.feature_mean) / (self.feature_std + 1e-8)

        # Convert to tensors
        x = torch.FloatTensor(features).to(self.device)
        h = torch.LongTensor(hours).to(self.device)
        d = torch.LongTensor(days).to(self.device)
        m = torch.LongTensor(months).to(self.device)

        # Standard prediction
        outputs = self.model(x, h, d, m, return_attention=False)

        # Denormalize predictions
        preds = outputs['forecasts'].cpu().numpy() * self.target_std + self.target_mean

        result = {'predictions': preds}

        if return_uncertainty:
            # Uncertainty is log variance, convert to std
            uncertainties = torch.exp(outputs['uncertainty']).cpu().numpy() * self.target_std
            result['uncertainty_std'] = uncertainties

            # 95% confidence intervals
            result['lower_95'] = preds - 1.96 * uncertainties
            result['upper_95'] = preds + 1.96 * uncertainties

            # Peak probability
            result['peak_probability'] = outputs['peak_probability'].cpu().numpy()

        return result

    @torch.no_grad()
    def predict_with_monte_carlo(
        self,
        features: np.ndarray,
        hours: np.ndarray,
        days: np.ndarray,
        months: np.ndarray,
        num_samples: int = 100
    ) -> Dict[str, np.ndarray]:
        """
        Make predictions using Monte Carlo dropout for uncertainty estimation.

        This runs multiple forward passes with dropout enabled to estimate
        prediction uncertainty.

        Args:
            features: Input features
            hours: Hour of day
            days: Day of week
            months: Month
            num_samples: Number of MC samples

        Returns:
            Dictionary with mean, std, and confidence intervals
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Enable dropout for MC sampling
        self.model.train()

        # Normalize features
        if self.feature_mean is not None and self.feature_std is not None:
            features_norm = (features - self.feature_mean) / (self.feature_std + 1e-8)
        else:
            features_norm = features

        # Convert to tensors
        x = torch.FloatTensor(features_norm).to(self.device)
        h = torch.LongTensor(hours).to(self.device)
        d = torch.LongTensor(days).to(self.device)
        m = torch.LongTensor(months).to(self.device)

        all_predictions = []

        for _ in range(num_samples):
            outputs = self.model(x, h, d, m, return_attention=False)
            preds = outputs['forecasts'].cpu().numpy() * self.target_std + self.target_mean
            all_predictions.append(preds)

        # Disable dropout again
        self.model.eval()

        all_predictions = np.stack(all_predictions, axis=0)  # [num_samples, batch, horizons]

        mean = np.mean(all_predictions, axis=0)
        std = np.std(all_predictions, axis=0)

        return {
            'mean': mean,
            'std': std,
            'lower_95': mean - 1.96 * std,
            'upper_95': mean + 1.96 * std,
            'all_samples': all_predictions
        }

    def predict_24h_forecast(
        self,
        historical_data: pd.DataFrame,
        feature_cols: List[str],
        target_col: str = 'demand_kwh',
        weather_forecast: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        Generate 24-hour ahead forecast.

        Args:
            historical_data: DataFrame with historical demand data
            feature_cols: List of feature column names
            target_col: Target column name
            weather_forecast: Optional weather forecast for the next 24 hours

        Returns:
            Dictionary with hourly forecasts and confidence intervals
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Sort by timestamp
        historical_data = historical_data.sort_values('timestamp')

        # Get last seq_len hours of data
        seq_len = self.model_config.get('seq_len', 168) if self.model_config else 168
        recent_data = historical_data.tail(seq_len).copy()

        # Prepare features
        features = recent_data[feature_cols].values
        hours = recent_data['hour'].values
        days = recent_data['day_of_week'].values
        months = recent_data['month'].values

        # Normalize
        if self.feature_mean is not None:
            features_norm = (features - self.feature_mean) / (self.feature_std + 1e-8)
        else:
            features_norm = features

        # Use last timestamp for initial prediction
        last_idx = len(historical_data) - 1
        next_hour = historical_data.iloc[last_idx]['timestamp'] + timedelta(hours=1)

        forecasts = []
        uncertainties = []
        peak_probs = []

        # Iteratively predict next 24 hours
        current_features = features_norm.copy()
        current_h = hours[-1]
        current_d = days[-1]
        current_m = months[-1]

        for i in range(24):
            # Predict
            pred = self.predict_single_step(
                current_features,
                np.array([(current_h + i) % 24]),
                np.array([(current_d + (current_h + i) // 24) % 7]),
                np.array([current_m])
            )

            forecasts.append(pred['predictions'][0])
            uncertainties.append(pred['uncertainty_std'][0])
            peak_probs.append(pred['peak_probability'][0])

        forecasts = np.array(forecasts)
        uncertainties = np.array(uncertainties)
        peak_probs = np.array(peak_probs)

        # Generate timestamps for forecast
        forecast_timestamps = [
            (historical_data.iloc[last_idx]['timestamp'] + timedelta(hours=i + 1)).isoformat()
            for i in range(24)
        ]

        # Identify peak hour
        peak_idx = np.argmax(forecasts[:, 0])  # First horizon (1h ahead)
        peak_hour = forecast_timestamps[peak_idx]

        return {
            'timestamps': forecast_timestamps,
            'forecasts': forecasts,
            'uncertainty_std': uncertainties,
            'lower_95': forecasts - 1.96 * uncertainties,
            'upper_95': forecasts + 1.96 * uncertainties,
            'peak_probability': peak_probs,
            'peak_hour': peak_hour,
            'peak_demand': float(forecasts[peak_idx, 0]),
            'horizons': self.model_config.get('forecast_horizons', [1, 6, 12, 24]) if self.model_config else [1, 6, 12, 24]
        }

    @torch.no_grad()
    def predict_single_step(
        self,
        features: np.ndarray,
        hour: np.ndarray,
        day_of_week: np.ndarray,
        month: np.ndarray
    ) -> Dict[str, np.ndarray]:
        """Predict a single step (for iterative forecasting)."""
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Normalize features
        if self.feature_mean is not None:
            features_norm = (features - self.feature_mean) / (self.feature_std + 1e-8)
        else:
            features_norm = features

        # Convert to tensors
        x = torch.FloatTensor(features_norm).to(self.device)
        h = torch.LongTensor(hour).to(self.device)
        d = torch.LongTensor(day_of_week).to(self.device)
        m = torch.LongTensor(month).to(self.device)

        outputs = self.model(x, h, d, m, return_attention=False)

        # Denormalize
        preds = outputs['forecasts'].cpu().numpy() * self.target_std + self.target_mean
        uncertainties = torch.exp(outputs['uncertainty']).cpu().numpy() * self.target_std
        peak_probs = outputs['peak_probability'].cpu().numpy()

        return {
            'predictions': preds,
            'uncertainty_std': uncertainties,
            'peak_probability': peak_probs
        }

    def format_forecast_response(self, forecast: Dict) -> Dict:
        """
        Format forecast for FastAPI response.

        Args:
            forecast: Raw forecast dictionary

        Returns:
            Formatted response ready for JSON
        """
        horizons = forecast.get('horizons', [1, 6, 12, 24])

        # Format hourly predictions
        hourly = []
        for i, ts in enumerate(forecast['timestamps']):
            hourly.append({
                'timestamp': ts,
                'demand_kwh': round(float(forecast['forecasts'][i, 0]), 1),
                'lower_95': round(float(forecast['lower_95'][i, 0]), 1),
                'upper_95': round(float(forecast['upper_95'][i, 0]), 1),
                'confidence': round(float(1 - forecast['uncertainty_std'][i, 0] / forecast['forecasts'][i, 0]), 3) if forecast['forecasts'][i, 0] > 0 else 0.9,
                'is_peak': bool(forecast['peak_probability'][i, 0] > 0.5)
            })

        # Format horizon predictions (1h, 6h, 12h, 24h)
        horizon_predictions = {}
        for j, h in enumerate(horizons):
            idx = horizons.index(h) if h in horizons else j
            horizon_predictions[f'+{h}h'] = {
                'demand_kwh': round(float(forecast['forecasts'][-1, idx]), 1),
                'uncertainty': round(float(forecast['uncertainty_std'][-1, idx]), 1)
            }

        return {
            'forecast': hourly,
            'horizon_predictions': horizon_predictions,
            'peak': {
                'hour': forecast['peak_hour'],
                'demand_kwh': forecast['peak_demand']
            },
            'model_version': 'lstm-transformer-v2.1',
            'generated_at': datetime.now().isoformat()
        }


class BatchInferenceEngine:
    """Handle batch inference for multiple sensors/zones."""

    def __init__(self, inference: EnergyInference):
        self.inference = inference

    def predict_zone_demand(
        self,
        zone_data: Dict[str, pd.DataFrame],
        feature_cols: List[str]
    ) -> Dict[str, Dict]:
        """
        Predict demand for multiple zones.

        Args:
            zone_data: Dict mapping zone_id to DataFrame with historical data
            feature_cols: Feature column names

        Returns:
            Dict mapping zone_id to forecast results
        """
        results = {}

        for zone_id, df in zone_data.items():
            try:
                forecast = self.inference.predict_24h_forecast(
                    historical_data=df,
                    feature_cols=feature_cols
                )
                results[zone_id] = {
                    'success': True,
                    'forecast': forecast
                }
            except Exception as e:
                results[zone_id] = {
                    'success': False,
                    'error': str(e)
                }

        return results

    def predict_city_wide_demand(
        self,
        aggregated_data: pd.DataFrame,
        feature_cols: List[str]
    ) -> Dict:
        """Predict total city-wide demand."""
        forecast = self.inference.predict_24h_forecast(
            historical_data=aggregated_data,
            feature_cols=feature_cols
        )

        return {
            'city_total': forecast,
            'aggregated_from': 'all_zones'
        }
