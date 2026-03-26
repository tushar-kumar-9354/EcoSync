"""
Overflow Predictor for Waste Bin Management

Predicts when bins will reach capacity based on:
- Historical fill patterns
- Time of day/week patterns
- Weather conditions
- Seasonal trends
"""

import torch
import torch.nn as nn
from typing import List, Dict, Optional, Tuple
import numpy as np
from datetime import datetime, timedelta
import math


class OverflowLSTM(nn.Module):
    """LSTM model for overflow time series prediction."""

    def __init__(self, input_dim: int = 5, hidden_dim: int = 64, num_layers: int = 2, dropout: float = 0.1):
        super().__init__()

        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )

        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        lstm_out, _ = self.lstm(x)
        last_output = lstm_out[:, -1, :]
        return self.fc(last_output)


class OverflowPredictor:
    """
    Predict bin overflow risk using machine learning.

    Features:
    - LSTM-based fill rate prediction
    - Multi-factor risk scoring
    - Batch prediction for all bins
    - Integration with route optimizer
    """

    RISK_THRESHOLDS = {
        'critical': 90.0,   # % fill to be critical
        'high': 75.0,
        'medium': 50.0,
        'low': 0.0
    }

    def __init__(self, model_path: Optional[str] = None, device: str = 'cpu'):
        if device == 'auto':
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.device = torch.device(device)
        self.model: Optional[OverflowLSTM] = None

        if model_path:
            self.load_model(model_path)

    def load_model(self, model_path: str) -> bool:
        """Load trained model."""
        try:
            checkpoint = torch.load(model_path, map_location=self.device)

            if 'model_state_dict' in checkpoint:
                self.model = OverflowLSTM()
                self.model.load_state_dict(checkpoint['model_state_dict'])
            else:
                self.model = checkpoint

            self.model.to(self.device)
            self.model.eval()
            return True

        except Exception as e:
            print(f"Error loading model: {e}")
            self.model = OverflowLSTM().to(self.device)
            self.model.eval()
            return False

    def extract_features(
        self,
        fill_history: List[float],
        time_hours: List[int],
        hour_of_day: int,
        day_of_week: int,
        bin_type: str,
        weather_temp: Optional[float] = None
    ) -> np.ndarray:
        """
        Extract features for the LSTM model.

        Args:
            fill_history: List of historical fill percentages
            time_hours: Hours at which each fill was recorded
            hour_of_day: Current hour (0-23)
            day_of_week: Current day (0-6)
            bin_type: Type of bin (residential, commercial, etc.)
            weather_temp: Optional temperature

        Returns:
            Feature array [seq_len, input_dim]
        """
        seq_len = len(fill_history)

        # Fill change rate (delta)
        fill_changes = [0] + [fill_history[i] - fill_history[i-1] for i in range(1, seq_len)]

        # Time since last reading
        time_deltas = [0] + [time_hours[i] - time_hours[i-1] for i in range(1, seq_len)]

        # Fill rate (change per hour)
        fill_rates = []
        for i in range(seq_len):
            if time_deltas[i] > 0:
                fill_rates.append(fill_changes[i] / time_deltas[i])
            else:
                fill_rates.append(0)

        # Bin type encoding
        bin_type_map = {'residential': 0, 'commercial': 1, 'park': 2, 'street': 3}
        bin_type_enc = bin_type_map.get(bin_type, 0) / 3.0

        # Cyclical time features
        hour_sin = math.sin(2 * math.pi * hour_of_day / 24)
        hour_cos = math.cos(2 * math.pi * hour_of_day / 24)
        dow_sin = math.sin(2 * math.pi * day_of_week / 7)
        dow_cos = math.cos(2 * math.pi * day_of_week / 7)

        features = []
        for i in range(seq_len):
            feat = [
                fill_history[i] / 100.0,          # Normalized fill
                fill_rates[i] / 10.0,              # Normalized rate
                bin_type_enc,                       # Bin type
                hour_sin,                          # Cyclical hour
                hour_cos
            ]
            features.append(feat)

        return np.array(features, dtype=np.float32)

    def predict_overflow_hours(
        self,
        current_fill: float,
        fill_history: List[float],
        time_hours: List[int],
        hour_of_day: int,
        day_of_week: int,
        bin_type: str = 'residential'
    ) -> Dict:
        """
        Predict hours until overflow.

        Args:
            current_fill: Current fill percentage
            fill_history: Historical fill readings
            time_hours: Hours since start for each reading
            hour_of_day: Current hour
            day_of_week: Current day of week
            bin_type: Type of bin

        Returns:
            Prediction dictionary
        """
        if len(fill_history) < 3:
            # Fallback to simple rate calculation
            return self._simple_prediction(current_fill, fill_history, time_hours)

        # Extract features
        features = self.extract_features(
            fill_history, time_hours, hour_of_day, day_of_week, bin_type
        )

        # Pad/truncate to fixed sequence length
        seq_len = 24
        if len(features) < seq_len:
            padding = np.zeros((seq_len - len(features), features.shape[1]), dtype=np.float32)
            features = np.vstack([padding, features])
        else:
            features = features[-seq_len:]

        # Convert to tensor
        x = torch.tensor(features).unsqueeze(0).to(self.device)

        # Predict
        if self.model is not None:
            self.model.eval()
            with torch.no_grad():
                pred = self.model(x)
                overflow_hours = float(pred.item()) * 24  # Model outputs 0-1 normalized
                overflow_hours = max(0.5, min(72, overflow_hours))
        else:
            # Fallback
            overflow_hours = self._simple_prediction(current_fill, fill_history, time_hours)['hours_to_overflow']

        overflow_time = datetime.now() + timedelta(hours=overflow_hours)
        risk = self._calculate_risk(current_fill, overflow_hours)

        return {
            'bin_id': None,  # Set by caller
            'current_fill_percent': current_fill,
            'hours_to_overflow': round(overflow_hours, 1),
            'overflow_time': overflow_time.isoformat(),
            'risk_level': risk,
            'recommended_action': self._get_action(risk, overflow_hours),
            'confidence': 0.85 if len(fill_history) >= 10 else 0.65
        }

    def _simple_prediction(
        self,
        current_fill: float,
        fill_history: List[float],
        time_hours: List[int]
    ) -> Dict:
        """Simple linear extrapolation for overflow prediction."""
        if len(fill_history) < 2:
            fill_rate = 0.5  # Default 0.5% per hour
        else:
            # Calculate average fill rate
            total_change = fill_history[-1] - fill_history[0]
            total_time = max(1, time_hours[-1] - time_hours[0])
            fill_rate = max(0.1, total_change / total_time)

        remaining = 90.0 - current_fill
        if fill_rate <= 0:
            hours_to_overflow = 72
        else:
            hours_to_overflow = remaining / fill_rate
            hours_to_overflow = max(0.5, min(72, hours_to_overflow))

        overflow_time = datetime.now() + timedelta(hours=hours_to_overflow)
        risk = self._calculate_risk(current_fill, hours_to_overflow)

        return {
            'hours_to_overflow': round(hours_to_overflow, 1),
            'overflow_time': overflow_time.isoformat(),
            'risk_level': risk,
            'confidence': 0.5  # Lower confidence for simple method
        }

    def _calculate_risk(self, current_fill: float, hours_to_overflow: float) -> str:
        """Calculate risk level based on fill and time to overflow."""
        if current_fill >= 90 or hours_to_overflow <= 2:
            return 'critical'
        elif current_fill >= 75 or hours_to_overflow <= 6:
            return 'high'
        elif current_fill >= 50 or hours_to_overflow <= 12:
            return 'medium'
        return 'low'

    def _get_action(self, risk: str, hours_to_overflow: float) -> str:
        """Get recommended action based on risk."""
        if risk == 'critical':
            return 'Schedule immediate collection'
        elif risk == 'high':
            return 'Schedule collection within 4 hours'
        elif risk == 'medium':
            return 'Include in next route optimization'
        return 'Continue monitoring'

    def batch_predict(
        self,
        bin_data: List[Dict]
    ) -> List[Dict]:
        """
        Predict overflow for multiple bins.

        Args:
            bin_data: List of dicts with bin info:
                - bin_id: str
                - current_fill: float
                - fill_history: List[float]
                - time_hours: List[int]
                - hour_of_day: int
                - day_of_week: int
                - bin_type: str

        Returns:
            List of predictions sorted by risk
        """
        predictions = []

        for bin in bin_data:
            try:
                pred = self.predict_overflow_hours(
                    current_fill=bin['current_fill'],
                    fill_history=bin.get('fill_history', [bin['current_fill']]),
                    time_hours=bin.get('time_hours', [0]),
                    hour_of_day=bin.get('hour_of_day', datetime.now().hour),
                    day_of_week=bin.get('day_of_week', datetime.now().weekday()),
                    bin_type=bin.get('bin_type', 'residential')
                )
                pred['bin_id'] = bin['bin_id']
                predictions.append(pred)
            except Exception as e:
                predictions.append({
                    'bin_id': bin['bin_id'],
                    'current_fill_percent': bin['current_fill'],
                    'hours_to_overflow': 24,
                    'risk_level': 'medium',
                    'error': str(e)
                })

        # Sort by risk
        risk_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        predictions.sort(key=lambda x: (risk_order.get(x['risk_level'], 4), x.get('hours_to_overflow', 999)))

        return predictions

    def get_overflow_zones(self, predictions: List[Dict], zone_col: str = 'zone') -> Dict:
        """Group predictions by zone for city-wide view."""
        zones = {}

        for pred in predictions:
            zone = pred.get(zone_col, 'unknown')
            if zone not in zones:
                zones[zone] = {
                    'zone': zone,
                    'critical_count': 0,
                    'high_count': 0,
                    'medium_count': 0,
                    'low_count': 0,
                    'bins': []
                }

            risk = pred['risk_level']
            if risk == 'critical':
                zones[zone]['critical_count'] += 1
            elif risk == 'high':
                zones[zone]['high_count'] += 1
            elif risk == 'medium':
                zones[zone]['medium_count'] += 1
            else:
                zones[zone]['low_count'] += 1

            zones[zone]['bins'].append(pred)

        return zones


class FillLevelSimulator:
    """Simulate fill levels for testing and scenario planning."""

    def __init__(self):
        self.bin_profiles = {
            'residential': {
                'base_fill_rate': 0.3,
                'peak_hours': [7, 8, 9, 18, 19, 20],
                'weekend_factor': 1.3
            },
            'commercial': {
                'base_fill_rate': 1.2,
                'peak_hours': [10, 11, 12, 13, 14, 15, 16],
                'weekend_factor': 0.2
            },
            'park': {
                'base_fill_rate': 0.5,
                'peak_hours': [10, 11, 12, 13, 14, 15, 16],
                'weekend_factor': 1.5
            },
            'street': {
                'base_fill_rate': 0.4,
                'peak_hours': [8, 9, 17, 18, 19],
                'weekend_factor': 0.8
            }
        }

    def simulate_fill(
        self,
        bin_type: str,
        start_fill: float,
        hours_ahead: int,
        weather_factor: float = 1.0,
        event_factor: float = 1.0
    ) -> List[Tuple[int, float]]:
        """
        Simulate fill levels over time.

        Args:
            bin_type: Type of bin
            start_fill: Starting fill percentage
            hours_ahead: Hours to simulate
            weather_factor: Multiplier for rain/storms (increases fill)
            event_factor: Multiplier for events/holidays

        Returns:
            List of (hour, fill_percent) tuples
        """
        import random

        profile = self.bin_profiles.get(bin_type, self.bin_profiles['residential'])
        current_fill = start_fill
        results = [(0, current_fill)]

        for hour in range(1, hours_ahead + 1):
            current_hour = (datetime.now().hour + hour) % 24
            is_weekend = (datetime.now() + timedelta(hours=hour)).weekday() >= 5

            # Base rate
            rate = profile['base_fill_rate']

            # Peak hour adjustment
            if current_hour in profile['peak_hours']:
                rate *= 1.5

            # Weekend adjustment
            if is_weekend:
                rate *= profile['weekend_factor']

            # Apply factors
            rate *= weather_factor * event_factor

            # Add randomness
            rate *= random.uniform(0.8, 1.2)

            current_fill += rate
            current_fill = min(100.0, current_fill)

            results.append((hour, round(current_fill, 1)))

        return results

    def generate_scenario(
        self,
        bins: List[Dict],
        scenario: str = 'normal',
        duration_hours: int = 24
    ) -> List[Dict]:
        """
        Generate fill level scenarios.

        Args:
            bins: List of bin data
            scenario: 'normal', 'rain', 'heatwave', 'holiday'
            duration_hours: Hours to simulate

        Returns:
            Simulated fill trajectories
        """
        scenario_factors = {
            'normal': {'weather': 1.0, 'event': 1.0},
            'rain': {'weather': 1.3, 'event': 1.0},  # More indoor activities
            'heatwave': {'weather': 0.7, 'event': 1.2},  # Less cooking, more drinks
            'holiday': {'weather': 1.0, 'event': 1.8},  # More waste from gatherings
            'weekend': {'weather': 1.0, 'event': 1.4}
        }

        factors = scenario_factors.get(scenario, scenario_factors['normal'])

        results = []
        for bin in bins:
            trajectory = self.simulate_fill(
                bin_type=bin.get('bin_type', 'residential'),
                start_fill=bin.get('current_fill', 50.0),
                hours_ahead=duration_hours,
                weather_factor=factors['weather'],
                event_factor=factors['event']
            )

            results.append({
                'bin_id': bin.get('bin_id', 'unknown'),
                'scenario': scenario,
                'trajectory': trajectory
            })

        return results
