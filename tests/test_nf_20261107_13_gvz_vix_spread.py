"""Tests for NF-20261107-13 / H126: SPY timing from GVZ-VIX implied-vol spread."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "run_nf_20261107_13_gvz_vix_spread",
    ROOT / "run_nf_20261107_13_gvz_vix_spread.py",
)
assert _SPEC and _SPEC.loader
MOD = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = MOD
_SPEC.loader.exec_module(MOD)


def _series(n=600, seed=7):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2014-01-02", periods=n)
    gvz = 18 + rng.normal(0.0, 3.0, n)
    vix = 15 + rng.normal(0.0, 3.0, n)
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, n)))
    return (
        pd.Series(gvz, index=idx),
        pd.Series(vix, index=idx),
        pd.Series(spy, index=idx),
    )


def test_spread_z_finite():
    gvz, vix, _ = _series()
    z = MOD.spread_z(gvz, vix, 21)
    assert np.isfinite(z.dropna()).all()


def test_spread_z_past_only():
    gvz, vix, _ = _series()
    z1 = MOD.spread_z(gvz, vix, 21)
    gvz2 = gvz.copy()
    gvz2.iloc[-1] = gvz2.iloc[-1] * 3.0
    z2 = MOD.spread_z(gvz2, vix, 21)
    pd.testing.assert_series_equal(z1.iloc[:-21], z2.iloc[:-21])


def test_build_exposure_bounded():
    idx = pd.bdate_range("2020-01-01", periods=100)
    z = pd.Series(np.random.default_rng(0).normal(0, 1, 100), index=idx)
    e = MOD.build_exposure(z, 1.5, 0.5, 0.10)
    assert (e >= -1e-12).all()
    assert (e <= 0.10 + 1e-12).all()


def test_build_exposure_exits_high_stress_reenters_low():
    idx = pd.bdate_range("2020-01-01", periods=60)
    z = pd.Series([2.0] * 20 + [0.2] * 20 + [2.0] * 20, index=idx)
    e = MOD.build_exposure(z, entry_z=1.0, exit_z=0.5, vol_target=0.10)
    assert e.iloc[0] == 0.0
    assert e.iloc[20] > 0
    assert e.iloc[40] == 0.0


def test_run_one_finite_outputs():
    gvz, vix, spy = _series()
    prices = pd.DataFrame({MOD.SPY: spy, MOD.VIX: vix, MOD.GVZ: gvz})
    res = MOD.run_one(prices, {"window": 21, "entry_z": 1.5, "exit_z": 0.5, "vol_target": 0.10})
    bt = res["backtest"]
    assert np.isfinite(bt.returns.fillna(0.0)).all()
    assert np.isfinite(bt.equity_curve).all()
    assert (bt.equity_curve > 0).all()


def test_metrics_empty_mask_safe():
    gvz, vix, spy = _series(300)
    prices = pd.DataFrame({MOD.SPY: spy, MOD.VIX: vix, MOD.GVZ: gvz})
    res = MOD.run_one(prices, {"window": 21, "entry_z": 1.5, "exit_z": 0.5, "vol_target": 0.10})
    mask = pd.Series(False, index=prices.index)
    m = MOD.metrics_from(res["backtest"], mask)
    assert m["n"] == 0 and m["trades"] == 0


def test_gate_evaluation():
    train = {"sharpe": 1.2}
    oos = {"sharpe": 1.1, "trades": 250, "profit_factor": 1.4, "max_drawdown": -0.10}
    passed, gates = MOD.evaluate_gates(
        train,
        oos,
        0.9,
        0.4,
        {"p_value": 0.01, "information_ratio": 0.1},
        {"min_ratio_vs_optimum": 0.6},
    )
    assert passed and all(gates.values())


def test_gate_fails_on_low_sharpe():
    train = {"sharpe": 1.2}
    oos = {"sharpe": 0.5, "trades": 250, "profit_factor": 1.4, "max_drawdown": -0.10}
    passed, gates = MOD.evaluate_gates(
        train,
        oos,
        0.9,
        0.4,
        {"p_value": 0.01, "information_ratio": 0.1},
        {"min_ratio_vs_optimum": 0.6},
    )
    assert not passed
    assert not gates["sharpe"]


def test_vol_scale_bounded():
    spy_ret = pd.Series(
        np.random.default_rng(0).normal(0, 0.01, 200),
        index=pd.bdate_range("2020-01-01", periods=200),
    )
    s = MOD.vol_scale(spy_ret, 0.15)
    assert (s >= 0).all() and (s <= 1.0 + 1e-12).all()


def test_ablations_finite():
    gvz, vix, spy = _series(600)
    prices = pd.DataFrame({MOD.SPY: spy, MOD.VIX: vix, MOD.GVZ: gvz})
    mask = pd.Series(True, index=prices.index)
    mask.iloc[:300] = False
    ab = MOD._ablations(
        prices,
        {"window": 21, "entry_z": 1.5, "exit_z": 0.5, "vol_target": 0.10},
        mask,
    )
    assert "buy_hold_spy" in ab and "random_exposure_matched" in ab
    assert np.isfinite(ab["buy_hold_spy"]["sharpe"])


def test_perturbation_returns_ratio():
    gvz, vix, spy = _series(500)
    prices = pd.DataFrame({MOD.SPY: spy, MOD.VIX: vix, MOD.GVZ: gvz})
    mask = pd.Series(True, index=prices.index)
    mask.iloc[:250] = False
    p = {"window": 21, "entry_z": 1.5, "exit_z": 0.5, "vol_target": 0.10}
    base = MOD.metrics_from(MOD.run_one(prices, p)["backtest"], mask)["sharpe"]
    pert = MOD._perturbation(prices, p, mask, base)
    assert "min_ratio_vs_optimum" in pert
    assert np.isfinite(pert["min_ratio_vs_optimum"])
