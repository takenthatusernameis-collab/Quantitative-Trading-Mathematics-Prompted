#!/usr/bin/env python3
"""Repair backfilled ``.meta.json`` sidecars whose schema fields disagree with
the artifact they describe.

Background: the 2026-11-13 sidecar backfill (remediation item 5 in
``REPRODUCIBILITY_AUDIT_REPORT.md``) derived ``shape``/``columns``/``dtypes``/
``index_type`` for parquet artifacts and top-level ``keys`` for JSON artifacts.
A subset of those sidecars recorded a datetime resolution (``datetime64[s]``)
that differs from the resolution actually stored on disk (``datetime64[ms]``).
This is a pandas/pyarrow version artifact: the sidecar was derived by reading
the artifact with a different resolution than the one the artifact carries.

This script re-derives each sidecar's schema fields from the artifact itself
and rewrites the sidecar **only when it disagrees**. It never touches an
artifact, never deletes a sidecar, and never overwrites a sidecar whose fields
already match. Hash-exact artifacts only (the 11 superseded hash-mismatch rows
are skipped, since their recorded hash is stale by design).

Idempotent: re-running produces no further changes.
"""

import hashlib
import json
from pathlib import Path

import pandas as pd

EXPERIMENTS_JSONL = Path(".experiments/experiments.jsonl")
EXPERIMENTS_ROOT = Path(".experiments")


def _file_hash(filepath: Path, length: int = 16) -> str:
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:length]


def _derive_parquet_schema(path: Path) -> dict:
    df = pd.read_parquet(path)
    return {
        "shape": list(df.shape),
        "columns": df.columns.tolist(),
        "dtypes": {str(k): str(v) for k, v in df.dtypes.to_dict().items()},
        "index_type": str(df.index.dtype),
    }


def _derive_json_keys(path: Path) -> dict:
    with open(path) as f:
        return {"keys": list(json.load(f).keys())}


def main() -> int:
    if not EXPERIMENTS_JSONL.exists():
        raise SystemExit(f"missing {EXPERIMENTS_JSONL}")

    repaired = 0
    checked = 0
    for line in open(EXPERIMENTS_JSONL):
        line = line.strip()
        if not line:
            continue
        exp = json.loads(line)
        for artifact_name, artifact_path_str in exp.get("artifacts", {}).items():
            artifact_path = Path(artifact_path_str)
            if not artifact_path.exists():
                continue  # caught by the missing-files audit

            recorded_hash = artifact_name.split("_")[-1] if "_" in artifact_name else None
            if recorded_hash is None or len(recorded_hash) != 16:
                continue  # no hash in name; not a hash-pinned artifact
            if _file_hash(artifact_path) != recorded_hash:
                continue  # superseded/stale row; skip by design

            meta_path = EXPERIMENTS_ROOT / f"{artifact_name}.meta.json"
            if not meta_path.exists():
                continue  # no sidecar to repair (backlog audit covers this)

            try:
                meta = json.loads(meta_path.read_text())
            except json.JSONDecodeError:
                continue

            if artifact_path.suffix == ".parquet":
                derived = _derive_parquet_schema(artifact_path)
            elif artifact_path.suffix == ".json":
                derived = _derive_json_keys(artifact_path)
            else:
                continue  # non-JSON/parquet artifact; no schema contract

            checked += 1
            if meta == derived:
                continue

            meta_path.write_text(json.dumps(derived, indent=2) + "\n")
            repaired += 1

    print(f"checked {checked} hash-exact sidecars, repaired {repaired}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
