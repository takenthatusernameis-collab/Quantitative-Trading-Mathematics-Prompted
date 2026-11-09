from __future__ import annotations

import numpy as np
import pandas as pd

import run_nf_20261109_06_gld_rv_stress_spy as h164


def _prices(n: int = 650) -> pd.DataFrame:
    idx = pd.bdate_range("2015-01-05", periods=n)
    rng = np.random.default_rng(164)
    cols = {
        h164.SPY: 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n))),
        h164.GLD: 120 * np.exp(np.cumsum(rng.normal(0.0001, 0.012, n))),
    }
    return pd.DataFrame(cols, index=idx)


def test_make_signals_columns_and_bounds() -> None:
    p = _prices()
    sig = h164.make_signals(
        p,
        {
            "rv_window": 21,
            "z_window": 126,
            "entry_scale": 1.0,
            "exit_scale": 0.0,
            "vol_target": 0.1,
        },
    )
    assert list(sig.columns) == h164.UNIVERSE
    assert (sig[h164.GLD] == 0).all()
    assert sig[h164.SPY].between(0.0, h164.MAX_POS + 1e-12).all()


def test_realized_vol_past_only() -> None:
    p = _prices()
    rv = h164.realized_vol(p[h164.GLD], 21)
    assert rv.iloc[:21].isna().all()
    assert rv.dropna().shape[0] > 100


def test_rv_state_hysteresis() -> None:
    idx = pd.bdate_range("2020-01-01", periods=7)
    z = pd.Series([np.nan, 0.5, 1.2, 0.2, -0.1, 1.5, -2.0], index=idx)
    state = h164.rv_state(z, entry_scale=1.0, exit_scale=0.0)
    np.testing.assert_allclose(state.values, [1.0, 1.0, 0.0, 0.0, 1.0, 0.0, 1.0])


def test_inverse_rv_state_flips() -> None:
    idx = pd.bdate_range("2020-01-01", periods=7)
    z = pd.Series([np.nan, 0.5, -1.2, -0.2, 0.1, -1.5, 2.0], index=idx)
    state = h164.inverse_rv_state(z, entry_scale=1.0, exit_scale=0.0)
    np.testing.assert_allclose(state.values, [1.0, 1.0, 0.0, 0.0, 1.0, 0.0, 1.0])


def test_param_grid_bounded_and_valid() -> None:
    g = h164.param_grid()
    assert 1 <= len(g) <= 100
    assert len(g) == 48
    for p in g:
        assert p["exit_scale"] <= p["entry_scale"]
        assert p["vol_target"] in (0.1, 0.15)


def test_zscore_past_only_min_periods() -> None:
    s = pd.Series(np.linspace(100, 120, 300))
    z = h164.zscore(s, 126)
    mp = max(30, 126 // 2)
    assert z.iloc[: mp - 1].isna().all()
    assert np.isfinite(z.iloc[mp + 5])
