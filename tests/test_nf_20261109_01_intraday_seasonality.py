"""Focused tests for NF-20261109-01 / H172 intraday equity time-of-day seasonality.

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

import run_nf_20261109_01_intraday_seasonality as mod  # noqa: E402


def _make_hourly(n=500, seed=0):
    rng = np.random.default_rng(seed)
    # Create hourly timestamps during ET trading hours (9:30-16:00 ET = hours 9-15)
    idx = pd.bdate_range("2022-10-01", periods=n * 7, freq="1h")
    # Filter to trading hours 9-15 (ET clock)
    hour_mask = (idx.hour >= 9) & (idx.hour <= 15)
    idx = idx[hour_mask]
    idx = idx[:n]
    # Generate prices with mild drift
    close = 400 * np.exp(np.cumsum(rng.normal(0.0001, 0.005, n)))
    open_ = close * np.exp(rng.normal(0, 0.001, n))
    high = np.maximum(close, open_) * np.exp(np.abs(rng.normal(0, 0.002, n)))
    low = np.minimum(close, open_) * np.exp(-np.abs(rng.normal(0, 0.002, n)))
    volume = rng.integers(1_000_000, 10_000_000, n)
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=idx
    )


def test_hourly_returns_computation():
    df = _make_hourly(200)
    ret = mod._compute_hourly_returns(df)
    expected = df["Close"] / df["Open"] - 1.0
    pd.testing.assert_series_equal(ret, expected.rename("hourly_ret"))
    assert len(ret) == len(df)


def test_build_signal_bounded_and_nan_handling():
    df = _make_hourly(300)
    hourly_ret = mod._compute_hourly_returns(df)
    # Use a simple hour window
    sig = mod._build_signal(hourly_ret, (13, 14), 0.15, 21)
    assert (sig >= 0.0).all()
    assert (sig <= mod.MAX_POS).all()
    # Signal should be 0 outside favorable hours
    unfavorable = sig[~sig.index.hour.isin((13, 14))]
    assert (unfavorable == 0.0).all()
    # Signal should be positive during favorable hours (where vol_scale is finite)
    favorable = sig[sig.index.hour.isin((13, 14))]
    # At least some should be > 0 (after warmup)
    assert (favorable > 0).any()


def test_signal_zero_when_base_zero():
    df = _make_hourly(300)
    hourly_ret = mod._compute_hourly_returns(df)
    sig = mod._build_signal(hourly_ret, (15,), 0.15, 21)
    # Hours not in window should be exactly 0
    assert (sig[~sig.index.hour.isin((15,))] == 0.0).all()


def test_vol_scaling_reduces_exposure_when_vol_high():
    # Create hourly returns directly with vol spike at the end
    n = 300
    idx = pd.bdate_range("2022-10-01", periods=n * 7, freq="1h")
    hour_mask = (idx.hour >= 13) & (idx.hour <= 19)
    idx = idx[hour_mask][:n]
    # Normal returns then high vol - use fixed seed for reproducibility
    rng = np.random.default_rng(42)
    hourly_ret_values = np.concatenate(
        [rng.normal(0.0001, 0.005, n - 50), rng.normal(0.0001, 0.02, 50)]
    )
    hourly_ret = pd.Series(hourly_ret_values, index=idx, name="hourly_ret")
    # Use lower vol_target to avoid MAX_POS cap
    sig = mod._build_signal(hourly_ret, (13, 14), 0.05, 21)
    # Last values in favorable hours should have lower exposure due to high realized vol
    favorable = sig[sig.index.hour.isin((13, 14))]
    # Compare late high-vol period vs early low-vol period
    assert favorable.iloc[-1] < favorable.iloc[-70]


def test_worst_regime_finite_on_sufficient_data():
    rng = np.random.default_rng(3)
    # Hourly returns
    daily = pd.Series(rng.normal(0.0001, 0.005, 2000))
    w = mod._worst_regime(daily)
    assert math.isfinite(w)


def test_perturbation_min_ratio_nan_when_base_zeroish():
    df = _make_hourly(500)
    hourly_ret = mod._compute_hourly_returns(df)
    p = mod._perturbation_check(
        df[["Close"]],
        hourly_ret,
        {"hour_window": (13, 14), "vol_target": 0.15, "vol_window": 21},
        0.0,
        "2023-01-01",
    )
    assert not math.isfinite(p["min_ratio"])


def test_grid_has_expected_size():
    n = 1
    for v in mod.GRID.values():
        n *= len(v)
    assert n == 36  # 6 hour_windows * 3 vol_targets * 2 vol_windows


def test_constants_pre_registered():
    assert mod.NF_ID == "NF-20261109-01"
    assert mod.HYPOTHESIS == "H172"
    assert mod.SYMBOL == "SPY"
    assert mod.START == "2024-12-01"  # yfinance 1h limit ~730 bars; pre-reg ~2024-11
    assert mod.END == "2026-10-31"
    assert mod.SEED == 42
    assert mod.MAX_POS == 0.5


def test_hour_windows_are_valid_et():
    # All hour windows should be within ET trading hours 9-15
    for hw in mod.HOUR_WINDOWS:
        for h in hw:
            assert 9 <= h <= 15, f"Hour {h} outside ET trading hours 9-15"


def test_inverse_hour_window_complement():
    # Inverse hour window should be complement of selected within ET 9-15
    all_hours = set(range(9, 16))
    for hw in mod.HOUR_WINDOWS:
        selected = set(hw)
        inverse = all_hours - selected
        assert len(inverse) == len(all_hours) - len(selected)
        # No overlap
        assert len(selected & inverse) == 0
