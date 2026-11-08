from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

import run_nf_20261108_14_gdx_gld_rv_spy as mod


def _fake_prices(n: int = 600, seed: int = 149) -> pd.DataFrame:
    idx = pd.date_range("2015-01-02", periods=n, freq="B")
    rng = np.random.default_rng(seed)
    cols = {}
    for c in mod.UNIVERSE:
        vol = 0.012 if c == mod.SPY else (0.018 if c == mod.GDX else 0.010)
        cols[c] = 100 * (1 + pd.Series(rng.normal(0.0002, vol, n), index=idx)).cumprod()
    return pd.DataFrame(cols, index=idx)


def test_rv_divergence_z_finite_after_warmup():
    df = _fake_prices()
    z = mod.rv_divergence_z(df, rv_window=21, z_window=126)
    assert len(z) == len(df)
    assert z.iloc[250:].notna().any()


def test_make_signals_bounds_and_signals_zero():
    df = _fake_prices()
    sig = mod.make_signals(
        df, {"rv_window": 21, "z_window": 126, "entry_scale": 1.5, "vol_target": 0.10}
    )
    assert list(sig.columns) == list(mod.UNIVERSE)
    assert (sig[mod.GDX] == 0.0).all()
    assert (sig[mod.GLD] == 0.0).all()
    assert (sig[mod.SPY] >= 0.0).all()
    assert (sig[mod.SPY] <= mod.MAX_POS + 1e-12).all()


def test_metrics_from_result_safe():
    df = _fake_prices()
    out = mod.run_one(
        df, {"rv_window": 21, "z_window": 126, "entry_scale": 1.5, "vol_target": 0.10}
    )
    m = mod._metrics_from_result(out["result"], pd.Series(True, index=df.index))
    assert set(m.keys()) == {"n", "sharpe", "profit_factor", "max_drawdown", "trades"}
    assert isinstance(m["trades"], int)


def test_inverse_differs_from_base():
    df = _fake_prices()
    p = {"rv_window": 21, "z_window": 126, "entry_scale": 1.5, "vol_target": 0.10}
    base = mod.make_signals(df, p)[mod.SPY]
    z = mod.rv_divergence_z(df, p["rv_window"], p["z_window"])
    stress = ((-z).clip(lower=0.0) / p["entry_scale"]).clip(0.0, 1.0)
    raw = (1.0 - stress) * p["vol_target"]
    inv = (raw * mod._vol_scale(df, p["vol_target"])).fillna(0.0).clip(0.0, mod.MAX_POS)
    assert not np.allclose(base.values, inv.values)


def test_random_and_benchmark():
    df = _fake_prices()
    mask = pd.Series(True, index=df.index)
    r = mod.random_exposure_matched(df, mask, 0.05, 149)
    assert "sharpe" in r and "trades" in r
    b = mod.benchmark_buy_hold(df, mask)
    assert b["trades"] == 1


def test_de_risks_when_gdx_rv_elevated():
    idx = pd.date_range("2020-01-02", periods=320, freq="B")
    rng = np.random.default_rng(7)
    spy = 100 * (1 + pd.Series(rng.normal(0, 0.005, 320), index=idx)).cumprod()
    gdx = (
        100
        * (
            1 + pd.Series(np.r_[rng.normal(0, 0.004, 200), rng.normal(0, 0.06, 120)], index=idx)
        ).cumprod()
    )
    gld = 100 * (1 + pd.Series(rng.normal(0, 0.004, 320), index=idx)).cumprod()
    df = pd.DataFrame({mod.SPY: spy, mod.GDX: gdx, mod.GLD: gld})
    params = {"rv_window": 21, "z_window": 63, "entry_scale": 1.0, "vol_target": 0.15}
    sig = mod.make_signals(df, params)
    z = mod.rv_divergence_z(df, params["rv_window"], params["z_window"])
    onset = slice(200, 230)
    pre = slice(140, 200)
    # GDX RV divergence should spike positive at shock onset and reduce exposure vs pre-shock
    assert float(z.iloc[onset].mean()) > float(z.iloc[pre].mean()) + 0.2
    assert float(sig[mod.SPY].iloc[onset].mean()) < float(sig[mod.SPY].iloc[pre].mean())
