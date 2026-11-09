from __future__ import annotations

import numpy as np
import pandas as pd

import run_nf_20261109_09_kre_xlf_stress_spy as h166


def _prices(n: int = 500) -> pd.DataFrame:
    idx = pd.bdate_range("2018-01-02", periods=n)
    rng = np.random.default_rng(166)
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
    kre = 50 * np.exp(np.cumsum(rng.normal(0.0002, 0.015, n)))
    xlf = 30 * np.exp(np.cumsum(rng.normal(0.0002, 0.011, n)))
    return pd.DataFrame({"SPY": spy, "KRE": kre, "XLF": xlf}, index=idx)


def test_make_signals_columns_and_bounds() -> None:
    p = _prices()
    sig = h166.make_signals(
        p, {"lookback": 63, "z_window": 126, "entry_scale": 1.5, "vol_target": 0.1}
    )
    assert list(sig.columns) == ["SPY", "KRE", "XLF"]
    assert (sig["KRE"] == 0).all()
    assert (sig["XLF"] == 0).all()
    assert sig["SPY"].between(0.0, h166.MAX_POS + 1e-12).all()


def test_stress_mapping_negative_z_reduces_exposure() -> None:
    p = _prices()
    params = {"lookback": 63, "z_window": 126, "entry_scale": 1.0, "vol_target": 0.1}
    sig = h166.make_signals(p, params)
    z = h166.kre_xlf_spread_z(p, params["lookback"], params["z_window"])
    vscale = h166._vol_scale(p, params["vol_target"])
    expected = (
        (1.0 - ((-z).clip(lower=0.0) / params["entry_scale"]).clip(0.0, 1.0))
        * params["vol_target"]
        * vscale
    ).clip(0.0, h166.MAX_POS)
    mask = z.notna() & sig["SPY"].notna()
    np.testing.assert_allclose(
        sig.loc[mask, "SPY"].values, expected.loc[mask].fillna(0).values, atol=1e-12
    )


def test_inverse_falsifier_mapping() -> None:
    p = _prices()
    params = {"lookback": 63, "z_window": 126, "entry_scale": 1.0, "vol_target": 0.1}
    z = h166.kre_xlf_spread_z(p, params["lookback"], params["z_window"])
    stress_base = ((-z).clip(lower=0.0) / 1.0).clip(0.0, 1.0)
    stress_inv = (z.clip(lower=0.0) / 1.0).clip(0.0, 1.0)
    assert not np.allclose(stress_base.fillna(0).values, stress_inv.fillna(0).values)
    inv = h166.inverse_regime(p, params)
    assert isinstance(inv, dict) and "sharpe" in inv


def test_spread_z_shape() -> None:
    p = _prices()
    z = h166.kre_xlf_spread_z(p, 63, 126)
    assert len(z) == len(p)
    assert isinstance(z, pd.Series)


def test_splits_cover_index() -> None:
    p = _prices(1200)
    train, val, test = h166._splits(p.index)
    assert (train | val | test).all()
    assert not (train & test).any()


def test_benchmark_buy_hold() -> None:
    p = _prices(300)
    mask = pd.Series(True, index=p.index)
    m = h166.benchmark_buy_hold(p, mask)
    assert set(m.keys()) >= {"sharpe", "profit_factor", "max_drawdown", "trades"}
    assert m["trades"] == 1


def test_negative_z_produces_lower_exposure_than_positive_z() -> None:
    p = _prices(300)
    params = {"lookback": 63, "z_window": 126, "entry_scale": 1.0, "vol_target": 0.1}
    sig = h166.make_signals(p, params)
    z = h166.kre_xlf_spread_z(p, params["lookback"], params["z_window"])
    mask = z.notna() & sig["SPY"].notna()
    neg = sig.loc[mask & (z <= -1.0), "SPY"]
    pos = sig.loc[mask & (z >= 0.0), "SPY"]
    assert len(neg) > 0 and len(pos) > 0
    assert neg.mean() < pos.mean()
