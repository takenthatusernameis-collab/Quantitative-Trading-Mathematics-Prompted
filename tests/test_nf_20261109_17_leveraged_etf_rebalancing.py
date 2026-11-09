from __future__ import annotations

import numpy as np
import pandas as pd

import run_nf_20261109_17_leveraged_etf_rebalancing as h170


def _prices(n: int = 2000) -> pd.DataFrame:
    idx = pd.bdate_range("2010-01-04", periods=n)
    rng = np.random.default_rng(170)
    # SPY and leveraged ETFs with correlated returns
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
    # Leveraged ETFs track SPY with leverage factor + noise
    sso = 50 * np.exp(np.cumsum(rng.normal(0.0006, 0.02, n)))  # 2x
    upro = 40 * np.exp(np.cumsum(rng.normal(0.0009, 0.03, n)))  # 3x
    sds = 80 * np.exp(np.cumsum(rng.normal(-0.0006, 0.02, n)))  # -2x
    spxl = 60 * np.exp(np.cumsum(rng.normal(0.0009, 0.03, n)))  # 3x
    spxs = 70 * np.exp(np.cumsum(rng.normal(-0.0009, 0.03, n)))  # -3x
    return pd.DataFrame(
        {
            "close_SPY": spy,
            "close_SSO": sso,
            "close_UPRO": upro,
            "close_SDS": sds,
            "close_SPXL": spxl,
            "close_SPXS": spxs,
        },
        index=idx,
    )


def test_compute_returns() -> None:
    p = _prices(500)
    ret = h170._compute_returns(p, "SPY")
    assert len(ret) == len(p)
    assert isinstance(ret, pd.Series)
    assert ret.notna().any()


def test_net_leveraged_etf_flow_computation() -> None:
    p = _prices(500)
    flow = h170._net_leveraged_etf_flow(p, ["SSO", "UPRO", "SDS"])
    assert len(flow) == len(p)
    assert isinstance(flow, pd.Series)
    assert flow.notna().any()


def test_net_leveraged_etf_flow_full_set() -> None:
    p = _prices(500)
    flow = h170._net_leveraged_etf_flow(p, ["SSO", "UPRO", "SDS", "SPXL", "SPXS"])
    assert len(flow) == len(p)
    assert isinstance(flow, pd.Series)
    assert flow.notna().any()


def test_zscore_behavior() -> None:
    p = _prices(500)
    flow = h170._net_leveraged_etf_flow(p, ["SSO", "UPRO", "SDS"])
    z = h170._zscore(flow, 21)
    assert len(z) == len(p)
    # First lookback-1 values should be NaN (min_periods=lookback on series with 1 leading NaN from pct_change)
    assert z.iloc[:20].isna().all()
    # After lookback, should have values
    assert z.iloc[20:].notna().any()


def test_vol_scale_bounds() -> None:
    p = _prices(500)
    spy_ret = h170._compute_returns(p, "SPY")
    vs = h170._vol_scale(spy_ret, 0.15)
    assert (vs.fillna(0) >= 0).all()
    assert (vs.fillna(0) <= 1).all()


def test_build_strategy_returns_structure() -> None:
    p = _prices(2000)
    params = {"leverage_set": "core_3", "lookback": 21, "vol_target": 0.1}
    strat_ret, pos = h170._build_strategy_returns(p, params)
    assert len(strat_ret) == len(p)
    assert len(pos) == len(p)
    assert isinstance(strat_ret, pd.Series)
    assert isinstance(pos, pd.Series)


def test_make_synthetic_price() -> None:
    rets = pd.Series(np.random.default_rng(170).normal(0.0003, 0.01, 500))
    p_strat = h170._make_synthetic_price(rets)
    assert isinstance(p_strat, pd.DataFrame)
    assert "STRAT" in p_strat.columns
    assert len(p_strat) == len(rets)
    # Price should be cumulative product
    expected = (1.0 + rets).cumprod()
    expected.iloc[0] = 1.0
    np.testing.assert_allclose(p_strat["STRAT"].values, expected.values, rtol=1e-10)


def test_splits_cover_index() -> None:
    p = _prices(3000)
    train, val, test = h170._splits(p.index)
    assert (train | val | test).all()
    assert not (train & test).any()
    assert not (train & val).any()
    assert not (val & test).any()


def test_select_params_returns_best() -> None:
    p = _prices(3000)
    train, _, _ = h170._splits(p.index)
    cfg = h170._cfg()
    best, rows = h170.select_params(p, train, cfg)
    assert set(best.keys()) == {"leverage_set", "lookback", "vol_target"}
    assert best["leverage_set"] in h170.LEVERAGE_SETS
    assert best["lookback"] in h170.LOOKBACKS
    assert best["vol_target"] in h170.VOL_TARGETS
    assert len(rows) == len(h170.LEVERAGE_SETS) * len(h170.LOOKBACKS) * len(h170.VOL_TARGETS)
    # Best should be first in sorted rows
    assert rows[0]["wf_train_mean_sharpe"] == max(r["wf_train_mean_sharpe"] for r in rows)


def test_perturbation_ratio() -> None:
    p = _prices(3000)
    train, val, test = h170._splits(p.index)
    oos = val | test
    cfg = h170._cfg()
    best, _ = h170.select_params(p, train, cfg)
    pert = h170.perturbation_ratio(p, oos, best, cfg)
    assert isinstance(pert, float)


def test_leverage_set_independence() -> None:
    """core_3 and full_5 leverage sets should produce different signals."""
    p = _prices(2000)
    params_core = {"leverage_set": "core_3", "lookback": 21, "vol_target": 0.1}
    params_full = {"leverage_set": "full_5", "lookback": 21, "vol_target": 0.1}
    ret_core, _ = h170._build_strategy_returns(p, params_core)
    ret_full, _ = h170._build_strategy_returns(p, params_full)
    # Returns should be different (different leveraged ETF baskets)
    assert not ret_core.equals(ret_full)


def test_worst_regime_sharpe() -> None:
    rets = pd.Series(np.random.default_rng(170).normal(0.0003, 0.01, 500))
    wrs = h170.worst_regime_sharpe(rets)
    assert isinstance(wrs, float)


def test_period_metrics() -> None:
    rets = pd.Series(np.random.default_rng(170).normal(0.0003, 0.01, 500))
    m = h170._period_metrics(rets, 10)
    assert set(m.keys()) == {"sharpe", "max_drawdown", "profit_factor", "trades"}
    assert isinstance(m["sharpe"], float)
    assert isinstance(m["max_drawdown"], float)
    assert isinstance(m["profit_factor"], float)
    assert isinstance(m["trades"], int)


def test_make_inverse_returns() -> None:
    p = _prices(2000)
    params = {"leverage_set": "core_3", "lookback": 21, "vol_target": 0.1}
    base_ret, _ = h170._build_strategy_returns(p, params)
    inv_ret = h170._make_inverse_returns(p, params)
    assert len(base_ret) == len(inv_ret)
    # Should have some opposite signs where both non-zero
    mask = (base_ret != 0) & (inv_ret != 0)
    if mask.any():
        assert (base_ret[mask] * inv_ret[mask] < 0).any()


def test_make_flat_returns() -> None:
    p = _prices(500)
    flat_ret = h170._make_flat_returns(p)
    assert (flat_ret == 0).all()


def test_make_random_flow_returns() -> None:
    p = _prices(2000)
    params = {"leverage_set": "core_3", "lookback": 21, "vol_target": 0.1}
    base_ret, _ = h170._build_strategy_returns(p, params)
    rand_ret = h170._make_random_flow_returns(p, params)
    assert len(base_ret) == len(rand_ret)
    # Both should have some non-zero values
    assert (base_ret != 0).any()
    assert (rand_ret != 0).any()


def test_make_equal_weight_returns() -> None:
    p = _prices(2000)
    params = {"leverage_set": "core_3", "lookback": 21, "vol_target": 0.1}
    base_ret, _ = h170._build_strategy_returns(p, params)
    eqw_ret = h170._make_equal_weight_returns(p, params)
    assert len(base_ret) == len(eqw_ret)
    assert (base_ret != 0).any()
    assert (eqw_ret != 0).any()
    # Should be different from AUM-weighted
    assert not base_ret.equals(eqw_ret)


def test_aum_estimates_present() -> None:
    """Verify all leveraged ETFs have AUM estimates."""
    for etf in h170.LEVERAGED_ETFS:
        assert etf in h170.AUM_ESTIMATES
        assert h170.AUM_ESTIMATES[etf] > 0


def test_leverage_factors_correct() -> None:
    """Verify leverage factors match fund specifications."""
    assert h170.LEVERAGED_ETFS["SSO"] == 2.0
    assert h170.LEVERAGED_ETFS["UPRO"] == 3.0
    assert h170.LEVERAGED_ETFS["SDS"] == -2.0
    assert h170.LEVERAGED_ETFS["SPXL"] == 3.0
    assert h170.LEVERAGED_ETFS["SPXS"] == -3.0
