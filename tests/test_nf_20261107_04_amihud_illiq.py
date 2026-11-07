import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "run_nf_20261107_04_amihud_illiq", ROOT / "run_nf_20261107_04_amihud_illiq.py"
)
assert _SPEC and _SPEC.loader
MOD = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = MOD
_SPEC.loader.exec_module(MOD)


def _prices(n=400, seed=7):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2014-01-02", periods=n)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, n)))
    vol = rng.integers(1e6, 2e6, n)
    return pd.DataFrame({"SPY": close}, index=idx), pd.Series(vol, index=idx)


def test_amihud_z_finite():
    prices, vol = _prices()
    z = MOD.amihud_z(prices["SPY"], vol, 20)
    assert np.isfinite(z.dropna()).all()


def test_build_exposure_bounded():
    idx = pd.bdate_range("2020-01-01", periods=100)
    z = pd.Series(np.random.default_rng(0).normal(0, 1, 100), index=idx)
    e = MOD.build_exposure(z, 1.5, 0.5, 0.10)
    assert (e >= -1e-12).all()
    assert (e <= 0.10 + 1e-12).all()


def test_run_one_finite():
    prices, vol = _prices(400)
    res = MOD.run_one(
        prices, {"window": 20, "entry_z": 1.5, "exit_z": 0.5, "vol_target": 0.10}, vol
    )
    bt = res["backtest"]
    assert np.isfinite(bt.returns.fillna(0.0)).all()
    assert np.isfinite(bt.equity_curve).all()


def test_metrics_empty():
    prices, vol = _prices(200)
    res = MOD.run_one(
        prices, {"window": 20, "entry_z": 1.5, "exit_z": 0.5, "vol_target": 0.10}, vol
    )
    mask = pd.Series(False, index=prices.index)
    m = MOD.metrics_from(res["backtest"], mask)
    assert m["n"] == 0


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
