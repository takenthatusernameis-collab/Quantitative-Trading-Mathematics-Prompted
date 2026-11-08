from __future__ import annotations

import numpy as np
import pandas as pd

import run_nf_20261108_30_vix_rv_vrp_spy as h158


def _prices(n: int = 500) -> pd.DataFrame:
    idx = pd.bdate_range("2018-01-02", periods=n)
    rng = np.random.default_rng(158)
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
    vix = 15 + np.abs(rng.normal(5, 3, n))
    return pd.DataFrame({"SPY": spy, "^VIX": vix}, index=idx)


def test_make_signals_columns_and_bounds() -> None:
    p = _prices()
    sig = h158.make_signals(
        p, {"rv_window": 21, "z_window": 126, "entry_scale": 1.5, "vol_target": 0.1}
    )
    assert list(sig.columns) == ["SPY", "^VIX"]
    assert (sig["^VIX"] == 0).all()
    assert sig["SPY"].between(0.0, h158.MAX_POS + 1e-12).all()


def test_stress_mapping_positive_z_reduces_exposure() -> None:
    p = _prices()
    params = {"rv_window": 21, "z_window": 126, "entry_scale": 1.0, "vol_target": 0.1}
    sig = h158.make_signals(p, params)
    z = h158.vix_rv_spread_z(p, params["rv_window"], params["z_window"])
    vscale = h158._vol_scale(p, params["vol_target"])
    expected = (
        (1.0 - (z.clip(lower=0.0) / params["entry_scale"]).clip(0.0, 1.0))
        * params["vol_target"]
        * vscale
    ).clip(0.0, h158.MAX_POS)
    mask = z.notna() & sig["SPY"].notna()
    np.testing.assert_allclose(
        sig.loc[mask, "SPY"].values, expected.loc[mask].fillna(0).values, atol=1e-12
    )


def test_inverse_falsifier_mapping_differs() -> None:
    p = _prices()
    params = {"rv_window": 21, "z_window": 126, "entry_scale": 1.0, "vol_target": 0.1}
    z = h158.vix_rv_spread_z(p, params["rv_window"], params["z_window"])
    stress_base = (z.clip(lower=0.0) / 1.0).clip(0.0, 1.0)
    stress_inv = ((-z).clip(lower=0.0) / 1.0).clip(0.0, 1.0)
    assert not np.allclose(stress_base.fillna(0).values, stress_inv.fillna(0).values)
    inv = h158.inverse_regime(p, params)
    assert isinstance(inv, dict) and "sharpe" in inv


def test_vix_rv_spread_z_shape() -> None:
    p = _prices()
    z = h158.vix_rv_spread_z(p, 21, 126)
    assert len(z) == len(p)
    assert isinstance(z, pd.Series)


def test_splits_cover_index() -> None:
    p = _prices(800)
    train, val, test = h158._splits(p.index)
    assert (train | val | test).all()
    assert not (train & test).any()


def test_benchmark_buy_hold() -> None:
    p = _prices(300)
    mask = pd.Series(True, index=p.index)
    m = h158.benchmark_buy_hold(p, mask)
    assert set(m.keys()) >= {"sharpe", "profit_factor", "max_drawdown", "trades"}
    assert m["trades"] == 1


def test_vix_jump_above_realized_gives_positive_z() -> None:
    # VIX jumps up mid-sample vs stable SPY realized vol -> spread rises ->
    # z positive in late window (rolling mean still catching up)
    idx = pd.bdate_range("2016-01-04", periods=500)
    rng = np.random.default_rng(7)
    n = len(idx)
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.008, n)))
    vix = np.where(np.arange(n) < n // 2, 15.0, 35.0)  # regime jump at midpoint
    p = pd.DataFrame({"SPY": spy, "^VIX": vix}, index=idx)
    z = h158.vix_rv_spread_z(p, 21, 126)
    early = z.iloc[150 : n // 2 - 10].dropna()
    late = z.iloc[n // 2 + 30 : n // 2 + 90].dropna()
    assert late.mean() > early.mean()
