"""Tests for ``scripts/probe_fred_availability.py`` (offline, no network).

The script verifies, for a curated set of free/public macro series, whether the
data is actually reachable from FRED (CSV, no key) so a discovery cycle can
*verify* a data-availability claim instead of assuming one.  Every test stubs the
network layer -- either ``urllib.request.urlopen`` (for ``fetch_fred``'s CSV
parsing) or the module-level ``fetch_fred`` helper (for ``probe``/``main``) -- so
the probe stays honest as the live FRED service evolves and no HTTP request is
ever made.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "probe_fred_availability.py"

spec = importlib.util.spec_from_file_location("probe_fred_availability", SCRIPT)
assert spec is not None and spec.loader is not None, f"cannot load {SCRIPT}"
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class _FakeResponse:
    """Minimal stand-in for the object returned by ``urllib.request.urlopen``."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


def _fred_csv(rows: str) -> bytes:
    return ("DATE,value\n" + rows).encode("utf-8")


def _series(dates: list[str], values: list[float]) -> pd.Series:
    return pd.Series(values, index=pd.to_datetime(dates), dtype="float64")


# --------------------------------------------------------------------------- #
# fetch_fred: CSV download + parsing
# --------------------------------------------------------------------------- #


def test_fetch_fred_parses_csv_and_drops_missing(monkeypatch):
    payload = _fred_csv("2020-01-02,1.5\n2020-01-03,.\n2020-01-06,2.5\n")
    monkeypatch.setattr(mod.urllib.request, "urlopen", lambda *a, **k: _FakeResponse(payload))

    series = mod.fetch_fred("T10YIE")

    assert list(series.index) == [pd.Timestamp("2020-01-02"), pd.Timestamp("2020-01-06")]
    assert series.tolist() == pytest.approx([1.5, 2.5])


def test_fetch_fred_empty_payload_yields_empty_series(monkeypatch):
    monkeypatch.setattr(mod.urllib.request, "urlopen", lambda *a, **k: _FakeResponse(_fred_csv("")))

    series = mod.fetch_fred("T10YIE")

    assert len(series) == 0


# --------------------------------------------------------------------------- #
# probe: per-series evidence row
# --------------------------------------------------------------------------- #


def test_probe_ok_row(monkeypatch):
    monkeypatch.setattr(
        mod, "fetch_fred", lambda sid: _series(["2020-01-02", "2020-01-06"], [1.0, 2.0])
    )

    row = mod.probe("T10YIE")

    assert row["status"] == "OK"
    assert row["n_obs"] == 2
    assert row["start"] == "2020-01-02"
    assert row["end"] == "2020-01-06"
    assert row["error"] == ""
    assert row["category"] == mod.FRED_SERIES["T10YIE"][1]


def test_probe_unreachable_row(monkeypatch):
    def boom(series_id):
        raise OSError("connection reset")

    monkeypatch.setattr(mod, "fetch_fred", boom)

    row = mod.probe("T10YIE")

    assert row["status"] == "UNREACHABLE"
    assert row["n_obs"] == 0
    assert row["start"] == ""
    assert row["end"] == ""
    assert row["error"].startswith("OSError:")


def test_probe_unknown_series_is_graceful(monkeypatch):
    # Regression guard: probe() used to index FRED_SERIES[series_id] *before* the
    # try block, so an unknown id raised KeyError and crashed the whole probe --
    # contradicting main()'s own "probing anyway" warning. It must return a row.
    monkeypatch.setattr(mod, "fetch_fred", lambda sid: _series(["2020-01-02"], [1.0]))

    row = mod.probe("NOTREAL")

    assert row["series"] == "NOTREAL"
    assert row["category"] == "unknown"
    assert row["status"] == "OK"


# --------------------------------------------------------------------------- #
# main: output + exit codes
# --------------------------------------------------------------------------- #


def test_main_returns_zero_when_all_reachable(monkeypatch, capsys):
    monkeypatch.setattr(
        mod, "fetch_fred", lambda sid: _series(["2020-01-02", "2020-01-06"], [1.0, 2.0])
    )

    rc = mod.main(["T10YIE"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "T10YIE" in out
    assert "reachable" in out.lower()


def test_main_returns_one_when_any_unreachable(monkeypatch, capsys):
    def boom(series_id):
        raise OSError("404")

    monkeypatch.setattr(mod, "fetch_fred", boom)

    rc = mod.main(["T10YIE"])
    captured = capsys.readouterr()

    assert rc == 1
    assert "UNREACHABLE" in captured.out
    assert "UNREACHABLE" in captured.err


def test_main_unknown_series_warns_and_does_not_crash(monkeypatch, capsys):
    def boom(series_id):
        raise OSError("404")

    monkeypatch.setattr(mod, "fetch_fred", boom)

    rc = mod.main(["NOTREAL"])
    out = capsys.readouterr().out

    assert rc == 1
    assert "warning" in out.lower()
    assert "NOTREAL" in out


def test_main_default_probes_curated_set(monkeypatch, capsys):
    monkeypatch.setattr(mod, "fetch_fred", lambda sid: _series(["2020-01-02"], [1.0]))

    rc = mod.main([])
    out = capsys.readouterr().out

    assert rc == 0
    for series_id in mod.FRED_SERIES:
        assert series_id in out


def test_fred_series_table_is_well_formed():
    assert mod.FRED_SERIES, "FRED_SERIES must not be empty"
    for series_id, entry in mod.FRED_SERIES.items():
        assert isinstance(series_id, str) and series_id
        assert isinstance(entry, tuple) and len(entry) == 2
        description, category = entry
        assert isinstance(description, str) and description
        assert isinstance(category, str) and category
