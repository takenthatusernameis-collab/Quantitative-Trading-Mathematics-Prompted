"""Focused tests for NF-20261107-53 / H139 (IWM-vs-SPY RV divergence)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import run_nf_20261107_53_iwm_spy_rv_divergence as nf  # noqa: E402


def _synthetic(n: int = 900) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    idx = pd.bdate_range("2015-01-02", periods=n)
    spy = 200 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
    iwm = 180 * np.exp(np.cumsum(rng.normal(0.0002, 0.012, n)))
    return pd.DataFrame({"SPY": spy, "IWM": iwm}, index=idx)


def test_rv_divergence_z_past_only():
    p = _synthetic()
    z_full = nf.rv_divergence_z(p, rv_window=21, z_window=126)
    p2 = p.copy()
    p2.loc[p2.index[-1], "SPY"] *= 1.5
    z_alt = nf.rv_divergence_z(p2, rv_window=21, z_window=126)
    assert np.allclose(z_full.iloc[:-1].to_numpy(), z_alt.iloc[:-1].to_numpy(), equal_nan=True)
    assert z_full.index.equals(p.index)


def test_build_exposure_bounds_and_nan():
    z = pd.Series([np.nan, -1.0, 0.0, 1.0, 5.0])
    ex = nf.build_exposure(z, entry_scale=2.0, vol_target=0.15)
    assert ex.iloc[0] == 0.0
    assert np.all(ex.dropna() >= 0.0)
    assert np.all(ex.dropna() <= 0.15 + 1e-12)
    assert ex.iloc[3] < ex.iloc[2]
    assert ex.iloc[4] <= ex.iloc[3]


def test_metrics_from_empty():
    class FakeBT:
        equity_curve = [1_000_000.0, 1_000_000.0]
        trades = []

    idx = pd.bdate_range("2020-01-01", periods=2)
    m = nf.metrics_from(FakeBT(), pd.Series([False, False], index=idx))
    assert m["n"] == 0
    assert m["sharpe"] == 0.0


def test_run_one_shapes_and_delay_compat():
    p = _synthetic(600)
    params = {"rv_window": 21, "z_window": 126, "entry_scale": 1.5, "vol_target": 0.10}
    res = nf.run_one(p, params)
    assert "SPY" in res["signals"].columns
    assert len(res["signals"]) == len(p)
    assert float(res["signals"]["SPY"].max()) <= nf.MAX_POS + 1e-12
    assert float(res["signals"]["SPY"].min()) >= -1e-12


def test_wf_train_sharpe_finite_or_floor():
    p = _synthetic(800)
    mask = pd.Series(True, index=p.index)
    params = {"rv_window": 21, "z_window": 126, "entry_scale": 1.5, "vol_target": 0.10}
    s = nf.wf_train_sharpe(p, mask, params, folds=4)
    assert np.isfinite(s)


def test_perturbation_and_random_exposure():
    p = _synthetic(700)
    mask = pd.Series(True, index=p.index)
    params = {"rv_window": 21, "z_window": 126, "entry_scale": 1.5, "vol_target": 0.10}
    pr = nf.perturbation_test(p, params, mask)
    assert np.isfinite(pr)
    randm = nf.random_exposure_matched(p, mask, mean_exposure=0.5, seed=42)
    assert set(randm) >= {"sharpe", "profit_factor", "max_drawdown", "trades"}


def test_inverse_regime_runs():
    p = _synthetic(600)
    params = {"rv_window": 21, "z_window": 126, "entry_scale": 1.5, "vol_target": 0.10}
    res = nf.inverse_regime(p, params)
    assert len(res["signals"]) == len(p)
