from __future__ import annotations

import numpy as np
import pandas as pd

import run_nf_20261109_05_ig_credit_spread as h163


def _prices(n: int = 600) -> pd.DataFrame:
    idx = pd.bdate_range("2016-01-04", periods=n)
    rng = np.random.default_rng(163)
    cols = {
        h163.SPY: 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n))),
        h163.LQD: 100 * np.exp(np.cumsum(rng.normal(0.0001, 0.003, n))),
        h163.IEF: 100 * np.exp(np.cumsum(rng.normal(0.00005, 0.002, n))),
    }
    return pd.DataFrame(cols, index=idx)


def test_make_signals_columns_and_bounds() -> None:
    p = _prices()
    sig = h163.make_signals(
        p,
        {
            "lookback": 63,
            "z_window": 126,
            "entry_scale": 1.0,
            "exit_scale": 0.0,
            "vol_target": 0.1,
        },
    )
    assert list(sig.columns) == h163.UNIVERSE
    assert (sig[[h163.LQD, h163.IEF]] == 0).all().all()
    assert sig[h163.SPY].between(0.0, h163.MAX_POS + 1e-12).all()


def test_ig_spread_uses_lqd_ief() -> None:
    p = _prices()
    spread = np.log(p[h163.LQD]) - np.log(p[h163.IEF])
    mp = max(30, 126 // 2)
    mu = spread.rolling(126, min_periods=mp).mean()
    sd = spread.rolling(126, min_periods=mp).std()
    expected = (spread - mu) / sd.replace(0.0, np.nan)
    z = h163.ig_spread_z(p, 126)
    pd.testing.assert_series_equal(z, expected, check_names=False)


def test_hysteresis_state_initial_long_and_transitions() -> None:
    idx = pd.bdate_range("2020-01-01", periods=6)
    z = pd.Series([np.nan, 0.5, 2.0, 0.2, -0.5, -1.0], index=idx)
    state = h163.hysteresis_state(z, entry_scale=1.0, exit_scale=0.0)
    # nan->1, 0.5<1 hold 1, 2.0>=1->0, 0.2 hold 0, -0.5<=0->1, -1.0<=0->1
    np.testing.assert_allclose(state.values, [1.0, 1.0, 0.0, 0.0, 1.0, 1.0])


def test_ig_spread_z_shape_and_finite() -> None:
    p = _prices()
    z = h163.ig_spread_z(p, 126)
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
    base = h163.run_one(p, params)["signals"].attrs["state"]
    inv = h163.inverse_regime(p, params)
    assert isinstance(inv, dict) and "sharpe" in inv
    # base and inverse should produce different state sequences (not all same)
    z = h163.ig_spread_z(p, params["z_window"])
    inv_state = np.empty(len(z), dtype=float)
    s = 1.0
    for i, v in enumerate(z.to_numpy(dtype=float)):
        if np.isfinite(v):
            if v <= -params["entry_scale"]:
                s = 0.0
            elif v >= -params["exit_scale"]:
                s = 1.0
        inv_state[i] = s
    assert not np.allclose(base.fillna(1).values, inv_state)


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
    # 3 lookbacks * 2 z_windows * 3 entry_scales * 2 exit_scales (0, 0.5 <= 1.0) * 2 vol_targets = 72
    # but exit_scale 0.5 > entry_scale 1.0? No, 0.5 <= 1.0. For entry_scale 1.0: exits 0.0, 0.5 (2)
    # For entry_scale 1.5: exits 0.0, 0.5 (2). For entry_scale 2.0: exits 0.0, 0.5 (2).
    # Total = 3 * 2 * (2+2+2) * 2 = 3 * 2 * 6 * 2 = 72
    assert combos == 3 * 2 * 6 * 2


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
