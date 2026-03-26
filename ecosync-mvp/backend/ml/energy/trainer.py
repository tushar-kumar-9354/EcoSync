"""
Training pipeline for Energy Forecasting Model

Handles:
- Data loading and preprocessing
- Training loop with validation
- Early stopping and model checkpointing
- Learning rate scheduling
- Gradient clipping
- Logging and metrics tracking
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import json
import math


class EnergyDataset(Dataset):
    """PyTorch dataset for energy forecasting."""

    def __init__(
        self,
        features: np.ndarray,
        targets: np.ndarray,
        hours: np.ndarray,
        days: np.ndarray,
        months: np.ndarray
    ):
        self.features = torch.FloatTensor(features)
        self.targets = torch.FloatTensor(targets)
        self.hours = torch.LongTensor(hours)
        self.days = torch.LongTensor(days)
        self.months = torch.LongTensor(months)

    def __len__(self) -> int:
        return len(self.features)

    def __getitem__(self, idx: int) -> Tuple[Dict[str, torch.Tensor], torch.Tensor]:
        x = self.features[idx]
        hour = self.hours[idx]
        day = self.days[idx]
        month = self.months[idx]

        return {
            'x': x,
            'hour': hour,
            'day_of_week': day,
            'month': month
        }, self.targets[idx]


class EnergyTrainer:
    """
    Trainer for the hybrid LSTM-Transformer energy forecasting model.

    Features:
    - Mixed loss function (MSE + uncertainty loss)
    - Gradient clipping
    - Learning rate scheduling (cosine annealing with warmup)
    - Early stopping based on validation loss
    - Model checkpointing
    - Training metrics logging
    """

    def __init__(
        self,
        model: nn.Module,
        learning_rate: float = 1e-4,
        weight_decay: float = 1e-5,
        batch_size: int = 64,
        num_epochs: int = 100,
        val_split: float = 0.2,
        device: str = 'auto',
        checkpoint_dir: str = 'checkpoints',
        log_interval: int = 10
    ):
        self.device = self._get_device(device)
        self.model = model.to(self.device)

        self.batch_size = batch_size
        self.num_epochs = num_epochs
        self.val_split = val_split
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.log_interval = log_interval

        # Optimizer with weight decay
        self.optimizer = optim.AdamW(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay
        )

        # Loss function: MSE with uncertainty weighting
        self.criterion = nn.MSELoss()

        # Learning rate scheduler
        self.scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
            self.optimizer,
            T_0=10,
            T_mult=2
        )

        self.train_losses: List[float] = []
        self.val_losses: List[float] = []
        self.best_val_loss = float('inf')
        self.epochs_without_improvement = 0
        self.patience = 15

    def _get_device(self, device: str) -> torch.device:
        if device == 'auto':
            return torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        return torch.device(device)

    def prepare_data(
        self,
        df: pd.DataFrame,
        feature_cols: List[str],
        target_col: str = 'demand_kwh',
        seq_len: int = 168  # 1 week of hourly data
    ) -> Tuple[DataLoader, DataLoader]:
        """
        Prepare train/val dataloaders from dataframe.

        Args:
            df: DataFrame with features and target
            feature_cols: List of feature column names
            target_col: Target column name
            seq_len: Sequence length for LSTM input

        Returns:
            Tuple of (train_loader, val_loader)
        """
        # Sort by timestamp
        df = df.sort_values('timestamp').reset_index(drop=True)

        # Extract features and targets
        features = df[feature_cols].values
        targets = df[target_col].values

        # Extract temporal info
        hours = df['hour'].values
        days = df['day_of_week'].values
        months = df['month'].values

        # Create sequences
        X, y, h, d, m = [], [], [], [], []
        for i in range(seq_len, len(features)):
            X.append(features[i-seq_len:i])
            y.append(targets[i])
            h.append(hours[i])
            d.append(days[i])
            m.append(months[i])

        X = np.array(X)
        y = np.array(y).reshape(-1, 1)
        h = np.array(h)
        d = np.array(d)
        m = np.array(m)

        # Normalize features
        self.feature_mean = X.mean(axis=(0, 1))
        self.feature_std = X.std(axis=(0, 1)) + 1e-8
        X = (X - self.feature_mean) / self.feature_std

        # Normalize targets
        self.target_mean = y.mean()
        self.target_std = y.std() + 1e-8
        y = (y - self.target_mean) / self.target_std

        # Train/val split
        val_size = int(len(X) * self.val_split)
        train_size = len(X) - val_size

        train_dataset = EnergyDataset(
            X[:train_size], y[:train_size], h[:train_size], d[:train_size], m[:train_size]
        )
        val_dataset = EnergyDataset(
            X[train_size:], y[train_size:], h[train_size:], d[train_size:], m[train_size:]
        )

        train_loader = DataLoader(
            train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=0
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=0
        )

        return train_loader, val_loader

    def compute_loss(
        self,
        outputs: Dict[str, torch.Tensor],
        targets: torch.Tensor,
        epoch: int
    ) -> torch.Tensor:
        """
        Compute combined loss.

        Uses weighted MSE + uncertainty loss + peak-aware loss.
        """
        predictions = outputs['forecasts']
        uncertainty = outputs['uncertainty']

        # Normalize targets
        targets_norm = (targets - self.target_mean) / self.target_std

        # MSE loss
        mse_loss = self.criterion(predictions, targets_norm)

        # Uncertainty loss (negative log-likelihood for heteroscedastic model)
        # Encourages the model to output higher uncertainty for harder samples
        uncertainty_loss = torch.mean(torch.exp(-uncertainty) * (predictions - targets_norm) ** 2 + uncertainty)

        # Peak-aware loss: give more weight to peak demand predictions
        is_peak = (targets_norm > 0.5).float()
        peak_weight = 1.0 + is_peak * 0.5  # 1.5x weight for peaks
        peak_loss = torch.mean(peak_weight * (predictions - targets_norm) ** 2)

        # Combine losses with annealing
        # Gradually increase uncertainty loss weight to encourage better calibration
        uncertainty_weight = min(0.1, epoch / 50 * 0.1)

        total_loss = (
            mse_loss +
            uncertainty_weight * uncertainty_loss +
            0.3 * peak_loss
        )

        return total_loss

    def train_epoch(self, train_loader: DataLoader, epoch: int) -> Dict[str, float]:
        """Train for one epoch."""
        self.model.train()
        total_loss = 0
        num_batches = 0

        for batch_idx, (inputs, targets) in enumerate(train_loader):
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            targets = targets.to(self.device)

            self.optimizer.zero_grad()

            outputs = self.model(
                x=inputs['x'],
                hour=inputs['hour'],
                day_of_week=inputs['day_of_week'],
                month=inputs['month']
            )

            loss = self.compute_loss(outputs, targets, epoch)

            loss.backward()

            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)

            self.optimizer.step()

            total_loss += loss.item()
            num_batches += 1

            if batch_idx % self.log_interval == 0:
                print(f"  Epoch {epoch} | Batch {batch_idx}/{len(train_loader)} | Loss: {loss.item():.4f}")

        avg_loss = total_loss / num_batches
        return {'train_loss': avg_loss}

    @torch.no_grad()
    def validate(self, val_loader: DataLoader) -> Dict[str, float]:
        """Validate the model."""
        self.model.eval()
        total_loss = 0
        num_batches = 0

        all_predictions = []
        all_targets = []
        all_uncertainties = []

        for inputs, targets in val_loader:
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            targets = targets.to(self.device)

            outputs = self.model(
                x=inputs['x'],
                hour=inputs['hour'],
                day_of_week=inputs['day_of_week'],
                month=inputs['month']
            )

            loss = self.criterion(outputs['forecasts'], targets)

            total_loss += loss.item()
            num_batches += 1

            # Denormalize for metrics
            preds_denorm = outputs['forecasts'].cpu().numpy() * self.target_std + self.target_mean
            targets_denorm = targets.cpu().numpy() * self.target_std + self.target_mean

            all_predictions.extend(preds_denorm.flatten())
            all_targets.extend(targets_denorm.flatten())
            all_uncertainties.extend(torch.exp(outputs['uncertainty']).cpu().numpy().flatten())

        avg_loss = total_loss / num_batches

        # Compute additional metrics
        all_predictions = np.array(all_predictions)
        all_targets = np.array(all_targets)
        all_uncertainties = np.array(all_uncertainties)

        mae = np.mean(np.abs(all_predictions - all_targets))
        mape = np.mean(np.abs((all_targets - all_predictions) / (all_targets + 1e-8))) * 100
        rmse = np.sqrt(np.mean((all_predictions - all_targets) ** 2))

        # Coverage: percentage of true values within 95% CI
        lower = all_predictions - 1.96 * all_uncertainties
        upper = all_predictions + 1.96 * all_uncertainties
        coverage = np.mean((all_targets >= lower) & (all_targets <= upper)) * 100

        return {
            'val_loss': avg_loss,
            'mae': mae,
            'mape': mape,
            'rmse': rmse,
            'coverage_95': coverage
        }

    def train(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        resume_from: Optional[str] = None
    ) -> Dict[str, List[float]]:
        """
        Full training loop.

        Args:
            train_loader: Training data loader
            val_loader: Validation data loader
            resume_from: Optional checkpoint path to resume from

        Returns:
            Dictionary of training metrics over time
        """
        start_epoch = 0

        if resume_from:
            checkpoint = self.load_checkpoint(resume_from)
            start_epoch = checkpoint['epoch'] + 1
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            print(f"Resumed from epoch {start_epoch}")

        for epoch in range(start_epoch, self.num_epochs):
            print(f"\nEpoch {epoch + 1}/{self.num_epochs}")

            # Train
            train_metrics = self.train_epoch(train_loader, epoch)
            self.train_losses.append(train_metrics['train_loss'])

            # Validate
            val_metrics = self.validate(val_loader)
            self.val_losses.append(val_metrics['val_loss'])

            print(f"Train Loss: {train_metrics['train_loss']:.4f}")
            print(f"Val Loss: {val_metrics['val_loss']:.4f}")
            print(f"MAE: {val_metrics['mae']:.2f} | RMSE: {val_metrics['rmse']:.2f}")
            print(f"MAPE: {val_metrics['mape']:.2f}% | Coverage: {val_metrics['coverage_95']:.1f}%")

            # Learning rate scheduling
            self.scheduler.step()

            # Early stopping check
            if val_metrics['val_loss'] < self.best_val_loss:
                self.best_val_loss = val_metrics['val_loss']
                self.epochs_without_improvement = 0
                self.save_checkpoint(epoch, 'best_model.pt')
                print(f"New best model saved (val_loss: {self.best_val_loss:.4f})")
            else:
                self.epochs_without_improvement += 1
                print(f"No improvement for {self.epochs_without_improvement} epochs")

            if self.epochs_without_improvement >= self.patience:
                print(f"Early stopping triggered after {epoch + 1} epochs")
                break

            # Save periodic checkpoint
            if (epoch + 1) % 10 == 0:
                self.save_checkpoint(epoch, f'checkpoint_epoch_{epoch + 1}.pt')

        return {
            'train_losses': self.train_losses,
            'val_losses': self.val_losses
        }

    def save_checkpoint(self, epoch: int, filename: str):
        """Save model checkpoint."""
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'train_losses': self.train_losses,
            'val_losses': self.val_losses,
            'best_val_loss': self.best_val_loss,
            'feature_mean': self.feature_mean,
            'feature_std': self.feature_std,
            'target_mean': self.target_mean,
            'target_std': self.target_std
        }

        path = self.checkpoint_dir / filename
        torch.save(checkpoint, path)
        print(f"Checkpoint saved to {path}")

    def load_checkpoint(self, path: str) -> Dict:
        """Load model checkpoint."""
        checkpoint = torch.load(path, map_location=self.device)
        return checkpoint


class ModelEvaluator:
    """Evaluate trained model on test data and generate comprehensive metrics."""

    def __init__(self, model: nn.Module, trainer: EnergyTrainer):
        self.model = model
        self.trainer = trainer
        self.model.eval()

    @torch.no_grad()
    def evaluate(
        self,
        test_loader: DataLoader,
        return_predictions: bool = False
    ) -> Dict:
        """
        Evaluate model on test set.

        Args:
            test_loader: Test data loader
            return_predictions: Whether to return raw predictions

        Returns:
            Dictionary of evaluation metrics
        """
        self.model.eval()

        all_predictions = []
        all_targets = []
        all_uncertainties = []
        all_peak_probs = []

        for inputs, targets in test_loader:
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            targets = targets.to(self.device)

            outputs = self.model(
                x=inputs['x'],
                hour=inputs['hour'],
                day_of_week=inputs['day_of_week'],
                month=inputs['month']
            )

            # Denormalize
            preds = outputs['forecasts'].cpu().numpy() * self.trainer.target_std + self.trainer.target_mean
            targets_denorm = targets.cpu().numpy() * self.trainer.target_std + self.trainer.target_mean
            uncertainties = torch.exp(outputs['uncertainty']).cpu().numpy() * self.trainer.target_std
            peak_probs = outputs['peak_probability'].cpu().numpy()

            all_predictions.extend(preds.flatten())
            all_targets.extend(targets_denorm.flatten())
            all_uncertainties.extend(uncertainties.flatten())
            all_peak_probs.extend(peak_probs.flatten())

        all_predictions = np.array(all_predictions)
        all_targets = np.array(all_targets)
        all_uncertainties = np.array(all_uncertainties)
        all_peak_probs = np.array(all_peak_probs)

        # Compute metrics
        mae = np.mean(np.abs(all_predictions - all_targets))
        rmse = np.sqrt(np.mean((all_predictions - all_targets) ** 2))
        mape = np.mean(np.abs((all_targets - all_predictions) / (all_targets + 1e-8))) * 100

        # R-squared
        ss_res = np.sum((all_targets - all_predictions) ** 2)
        ss_tot = np.sum((all_targets - np.mean(all_targets)) ** 2)
        r2 = 1 - (ss_res / ss_tot)

        # Coverage at different confidence levels
        results = {
            'mae': mae,
            'rmse': rmse,
            'mape': mape,
            'r2': r2,
            'mean_uncertainty': np.mean(all_uncertainties),
            'peak_detection_rate': np.mean(all_peak_probs > 0.5)
        }

        for conf_level, multiplier in [(90, 1.645), (95, 1.96), (99, 2.576)]:
            lower = all_predictions - multiplier * all_uncertainties
            upper = all_predictions + multiplier * all_uncertainties
            coverage = np.mean((all_targets >= lower) & (all_targets <= upper)) * 100
            results[f'coverage_{conf_level}'] = coverage

        # Pinball loss for quantile forecasting
        for quantile in [0.1, 0.5, 0.9]:
            errors = all_targets - all_predictions
            pinball_loss = np.mean(np.where(
                errors > 0,
                quantile * errors,
                (quantile - 1) * errors
            ))
            results[f'pinball_{int(quantile*100)}'] = pinball_loss

        if return_predictions:
            results['predictions'] = all_predictions
            results['targets'] = all_targets
            results['uncertainties'] = all_uncertainties

        return results
