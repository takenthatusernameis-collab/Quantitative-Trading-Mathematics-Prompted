from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

import run_nf_20261108_15_es_mm_flow_spy as mod


def _fake_prices(n: int = 600, seed: int = 150) -> pd.DataFrame:
    idx = pd.date_range("2015-01-02", periods=n, freq="B")
    rng = np.random.default_rng(seed)
    cols = {}
    for c in mod.UNIVERSE:
        vol = 0.012 if c == mod.SPY else 0.010
        cols[c] = 100 * (1 + pd.Series(rng.normal(0.0002, vol, n), index=idx)).cumprod()
    return pd.DataFrame(cols, index=idx)


def _fake_mm_net(n: int = 600, seed: int = 150) -> pd.Series:
    idx = pd.date_range("2015-01-02", periods=n, freq="B")
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(0.0, 1000.0, n), index=idx)


def test_mm_zscore_finite_after_warmup():
    mm = _fake_mm_net()
    z = mod._mm_zscore(mm, mm_window=63, z_window=126)
    assert len(z) == len(mm)
    assert z.iloc[200:].notna().any()


def test_make_signals_bounds_and_signals_zero():
    df = _fake_prices()
    mm = _fake_mm_net(len(df))
    mm = mm.set_axis(df.index)
    sig = mod.make_signals(
        df, mm, {"mm_window": 63, "z_window": 126, "entry_scale": 1.5, "vol_target": 0.10}
    )
    assert list(sig.columns) == list(mod.UNIVERSE)
    assert (sig[mod.ES] == 0.0).all()
    assert (sig[mod.SPY] >= 0.0).all()
    assert (sig[mod.SPY] <= mod.MAX_POS + 1e-12).all()


def test_metrics_from_result_safe():
    df = _fake_prices()
    mm = _fake_mm_net(len(df)).set_axis(df.index)
    out = mod.run_one(
        df, mm, {"mm_window": 63, "z_window": 126, "entry_scale": 1.5, "vol_target": 0.10}
    )
    m = mod._metrics_from_result(out["result"], pd.Series(True, index=df.index))
    assert set(m.keys()) == {"n", "sharpe", "profit_factor", "max_drawdown", "trades"}
    assert isinstance(m["trades"], int)


def test_inverse_differs_from_base():
    df = _fake_prices()
    mm = _fake_mm_net(len(df)).set_axis(df.index)
    p = {"mm_window": 63, "z_window": 126, "entry_scale": 1.5, "vol_target": 0.10}
    base = mod.make_signals(df, mm, p)[mod.SPY]
    z = mod._mm_zscore(mm, p["mm_window"], p["z_window"]).reindex(df.index, method="ffill").fillna(0.0)
    stress = ((-z).clip(lower=0.0) / p["entry_scale"]).clip(0.0, 1.0)
    raw = (1.0 - stress) * p["vol_target"]
    inv = (raw * mod._vol_scale(df, p["vol_target"])).fillna(0.0).clip(0.0, mod.MAX_POS)
    assert not np.allclose(base.values, inv.values)


def test_random_and_benchmark():
    df = _fake_prices()
    mask = pd.Series(True, index=df.index)
    r = mod.random_exposure_matched(df, mask, 0.05, 150)
    assert "sharpe" in r and "trades" in r
    b = mod.benchmark_buy_hold(df, mask)
    assert b["trades"] == 1


def test_de_risks_when_es_mm_net_elevated():
    idx = pd.date_range("2020-01-02", periods=320, freq="B")
    rng = np.random.default_rng(7)
    spy = 100 * (1 + pd.Series(rng.normal(0, 0.005, 320), index=idx)).cumprod()
    es = 100 * (1 + pd.Series(rng.normal(0, 0.004, 320), index=idx)).cumprod()
    df = pd.DataFrame({mod.SPY: spy, mod.ES: es})
    mm = pd.Series(
        np.r_[rng.normal(0, 500, 200), rng.normal(4000, 500, 120)], index=idx
    )
    params = {"mm_window": 63, "z_window": 63, "entry_scale": 1.0, "vol_target": 0.15}
    sig = mod.make_signals(df, mm, params)
    z = mod._mm_zscore(mm, params["mm_window"], params["z_window"]).reindex(
        df.index, method="ffill"
    ).fillna(0.0)
    onset = slice(200, 230)
    pre = slice(140, 200)
    # ES MM net position shock should spike positive z at onset and reduce
    # exposure vs pre-shock (de-risking on crowding).
    assert float(z.iloc[onset].mean()) > float(z.iloc[pre].mean()) + 0.2
    assert float(sig[mod.SPY].iloc[onset].mean()) < float(sig[mod.SPY].iloc[pre].mean())
