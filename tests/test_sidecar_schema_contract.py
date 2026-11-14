"""Contract: every committed ``.meta.json`` sidecar must describe its artifact.

The 2026-11-13 sidecar backfill derived parquet schema fields
(``shape``/``columns``/``dtypes``/``index_type``) and JSON top-level ``keys``
by reading each artifact. A subset recorded a datetime resolution that
disagreed with the resolution actually stored on disk (a pandas/pyarrow
version artifact), so the sidecar could not be used to re-derive the artifact.
This guard re-derives every hash-exact sidecar from its artifact and fails on
disagreement, encoding the invariant in CI rather than in a doc.

Hash-exact artifacts only: the 11 superseded hash-mismatch rows carry a stale
recorded hash by design (see ``REPRODUCIBILITY_AUDIT_REPORT.md`` §2) and are
skipped here — their on-disk file is authoritative.

Read-only: does not modify ``src/qtr``, frozen-contract tests, artifacts, or
sidecars.
"""

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

EXPERIMENTS_JSONL = Path(".experiments/experiments.jsonl")
EXPERIMENTS_ROOT = Path(".experiments")


def _file_hash(filepath: Path, length: int = 16) -> str:
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:length]


def _parquet_schema(path: Path) -> dict:
    df = pd.read_parquet(path)
    return {
        "shape": list(df.shape),
        "columns": df.columns.tolist(),
        "dtypes": {str(k): str(v) for k, v in df.dtypes.to_dict().items()},
        "index_type": str(df.index.dtype),
    }


def _json_keys(path: Path) -> dict:
    with open(path) as f:
        return {"keys": list(json.load(f).keys())}


def _load_hash_exact_pairs():
    """Yield (artifact_name, artifact_path, meta_path) for hash-exact artifacts."""
    if not EXPERIMENTS_JSONL.exists():
        return
    with open(EXPERIMENTS_JSONL) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            exp = json.loads(line)
            for artifact_name, artifact_path_str in exp.get("artifacts", {}).items():
                artifact_path = Path(artifact_path_str)
                if not artifact_path.exists():
                    continue
                recorded_hash = artifact_name.split("_")[-1] if "_" in artifact_name else None
                if recorded_hash is None or len(recorded_hash) != 16:
                    continue
                if _file_hash(artifact_path) != recorded_hash:
                    continue  # superseded/stale row; on-disk file is authoritative
                meta_path = EXPERIMENTS_ROOT / f"{artifact_name}.meta.json"
                if meta_path.exists():
                    yield artifact_name, artifact_path, meta_path


PAIRS = list(_load_hash_exact_pairs())


def test_every_hash_exact_artifact_has_a_matching_sidecar():
    """Every hash-exact artifact's sidecar must re-derive from the artifact."""
    mismatches = []
    for artifact_name, artifact_path, meta_path in PAIRS:
        try:
            meta = json.loads(meta_path.read_text())
        except json.JSONDecodeError as exc:
            mismatches.append((artifact_name, f"unparseable sidecar: {exc}"))
            continue

        if artifact_path.suffix == ".parquet":
            derived = _parquet_schema(artifact_path)
        elif artifact_path.suffix == ".json":
            derived = _json_keys(artifact_path)
        else:
            continue  # no schema contract for non-JSON/parquet artifacts

        if meta != derived:
            bad_fields = [field for field in derived if meta.get(field) != derived[field]]
            mismatches.append((artifact_name, bad_fields))

    assert not mismatches, (
        f"{len(mismatches)} sidecar(s) disagree with their artifact:\n"
        + "\n".join(f"  {name}: {fields}" for name, fields in mismatches[:20])
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
