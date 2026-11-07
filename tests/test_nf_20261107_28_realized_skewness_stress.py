"""Tests for NF-20261107-28 / H128: SPY timing from realized skewness stress."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "run_nf_20261107_28_realized_skewness_stress",
    ROOT / "run_nf_20261107_28_realized_skewness_stress.py",
)
assert _SPEC and _SPEC.loader
MOD = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = MOD
_SPEC.loader.exec_module(MOD)


def _series(n=700, seed=7):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2014-01-02", periods=n)
    spy = 200 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, n)))
    return pd.Series(spy, index=idx)


def test_skew_z_finite():
    spy = _series()
    z = MOD.realized_skew_z(spy, 63, 63)
    assert np.isfinite(z.dropna()).all()


def test_skew_z_past_only():
    spy = _series()
    z1 = MOD.realized_skew_z(spy, 63, 63)
    spy2 = spy.copy()
    spy2.iloc[-1] = spy2.iloc[-1] * 1.5
    z2 = MOD.realized_skew_z(spy2, 63, 63)
    pd.testing.assert_series_equal(z1.iloc[:-90], z2.iloc[:-90])


def test_build_exposure_bounded():
    idx = pd.bdate_range("2020-01-01", periods=120)
    z = pd.Series(np.random.default_rng(0).normal(0, 1, 120), index=idx)
    e = MOD.build_exposure(z, 0.0, -0.5, 0.10)
    assert (e >= -1e-12).all()
    assert (e <= 0.10 + 1e-12).all()


def test_build_exposure_enters_high_skew_exits_low():
    idx = pd.bdate_range("2020-01-01", periods=60)
    # high skew -> long, low skew -> flat, then above entry_z re-enters long
    z = pd.Series([1.0] * 20 + [-1.0] * 20 + [0.2] * 20, index=idx)
    e = MOD.build_exposure(z, entry_z=0.0, exit_z=-0.5, vol_target=0.10)
    assert e.iloc[0] > 0
    assert e.iloc[20] == 0.0
    assert e.iloc[40] > 0


def test_run_one_finite_outputs():
    spy = _series()
    prices = pd.DataFrame({MOD.SPY: spy})
    res = MOD.run_one(
        prices,
        {
            "lookback": 63,
            "z_window": 63,
            "entry_z": 0.0,
            "exit_z": -0.5,
            "vol_target": 0.10,
        },
    )
    bt = res["backtest"]
    assert np.isfinite(bt.returns.fillna(0.0)).all()
    assert np.isfinite(bt.equity_curve).all()
    assert (bt.equity_curve > 0).all()


def test_metrics_empty_mask_safe():
    spy = _series(300)
    prices = pd.DataFrame({MOD.SPY: spy})
    res = MOD.run_one(
        prices,
        {
            "lookback": 63,
            "z_window": 63,
            "entry_z": 0.0,
            "exit_z": -0.5,
            "vol_target": 0.10,
        },
    )
    mask = pd.Series(False, index=prices.index)
    met = MOD.metrics_from(res["backtest"], mask)
    assert met["trades"] == 0


def test_wf_stability_range():
    spy = _series(500)
    prices = pd.DataFrame({MOD.SPY: spy})
    train_mask = pd.Series(True, index=prices.index)
    wf = MOD.wf_stability(
        prices,
        {
            "lookback": 63,
            "z_window": 63,
            "entry_z": 0.0,
            "exit_z": -0.5,
            "vol_target": 0.10,
        },
        train_mask,
    )
    assert 0.0 <= wf <= 1.0


def test_splits_cover_index():
    idx = pd.bdate_range("2015-01-01", periods=300)
    tr, va, te = MOD._splits(idx)
    assert (tr | va | te).all()
    assert not (tr & va).any()
