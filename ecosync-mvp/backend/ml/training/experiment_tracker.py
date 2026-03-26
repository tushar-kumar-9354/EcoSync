"""
ML Training Pipeline Infrastructure

Provides:
- Experiment tracking (similar to MLflow)
- Data versioning (similar to DVC)
- Drift detection for model monitoring
- Model registry and retraining orchestration
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json
import hashlib


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
        self.storage_path = storage_path
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
        """Log a single training run."""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")

        run_id = hashlib.md5(f"{experiment_id}{datetime.now().isoformat()}".encode()).hexdigest()[:12]

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
        self.experiments[experiment_id]['runs'].append(run_id)

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
                start = datetime.fromisoformat(run['created_at'])
                end = datetime.fromisoformat(run['completed_at'])
                run['duration_seconds'] = (end - start).total_seconds()
                break

    def get_experiment(self, experiment_id: str) -> Dict:
        """Get experiment details."""
        exp = self.experiments.get(experiment_id, {})
        if exp:
            runs = self.runs.get(experiment_id, [])
            exp['run_count'] = len(runs)
            exp['completed_runs'] = len([r for r in runs if r['status'] == 'completed'])
        return exp

    def save(self):
        """Save experiments to disk."""
        data = {'experiments': self.experiments, 'runs': self.runs}
        with open(f'{self.storage_path}/experiments.json', 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def load(self):
        """Load experiments from disk."""
        path = f'{self.storage_path}/experiments.json'
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                self.experiments = data.get('experiments', {})
                self.runs = data.get('runs', {})
        except FileNotFoundError:
            pass
