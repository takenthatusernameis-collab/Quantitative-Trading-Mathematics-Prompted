from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd

import run_nf_20261107_34_vix_termstructure_regime as mod


def _make_prices(n=600):
    idx = pd.date_range("2015-01-02", periods=n, freq="B")
    rng = np.random.RandomState(123)
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, n)))
    vix = 15 + rng.normal(0, 1, n)
    vix3m = vix * (1.0 + rng.normal(0.1, 0.02, n))
    return pd.DataFrame({mod.SPY: spy, mod.VIX: vix, mod.VIX3M: vix3m}, index=idx)


def test_fetch_mocked(monkeypatch):
    prices = _make_prices()
    monkeypatch.setattr(mod, "_fetch", lambda: prices)
    p = mod._fetch()
    assert mod.SPY in p.columns


def test_splits():
    prices = _make_prices()
    tr, va, te = mod._splits(prices.index)
    assert (tr | va | te).sum() == len(prices)


def test_vix_z():
    prices = _make_prices()
    z = mod.vix_termstructure_z(prices, 63)
    assert isinstance(z, pd.Series)
    assert z.dropna().shape[0] > 0


def test_vol_scale_and_build():
    prices = _make_prices()
    spy_ret = prices[mod.SPY].pct_change().fillna(0.0)
    vs = mod.vol_scale(spy_ret, 0.10)
    assert vs.clip(0, 1).equals(vs)
    z = mod.vix_termstructure_z(prices, 63)
    exp = mod.build_exposure(z, 2.0, 0.10)
    assert (exp >= 0).all()
    assert (exp <= 0.10).all()


def test_run_one_and_metrics():
    prices = _make_prices()
    res = mod.run_one(prices, {"z_window": 63, "entry_scale": 2.0, "vol_target": 0.10})
    assert "backtest" in res
    tr, va, te = mod._splits(prices.index)
    m = mod.metrics_from(res["backtest"], tr)
    assert "sharpe" in m and "trades" in m


def test_ablation_helpers():
    prices = _make_prices()
    tr, va, te = mod._splits(prices.index)
    bh = mod.benchmark_buyhold(prices, tr)
    assert bh["trades"] >= 0
    rm = mod.random_exposure_matched(prices, tr, 0.1, 42)
    assert "sharpe" in rm
    inv = mod.inverse_regime(prices, {"z_window": 63, "entry_scale": 2.0, "vol_target": 0.10})
    assert "backtest" in inv


def test_wf_and_diagnostics():
    prices = _make_prices()
    tr, va, te = mod._splits(prices.index)
    ws = mod.wf_train_sharpe(prices, tr, {"z_window": 63, "entry_scale": 2.0, "vol_target": 0.10})
    assert isinstance(ws, float)
    r = prices[mod.SPY].pct_change().fillna(0.0)
    wr = mod.worst_regime_rolling_sharpe(r, window=50)
    assert isinstance(wr, float)
    pt = mod.perturbation_test(prices, {"z_window": 63, "entry_scale": 2.0, "vol_target": 0.10}, tr)
    assert isinstance(pt, float)
