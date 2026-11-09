"""Focused tests for NF-20261109-21 / H171 yield curve slope regime SPY timing.

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

import run_nf_20261109_21_yield_curve_slope_spy as mod  # noqa: E402


def _make_close(n=800, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2015-01-01", periods=n)
    # yields in percent, positive
    tyx = 3.0 + np.cumsum(rng.normal(0, 0.02, n))
    fvx = 2.0 + np.cumsum(rng.normal(0, 0.02, n))
    tyx = np.clip(tyx, 0.5, 6.0)
    fvx = np.clip(fvx, 0.2, 5.5)
    spy = 200 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
    return pd.DataFrame({"^TYX": tyx, "^FVX": fvx, "SPY": spy}, index=idx)


def test_slope_is_tyx_minus_fvx():
    close = _make_close(300)
    slope = mod._build_slope(close)
    expected = close["^TYX"] - close["^FVX"]
    pd.testing.assert_series_equal(slope, expected.rename("slope"))


def test_zscore_past_only_warmup_nan():
    close = _make_close(400)
    slope = mod._build_slope(close)
    w = 63
    z = mod._zscore(slope, w)
    # first w-1 should be NaN due to min_periods
    assert z.iloc[: w - 1].isna().all()
    assert math.isfinite(float(z.iloc[w + 5]))


def test_signal_bounded_and_nan_to_zero():
    close = _make_close(400)
    slope = mod._build_slope(close)
    z = mod._zscore(slope, 126)
    sig = mod._signal_from_z(z, entry_scale=1.0, vol_target=0.15)
    assert (sig >= 0.0).all()
    assert (sig <= mod.MAX_POS).all()
    # where z is nan, signal must be 0
    assert (sig[z.isna()] == 0.0).all()


def test_negative_z_reduces_exposure():
    idx = pd.bdate_range("2020-01-01", periods=300)
    # construct slope dropping sharply at end to force negative z
    slope = pd.Series(
        np.linspace(1.0, 1.0, 200).tolist() + np.linspace(1.0, -1.0, 100).tolist(), index=idx
    )
    z = mod._zscore(slope, 126)
    sig = mod._signal_from_z(z, entry_scale=1.0, vol_target=0.15)
    # last values should be de-risked (stress from negative z)
    assert sig.iloc[-1] < 0.15
    assert sig.iloc[-1] >= 0.0


def test_inverse_regime_opposite_stress_direction():
    close = _make_close(400, seed=7)
    slope = mod._build_slope(close)
    z = mod._zscore(slope, 126)
    base = mod._signal_from_z(z, 1.0, 0.15)
    stress_inv = (z.clip(lower=0.0) / 1.0).clip(0.0, 1.0)
    inv = ((1.0 - stress_inv) * 0.15).clip(0.0, mod.MAX_POS)
    inv = inv.where(z.notna(), 0.0)
    # not identical in general
    assert not np.allclose(base.values, inv.values, equal_nan=True)


def test_worst_regime_finite_on_sufficient_data():
    rng = np.random.default_rng(3)
    daily = pd.Series(rng.normal(0.0002, 0.01, 500))
    w = mod._worst_regime(daily)
    assert math.isfinite(w)


def test_perturbation_min_ratio_nan_when_base_zeroish():
    close = _make_close(500)
    slope = mod._build_slope(close)
    p = mod._perturbation_check(
        close, slope, {"z_window": 126, "entry_scale": 1.0, "vol_target": 0.15}, 0.0
    )
    assert not math.isfinite(p["min_ratio"])


def test_grid_has_expected_size():
    n = 1
    for v in mod.GRID.values():
        n *= len(v)
    assert n == 8


def test_constants_pre_registered():
    assert mod.NF_ID == "NF-20261109-21"
    assert mod.HYPOTHESIS == "H171"
    assert mod.TRAIN_END == "2019-12-31"
    assert mod.VAL_END == "2022-12-31"
    assert mod.END == "2026-10-31"
    assert mod.SEED == 42
    assert mod.MAX_POS == 0.5
