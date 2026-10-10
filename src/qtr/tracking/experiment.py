"""
Experiment tracking and reproducibility framework.

Logs experiments to JSONL files with full reproducibility metadata.
"""

import json
import hashlib
import subprocess
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict, field
import pandas as pd
import numpy as np

from qtr.utils.config import get_config
from loguru import logger


@dataclass
class ExperimentMetadata:
    """Metadata for experiment reproducibility."""
    experiment_id: str
    name: str
    description: str
    timestamp: str
    git_commit: str
    git_dirty: bool
    python_version: str
    dependencies: Dict[str, str]
    random_seeds: Dict[str, int]
    config: Dict[str, Any]
    data_sources: Dict[str, Any]
    compute_budget: Dict[str, Any]


@dataclass
class ExperimentResult:
    """Container for experiment results."""
    metadata: ExperimentMetadata
    metrics: Dict[str, float]
    artifacts: Dict[str, str]  # artifact_name -> file_path
    status: str  # "completed", "failed", "running"
    error: Optional[str] = None


class ExperimentTracker:
    """
    Tracks experiments with full reproducibility metadata.

    Stores:
    - Experiment metadata (code version, data versions, seeds, config)
    - Metrics (JSON-serializable)
    - Artifact references (file paths with hashes)
    """

    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or Path(get_config().get("tracking.log_dir", ".experiments"))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_experiment: Optional[ExperimentMetadata] = None
        self.current_results: Dict[str, Any] = {}
        self.current_artifacts: Dict[str, str] = {}

    def start_experiment(
        self,
        name: str,
        description: str = "",
        config: Optional[Dict[str, Any]] = None,
        data_sources: Optional[Dict[str, Any]] = None,
        compute_budget: Optional[Dict[str, Any]] = None,
        random_seeds: Optional[Dict[str, int]] = None,
    ) -> str:
        """Start a new experiment and return experiment ID."""
        # Generate experiment ID
        timestamp = datetime.utcnow().isoformat() + "Z"
        exp_id = f"exp_{timestamp.replace(':', '-').replace('.', '-')}"

        # Get git info
        git_commit, git_dirty = self._get_git_info()

        # Get dependencies
        dependencies = self._get_dependencies()

        # Default seeds
        if random_seeds is None:
            random_seeds = {
                "numpy": 42,
                "python": 42,
            }

        metadata = ExperimentMetadata(
            experiment_id=exp_id,
            name=name,
            description=description,
            timestamp=timestamp,
            git_commit=git_commit,
            git_dirty=git_dirty,
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            dependencies=dependencies,
            random_seeds=random_seeds,
            config=config or {},
            data_sources=data_sources or {},
            compute_budget=compute_budget or {},
        )

        self.current_experiment = metadata
        self.current_results = {}
        self.current_artifacts = {}

        logger.info(f"Started experiment: {exp_id} ({name})")
        return exp_id

    def log_metric(self, name: str, value: float, step: Optional[int] = None) -> None:
        """Log a single metric."""
        if self.current_experiment is None:
            raise RuntimeError("No active experiment. Call start_experiment() first.")

        key = f"{name}" + (f"_step{step}" if step is not None else "")
        self.current_results[key] = value

    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None) -> None:
        """Log multiple metrics at once."""
        for name, value in metrics.items():
            self.log_metric(name, value, step)

    def log_artifact(self, name: str, file_path: Path, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Log an artifact file, return its hash."""
        if self.current_experiment is None:
            raise RuntimeError("No active experiment. Call start_experiment() first.")

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Artifact not found: {file_path}")

        # Compute hash
        with open(file_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()[:16]

        # Store with hash in name for deduplication
        artifact_name = f"{name}_{file_hash}"
        self.current_artifacts[artifact_name] = str(file_path)

        # Save metadata if provided
        if metadata:
            meta_path = self.log_dir / f"{artifact_name}.meta.json"
            with open(meta_path, "w") as f:
                json.dump(metadata, f, indent=2)

        logger.debug(f"Logged artifact: {artifact_name}")
        return file_hash

    def log_dataframe(self, name: str, df: pd.DataFrame, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Log a DataFrame as parquet artifact."""
        artifact_dir = self.log_dir / "artifacts" / self.current_experiment.experiment_id
        artifact_dir.mkdir(parents=True, exist_ok=True)

        file_path = artifact_dir / f"{name}.parquet"
        df.to_parquet(file_path)

        meta = metadata or {}
        meta.update({
            "shape": df.shape,
            "columns": df.columns.tolist(),
            "dtypes": {str(k): str(v) for k, v in df.dtypes.to_dict().items()},
            "index_type": str(df.index.dtype),
        })

        return self.log_artifact(name, file_path, meta)

    def finish_experiment(self, status: str = "completed", error: Optional[str] = None) -> ExperimentResult:
        """Finish the current experiment and persist results."""
        if self.current_experiment is None:
            raise RuntimeError("No active experiment.")

        result = ExperimentResult(
            metadata=self.current_experiment,
            metrics=self.current_results,
            artifacts=self.current_artifacts,
            status=status,
            error=error,
        )

        # Save experiment record
        self._save_experiment(result)

        logger.info(f"Finished experiment: {self.current_experiment.experiment_id} ({status})")
        self.current_experiment = None
        return result

    def _save_experiment(self, result: ExperimentResult) -> None:
        """Save experiment to JSONL log."""
        log_file = self.log_dir / "experiments.jsonl"

        record = {
            "metadata": asdict(result.metadata),
            "metrics": result.metrics,
            "artifacts": result.artifacts,
            "status": result.status,
            "error": result.error,
        }

        with open(log_file, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def _get_git_info(self) -> Tuple[str, bool]:
        """Get current git commit and dirty status."""
        try:
            commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
            ).decode().strip()
            dirty = subprocess.call(
                ["git", "diff", "--quiet"], stderr=subprocess.DEVNULL
            ) != 0
            return commit, dirty
        except Exception:
            return "unknown", False

    def _get_dependencies(self) -> Dict[str, str]:
        """Get installed package versions."""
        try:
            import pkg_resources
            return {d.key: d.version for d in pkg_resources.working_set}
        except Exception:
            return {}

    def load_experiment(self, experiment_id: str) -> Optional[ExperimentResult]:
        """Load a previous experiment by ID."""
        log_file = self.log_dir / "experiments.jsonl"
        if not log_file.exists():
            return None

        with open(log_file) as f:
            for line in f:
                record = json.loads(line)
                if record["metadata"]["experiment_id"] == experiment_id:
                    return ExperimentResult(
                        metadata=ExperimentMetadata(**record["metadata"]),
                        metrics=record["metrics"],
                        artifacts=record["artifacts"],
                        status=record["status"],
                        error=record.get("error"),
                    )
        return None

    def list_experiments(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List recent experiments."""
        log_file = self.log_dir / "experiments.jsonl"
        if not log_file.exists():
            return []

        experiments = []
        with open(log_file) as f:
            for line in f:
                record = json.loads(line)
                meta = record["metadata"]
                experiments.append({
                    "experiment_id": meta["experiment_id"],
                    "name": meta["name"],
                    "timestamp": meta["timestamp"],
                    "status": record["status"],
                    "metrics": record["metrics"],
                })

        return sorted(experiments, key=lambda x: x["timestamp"], reverse=True)[:limit]


def get_tracker() -> ExperimentTracker:
    """Singleton experiment tracker."""
    if not hasattr(get_tracker, "_instance"):
        get_tracker._instance = ExperimentTracker()
    return get_tracker._instance