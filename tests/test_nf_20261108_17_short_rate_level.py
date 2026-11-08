from __future__ import annotations

import numpy as np
import pandas as pd

import run_nf_20261108_17_short_rate_level as h154


def _prices(n: int = 500) -> pd.DataFrame:
    idx = pd.bdate_range("2018-01-02", periods=n)
    rng = np.random.default_rng(7)
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
    shy = 80 * np.exp(np.cumsum(rng.normal(0.00005, 0.0015, n)))
    return pd.DataFrame({"SPY": spy, "SHY": shy}, index=idx)


def test_make_signals_columns_and_bounds() -> None:
    p = _prices()
    sig = h154.make_signals(
        p, {"shy_window": 21, "z_window": 63, "entry_scale": 1.5, "vol_target": 0.1}
    )
    assert list(sig.columns) == ["SPY", "SHY"]
    assert (sig["SHY"] == 0).all()
    assert sig["SPY"].between(0.0, h154.MAX_POS + 1e-12).all()


def test_stress_mapping_negative_z_reduces_exposure() -> None:
    # Direct mapping check: stress activates on negative z (tight/high-rate proxy)
    p = _prices()
    params = {"shy_window": 21, "z_window": 126, "entry_scale": 1.0, "vol_target": 0.1}
    sig = h154.make_signals(p, params)
    z = h154.shy_cumret_z(p, params["shy_window"], params["z_window"])
    vscale = h154._vol_scale(p, params["vol_target"])
    expected = (
        (1.0 - ((-z).clip(lower=0.0) / params["entry_scale"]).clip(0.0, 1.0))
        * params["vol_target"]
        * vscale
    ).clip(0.0, h154.MAX_POS)
    # compare where z is finite
    mask = z.notna() & sig["SPY"].notna()
    np.testing.assert_allclose(
        sig.loc[mask, "SPY"].values, expected.loc[mask].fillna(0).values, atol=1e-12
    )
    # negative z -> lower or equal exposure than full (stress >= 0)
    neg = z < -0.5
    if neg.any():
        full = (params["vol_target"] * vscale).clip(0.0, h154.MAX_POS)
        assert (sig.loc[neg, "SPY"] <= full.loc[neg] + 1e-12).all()


def test_inverse_falsifier_mapping() -> None:
    p = _prices()
    params = {"shy_window": 21, "z_window": 126, "entry_scale": 1.0, "vol_target": 0.1}
    z = h154.shy_cumret_z(p, params["shy_window"], params["z_window"])
    stress_base = ((-z).clip(lower=0.0) / 1.0).clip(0.0, 1.0)
    stress_inv = (z.clip(lower=0.0) / 1.0).clip(0.0, 1.0)
    assert not np.allclose(stress_base.fillna(0).values, stress_inv.fillna(0).values)
    inv = h154.inverse_regime(p, params)
    assert isinstance(inv, dict) and "sharpe" in inv


def test_shy_cumret_z_shape() -> None:
    p = _prices()
    z = h154.shy_cumret_z(p, 21, 63)
    assert len(z) == len(p)
    assert isinstance(z, pd.Series)


def test_splits_cover_index() -> None:
    p = _prices(800)
    train, val, test = h154._splits(p.index)
    assert (train | val | test).all()
    assert not (train & test).any()


def test_benchmark_buy_hold() -> None:
    p = _prices(300)
    mask = pd.Series(True, index=p.index)
    m = h154.benchmark_buy_hold(p, mask)
    assert set(m.keys()) >= {"sharpe", "profit_factor", "max_drawdown", "trades"}
    assert m["trades"] == 1
