"""Lock the artifact restoration plan's row counts.

The planner in ``scripts/plan_artifact_restoration.py`` is read-only: it
emits a plan of which missing artifacts can be restored hash-exactly from a
same-basename candidate elsewhere in ``.experiments/artifacts``.  This test
pins the committed corpus's current recoverable / unrecoverable split so a
future drift (a new missing artifact, a corrupted candidate, a renamed
source) is caught by CI rather than silently changing the remediation scope.

The counts are a baseline ratchet, not a zero assertion: the corpus carries
a historical backlog (see ``REPRODUCIBILITY_AUDIT_REPORT.md``) and lowering
the counts requires a deliberate, authorized remediation plus a report
update, exactly like ``REPRODUCIBILITY_BASELINE`` in
``tests/test_reproducibility_audit.py``.
"""

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PLANNER = ROOT / "scripts" / "plan_artifact_restoration.py"

# Baseline computed from the committed corpus at the time this gate was
# introduced. 346 missing referenced artifacts; 321 have a same-basename
# candidate whose SHA-256 16-char prefix matches the recorded hash; 25 do not.
RECOVERABLE_BASELINE = 321
UNRECOVERABLE_BASELINE = 25


def _load_planner_module():
    spec = importlib.util.spec_from_file_location("plan_artifact_restoration", PLANNER)
    assert spec is not None and spec.loader is not None, f"cannot load {PLANNER}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_plan_row_counts_match_recorded_baseline():
    planner = _load_planner_module()
    experiments = planner._load_experiments()
    candidate_index = planner._build_candidate_index()
    recoverable, unrecoverable = planner.build_plan(experiments, candidate_index)

    assert len(recoverable) == RECOVERABLE_BASELINE, (
        f"recoverable rows changed: {len(recoverable)} "
        f"(recorded baseline {RECOVERABLE_BASELINE}).\n"
        "If this is an authorized remediation, lower the baseline here and in "
        "REPRODUCIBILITY_RESTORATION_PLAN.md. If it is drift, fix the artifact "
        "store instead of raising the baseline."
    )
    assert len(unrecoverable) == UNRECOVERABLE_BASELINE, (
        f"unrecoverable rows changed: {len(unrecoverable)} "
        f"(recorded baseline {UNRECOVERABLE_BASELINE}).\n"
        "A decrease means a previously-unrecoverable artifact became recoverable "
        "(verify the source hash); an increase means a new gap appeared."
    )


def test_every_recoverable_row_is_hash_verified():
    planner = _load_planner_module()
    experiments = planner._load_experiments()
    candidate_index = planner._build_candidate_index()
    recoverable, _ = planner.build_plan(experiments, candidate_index)

    for row in recoverable:
        assert row["source_path"], f"recoverable row has no source: {row}"
        assert row["source_hash"] == row["recorded_hash"], (
            f"hash mismatch in plan row for {row['artifact_name']}: "
            f"recorded {row['recorded_hash']} != source {row['source_hash']}"
        )
        # The source must actually exist on disk (paths are repo-relative).
        source = Path(row["source_path"])
        if not source.is_absolute():
            source = ROOT / source
        assert source.exists(), f"planned source missing on disk: {row['source_path']}"


def test_no_recoverable_row_targets_an_existing_path():
    """A planned restore must not overwrite an already-present artifact."""
    planner = _load_planner_module()
    experiments = planner._load_experiments()
    candidate_index = planner._build_candidate_index()
    recoverable, _ = planner.build_plan(experiments, candidate_index)

    for row in recoverable:
        assert not Path(row["expected_path"]).exists(), (
            f"planned target already exists: {row['expected_path']}"
        )


def test_planner_module_is_importable_and_deterministic():
    """build_plan is deterministic across repeated invocations."""
    planner = _load_planner_module()
    experiments = planner._load_experiments()
    candidate_index = planner._build_candidate_index()

    first = planner.build_plan(experiments, candidate_index)
    second = planner.build_plan(experiments, candidate_index)

    assert first == second, "build_plan is not deterministic"


def _row(root: Path, *, rel_source: str, rel_target: str, recorded_hash: str) -> dict:
    """Build a synthetic plan row with repo-relative paths under ``root``."""
    return {
        "artifact_name": f"x_{recorded_hash}",
        "recorded_hash": recorded_hash,
        "source_path": rel_source,
        "expected_path": rel_target,
    }


def _write_source(root: Path, rel: str, content: bytes) -> str:
    src = root / rel
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(content)
    return hashlib.sha256(content).hexdigest()[:16]


def test_apply_plan_copies_hash_exact_rows(tmp_path):
    """--apply copies a hash-exact row to its expected path, byte-for-byte."""
    planner = _load_planner_module()
    content = b"parquet-bytes\x00\x01\x02"
    recorded = _write_source(tmp_path, "artifacts/src/x.parquet", content)
    row = _row(
        tmp_path,
        rel_source="artifacts/src/x.parquet",
        rel_target="artifacts/exp/x.parquet",
        recorded_hash=recorded,
    )

    applied = planner.apply_plan([row], root=tmp_path)

    target = tmp_path / "artifacts/exp/x.parquet"
    assert target.exists()
    assert target.read_bytes() == content
    assert len(applied) == 1
    assert applied[0]["target"] == str(target)


def test_apply_plan_dry_run_writes_nothing(tmp_path):
    """--apply --dry-run reports the plan but creates no files."""
    planner = _load_planner_module()
    recorded = _write_source(tmp_path, "artifacts/src/x.parquet", b"payload")
    row = _row(
        tmp_path,
        rel_source="artifacts/src/x.parquet",
        rel_target="artifacts/exp/x.parquet",
        recorded_hash=recorded,
    )

    applied = planner.apply_plan([row], dry_run=True, root=tmp_path)

    assert not (tmp_path / "artifacts/exp/x.parquet").exists()
    assert len(applied) == 1


def test_apply_plan_refuses_to_overwrite_existing_target(tmp_path):
    """A target that already exists is never overwritten."""
    planner = _load_planner_module()
    recorded = _write_source(tmp_path, "artifacts/src/x.parquet", b"payload")
    target = tmp_path / "artifacts/exp/x.parquet"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"existing")
    row = _row(
        tmp_path,
        rel_source="artifacts/src/x.parquet",
        rel_target="artifacts/exp/x.parquet",
        recorded_hash=recorded,
    )

    with pytest.raises(AssertionError):
        planner.apply_plan([row], root=tmp_path)

    assert target.read_bytes() == b"existing"


def test_apply_plan_refuses_when_source_hash_drifted(tmp_path):
    """A source whose hash no longer matches the recorded hash is refused."""
    planner = _load_planner_module()
    _write_source(tmp_path, "artifacts/src/x.parquet", b"payload")
    row = _row(
        tmp_path,
        rel_source="artifacts/src/x.parquet",
        rel_target="artifacts/exp/x.parquet",
        recorded_hash="deadbeefdeadbeef",
    )

    with pytest.raises(AssertionError):
        planner.apply_plan([row], root=tmp_path)

    assert not (tmp_path / "artifacts/exp/x.parquet").exists()
