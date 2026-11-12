"""Reproducibility audit: verify all experiment artifacts can be re-derived
from tracked metadata.

Per STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §6 fallback path:
"Reproducibility audit — verify all experiment artifacts can be re-derived
from tracked metadata"

This test reads experiments.jsonl and validates:
1. Every referenced artifact file exists on disk
2. SHA-256 hashes match the recorded values (16-char prefix)
3. No experiment references missing or corrupted artifacts
"""

import hashlib
import json
from pathlib import Path

import pytest

EXPERIMENTS_JSONL = Path(".experiments/experiments.jsonl")
ARTIFACTS_ROOT = Path(".experiments/artifacts")


def _compute_file_hash(filepath: Path, length: int = 16) -> str:
    """Compute SHA-256 hash of a file, return first `length` chars."""
    with open(filepath, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    return file_hash[:length]


def _load_experiments() -> list[dict]:
    """Load all experiment records from JSONL."""
    if not EXPERIMENTS_JSONL.exists():
        pytest.skip(f"Experiments log not found: {EXPERIMENTS_JSONL}")
    experiments = []
    with open(EXPERIMENTS_JSONL) as f:
        for line in f:
            line = line.strip()
            if line:
                experiments.append(json.loads(line))
    return experiments


class TestReproducibilityAudit:
    """Audit all experiment artifacts for reproducibility."""

    def test_experiments_log_exists_and_nonempty(self):
        """Experiments log must exist and contain records."""
        assert EXPERIMENTS_JSONL.exists(), f"Missing: {EXPERIMENTS_JSONL}"
        experiments = _load_experiments()
        assert len(experiments) > 0, "Experiments log is empty"

    def test_all_artifact_files_exist(self):
        """Every artifact referenced in experiments must exist on disk."""
        experiments = _load_experiments()
        missing_artifacts = []

        for exp in experiments:
            artifacts = exp.get("artifacts", {})
            for artifact_name, artifact_path_str in artifacts.items():
                artifact_path = Path(artifact_path_str)
                if not artifact_path.exists():
                    missing_artifacts.append(
                        {
                            "experiment_id": exp["metadata"]["experiment_id"],
                            "experiment_name": exp["metadata"]["name"],
                            "artifact_name": artifact_name,
                            "expected_path": artifact_path_str,
                        }
                    )

        if missing_artifacts:
            details = "\n".join(
                f"  Exp {m['experiment_id']} ({m['experiment_name']}): "
                f"{m['artifact_name']} -> {m['expected_path']}"
                for m in missing_artifacts[:20]
            )
            if len(missing_artifacts) > 20:
                details += f"\n  ... and {len(missing_artifacts) - 20} more"
            pytest.fail(f"Found {len(missing_artifacts)} missing artifact(s):\n{details}")

    def test_all_artifact_hashes_match(self):
        """Every artifact's SHA-256 hash must match the recorded prefix."""
        experiments = _load_experiments()
        hash_mismatches = []

        for exp in experiments:
            artifacts = exp.get("artifacts", {})
            for artifact_name, artifact_path_str in artifacts.items():
                artifact_path = Path(artifact_path_str)
                if not artifact_path.exists():
                    continue  # Already caught by existence test

                # Extract recorded hash from artifact name (format: name_hash)
                recorded_hash = artifact_name.split("_")[-1] if "_" in artifact_name else None
                if recorded_hash is None or len(recorded_hash) != 16:
                    # Skip artifacts that don't follow the naming convention
                    continue

                actual_hash = _compute_file_hash(artifact_path)
                if actual_hash != recorded_hash:
                    hash_mismatches.append(
                        {
                            "experiment_id": exp["metadata"]["experiment_id"],
                            "experiment_name": exp["metadata"]["name"],
                            "artifact_name": artifact_name,
                            "path": artifact_path_str,
                            "expected_hash": recorded_hash,
                            "actual_hash": actual_hash,
                        }
                    )

        if hash_mismatches:
            details = "\n".join(
                f"  Exp {m['experiment_id']} ({m['experiment_name']}): "
                f"{m['artifact_name']} expected {m['expected_hash']}, got {m['actual_hash']}"
                for m in hash_mismatches[:20]
            )
            if len(hash_mismatches) > 20:
                details += f"\n  ... and {len(hash_mismatches) - 20} more"
            pytest.fail(f"Found {len(hash_mismatches)} hash mismatch(es):\n{details}")

    def test_no_orphaned_artifacts_in_artifacts_dir(self):
        """Every file under .experiments/artifacts should be referenced by at least one experiment."""
        if not ARTIFACTS_ROOT.exists():
            pytest.skip(f"Artifacts directory not found: {ARTIFACTS_ROOT}")

        # Collect all referenced artifact paths
        experiments = _load_experiments()
        referenced_paths = set()
        for exp in experiments:
            for artifact_path_str in exp.get("artifacts", {}).values():
                referenced_paths.add(Path(artifact_path_str).resolve())

        # Walk artifacts directory
        orphaned = []
        for artifact_file in ARTIFACTS_ROOT.rglob("*"):
            if artifact_file.is_file() and not artifact_file.name.endswith(".meta.json"):
                resolved = artifact_file.resolve()
                if resolved not in referenced_paths:
                    orphaned.append(str(artifact_file))

        if orphaned:
            details = "\n".join(f"  {p}" for p in orphaned[:20])
            if len(orphaned) > 20:
                details += f"\n  ... and {len(orphaned) - 20} more"
            pytest.fail(
                f"Found {len(orphaned)} orphaned artifact file(s) not referenced by any experiment:\n{details}"
            )

    def test_experiment_metadata_completeness(self):
        """Every experiment must have required metadata fields."""
        experiments = _load_experiments()
        incomplete = []

        required_fields = [
            "experiment_id",
            "name",
            "timestamp",
            "git_commit",
            "git_dirty",
            "python_version",
            "dependencies",
            "random_seeds",
            "config",
            "data_sources",
            "compute_budget",
        ]

        for exp in experiments:
            metadata = exp.get("metadata", {})
            missing = [f for f in required_fields if f not in metadata]
            if missing:
                incomplete.append(
                    {
                        "experiment_id": metadata.get("experiment_id", "UNKNOWN"),
                        "missing_fields": missing,
                    }
                )

        if incomplete:
            details = "\n".join(
                f"  Exp {i['experiment_id']}: missing {i['missing_fields']}" for i in incomplete
            )
            pytest.fail(
                f"Found {len(incomplete)} experiment(s) with incomplete metadata:\n{details}"
            )

    def test_git_commit_consistency(self):
        """All experiments should reference valid git commits (not 'unknown')."""
        experiments = _load_experiments()
        unknown_commits = []

        for exp in experiments:
            commit = exp.get("metadata", {}).get("git_commit")
            if commit == "unknown":
                unknown_commits.append(exp["metadata"]["experiment_id"])

        if unknown_commits:
            details = "\n".join(f"  {eid}" for eid in unknown_commits[:20])
            if len(unknown_commits) > 20:
                details += f"\n  ... and {len(unknown_commits) - 20} more"
            pytest.fail(
                f"Found {len(unknown_commits)} experiment(s) with unknown git commit:\n{details}"
            )

    def test_artifact_meta_files_exist(self):
        """Every artifact should have a corresponding .meta.json file."""
        experiments = _load_experiments()
        missing_meta = []

        for exp in experiments:
            artifacts = exp.get("artifacts", {})
            for artifact_name, artifact_path_str in artifacts.items():
                artifact_path = Path(artifact_path_str)
                if not artifact_path.exists():
                    continue  # Already caught by existence test

                meta_path = artifact_path.with_suffix(artifact_path.suffix + ".meta.json")
                if not meta_path.exists():
                    # Check alternative naming: artifact_dir/name_hash.meta.json
                    meta_path_alt = artifact_path.parent / f"{artifact_name}.meta.json"
                    if not meta_path_alt.exists():
                        missing_meta.append(
                            {
                                "experiment_id": exp["metadata"]["experiment_id"],
                                "artifact_name": artifact_name,
                                "artifact_path": artifact_path_str,
                                "expected_meta": str(meta_path),
                            }
                        )

        if missing_meta:
            details = "\n".join(
                f"  Exp {m['experiment_id']}: {m['artifact_name']} -> missing {m['expected_meta']}"
                for m in missing_meta[:20]
            )
            if len(missing_meta) > 20:
                details += f"\n  ... and {len(missing_meta) - 20} more"
            pytest.fail(f"Found {len(missing_meta)} artifact(s) without .meta.json:\n{details}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
