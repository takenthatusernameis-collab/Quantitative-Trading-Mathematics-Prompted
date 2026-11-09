from __future__ import annotations

import numpy as np
import pandas as pd

import run_nf_20261109_08_spy_vix_corr_regime as h165


def _prices(n: int = 500) -> pd.DataFrame:
    idx = pd.bdate_range("2018-01-02", periods=n)
    rng = np.random.default_rng(165)
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
    vix = 20 * np.exp(np.cumsum(rng.normal(0.0, 0.05, n)))
    return pd.DataFrame({"SPY": spy, "^VIX": vix}, index=idx)


def test_make_signals_columns_and_bounds() -> None:
    p = _prices()
    sig = h165.make_signals(
        p, {"corr_window": 63, "z_window": 126, "entry_scale": 1.5, "vol_target": 0.1}
    )
    assert list(sig.columns) == ["SPY", "^VIX"]
    assert (sig["^VIX"] == 0).all()
    assert sig["SPY"].between(0.0, h165.MAX_POS + 1e-12).all()


def test_stress_mapping_negative_z_reduces_exposure() -> None:
    p = _prices()
    params = {"corr_window": 63, "z_window": 126, "entry_scale": 1.0, "vol_target": 0.1}
    sig = h165.make_signals(p, params)
    z = h165.spy_vix_corr_z(p, params["corr_window"], params["z_window"])
    vscale = h165._vol_scale(p, params["vol_target"])
    expected = (
        (1.0 - ((-z).clip(lower=0.0) / params["entry_scale"]).clip(0.0, 1.0))
        * params["vol_target"]
        * vscale
    ).clip(0.0, h165.MAX_POS)
    mask = z.notna() & sig["SPY"].notna()
    np.testing.assert_allclose(
        sig.loc[mask, "SPY"].values, expected.loc[mask].fillna(0).values, atol=1e-12
    )


def test_inverse_falsifier_mapping() -> None:
    p = _prices()
    params = {"corr_window": 63, "z_window": 126, "entry_scale": 1.0, "vol_target": 0.1}
    z = h165.spy_vix_corr_z(p, params["corr_window"], params["z_window"])
    stress_base = ((-z).clip(lower=0.0) / 1.0).clip(0.0, 1.0)
    stress_inv = (z.clip(lower=0.0) / 1.0).clip(0.0, 1.0)
    assert not np.allclose(stress_base.fillna(0).values, stress_inv.fillna(0).values)
    inv = h165.inverse_regime(p, params)
    assert isinstance(inv, dict) and "sharpe" in inv


def test_spy_vix_corr_z_shape() -> None:
    p = _prices()
    z = h165.spy_vix_corr_z(p, 63, 126)
    assert len(z) == len(p)
    assert isinstance(z, pd.Series)


def test_splits_cover_index() -> None:
    p = _prices(1200)
    train, val, test = h165._splits(p.index)
    assert (train | val | test).all()
    assert not (train & test).any()


def test_benchmark_buy_hold() -> None:
    p = _prices(300)
    mask = pd.Series(True, index=p.index)
    m = h165.benchmark_buy_hold(p, mask)
    assert set(m.keys()) >= {"sharpe", "profit_factor", "max_drawdown", "trades"}
    assert m["trades"] == 1


def test_high_negative_correlation_increases_stress() -> None:
    idx = pd.bdate_range("2016-01-04", periods=520)
    rng = np.random.default_rng(11)
    spy_ret = rng.normal(0.0002, 0.008, len(idx))
    spy = 100.0 * np.exp(np.cumsum(spy_ret))
    vix = 20.0 * np.exp(
        np.cumsum(
            np.concatenate([rng.normal(0.0, 0.005, len(idx) // 2), -spy_ret[len(idx) // 2 :]])
        )
    )
    p = pd.DataFrame({"SPY": spy, "^VIX": vix}, index=idx)
    z = h165.spy_vix_corr_z(p, 21, 60)
    vscale = h165._vol_scale(p, 0.1)
    stress = ((-z).clip(lower=0.0) / 1.0).clip(0.0, 1.0) * 0.1 * vscale
    early = stress.iloc[120:260].dropna()
    shock = stress.iloc[340:480].dropna()
    assert len(early) > 0 and len(shock) > 0
    assert shock.mean() > early.mean()
