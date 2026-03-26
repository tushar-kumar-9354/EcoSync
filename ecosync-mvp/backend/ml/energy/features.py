"""
Feature Engineering for Energy Demand Forecasting

Features include:
- Time-based: hour, day of week, month, season, holidays
- Weather: temperature, humidity, wind, pressure, weather conditions
- Occupancy proxies: historical consumption patterns
- Cyclical encoding for periodic features
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Any


class FeatureEngineering:
    """
    Feature engineering pipeline for energy demand prediction.

    Generates features from raw temporal and weather data.
    """

    def __init__(self):
        self.hour_bins = [0, 6, 9, 12, 14, 17, 20, 24]
        self.temp_bins = [-10, 0, 10, 20, 25, 30, 35, 50]
        self._feature_columns: List[str] = []

    def create_temporal_features(self, df: pd.DataFrame, timestamp_col: str = 'timestamp') -> pd.DataFrame:
        """Create time-based features from timestamp."""
        df = df.copy()

        if not pd.api.types.is_datetime64_any_dtype(df[timestamp_col]):
            df[timestamp_col] = pd.to_datetime(df[timestamp_col])

        dt = df[timestamp_col]

        # Basic temporal features
        df['hour'] = dt.dt.hour
        df['day_of_week'] = dt.dt.dayofweek
        df['day_of_year'] = dt.dt.dayofyear
        df['week_of_year'] = dt.dt.isocalendar().week.astype(int)
        df['month'] = dt.dt.month
        df['quarter'] = dt.dt.quarter
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        df['is_business_hour'] = ((df['hour'] >= 8) & (df['hour'] <= 18) & (~df['is_weekend'].astype(bool))).astype(int)
        df['is_peak_hour'] = df['hour'].isin([9, 10, 11, 14, 15, 16, 17]).astype(int)

        # Cyclical encoding for periodic features
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        df['year_sin'] = np.sin(2 * np.pi * df['day_of_year'] / 365)
        df['year_cos'] = np.cos(2 * np.pi * df['day_of_year'] / 365)

        # Season encoding (Northern Hemisphere)
        def get_season(month):
            if month in [12, 1, 2]:
                return 0  # Winter
            elif month in [3, 4, 5]:
                return 1  # Spring
            elif month in [6, 7, 8]:
                return 2  # Summer
            else:
                return 3  # Fall

        df['season'] = df['month'].apply(get_season)

        # Part of day categories
        def get_part_of_day(hour):
            if 6 <= hour < 12:
                return 0  # Morning
            elif 12 <= hour < 17:
                return 1  # Afternoon
            elif 17 <= hour < 21:
                return 2  # Evening
            else:
                return 3  # Night

        df['part_of_day'] = df['hour'].apply(get_part_of_day)

        return df

    def create_weather_features(self, df: pd.DataFrame, weather_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Create weather-derived features."""
        df = df.copy()

        # If weather data provided, merge it
        if weather_df is not None:
            df = df.merge(weather_df, on='timestamp', how='left', suffixes=('', '_weather'))

        # Temperature features
        if 'temperature' in df.columns:
            df['temp_squared'] = df['temperature'] ** 2
            df['temp_cubed'] = df['temperature'] ** 3

            # Heating/cooling degree indicators
            df['heating_degree'] = np.maximum(0, 18 - df['temperature'])
            df['cooling_degree'] = np.maximum(0, df['temperature'] - 18)

            # Thermal comfort zone indicator
            df['in_comfort_zone'] = ((df['temperature'] >= 18) & (df['temperature'] <= 24)).astype(int)

            # Temperature bins
            df['temp_bin'] = pd.cut(df['temperature'], bins=self.temp_bins, labels=False)

        # Humidity features
        if 'humidity' in df.columns:
            df['humidity_squared'] = df['humidity'] ** 2
            df['high_humidity'] = (df['humidity'] > 70).astype(int)

        # Wind features
        if 'wind_speed' in df.columns:
            df['wind_speed_squared'] = df['wind_speed'] ** 2
            df['high_wind'] = (df['wind_speed'] > 20).astype(int)

        # Pressure features
        if 'pressure' in df.columns:
            df['pressure_change'] = df['pressure'].diff()
            df['pressure_change'] = df['pressure_change'].fillna(0)

        # Weather condition encoding
        if 'weather_condition' in df.columns:
            condition_dummies = pd.get_dummies(df['weather_condition'], prefix='weather')
            df = pd.concat([df, condition_dummies], axis=1)

        return df

    def create_lag_features(
        self,
        df: pd.DataFrame,
        value_col: str,
        lags: List[int] = [1, 2, 3, 6, 12, 24, 48, 168],
        group_col: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Create lag features for time series.

        Args:
            df: Input dataframe
            value_col: Column to create lags from
            lags: List of lag periods (hours)
            group_col: Column to group by (e.g., sensor_id, zone)
        """
        df = df.copy()

        if group_col:
            for lag in lags:
                df[f'{value_col}_lag_{lag}h'] = df.groupby(group_col)[value_col].shift(lag)
        else:
            for lag in lags:
                df[f'{value_col}_lag_{lag}h'] = df[value_col].shift(lag)

        return df

    def create_rolling_features(
        self,
        df: pd.DataFrame,
        value_col: str,
        windows: List[int] = [3, 6, 12, 24, 48, 168],
        group_col: Optional[str] = None,
        agg: str = 'mean'
    ) -> pd.DataFrame:
        """
        Create rolling window statistics.

        Args:
            df: Input dataframe
            value_col: Column to aggregate
            windows: List of window sizes (hours)
            group_col: Column to group by
            agg: Aggregation function ('mean', 'std', 'min', 'max')
        """
        df = df.copy()

        for window in windows:
            roll_col = f'{value_col}_roll_{window}h_{agg}'

            if group_col:
                df[roll_col] = df.groupby(group_col)[value_col].transform(
                    lambda x: x.rolling(window, min_periods=1).agg(agg)
                )
            else:
                df[roll_col] = df[value_col].rolling(window, min_periods=1).agg(agg)

        return df

    def create_ewm_features(
        self,
        df: pd.DataFrame,
        value_col: str,
        spans: List[int] = [3, 6, 12, 24],
        group_col: Optional[str] = None
    ) -> pd.DataFrame:
        """Create exponentially weighted moving average features."""
        df = df.copy()

        for span in spans:
            ewm_col = f'{value_col}_ewm_{span}h'

            if group_col:
                df[ewm_col] = df.groupby(group_col)[value_col].transform(
                    lambda x: x.ewm(span=span, adjust=False).mean()
                )
            else:
                df[value_col] = df[value_col]
                df[ewm_col] = df[value_col].ewm(span=span, adjust=False).mean()

        return df

    def create_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create interaction features between existing variables."""
        df = df.copy()

        # Temperature-humidity interaction (heat index approximation)
        if 'temperature' in df.columns and 'humidity' in df.columns:
            df['heat_index'] = (
                df['temperature'] +
                0.05 * df['humidity'] * df['temperature'] / 100
            )
            df['temp_humidity_interaction'] = df['temperature'] * df['humidity'] / 100

        # Occupancy-weather interaction
        if 'is_business_hour' in df.columns and 'temperature' in df.columns:
            df['business_temp_interaction'] = df['is_business_hour'] * df['temperature']

        if 'is_peak_hour' in df.columns and 'temperature' in df.columns:
            df['peak_temp_interaction'] = df['is_peak_hour'] * df['temperature']

        # Weekend-weather interaction
        if 'is_weekend' in df.columns and 'temperature' in df.columns:
            df['weekend_temp_interaction'] = df['is_weekend'] * df['temperature']

        return df

    def create_holiday_features(self, df: pd.DataFrame, holidays: Optional[List[datetime]] = None) -> pd.DataFrame:
        """Create holiday and special event features."""
        df = df.copy()

        if holidays is None:
            # Default US federal holidays (approximate)
            holidays = self._get_default_holidays()

        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])

        holiday_dates = {h.strftime('%m-%d') for h in holidays}
        df['is_holiday'] = df['timestamp'].dt.strftime('%m-%d').isin(holiday_dates).astype(int)

        # Days near holiday (reduced business activity)
        df['near_holiday'] = (
            df['timestamp'].dt.strftime('%m-%d').isin([
                '12-24', '12-25', '12-26', '01-01', '07-03', '07-04', '11-27', '11-28'
            ])
        ).astype(int)

        return df

    def _get_default_holidays(self) -> List[datetime]:
        """Get default US federal holidays for the year."""
        year = datetime.now().year
        return [
            datetime(year, 1, 1),   # New Year
            datetime(year, 1, 15),  # MLK Day
            datetime(year, 2, 19),  # Presidents Day
            datetime(year, 5, 27),  # Memorial Day
            datetime(year, 7, 4),   # Independence Day
            datetime(year, 9, 2),   # Labor Day
            datetime(year, 10, 14), # Columbus Day
            datetime(year, 11, 11), # Veterans Day
            datetime(year, 11, 28), # Thanksgiving
            datetime(year, 12, 25), # Christmas
        ]

    def create_all_features(
        self,
        df: pd.DataFrame,
        value_col: str = 'demand_kwh',
        weather_df: Optional[pd.DataFrame] = None,
        holidays: Optional[List[datetime]] = None,
        group_col: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Create all feature types in a single pipeline.

        Args:
            df: Input dataframe with 'timestamp' and demand columns
            value_col: Target/demand column name
            weather_df: Optional weather dataframe to merge
            holidays: Optional list of holiday dates
            group_col: Column to group lag/rolling features by

        Returns:
            DataFrame with all engineered features
        """
        df = df.copy()

        # Temporal features
        df = self.create_temporal_features(df)

        # Weather features
        if weather_df is not None or any(col in df.columns for col in ['temperature', 'humidity', 'pressure']):
            df = self.create_weather_features(df, weather_df)

        # Lag features
        df = self.create_lag_features(df, value_col, lags=[1, 2, 3, 6, 12, 24, 48, 168], group_col=group_col)

        # Rolling features
        df = self.create_rolling_features(df, value_col, windows=[3, 6, 12, 24, 48], group_col=group_col, agg='mean')
        df = self.create_rolling_features(df, value_col, windows=[6, 12, 24], group_col=group_col, agg='std')

        # EWM features
        df = self.create_ewm_features(df, value_col, spans=[3, 6, 12, 24], group_col=group_col)

        # Interaction features
        df = self.create_interaction_features(df)

        # Holiday features
        df = self.create_holiday_features(df, holidays)

        # Drop rows with NaN from lagging (first few rows)
        df = df.dropna()

        self._feature_columns = [col for col in df.columns if col not in [
            'timestamp', value_col, group_col
        ]]

        return df

    def get_feature_columns(self) -> List[str]:
        """Get list of feature column names."""
        return self._feature_columns

    def get_feature_importance_summary(self) -> Dict[str, str]:
        """
        Return expected feature importance based on domain knowledge.

        This is a rough guide - actual importance should be computed
        from the trained model using SHAP or permutation importance.
        """
        return {
            'high_importance': [
                'hour_sin', 'hour_cos', 'day_of_week', 'is_weekend',
                'lag_1h', 'lag_24h', 'lag_168h',
                'roll_24h_mean', 'roll_24h_std',
                'temperature', 'cooling_degree', 'heating_degree',
                'is_business_hour', 'is_peak_hour'
            ],
            'medium_importance': [
                'month_sin', 'month_cos', 'season',
                'roll_6h_mean', 'roll_12h_mean',
                'ewm_12h', 'ewm_24h',
                'humidity', 'wind_speed',
                'is_holiday', 'near_holiday'
            ],
            'low_importance': [
                'quarter', 'part_of_day', 'week_of_year',
                'temp_squared', 'humidity_squared',
                'temp_humidity_interaction'
            ]
        }


class DataPreprocessor:
    """Handle data preprocessing: normalization, handling missing values, outlier removal."""

    def __init__(self, normalization_method: str = 'standard'):
        """
        Args:
            normalization_method: 'standard' (z-score) or 'minmax'
        """
        self.method = normalization_method
        self.means: Dict[str, float] = {}
        self.stds: Dict[str, float] = {}
        self.mins: Dict[str, float] = {}
        self.maxs: Dict[str, float] = {}
        self.feature_columns: List[str] = []

    def fit(self, df: pd.DataFrame, feature_columns: List[str]) -> 'DataPreprocessor':
        """Compute normalization parameters from training data."""
        self.feature_columns = feature_columns

        if self.method == 'standard':
            for col in feature_columns:
                self.means[col] = df[col].mean()
                self.stds[col] = df[col].std()
                if self.stds[col] == 0:
                    self.stds[col] = 1  # Avoid division by zero
        else:  # minmax
            for col in feature_columns:
                self.mins[col] = df[col].min()
                self.maxs[col] = df[col].max()
                if self.maxs[col] == self.mins[col]:
                    self.maxs[col] = self.mins[col] + 1  # Avoid division by zero

        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply normalization to data."""
        df = df.copy()

        for col in self.feature_columns:
            if col not in df.columns:
                continue

            if self.method == 'standard':
                df[col] = (df[col] - self.means[col]) / self.stds[col]
            else:
                df[col] = (df[col] - self.mins[col]) / (self.maxs[col] - self.mins[col])

        return df

    def fit_transform(self, df: pd.DataFrame, feature_columns: List[str]) -> pd.DataFrame:
        """Fit and transform in one call."""
        self.fit(df, feature_columns)
        return self.transform(df)

    def inverse_transform(self, df: pd.DataFrame, col: str) -> pd.Series:
        """Reverse normalization for a single column."""
        if self.method == 'standard':
            return df[col] * self.stds[col] + self.means[col]
        else:
            return df[col] * (self.maxs[col] - self.mins[col]) + self.mins[col]

    def handle_missing_values(self, df: pd.DataFrame, strategy: str = 'interpolate') -> pd.DataFrame:
        """
        Handle missing values in dataframe.

        Args:
            df: Input dataframe
            strategy: 'interpolate' (linear), 'forward_fill', 'backward_fill', 'mean'
        """
        df = df.copy()

        if strategy == 'interpolate':
            df = df.interpolate(method='linear', limit_direction='both')
        elif strategy == 'forward_fill':
            df = df.fillna(method='ffill')
        elif strategy == 'backward_fill':
            df = df.fillna(method='bfill')
        elif strategy == 'mean':
            df = df.fillna(df.mean())

        # Any remaining NaNs, fill with 0
        df = df.fillna(0)

        return df

    def remove_outliers(
        self,
        df: pd.DataFrame,
        columns: List[str],
        n_std: float = 3.0
    ) -> pd.DataFrame:
        """
        Remove outliers beyond n standard deviations.

        Uses z-score method.
        """
        df = df.copy()

        for col in columns:
            if col not in df.columns:
                continue

            mean = df[col].mean()
            std = df[col].std()
            lower = mean - n_std * std
            upper = mean + n_std * std

            df = df[(df[col] >= lower) & (df[col] <= upper)]

        return df
