"""Offline tests for scripts/plan_artifact_restoration.py (pure functions)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts.plan_artifact_restoration import (
    _hash_file,
    _recorded_hash,
    build_plan,
    is_h28_experiment,
)


def test_is_h28_experiment_true():
    assert is_h28_experiment({"metadata": {"name": "h28_causal_recert"}}) is True


def test_is_h28_experiment_false():
    assert is_h28_experiment({"metadata": {"name": "h197_foo"}}) is False
    assert is_h28_experiment({}) is False


def test_recorded_hash_valid():
    name = "artifact_" + "a" * 16
    assert _recorded_hash(name) == "a" * 16


def test_recorded_hash_none():
    assert _recorded_hash("nohash") is None
    assert _recorded_hash("short_abcd") is None


def test_hash_file(tmp_path: Path):
    p = tmp_path / "f.txt"
    p.write_text("hello", encoding="utf-8")
    expected = hashlib.sha256(b"hello").hexdigest()[:16]
    assert _hash_file(p) == expected


def test_build_plan_missing_and_matching(tmp_path: Path):
    # candidate with matching hash
    src = tmp_path / "src_artifact.json"
    content = b"payload"
    src.write_bytes(content)
    h = hashlib.sha256(content).hexdigest()[:16]
    artifact_name = f"artifact_{h}"
    missing = tmp_path / "missing" / "artifact.json"
    exp = {
        "metadata": {"experiment_id": "EXP1", "name": "foo"},
        "artifacts": {artifact_name: str(missing)},
    }
    idx = {missing.name: [src]}
    recoverable, unrecoverable, excluded = build_plan([exp], idx)
    assert len(recoverable) == 1
    assert recoverable[0]["exact_match"] is True
    assert len(unrecoverable) == 0
    assert len(excluded) == 0


def test_build_plan_unrecoverable():
    missing = Path("/tmp/does_not_exist_xyz/artifact.json")
    exp = {
        "metadata": {"experiment_id": "EXP2", "name": "bar"},
        "artifacts": {"nohash": str(missing)},
    }
    recoverable, unrecoverable, excluded = build_plan([exp], {})
    assert len(unrecoverable) == 1
    assert len(recoverable) == 0


def test_build_plan_h28_excluded(tmp_path: Path):
    src = tmp_path / "src_artifact.json"
    content = b"payload2"
    src.write_bytes(content)
    h = hashlib.sha256(content).hexdigest()[:16]
    artifact_name = f"artifact_{h}"
    missing = tmp_path / "missing2" / "artifact.json"
    exp = {
        "metadata": {"experiment_id": "EXP3", "name": "h28_causal_recertification"},
        "artifacts": {artifact_name: str(missing)},
    }
    idx = {missing.name: [src]}
    recoverable, unrecoverable, excluded = build_plan([exp], idx)
    assert len(excluded) == 1
    assert len(recoverable) == 0
