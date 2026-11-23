"""Tests for ``run_nf_20261122_04_size_premium.py`` (H199).

The runner tests the market-cap size premium (small-minus-big) on the broad
S&P 500/400/600 universe.  It is the only ``run_nf_*`` experiment runner that
shipped without a dedicated test module, even though every sibling H187-H198
runner has one.  These tests exercise the pure, offline pieces -- the PIT shares
panel, the market-cap panel, the size-bin portfolio construction, the
delever-only vol scaling, the walk-forward selector and the OAT perturbation --
with synthetic fixtures (no network), plus the committed artifact schema.

The most important invariant pinned here is the point-in-time rule: a month-end
shares value may only use a frames observation whose instant is at least
``PIT_LAG_DAYS`` before the rebalance date, so a later 10-Q/10-K value can never
leak backwards into an earlier backtest bar.
"""

from __future__ import annotations

import glob
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "nf_20261122_04", ROOT / "run_nf_20261122_04_size_premium.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


# --------------------------------------------------------------------------- #
# Synthetic fixtures (offline)
# --------------------------------------------------------------------------- #
def _synthetic_closes(n_days=400, n_names=6, seed=0, start="2020-01-01"):
    rng = np.random.default_rng(seed)
    calendar = pd.bdate_range(start, periods=n_days)
    rets = rng.normal(0.0, 0.01, size=(n_days, n_names))
    prices = 100.0 * np.cumprod(1.0 + rets, axis=0)
    columns = [f"S{i}" for i in range(n_names)]
    closes = pd.DataFrame(prices, index=calendar, columns=columns)
    return closes, calendar


def _constant_market_cap(calendar, n_names=6):
    """A market cap that increases with the name index (S0 smallest)."""
    return pd.DataFrame(
        {f"S{i}": 10.0 * (i + 1) for i in range(n_names)},
        index=calendar,
    )


# --------------------------------------------------------------------------- #
# Constants / pre-registration
# --------------------------------------------------------------------------- #
def test_constants_match_preregistration():
    assert mod.EXPERIMENT == "nf_20261122_04_size_premium"
    assert mod.NF_ID == "NF-20261122-04"
    assert mod.HYPOTHESIS == "H199"
    assert mod.START == "2015-01-01"
    assert mod.END == "2026-11-21"
    assert mod.TRAIN_END == "2021-12-31"
    assert mod.VAL_END == "2023-12-31"
    assert mod.COST_ONE_WAY_BPS == 5.0
    assert mod.MIN_ACTIVE_NAMES == 30
    assert mod.PIT_LAG_DAYS == 90
    assert mod.VOL_LOOKBACK == 60
    assert mod.DAYS_PER_YEAR == 252
    assert mod.GATES == mod.h184.GATES
    assert mod.GRID == {"n_bins": [3, 5], "vol_target": [0.10, 0.15]}


def test_bounded_grid_is_four_declared_combos():
    combos = list(mod.iter_grid())
    assert len(combos) == 2 * 2 == 4
    assert {row["n_bins"] for row in combos} == {3, 5}
    assert {row["vol_target"] for row in combos} == {0.10, 0.15}
    for row in combos:
        assert isinstance(row["n_bins"], int)
        assert isinstance(row["vol_target"], float)


# --------------------------------------------------------------------------- #
# Constituent loading (offline, cache / fetch paths)
# --------------------------------------------------------------------------- #
def test_load_constituents_reads_sorted_unique_cache(tmp_path):
    cache = tmp_path / "broad_shares"
    cache.mkdir()
    pd.DataFrame({"ticker": ["B", "A", "A"]}).to_csv(cache / "constituents.csv", index=False)
    assert mod.load_constituents(cache_dir=cache) == ["A", "B"]


def test_load_constituents_fetches_dedups_and_sorts(tmp_path, monkeypatch):
    monkeypatch.setattr(
        mod.avail_probe,
        "fetch_constituents",
        lambda fetch_fn=None: {"sp500": ["B", "A"], "sp400": ["A", "C"]},
    )
    result = mod.load_constituents(cache_dir=tmp_path / "fresh", refresh=True)
    assert result == ["A", "B", "C"]
    assert (tmp_path / "fresh" / "constituents.csv").exists()


# --------------------------------------------------------------------------- #
# Returns (calendar-aligned ffill + pct_change, H191 convention)
# --------------------------------------------------------------------------- #
def test_returns_from_closes_first_row_nan_and_calendar_aligned():
    closes, calendar = _synthetic_closes(n_days=20, n_names=3)
    returns = mod.returns_from_closes(closes, calendar)
    assert returns.index.equals(calendar)
    assert returns.iloc[0].isna().all()
    assert np.isfinite(returns.iloc[1:].to_numpy()).all()
    expected = closes.iloc[1] / closes.iloc[0] - 1.0
    assert np.allclose(returns.iloc[1].to_numpy(), expected.to_numpy())


def test_returns_from_closes_reindexes_missing_days():
    closes, calendar = _synthetic_closes(n_days=20, n_names=3)
    sparse = closes.drop(closes.index[5])
    returns = mod.returns_from_closes(sparse, calendar)
    # the missing day is forward-filled, so its return is exactly zero
    assert returns.iloc[5].abs().max() == 0.0


# --------------------------------------------------------------------------- #
# PIT shares panel (the mechanism's causal core)
# --------------------------------------------------------------------------- #
def _shares_frames():
    return {
        "CY2018Q2I": [{"cik": 1, "val": 100.0, "end": "2018-06-01"}],
        "CY2020Q2I": [{"cik": 1, "val": 200.0, "end": "2020-06-01"}],
    }


def test_monthly_shares_panel_respects_pit_lag():
    calendar = pd.bdate_range("2020-01-01", "2020-12-31")
    panel = mod.build_monthly_shares_panel(_shares_frames(), calendar)

    assert panel.index.equals(calendar)
    assert list(panel.columns) == [1]

    # 2020-03-31: cutoff 2020-01-01 -> only the 2018-06-01 observation is usable.
    assert panel.loc[pd.Timestamp("2020-03-31"), 1] == 100.0
    # 2020-05-01: most recent month-end 2020-04-30 (cutoff 2020-01-31) -> the
    # 2020-06-01 observation must NOT leak backwards (PIT).
    assert panel.loc[pd.Timestamp("2020-05-01"), 1] == 100.0
    # 2020-09-30: cutoff 2020-07-02 -> the 2020-06-01 observation is now usable.
    assert panel.loc[pd.Timestamp("2020-09-30"), 1] == 200.0
    # 2020-10-01: forward-filled from the 2020-09-30 month-end.
    assert panel.loc[pd.Timestamp("2020-10-01"), 1] == 200.0


def test_monthly_shares_panel_is_nan_before_first_usable_observation():
    calendar = pd.bdate_range("2019-01-01", "2019-06-30")
    # A single observation dated after the whole calendar window -> never usable.
    frames = {"CY2020Q2I": [{"cik": 1, "val": 100.0, "end": "2020-06-01"}]}
    panel = mod.build_monthly_shares_panel(frames, calendar)
    assert list(panel.columns) == [1]
    assert panel[1].isna().all()


def test_monthly_shares_panel_empty_frames_returns_calendar_indexed_frame():
    calendar = pd.bdate_range("2020-01-01", periods=10)
    panel = mod.build_monthly_shares_panel({}, calendar)
    assert panel.index.equals(calendar)
    assert panel.empty


# --------------------------------------------------------------------------- #
# Market-cap panel (shares x close, ticker/CIK alignment)
# --------------------------------------------------------------------------- #
def test_build_market_cap_panel_multiplies_shares_by_close(monkeypatch):
    closes, calendar = _synthetic_closes(n_days=20, n_names=3, seed=1)
    shares_daily = pd.DataFrame({1: 100.0, 2: 200.0, 3: 300.0}, index=calendar)
    monkeypatch.setattr(
        mod.shares_probe,
        "load_ticker_cik_map",
        lambda *args, **kwargs: {"S0": 1, "S1": 2, "S2": 3},
    )
    market_cap = mod.build_market_cap_panel(shares_daily, closes, calendar)
    assert list(market_cap.columns) == list(closes.columns)
    assert np.allclose(market_cap["S0"].to_numpy(), 100.0 * closes["S0"].to_numpy())
    assert np.allclose(market_cap["S2"].to_numpy(), 300.0 * closes["S2"].to_numpy())


def test_build_market_cap_panel_unmapped_ticker_is_all_nan(monkeypatch):
    closes, calendar = _synthetic_closes(n_days=10, n_names=2, seed=6)
    shares_daily = pd.DataFrame({1: 100.0}, index=calendar)
    monkeypatch.setattr(mod.shares_probe, "load_ticker_cik_map", lambda *args, **kwargs: {"S0": 1})
    market_cap = mod.build_market_cap_panel(shares_daily, closes, calendar)
    assert market_cap["S0"].notna().any()
    assert market_cap["S1"].isna().all()


# --------------------------------------------------------------------------- #
# Size-bin portfolio construction
# --------------------------------------------------------------------------- #
def test_build_size_weights_long_small_short_big_gross_normalized():
    _, calendar = _synthetic_closes(n_days=400, n_names=6, seed=0)
    market_cap = _constant_market_cap(calendar, n_names=6)

    weights = mod.build_size_weights(market_cap, calendar, n_bins=3)
    active = weights[weights.abs().sum(axis=1) > 0]
    assert len(active) > 0
    # Every active (rebalance) row is dollar-neutral and gross-normalized to 1.
    assert np.allclose(active.abs().sum(axis=1), 1.0)

    row = active.iloc[0]
    # terciles of 6 names -> 2 small (long) / 2 big (short)
    assert row["S0"] == 0.25
    assert row["S1"] == 0.25
    assert row["S4"] == -0.25
    assert row["S5"] == -0.25
    assert row["S2"] == 0.0
    assert row["S3"] == 0.0


def test_build_size_weights_rebalance_rows_are_month_ends_without_interim_hold():
    """Documents the committed runner's *actual* holding behavior.

    The module docstring / pre-registration say positions are "held until the
    next monthly rebalance (ffill between rebalances)", but ``build_size_weights``
    initialises the frame to ``0.0`` and then calls ``ffill()`` -- a no-op,
    because a 0.0-initialised frame has no NaNs to propagate. So in the committed
    runner the weights are nonzero only on the month-end rebalance rows (a
    one-day hold per month via the engine's ``shift(1)``), NOT held between
    rebalances. This test pins the actual behavior so any future fix is a
    deliberate, reviewed change; see NEXT_TASK.md for the maintainer decision.
    """
    _, calendar = _synthetic_closes(n_days=400, n_names=6, seed=0)
    market_cap = _constant_market_cap(calendar, n_names=6)

    weights = mod.build_size_weights(market_cap, calendar, n_bins=3)
    active = weights[weights.abs().sum(axis=1) > 0]

    # Nonzero rows are exactly the month-end rebalance dates.
    month_ends = pd.DatetimeIndex(
        calendar.to_series().groupby(calendar.to_series().dt.to_period("M")).last().values
    )
    assert set(active.index) == set(month_ends)
    # The day after a rebalance carries no position (no interim hold).
    first_rd = active.index[0]
    next_day = calendar[calendar.get_loc(first_rd) + 1]
    assert weights.loc[next_day].abs().sum() == 0.0
    # Active rows are still dollar-neutral and gross-normalized to 1.
    assert np.allclose(active.abs().sum(axis=1), 1.0)


def test_build_size_weights_skips_when_too_few_names():
    _, calendar = _synthetic_closes(n_days=400, n_names=6, seed=0)
    market_cap = _constant_market_cap(calendar, n_names=3)

    weights = mod.build_size_weights(market_cap, calendar, n_bins=3)
    # 3 names < n_bins * 2 = 6 -> no rebalance is ever formed.
    assert (weights.to_numpy() == 0.0).all()


def test_build_size_weights_excludes_nan_names():
    _, calendar = _synthetic_closes(n_days=400, n_names=7, seed=0)
    market_cap = _constant_market_cap(calendar, n_names=7)
    market_cap["S6"] = np.nan  # largest name missing -> excluded from the ranking

    weights = mod.build_size_weights(market_cap, calendar, n_bins=3)
    active = weights[weights.abs().sum(axis=1) > 0]
    row = active.iloc[0]
    # 6 ranked names -> bin_size 2: small = S0,S1; big = S4,S5; S6 excluded.
    assert row["S0"] == 0.25
    assert row["S1"] == 0.25
    assert row["S4"] == -0.25
    assert row["S5"] == -0.25
    assert row["S6"] == 0.0


# --------------------------------------------------------------------------- #
# Delever-only vol scaling
# --------------------------------------------------------------------------- #
def test_scaled_size_weights_delevers_only():
    closes, calendar = _synthetic_closes(n_days=400, n_names=6, seed=2)
    market_cap = _constant_market_cap(calendar, n_names=6)
    returns = mod.returns_from_closes(closes, calendar)

    weights = mod.build_size_weights(market_cap, calendar, n_bins=3)
    raw_gross = weights.abs().sum(axis=1)
    scaled = mod.scaled_size_weights(weights, returns, 0.10)
    scaled_gross = scaled.abs().sum(axis=1)

    # scale = min(target / trailing vol, 1) <= 1 -> never levers above input gross.
    assert (scaled_gross <= raw_gross + 1e-9).all()
    # input gross is 1 on active rows, so scaled gross is bounded by 1.
    assert (scaled_gross <= 1.0 + 1e-9).all()


# --------------------------------------------------------------------------- #
# Walk-forward selector
# --------------------------------------------------------------------------- #
def test_size_walk_forward_score_short_train_returns_sentinel():
    closes, calendar = _synthetic_closes(n_days=300, n_names=6, seed=3)
    market_cap = _constant_market_cap(calendar, n_names=6)
    returns = mod.returns_from_closes(closes, calendar)

    score = mod.size_walk_forward_score(
        market_cap,
        returns,
        list(closes.columns),
        calendar[:200],
        {"n_bins": 3, "vol_target": 0.10},
    )
    assert score == -999.0


def test_size_walk_forward_score_finite_on_synthetic_sample():
    closes, calendar = _synthetic_closes(n_days=800, n_names=8, seed=4)
    market_cap = _constant_market_cap(calendar, n_names=8)
    returns = mod.returns_from_closes(closes, calendar)

    score = mod.size_walk_forward_score(
        market_cap,
        returns,
        list(closes.columns),
        calendar[:500],
        {"n_bins": 3, "vol_target": 0.10},
    )
    assert np.isfinite(score)


# --------------------------------------------------------------------------- #
# OAT perturbation
# --------------------------------------------------------------------------- #
def test_perturbation_sharpes_returns_four_points():
    closes, calendar = _synthetic_closes(n_days=700, n_names=10, seed=5)
    market_cap = _constant_market_cap(calendar, n_names=10)
    returns = mod.returns_from_closes(closes, calendar)

    values = mod.perturbation_sharpes(
        market_cap,
        returns,
        list(closes.columns),
        {"n_bins": 3, "vol_target": 0.10},
        calendar[300:],
    )
    assert len(values) == 4
    assert all(np.isfinite(value) for value in values)


# --------------------------------------------------------------------------- #
# Zero-roll helper (engine input)
# --------------------------------------------------------------------------- #
def test_zero_rolls_shape_and_values():
    calendar = pd.bdate_range("2020-01-01", periods=5)
    products = ["A", "B"]
    rolls = mod.zero_rolls(calendar, products)
    assert list(rolls.columns) == products
    assert rolls.index.equals(calendar)
    assert (rolls.to_numpy() == 0.0).all()


# --------------------------------------------------------------------------- #
# Committed artifact
# --------------------------------------------------------------------------- #
def _latest_artifact() -> Path:
    runs = sorted(
        glob.glob(str(ROOT / ".experiments" / "nf_runs" / "nf_20261122_04_size_premium_*"))
    )
    if not runs:
        pytest.skip("H199 artifact not yet generated")
    return Path(runs[-1]) / "summary.json"


def test_artifact_summary_exists_and_verdict():
    with open(_latest_artifact()) as fh:
        summary = json.load(fh)
    assert summary["experiment"] == "nf_20261122_04_size_premium"
    assert summary["nf_id"] == "NF-20261122-04"
    assert summary["hypothesis"] == "H199"
    assert summary["verdict"] in {"ACCEPT", "REJECT"}
    assert summary["gates_passed"] >= 0
    assert summary["gates_total"] == 8
    assert summary["grid_size"] == 4
    assert summary["selected"]["n_bins"] in {3, 5}
    assert summary["selected"]["vol_target"] in {0.10, 0.15}
    assert summary["integrity"]["src_qtr_unchanged"] is True
    assert summary["integrity"]["gate_weakening"] is False


def test_artifact_grid_csv_has_four_rows():
    grids = glob.glob(
        str(ROOT / ".experiments" / "nf_runs" / "nf_20261122_04_size_premium_*" / "grid.csv")
    )
    if not grids:
        pytest.skip("H199 grid artifact not yet generated")
    grid = pd.read_csv(max(grids))
    assert len(grid) == 4
    assert {"n_bins", "vol_target", "wf_train_sharpe"} == set(grid.columns)


def test_artifact_has_data_meta_with_coverage():
    metas = glob.glob(
        str(ROOT / ".experiments" / "nf_runs" / "nf_20261122_04_size_premium_*" / "data_meta.json")
    )
    if not metas:
        pytest.skip("H199 data_meta artifact not yet generated")
    with open(max(metas)) as fh:
        meta = json.load(fh)
    assert meta["universe_size"] >= 1000
    assert meta["tradeable_names"] >= 100
    assert meta["pit_lag_days"] == mod.PIT_LAG_DAYS
    assert meta["cost_one_way_bps"] == 5.0
    assert meta["borrow_cost_modelled"] is False
    assert meta["shares_source"].startswith("SEC XBRL")
    assert meta["price_source"].startswith("yfinance")
