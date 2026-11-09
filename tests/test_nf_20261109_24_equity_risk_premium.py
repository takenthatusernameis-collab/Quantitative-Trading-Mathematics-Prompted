"""Focused tests for NF-20261109-24 / H173 Equity Risk Premium / Fed Model SPY timing.

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

import run_nf_20261109_24_equity_risk_premium as mod  # noqa: E402


def _make_daily_dividends(n=600, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2010-01-01", periods=n)
    close = 400 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, n)))
    # Quarterly-ish dividends: every ~63 days a small dividend.
    dividend = pd.Series(0.0, index=idx)
    dividend.iloc[::63] = 1.0
    return pd.DataFrame({"Close": close}, index=idx), dividend


def _make_tnx(n=600, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2010-01-01", periods=n)
    # TNX in percent, roughly 1.5-5%.
    tnx = 3.0 + np.cumsum(rng.normal(0.0, 0.05, n))
    tnx = np.clip(tnx, 0.5, 7.0)
    return pd.DataFrame({"Close": tnx}, index=idx)


def test_trailing_div_yield_computation():
    prices, dividends = _make_daily_dividends(400)
    dy = mod._compute_trailing_div_yield(prices, dividends, lookback=63)
    assert len(dy) == len(prices)
    # Dividend yield should be >= 0
    assert (dy.dropna() >= 0).all()
    # Warmup: first lookback-1 values should be NaN (min_periods=lookback)
    assert dy.iloc[:62].isna().all()
    assert math.isfinite(dy.iloc[63])


def test_erp_computation():
    prices, dividends = _make_daily_dividends(400)
    tnx = _make_tnx(400)
    dy = mod._compute_trailing_div_yield(prices, dividends, lookback=63)
    erp = mod._compute_erp(dy, tnx["Close"])
    assert len(erp) == len(prices)
    # ERP = div_yield - tnx/100; can be negative.
    assert erp.dropna().abs().max() < 1.0


def test_build_signal_bounded_and_entry_logic():
    prices, dividends = _make_daily_dividends(400)
    tnx = _make_tnx(400)
    dy = mod._compute_trailing_div_yield(prices, dividends, lookback=63)
    erp = mod._compute_erp(dy, tnx["Close"])
    spy_ret = (prices["Close"] / prices["Close"].shift(1) - 1.0).fillna(0.0)
    sig = mod._build_signal(erp, spy_ret, 63, 126, 0.5, 0.15, 63)
    assert (sig >= 0.0).all()
    assert (sig <= mod.MAX_POS).all()
    # Signal > 0 only where erp_z >= entry_z (after warmup).
    erp_mean = erp.rolling(126, min_periods=126).mean()
    erp_std = erp.rolling(126, min_periods=126).std(ddof=0)
    erp_z = (erp - erp_mean) / erp_std.replace(0, np.nan)
    eligible = erp_z >= 0.5
    active = sig > 0
    # Every active bar must have erp_z >= entry_z.
    assert (active[eligible == False] == 0.0).all()  # noqa: E712


def test_signal_zero_before_warmup():
    prices, dividends = _make_daily_dividends(200)
    tnx = _make_tnx(200)
    dy = mod._compute_trailing_div_yield(prices, dividends, lookback=63)
    erp = mod._compute_erp(dy, tnx["Close"])
    spy_ret = (prices["Close"] / prices["Close"].shift(1) - 1.0).fillna(0.0)
    sig = mod._build_signal(erp, spy_ret, 63, 126, 0.5, 0.15, 63)
    # Before z_window warmup, erp_z is NaN -> signal 0.
    assert (sig.iloc[:126] == 0.0).all()


def test_vol_scaling_reduces_exposure_when_vol_high():
    prices, dividends = _make_daily_dividends(400)
    tnx = _make_tnx(400)
    dy = mod._compute_trailing_div_yield(prices, dividends, lookback=63)
    erp = mod._compute_erp(dy, tnx["Close"])
    # Low vol then high vol.
    spy_ret_values = np.concatenate(
        [
            np.random.default_rng(42).normal(0.0002, 0.005, 300),
            np.random.default_rng(42).normal(0.0002, 0.04, 100),
        ]
    )
    spy_ret = pd.Series(spy_ret_values, index=prices.index[:400], name="spy_ret")
    sig = mod._build_signal(erp.iloc[:400], spy_ret, 63, 63, 0.0, 0.05, 63)
    favorable = sig[sig > 0]
    # Late high-vol period should have lower exposure than early low-vol period.
    assert favorable.iloc[-1] < favorable.iloc[-70]


def test_worst_regime_finite_on_sufficient_data():
    rng = np.random.default_rng(3)
    daily = pd.Series(rng.normal(0.0002, 0.01, 2000))
    w = mod._worst_regime(daily)
    assert math.isfinite(w)


def test_perturbation_min_ratio_nan_when_base_zeroish():
    prices, dividends = _make_daily_dividends(400)
    tnx = _make_tnx(400)
    dy = mod._compute_trailing_div_yield(prices, dividends, lookback=63)
    erp = mod._compute_erp(dy, tnx["Close"])
    spy_ret = (prices["Close"] / prices["Close"].shift(1) - 1.0).fillna(0.0)
    sig = mod._build_signal(erp, spy_ret, 63, 126, 0.5, 0.15, 63)
    sig_df = sig.to_frame(name="SPY")
    sig_df["erp"] = erp
    sig_df["spy_ret"] = spy_ret
    p = mod._perturbation_check(
        prices[["Close"]],
        sig_df,
        {"div_lookback": 63, "z_window": 126, "entry_z": 0.5, "vol_target": 0.15, "vol_window": 63},
        0.0,
        "2023-01-01",
    )
    assert not math.isfinite(p["min_ratio"])


def test_grid_has_expected_size():
    n = 1
    for v in mod.GRID.values():
        n *= len(v)
    assert n == 36  # 2*2*3*3


def test_constants_pre_registered():
    assert mod.NF_ID == "NF-20261109-24"
    assert mod.HYPOTHESIS == "H173"
    assert mod.SPY_SYMBOL == "SPY"
    assert mod.TNX_SYMBOL == "^TNX"
    assert mod.START == "2010-01-01"
    assert mod.END == "2026-10-31"
    assert mod.SEED == 42
    assert mod.MAX_POS == 0.5


def test_entry_threshold_complement():
    # With entry_z very high, few/no bars active; with entry_z very low, more active.
    prices, dividends = _make_daily_dividends(400)
    tnx = _make_tnx(400)
    dy = mod._compute_trailing_div_yield(prices, dividends, lookback=63)
    erp = mod._compute_erp(dy, tnx["Close"])
    spy_ret = (prices["Close"] / prices["Close"].shift(1) - 1.0).fillna(0.0)
    sig_low = mod._build_signal(erp, spy_ret, 63, 126, -3.0, 0.15, 63)
    sig_high = mod._build_signal(erp, spy_ret, 63, 126, 3.0, 0.15, 63)
    assert (sig_low > 0).sum() >= (sig_high > 0).sum()
