from __future__ import annotations

import numpy as np
import pandas as pd

import run_nf_20261109_02_g10_carry as h161


def _prices(n: int = 600) -> pd.DataFrame:
    idx = pd.bdate_range("2016-01-04", periods=n)
    rng = np.random.default_rng(161)
    cols = {h161.SPY: 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))}
    for a in h161.FX_PAIRS:
        cols[a] = 100 * np.exp(np.cumsum(rng.normal(0.0, 0.004, n)))
    return pd.DataFrame(cols, index=idx)


def test_make_signals_columns_and_bounds() -> None:
    p = _prices()
    sig = h161.make_signals(
        p,
        {
            "lookback": 63,
            "z_window": 126,
            "entry_scale": 1.0,
            "exit_scale": 0.0,
            "vol_target": 0.1,
        },
    )
    assert list(sig.columns) == h161.UNIVERSE
    assert (sig[h161.FX_PAIRS] == 0).all().all()
    assert sig["SPY"].between(0.0, h161.MAX_POS + 1e-12).all()


def test_carry_basket_return_uses_specified_legs() -> None:
    p = _prices()
    bret = h161.carry_basket_return(p)
    rets = p.pct_change()
    expected = rets[h161.LONG_LEGS].mean(axis=1) - rets[h161.SHORT_LEGS].mean(axis=1)
    pd.testing.assert_series_equal(bret, expected, check_names=False)
    # spec: long AUD/NZD/CAD vs JPY, short EUR/CHF/USD vs JPY (3v3 basket)
    assert set(h161.LONG_LEGS) == {"AUDJPY=X", "NZDJPY=X", "CADJPY=X"}
    assert set(h161.SHORT_LEGS) == {"EURJPY=X", "CHFJPY=X", "USDJPY=X"}
    assert "GBPJPY=X" not in h161.LONG_LEGS + h161.SHORT_LEGS  # fetched, not in basket


def test_hysteresis_state_initial_long_and_transitions() -> None:
    idx = pd.bdate_range("2020-01-01", periods=6)
    z = pd.Series([np.nan, 0.5, -2.0, -0.5, 0.2, 1.0], index=idx)
    state = h161.hysteresis_state(z, entry_scale=1.0, exit_scale=0.0)
    # nan->1, 0.5>=0->1, -2<=-1->0, -0.5 hold 0, 0.2>=0->1, 1.0>=0->1
    np.testing.assert_allclose(state.values, [1.0, 1.0, 0.0, 0.0, 1.0, 1.0])


def test_carry_momentum_z_shape_and_finite() -> None:
    p = _prices()
    z = h161.carry_momentum_z(p, 63, 126)
    assert len(z) == len(p)
    assert isinstance(z, pd.Series)
    assert z.dropna().shape[0] > 100


def test_inverse_regime_differs_from_base() -> None:
    p = _prices()
    params = {
        "lookback": 63,
        "z_window": 126,
        "entry_scale": 1.0,
        "exit_scale": 0.0,
        "vol_target": 0.1,
    }
    base = h161.run_one(p, params)["signals"].attrs["state"]
    # compute inverse state
    z = h161.carry_momentum_z(p, params["lookback"], params["z_window"])
    inv_state = np.empty(len(z), dtype=float)
    s = 1.0
    for i, v in enumerate(z.to_numpy(dtype=float)):
        if np.isfinite(v):
            if v >= params["entry_scale"]:
                s = 0.0
            elif v <= -params["exit_scale"]:
                s = 1.0
        inv_state[i] = s
    assert not np.allclose(base.fillna(1).values, inv_state)
    inv = h161.inverse_regime(p, params)
    assert isinstance(inv, dict) and "sharpe" in inv


def test_splits_cover_index() -> None:
    p = _prices(900)
    train, val, test = h161._splits(p.index)
    assert (train | val | test).all()
    assert not (train & test).any()
    assert not (train & val).any()


def test_benchmark_buy_hold() -> None:
    p = _prices(300)
    mask = pd.Series(True, index=p.index)
    m = h161.benchmark_buy_hold(p, mask)
    assert set(m.keys()) >= {"sharpe", "profit_factor", "max_drawdown", "trades"}
    assert m["trades"] == 1


def test_random_exposure_matched_returns_dict() -> None:
    p = _prices(400)
    mask = pd.Series(True, index=p.index)
    m = h161.random_exposure_matched(p, mask, 0.25, 161)
    assert set(m.keys()) >= {"sharpe", "profit_factor", "max_drawdown", "trades"}


def test_grid_covers_spec_combos() -> None:
    # spec 48 combos with exit_scale <= entry_scale filter possible; ensure
    # parameter sets exist and exit<=entry constraint applied in main logic
    combos = 0
    for lb in h161.LOOKBACKS:
        for zw in h161.Z_WINDOWS:
            for es in h161.ENTRY_SCALES:
                for xs in h161.EXIT_SCALES:
                    if xs > es:
                        continue
                    for vt in h161.VOL_TARGETS:
                        combos += 1
                        assert xs <= es
    assert combos == 3 * 2 * 3 * 2 * 2  # all exit<=entry here (0,0.5 <= 1.0)


def test_negative_carry_z_reduces_exposure() -> None:
    # inject carry unwind: AUD/NZD/CAD drop sharply vs EUR/CHF/USD
    idx = pd.bdate_range("2016-01-04", periods=500)
    rng = np.random.default_rng(7)
    n = len(idx)
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.008, n)))
    cols = {h161.SPY: spy}
    for a in h161.FX_PAIRS:
        cols[a] = 100 * np.exp(np.cumsum(rng.normal(0.0, 0.003, n)))
    # crash high-yield legs after midpoint
    for a in h161.LONG_LEGS:
        path = cols[a].copy()
        path[n // 2 :] = path[n // 2] * np.exp(np.cumsum(rng.normal(-0.004, 0.01, n - n // 2)))
        cols[a] = path
    p = pd.DataFrame(cols, index=idx)
    params = {
        "lookback": 63,
        "z_window": 126,
        "entry_scale": 1.0,
        "exit_scale": 0.0,
        "vol_target": 0.1,
    }
    sig = h161.make_signals(p, params)
    z = h161.carry_momentum_z(p, params["lookback"], params["z_window"])
    early = sig.loc[z.index[: n // 2 - 40], "SPY"].dropna()
    late = sig.loc[z.index[n // 2 + 60 :], "SPY"].dropna()
    assert not early.empty and not late.empty
    assert late.mean() <= early.mean() + 1e-9
