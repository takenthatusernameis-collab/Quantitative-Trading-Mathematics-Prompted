from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "rebuild_13f_cik_map", ROOT / "scripts" / "rebuild_13f_cik_map.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def test_build_title_index_groups_by_lowercase_title():
    tickers = [
        {"cik_str": "1", "ticker": "BRK", "title": "Berkshire Hathaway Inc"},
        {"cik_str": "2", "ticker": "BRK", "title": "Berkshire Hathaway Inc"},
        {"cik_str": "3", "ticker": "UBS", "title": "UBS Group AG"},
    ]
    index = mod.build_title_index(tickers)
    assert set(index) == {"berkshire hathaway inc", "ubs group ag"}
    assert len(index["berkshire hathaway inc"]) == 2


def test_resolve_cik_exact_match():
    tickers = [{"cik_str": "1067983", "ticker": "BRK", "title": "Berkshire Hathaway Inc"}]
    index = mod.build_title_index(tickers)
    assert mod.resolve_cik("Berkshire Hathaway Inc", index) == 1067983


def test_resolve_cik_ampersand_normalised():
    tickers = [{"cik_str": "7", "ticker": "FMR", "title": "Fidelity Management and Research"}]
    index = mod.build_title_index(tickers)
    assert mod.resolve_cik("Fidelity Management & Research", index) == 7


def test_resolve_cik_starts_with_and_prefers_shortest():
    tickers = [
        {"cik_str": "10", "ticker": "BLK", "title": "BlackRock Inc"},
        {"cik_str": "11", "ticker": "BLK", "title": "BlackRock Inc Fund Advisors"},
    ]
    index = mod.build_title_index(tickers)
    # Exact "blackrock inc" wins.
    assert mod.resolve_cik("BlackRock Inc", index) == 10
    # A longer name falls back to the shortest title that contains it.
    tickers2 = [
        {"cik_str": "20", "ticker": "WPG", "title": "Wellington Management Group"},
        {"cik_str": "21", "ticker": "WPG", "title": "Wellington Management Group Fund"},
    ]
    index2 = mod.build_title_index(tickers2)
    assert mod.resolve_cik("Wellington Management", index2) == 20


def test_resolve_cik_unresolved_returns_none():
    index = mod.build_title_index([{"cik_str": "1", "ticker": "X", "title": "Acme"}])
    assert mod.resolve_cik("Nonexistent Manager", index) is None


def test_target_managers_is_nonempty_and_unique():
    assert len(mod.TARGET_MANAGERS) > 0
    assert len(set(mod.TARGET_MANAGERS)) == len(mod.TARGET_MANAGERS)
