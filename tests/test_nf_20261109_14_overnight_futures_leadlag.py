from __future__ import annotations

import numpy as np
import pandas as pd

import run_nf_20261109_14_overnight_futures_leadlag as h169


def _prices(n: int = 2000) -> pd.DataFrame:
    idx = pd.bdate_range("2010-01-04", periods=n)
    rng = np.random.default_rng(169)
    # Futures and cash prices with some correlation
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
    es = spy * (1 + rng.normal(0.0, 0.001, n))  # futures slightly different
    qqq = 200 * np.exp(np.cumsum(rng.normal(0.0002, 0.012, n)))
    nq = qqq * (1 + rng.normal(0.0, 0.001, n))
    return pd.DataFrame(
        {
            "open_ES=F": es * (1 + rng.normal(0.0, 0.0005, n)),
            "close_ES=F": es,
            "open_SPY": spy * (1 + rng.normal(0.0, 0.0005, n)),
            "close_SPY": spy,
            "open_NQ=F": nq * (1 + rng.normal(0.0, 0.0005, n)),
            "close_NQ=F": nq,
            "open_QQQ": qqq * (1 + rng.normal(0.0, 0.0005, n)),
            "close_QQQ": qqq,
        },
        index=idx,
    )


def test_overnight_futures_return_computation() -> None:
    p = _prices(500)
    overnight = h169._overnight_futures_return(p, "ES=F")
    assert len(overnight) == len(p)
    assert isinstance(overnight, pd.Series)
    # First value should be NaN (no prior close)
    assert pd.isna(overnight.iloc[0])
    # Should have some non-NaN values
    assert overnight.notna().any()


def test_cash_daytime_return_computation() -> None:
    p = _prices(500)
    daytime = h169._cash_daytime_return(p, "SPY")
    assert len(daytime) == len(p)
    assert isinstance(daytime, pd.Series)
    assert daytime.notna().all()


def test_zscore_behavior() -> None:
    p = _prices(500)
    overnight = h169._overnight_futures_return(p, "ES=F")
    z = h169._zscore(overnight, 21)
    assert len(z) == len(p)
    # First 21 values should be NaN (min_periods=lookback)
    assert z.iloc[:21].isna().all()
    # After lookback, should have values
    assert z.iloc[21:].notna().any()


def test_vol_scale_bounds() -> None:
    p = _prices(500)
    intraday = h169._cash_daytime_return(p, "SPY")
    vs = h169._vol_scale(intraday, 0.15)
    assert (vs.fillna(0) >= 0).all()
    assert (vs.fillna(0) <= 1).all()


def test_build_strategy_returns_structure() -> None:
    p = _prices(2000)
    params = {"pair": "ES_SPY", "lookback": 21, "z_entry": 0.5, "vol_target": 0.1}
    strat_ret, pos = h169._build_strategy_returns(p, params)
    assert len(strat_ret) == len(p)
    assert len(pos) == len(p)
    assert isinstance(strat_ret, pd.Series)
    assert isinstance(pos, pd.Series)


def test_make_synthetic_price() -> None:
    rets = pd.Series(np.random.default_rng(169).normal(0.0003, 0.01, 500))
    p_strat = h169._make_synthetic_price(rets)
    assert isinstance(p_strat, pd.DataFrame)
    assert "STRAT" in p_strat.columns
    assert len(p_strat) == len(rets)
    # Price should be cumulative product
    expected = (1.0 + rets).cumprod()
    expected.iloc[0] = 1.0
    np.testing.assert_allclose(p_strat["STRAT"].values, expected.values, rtol=1e-10)


def test_splits_cover_index() -> None:
    p = _prices(3000)
    train, val, test = h169._splits(p.index)
    assert (train | val | test).all()
    assert not (train & test).any()
    assert not (train & val).any()
    assert not (val & test).any()


def test_select_params_returns_best() -> None:
    p = _prices(3000)
    train, _, _ = h169._splits(p.index)
    cfg = h169._cfg()
    best, rows = h169.select_params(p, train, cfg)
    assert set(best.keys()) == {"pair", "lookback", "z_entry", "vol_target"}
    assert best["pair"] in h169.PAIRS
    assert best["lookback"] in h169.LOOKBACKS
    assert best["z_entry"] in h169.Z_ENTRIES
    assert best["vol_target"] in h169.VOL_TARGETS
    assert len(rows) == len(h169.PAIRS) * len(h169.LOOKBACKS) * len(h169.Z_ENTRIES) * len(
        h169.VOL_TARGETS
    )
    # Best should be first in sorted rows
    assert rows[0]["wf_train_mean_sharpe"] == max(r["wf_train_mean_sharpe"] for r in rows)


def test_perturbation_ratio() -> None:
    p = _prices(3000)
    train, val, test = h169._splits(p.index)
    oos = val | test
    cfg = h169._cfg()
    best, _ = h169.select_params(p, train, cfg)
    pert = h169.perturbation_ratio(p, oos, best, cfg)
    assert isinstance(pert, float)
    # Ratio can be negative if perturbed Sharpe has opposite sign


def test_pair_independence_nq_qqq() -> None:
    """NQ/QQQ pair should produce independent signals from ES/SPY."""
    p = _prices(2000)
    params_es = {"pair": "ES_SPY", "lookback": 21, "z_entry": 0.5, "vol_target": 0.1}
    params_nq = {"pair": "NQ_QQQ", "lookback": 21, "z_entry": 0.5, "vol_target": 0.1}
    ret_es, _ = h169._build_strategy_returns(p, params_es)
    ret_nq, _ = h169._build_strategy_returns(p, params_nq)
    # Returns should be different (different underlying data)
    assert not ret_es.equals(ret_nq)


def test_worst_regime_sharpe() -> None:
    rets = pd.Series(np.random.default_rng(169).normal(0.0003, 0.01, 500))
    wrs = h169.worst_regime_sharpe(rets)
    assert isinstance(wrs, float)


def test_period_metrics() -> None:
    rets = pd.Series(np.random.default_rng(169).normal(0.0003, 0.01, 500))
    m = h169._period_metrics(rets, 10)
    assert set(m.keys()) == {"sharpe", "max_drawdown", "profit_factor", "trades"}
    assert isinstance(m["sharpe"], float)
    assert isinstance(m["max_drawdown"], float)
    assert isinstance(m["profit_factor"], float)
    assert isinstance(m["trades"], int)


def test_make_inverse_returns() -> None:
    p = _prices(2000)
    params = {"pair": "ES_SPY", "lookback": 21, "z_entry": 0.5, "vol_target": 0.1}
    base_ret, _ = h169._build_strategy_returns(p, params)
    inv_ret = h169._make_inverse_returns(p, params)
    assert len(base_ret) == len(inv_ret)
    # Should have some opposite signs where both non-zero
    mask = (base_ret != 0) & (inv_ret != 0)
    if mask.any():
        assert (base_ret[mask] * inv_ret[mask] < 0).any()


def test_make_flat_returns() -> None:
    p = _prices(500)
    flat_ret = h169._make_flat_returns(p, "SPY")
    assert (flat_ret == 0).all()


def test_make_random_futures_returns() -> None:
    p = _prices(2000)
    params = {"pair": "ES_SPY", "lookback": 21, "z_entry": 0.5, "vol_target": 0.1}
    base_ret, _ = h169._build_strategy_returns(p, params)
    rand_ret = h169._make_random_futures_returns(p, params)
    assert len(base_ret) == len(rand_ret)
    # Both should have some non-zero values
    assert (base_ret != 0).any()
    assert (rand_ret != 0).any()
