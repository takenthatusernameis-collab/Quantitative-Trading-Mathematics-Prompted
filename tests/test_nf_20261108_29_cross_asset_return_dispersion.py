from __future__ import annotations

import numpy as np
import pandas as pd

import run_nf_20261108_29_cross_asset_return_dispersion as h162


def _prices(n: int = 600) -> pd.DataFrame:
    idx = pd.bdate_range("2016-01-04", periods=n)
    rng = np.random.default_rng(162)
    cols = {h162.SPY: 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))}
    for a in h162.ASSETS:
        cols[a] = 100 * np.exp(np.cumsum(rng.normal(0.0, 0.004, n)))
    return pd.DataFrame(cols, index=idx)


def test_make_signals_columns_and_bounds() -> None:
    p = _prices()
    sig = h162.make_signals(
        p,
        {
            "z_window": 126,
            "entry_scale": 1.0,
            "exit_scale": 0.0,
            "vol_target": 0.1,
        },
    )
    assert list(sig.columns) == h162.UNIVERSE
    assert (sig[h162.ASSETS] == 0).all().all()
    assert sig["SPY"].between(0.0, h162.MAX_POS + 1e-12).all()


def test_cross_asset_dispersion_uses_all_assets() -> None:
    p = _prices()
    disp = h162.cross_asset_dispersion(p)
    rets = p.pct_change()
    expected = rets.std(axis=1)
    pd.testing.assert_series_equal(disp, expected, check_names=False)
    assert set(h162.UNIVERSE) == {"SPY", "TLT", "GLD", "UUP"}


def test_dispersion_state_initial_full_and_transitions() -> None:
    idx = pd.bdate_range("2020-01-01", periods=6)
    z = pd.Series([np.nan, 0.5, 3.0, 0.2, -0.1, 1.0], index=idx)
    # nan->1, 0.5 hold 1, 3.0>=1.0->0, 0.2 hold 0, -0.1<=0.0->1, 1.0>=1.0->0
    state = h162.dispersion_state(z, entry_scale=1.0, exit_scale=0.0)
    np.testing.assert_allclose(state.values, [1.0, 1.0, 0.0, 0.0, 1.0, 0.0])


def test_inverse_dispersion_state_flips_direction() -> None:
    idx = pd.bdate_range("2020-01-01", periods=6)
    z = pd.Series([np.nan, 0.5, 3.0, 0.2, -0.1, 1.0], index=idx)
    # inverse: nan->1, 0.5 hold 1, 3.0>=entry(1.0)->1, 0.2 hold 1, -0.1<=exit(0.0)->0, 1.0>=entry->1
    state = h162.inverse_dispersion_state(z, entry_scale=1.0, exit_scale=0.0)
    np.testing.assert_allclose(state.values, [1.0, 1.0, 1.0, 1.0, 0.0, 1.0])


def test_dispersion_z_shape_and_finite() -> None:
    p = _prices()
    z = h162.dispersion_z(p, 126)
    assert len(z) == len(p)
    assert isinstance(z, pd.Series)
    assert z.dropna().shape[0] > 100


def test_inverse_regime_differs_from_base() -> None:
    p = _prices()
    params = {
        "z_window": 126,
        "entry_scale": 1.0,
        "exit_scale": 0.0,
        "vol_target": 0.1,
    }
    base = h162.run_one(p, params)["signals"].attrs["state"]
    z = h162.dispersion_z(p, params["z_window"])
    inv_state = h162.inverse_dispersion_state(z, params["entry_scale"], params["exit_scale"])
    assert not np.allclose(base.fillna(1).values, inv_state.values)
    inv = h162.inverse_regime(p, params)
    assert isinstance(inv, dict) and "sharpe" in inv


def test_splits_cover_index() -> None:
    p = _prices(900)
    train, val, test = h162._splits(p.index)
    assert (train | val | test).all()
    assert not (train & test).any()
    assert not (train & val).any()


def test_benchmark_buy_hold() -> None:
    p = _prices(300)
    mask = pd.Series(True, index=p.index)
    m = h162.benchmark_buy_hold(p, mask)
    assert set(m.keys()) >= {"sharpe", "profit_factor", "max_drawdown", "trades"}
    assert m["trades"] == 1


def test_random_exposure_matched_returns_dict() -> None:
    p = _prices(400)
    mask = pd.Series(True, index=p.index)
    m = h162.random_exposure_matched(p, mask, 0.25, 162)
    assert set(m.keys()) >= {"sharpe", "profit_factor", "max_drawdown", "trades"}


def test_grid_covers_spec_combos() -> None:
    combos = 0
    for zw in h162.Z_WINDOWS:
        for es in h162.ENTRY_SCALES:
            for xs in h162.EXIT_SCALES:
                if xs > es:
                    continue
                for vt in h162.VOL_TARGETS:
                    combos += 1
                    assert xs <= es
    assert combos == 2 * 3 * 2 * 2  # z_window x entry x exit x vol


def test_high_dispersion_reduces_exposure() -> None:
    # inject cross-asset stress: TLT crashes vs SPY/GLD/UUP after midpoint
    idx = pd.bdate_range("2016-01-04", periods=500)
    rng = np.random.default_rng(7)
    n = len(idx)
    base = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.008, n)))
    cols = {h162.SPY: base.copy()}
    for a in h162.ASSETS:
        cols[a] = 100 * np.exp(np.cumsum(rng.normal(0.0, 0.003, n)))
    # crash TLT after midpoint -> dispersion jumps
    tlt = cols["TLT"].copy()
    tlt[n // 2 :] = tlt[n // 2] * np.exp(np.cumsum(rng.normal(-0.006, 0.01, n - n // 2)))
    cols["TLT"] = tlt
    p = pd.DataFrame(cols, index=idx)
    params = {
        "z_window": 126,
        "entry_scale": 1.0,
        "exit_scale": 0.0,
        "vol_target": 0.1,
    }
    sig = h162.make_signals(p, params)
    z = h162.dispersion_z(p, params["z_window"])
    early = sig.loc[z.index[: n // 2 - 40], "SPY"].dropna()
    late = sig.loc[z.index[n // 2 + 60 :], "SPY"].dropna()
    assert not early.empty and not late.empty
    assert late.mean() <= early.mean() + 1e-9
