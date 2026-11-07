"""Tests for NF-20261107-03 / H120: SPY short-term time-series reversal."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "run_nf_20261107_03_spy_ts_reversal",
    ROOT / "run_nf_20261107_03_spy_ts_reversal.py",
)
assert _SPEC and _SPEC.loader
MOD = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = MOD
_SPEC.loader.exec_module(MOD)


def _prices(n=900, seed=7):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2014-01-02", periods=n)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, n)))
    return pd.DataFrame({"SPY": close}, index=idx)


def test_no_lookahead_exposure_uses_past_returns_only():
    prices = _prices()
    spy_ret = prices["SPY"].pct_change().fillna(0.0)
    e1 = MOD.build_exposure(spy_ret, 5, -0.01, 0.0, 0.10)
    ret2 = spy_ret.copy()
    ret2.iloc[-1] = 0.5  # future change at end must not affect earlier exposure
    e2 = MOD.build_exposure(ret2, 5, -0.01, 0.0, 0.10)
    pd.testing.assert_series_equal(e1.iloc[:-5], e2.iloc[:-5])


def test_exposure_bounded_long_only():
    prices = _prices()
    spy_ret = prices["SPY"].pct_change().fillna(0.0)
    e = MOD.build_exposure(spy_ret, 3, -0.005, 0.0, 0.15)
    assert (e >= -1e-12).all()
    assert (e <= MOD.MAX_POS + 1e-12).all()


def test_reversal_signal_enters_after_weakness():
    idx = pd.bdate_range("2020-01-01", periods=40)
    rets = pd.Series([0.0] * 30 + [-0.02, -0.02, -0.02] + [0.001] * 7, index=idx)
    e = MOD.build_exposure(rets, 3, -0.01, 0.0, 0.10)
    assert e.max() > 0


def test_hysteresis_exits_only_at_exit_threshold():
    idx = pd.bdate_range("2018-01-01", periods=260)
    rets = pd.Series(0.001, index=idx)
    rets.iloc[200] = -0.015
    rets.iloc[201] = -0.015
    rets.iloc[202] = -0.004
    rets.iloc[203] = -0.004
    rets.iloc[204] = 0.02
    rets.iloc[205] = 0.02
    e = MOD.build_exposure(rets, 2, -0.02, 0.0, 0.10)
    assert e.max() > 0
    # after strong positive recovery (cum >= 0), raw exits to flat
    cum = rets.rolling(2, min_periods=2).sum()
    assert (cum.iloc[204:206] >= 0.0).all()
    assert (e.iloc[206:210] == 0.0).all()


def test_run_one_produces_finite_outputs():
    prices = _prices()
    res = MOD.run_one(
        prices, {"lookback": 3, "entry_thr": -0.01, "exit_thr": 0.0, "vol_target": 0.10}
    )
    bt = res["backtest"]
    assert np.isfinite(bt.returns.fillna(0.0)).all()
    assert np.isfinite(bt.equity_curve).all()
    assert (bt.equity_curve > 0).all()


def test_metrics_empty_mask_safe():
    prices = _prices(300)
    res = MOD.run_one(
        prices, {"lookback": 3, "entry_thr": -0.01, "exit_thr": 0.0, "vol_target": 0.10}
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


def test_vol_scale_bounded():
    spy_ret = pd.Series(
        np.random.default_rng(0).normal(0, 0.01, 200),
        index=pd.bdate_range("2020-01-01", periods=200),
    )
    s = MOD.vol_scale(spy_ret, 0.15)
    assert (s >= 0).all() and (s <= 1.0 + 1e-12).all()


def test_benchmark_ablation_finite():
    prices = _prices(600)
    mask = pd.Series(True, index=prices.index)
    mask.iloc[:300] = False
    ab = MOD._ablations(
        prices, {"lookback": 3, "entry_thr": -0.01, "exit_thr": 0.0, "vol_target": 0.10}, mask
    )
    assert "buy_hold_spy" in ab and "random_exposure_matched" in ab
    assert np.isfinite(ab["buy_hold_spy"]["sharpe"])


def test_invalid_exit_not_in_grid_logic():
    prices = _prices(300)
    spy_ret = prices["SPY"].pct_change().fillna(0.0)
    e = MOD.build_exposure(spy_ret, 3, -0.01, -0.02, 0.10)
    assert len(e) == len(spy_ret)
