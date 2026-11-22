"""Tests for ``scripts/probe_broad_universe_shares_availability.py`` (offline, no network).

The probe verifies -- reproducibly -- that point-in-time shares outstanding for the
broad S&P 500/400/600 universe is reachable from the SEC ``frames`` API (one request
per quarter returns every reporting entity), so the Cycle 271 "PIT shares are not
bounded" blocker can be *measured* rather than re-asserted.  Every network layer is
stubbed through ``fetch_fn``: the SEC ticker map, the Wikipedia constituent lists and
each frames period.  No HTTP request is made.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "probe_broad_universe_shares_availability.py"

spec = importlib.util.spec_from_file_location("probe_broad_universe_shares_availability", SCRIPT)
assert spec is not None and spec.loader is not None, f"cannot load {SCRIPT}"
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def _constituents_html(symbols: list[str]) -> bytes:
    rows = "".join(f"<tr><td>{s}</td><td>Security {s}</td></tr>" for s in symbols)
    return f"<table><tr><th>Symbol</th><th>Security</th></tr>{rows}</table>".encode()


def _fake_fetch(mapping: dict[str, bytes]):
    """Return a ``fetch_fn(url)`` serving ``mapping`` by first-substring match."""

    def _fetch(url: str, timeout: float = 30.0) -> bytes:
        for key, value in mapping.items():
            if key in url:
                return value
        raise AssertionError(f"unexpected URL in test: {url}")

    return _fetch


def _ticker_map_json(tickers_ciks: dict[str, int]) -> bytes:
    raw = {str(i): {"ticker": t, "cik_str": c} for i, (t, c) in enumerate(tickers_ciks.items())}
    return json.dumps(raw).encode()


def _frame_json(rows: list[dict]) -> bytes:
    return json.dumps(
        {"data": rows, "taxonomy": "dei", "tag": "EntityCommonStockSharesOutstanding"}
    ).encode()


def _entity(cik: int, end: str, val: float) -> dict:
    return {
        "cik": cik,
        "end": end,
        "val": val,
        "accn": "0000000000-00-000000",
        "entityName": f"E{cik}",
    }


# --------------------------------------------------------------------------- #
# _normalize_ticker / parse_constituents
# --------------------------------------------------------------------------- #


def test_normalize_ticker_maps_class_shares_and_strips_caret():
    assert mod._normalize_ticker("brk.b") == "BRK-B"
    assert mod._normalize_ticker("bf.b") == "BF-B"
    assert mod._normalize_ticker("^gspc") == "GSPC"
    assert mod._normalize_ticker(" aapl ") == "AAPL"


def test_parse_constituents_extracts_symbol_column_and_dedups():
    html = _constituents_html(["AAPL", "MSFT", "BRK.B", "AAPL"])
    got = mod.parse_constituents(html.decode())
    assert got == ["AAPL", "BRK-B", "MSFT"]


def test_parse_constituents_returns_empty_when_no_symbol_column():
    html = b"<table><tr><th>Name</th></tr><tr><td>x</td></tr></table>"
    assert mod.parse_constituents(html.decode()) == []


# --------------------------------------------------------------------------- #
# frame_periods: quarter stepping and in-progress-quarter skip
# --------------------------------------------------------------------------- #


def test_frame_periods_skips_in_progress_quarter_newest_first():
    import datetime as dt

    # 2024-02-15 is in Q1 2024; the last *completed* quarter is Q4 2023.
    periods = mod.frame_periods(5, end=dt.date(2024, 2, 15))
    assert periods == ["CY2023Q4I", "CY2023Q3I", "CY2023Q2I", "CY2023Q1I", "CY2022Q4I"]


def test_frame_periods_crosses_year_boundary():
    import datetime as dt

    periods = mod.frame_periods(3, end=dt.date(2024, 5, 10))  # Q2 2024 -> start Q1 2024
    assert periods == ["CY2024Q1I", "CY2023Q4I", "CY2023Q3I"]


def test_frame_periods_zero_is_empty():
    assert mod.frame_periods(0) == []


# --------------------------------------------------------------------------- #
# load_ticker_cik_map: cached read / fetch / missing-without-fetch
# --------------------------------------------------------------------------- #


def test_load_ticker_cik_map_reads_cache(tmp_path):
    (tmp_path / "company_tickers.json").write_bytes(_ticker_map_json({"AAPL": 320193}))
    mapping = mod.load_ticker_cik_map(tmp_path, fetch=False)
    assert mapping == {"AAPL": 320193}


def test_load_ticker_cik_map_missing_without_fetch_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        mod.load_ticker_cik_map(tmp_path, fetch=False)


def test_load_ticker_cik_map_fetches_and_caches(tmp_path):
    calls = {"n": 0}

    def fetch(url, timeout=30.0):
        calls["n"] += 1
        return _ticker_map_json({"AAPL": 320193, "MSFT": 789019})

    mapping = mod.load_ticker_cik_map(tmp_path, fetch=True, fetch_fn=fetch)
    assert mapping == {"AAPL": 320193, "MSFT": 789019}
    assert calls["n"] == 1
    assert (tmp_path / "company_tickers.json").is_file()


# --------------------------------------------------------------------------- #
# fetch_frame / fetch_frames: parse + retry + rate-limit pause
# --------------------------------------------------------------------------- #


def test_fetch_frame_parses_data_list():
    rows = [_entity(1, "2024-01-01", 100.0), _entity(2, "2024-01-01", 200.0)]
    out = mod.fetch_frame("CY2023Q4I", fetch_fn=_fake_fetch({"frames": _frame_json(rows)}))
    assert [r["cik"] for r in out] == [1, 2]


def test_fetch_frame_recovers_after_transient_failures():
    state = {"n": 0}
    rows = [_entity(1, "2024-01-01", 100.0)]

    def fetch(url, timeout=30.0):
        state["n"] += 1
        if state["n"] < 3:
            raise OSError("transient")
        return _frame_json(rows)

    out = mod.fetch_frame("CY2023Q4I", fetch_fn=fetch, retries=3, throttle_s=0.0)
    assert out == rows
    assert state["n"] == 3


def test_fetch_frame_returns_empty_after_persistent_failure():
    def fetch(url, timeout=30.0):
        raise OSError("down")

    out = mod.fetch_frame("CY2023Q4I", fetch_fn=fetch, retries=2, throttle_s=0.0)
    assert out == []


def test_fetch_frames_returns_each_period():
    rows = [_entity(1, "2024-01-01", 100.0)]
    frames = mod.fetch_frames(
        ["CY2023Q4I", "CY2023Q3I"], fetch_fn=_fake_fetch({"frames": _frame_json(rows)}), pause_s=0.0
    )
    assert set(frames) == {"CY2023Q4I", "CY2023Q3I"}
    assert all(v == rows for v in frames.values())


# --------------------------------------------------------------------------- #
# build_shares_panel
# --------------------------------------------------------------------------- #


def test_build_shares_panel_groups_by_cik_and_skips_incomplete():
    frames = {
        "CY2023Q4I": [
            _entity(1, "2023-11-01", 100.0),
            {"cik": 2, "end": "2023-11-01"},  # missing val -> skipped
            {"cik": None, "end": "2023-11-01", "val": 5.0},  # missing cik -> skipped
        ],
        "CY2023Q3I": [_entity(1, "2023-08-01", 99.0)],
    }
    panel = mod.build_shares_panel(frames)
    assert set(panel) == {1}
    assert [row["period"] for row in panel[1]] == ["CY2023Q4I", "CY2023Q3I"]
    assert panel[1][0]["val"] == 100.0


# --------------------------------------------------------------------------- #
# compute_coverage
# --------------------------------------------------------------------------- #


def _panel_for(cik_quarters: dict[int, int]) -> dict[int, list[dict]]:
    periods = ["CY2024Q1I", "CY2024Q2I", "CY2024Q3I", "CY2024Q4I"]
    panel: dict[int, list[dict]] = {}
    for cik, depth in cik_quarters.items():
        panel[cik] = [
            {"end": f"2024-0{1 + i}-01", "val": 100.0 + i, "period": periods[i]}
            for i in range(depth)
        ]
    return panel


def test_compute_coverage_counts_depth_and_missing_cik():
    universe = ["AAA", "BBB", "CCC"]
    ticker_to_cik = {"AAA": 1, "BBB": 2}  # CCC has no CIK
    panel = _panel_for({1: 4, 2: 1})
    cov = mod.compute_coverage(universe, ticker_to_cik, panel, min_quarters=4)
    assert cov["universe_size"] == 3
    assert cov["n_with_any_shares"] == 2
    assert cov["frac_with_any_shares"] == pytest.approx(2 / 3)
    assert cov["n_with_min_quarters"] == 1  # only AAA reaches 4 quarters
    assert cov["frac_with_min_quarters"] == pytest.approx(1 / 3)
    assert cov["n_without_cik"] == 1
    assert cov["per_name"]["AAA"]["quarters"] == 4
    assert cov["per_name"]["CCC"]["has_data"] is False


def test_compute_coverage_median_depth():
    universe = ["AAA", "BBB", "CCC"]
    ticker_to_cik = {"AAA": 1, "BBB": 2, "CCC": 3}
    panel = _panel_for({1: 1, 2: 4})  # CCC present but no observations
    cov = mod.compute_coverage(universe, ticker_to_cik, panel, min_quarters=1)
    assert cov["median_quarters_per_name"] == 1  # upper median of depths [0, 1, 4]


def test_compute_coverage_empty_universe():
    cov = mod.compute_coverage([], {}, {}, min_quarters=4)
    assert cov["universe_size"] == 0
    assert cov["frac_with_any_shares"] == 0.0
    assert cov["median_quarters_per_name"] == 0


# --------------------------------------------------------------------------- #
# main: end-to-end, fully offline, exit codes + artifact
# --------------------------------------------------------------------------- #


def _main_fetch(n_quarters_entities: int = 5):
    symbols = ["AAA", "BBB", "CCC", "DDD", "EEE"]
    tickers_ciks = {s: i + 1 for i, s in enumerate(symbols)}
    entities = [_entity(i + 1, "2024-01-01", 100.0 + i) for i in range(n_quarters_entities)]
    mapping = {
        "List_of_S": _constituents_html(symbols),
        "company_tickers": _ticker_map_json(tickers_ciks),
        "frames": _frame_json(entities),
    }
    return _fake_fetch(mapping)


def test_main_reachable_returns_zero_and_writes_artifact(tmp_path):
    artifact = tmp_path / "shares.json"
    rc = mod.main(
        [
            "--quarters",
            "4",
            "--min-quarters",
            "4",
            "--cache-dir",
            str(tmp_path / "cache"),
            "--write-artifact",
            str(artifact),
        ],
        fetch_fn=_main_fetch(),
    )
    assert rc == 0
    data = json.loads(artifact.read_text())
    assert data["status"] == "REACHABLE"
    assert data["coverage"]["frac_with_min_quarters"] == pytest.approx(1.0)
    assert data["coverage"]["universe_size"] == 5
    assert len(data["periods"]) == 4


def test_main_low_depth_returns_nonzero(tmp_path):
    # One quarter only, but min depth 4 -> nothing qualifies -> BLOCKED.
    rc = mod.main(
        ["--quarters", "1", "--min-quarters", "4", "--cache-dir", str(tmp_path / "cache")],
        fetch_fn=_main_fetch(n_quarters_entities=5),
    )
    assert rc == 1


def test_main_no_constituents_returns_two(tmp_path):
    def fetch(url, timeout=30.0):
        if "company_tickers" in url:
            return _ticker_map_json({"AAA": 1})
        if "frames" in url:
            return _frame_json([_entity(1, "2024-01-01", 100.0)])
        return b"<table><tr><th>Name</th></tr><tr><td>x</td></tr></table>"  # no Symbol column

    rc = mod.main(["--cache-dir", str(tmp_path / "cache")], fetch_fn=fetch)
    assert rc == 2
