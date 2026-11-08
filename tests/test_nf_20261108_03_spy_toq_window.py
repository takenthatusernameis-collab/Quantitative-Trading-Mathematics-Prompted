from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

import run_nf_20261108_03_spy_toq_window as mod


def _fake_prices():
    idx = pd.date_range("2020-01-02", periods=400, freq="B")
    rng = np.random.default_rng(123)
    rets = rng.normal(0.0002, 0.01, len(idx))
    px = 100 * (1 + pd.Series(rets, index=idx)).cumprod()
    df = pd.DataFrame({"SPY": px}, index=idx)
    return df


def test_toq_window_deterministic():
    df = _fake_prices()
    w1 = mod.toq_window(df.index, end_days=2, start_days=1)
    w2 = mod.toq_window(df.index, end_days=2, start_days=1)
    assert (w1 == w2).all()
    assert w1.dtype == bool or w1.dtype == object


def test_exposure_nonnegative():
    df = _fake_prices()
    toq = mod.toq_window(df.index, end_days=2, start_days=1)
    ex = mod.build_exposure(toq, entry_scale=2.0, vol_target=0.10)
    assert (ex >= 0).all()
    assert (ex <= 0.10 + 1e-12).all()


def test_metrics_from_empty_trades_guard():
    df = _fake_prices()
    out = mod.run_one(df, {"end_days": 2, "start_days": 1, "entry_scale": 2.0, "vol_target": 0.10})
    m = mod.metrics_from(out["result"], pd.Series(True, index=df.index))
    assert set(m.keys()) == {"n", "sharpe", "profit_factor", "max_drawdown", "trades"}
    assert isinstance(m["trades"], int)


def test_wf_and_perturbation():
    df = _fake_prices()
    train = pd.Series(True, index=df.index)
    p = {"end_days": 2, "start_days": 1, "entry_scale": 2.0, "vol_target": 0.10}
    wf = mod.wf_train_sharpe(df, train, p, 2)
    assert isinstance(wf, float)
    pert = mod.perturbation_test(df, p, train)
    assert isinstance(pert, float)


def test_random_and_inverse():
    df = _fake_prices()
    oos = pd.Series(True, index=df.index)
    p = {"end_days": 2, "start_days": 1, "entry_scale": 2.0, "vol_target": 0.10}
    r = mod.random_exposure_matched(df, oos, 0.1, 42)
    assert "sharpe" in r
    inv = mod.inverse_regime(df, p)
    m = mod.metrics_from(inv["result"], oos)
    assert m["trades"] >= 0
