from __future__ import annotations

import numpy as np
import pandas as pd

import run_nf_20261109_01_ivol_dispersion_spy as h160


def _prices(n: int = 500) -> pd.DataFrame:
    idx = pd.bdate_range("2018-01-02", periods=n)
    rng = np.random.default_rng(160)
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
    etfs = {}
    for i, a in enumerate(h160.IVOL_ASSETS):
        # same drift-ish but idiosyncratic noise
        etfs[a] = 50 * np.exp(np.cumsum(rng.normal(0.0002, 0.012, n)) * (1 + 0.05 * i))
    return pd.DataFrame({"SPY": spy, **etfs}, index=idx)


def test_make_signals_columns_and_bounds() -> None:
    p = _prices()
    sig = h160.make_signals(
        p,
        {
            "ivol_lookback": 63,
            "z_window": 126,
            "entry_scale": 1.0,
            "vol_target": 0.1,
        },
    )
    assert list(sig.columns) == h160.UNIVERSE
    assert (sig[h160.IVOL_ASSETS] == 0).all().all()
    assert sig["SPY"].between(0.0, h160.MAX_POS + 1e-12).all()


def test_ivol_panel_returns_cross_sectional_std() -> None:
    p = _prices()
    ivol = h160.ivol_panel(p, 63)
    assert set(ivol.columns) == set(h160.IVOL_ASSETS)
    assert ivol.shape == (len(p), len(h160.IVOL_ASSETS))
    # residual std vs SPY equals rolling residual vol
    rets = p.pct_change()
    resid = rets["QQQ"] - rets["SPY"]
    expect = resid.rolling(63, min_periods=15).std() * np.sqrt(252.0)
    np.testing.assert_allclose(ivol["QQQ"].dropna().values, expect.dropna().values, atol=1e-9)


def test_stress_mapping_positive_z_reduces_exposure() -> None:
    p = _prices()
    params = {"ivol_lookback": 63, "z_window": 126, "entry_scale": 1.0, "vol_target": 0.1}
    sig = h160.make_signals(p, params)
    z = h160.ivol_dispersion_z(p, params["ivol_lookback"], params["z_window"])
    vscale = h160._vol_scale(p, params["vol_target"])
    expected = (
        (1.0 - (z.clip(lower=0.0) / params["entry_scale"]).clip(0.0, 1.0))
        * params["vol_target"]
        * vscale
    ).clip(0.0, h160.MAX_POS)
    mask = z.notna() & sig["SPY"].notna()
    np.testing.assert_allclose(
        sig.loc[mask, "SPY"].values, expected.loc[mask].fillna(0).values, atol=1e-12
    )


def test_inverse_falsifier_mapping_differs() -> None:
    p = _prices()
    params = {"ivol_lookback": 63, "z_window": 126, "entry_scale": 1.0, "vol_target": 0.1}
    z = h160.ivol_dispersion_z(p, params["ivol_lookback"], params["z_window"])
    stress_base = (z.clip(lower=0.0) / 1.0).clip(0.0, 1.0)
    stress_inv = ((-z).clip(lower=0.0) / 1.0).clip(0.0, 1.0)
    assert not np.allclose(stress_base.fillna(0).values, stress_inv.fillna(0).values)
    inv = h160.inverse_regime(p, params)
    assert isinstance(inv, dict) and "sharpe" in inv


def test_ivol_dispersion_z_shape() -> None:
    p = _prices()
    z = h160.ivol_dispersion_z(p, 63, 126)
    assert len(z) == len(p)
    assert isinstance(z, pd.Series)


def test_splits_cover_index() -> None:
    p = _prices(800)
    train, val, test = h160._splits(p.index)
    assert (train | val | test).all()
    assert not (train & test).any()
    assert not (train & val).any()


def test_benchmark_buy_hold() -> None:
    p = _prices(300)
    mask = pd.Series(True, index=p.index)
    m = h160.benchmark_buy_hold(p, mask)
    assert set(m.keys()) >= {"sharpe", "profit_factor", "max_drawdown", "trades"}
    assert m["trades"] == 1


def test_random_exposure_matched_returns_dict() -> None:
    p = _prices(400)
    mask = pd.Series(True, index=p.index)
    m = h160.random_exposure_matched(p, mask, 0.25, 160)
    assert set(m.keys()) >= {"sharpe", "profit_factor", "max_drawdown", "trades"}


def test_return_dispersion_control_returns_dict() -> None:
    p = _prices(400)
    params = {"ivol_lookback": 63, "z_window": 126, "entry_scale": 1.0, "vol_target": 0.1}
    m = h160.return_dispersion_control(p, params)
    assert set(m.keys()) >= {"sharpe", "profit_factor", "max_drawdown", "trades"}


def test_high_ivol_dispersion_regime_lowers_spy_exposure() -> None:
    # inject a high-IVOL-dispersion window: QQQ noise spikes -> dispersion up -> exposure down
    idx = pd.bdate_range("2016-01-04", periods=400)
    rng = np.random.default_rng(9)
    n = len(idx)
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.008, n)))
    qqq = spy.copy()
    qqq[n // 2 :] = qqq[n // 2] * np.exp(
        np.cumsum(rng.normal(0.0, 0.08, n - n // 2))  # high vol after midpoint
    )
    etfs = {"SPY": spy, "QQQ": qqq}
    for i, a in enumerate(h160.IVOL_ASSETS[1:]):
        etfs[a] = 50 * np.exp(np.cumsum(rng.normal(0.0002, 0.012, n)))
    p = pd.DataFrame(etfs, index=idx)
    params = {"ivol_lookback": 63, "z_window": 126, "entry_scale": 1.0, "vol_target": 0.1}
    sig = h160.make_signals(p, params)
    z = h160.ivol_dispersion_z(p, params["ivol_lookback"], params["z_window"])
    early = sig.loc[z.index[: n // 2 - 30], "SPY"].dropna()
    late = sig.loc[z.index[n // 2 + 30 :], "SPY"].dropna()
    assert not early.empty and not late.empty
    assert late.mean() < early.mean()
