from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

import run_nf_20261108_06_spy_overnight_gap_rv as mod


def _fake_ohlc(n: int = 500, seed: int = 7) -> pd.DataFrame:
    idx = pd.date_range("2015-01-02", periods=n, freq="B")
    rng = np.random.default_rng(seed)
    close = 100 * (1 + pd.Series(rng.normal(0.0002, 0.01, n), index=idx)).cumprod()
    gap = rng.normal(0.0, 0.003, n)
    open_ = close.shift(1).fillna(close.iloc[0]) * np.exp(gap)
    return pd.DataFrame({"Open": open_, "Close": close}, index=idx)


def test_overnight_gap_rv_z_finite_after_warmup():
    df = _fake_ohlc()
    z = mod.overnight_gap_rv_z(df, rv_window=21, z_window=63)
    assert len(z) == len(df)
    assert z.iloc[120:].notna().any()


def test_build_exposure_bounds():
    z = pd.Series([np.nan, -2.0, 0.0, 1.0, 4.0])
    ex = mod.build_exposure(z, entry_scale=2.0, vol_target=0.10)
    assert (ex >= 0).all()
    assert (ex <= 0.10 + 1e-12).all()
    assert ex.iloc[4] == 0.0  # stress clipped to 1


def test_metrics_from_empty_trades_guard():
    df = _fake_ohlc()
    out = mod.run_one(df, {"rv_window": 21, "z_window": 63, "entry_scale": 2.0, "vol_target": 0.10})
    m = mod.metrics_from(out["result"], pd.Series(True, index=df.index))
    assert set(m.keys()) == {"n", "sharpe", "profit_factor", "max_drawdown", "trades"}
    assert isinstance(m["trades"], int)


def test_inverse_differs_from_base_signal():
    df = _fake_ohlc()
    p = {"rv_window": 21, "z_window": 63, "entry_scale": 2.0, "vol_target": 0.10}
    base = mod.run_one(df, p)["signals"]["SPY"]
    inv = mod.inverse_regime(df, p)["signals"]["SPY"]
    assert not np.allclose(base.values, inv.values)


def test_random_and_benchmark():
    df = _fake_ohlc()
    mask = pd.Series(True, index=df.index)
    r = mod.random_exposure_matched(df, mask, 0.05, 42)
    assert "sharpe" in r
    b = mod.benchmark_buy_hold(df, mask)
    assert b["trades"] >= 0
