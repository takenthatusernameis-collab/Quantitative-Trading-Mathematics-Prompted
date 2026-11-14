"""Contract tests for ``scripts/fetch_h182_insider_data.py`` (no network).

The corpus builder must never cache a zero-row acquisition. The original script
wrote an empty parquet whenever EDGAR returned nothing (for example during a
transient outage) and then skipped that file on every later run, silently
dropping the issuer's history. These tests pin the repaired cache contract
through ``main`` with a stubbed EDGAR fetch, so they never contact the network.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

from qtr.data import insider

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "fetch_h182_insider_data.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("fetch_h182_insider_data", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def script():
    return _load_script()


def _transactions(rows: int = 1) -> pd.DataFrame:
    return pd.DataFrame(
        [{"transaction_code": "S", "available_at": pd.Timestamp("2026-11-12")}] * rows,
        columns=["transaction_code", "available_at"],
    )


def _write_cache(path: Path, rows: int) -> None:
    _transactions(rows).to_parquet(path)


def _run(script, monkeypatch, tmp_path, *, cached_rows, fetch_result, force=False):
    calls = []

    def fake_fetch(cik, **kwargs):
        calls.append(cik)
        if isinstance(fetch_result, BaseException):
            raise fetch_result
        return fetch_result

    monkeypatch.setattr(insider, "fetch_insider_transactions", fake_fetch)
    argv = [
        "fetch_h182_insider_data.py",
        "--cache-dir",
        str(tmp_path),
        "--symbols",
        "AAPL",
    ]
    if force:
        argv.append("--force")
    monkeypatch.setattr(sys, "argv", argv)

    out = tmp_path / "AAPL.parquet"
    if cached_rows is not None:
        _write_cache(out, cached_rows)

    script.main()
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    return calls, manifest["symbols"]["AAPL"]


def test_empty_cache_is_refetched_and_populated(script, monkeypatch, tmp_path):
    calls, entry = _run(script, monkeypatch, tmp_path, cached_rows=0, fetch_result=_transactions(3))
    assert calls == [script.UNIVERSE["AAPL"]]
    assert entry["rows"] == 3
    assert entry["source"] == "edgar"
    assert len(pd.read_parquet(tmp_path / "AAPL.parquet")) == 3


def test_non_empty_cache_is_skipped(script, monkeypatch, tmp_path):
    calls, entry = _run(script, monkeypatch, tmp_path, cached_rows=2, fetch_result=_transactions(1))
    assert calls == []
    assert entry["rows"] == 2
    assert entry["source"] == "cache"


def test_force_refetches_a_non_empty_cache(script, monkeypatch, tmp_path):
    calls, entry = _run(
        script,
        monkeypatch,
        tmp_path,
        cached_rows=2,
        fetch_result=_transactions(5),
        force=True,
    )
    assert calls == [script.UNIVERSE["AAPL"]]
    assert entry["rows"] == 5
    assert entry["source"] == "edgar"


def test_fetch_error_is_recorded_and_not_cached(script, monkeypatch, tmp_path):
    calls, entry = _run(
        script, monkeypatch, tmp_path, cached_rows=0, fetch_result=OSError("outage")
    )
    assert calls == [script.UNIVERSE["AAPL"]]
    assert entry["rows"] == 0
    assert entry["source"] == "error"
    assert "outage" in entry["error"]
    assert len(pd.read_parquet(tmp_path / "AAPL.parquet")) == 0


def test_empty_fetch_is_not_cached_as_a_valid_result(script, monkeypatch, tmp_path):
    calls, entry = _run(
        script,
        monkeypatch,
        tmp_path,
        cached_rows=0,
        fetch_result=_transactions(0),
    )
    assert calls == [script.UNIVERSE["AAPL"]]
    assert entry["rows"] == 0
    assert entry["source"] == "empty"
    assert len(pd.read_parquet(tmp_path / "AAPL.parquet")) == 0
