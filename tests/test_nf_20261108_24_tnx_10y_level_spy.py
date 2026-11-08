from __future__ import annotations

import numpy as np
import pandas as pd

import run_nf_20261108_24_tnx_10y_level_spy as h155


def _prices(n: int = 500) -> pd.DataFrame:
    idx = pd.bdate_range("2018-01-02", periods=n)
    rng = np.random.default_rng(17)
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
    tnx = 2.5 + np.cumsum(rng.normal(0.0, 0.03, n))
    tnx = np.clip(tnx, 0.5, 5.5)
    return pd.DataFrame({"SPY": spy, "^TNX": tnx}, index=idx)


def test_make_signals_columns_and_bounds() -> None:
    p = _prices()
    sig = h155.make_signals(p, {"z_window": 63, "entry_scale": 1.5, "vol_target": 0.1})
    assert list(sig.columns) == ["SPY", "^TNX"]
    assert (sig["^TNX"] == 0).all()
    assert sig["SPY"].between(0.0, h155.MAX_POS + 1e-12).all()


def test_stress_mapping_positive_z_reduces_exposure() -> None:
    # pre-registered: stress activates on positive z (abnormally high 10Y yield)
    p = _prices()
    params = {"z_window": 126, "entry_scale": 1.0, "vol_target": 0.1}
    sig = h155.make_signals(p, params)
    z = h155.tnx_level_z(p, params["z_window"])
    vscale = h155._vol_scale(p, params["vol_target"])
    expected = (
        (1.0 - (z.clip(lower=0.0) / params["entry_scale"]).clip(0.0, 1.0))
        * params["vol_target"]
        * vscale
    ).clip(0.0, h155.MAX_POS)
    mask = z.notna() & sig["SPY"].notna()
    np.testing.assert_allclose(
        sig.loc[mask, "SPY"].values, expected.loc[mask].fillna(0).values, atol=1e-12
    )
    pos = z > 0.5
    if pos.any():
        full = (params["vol_target"] * vscale).clip(0.0, h155.MAX_POS)
        assert (sig.loc[pos, "SPY"] <= full.loc[pos] + 1e-12).all()


def test_inverse_falsifier_mapping() -> None:
    p = _prices()
    params = {"z_window": 126, "entry_scale": 1.0, "vol_target": 0.1}
    z = h155.tnx_level_z(p, params["z_window"])
    stress_base = (z.clip(lower=0.0) / 1.0).clip(0.0, 1.0)
    stress_inv = ((-z).clip(lower=0.0) / 1.0).clip(0.0, 1.0)
    assert not np.allclose(stress_base.fillna(0).values, stress_inv.fillna(0).values)
    inv = h155.inverse_regime(p, params)
    assert isinstance(inv, dict) and "sharpe" in inv


def test_tnx_level_z_shape() -> None:
    p = _prices()
    z = h155.tnx_level_z(p, 63)
    assert len(z) == len(p)
    assert isinstance(z, pd.Series)


def test_splits_cover_index() -> None:
    p = _prices(800)
    train, val, test = h155._splits(p.index)
    assert (train | val | test).all()
    assert not (train & test).any()


def test_benchmark_buy_hold() -> None:
    p = _prices(300)
    mask = pd.Series(True, index=p.index)
    m = h155.benchmark_buy_hold(p, mask)
    assert set(m.keys()) >= {"sharpe", "profit_factor", "max_drawdown", "trades"}
    assert m["trades"] == 1
