from __future__ import annotations

import numpy as np
import pandas as pd

import run_nf_20261109_05_hyg_momentum_spy as h163


def _prices(n: int = 650) -> pd.DataFrame:
    idx = pd.bdate_range("2015-01-05", periods=n)
    rng = np.random.default_rng(163)
    cols = {
        h163.SPY: 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n))),
        h163.HYG: 50 * np.exp(np.cumsum(rng.normal(0.0001, 0.004, n))),
    }
    return pd.DataFrame(cols, index=idx)


def test_make_signals_columns_and_bounds() -> None:
    p = _prices()
    sig = h163.make_signals(
        p,
        {
            "lookback": 126,
            "z_window": 126,
            "entry_scale": 1.0,
            "exit_scale": 0.0,
            "vol_target": 0.1,
        },
    )
    assert list(sig.columns) == h163.UNIVERSE
    assert (sig[h163.HYG] == 0).all()
    assert sig["SPY"].between(0.0, h163.MAX_POS + 1e-12).all()


def test_hyg_momentum_past_only() -> None:
    p = _prices()
    mom = h163.hyg_momentum(p, 63)
    # momentum is pct_change(63); first 63 should be NaN
    assert mom.iloc[:63].isna().all()
    assert mom.dropna().shape[0] > 100


def test_momentum_state_hysteresis() -> None:
    idx = pd.bdate_range("2020-01-01", periods=7)
    z = pd.Series([np.nan, 0.5, -1.2, -0.2, 0.1, 0.8, -2.0], index=idx)
    # nan->1, 0.5>=0 full->1, -1.2<=-1 de-risk->0, -0.2 hold->0,
    # 0.1>=0 full->1, 0.8>=0 full->1, -2.0<=-1 de-risk->0
    state = h163.momentum_state(z, entry_scale=1.0, exit_scale=0.0)
    np.testing.assert_allclose(state.values, [1.0, 1.0, 0.0, 0.0, 1.0, 1.0, 0.0])


def test_inverse_state_flips() -> None:
    idx = pd.bdate_range("2020-01-01", periods=7)
    z = pd.Series([np.nan, 0.5, -1.2, -0.2, 0.1, 1.5, -2.0], index=idx)
    # inverse: de-risk on strong z (>=entry 1.0), full on weak z (<=-exit 0.0)
    # nan->1, 0.5 hold 1, -1.2<=0->1, -0.2<=0->1, 0.1 hold 1, 1.5>=1.0->0, -2.0<=0->1
    state = h163.inverse_momentum_state(z, entry_scale=1.0, exit_scale=0.0)
    np.testing.assert_allclose(state.values, [1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0])


def test_hyg_momentum_z_shape() -> None:
    p = _prices()
    z = h163.hyg_momentum_z(p, 126, 126)
    assert len(z) == len(p)
    assert z.dropna().shape[0] > 100


def test_inverse_regime_differs() -> None:
    p = _prices()
    params = {
        "lookback": 126,
        "z_window": 126,
        "entry_scale": 1.0,
        "exit_scale": 0.0,
        "vol_target": 0.1,
    }
    base = h163.run_one(p, params)["signals"].attrs["state"]
    z = h163.hyg_momentum_z(p, params["lookback"], params["z_window"])
    inv_state = h163.inverse_momentum_state(z, params["entry_scale"], params["exit_scale"])
    assert not np.allclose(base.fillna(1).values, inv_state.values)
    inv = h163.inverse_regime(p, params)
    assert isinstance(inv, dict) and "sharpe" in inv


def test_splits_cover_index() -> None:
    p = _prices(900)
    train, val, test = h163._splits(p.index)
    assert (train | val | test).all()
    assert not (train & test).any()
    assert not (train & val).any()


def test_benchmark_buy_hold() -> None:
    p = _prices(300)
    mask = pd.Series(True, index=p.index)
    m = h163.benchmark_buy_hold(p, mask)
    assert set(m.keys()) >= {"sharpe", "profit_factor", "max_drawdown", "trades"}
    assert m["trades"] == 1


def test_random_exposure_matched_returns_dict() -> None:
    p = _prices(400)
    mask = pd.Series(True, index=p.index)
    m = h163.random_exposure_matched(p, mask, 0.25, 163)
    assert set(m.keys()) >= {"sharpe", "profit_factor", "max_drawdown", "trades"}


def test_grid_covers_spec_combos() -> None:
    combos = 0
    for lb in h163.LOOKBACKS:
        for zw in h163.Z_WINDOWS:
            for es in h163.ENTRY_SCALES:
                for xs in h163.EXIT_SCALES:
                    if xs > es:
                        continue
                    for vt in h163.VOL_TARGETS:
                        combos += 1
                        assert xs <= es
    assert combos == 3 * 2 * 3 * 2 * 2


def test_weak_hyg_momentum_reduces_exposure() -> None:
    idx = pd.bdate_range("2015-01-05", periods=550)
    rng = np.random.default_rng(7)
    n = len(idx)
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.008, n)))
    hyg = 50 * np.exp(np.cumsum(rng.normal(0.0001, 0.003, n)))
    # HYG crashes after midpoint -> negative momentum / de-risk
    hyg[n // 2 :] = hyg[n // 2] * np.exp(np.cumsum(rng.normal(-0.004, 0.006, n - n // 2)))
    p = pd.DataFrame({h163.SPY: spy, h163.HYG: hyg}, index=idx)
    params = {
        "lookback": 126,
        "z_window": 126,
        "entry_scale": 1.0,
        "exit_scale": 0.0,
        "vol_target": 0.1,
    }
    sig = h163.make_signals(p, params)
    z = h163.hyg_momentum_z(p, params["lookback"], params["z_window"])
    early = sig.loc[z.index[: n // 2 - 40], "SPY"].dropna()
    late = sig.loc[z.index[n // 2 + 80 :], "SPY"].dropna()
    assert not early.empty and not late.empty
    assert late.mean() <= early.mean() + 1e-9
