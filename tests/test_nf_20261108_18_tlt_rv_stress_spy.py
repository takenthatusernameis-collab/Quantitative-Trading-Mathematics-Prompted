from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

import run_nf_20261108_18_tlt_rv_stress_spy as mod


def _fake_prices(n: int = 2600, seed: int = 151) -> pd.DataFrame:
    idx = pd.date_range("2014-01-02", periods=n, freq="B")
    rng = np.random.default_rng(seed)
    spy = 100 * (1 + pd.Series(rng.normal(0.0003, 0.012, n), index=idx)).cumprod()
    tlt = 100 * (1 + pd.Series(rng.normal(0.0001, 0.010, n), index=idx)).cumprod()
    return pd.DataFrame({mod.SPY: spy, mod.TLT: tlt}, index=idx)


def test_tlt_rv_z_finite_after_warmup():
    prices = _fake_prices()
    z = mod.tlt_rv_z(prices, rv_window=21, z_window=126)
    assert len(z) == len(prices)
    assert z.iloc[260:].notna().any()


def test_make_signals_bounds_and_tlt_zero():
    prices = _fake_prices()
    sig = mod.make_signals(
        prices, {"rv_window": 21, "z_window": 126, "entry_scale": 1.5, "vol_target": 0.10}
    )
    assert list(sig.columns) == list(mod.UNIVERSE)
    assert (sig[mod.TLT] == 0.0).all()
    assert (sig[mod.SPY] >= 0.0).all()
    assert (sig[mod.SPY] <= mod.MAX_POS + 1e-12).all()


def test_metrics_from_result_safe():
    prices = _fake_prices()
    out = mod.run_one(
        prices, {"rv_window": 21, "z_window": 126, "entry_scale": 1.5, "vol_target": 0.10}
    )
    m = mod._metrics_from_result(out["result"], pd.Series(True, index=prices.index))
    assert set(m.keys()) == {"n", "sharpe", "profit_factor", "max_drawdown", "trades"}
    assert isinstance(m["trades"], int)


def test_inverse_differs_from_base():
    prices = _fake_prices()
    p = {"rv_window": 21, "z_window": 126, "entry_scale": 1.5, "vol_target": 0.10}
    base = mod.make_signals(prices, p)[mod.SPY]
    inv = mod.inverse_regime(prices, p)
    z = mod.tlt_rv_z(prices, p["rv_window"], p["z_window"])
    stress = ((-z).clip(lower=0.0) / p["entry_scale"]).clip(0.0, 1.0)
    raw = (1.0 - stress) * p["vol_target"]
    inv_expo = (raw * mod._vol_scale(prices, p["vol_target"])).fillna(0.0).clip(0.0, mod.MAX_POS)
    assert not np.allclose(base.values, inv_expo.values)
    assert isinstance(inv["trades"], int)


def test_random_and_benchmark():
    prices = _fake_prices()
    mask = pd.Series(True, index=prices.index)
    r = mod.random_exposure_matched(prices, mask, 0.05, 151)
    assert "sharpe" in r and "trades" in r
    b = mod.benchmark_buy_hold(prices, mask)
    assert b["trades"] == 1


def test_de_risks_when_tlt_rv_abnormally_high():
    prices = _fake_prices()
    # inject high-vol regime in TLT in second half
    tlt = prices[mod.TLT].copy()
    rng = np.random.default_rng(99)
    n = len(tlt)
    shock = 1 + pd.Series(
        np.r_[rng.normal(0, 0.005, n // 2), rng.normal(0, 0.04, n - n // 2)], index=tlt.index
    )
    prices2 = prices.copy()
    prices2[mod.TLT] = 100 * shock.cumprod()
    params = {"rv_window": 21, "z_window": 126, "entry_scale": 1.0, "vol_target": 0.15}
    sig = mod.make_signals(prices2, params)
    early = float(sig[mod.SPY].iloc[300 : n // 2].mean())
    late = float(sig[mod.SPY].iloc[n // 2 + 80 :].mean())
    assert late <= early + 1e-9
