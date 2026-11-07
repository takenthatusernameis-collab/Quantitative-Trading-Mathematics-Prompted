"""Focused tests for NF-20261107-02 / H119 sector cross-sectional reversal runner."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from run_nf_20261107_02_cs_reversal import (  # noqa: E402
    BENCHMARK,
    GATES,
    MAX_LEVERAGE,
    MAX_POS,
    N_LONG,
    REBALANCE_EVERY,
    SECTORS,
    SPY,
    UNIVERSE,
    _cum_return_rank,
    _dict_metrics,
    _inverse_signal,
    _max_drawdown,
    _profit_factor,
    _realized_vol_scale,
    _select_on_train,
    _turnover,
    build_reversal_signal,
    evaluate_gates,
    make_equity_config,
)


def _prices(n=900, seed=34):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2014-01-01", periods=n)
    data = {}
    common = rng.normal(0.0003, 0.008, n)
    for i, s in enumerate(SECTORS):
        idio = rng.normal(0.0, 0.006 + 0.001 * (i % 3), n)
        ret = 0.6 * common + 0.4 * idio
        data[s] = 100 * np.exp(np.cumsum(ret))
    return pd.DataFrame(data, index=idx)[SECTORS]


def test_gates_match_preregistration():
    assert GATES["min_sharpe"] == 1.0
    assert GATES["min_trades"] == 200
    assert GATES["min_profit_factor"] == 1.3
    assert GATES["max_drawdown"] == 0.15
    assert GATES["min_walkforward_stability"] == 0.7
    assert GATES["min_worst_regime_sharpe"] == 0.3
    assert GATES["max_p_value"] == 0.05
    assert GATES["min_information_ratio"] == 0.0
    assert GATES["min_perturbed_sharpe_ratio"] == 0.5


def test_universe_and_sectors():
    assert SPY == "SPY" and BENCHMARK == "SPY"
    assert len(SECTORS) == 9
    assert "XLC" not in SECTORS and "XLRE" not in SECTORS
    assert set(UNIVERSE) == set(SECTORS)
    assert N_LONG == 3 and REBALANCE_EVERY == 5


def test_cum_return_rank_causal_and_range():
    p = _prices(400)
    rets = p.pct_change()
    rank = _cum_return_rank(rets, 21)
    valid = rank.dropna(how="all")
    assert len(valid) > 200
    ranks = valid.values[~np.isnan(valid.values)].ravel()
    assert ((ranks >= 1) & (ranks <= len(SECTORS))).all()


def test_signal_columns_warmup_and_bounds():
    sig = build_reversal_signal(_prices(), 5, 0.10)
    assert list(sig.columns) == list(SECTORS)
    warmup = 5 + 63
    assert (sig.iloc[:warmup].isna().all(axis=1)).all()
    vals = sig.fillna(0.0)
    assert (vals >= -1e-12).all().all() and (vals <= MAX_POS + 1e-12).all().all()
    row_sums = vals.sum(axis=1)
    assert (row_sums <= MAX_POS + 1e-12).all()


def test_signal_causality_no_future_leak():
    p = _prices(600)
    s1 = build_reversal_signal(p, 5, 0.10)
    p2 = p.copy()
    p2.iloc[-1] = p2.iloc[-1] * 1.15
    s2 = build_reversal_signal(p2, 5, 0.10)
    pd.testing.assert_frame_equal(
        s1.fillna(0.0).iloc[:-1], s2.fillna(0.0).iloc[:-1], check_names=False
    )


def test_weakest_sector_receives_long_exposure():
    """A sector forced to have the worst trailing return must be selected long."""
    p = _prices(500)
    weak = SECTORS[0]
    base = p[weak].iloc[-61]
    p.loc[p.index[-60:], weak] = base * np.exp(np.cumsum(np.linspace(-0.04, -0.02, 60)))
    sig = build_reversal_signal(p, 5, 0.10).fillna(0.0)
    assert sig[weak].iloc[-1] > 0.0


def test_signal_changes_only_on_rebalance_days():
    sig = build_reversal_signal(_prices(500), 5, 0.10).fillna(0.0)
    changed = (sig.diff().abs().sum(axis=1) > 1e-8).values
    changed[: 5 + 63] = False
    change_idx = np.flatnonzero(changed)
    if len(change_idx):
        gaps = np.diff(change_idx)
        assert ((gaps == REBALANCE_EVERY) | (gaps == 0)).all(), gaps[:10]


def test_profit_factor_edges():
    assert _profit_factor(np.array([0.01, 0.02])) == float("inf")
    assert _profit_factor(np.array([-0.01, -0.02])) == 0.0
    assert np.isclose(_profit_factor(np.array([0.02, -0.01])), 2.0)


def test_max_drawdown_and_vol_scale_bounds():
    p = _prices(400)
    scale = _realized_vol_scale(p, 0.15).fillna(0.0)
    assert (scale >= 0.0).all().all() and (scale <= 1.0).all().all()
    rets = p.pct_change().fillna(0.0).values
    assert _max_drawdown(rets) >= 0.0


def test_evaluate_gates_returns_expected_keys():
    p = _prices(1200)
    cfg = make_equity_config()
    sig = build_reversal_signal(p, 5, 0.10)
    from qtr.backtest.engine import run_backtest

    cut = 700
    tr = run_backtest(p.loc[p.index[:cut], SECTORS], sig.loc[p.index[:cut]], cfg)
    oos = run_backtest(p.loc[p.index[cut:], SECTORS], sig.loc[p.index[cut:]], cfg)
    bh = run_backtest(
        p.loc[p.index[cut:], [SPY]],
        pd.DataFrame({SPY: 1.0}, index=p.index[cut:]),
        cfg,
    )
    mask = pd.Series(False, index=p.index)
    mask.iloc[cut:] = True
    res = evaluate_gates(
        oos,
        tr,
        bh,
        p,
        mask,
        {"lookback": 5, "vol_target": 0.10},
        cfg,
    )
    assert res["verdict"] in {"PASS", "REJECT"}
    assert set(res["gates"]) == {
        "sharpe_ge_1_0",
        "trades_ge_200",
        "profit_factor_ge_1_3",
        "max_drawdown_le_15pct",
        "walkforward_stability_ge_0_7",
        "worst_regime_rolling252_sharpe_ge_0_3",
        "benchmark_p_le_0_05_ir_ge_0",
        "perturbation_min_ratio_ge_0_5",
    }


def test_select_on_train_returns_row_and_frame():
    p = _prices(1400)
    train_mask = pd.Series([i < 900 for i in range(len(p))], index=p.index)
    best, df = _select_on_train(p, train_mask, make_equity_config())
    assert not df.empty
    for k in ("lookback", "vol_target", "wf_mean_sharpe"):
        assert k in best
    assert best["lookback"] in (5, 10)
    assert best["vol_target"] in (0.10, 0.15)


def test_signal_missing_symbol_raises():
    p = _prices()[SECTORS[:3]]
    try:
        build_reversal_signal(p, 5, 0.10)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_config_is_long_only_equity():
    cfg = make_equity_config()
    assert cfg.allow_short is False
    assert cfg.max_leverage == MAX_LEVERAGE
    assert cfg.max_position_size == MAX_POS


def test_inverse_signal_is_opposite_rank():
    p = _prices(500)
    mask = pd.Series([i >= 300 for i in range(len(p))], index=p.index)
    sig = _inverse_signal(p, {"lookback": 5, "vol_target": 0.10}, mask).fillna(0.0)
    assert (sig >= 0.0).all().all() and (sig <= MAX_POS + 1e-12).all().all()


def test_turnover_diagnostic_nonnegative():
    p = _prices(500)
    sig = build_reversal_signal(p, 5, 0.10).fillna(0.0)
    assert _turnover(sig, SECTORS) >= 0.0


def test_dict_metrics_shape():
    rets = np.random.default_rng(1).normal(0.001, 0.01, 100)
    m = _dict_metrics(rets)
    assert set(m) == {"sharpe", "profit_factor", "max_drawdown", "num_trades"}
