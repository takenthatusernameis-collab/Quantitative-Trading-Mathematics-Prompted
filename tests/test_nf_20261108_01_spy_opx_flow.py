"""Focused tests for NF-20261108-01 / H140 (SPY OPX flow-proximity regime)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import datetime as dt  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import run_nf_20261108_01_spy_opx_flow as nf  # noqa: E402


def _synthetic(n: int = 900) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    idx = pd.bdate_range("2015-01-02", periods=n)
    spy = 200 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
    return pd.DataFrame({"SPY": spy}, index=idx)


def test_opx_dates_third_friday():
    start = pd.Timestamp("2025-01-01")
    end = pd.Timestamp("2025-06-30")
    dates = nf._monthly_opx_dates(start, end)
    assert len(dates) == 6
    for d in dates:
        assert d.weekday() == 4  # Friday
        # third Friday: between 15th and 21st
        assert 15 <= d.day <= 21


def test_opx_flow_z_past_only():
    p = _synthetic()
    opx = nf._monthly_opx_dates(pd.Timestamp("2014-01-01"), pd.Timestamp("2026-01-01"))
    z_full = nf.opx_flow_z(p, opx, z_window=63)
    p2 = p.copy()
    p2.loc[p2.index[-1], "SPY"] *= 1.5
    z_alt = nf.opx_flow_z(p2, opx, z_window=63)
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
    opx = nf._monthly_opx_dates(pd.Timestamp("2014-01-01"), pd.Timestamp("2026-01-01"))
    params = {"z_window": 63, "entry_scale": 1.5, "vol_target": 0.10}
    res = nf.run_one(p, opx, params)
    assert "SPY" in res["signals"].columns
    assert len(res["signals"]) == len(p)
    assert float(res["signals"]["SPY"].max()) <= nf.MAX_POS + 1e-12
    assert float(res["signals"]["SPY"].min()) >= -1e-12


def test_wf_train_sharpe_finite_or_floor():
    p = _synthetic(800)
    opx = nf._monthly_opx_dates(pd.Timestamp("2014-01-01"), pd.Timestamp("2026-01-01"))
    mask = pd.Series(True, index=p.index)
    params = {"z_window": 63, "entry_scale": 1.5, "vol_target": 0.10}
    s = nf.wf_train_sharpe(p, opx, mask, params, folds=4)
    assert np.isfinite(s)


def test_perturbation_and_random_exposure():
    p = _synthetic(700)
    opx = nf._monthly_opx_dates(pd.Timestamp("2014-01-01"), pd.Timestamp("2026-01-01"))
    mask = pd.Series(True, index=p.index)
    params = {"z_window": 63, "entry_scale": 1.5, "vol_target": 0.10}
    pr = nf.perturbation_test(p, opx, params, mask)
    assert np.isfinite(pr)
    randm = nf.random_exposure_matched(p, mask, mean_exposure=0.5, seed=42)
    assert set(randm) >= {"sharpe", "profit_factor", "max_drawdown", "trades"}


def test_inverse_regime_runs():
    p = _synthetic(600)
    opx = nf._monthly_opx_dates(pd.Timestamp("2014-01-01"), pd.Timestamp("2026-01-01"))
    params = {"z_window": 63, "entry_scale": 1.5, "vol_target": 0.10}
    res = nf.inverse_regime(p, opx, params)
    assert len(res["signals"]) == len(p)
