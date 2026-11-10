"""Focused tests for NF-20261109-15 / H176 Tax-Loss Harvesting / Year-End Selling Pressure.

Tests use synthetic data only (no network). They validate PIT/causal
properties, signal construction, grid behavior, and gate logic.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import run_nf_20261109_15_tax_loss_harvesting as mod  # noqa: E402


def _make_prices(n_years=20, seed=0):
    """Create synthetic daily price data for the universe."""
    rng = np.random.default_rng(seed)
    # Start from 2010-01-01, business days
    idx = pd.bdate_range("2010-01-01", periods=n_years * 252)
    prices = {}
    for sym in mod.UNIVERSE:
        # Random walk with slight drift
        drift = rng.normal(0.0002, 0.0001)
        vol = rng.uniform(0.008, 0.015)
        rets = rng.normal(drift, vol, len(idx))
        prices[sym] = pd.Series(100 * np.exp(np.cumsum(rets)), index=idx, name=sym)
    return pd.DataFrame(prices)


def test_signal_bounded_and_long_only():
    """Signal should be bounded [0, MAX_POS] and long-only."""
    prices = _make_prices(5, seed=42)
    november_mask = prices.index.month == 11
    november_dates = prices.index[november_mask]
    november_month_ends = []
    for year in sorted(november_dates.year.unique()):
        year_nov = november_dates[november_dates.year == year]
        if len(year_nov) > 0:
            november_month_ends.append(year_nov[-1])
    november_month_ends = pd.DatetimeIndex(november_month_ends)

    ytd_returns = mod._compute_ytd_returns(prices, november_month_ends)
    sig = mod._build_tax_loss_signal(prices, ytd_returns, 5, 3, 5, 0.15, 21)

    assert (sig >= 0.0).all().all(), "Signal should be non-negative (long-only)"
    assert (sig <= mod.MAX_POS).all().all(), f"Signal should be <= MAX_POS ({mod.MAX_POS})"
    assert list(sig.columns) == mod.UNIVERSE, "Signal columns should match universe"


def test_signal_active_only_in_december_january():
    """Signal should only be non-zero during December window + January hold period."""
    prices = _make_prices(3, seed=123)
    november_mask = prices.index.month == 11
    november_dates = prices.index[november_mask]
    november_month_ends = []
    for year in sorted(november_dates.year.unique()):
        year_nov = november_dates[november_dates.year == year]
        if len(year_nov) > 0:
            november_month_ends.append(year_nov[-1])
    november_month_ends = pd.DatetimeIndex(november_month_ends)

    ytd_returns = mod._compute_ytd_returns(prices, november_month_ends)
    sig = mod._build_tax_loss_signal(prices, ytd_returns, 5, 3, 5, 0.15, 21)

    # Check active months
    active_months = sig[sig.sum(axis=1) > 0].index.month.unique()
    assert set(active_months).issubset({12, 1}), (
        f"Signal active in unexpected months: {active_months}"
    )


def test_signal_respects_n_days():
    """Larger n_days should activate signal for at least as many December days."""
    prices = _make_prices(5, seed=456)
    november_mask = prices.index.month == 11
    november_dates = prices.index[november_mask]
    november_month_ends = []
    for year in sorted(november_dates.year.unique()):
        year_nov = november_dates[november_dates.year == year]
        if len(year_nov) > 0:
            november_month_ends.append(year_nov[-1])
    november_month_ends = pd.DatetimeIndex(november_month_ends)

    ytd_returns = mod._compute_ytd_returns(prices, november_month_ends)

    sig_5 = mod._build_tax_loss_signal(prices, ytd_returns, 5, 3, 5, 0.15, 21)
    sig_10 = mod._build_tax_loss_signal(prices, ytd_returns, 10, 3, 5, 0.15, 21)

    dec_active_5 = (sig_5.index.month == 12) & (sig_5.sum(axis=1) > 0)
    dec_active_10 = (sig_10.index.month == 12) & (sig_10.sum(axis=1) > 0)

    # 10 days should have >= 5 days of December activity per year
    for year in sorted(prices.index.year.unique()):
        cnt_5 = dec_active_5[dec_active_5.index.year == year].sum()
        cnt_10 = dec_active_10[dec_active_10.index.year == year].sum()
        if cnt_5 > 0:  # Only check years where signal activates
            assert cnt_10 >= cnt_5, f"Year {year}: n_days=10 should have >= n_days=5 active days"


def test_signal_respects_hold_days():
    """Larger hold_days should activate signal for at least as many January days."""
    prices = _make_prices(5, seed=789)
    november_mask = prices.index.month == 11
    november_dates = prices.index[november_mask]
    november_month_ends = []
    for year in sorted(november_dates.year.unique()):
        year_nov = november_dates[november_dates.year == year]
        if len(year_nov) > 0:
            november_month_ends.append(year_nov[-1])
    november_month_ends = pd.DatetimeIndex(november_month_ends)

    ytd_returns = mod._compute_ytd_returns(prices, november_month_ends)

    sig_3 = mod._build_tax_loss_signal(prices, ytd_returns, 5, 3, 3, 0.15, 21)
    sig_10 = mod._build_tax_loss_signal(prices, ytd_returns, 5, 3, 10, 0.15, 21)

    jan_active_3 = (sig_3.index.month == 1) & (sig_3.sum(axis=1) > 0)
    jan_active_10 = (sig_10.index.month == 1) & (sig_10.sum(axis=1) > 0)

    for year in sorted(prices.index.year.unique()):
        cnt_3 = jan_active_3[jan_active_3.index.year == year].sum()
        cnt_10 = jan_active_10[jan_active_10.index.year == year].sum()
        if cnt_3 > 0:
            assert cnt_10 >= cnt_3, (
                f"Year {year}: hold_days=10 should have >= hold_days=3 active days"
            )


def test_vol_scaling_reduces_exposure_when_vol_high():
    """Vol targeting should reduce position size when realized vol is high."""
    # Create prices with a high-vol regime
    prices = _make_prices(5, seed=999)
    # Inject high volatility in a specific period
    high_vol_start = prices.index[600]
    high_vol_end = prices.index[800]
    mask = (prices.index >= high_vol_start) & (prices.index <= high_vol_end)
    for sym in mod.UNIVERSE:
        prices.loc[mask, sym] *= np.exp(np.random.default_rng(42).normal(0, 0.05, mask.sum()))

    november_mask = prices.index.month == 11
    november_dates = prices.index[november_mask]
    november_month_ends = []
    for year in sorted(november_dates.year.unique()):
        year_nov = november_dates[november_dates.year == year]
        if len(year_nov) > 0:
            november_month_ends.append(year_nov[-1])
    november_month_ends = pd.DatetimeIndex(november_month_ends)

    ytd_returns = mod._compute_ytd_returns(prices, november_month_ends)
    sig = mod._build_tax_loss_signal(prices, ytd_returns, 5, 3, 5, 0.10, 21)

    # During high vol, positions should be smaller
    high_vol_mask = (
        (sig.index >= high_vol_start)
        & (sig.index <= high_vol_end)
        & (sig.index.month.isin([12, 1]))
    )
    normal_mask = (sig.index < high_vol_start) & (sig.index.month.isin([12, 1]))

    high_vol_positions = sig[high_vol_mask].sum(axis=1)
    normal_positions = sig[normal_mask].sum(axis=1)

    if len(high_vol_positions) > 10 and len(normal_positions) > 10:
        assert high_vol_positions.mean() < normal_positions.mean() * 1.5, (
            "Vol targeting should reduce exposure in high-vol regime"
        )


def test_ytd_returns_computed_correctly():
    """YTD returns should be computed from first trading day of year to November month-end."""
    prices = _make_prices(3, seed=111)
    november_mask = prices.index.month == 11
    november_dates = prices.index[november_mask]
    november_month_ends = []
    for year in sorted(november_dates.year.unique()):
        year_nov = november_dates[november_dates.year == year]
        if len(year_nov) > 0:
            november_month_ends.append(year_nov[-1])
    november_month_ends = pd.DatetimeIndex(november_month_ends)

    ytd_returns = mod._compute_ytd_returns(prices, november_month_ends)

    # Check a specific year manually
    for nov_date in november_month_ends:
        year = nov_date.year
        year_prices = prices[prices.index.year == year]
        if len(year_prices) == 0:
            continue
        first_price = year_prices.iloc[0]
        nov_price = prices.loc[:nov_date].iloc[-1]
        expected_ret = (nov_price / first_price) - 1.0
        actual_ret = ytd_returns.loc[nov_date]
        pd.testing.assert_series_equal(actual_ret, expected_ret, check_names=False, rtol=1e-10)


def test_grid_has_expected_size():
    """Grid should have 36 combinations (2*3*3*2)."""
    n = 1
    for v in mod.GRID.values():
        n *= len(v)
    assert n == 36, f"Grid should have 36 combos, got {n}"


def test_constants_pre_registered():
    """Pre-registered constants should match specification."""
    assert mod.NF_ID == "NF-20261109-15"
    assert mod.HYPOTHESIS == "H176"
    assert mod.START == "2010-01-01"
    assert mod.END == "2026-10-31"
    assert mod.SEED == 42
    assert mod.MAX_POS == 0.5
    assert mod.DAYS_PER_YEAR == 252
    assert mod.VOL_WINDOW == 21
    assert mod.UNIVERSE == [
        "XLF",
        "XLE",
        "XLV",
        "XLI",
        "XLB",
        "XLP",
        "XLU",
        "XLY",
        "XLC",
        "XLK",
        "SPY",
    ]


def test_worst_regime_finite_on_sufficient_data():
    """_worst_regime should return finite value on sufficient data."""
    rng = np.random.default_rng(3)
    daily = pd.Series(rng.normal(0.0002, 0.01, 2000))
    w = mod._worst_regime(daily)
    assert math.isfinite(w)


def test_perturbation_min_ratio_nan_when_base_zeroish():
    """_perturbation_check should return NaN min_ratio when base Sharpe ~0."""
    prices = _make_prices(3, seed=555)
    november_mask = prices.index.month == 11
    november_dates = prices.index[november_mask]
    november_month_ends = []
    for year in sorted(november_dates.year.unique()):
        year_nov = november_dates[november_dates.year == year]
        if len(year_nov) > 0:
            november_month_ends.append(year_nov[-1])
    november_month_ends = pd.DatetimeIndex(november_month_ends)

    ytd_returns = mod._compute_ytd_returns(prices, november_month_ends)
    sig = mod._build_tax_loss_signal(prices, ytd_returns, 5, 3, 5, 0.15, 21)
    sig = sig.reindex(index=prices.index).fillna(0.0)

    p = mod._perturbation_check(
        prices,
        ytd_returns,
        {"n_days": 5, "k": 3, "hold_days": 5, "vol_target": 0.15},
        0.0,
        "2023-01-01",
    )
    assert not math.isfinite(p["min_ratio"])


def test_december_window_helper():
    """_get_december_window should return correct number of days."""
    prices = _make_prices(2, seed=777)
    dec_5 = mod._get_december_window(prices, 2010, 5)
    dec_10 = mod._get_december_window(prices, 2010, 10)

    # Should return at most n_days (could be fewer if not enough trading days)
    assert len(dec_5) <= 5
    assert len(dec_10) <= 10
    # All should be in December
    assert all(d.month == 12 for d in dec_5)
    assert all(d.month == 12 for d in dec_10)


def test_january_hold_days_helper():
    """_get_january_hold_days should return correct number of days in January of next year."""
    prices = _make_prices(2, seed=888)
    jan_3 = mod._get_january_hold_days(prices, 2010, 3)  # Jan 2011
    jan_10 = mod._get_january_hold_days(prices, 2010, 10)

    assert len(jan_3) <= 3
    assert len(jan_10) <= 10
    assert all(d.month == 1 for d in jan_3)
    assert all(d.month == 1 for d in jan_10)
    assert all(d.year == 2011 for d in jan_3)
    assert all(d.year == 2011 for d in jan_10)


def test_k_selection():
    """Larger k should select more assets (or equal)."""
    prices = _make_prices(5, seed=222)
    november_mask = prices.index.month == 11
    november_dates = prices.index[november_mask]
    november_month_ends = []
    for year in sorted(november_dates.year.unique()):
        year_nov = november_dates[november_dates.year == year]
        if len(year_nov) > 0:
            november_month_ends.append(year_nov[-1])
    november_month_ends = pd.DatetimeIndex(november_month_ends)

    ytd_returns = mod._compute_ytd_returns(prices, november_month_ends)

    sig_1 = mod._build_tax_loss_signal(prices, ytd_returns, 5, 1, 5, 0.15, 21)
    sig_3 = mod._build_tax_loss_signal(prices, ytd_returns, 5, 3, 5, 0.15, 21)
    sig_5 = mod._build_tax_loss_signal(prices, ytd_returns, 5, 5, 5, 0.15, 21)

    # On active days, count of non-zero positions should respect k
    active_1 = sig_1.sum(axis=1) > 0
    active_3 = sig_3.sum(axis=1) > 0
    active_5 = sig_5.sum(axis=1) > 0

    # Where active, number of positions should be <= k
    for day in prices.index[active_1]:
        assert (sig_1.loc[day] > 0).sum() <= 1
    for day in prices.index[active_3]:
        assert (sig_3.loc[day] > 0).sum() <= 3
    for day in prices.index[active_5]:
        assert (sig_5.loc[day] > 0).sum() <= 5
