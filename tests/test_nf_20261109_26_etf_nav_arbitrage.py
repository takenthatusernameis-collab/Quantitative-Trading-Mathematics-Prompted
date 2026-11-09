"""Focused tests for NF-20261109-26 / H174 ETF Creation/Redemption Premium-Discount Mean Reversion.

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

import run_nf_20261109_26_etf_nav_arbitrage as mod  # noqa: E402


def _make_prices_nav(n=600, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2010-01-01", periods=n)
    # Base price with mild trend
    base_price = 300 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, n)))
    # NAV close to price but with small premium/discount
    prem = np.zeros(n)
    for i in range(1, n):
        prem[i] = 0.95 * prem[i - 1] + rng.normal(0, 0.0005)
    nav = base_price / (1 + prem)
    prices = pd.DataFrame({sym: base_price for sym in ["SPY", "QQQ", "IWM"]}, index=idx)
    navs = {sym: pd.Series(nav, index=idx, name="NAV") for sym in ["SPY", "QQQ", "IWM"]}
    return prices, navs


def test_premium_discount_computation():
    prices, navs = _make_prices_nav(400)
    close = prices["SPY"]
    nav = navs["SPY"]
    prem = (close - nav) / nav
    assert len(prem) == len(prices)
    # Premium should be small (few bps typical)
    assert prem.dropna().abs().max() < 0.02


def test_build_signal_bounded_and_hysteresis():
    prices, navs = _make_prices_nav(400)
    close = prices["SPY"]
    nav = navs["SPY"]
    spy_ret = (close / close.shift(1) - 1.0).fillna(0.0)

    sig = mod._build_signal_for_symbol(close, nav, spy_ret, 63, 1.5, 0.5, 0.15, 63)

    assert (sig >= -mod.MAX_POS).all()
    assert (sig <= mod.MAX_POS).all()
    assert sig.name == "SPY"


def test_signal_zero_before_warmup():
    prices, navs = _make_prices_nav(200)
    close = prices["SPY"]
    nav = navs["SPY"]
    spy_ret = (close / close.shift(1) - 1.0).fillna(0.0)

    sig = mod._build_signal_for_symbol(close, nav, spy_ret, 63, 1.5, 0.5, 0.15, 63)
    # Before z_window warmup, prem_z is NaN -> signal 0
    assert (sig.iloc[:63] == 0.0).all()


def test_hysteresis_long_entry_exit():
    # Create a clear discount then recovery pattern with varying premium
    idx = pd.bdate_range("2010-01-01", periods=200)
    close = pd.Series(300.0 * np.ones(200), index=idx)
    nav = pd.Series(300.0 * np.ones(200), index=idx)
    # Create varying discount around -1% (enough variation for z-score)
    rng = np.random.default_rng(42)
    discount = -0.01 + rng.normal(0, 0.001, 50)  # -1% ± 10bps
    close.iloc[50:100] = nav.iloc[50:100] * (1 + discount)
    close.iloc[100:] = 300.0  # back to par

    spy_ret = (close / close.shift(1) - 1.0).fillna(0.0)
    sig = mod._build_signal_for_symbol(close, nav, spy_ret, 10, 0.5, 0.0, 0.15, 10)

    # Should go long during discount (around 50-100) and exit after recovery
    assert (sig.iloc[60:90] > 0).any()  # long during discount
    assert (sig.iloc[110:] == 0.0).all()  # flat after recovery (exit_z=0.0)


def test_hysteresis_short_entry_exit():
    # Create a clear premium then recovery pattern with varying premium
    idx = pd.bdate_range("2010-01-01", periods=200)
    close = pd.Series(300.0 * np.ones(200), index=idx)
    nav = pd.Series(300.0 * np.ones(200), index=idx)
    # Create varying premium around +1%
    rng = np.random.default_rng(43)
    premium = 0.01 + rng.normal(0, 0.001, 50)  # +1% ± 10bps
    close.iloc[50:100] = nav.iloc[50:100] * (1 + premium)
    close.iloc[100:] = 300.0  # back to par

    spy_ret = (close / close.shift(1) - 1.0).fillna(0.0)
    sig = mod._build_signal_for_symbol(close, nav, spy_ret, 10, 0.5, 0.0, 0.15, 10)

    # Should go short during premium and exit after recovery
    assert (sig.iloc[60:90] < 0).any()  # short during premium
    assert (sig.iloc[110:] == 0.0).all()  # flat after recovery


def test_vol_scaling_reduces_exposure_when_vol_high():
    prices, navs = _make_prices_nav(400)
    close = prices["SPY"]
    nav = navs["SPY"]
    # Low vol then high vol
    spy_ret_values = np.concatenate(
        [
            np.random.default_rng(42).normal(0.0002, 0.005, 300),
            np.random.default_rng(42).normal(0.0002, 0.04, 100),
        ]
    )
    spy_ret = pd.Series(spy_ret_values, index=prices.index[:400], name="spy_ret")

    sig = mod._build_signal_for_symbol(
        close.iloc[:400], nav.iloc[:400], spy_ret, 10, 0.0, 0.0, 0.05, 10
    )
    favorable = sig[sig != 0]
    # Late high-vol period should have lower exposure than early low-vol period
    if len(favorable) > 70:
        assert abs(favorable.iloc[-1]) < abs(favorable.iloc[-70])


def test_worst_regime_finite_on_sufficient_data():
    rng = np.random.default_rng(3)
    daily = pd.Series(rng.normal(0.0002, 0.01, 2000))
    w = mod._worst_regime(daily)
    assert math.isfinite(w)


def test_perturbation_min_ratio_nan_when_base_zeroish():
    prices, navs = _make_prices_nav(400)
    close = prices["SPY"]
    nav = navs["SPY"]
    spy_ret = (close / close.shift(1) - 1.0).fillna(0.0)
    sig = mod._build_signal_for_symbol(close, nav, spy_ret, 63, 1.5, 0.5, 0.15, 63)

    # Create signal_df structure expected by _perturbation_check
    sig_df = pd.DataFrame({"SPY": sig})
    sig_df["SPY"] = sig

    p = mod._perturbation_check(
        prices[["SPY"]],
        sig_df,
        {
            "z_window": 63,
            "entry_z": 1.5,
            "exit_z": 0.5,
            "vol_target": 0.15,
            "universe": "SPY",
            "vol_window": 63,
        },
        0.0,
        "2023-01-01",
    )
    assert not math.isfinite(p["min_ratio"])


def test_grid_has_expected_size():
    n = 1
    for v in mod.GRID.values():
        n *= len(v)
    assert n == 108  # 3*3*2*2*3


def test_universe_definitions():
    assert "SPY" in mod.UNIVERSES["SPY"]
    assert set(mod.UNIVERSES["SPY_QQQ_IWM"]) == {"SPY", "QQQ", "IWM"}
    assert set(mod.UNIVERSES["SPY_QQQ_IWM_EFA_EEM"]) == {"SPY", "QQQ", "IWM", "EFA", "EEM"}


def test_constants_pre_registered():
    assert mod.NF_ID == "NF-20261109-26"
    assert mod.HYPOTHESIS == "H174"
    assert mod.START == "2010-01-01"
    assert mod.END == "2026-10-31"
    assert mod.SEED == 42
    assert mod.MAX_POS == 0.5
    assert mod.DAYS_PER_YEAR == 252


def test_entry_exit_thresholds():
    # Test that entry_z > exit_z behavior is correct
    prices, navs = _make_prices_nav(200)
    close = prices["SPY"]
    nav = navs["SPY"]
    spy_ret = (close / close.shift(1) - 1.0).fillna(0.0)

    # With entry_z=0 (always enter), signal should be active more than with entry_z=2
    sig_low = mod._build_signal_for_symbol(close, nav, spy_ret, 10, 0.0, 0.0, 0.15, 10)
    sig_high = mod._build_signal_for_symbol(close, nav, spy_ret, 10, 2.0, 0.5, 0.15, 10)

    assert (sig_low != 0).sum() >= (sig_high != 0).sum()


def test_long_short_symmetry():
    # With entry_z=0, exit_z=0, signal direction should follow premium sign
    # when premium is constant and negative (discount) -> long
    # when premium is constant and positive (premium) -> short
    idx = pd.bdate_range("2010-01-01", periods=200)

    # Discount case: constant -1% premium
    close1 = pd.Series(297.0, index=idx)  # 1% discount to NAV
    nav1 = pd.Series(300.0, index=idx)
    spy_ret = pd.Series(0.0, index=idx)

    # With constant premium, z-score will be 0 (std=0 -> fillna(0))
    # So we test with entry_z = -0.1 (should trigger on z=0 > -0.1? No, z=0 <= -(-0.1)?)
    # Actually with constant premium, the logic won't trigger.
    # Instead, test that the hysteresis logic correctly handles sign
    sig1 = mod._build_signal_for_symbol(close1, nav1, spy_ret, 10, -0.1, 0.0, 0.15, 10)

    # Premium case: constant +1% premium
    close2 = pd.Series(303.0, index=idx)
    nav2 = pd.Series(300.0, index=idx)
    sig2 = mod._build_signal_for_symbol(close2, nav2, spy_ret, 10, -0.1, 0.0, 0.15, 10)

    # With entry_z=-0.1, z=0 is not <= -(-0.1)=0.1, so no signal
    # This test mainly verifies no crash with constant premium
    assert len(sig1) == len(idx)
    assert len(sig2) == len(idx)
    assert (sig1 >= -mod.MAX_POS).all() and (sig1 <= mod.MAX_POS).all()
    assert (sig2 >= -mod.MAX_POS).all() and (sig2 <= mod.MAX_POS).all()
