"""Reproducibility audit: verify experiment artifacts can be re-derived
from tracked metadata.

Per STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §6 fallback path:
"Reproducibility audit — verify all experiment artifacts can be re-derived
from tracked metadata"

The audit reads ``.experiments/experiments.jsonl`` and checks:

1. Every referenced artifact file exists on disk
2. SHA-256 hashes match the recorded values (16-char prefix)
3. Every file under ``.experiments/artifacts`` is referenced by an experiment
4. Every existing artifact has a ``.meta.json`` sidecar
5. Experiment metadata is complete
6. Every experiment references a real git commit

The committed corpus predates the current tracking contract, so it carries a
known historical backlog (missing files, hash drift, orphaned files, missing
sidecars). That backlog is recorded in ``REPRODUCIBILITY_BASELINE`` below.
Each backlog check asserts the current count *equals* the recorded baseline:
the backlog can neither grow (regression) nor silently shrink (stale baseline)
without a deliberate, reviewable update. This mirrors
``tests/test_experiment_artifact_schema.py``'s
``test_incomplete_runs_match_audit_inventory``.

The desired end state is a zero backlog; see REPRODUCIBILITY_AUDIT_REPORT.md
for the remediation plan.
"""

import hashlib
import json
from pathlib import Path

import pytest

EXPERIMENTS_JSONL = Path(".experiments/experiments.jsonl")
EXPERIMENTS_ROOT = Path(".experiments")
ARTIFACTS_ROOT = Path(".experiments/artifacts")

# Snapshot of the historical reproducibility backlog when this gate was
# introduced. Update deliberately (together with REPRODUCIBILITY_AUDIT_REPORT.md)
# when artifacts are remediated or when a new run legitimately adds artifacts.
#
# 2026-11-12 remediation: 149 non-H28 hash-exact artifacts were restored into
# place, so ``missing_files`` fell 346 -> 197. The remaining 172 H28 rows are
# hash-exact but must stay at their depth-one paths un-restored (restoring them
# would violate the H28 depth-one invariant in
# tests/test_h28_causal_recertification.py), and 25 have no hash-matching source.
# Sidecar count is unchanged at 0 after the 2026-11-13 backfill: all 140
# historically missing ``.meta.json`` sidecars were derived additively
# (JSON -> top-level keys; parquet -> shape/columns/dtypes/index_type) and no
# existing sidecar was overwritten. See REPRODUCIBILITY_AUDIT_REPORT.md §4.
REPRODUCIBILITY_BASELINE = {
    "missing_files": 197,
    "hash_mismatches": 11,
    "orphaned_files": 528,
    "missing_meta_files": 0,
}


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


def _assert_backlog_matches_baseline(check: str, count: int, details: str) -> None:
    """Assert a historical backlog count equals its recorded baseline.

    A changed count is a deliberate signal: either a remediation (lower the
    baseline) or a regression (fix the drift, do not raise the baseline).
    """
    expected = REPRODUCIBILITY_BASELINE[check]
    assert count == expected, (
        f"{check} backlog changed: {count} (recorded baseline {expected}).\n"
        f"{details}\n"
        "If this is a remediation, lower the baseline in "
        "tests/test_reproducibility_audit.py and update "
        "REPRODUCIBILITY_AUDIT_REPORT.md. If it is a regression, fix the "
        "artifact drift instead of raising the baseline."
    )


class TestReproducibilityAudit:
    """Audit all experiment artifacts for reproducibility."""

    def test_experiments_log_exists_and_nonempty(self):
        """Experiments log must exist and contain records."""
        assert EXPERIMENTS_JSONL.exists(), f"Missing: {EXPERIMENTS_JSONL}"
        experiments = _load_experiments()
        assert len(experiments) > 0, "Experiments log is empty"

    def test_artifact_files_match_recorded_backlog(self):
        """Missing referenced artifacts must equal the recorded backlog."""
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

        details = "\n".join(
            f"  Exp {m['experiment_id']} ({m['experiment_name']}): "
            f"{m['artifact_name']} -> {m['expected_path']}"
            for m in missing_artifacts[:20]
        )
        if len(missing_artifacts) > 20:
            details += f"\n  ... and {len(missing_artifacts) - 20} more"
        _assert_backlog_matches_baseline("missing_files", len(missing_artifacts), details)

    def test_artifact_hashes_match_recorded_backlog(self):
        """Artifact hash drift must equal the recorded backlog."""
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

        details = "\n".join(
            f"  Exp {m['experiment_id']} ({m['experiment_name']}): "
            f"{m['artifact_name']} expected {m['expected_hash']}, got {m['actual_hash']}"
            for m in hash_mismatches[:20]
        )
        if len(hash_mismatches) > 20:
            details += f"\n  ... and {len(hash_mismatches) - 20} more"
        _assert_backlog_matches_baseline("hash_mismatches", len(hash_mismatches), details)

    def test_orphaned_artifacts_match_recorded_backlog(self):
        """Unreferenced artifact files must equal the recorded backlog."""
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

        details = "\n".join(f"  {p}" for p in orphaned[:20])
        if len(orphaned) > 20:
            details += f"\n  ... and {len(orphaned) - 20} more"
        _assert_backlog_matches_baseline("orphaned_files", len(orphaned), details)

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

    def test_artifact_meta_files_match_recorded_backlog(self):
        """Missing artifact metadata sidecars must equal the recorded backlog.

        ``ExperimentTracker.log_artifact`` writes sidecars to
        ``<log_dir>/<artifact_name>.meta.json`` (default ``.experiments``).
        Artifacts logged without a metadata dict intentionally have no sidecar.
        """
        experiments = _load_experiments()
        missing_meta = []

        for exp in experiments:
            artifacts = exp.get("artifacts", {})
            for artifact_name, artifact_path_str in artifacts.items():
                artifact_path = Path(artifact_path_str)
                if not artifact_path.exists():
                    continue  # Already caught by existence test

                meta_path = EXPERIMENTS_ROOT / f"{artifact_name}.meta.json"
                if not meta_path.exists():
                    missing_meta.append(
                        {
                            "experiment_id": exp["metadata"]["experiment_id"],
                            "artifact_name": artifact_name,
                            "artifact_path": artifact_path_str,
                            "expected_meta": str(meta_path),
                        }
                    )

        details = "\n".join(
            f"  Exp {m['experiment_id']}: {m['artifact_name']} -> missing {m['expected_meta']}"
            for m in missing_meta[:20]
        )
        if len(missing_meta) > 20:
            details += f"\n  ... and {len(missing_meta) - 20} more"
        _assert_backlog_matches_baseline("missing_meta_files", len(missing_meta), details)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
