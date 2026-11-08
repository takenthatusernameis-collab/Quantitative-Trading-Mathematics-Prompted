from __future__ import annotations

import numpy as np
import pandas as pd

import run_nf_20261108_17_short_rate_level as h154


def _prices(n: int = 400) -> pd.DataFrame:
    idx = pd.bdate_range("2018-01-02", periods=n)
    rng = np.random.default_rng(7)
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
    shy = 80 * np.exp(np.cumsum(rng.normal(0.00005, 0.0015, n)))
    return pd.DataFrame({"SPY": spy, "SHY": shy}, index=idx)


def test_make_signals_columns_and_bounds() -> None:
    p = _prices()
    sig = h154.make_signals(p, shy_window=21, z_window=63, entry_scale=1.5, vol_target=0.1)
    assert list(sig.columns) == ["SPY", "SHY"]
    assert (sig["SHY"] == 0).all()
    assert sig["SPY"].between(-h154.MAX_POS, h154.MAX_POS).all()


def test_stress_on_negative_z_reduces_exposure() -> None:
    # SHY drops sharply (tight/high-rate proxy) -> negative z -> reduced exposure
    n = 300
    idx = pd.bdate_range("2019-01-02", periods=n)
    spy = pd.Series(100.0, index=idx)
    shy = pd.Series(80.0, index=idx)
    shy.iloc[200:] = 75.0  # sharp drop
    p = pd.DataFrame({"SPY": spy, "SHY": shy}, index=idx)
    sig = h154.make_signals(p, shy_window=21, z_window=63, entry_scale=1.0, vol_target=0.15)
    # after drop, exposure should be lower than early period median
    early = sig["SPY"].iloc[80:180].median()
    late = sig["SPY"].iloc[230:280].median()
    assert late <= early + 1e-9


def test_inverse_differs_from_base() -> None:
    p = _prices()
    base = h154.make_signals(p, shy_window=21, z_window=63, entry_scale=1.5, vol_target=0.1)
    inv = h154.make_signals_inverse(p, shy_window=21, z_window=63, entry_scale=1.5, vol_target=0.1)
    assert not np.allclose(base["SPY"].values, inv["SPY"].values)


def test_sharpe_and_metrics_safe() -> None:
    assert h154.sharpe(pd.Series([0.0, 0.0])) == 0.0
    assert h154.profit_factor(pd.Series([-0.01, -0.02])) == 0.0
    assert h154.max_drawdown(pd.Series([1.0, 1.1, 1.0])) <= 0.0


def test_worst_regime_returns_finite() -> None:
    p = _prices(500)
    ret = p["SPY"].pct_change().fillna(0.0)
    val = h154.worst_regime_sharpe(ret, p["SPY"])
    assert np.isfinite(val)


def test_zscore_shape() -> None:
    s = pd.Series(np.arange(100.0))
    z = h154.zscore(s, 20)
    assert len(z) == 100
