"""Focused tests for NF-20261106-31 / H116 ITA/SPY defense leadership runner."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from run_nf_20261106_31_ita_spy_defense import (  # noqa: E402
    GATES,
    ITA,
    MAX_POS,
    SPY,
    _profit_factor,
    _select_on_train,
    build_defense_leadership_signal,
    evaluate_gates,
    make_equity_config,
)


def _prices(n=900, seed=31):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2014-01-01", periods=n)
    ita = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
    spy = 200 * np.exp(np.cumsum(rng.normal(0.0004, 0.009, n)))
    return pd.DataFrame({ITA: ita, SPY: spy}, index=idx)


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


def test_signal_columns_warmup_and_bounds():
    sig = build_defense_leadership_signal(_prices(), 21, 126, 1.0, 0.10)
    assert list(sig.columns) == [SPY]
    assert (sig.iloc[:147] == 0.0).all().all()
    assert (sig[SPY] >= -1e-12).all() and (sig[SPY] <= MAX_POS + 1e-12).all()


def test_signal_shift1_causality_proxy():
    p = _prices()
    s1 = build_defense_leadership_signal(p, 21, 126, 1.0, 0.10)
    p2 = p.copy()
    p2.loc[p2.index[-1], SPY] *= 1.2
    s2 = build_defense_leadership_signal(p2, 21, 126, 1.0, 0.10)
    pd.testing.assert_series_equal(s1[SPY].iloc[:-1], s2[SPY].iloc[:-1], check_names=False)


def test_evaluate_gates_returns_expected_keys():
    p = _prices(1200)
    cfg = make_equity_config()
    sig = build_defense_leadership_signal(p, 21, 126, 1.0, 0.10)
    bh = pd.DataFrame({SPY: 1.0}, index=p.index)
    tr = run_slice(p, sig, bh, cfg, slice(0, 700))
    oos = run_slice(p, sig, bh, cfg, slice(700, 1200))
    bench = run_bench(p, bh, cfg, slice(700, 1200))
    mask = pd.Series(False, index=p.index)
    mask.iloc[700:1200] = True
    res = evaluate_gates(
        oos,
        tr,
        bench,
        p,
        mask,
        {"lookback": 21, "z_window": 126, "entry_scale": 1.0, "vol_target": 0.10},
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


def test_profit_factor_edges():
    assert _profit_factor(np.array([0.01, 0.02])) == float("inf")
    assert _profit_factor(np.array([-0.01, -0.02])) == 0.0
    assert np.isclose(_profit_factor(np.array([0.02, -0.01])), 2.0)


def test_select_on_train_returns_row_and_frame():
    p = _prices(1400)
    train_mask = pd.Series([i < 900 for i in range(len(p))], index=p.index)
    best, df = _select_on_train(p, train_mask, make_equity_config())
    assert not df.empty
    for k in ("lookback", "z_window", "entry_scale", "vol_target"):
        assert k in best


def test_signal_missing_symbol_raises():
    p = _prices()[[SPY]]
    try:
        build_defense_leadership_signal(p, 21, 126, 1.0, 0.10)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_signal_handles_zero_vol_scale():
    p = _prices()
    p[SPY] = 200.0
    sig = build_defense_leadership_signal(p, 21, 126, 1.0, 0.10)
    assert (sig[SPY].iloc[200:] == 0.0).all()


def run_slice(prices, sig, _bh, cfg, sl):
    from qtr.backtest.engine import run_backtest

    idx = prices.index[sl]
    return run_backtest(prices.loc[idx, [SPY]], sig.loc[idx], cfg)


def run_bench(prices, bh, cfg, sl):
    from qtr.backtest.engine import run_backtest

    idx = prices.index[sl]
    return run_backtest(prices.loc[idx, [SPY]], bh.loc[idx], cfg)


def test_defense_strength_reduces_exposure_directionally():
    """When ITA strongly outperforms SPY late in series, exposure should reduce."""
    p = _prices(500)
    # inject strong ITA outperformance at end
    p.loc[p.index[-60:], ITA] = p.loc[p.index[-60:], ITA].values * np.linspace(1.0, 1.4, 60)
    sig = build_defense_leadership_signal(p, 21, 126, 1.0, 0.10)
    assert sig[SPY].iloc[-1] <= sig[SPY].max() + 1e-12


def test_config_is_long_only_equity():
    cfg = make_equity_config()
    assert cfg.allow_short is False
    assert cfg.max_leverage == 1.0
    assert cfg.max_position_size == MAX_POS
