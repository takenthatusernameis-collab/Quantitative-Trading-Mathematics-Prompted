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
import re
from pathlib import Path

import pytest

EXPERIMENTS_JSONL = Path(".experiments/experiments.jsonl")
EXPERIMENTS_ROOT = Path(".experiments")
ARTIFACTS_ROOT = Path(".experiments/artifacts")
AUDIT_REPORT = Path("REPRODUCIBILITY_AUDIT_REPORT.md")

# Snapshot of the historical reproducibility backlog when this gate was
# introduced. Update deliberately (together with REPRODUCIBILITY_AUDIT_REPORT.md)
# when artifacts are remediated or when a new run legitimately adds artifacts.
#
# 2026-11-12 remediation: 149 non-H28 hash-exact artifacts were restored into
# place, so ``missing_files`` fell 346 -> 197.
# 2026-11-19 remediation (applied in commit 1a7c83a):
# the 172 H28 rows were not missing files at all -- ``experiments.jsonl`` recorded
# obsolete depth-one paths while the artifacts live under
# ``.experiments/artifacts/h28_causal_recertification/runs/<exp_id>/``. The log's
# recorded paths were corrected to the real location (each replacement verified
# hash-exact), so ``missing_files`` fell 197 -> 25 (all now unrecoverable) and
# ``orphaned_files`` fell 528 -> 356 (the once-orphaned H28 files are referenced).
# The remaining 25 have no hash-matching source anywhere in the artifact store.
# Sidecar count is unchanged at 0 after the 2026-11-13 backfill: all 140
# historically missing ``.meta.json`` sidecars were derived additively
# (JSON -> top-level keys; parquet -> shape/columns/dtypes/index_type) and no
# existing sidecar was overwritten. The 2026-11-19 path correction made 8 H28
# summary files newly reachable; their sidecars were derived the same additive
# way, so ``missing_meta_files`` stays 0. See REPRODUCIBILITY_AUDIT_REPORT.md §4.
REPRODUCIBILITY_BASELINE = {
    "missing_files": 25,
    "hash_mismatches": 11,
    "orphaned_files": 356,
    "missing_meta_files": 0,
}

# Pinned identity of the 11 hash_mismatches (2026-11-19, Cycle 217).
# Each entry: (experiment_id, experiment_name, artifact_name, expected_hash, actual_hash).
# This list prevents a fixed row from being silently replaced by a new mismatch.
# Do not modify artifacts; only update this list if a deliberate remediation occurs
# (and update REPRODUCIBILITY_AUDIT_REPORT.md together with it).
PINNED_HASH_MISMATCHES = [
    (
        "exp_2026-10-10T20-56-30-507309Z",
        "ts_momentum_20etf_v1",
        "param_grid_results_3c3ca96bf45b5f28",
        "3c3ca96bf45b5f28",
        "2cfbb88200656d0d",
    ),
    (
        "exp_2026-10-10T20-57-26-136503Z",
        "ts_momentum_20etf_v1",
        "param_grid_results_3c3ca96bf45b5f28",
        "3c3ca96bf45b5f28",
        "2cfbb88200656d0d",
    ),
    (
        "exp_2026-10-10T20-59-28-306148Z",
        "cs_momentum_10etf_v1",
        "param_grid_results_3c5c66cd85442477",
        "3c5c66cd85442477",
        "c7a1cedb8a4fc5b1",
    ),
    (
        "exp_2026-10-10T21-08-54-188263Z",
        "ts_momentum_20etf_v1",
        "param_grid_results_3c3ca96bf45b5f28",
        "3c3ca96bf45b5f28",
        "2cfbb88200656d0d",
    ),
    (
        "exp_2026-10-10T21-09-06-830199Z",
        "cs_momentum_10etf_v1",
        "param_grid_results_3c5c66cd85442477",
        "3c5c66cd85442477",
        "c7a1cedb8a4fc5b1",
    ),
    (
        "exp_2026-10-10T21-27-13-928282Z",
        "regime_gated_momentum_20etf_v1",
        "param_grid_results_5aa48f8683d54d37",
        "5aa48f8683d54d37",
        "b7dddfb0dc0c524d",
    ),
    (
        "exp_2026-10-10T21-28-20-920399Z",
        "regime_gated_momentum_20etf_v1",
        "param_grid_results_5aa48f8683d54d37",
        "5aa48f8683d54d37",
        "b7dddfb0dc0c524d",
    ),
    (
        "exp_2026-10-14T08-26-18-385545Z",
        "ts_momentum_20etf_v1",
        "param_grid_results_3c3ca96bf45b5f28",
        "3c3ca96bf45b5f28",
        "2cfbb88200656d0d",
    ),
    (
        "exp_2026-11-05T18-20-38-363385Z",
        "nf_20261105_14_credit_regime",
        "summary_b8cf0dae88579c7a",
        "b8cf0dae88579c7a",
        "63139e710dc45c09",
    ),
    (
        "exp_2026-11-05T19-06-45-864432Z",
        "nf_20261105_16_usd_macro",
        "summary_361a5942ebe194a6",
        "361a5942ebe194a6",
        "7ec56dd201670d5a",
    ),
    (
        "exp_2026-11-06T01-28-49-517869Z",
        "nf_20261105_19_pead",
        "summary_4eff6682192c3e69",
        "4eff6682192c3e69",
        "da9da6784d5a7d8d",
    ),
]

# Pinned identity digests for the two count-only backlogs (2026-11-19, Cycle 223).
# A bare count cannot distinguish "still 25 stale rows" from "one row fixed and a
# different row regressed". These SHA-256 digests pin the exact row set:
#   missing  -> sorted "<experiment_id>|<experiment_name>|<artifact_name>|<path>" lines
#   orphaned -> sorted artifact paths (relative, POSIX)
# Update deliberately (together with REPRODUCIBILITY_AUDIT_REPORT.md) only after a
# remediation or a reviewed corpus change, exactly like PINNED_HASH_MISMATCHES.
PINNED_MISSING_FILES_DIGEST = "a50244430ef816f0a00733d82e3f140a92a9bbb29d9f6ee4157c819a2accaaff"
PINNED_ORPHANED_FILES_DIGEST = "c6611f77e80f5bf80ce351d444a7b35e5a7b72427867da16225a99a3f1143c50"

assert len(PINNED_HASH_MISMATCHES) == REPRODUCIBILITY_BASELINE["hash_mismatches"]

# Findings-table label -> baseline key. ``test_audit_report_findings_table_matches_pinned_baseline``
# parses the human-visible status table in REPRODUCIBILITY_AUDIT_REPORT.md and asserts its
# counts equal REPRODUCIBILITY_BASELINE, so prose can no longer drift from the gate
# (Cycles 222-225 repeatedly left stale counts in the report and handoffs).
REPORT_ROW_LABELS = {
    "Artifact files exist on disk": "missing_files",
    "Artifact hashes match recorded values": "hash_mismatches",
    "No orphaned files in artifacts dir": "orphaned_files",
    "Artifact `.meta.json` sidecars exist": "missing_meta_files",
}


def _report_status_row_counts(text: str) -> dict[str, int]:
    """Extract baseline counts from the audit report's Findings status table."""
    counts: dict[str, int] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 3 or cells[0] not in REPORT_ROW_LABELS:
            continue
        match = re.search(r"\d+", cells[2])
        if match:
            counts[REPORT_ROW_LABELS[cells[0]]] = int(match.group())
    return counts


def _digest_lines(lines: list[str]) -> str:
    """SHA-256 digest over sorted, newline-joined identity lines."""
    return hashlib.sha256("\n".join(sorted(lines)).encode()).hexdigest()


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

    def test_backlog_identity_digests_are_not_vacuous(self):
        """The identity digests must discriminate substituted and removed rows.

        Guards against the pinned digest silently becoming a constant that any
        backlog composition satisfies.
        """
        base = ["exp_a|name_a|art_a|.experiments/artifacts/exp_a/art.parquet"]
        substituted = ["exp_a|name_a|art_a|.experiments/artifacts/exp_a/other.parquet"]
        assert _digest_lines(base) != _digest_lines(substituted)
        assert _digest_lines(base) != _digest_lines(base + substituted)
        assert _digest_lines(base) != _digest_lines([])
        assert PINNED_MISSING_FILES_DIGEST != PINNED_ORPHANED_FILES_DIGEST

    def test_audit_report_findings_table_matches_pinned_baseline(self):
        """REPRODUCIBILITY_AUDIT_REPORT.md must state the live pinned backlog.

        The report is the durable human record; the baseline in this module is the
        executable one. This keeps them in lockstep: editing either without the
        other fails here.
        """
        assert AUDIT_REPORT.exists(), f"Missing: {AUDIT_REPORT}"
        text = AUDIT_REPORT.read_text(encoding="utf-8")

        counted = _report_status_row_counts(text)
        missing_labels = sorted(set(REPORT_ROW_LABELS.values()) - set(counted))
        assert not missing_labels, (
            "Could not parse the Findings status rows for: "
            f"{missing_labels}. Keep the report's Findings table labels intact."
        )
        assert counted == REPRODUCIBILITY_BASELINE, (
            "REPRODUCIBILITY_AUDIT_REPORT.md status table disagrees with "
            f"REPRODUCIBILITY_BASELINE: report={counted}, baseline="
            f"{REPRODUCIBILITY_BASELINE}. Update both together."
        )

        # The identity pins that the count cannot express must be quoted verbatim.
        for digest in (PINNED_MISSING_FILES_DIGEST, PINNED_ORPHANED_FILES_DIGEST):
            assert digest in text, (
                "REPRODUCIBILITY_AUDIT_REPORT.md is missing a live identity digest: "
                f"{digest}. Update the report when a digest is re-pinned."
            )

    def test_audit_report_count_parser_is_not_vacuous(self):
        """A drifted count in the report must be detectable, not silently ignored."""
        parsed = _report_status_row_counts(
            "| Artifact files exist on disk | ⚠ BASELINE | 26 missing | extra |\n"
            "| No orphaned files in artifacts dir | ⚠ BASELINE | 3 orphaned | scale |\n"
            "| unrelated | row | 999 |\n"
        )
        assert parsed == {"missing_files": 26, "orphaned_files": 3}
        assert parsed != REPRODUCIBILITY_BASELINE

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

        # Verify exact identity matches the pinned digest (order-insensitive)
        identity_lines = [
            "|".join(
                (
                    m["experiment_id"],
                    m["experiment_name"],
                    m["artifact_name"],
                    Path(m["expected_path"]).as_posix(),
                )
            )
            for m in missing_artifacts
        ]
        assert _digest_lines(identity_lines) == PINNED_MISSING_FILES_DIGEST, (
            "Missing-artifact identity changed: a pinned row was fixed or a new row went missing.\n"
            f"Expected digest: {PINNED_MISSING_FILES_DIGEST}\n"
            f"Actual digest:   {_digest_lines(identity_lines)}\n"
            "If this is a deliberate remediation, update PINNED_MISSING_FILES_DIGEST and "
            "REPRODUCIBILITY_BASELINE['missing_files'] together with "
            "REPRODUCIBILITY_AUDIT_REPORT.md."
        )

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

        # Verify count matches baseline
        details = "\n".join(
            f"  Exp {m['experiment_id']} ({m['experiment_name']}): "
            f"{m['artifact_name']} expected {m['expected_hash']}, got {m['actual_hash']}"
            for m in hash_mismatches[:20]
        )
        if len(hash_mismatches) > 20:
            details += f"\n  ... and {len(hash_mismatches) - 20} more"
        _assert_backlog_matches_baseline("hash_mismatches", len(hash_mismatches), details)

        # Verify exact identity matches pinned list (order-insensitive)
        actual_tuples = {
            (
                m["experiment_id"],
                m["experiment_name"],
                m["artifact_name"],
                m["expected_hash"],
                m["actual_hash"],
            )
            for m in hash_mismatches
        }
        expected_tuples = set(PINNED_HASH_MISMATCHES)
        assert actual_tuples == expected_tuples, (
            "Hash mismatch identity changed: a pinned row was fixed or a new mismatch appeared.\n"
            f"Expected: {sorted(expected_tuples)}\n"
            f"Actual:   {sorted(actual_tuples)}\n"
            "If this is a deliberate remediation, update PINNED_HASH_MISMATCHES and "
            "REPRODUCIBILITY_BASELINE['hash_mismatches'] together with "
            "REPRODUCIBILITY_AUDIT_REPORT.md."
        )

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

        # Verify exact identity matches the pinned digest (order-insensitive)
        identity_lines = [Path(p).as_posix() for p in orphaned]
        assert _digest_lines(identity_lines) == PINNED_ORPHANED_FILES_DIGEST, (
            "Orphaned-artifact identity changed: a pinned row was removed or a new orphan appeared.\n"
            f"Expected digest: {PINNED_ORPHANED_FILES_DIGEST}\n"
            f"Actual digest:   {_digest_lines(identity_lines)}\n"
            "If this is a deliberate catalog change, update PINNED_ORPHANED_FILES_DIGEST and "
            "REPRODUCIBILITY_BASELINE['orphaned_files'] together with "
            "REPRODUCIBILITY_AUDIT_REPORT.md."
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
