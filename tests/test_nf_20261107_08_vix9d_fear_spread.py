"""Tests for NF-20261107-08 / H123: SPY timing from the VIX9D/VIX front-end fear spread."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "run_nf_20261107_08_vix9d_fear_spread",
    ROOT / "run_nf_20261107_08_vix9d_fear_spread.py",
)
assert _SPEC and _SPEC.loader
MOD = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = MOD
_SPEC.loader.exec_module(MOD)


def _series(n=600, seed=7):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2014-01-02", periods=n)
    vix9d = 15 + rng.normal(0.0, 3.0, n)
    vix = 15 + rng.normal(0.0, 3.0, n)
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, n)))
    return pd.Series(vix9d, index=idx), pd.Series(vix, index=idx), pd.Series(spy, index=idx)


def test_fear_z_finite():
    vix9d, vix, spy = _series()
    z = MOD.fear_z(vix9d, vix, 21)
    assert np.isfinite(z.dropna()).all()


def test_fear_z_uses_past_only():
    vix9d, vix, spy = _series()
    z1 = MOD.fear_z(vix9d, vix, 21)
    vix9d2 = vix9d.copy()
    vix9d2.iloc[-1] = vix9d2.iloc[-1] * 3.0  # future change at end
    z2 = MOD.fear_z(vix9d2, vix, 21)
    pd.testing.assert_series_equal(z1.iloc[:-21], z2.iloc[:-21])


def test_build_exposure_bounded():
    idx = pd.bdate_range("2020-01-01", periods=100)
    z = pd.Series(np.random.default_rng(0).normal(0, 1, 100), index=idx)
    e = MOD.build_exposure(z, 1.5, 0.5, 0.10)
    assert (e >= -1e-12).all()
    assert (e <= 0.10 + 1e-12).all()


def test_build_exposure_enters_low_fear_exits_high_fear():
    idx = pd.bdate_range("2020-01-01", periods=60)
    z = pd.Series([2.0] * 20 + [0.2] * 20 + [2.0] * 20, index=idx)
    e = MOD.build_exposure(z, entry_z=1.0, exit_z=0.5, vol_target=0.10)
    # starts long (z=2.0 > entry 1.0 -> actually exits immediately), check logic:
    # in_pos starts True; z=2.0 > entry 1.0 at index 0 -> exits to flat
    assert e.iloc[0] == 0.0
    # z drops to 0.2 at index 20 (< exit_z 0.5? no, 0.2 < 0.5 so re-enters)
    assert e.iloc[20] > 0
    # z back to 2.0 at index 40 (> entry) -> flat
    assert e.iloc[40] == 0.0


def test_hysteresis_exit_only_above_entry_reenters_below_exit():
    idx = pd.bdate_range("2018-01-01", periods=260)
    z = pd.Series([0.2] * 100 + [2.0] * 40 + [0.2] * 40 + [2.0] * 80, index=idx)
    e = MOD.build_exposure(z, entry_z=1.0, exit_z=0.5, vol_target=0.10)
    # starts long (z=0.2 <= entry 1.0)
    assert e.iloc[0] > 0
    # exits when z jumps to 2.0 > entry at index 100
    assert e.iloc[100] == 0.0
    # stays flat during z=0.2 (not < exit_z=0.5 since 0.2 < 0.5 -> re-enters at index 140)
    # wait: re-enter condition is z < exit_z. z=0.2 < 0.5 so re-enters at index 140
    assert e.iloc[140] > 0
    # exits again when z=2.0 > entry at index 180
    assert e.iloc[180] == 0.0


def test_run_one_produces_finite_outputs():
    vix9d, vix, spy = _series()
    prices = pd.DataFrame({MOD.SPY: spy})
    res = MOD.run_one(
        prices,
        vix9d,
        vix,
        {"window": 21, "entry_z": 1.5, "exit_z": 0.5, "vol_target": 0.10},
    )
    bt = res["backtest"]
    assert np.isfinite(bt.returns.fillna(0.0)).all()
    assert np.isfinite(bt.equity_curve).all()
    assert (bt.equity_curve > 0).all()


def test_metrics_empty_mask_safe():
    vix9d, vix, spy = _series(300)
    prices = pd.DataFrame({MOD.SPY: spy})
    res = MOD.run_one(
        prices,
        vix9d,
        vix,
        {"window": 21, "entry_z": 1.5, "exit_z": 0.5, "vol_target": 0.10},
    )
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


def test_benchmark_ablation_finite():
    vix9d, vix, spy = _series(600)
    prices = pd.DataFrame({MOD.SPY: spy})
    mask = pd.Series(True, index=prices.index)
    mask.iloc[:300] = False
    res = MOD.run_one(
        prices,
        vix9d,
        vix,
        {"window": 21, "entry_z": 1.5, "exit_z": 0.5, "vol_target": 0.10},
    )
    ab = MOD._ablations(
        prices,
        vix9d,
        vix,
        {"window": 21, "entry_z": 1.5, "exit_z": 0.5, "vol_target": 0.10},
        mask,
    )
    assert "buy_hold_spy" in ab and "random_exposure_matched" in ab
    assert np.isfinite(ab["buy_hold_spy"]["sharpe"])


def test_perturbation_returns_ratio():
    vix9d, vix, spy = _series(500)
    prices = pd.DataFrame({MOD.SPY: spy})
    res = MOD.run_one(
        prices,
        vix9d,
        vix,
        {"window": 21, "entry_z": 1.5, "exit_z": 0.5, "vol_target": 0.10},
    )
    oos_mask = pd.Series(True, index=prices.index)
    oos_mask.iloc[:300] = False
    perturb = MOD._perturbation(
        prices,
        vix9d,
        vix,
        {"window": 21, "entry_z": 1.5, "exit_z": 0.5, "vol_target": 0.10},
        oos_mask,
        1.0,
    )
    assert "min_ratio_vs_optimum" in perturb
    assert np.isfinite(perturb["min_ratio_vs_optimum"])


def test_invalid_exit_not_in_grid_logic():
    vix9d, vix, spy = _series(300)
    z = MOD.fear_z(vix9d, vix, 21)
    e = MOD.build_exposure(z, 1.5, 2.0, 0.10)
    assert len(e) == len(z)
