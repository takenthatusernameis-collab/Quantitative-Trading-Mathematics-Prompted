from __future__ import annotations

import numpy as np
import pandas as pd

import run_nf_20261108_27_ewj_spy_relmom as h157


def _prices(n: int = 500) -> pd.DataFrame:
    idx = pd.bdate_range("2018-01-02", periods=n)
    rng = np.random.default_rng(157)
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
    ewj = 60 * np.exp(np.cumsum(rng.normal(0.0002, 0.011, n)))
    return pd.DataFrame({"SPY": spy, "EWJ": ewj}, index=idx)


def test_make_signals_columns_and_bounds() -> None:
    p = _prices()
    sig = h157.make_signals(
        p, {"mom_window": 21, "z_window": 126, "entry_scale": 1.5, "vol_target": 0.1}
    )
    assert list(sig.columns) == ["SPY", "EWJ"]
    assert (sig["EWJ"] == 0).all()
    assert sig["SPY"].between(0.0, h157.MAX_POS + 1e-12).all()


def test_stress_mapping_negative_z_reduces_exposure() -> None:
    p = _prices()
    params = {"mom_window": 21, "z_window": 126, "entry_scale": 1.0, "vol_target": 0.1}
    sig = h157.make_signals(p, params)
    z = h157.relmom_z(p, params["mom_window"], params["z_window"])
    vscale = h157._vol_scale(p, params["vol_target"])
    expected = (
        (1.0 - ((-z).clip(lower=0.0) / params["entry_scale"]).clip(0.0, 1.0))
        * params["vol_target"]
        * vscale
    ).clip(0.0, h157.MAX_POS)
    mask = z.notna() & sig["SPY"].notna()
    np.testing.assert_allclose(
        sig.loc[mask, "SPY"].values, expected.loc[mask].fillna(0).values, atol=1e-12
    )


def test_inverse_falsifier_mapping_differs() -> None:
    p = _prices()
    params = {"mom_window": 21, "z_window": 126, "entry_scale": 1.0, "vol_target": 0.1}
    z = h157.relmom_z(p, params["mom_window"], params["z_window"])
    stress_base = ((-z).clip(lower=0.0) / 1.0).clip(0.0, 1.0)
    stress_inv = (z.clip(lower=0.0) / 1.0).clip(0.0, 1.0)
    assert not np.allclose(stress_base.fillna(0).values, stress_inv.fillna(0).values)
    inv = h157.inverse_regime(p, params)
    assert isinstance(inv, dict) and "sharpe" in inv


def test_relmom_z_shape() -> None:
    p = _prices()
    z = h157.relmom_z(p, 21, 126)
    assert len(z) == len(p)
    assert isinstance(z, pd.Series)


def test_splits_cover_index() -> None:
    p = _prices(800)
    train, val, test = h157._splits(p.index)
    assert (train | val | test).all()
    assert not (train & test).any()


def test_benchmark_buy_hold() -> None:
    p = _prices(300)
    mask = pd.Series(True, index=p.index)
    m = h157.benchmark_buy_hold(p, mask)
    assert set(m.keys()) >= {"sharpe", "profit_factor", "max_drawdown", "trades"}
    assert m["trades"] == 1


def test_ewj_underperformance_gives_negative_z() -> None:
    # EWJ drops sharply late -> relmom negative -> z negative in late window
    idx = pd.bdate_range("2016-01-04", periods=500)
    rng = np.random.default_rng(7)
    n = len(idx)
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.008, n)))
    ewj = 60.0 * np.ones(n)
    for i in range(1, n // 2):
        ewj[i] = ewj[i - 1] * (1 + rng.normal(0.0003, 0.006))
    for i in range(n // 2, n):
        ewj[i] = ewj[i - 1] * (1 + rng.normal(-0.002, 0.012))
    p = pd.DataFrame({"SPY": spy, "EWJ": ewj}, index=idx)
    z = h157.relmom_z(p, 21, 126)
    early = z.iloc[150 : n // 2 - 10].dropna()
    weak = z.iloc[n // 2 + 30 : n // 2 + 90].dropna()
    assert weak.mean() < early.mean()
