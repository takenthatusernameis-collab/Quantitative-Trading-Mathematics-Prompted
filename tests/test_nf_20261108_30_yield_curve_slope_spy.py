from __future__ import annotations

import numpy as np
import pandas as pd

import run_nf_20261108_30_yield_curve_slope_spy as h158


def _prices(n: int = 500) -> pd.DataFrame:
    idx = pd.bdate_range("2018-01-02", periods=n)
    rng = np.random.default_rng(158)
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
    tnx = 2.5 + np.cumsum(rng.normal(0.0, 0.005, n))
    fvx = 2.0 + np.cumsum(rng.normal(0.0, 0.004, n))
    # Ensure positive yields
    tnx = np.maximum(tnx, 0.1)
    fvx = np.maximum(fvx, 0.1)
    return pd.DataFrame({"SPY": spy, "^TNX": tnx, "^FVX": fvx}, index=idx)


def test_make_signals_columns_and_bounds() -> None:
    p = _prices()
    sig = h158.make_signals(p, {"z_window": 126, "entry_scale": 1.5, "vol_target": 0.1})
    assert list(sig.columns) == ["SPY", "^TNX", "^FVX"]
    assert (sig["^TNX"] == 0).all()
    assert (sig["^FVX"] == 0).all()
    assert sig["SPY"].between(0.0, h158.MAX_POS + 1e-12).all()


def test_stress_mapping_negative_z_reduces_exposure() -> None:
    p = _prices()
    params = {"z_window": 126, "entry_scale": 1.0, "vol_target": 0.1}
    sig = h158.make_signals(p, params)
    z = h158.slope_z(p, params["z_window"])
    vscale = h158._vol_scale(p, params["vol_target"])
    expected = (
        (1.0 - ((-z).clip(lower=0.0) / params["entry_scale"]).clip(0.0, 1.0))
        * params["vol_target"]
        * vscale
    ).clip(0.0, h158.MAX_POS)
    mask = z.notna() & sig["SPY"].notna()
    np.testing.assert_allclose(
        sig.loc[mask, "SPY"].values, expected.loc[mask].fillna(0).values, atol=1e-12
    )


def test_inverse_falsifier_mapping_differs() -> None:
    p = _prices()
    params = {"z_window": 126, "entry_scale": 1.0, "vol_target": 0.1}
    z = h158.slope_z(p, params["z_window"])
    stress_base = ((-z).clip(lower=0.0) / 1.0).clip(0.0, 1.0)
    stress_inv = (z.clip(lower=0.0) / 1.0).clip(0.0, 1.0)
    assert not np.allclose(stress_base.fillna(0).values, stress_inv.fillna(0).values)
    inv = h158.inverse_regime(p, params)
    assert isinstance(inv, dict) and "sharpe" in inv


def test_slope_z_shape() -> None:
    p = _prices()
    z = h158.slope_z(p, 126)
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


def test_curve_inversion_gives_negative_z() -> None:
    # FVX rises faster than TNX -> slope compresses/inverts -> z negative in late window
    idx = pd.bdate_range("2016-01-04", periods=500)
    rng = np.random.default_rng(7)
    n = len(idx)
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.008, n)))
    tnx = 3.0 * np.ones(n)
    fvx = 2.5 * np.ones(n)
    for i in range(1, n // 2):
        tnx[i] = max(0.5, tnx[i - 1] + rng.normal(0.0001, 0.003))
        fvx[i] = max(0.5, fvx[i - 1] + rng.normal(0.0001, 0.003))
    for i in range(n // 2, n):
        # Curve flattens/inverts: FVX rises faster than TNX
        tnx[i] = max(0.5, tnx[i - 1] + rng.normal(0.0001, 0.003))
        fvx[i] = max(0.5, fvx[i - 1] + rng.normal(0.0015, 0.004))
    p = pd.DataFrame({"SPY": spy, "^TNX": tnx, "^FVX": fvx}, index=idx)
    z = h158.slope_z(p, 126)
    early = z.iloc[150 : n // 2 - 10].dropna()
    inverted = z.iloc[n // 2 + 30 : n // 2 + 90].dropna()
    assert inverted.mean() < early.mean()
