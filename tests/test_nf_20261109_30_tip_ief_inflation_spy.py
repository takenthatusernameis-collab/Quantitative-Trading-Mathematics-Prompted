from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from run_nf_20261109_30_tip_ief_inflation_spy import (  # noqa: E402
    benchmark_ir_p,
    build_signal,
    max_dd,
    perturbation_min_ratio,
    profit_factor,
    rolling_z,
    split_index,
    worst_regime_sharpe,
)


def _prices(n=600):
    idx = pd.bdate_range("2015-01-01", periods=n)
    rng = np.random.default_rng(0)
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
    tip = 100 * np.exp(np.cumsum(rng.normal(0.0001, 0.004, n)))
    ief = 100 * np.exp(np.cumsum(rng.normal(0.00005, 0.003, n)))
    return pd.DataFrame({"SPY": spy, "TIP": tip, "IEF": ief}, index=idx)


def test_rolling_z_shape_and_nans():
    s = pd.Series(np.arange(100.0))
    z = rolling_z(s, 20)
    assert len(z) == 100
    assert z.iloc[:19].isna().all()
    assert np.isfinite(z.iloc[50])


def test_build_signal_bounds_and_columns():
    prices = _prices()
    sig = build_signal(
        prices, mom_window=21, z_window=126, entry_scale=1.0, vol_target=0.15
    )
    assert list(sig.columns) == ["SPY"]
    assert sig["SPY"].between(0.0, 0.5 + 1e-12).all()


def test_build_signal_zero_when_z_nan():
    prices = _prices(200)
    sig = build_signal(
        prices, mom_window=21, z_window=126, entry_scale=1.0, vol_target=0.15
    )
    assert (sig["SPY"].iloc[:125] == 0.0).all()


def test_split_index_covers_all():
    idx = pd.bdate_range("2010-01-04", "2026-10-30")
    tr, va, te = split_index(idx)
    assert len(tr) + len(va) + len(te) == len(idx)
    assert tr.max() < va.min()
    assert va.max() < te.min()


def test_profit_factor_and_max_dd():
    rets = pd.Series([0.01, -0.005, 0.02, -0.01])
    assert profit_factor(rets) > 0
    eq = (1 + rets).cumprod()
    assert max_dd(eq) <= 0


def test_worst_regime_sharpe_short_nan():
    assert np.isnan(worst_regime_sharpe(pd.Series([0.01] * 10)))


def test_benchmark_ir_p_finite():
    rng = np.random.default_rng(1)
    s = pd.Series(rng.normal(0.0002, 0.01, 300))
    b = pd.Series(rng.normal(0.0001, 0.01, 300))
    ir, p = benchmark_ir_p(s, b)
    assert np.isfinite(ir)
    assert 0.0 <= p <= 1.0


def test_perturbation_min_ratio_finite():
    prices = _prices(800)
    oos = prices.index[500:]
    base = dict(mom_window=21, z_window=126, entry_scale=1.0, vol_target=0.15)
    r = perturbation_min_ratio(prices, base, 0.5, oos)
    assert np.isfinite(r)


def test_de_risk_direction_negative_z_reduces_exposure():
    # deterministic case: TIP falls, IEF flat -> negative relmom / TIP underperforms
    n = 300
    idx = pd.bdate_range("2015-01-01", periods=n)
    spy = pd.Series(100.0, index=idx)
    tip = pd.Series(np.linspace(100, 90, n), index=idx)
    ief = pd.Series(100.0, index=idx)
    prices = pd.DataFrame({"SPY": spy, "TIP": tip, "IEF": ief}, index=idx)
    sig = build_signal(
        prices, mom_window=21, z_window=126, entry_scale=1.0, vol_target=0.15
    )
    tail = sig["SPY"].iloc[150:]
    assert (tail < 0.5).any()
