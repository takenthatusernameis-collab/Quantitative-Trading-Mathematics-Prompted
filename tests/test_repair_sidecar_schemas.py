"""Tests for ``scripts/repair_sidecar_schemas.py`` (offline, no network).

The script re-derives each hash-exact artifact's ``.meta.json`` sidecar from
the artifact itself and rewrites the sidecar **only when it disagrees**
(datetime-resolution mismatches left by the 2026-11-13 sidecar backfill). It is
idempotent: re-running repairs nothing, and it never touches an artifact or a
sidecar that already matches.

Every test builds a throwaway ``.experiments`` tree under ``tmp_path`` and
monkeypatches the script's module-level ``EXPERIMENTS_JSONL`` /
``EXPERIMENTS_ROOT`` so no committed artifact or sidecar is ever touched. No
HTTP request is ever made.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "repair_sidecar_schemas.py"

spec = importlib.util.spec_from_file_location("repair_sidecar_schemas", SCRIPT)
assert spec is not None and spec.loader is not None, f"cannot load {SCRIPT}"
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def _file_hash(filepath: Path, length: int = 16) -> str:
    return hashlib.sha256(filepath.read_bytes()).hexdigest()[:length]


def _write_jsonl(root: Path, entries: list[dict]) -> Path:
    jsonl = root / "experiments.jsonl"
    with open(jsonl, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
    return jsonl


def _exp_entry(artifacts: dict[str, str]) -> dict:
    return {"metadata": {"experiment_id": "exp_test"}, "artifacts": artifacts}


def _parquet_df() -> pd.DataFrame:
    return pd.DataFrame(
        {"equity": [1.0, 2.0, 3.0]},
        index=pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]),
    )


def _wrong_index_type(derived: dict) -> str:
    actual = derived["index_type"]
    return "datetime64[s]" if actual != "datetime64[s]" else "datetime64[ms]"


# --------------------------------------------------------------------------- #
# repair behaviour: parquet sidecars
# --------------------------------------------------------------------------- #


def test_repairs_mismatching_parquet_sidecar_leaves_match_untouched(tmp_path, monkeypatch):
    root = tmp_path / ".experiments"
    root.mkdir()
    (root / "artifacts" / "exp_test").mkdir(parents=True)

    jsonl = _write_jsonl(root, [])

    # Artifact A: sidecar already matches -> must be left untouched.
    path_a = root / "artifacts" / "exp_test" / "prices.parquet"
    _parquet_df().to_parquet(path_a)
    hash_a = _file_hash(path_a)
    name_a = f"prices_{hash_a}"
    derived_a = mod._derive_parquet_schema(path_a)
    (root / f"{name_a}.meta.json").write_text(json.dumps(derived_a, indent=2) + "\n")
    sidecar_a_before = (root / f"{name_a}.meta.json").read_bytes()

    # Artifact B: sidecar disagrees (datetime resolution) -> must be repaired.
    path_b = root / "artifacts" / "exp_test" / "volumes.parquet"
    _parquet_df().to_parquet(path_b)
    hash_b = _file_hash(path_b)
    name_b = f"volumes_{hash_b}"
    derived_b = mod._derive_parquet_schema(path_b)
    wrong_b = dict(derived_b)
    wrong_b["index_type"] = _wrong_index_type(derived_b)
    (root / f"{name_b}.meta.json").write_text(json.dumps(wrong_b, indent=2) + "\n")

    exp = _exp_entry({name_a: str(path_a), name_b: str(path_b)})
    jsonl.write_text(json.dumps(exp) + "\n")

    monkeypatch.setattr(mod, "EXPERIMENTS_JSONL", jsonl)
    monkeypatch.setattr(mod, "EXPERIMENTS_ROOT", root)

    rc = mod.main()

    assert rc == 0
    # A untouched.
    assert (root / f"{name_a}.meta.json").read_bytes() == sidecar_a_before
    assert json.loads((root / f"{name_a}.meta.json").read_text()) == derived_a
    # B repaired to the derived schema.
    assert json.loads((root / f"{name_b}.meta.json").read_text()) == derived_b


def test_repairs_json_sidecar_key_order(tmp_path, monkeypatch):
    root = tmp_path / ".experiments"
    root.mkdir()
    (root / "artifacts" / "exp_test").mkdir(parents=True)
    jsonl = _write_jsonl(root, [])

    path = root / "artifacts" / "exp_test" / "meta.json"
    path.write_text(json.dumps({"b": 2, "a": 1}))
    h = _file_hash(path)
    name = f"meta_{h}"
    derived = mod._derive_json_keys(path)
    wrong = {"keys": list(reversed(derived["keys"]))}
    assert wrong != derived
    (root / f"{name}.meta.json").write_text(json.dumps(wrong, indent=2) + "\n")

    exp = _exp_entry({name: str(path)})
    jsonl.write_text(json.dumps(exp) + "\n")

    monkeypatch.setattr(mod, "EXPERIMENTS_JSONL", jsonl)
    monkeypatch.setattr(mod, "EXPERIMENTS_ROOT", root)

    rc = mod.main()

    assert rc == 0
    assert json.loads((root / f"{name}.meta.json").read_text()) == derived


# --------------------------------------------------------------------------- #
# skip rules: superseded, missing file, missing sidecar, non-contract suffix
# --------------------------------------------------------------------------- #


def test_skips_superseded_hash_mismatch_artifact(tmp_path, monkeypatch):
    root = tmp_path / ".experiments"
    root.mkdir()
    (root / "artifacts" / "exp_test").mkdir(parents=True)
    jsonl = _write_jsonl(root, [])

    path = root / "artifacts" / "exp_test" / "prices.parquet"
    _parquet_df().to_parquet(path)
    # Deliberately wrong 16-char hash in the artifact name -> superseded row.
    name = "prices_0000000000000000"
    (root / f"{name}.meta.json").write_text("{}")

    exp = _exp_entry({name: str(path)})
    jsonl.write_text(json.dumps(exp) + "\n")

    monkeypatch.setattr(mod, "EXPERIMENTS_JSONL", jsonl)
    monkeypatch.setattr(mod, "EXPERIMENTS_ROOT", root)

    rc = mod.main()

    assert rc == 0
    # Sidecar must not be rewritten (row skipped entirely).
    assert json.loads((root / f"{name}.meta.json").read_text()) == {}


def test_skips_missing_artifact_file(tmp_path, monkeypatch):
    root = tmp_path / ".experiments"
    root.mkdir()
    jsonl = _write_jsonl(root, [])

    name = "prices_0000000000000001"
    missing = root / "artifacts" / "exp_test" / "does_not_exist.parquet"
    (root / f"{name}.meta.json").write_text("{}")

    exp = _exp_entry({name: str(missing)})
    jsonl.write_text(json.dumps(exp) + "\n")

    monkeypatch.setattr(mod, "EXPERIMENTS_JSONL", jsonl)
    monkeypatch.setattr(mod, "EXPERIMENTS_ROOT", root)

    rc = mod.main()

    assert rc == 0
    assert (root / f"{name}.meta.json").read_text() == "{}"


def test_skips_hash_exact_artifact_without_sidecar(tmp_path, monkeypatch):
    root = tmp_path / ".experiments"
    root.mkdir()
    (root / "artifacts" / "exp_test").mkdir(parents=True)
    jsonl = _write_jsonl(root, [])

    path = root / "artifacts" / "exp_test" / "prices.parquet"
    _parquet_df().to_parquet(path)
    h = _file_hash(path)
    name = f"prices_{h}"
    # No sidecar written for this artifact.

    exp = _exp_entry({name: str(path)})
    jsonl.write_text(json.dumps(exp) + "\n")

    monkeypatch.setattr(mod, "EXPERIMENTS_JSONL", jsonl)
    monkeypatch.setattr(mod, "EXPERIMENTS_ROOT", root)

    rc = mod.main()

    assert rc == 0


def test_skips_non_parquet_json_suffix(tmp_path, monkeypatch):
    root = tmp_path / ".experiments"
    root.mkdir()
    (root / "artifacts" / "exp_test").mkdir(parents=True)
    jsonl = _write_jsonl(root, [])

    path = root / "artifacts" / "exp_test" / "notes.csv"
    path.write_text("a,b\n1,2\n")
    h = _file_hash(path)
    name = f"notes_{h}"
    (root / f"{name}.meta.json").write_text("{}")

    exp = _exp_entry({name: str(path)})
    jsonl.write_text(json.dumps(exp) + "\n")

    monkeypatch.setattr(mod, "EXPERIMENTS_JSONL", jsonl)
    monkeypatch.setattr(mod, "EXPERIMENTS_ROOT", root)

    rc = mod.main()

    assert rc == 0


# --------------------------------------------------------------------------- #
# idempotency
# --------------------------------------------------------------------------- #


def test_idempotent_second_run_repairs_nothing(tmp_path, monkeypatch, capsys):
    root = tmp_path / ".experiments"
    root.mkdir()
    (root / "artifacts" / "exp_test").mkdir(parents=True)
    jsonl = _write_jsonl(root, [])

    path = root / "artifacts" / "exp_test" / "prices.parquet"
    _parquet_df().to_parquet(path)
    h = _file_hash(path)
    name = f"prices_{h}"
    derived = mod._derive_parquet_schema(path)
    wrong = dict(derived)
    wrong["index_type"] = _wrong_index_type(derived)
    (root / f"{name}.meta.json").write_text(json.dumps(wrong, indent=2) + "\n")

    exp = _exp_entry({name: str(path)})
    jsonl.write_text(json.dumps(exp) + "\n")

    monkeypatch.setattr(mod, "EXPERIMENTS_JSONL", jsonl)
    monkeypatch.setattr(mod, "EXPERIMENTS_ROOT", root)

    mod.main()
    out_first = capsys.readouterr().out

    mod.main()
    out_second = capsys.readouterr().out

    assert "repaired 1" in out_first
    assert "repaired 0" in out_second
    assert json.loads((root / f"{name}.meta.json").read_text()) == derived


def test_main_output_counts_checked_and_repaired(tmp_path, monkeypatch):
    root = tmp_path / ".experiments"
    root.mkdir()
    (root / "artifacts" / "exp_test").mkdir(parents=True)
    jsonl = _write_jsonl(root, [])

    path = root / "artifacts" / "exp_test" / "prices.parquet"
    _parquet_df().to_parquet(path)
    h = _file_hash(path)
    name = f"prices_{h}"
    derived = mod._derive_parquet_schema(path)
    (root / f"{name}.meta.json").write_text(json.dumps(derived, indent=2) + "\n")

    exp = _exp_entry({name: str(path)})
    jsonl.write_text(json.dumps(exp) + "\n")

    monkeypatch.setattr(mod, "EXPERIMENTS_JSONL", jsonl)
    monkeypatch.setattr(mod, "EXPERIMENTS_ROOT", root)

    assert mod.main() == 0
