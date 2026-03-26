"""
ML Training Pipeline Infrastructure

Implements:
- Experiment tracking (MLflow-like functionality)
- Data versioning (DVC-like)
- Drift detection
- Model registry
- Retraining orchestration
"""

import torch
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
import hashlib
import os
from pathlib import Path
import shutil


class ExperimentTracker:
    """
    Lightweight experiment tracking for EcoSync ML models.

    Tracks:
    - Experiment parameters
    - Training metrics
    - Model artifacts
    - Dataset versions
    """

    def __init__(self, storage_path: str = "experiments"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.experiments: Dict[str, Dict] = {}
        self.runs: Dict[str, List[Dict]] = {}

    def create_experiment(self, name: str, description: str = "") -> str:
        """Create a new experiment."""
        exp_id = hashlib.md5(f"{name}{datetime.now().isoformat()}".encode()).hexdigest()[:8]

        self.experiments[exp_id] = {
            'id': exp_id,
            'name': name,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'runs': [],
            'best_run': None,
            'best_metric': None
        }

        return exp_id

    def log_run(
        self,
        experiment_id: str,
        params: Dict[str, Any],
        metrics: Dict[str, float],
        artifacts: Optional[Dict[str, str]] = None,
        status: str = "running"
    ) -> str:
        """
        Log a single training run.

        Args:
            experiment_id: Experiment ID
            params: Hyperparameters
            metrics: Training/validation metrics
            artifacts: Paths to model files, etc.
            status: 'running', 'completed', 'failed'

        Returns:
            Run ID
        """
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")

        run_id = hashlib.md5(
            f"{experiment_id}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        run = {
            'id': run_id,
            'experiment_id': experiment_id,
            'params': params,
            'metrics': metrics,
            'artifacts': artifacts or {},
            'status': status,
            'created_at': datetime.now().isoformat(),
            'completed_at': None,
            'duration_seconds': None
        }

        if experiment_id not in self.runs:
            self.runs[experiment_id] = []
        self.runs[experiment_id].append(run)

        # Update experiment
        self.experiments[experiment_id]['runs'].append(run_id)

        # Check if best
        if status == "completed":
            primary_metric = metrics.get('val_loss') or metrics.get('val_mae')
            if primary_metric is not None:
                best = self.experiments[experiment_id]['best_metric']
                if best is None or primary_metric < best:
                    self.experiments[experiment_id]['best_metric'] = primary_metric
                    self.experiments[experiment_id]['best_run'] = run_id

        return run_id

    def complete_run(self, run_id: str, experiment_id: str, final_metrics: Optional[Dict] = None):
        """Mark a run as completed."""
        runs = self.runs.get(experiment_id, [])
        for run in runs:
            if run['id'] == run_id:
                run['status'] = 'completed'
                run['completed_at'] = datetime.now().isoformat()
                if final_metrics:
                    run['metrics'].update(final_metrics)

                # Calculate duration
                start = datetime.fromisoformat(run['created_at'])
                end = datetime.fromisoformat(run['completed_at'])
                run['duration_seconds'] = (end - start).total_seconds()
                break

    def get_experiment(self, experiment_id: str) -> Dict:
        """Get experiment details with all runs."""
        exp = self.experiments.get(experiment_id, {})
        if exp:
            runs = self.runs.get(experiment_id, [])
            exp['run_count'] = len(runs)
            exp['completed_runs'] = len([r for r in runs if r['status'] == 'completed'])
            exp['failed_runs'] = len([r for r in runs if r['status'] == 'failed'])
        return exp

    def compare_runs(self, experiment_id: str, metric: str = 'val_loss') -> pd.DataFrame:
        """Compare all runs of an experiment on a specific metric."""
        runs = self.runs.get(experiment_id, [])

        data = []
        for run in runs:
            if run['status'] == 'completed' and metric in run['metrics']:
                data.append({
                    'run_id': run['id'],
                    'params': json.dumps(run['params']),
                    metric: run['metrics'][metric],
                    'duration': run.get('duration_seconds'),
                    'created_at': run['created_at']
                })

        return pd.DataFrame(data)

    def save(self):
        """Save experiments to disk."""
        data = {
            'experiments': self.experiments,
            'runs': self.runs
        }

        with open(self.storage_path / 'experiments.json', 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def load(self):
        """Load experiments from disk."""
        path = self.storage_path / 'experiments.json'
        if path.exists():
            with open(path, 'r') as f:
                data = json.load(f)
                self.experiments = data.get('experiments', {})
                self.runs = data.get('runs', {})


class DataVersioning:
    """
    Simple data versioning for ML datasets.

    Tracks:
    - Dataset hashes
    - Feature statistics
    - Schema
    - Lineage
    """

    def __init__(self, storage_path: str = "data_versions"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.versions: Dict[str, Dict] = {}
        self._load_versions()

    def _load_versions(self):
        """Load existing versions."""
        path = self.storage_path / 'versions.json'
        if path.exists():
            with open(path, 'r') as f:
                self.versions = json.load(f)

    def _save_versions(self):
        """Save versions to disk."""
        with open(self.storage_path / 'versions.json', 'w') as f:
            json.dump(self.versions, f, indent=2, default=str)

    def compute_hash(self, df: pd.DataFrame) -> str:
        """Compute hash of dataframe."""
        content = df.to_csv() if hasattr(df, 'to_csv') else str(df)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def register_version(
        self,
        dataset_name: str,
        df: pd.DataFrame,
        version_tag: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Register a new dataset version.

        Args:
            dataset_name: Name of the dataset
            df: DataFrame
            version_tag: Version tag (e.g., 'v1.0.0')
            metadata: Additional metadata

        Returns:
            Version ID
        """
        version_id = hashlib.md5(
            f"{dataset_name}{version_tag}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        # Compute statistics
        stats = {}
        for col in df.select_dtypes(include=[np.number]).columns:
            stats[col] = {
                'mean': float(df[col].mean()),
                'std': float(df[col].std()),
                'min': float(df[col].min()),
                'max': float(df[col].max()),
                'null_count': int(df[col].isnull().sum())
            }

        self.versions[version_id] = {
            'id': version_id,
            'dataset_name': dataset_name,
            'version_tag': version_tag,
            'hash': self.compute_hash(df),
            'row_count': len(df),
            'column_count': len(df.columns),
            'columns': list(df.columns),
            'statistics': stats,
            'metadata': metadata or {},
            'created_at': datetime.now().isoformat()
        }

        self._save_versions()
        return version_id

    def get_version(self, version_id: str) -> Optional[Dict]:
        """Get version info."""
        return self.versions.get(version_id)

    def compare_versions(self, version_id1: str, version_id2: str) -> Dict:
        """Compare two dataset versions."""
        v1 = self.versions.get(version_id1, {})
        v2 = self.versions.get(version_id2, {})

        return {
            'version1': {
                'tag': v1.get('version_tag'),
                'hash': v1.get('hash'),
                'rows': v1.get('row_count')
            },
            'version2': {
                'tag': v2.get('version_tag'),
                'hash': v2.get('hash'),
                'rows': v2.get('row_count')
            },
            'hash_changed': v1.get('hash') != v2.get('hash'),
            'row_diff': v2.get('row_count', 0) - v1.get('row_count', 0)
        }


class DriftDetector:
    """
    Detect data drift and model degradation.

    Methods:
    - Population Stability Index (PSI)
    - Kolmogorov-Smirnov test
    - Feature drift detection
    - Prediction drift detection
    """

    def __init__(self, threshold: float = 0.2):
        self.threshold = threshold
        self.baseline_stats: Dict[str, Dict] = {}

    def set_baseline(self, data: np.ndarray, feature_name: str = "default"):
        """Set baseline distribution for comparison."""
        self.baseline_stats[feature_name] = {
            'mean': float(np.mean(data)),
            'std': float(np.std(data)),
            'min': float(np.min(data)),
            'max': float(np.max(data)),
            'p5': float(np.percentile(data, 5)),
            'p25': float(np.percentile(data, 25)),
            'p50': float(np.percentile(data, 50)),
            'p75': float(np.percentile(data, 75)),
            'p95': float(np.percentile(data, 95)),
            'histogram': self._compute_histogram(data),
            'n': len(data)
        }

    def _compute_histogram(self, data: np.ndarray, bins: int = 10) -> List[float]:
        """Compute normalized histogram."""
        hist, _ = np.histogram(data, bins=bins, density=True)
        return hist.tolist()

    def compute_psi(
        self,
        baseline: np.ndarray,
        current: np.ndarray,
        n_bins: int = 10
    ) -> float:
        """
        Compute Population Stability Index.

        PSI < 0.1: No significant drift
        0.1 <= PSI < 0.2: Moderate drift
        PSI >= 0.2: Significant drift

        Args:
            baseline: Baseline distribution
            current: Current distribution
            n_bins: Number of bins

        Returns:
            PSI value
        """
        # Create bins based on baseline
        breakpoints = np.percentile(baseline, np.linspace(0, 100, n_bins + 1))

        # Ensure all breakpoints are unique
        breakpoints = np.unique(breakpoints)
        if len(breakpoints) < 3:
            return 0.0

        # Compute actual percentages
        baseline_counts = np.histogram(baseline, bins=breakpoints)[0]
        current_counts = np.histogram(current, bins=breakpoints)[0]

        # Convert to proportions
        baseline_pct = baseline_counts / (len(baseline) + 1e-8)
        current_pct = current_counts / (len(current) + 1e-8)

        # Add small value to avoid log(0)
        baseline_pct = baseline_pct + 0.0001
        current_pct = current_pct + 0.0001

        # Normalize
        baseline_pct = baseline_pct / baseline_pct.sum()
        current_pct = current_pct / current_pct.sum()

        # Compute PSI
        psi = np.sum((current_pct - baseline_pct) * np.log(current_pct / baseline_pct))

        return float(psi)

    def detect_drift(
        self,
        current_data: np.ndarray,
        feature_name: str = "default",
        method: str = "psi"
    ) -> Dict:
        """
        Detect drift from baseline.

        Returns:
            Drift detection result
        """
        if feature_name not in self.baseline_stats:
            return {
                'drifted': False,
                'error': 'No baseline set for this feature'
            }

        baseline = self.baseline_stats[feature_name]

        if method == "psi":
            psi = self.compute_psi(
                np.random.normal(
                    baseline['mean'],
                    baseline['std'],
                    baseline['n']
                ),
                current_data
            )
            drifted = psi >= self.threshold

            return {
                'drifted': drifted,
                'psi': psi,
                'threshold': self.threshold,
                'severity': 'none' if psi < 0.1 else ('moderate' if psi < 0.2 else 'severe'),
                'recommendation': self._get_recommendation(psi)
            }

        elif method == "ks":
            # Kolmogorov-Smirnov test
            from scipy import stats
            baseline_samples = np.random.normal(
                baseline['mean'], baseline['std'], baseline['n']
            )
            ks_stat, p_value = stats.ks_2samp(baseline_samples, current_data)

            return {
                'drifted': p_value < 0.05,
                'ks_statistic': float(ks_stat),
                'p_value': float(p_value)
            }

        return {'drifted': False, 'error': 'Unknown method'}

    def _get_recommendation(self, psi: float) -> str:
        """Get recommendation based on PSI value."""
        if psi < 0.1:
            return "No action needed - stable distribution"
        elif psi < 0.2:
            return "Monitor closely - moderate drift detected"
        else:
            return "Retrain model - significant drift detected"

    def batch_detect_drift(
        self,
        current_data: Dict[str, np.ndarray],
        method: str = "psi"
    ) -> Dict[str, Dict]:
        """Detect drift for multiple features."""
        results = {}
        for feature_name, data in current_data.items():
            results[feature_name] = self.detect_drift(data, feature_name, method)
        return results


class ModelMonitor:
    """
    Monitor deployed models for performance and drift.

    Tracks:
    - Prediction distributions
    - Feature drift
    - Accuracy degradation
    - Latency
    """

    def __init__(self):
        self.predictions_history: List[Dict] = []
        self.feature_history: Dict[str, List[Dict]] = {}
        self.alerts: List[Dict] = []
        self.drift_detector = DriftDetector()

    def log_prediction(
        self,
        model_name: str,
        prediction: float,
        features: Dict[str, float],
        actual: Optional[float] = None,
        latency_ms: Optional[float] = None
    ):
        """Log a single prediction."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'model_name': model_name,
            'prediction': float(prediction),
            'features': features,
            'actual': float(actual) if actual is not None else None,
            'latency_ms': float(latency_ms) if latency_ms is not None else None
        }

        self.predictions_history.append(entry)

        # Keep only last 10000 entries
        if len(self.predictions_history) > 10000:
            self.predictions_history = self.predictions_history[-5000:]

        # Log features separately for drift detection
        for feat_name, feat_value in features.items():
            if feat_name not in self.feature_history:
                self.feature_history[feat_name] = []
            self.feature_history[feat_name].append({
                'timestamp': datetime.now().isoformat(),
                'value': float(feat_value)
            })

    def check_drift(self, window_size: int = 1000) -> Dict:
        """Check for drift in recent predictions."""
        if len(self.predictions_history) < window_size:
            return {'status': 'insufficient_data'}

        recent = self.predictions_history[-window_size:]

        # Check prediction distribution
        predictions = np.array([p['prediction'] for p in recent])
        pred_mean = np.mean(predictions)
        pred_std = np.std(predictions)

        # Check for accuracy degradation if actuals available
        with_actuals = [p for p in recent if p['actual'] is not None]
        if len(with_actuals) >= 100:
            errors = np.array([
                p['prediction'] - p['actual'] for p in with_actuals[-100:]
            ])
            mae = np.mean(np.abs(errors))
            mse = np.mean(errors ** 2)

            alerts = []

            if mae > 1.5 * np.std(predictions):
                alerts.append({
                    'type': 'accuracy_degradation',
                    'severity': 'high',
                    'message': f"MAE ({mae:.2f}) significantly higher than expected"
                })

            return {
                'status': 'monitoring',
                'prediction_mean': float(pred_mean),
                'prediction_std': float(pred_std),
                'recent_mae': float(mae),
                'recent_mse': float(mse),
                'alerts': alerts
            }

        return {
            'status': 'monitoring',
            'prediction_mean': float(pred_mean),
            'prediction_std': float(pred_std)
        }

    def get_performance_summary(
        self,
        model_name: str,
        time_window_hours: int = 24
    ) -> Dict:
        """Get performance summary for a model over time window."""
        cutoff = datetime.now() - timedelta(hours=time_window_hours)

        recent = [
            p for p in self.predictions_history
            if p['model_name'] == model_name and
            datetime.fromisoformat(p['timestamp']) > cutoff
        ]

        if not recent:
            return {'status': 'no_data', 'model': model_name}

        predictions = [p['prediction'] for p in recent]
        latencies = [p['latency_ms'] for p in recent if p['latency_ms'] is not None]
        with_actuals = [p for p in recent if p['actual'] is not None]

        summary = {
            'model_name': model_name,
            'time_window_hours': time_window_hours,
            'total_predictions': len(recent),
            'predictions_per_minute': len(recent) / (time_window_hours * 60),
            'prediction_stats': {
                'mean': float(np.mean(predictions)),
                'std': float(np.std(predictions)),
                'min': float(np.min(predictions)),
                'max': float(np.max(predictions))
            }
        }

        if latencies:
            summary['latency_stats'] = {
                'mean_ms': float(np.mean(latencies)),
                'p50_ms': float(np.percentile(latencies, 50)),
                'p95_ms': float(np.percentile(latencies, 95)),
                'p99_ms': float(np.percentile(latencies, 99))
            }

        if with_actuals:
            errors = [p['prediction'] - p['actual'] for p in with_actuals]
            summary['accuracy'] = {
                'mae': float(np.mean(np.abs(errors))),
                'rmse': float(np.sqrt(np.mean(np.array(errors) ** 2))),
                'sample_size': len(with_actuals)
            }

        return summary

    def generate_alert(self, alert_type: str, severity: str, message: str):
        """Generate an alert."""
        alert = {
            'id': hashlib.md5(f"{alert_type}{datetime.now().isoformat()}".encode()).hexdigest()[:8],
            'type': alert_type,
            'severity': severity,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'acknowledged': False
        }
        self.alerts.append(alert)
        return alert


class RetrainingScheduler:
    """
    Schedule and trigger model retraining based on drift detection.
    """

    def __init__(
        self,
        monitor: ModelMonitor,
        tracker: ExperimentTracker
    ):
        self.monitor = monitor
        self.tracker = tracker
        self.retraining_config: Dict[str, Dict] = {}

    def should_retrain(
        self,
        model_name: str,
        drift_threshold: float = 0.2,
        min_predictions: int = 5000,
        cooldown_hours: int = 24
    ) -> Dict:
        """
        Determine if a model should be retrained.

        Args:
            model_name: Name of the model
            drift_threshold: PSI threshold for drift
            min_predictions: Minimum predictions before considering retrain
            cooldown_hours: Hours between retrain recommendations

        Returns:
            Dict with recommendation
        """
        summary = self.monitor.get_performance_summary(model_name)

        if summary.get('status') == 'no_data':
            return {'should_retrain': False, 'reason': 'Insufficient data'}

        total_preds = summary.get('total_predictions', 0)
        if total_preds < min_predictions:
            return {
                'should_retrain': False,
                'reason': f'Only {total_preds} predictions, need {min_predictions}'
            }

        # Check for drift alerts
        drift_check = self.monitor.check_drift()

        if drift_check.get('alerts'):
            for alert in drift_check['alerts']:
                if alert['type'] == 'accuracy_degradation':
                    return {
                        'should_retrain': True,
                        'reason': 'Significant accuracy degradation detected',
                        'severity': alert.get('severity', 'unknown'),
                        'details': alert
                    }

        return {'should_retrain': False, 'reason': 'Model performing within expected bounds'}

    def schedule_retraining(
        self,
        model_name: str,
        trigger: str,
        priority: str = "medium"
    ) -> Dict:
        """Schedule a retraining job."""
        job_id = hashlib.md5(
            f"{model_name}{trigger}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        job = {
            'id': job_id,
            'model_name': model_name,
            'trigger': trigger,
            'priority': priority,
            'status': 'scheduled',
            'scheduled_at': datetime.now().isoformat(),
            'started_at': None,
            'completed_at': None
        }

        self.retraining_config[job_id] = job

        return job
