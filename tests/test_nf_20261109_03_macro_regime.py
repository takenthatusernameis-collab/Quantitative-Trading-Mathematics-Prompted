"""Focused tests for NF-20261109-03 / H175 Cross-Asset Macro Regime Timing.

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

import run_nf_20261109_03_macro_regime as mod  # noqa: E402


def _make_series(n=600, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2010-01-01", periods=n)
    hg = pd.Series(300 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, n))), index=idx)
    gc = pd.Series(2000 * np.exp(np.cumsum(rng.normal(0.0001, 0.008, n))), index=idx)
    tip = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0001, 0.006, n))), index=idx)
    ief = pd.Series(90 * np.exp(np.cumsum(rng.normal(0.00015, 0.007, n))), index=idx)
    spy_ret = pd.Series(rng.normal(0.0002, 0.01, n), index=idx)
    return hg, gc, tip, ief, spy_ret


def test_regime_signal_bounded():
    hg, gc, tip, ief, spy_ret = _make_series(400)
    sig = mod._build_regime_signal(hg, gc, tip, ief, spy_ret, 63, 1.0, 0.0, 0.15, 21)
    assert (sig >= 0.0).all()
    assert (sig <= mod.MAX_POS).all()
    assert sig.name == "SPY"


def test_regime_signal_zero_before_warmup():
    hg, gc, tip, ief, spy_ret = _make_series(200)
    lookback = 63
    sig = mod._build_regime_signal(hg, gc, tip, ief, spy_ret, lookback, 1.0, 0.0, 0.15, 21)
    # Rolling z-scores need `lookback` observations; before that, regime=0 -> signal 0.
    assert (sig.iloc[: lookback - 1] == 0.0).all()


def test_regime_hysteresis_long_then_flat():
    # Sustained, varying favorable growth regime in the middle -> long during it,
    # flat after the regime returns to neutral (constant -> z=0).
    n = 200
    idx = pd.bdate_range("2010-01-01", periods=n)
    hg = pd.Series(300.0, index=idx)
    gc = pd.Series(2000.0, index=idx)
    tip = pd.Series(100.0, index=idx)
    ief = pd.Series(90.0, index=idx)
    rng = np.random.default_rng(7)
    # Boost HG/GC with variation during 50-99 (elevated & varying growth proxy).
    hg.iloc[50:100] = 300.0 * np.exp(0.10 + rng.normal(0, 0.02, 50))
    spy_ret = pd.Series(rng.normal(0.0002, 0.01, n), index=idx)
    sig = mod._build_regime_signal(hg, gc, tip, ief, spy_ret, 10, 0.3, 0.0, 0.15, 10)

    # Long at some point during the favorable/varying regime window.
    assert (sig.iloc[55:95] > 0).any()
    # Flat once the window is fully back to neutral constant growth (z=0).
    assert (sig.iloc[110:] == 0.0).all()


def test_vol_scaling_reduces_exposure_when_vol_high():
    hg, gc, tip, ief, _ = _make_series(400)
    spy_ret_values = np.concatenate(
        [
            np.random.default_rng(42).normal(0.0002, 0.005, 300),
            np.random.default_rng(42).normal(0.0002, 0.04, 100),
        ]
    )
    spy_ret = pd.Series(spy_ret_values, index=hg.index[:400], name="spy_ret")
    sig = mod._build_regime_signal(
        hg.iloc[:400],
        gc.iloc[:400],
        tip.iloc[:400],
        ief.iloc[:400],
        spy_ret,
        10,
        0.0,
        0.0,
        0.05,
        10,
    )
    favorable = sig[sig != 0]
    if len(favorable) > 70:
        assert abs(favorable.iloc[-1]) < abs(favorable.iloc[-70])


def test_worst_regime_finite_on_sufficient_data():
    rng = np.random.default_rng(3)
    daily = pd.Series(rng.normal(0.0002, 0.01, 2000))
    w = mod._worst_regime(daily)
    assert math.isfinite(w)


def test_perturbation_min_ratio_nan_when_base_zeroish():
    hg, gc, tip, ief, spy_ret = _make_series(400)
    sig = mod._build_regime_signal(hg, gc, tip, ief, spy_ret, 63, 1.0, 0.0, 0.15, 21)
    sig_df = pd.DataFrame({"SPY": sig})
    prices = pd.DataFrame({"SPY": hg.values}, index=hg.index)
    p = mod._perturbation_check(
        prices,
        hg,
        gc,
        tip,
        ief,
        spy_ret,
        {"lookback": 63, "entry_z": 1.0, "exit_z": 0.0, "vol_target": 0.15},
        0.0,
        "2023-01-01",
    )
    assert not math.isfinite(p["min_ratio"])


def test_grid_has_expected_size():
    n = 1
    for v in mod.GRID.values():
        n *= len(v)
    assert n == 36  # 3*3*2*2


def test_constants_pre_registered():
    assert mod.NF_ID == "NF-20261109-03"
    assert mod.HYPOTHESIS == "H175"
    assert mod.START == "2010-01-01"
    assert mod.END == "2026-10-31"
    assert mod.SEED == 42
    assert mod.MAX_POS == 0.5
    assert mod.DAYS_PER_YEAR == 252


def test_entry_exit_threshold_behavior():
    hg, gc, tip, ief, spy_ret = _make_series(200)
    sig_low = mod._build_regime_signal(hg, gc, tip, ief, spy_ret, 10, 0.0, 0.0, 0.15, 10)
    sig_high = mod._build_regime_signal(hg, gc, tip, ief, spy_ret, 10, 2.0, 0.5, 0.15, 10)
    # Lower entry threshold activates at least as often as higher threshold
    assert (sig_low != 0).sum() >= (sig_high != 0).sum()


def test_long_only_no_short():
    hg, gc, tip, ief, spy_ret = _make_series(400)
    sig = mod._build_regime_signal(hg, gc, tip, ief, spy_ret, 63, 1.0, 0.0, 0.15, 21)
    assert (sig >= 0.0).all()  # long-only, never negative
