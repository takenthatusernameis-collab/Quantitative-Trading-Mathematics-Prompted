from __future__ import annotations

import numpy as np
import pandas as pd

import run_nf_20261109_11_spy_index_rebalance as h168


def _prices(n: int = 1000) -> pd.DataFrame:
    idx = pd.bdate_range("2010-01-04", periods=n)
    rng = np.random.default_rng(168)
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
    return pd.DataFrame({"SPY": spy}, index=idx)


def test_make_signals_columns_and_bounds() -> None:
    p = _prices()
    sig = h168.make_signals(p, {"end_days": 3, "start_days": 3, "vol_target": 0.1})
    assert list(sig.columns) == ["SPY"]
    assert sig["SPY"].between(0.0, h168.MAX_POS + 1e-12).all()


def test_in_window_reduces_exposure() -> None:
    p = _prices(2000)
    params = {"end_days": 3, "start_days": 3, "vol_target": 0.1}
    sig = h168.make_signals(p, params)
    in_window = h168._is_in_rebalance_window(p.index, params["end_days"], params["start_days"])
    vscale = h168._vol_scale(p, params["vol_target"])
    expected = ((~in_window).astype(float) * params["vol_target"] * vscale).clip(0.0, h168.MAX_POS)
    mask = in_window.notna() & sig["SPY"].notna()
    np.testing.assert_allclose(
        sig.loc[mask, "SPY"].values, expected.loc[mask].fillna(0).values, atol=1e-12
    )


def test_inverse_falsifier_mapping() -> None:
    p = _prices(2000)
    params = {"end_days": 3, "start_days": 3, "vol_target": 0.1}
    in_window = h168._is_in_rebalance_window(p.index, params["end_days"], params["start_days"])
    vscale = h168._vol_scale(p, params["vol_target"])
    w_base = ((~in_window).astype(float) * params["vol_target"] * vscale).clip(0.0, h168.MAX_POS)
    w_inv = (in_window.astype(float) * params["vol_target"] * vscale).clip(0.0, h168.MAX_POS)
    assert not np.allclose(w_base.fillna(0).values, w_inv.fillna(0).values)
    inv = h168.make_inverse_signals(p, params)
    assert isinstance(inv, pd.DataFrame) and "SPY" in inv.columns


def test_rebalance_window_shape() -> None:
    p = _prices(2000)
    in_window = h168._is_in_rebalance_window(p.index, 3, 3)
    assert len(in_window) == len(p)
    assert isinstance(in_window, pd.Series)
    # Should have some True values (quarterly rebalance windows)
    assert in_window.sum() > 0


def test_splits_cover_index() -> None:
    p = _prices(3000)
    train, val, test = h168._splits(p.index)
    assert (train | val | test).all()
    assert not (train & test).any()


def test_benchmark_buy_hold() -> None:
    p = _prices(500)
    mask = pd.Series(True, index=p.index)
    m = h168.benchmark_buy_hold(p, mask)
    assert set(m.keys()) >= {"sharpe", "profit_factor", "max_drawdown", "trades"}
    assert m["trades"] == 1


def test_always_flat_falsifier() -> None:
    p = _prices(500)
    flat = h168.make_always_flat(p)
    assert (flat["SPY"] == 0).all()


def test_out_of_window_higher_exposure_than_in_window() -> None:
    p = _prices(2000)
    params = {"end_days": 3, "start_days": 3, "vol_target": 0.1}
    sig = h168.make_signals(p, params)
    in_window = h168._is_in_rebalance_window(p.index, params["end_days"], params["start_days"])
    mask = in_window.notna() & sig["SPY"].notna()
    out = sig.loc[mask & (~in_window), "SPY"]
    inn = sig.loc[mask & in_window, "SPY"]
    assert len(out) > 0 and len(inn) > 0
    assert out.mean() > inn.mean()


def test_vol_scale_bounds() -> None:
    p = _prices(500)
    vs = h168._vol_scale(p, 0.15)
    assert (vs.fillna(0) >= 0).all()
    assert (vs.fillna(0) <= 1).all()
