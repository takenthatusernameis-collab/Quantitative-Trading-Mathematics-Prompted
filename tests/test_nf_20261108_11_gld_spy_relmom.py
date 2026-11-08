from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

import run_nf_20261108_11_gld_spy_relmom as mod


def _fake_prices(n: int = 500, seed: int = 11) -> pd.DataFrame:
    idx = pd.date_range("2015-01-02", periods=n, freq="B")
    rng = np.random.default_rng(seed)
    spy = 100 * (1 + pd.Series(rng.normal(0.0003, 0.01, n), index=idx)).cumprod()
    gld = 100 * (1 + pd.Series(rng.normal(0.0002, 0.012, n), index=idx)).cumprod()
    return pd.DataFrame({"SPY": spy, "GLD": gld}, index=idx)


def test_relmom_z_finite_after_warmup():
    df = _fake_prices()
    z = mod.relmom_z(df, mom_window=21, z_window=126)
    assert len(z) == len(df)
    assert z.iloc[180:].notna().any()


def test_make_signals_bounds_and_gld_zero():
    df = _fake_prices()
    sig = mod.make_signals(
        df, {"mom_window": 21, "z_window": 126, "entry_scale": 2.0, "vol_target": 0.10}
    )
    assert (sig["GLD"] == 0.0).all()
    assert (sig["SPY"] >= 0.0).all()
    assert (sig["SPY"] <= mod.MAX_POS + 1e-12).all()


def test_metrics_from_result_empty_trades_safe():
    df = _fake_prices()
    out = mod.run_one(
        df, {"mom_window": 21, "z_window": 126, "entry_scale": 2.0, "vol_target": 0.10}
    )
    m = mod._metrics_from_result(out["result"], pd.Series(True, index=df.index))
    assert set(m.keys()) == {"n", "sharpe", "profit_factor", "max_drawdown", "trades"}
    assert isinstance(m["trades"], int)


def test_inverse_differs_from_base():
    df = _fake_prices()
    p = {"mom_window": 21, "z_window": 126, "entry_scale": 2.0, "vol_target": 0.10}
    base = mod.make_signals(df, p)["SPY"]
    # inverse construction: stress on positive z
    z = mod.relmom_z(df, p["mom_window"], p["z_window"])
    stress = (z.clip(lower=0.0) / p["entry_scale"]).clip(0.0, 1.0)
    raw = (1.0 - stress) * p["vol_target"]
    inv = (raw * mod._vol_scale(df, p["vol_target"])).fillna(0.0).clip(0.0, mod.MAX_POS)
    assert not np.allclose(base.values, inv.values)


def test_random_and_benchmark():
    df = _fake_prices()
    mask = pd.Series(True, index=df.index)
    r = mod.random_exposure_matched(df, mask, 0.05, 42)
    assert "sharpe" in r and "trades" in r
    b = mod.benchmark_buy_hold(df, mask)
    assert b["trades"] == 1
