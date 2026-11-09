from __future__ import annotations

import numpy as np
import pandas as pd

import run_nf_20261109_06_idio_skew_regime as h164


def _prices(n: int = 600) -> pd.DataFrame:
    idx = pd.bdate_range("2016-01-04", periods=n)
    rng = np.random.default_rng(164)
    cols = {h164.SPY: 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))}
    for a in h164.SKEW_ASSETS:
        cols[a] = 100 * np.exp(np.cumsum(rng.normal(0.0, 0.004, n)))
    return pd.DataFrame(cols, index=idx)


def test_make_signals_columns_and_bounds() -> None:
    p = _prices()
    sig = h164.make_signals(
        p,
        {
            "lookback": 63,
            "z_window": 126,
            "entry_z": 1.0,
            "exit_z": 0.0,
            "vol_target": 0.1,
        },
    )
    assert list(sig.columns) == h164.UNIVERSE
    assert (sig[h164.SKEW_ASSETS] == 0).all().all()
    assert sig["SPY"].between(0.0, h164.MAX_POS + 1e-12).all()


def test_idiosyncratic_skew_shape_and_past_only() -> None:
    p = _prices(900)
    skew = h164.idiosyncratic_skew_cross_section_mean(p, 126)
    assert len(skew) == len(p)
    assert isinstance(skew, pd.Series)
    assert skew.dropna().shape[0] > 200
    # Past-only: skewness at bar t must equal a manual recomputation using only
    # data through bar t (rolling windows are trailing, not centered).
    t = 500
    rets = p.pct_change()
    spy_ret = rets[h164.SPY]
    mp = max(10, 126 // 2)
    spy_var = spy_ret.iloc[: t + 1].rolling(126, min_periods=mp).var().iloc[-1]
    manual = []
    for a in h164.SKEW_ASSETS:
        cov = rets[a].iloc[: t + 1].rolling(126, min_periods=mp).cov(spy_ret.iloc[: t + 1]).iloc[-1]
        beta = cov / spy_var if spy_var and spy_var > 0 else 0.0
        res = rets[a].iloc[: t + 1] - beta * spy_ret.iloc[: t + 1]
        manual.append(res.skew())
    expected = float(np.mean(manual))
    got = float(skew.iloc[t])
    assert np.isfinite(got)
    assert abs(got - expected) < 1e-9


def test_skew_z_score_shape() -> None:
    p = _prices(900)
    skew = h164.idiosyncratic_skew_cross_section_mean(p, 126)
    z = h164.skew_z_score(skew, 252)
    assert len(z) == len(p)
    assert isinstance(z, pd.Series)
    assert z.dropna().shape[0] > 100


def test_hysteresis_state_initial_long_and_transitions() -> None:
    idx = pd.bdate_range("2020-01-01", periods=8)
    z = pd.Series([np.nan, 0.5, 2.5, 1.5, -0.5, -2.5, -1.0, 0.2], index=idx)
    state = h164.hysteresis_state(z, entry_z=1.0, exit_z=0.0)
    # nan->1 hold, 0.5 hold 1, 2.5>=1->0, 1.5>=0 hold 0, -0.5 hold 0,
    # -2.5<=0->1, -1.0 hold 1, 0.2 hold 1
    np.testing.assert_allclose(state.values, [1.0, 1.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0])


def test_high_cross_sectional_skew_reduces_exposure() -> None:
    # inject lottery-type positive-skew residuals into signal assets late in sample
    idx = pd.bdate_range("2016-01-04", periods=700)
    rng = np.random.default_rng(11)
    n = len(idx)
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.008, n)))
    cols = {h164.SPY: spy}
    for a in h164.SKEW_ASSETS:
        cols[a] = 100 * np.exp(np.cumsum(rng.normal(0.0, 0.003, n)))
    # rare large positive jumps in signal assets after midpoint -> positive skew
    for a in h164.SKEW_ASSETS:
        path = cols[a].copy()
        jump_idx = n // 2 + 50
        path[jump_idx:] = path[jump_idx - 1] * np.exp(
            np.cumsum(np.concatenate([[0.0], rng.normal(0.002, 0.06, n - jump_idx)]))
        )
        cols[a] = path
    p = pd.DataFrame(cols, index=idx)
    params = {
        "lookback": 63,
        "z_window": 126,
        "entry_z": 1.0,
        "exit_z": 0.0,
        "vol_target": 0.1,
    }
    sig = h164.make_signals(p, params)
    z = h164.skew_z_score(
        h164.idiosyncratic_skew_cross_section_mean(p, params["lookback"]),
        params["z_window"],
    )
    early = sig.loc[z.index[: n // 2 - 80], "SPY"].dropna()
    late = sig.loc[z.index[n // 2 + 120 :], "SPY"].dropna()
    assert not early.empty and not late.empty
    assert late.mean() <= early.mean() + 1e-9


def test_splits_cover_index() -> None:
    p = _prices(900)
    train, val, test = h164._splits(p.index)
    assert (train | val | test).all()
    assert not (train & test).any()
    assert not (train & val).any()


def test_benchmark_buy_hold() -> None:
    p = _prices(300)
    mask = pd.Series(True, index=p.index)
    m = h164.benchmark_buy_hold(p, mask)
    assert set(m.keys()) >= {"sharpe", "profit_factor", "max_drawdown", "trades"}
    assert m["trades"] == 1


def test_random_exposure_matched_returns_dict() -> None:
    p = _prices(400)
    mask = pd.Series(True, index=p.index)
    m = h164.random_exposure_matched(p, mask, 0.25, 164)
    assert set(m.keys()) >= {"sharpe", "profit_factor", "max_drawdown", "trades"}


def test_grid_exit_z_below_entry_z() -> None:
    combos = 0
    for lb in h164.LOOKBACKS:
        for zw in h164.Z_WINDOWS:
            for ez in h164.ENTRY_ZS:
                for xz in h164.EXIT_ZS:
                    if xz >= ez:
                        continue
                    for vt in h164.VOL_TARGETS:
                        combos += 1
                        assert xz < ez
    assert combos == 3 * 2 * 3 * 2 * 2  # all exit<entry pairs here


def test_run_one_returns_sharpe_dict() -> None:
    p = _prices(700)
    params = {
        "lookback": 126,
        "z_window": 252,
        "entry_z": 1.5,
        "exit_z": 0.5,
        "vol_target": 0.15,
    }
    out = h164.run_one(p, params)
    assert set(out.keys()) >= {"result", "signals", "z"}
    m = h164._metrics_from_result(out["result"], pd.Series(True, index=p.index))
    assert set(m.keys()) >= {"sharpe", "profit_factor", "max_drawdown", "trades"}
    assert np.isfinite(m["sharpe"])
