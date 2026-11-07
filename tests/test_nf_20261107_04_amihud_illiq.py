"""Tests for NF-20261107-04 / H121: SPY Amihud illiquidity-stress regime timing."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "run_nf_20261107_04_amihud_illiq",
    ROOT / "run_nf_20261107_04_amihud_illiq.py",
)
assert _SPEC and _SPEC.loader
MOD = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = MOD
_SPEC.loader.exec_module(MOD)


def _prices(n=900, seed=7):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2014-01-02", periods=n)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, n)))
    vol = rng.integers(1_000_000, 2_000_000, n)
    return pd.DataFrame({"SPY": close}, index=idx), pd.Series(vol, index=idx)


def test_amihud_z_finite():
    prices, vol = _prices()
    z = MOD.amihud_z(prices["SPY"], vol, 20)
    assert np.isfinite(z.dropna()).all()


def test_amihud_z_uses_past_only():
    prices, vol = _prices()
    z1 = MOD.amihud_z(prices["SPY"], vol, 20)
    close2 = prices["SPY"].copy()
    close2.iloc[-1] = close2.iloc[-1] * 1.5  # future change at end
    z2 = MOD.amihud_z(close2, vol, 20)
    pd.testing.assert_series_equal(z1.iloc[:-20], z2.iloc[:-20])


def test_build_exposure_bounded():
    idx = pd.bdate_range("2020-01-01", periods=100)
    z = pd.Series(np.random.default_rng(0).normal(0, 1, 100), index=idx)
    e = MOD.build_exposure(z, 1.5, 0.5, 0.10)
    assert (e >= -1e-12).all()
    assert (e <= 0.10 + 1e-12).all()


def test_build_exposure_enters_low_illiquidity_exits_high():
    idx = pd.bdate_range("2020-01-01", periods=60)
    z = pd.Series([2.0] * 20 + [0.2] * 20 + [2.0] * 20, index=idx)
    e = MOD.build_exposure(z, 1.0, 0.5, 0.10)
    # starts flat (z=2.0 > entry 1.0), enters when z drops to 0.2, exits when z back to 2.0
    assert e.iloc[15] == 0.0
    assert e.iloc[20] > 0
    assert e.iloc[40] == 0.0


def test_hysteresis_exit_only_above_exit_z():
    idx = pd.bdate_range("2018-01-01", periods=260)
    z = pd.Series([2.0] * 100 + [0.2] * 40 + [1.2] * 40 + [0.2] * 80, index=idx)
    e = MOD.build_exposure(z, entry_z=1.0, exit_z=0.5, vol_target=0.10)
    # enters at index 100 (z drops to 0.2 <= 1.0)
    assert e.iloc[100] > 0
    # stays in during z=1.2 (not > exit_z=0.5 means stay... actually z=1.2 > 0.5 so exits)
    # wait: exit condition is z > exit_z. z=1.2 > 0.5 so exits
    assert e.iloc[140] == 0.0
    # re-enters at index 180 (z=0.2 <= 1.0)
    assert e.iloc[180] > 0


def test_run_one_produces_finite_outputs():
    prices, vol = _prices()
    res = MOD.run_one(
        prices, vol, {"window": 20, "entry_z": 1.5, "exit_z": 0.5, "vol_target": 0.10}
    )
    bt = res["backtest"]
    assert np.isfinite(bt.returns.fillna(0.0)).all()
    assert np.isfinite(bt.equity_curve).all()
    assert (bt.equity_curve > 0).all()


def test_metrics_empty_mask_safe():
    prices, vol = _prices(300)
    res = MOD.run_one(
        prices, vol, {"window": 20, "entry_z": 1.5, "exit_z": 0.5, "vol_target": 0.10}
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
    prices, vol = _prices(600)
    mask = pd.Series(True, index=prices.index)
    mask.iloc[:300] = False
    ab = MOD._ablations(
        prices,
        vol,
        {"window": 20, "entry_z": 1.5, "exit_z": 0.5, "vol_target": 0.10},
        mask,
    )
    assert "buy_hold_spy" in ab and "random_exposure_matched" in ab
    assert np.isfinite(ab["buy_hold_spy"]["sharpe"])


def test_perturbation_returns_ratio():
    prices, vol = _prices(500)
    sel = MOD.run_one(
        prices, vol, {"window": 20, "entry_z": 1.5, "exit_z": 0.5, "vol_target": 0.10}
    )
    oos_mask = pd.Series(True, index=prices.index)
    oos_mask.iloc[:300] = False
    perturb = MOD._perturbation(
        prices,
        vol,
        sel["params"]
        if "params" in sel
        else {"window": 20, "entry_z": 1.5, "exit_z": 0.5, "vol_target": 0.10},
        oos_mask,
        1.0,
    )
    assert "min_ratio_vs_optimum" in perturb
    assert np.isfinite(perturb["min_ratio_vs_optimum"])


def test_invalid_exit_not_in_grid_logic():
    prices, vol = _prices(300)
    z = MOD.amihud_z(prices["SPY"], vol, 20)
    e = MOD.build_exposure(z, 1.5, 2.0, 0.10)
    assert len(e) == len(z)
