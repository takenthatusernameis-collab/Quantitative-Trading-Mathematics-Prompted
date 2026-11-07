"""Tests for NF-20261107-30 / H130: SPY timing from average sector IVOL regime."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "run_nf_20261107_30_avg_ivol_regime",
    ROOT / "run_nf_20261107_30_avg_ivol_regime.py",
)
assert _SPEC and _SPEC.loader
MOD = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = MOD
_SPEC.loader.exec_module(MOD)


def _prices(n=700, seed=11):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2014-01-02", periods=n)
    data = {}
    mkt = rng.normal(0.0003, 0.01, n)
    for c in MOD.UNIVERSE:
        noise = rng.normal(0.0, 0.006, n)
        beta = 1.0 if c == MOD.SPY else 0.8 + 0.4 * rng.random()
        data[c] = 100 * np.exp(np.cumsum(beta * mkt + noise))
    return pd.DataFrame(data, index=idx)


def test_avg_ivol_z_finite():
    prices = _prices()
    z = MOD.avg_ivol_z(prices, 63, 126)
    assert np.isfinite(z.dropna()).all()


def test_avg_ivol_z_past_only():
    prices = _prices()
    z1 = MOD.avg_ivol_z(prices, 63, 126)
    p2 = prices.copy()
    p2.iloc[-1, 1] = p2.iloc[-1, 1] * 1.5
    z2 = MOD.avg_ivol_z(p2, 63, 126)
    pd.testing.assert_series_equal(z1.iloc[:-120], z2.iloc[:-120])


def test_build_exposure_bounded():
    idx = pd.bdate_range("2020-01-01", periods=120)
    z = pd.Series(np.random.default_rng(0).normal(0, 1, 120), index=idx)
    e = MOD.build_exposure(z, 1.5, 0.10)
    assert (e >= -1e-12).all()
    assert (e <= 0.10 + 1e-12).all()


def test_build_exposure_derisks_on_high_z():
    idx = pd.bdate_range("2020-01-01", periods=60)
    z = pd.Series([-1.0] * 20 + [0.0] * 20 + [3.0] * 20, index=idx)
    e = MOD.build_exposure(z, entry_scale=1.5, vol_target=0.10)
    assert e.iloc[0] == 0.10
    assert e.iloc[20] == 0.10
    assert e.iloc[40] == 0.0


def test_run_one_finite_outputs():
    prices = _prices()
    res = MOD.run_one(
        prices,
        {"beta_window": 63, "z_window": 126, "entry_scale": 1.5, "vol_target": 0.10},
    )
    bt = res["backtest"]
    assert np.isfinite(bt.returns.fillna(0.0)).all()
    assert np.isfinite(bt.equity_curve).all()
    assert (bt.equity_curve > 0).all()


def test_metrics_empty_mask_safe():
    prices = _prices(350)
    res = MOD.run_one(
        prices,
        {"beta_window": 63, "z_window": 126, "entry_scale": 1.5, "vol_target": 0.10},
    )
    mask = pd.Series(False, index=prices.index)
    met = MOD.metrics_from(res["backtest"], mask)
    assert met["trades"] == 0


def test_wf_stability_range():
    prices = _prices(500)
    train_mask = pd.Series(True, index=prices.index)
    wf = MOD.wf_stability(
        prices,
        {"beta_window": 63, "z_window": 126, "entry_scale": 1.5, "vol_target": 0.10},
        train_mask,
    )
    assert 0.0 <= wf <= 1.0


def test_splits_cover_index():
    idx = pd.bdate_range("2015-01-01", periods=300)
    tr, va, te = MOD._splits(idx)
    assert (tr | va | te).all()
    assert not (tr & va).any()
