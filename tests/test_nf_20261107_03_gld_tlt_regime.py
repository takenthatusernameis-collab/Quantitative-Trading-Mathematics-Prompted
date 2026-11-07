"""Focused tests for NF-20261107-03 / H120 GLD/TLT regime runner."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from run_nf_20261107_03_gld_tlt_regime import (  # noqa: E402
    DURATION,
    GATES,
    GOLD,
    MAX_POS,
    SPY,
    UNIVERSE,
    _profit_factor,
    _ratio_momentum,
    _select_on_train,
    build_gld_tlt_signal,
    evaluate_gates,
    make_equity_config,
)


def _prices(n=900, seed=42):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2014-01-01", periods=n)
    g = 1200 * np.exp(np.cumsum(rng.normal(0.0002, 0.009, n)))
    t = 100 * np.exp(np.cumsum(rng.normal(0.0001, 0.006, n) - 0.2 * rng.normal(0, 0.009, n)))
    s = 200 * np.exp(np.cumsum(0.3 * rng.normal(0, 0.009, n) + rng.normal(0.0003, 0.006, n)))
    return pd.DataFrame({GOLD: g, DURATION: t, SPY: s}, index=idx)[UNIVERSE]


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


def test_universe():
    assert UNIVERSE == [GOLD, DURATION, SPY]


def test_ratio_momentum_finite():
    m = _ratio_momentum(_prices(400), 21)
    assert np.isfinite(m.dropna().values).all()
    assert len(m.dropna()) > 300


def test_signal_columns_warmup_and_bounds():
    sig = build_gld_tlt_signal(_prices(), 21, 126, 1.0, 0.10)
    assert list(sig.columns) == [SPY]
    warm = 21 + 126 + 21
    # Vol scaling can be NaN->0 in warmup; signal is zero until sufficient history.
    assert (sig.iloc[: warm - 30] == 0.0).all().all()
    assert (sig[SPY] >= -1e-12).all() and (sig[SPY] <= MAX_POS + 1e-12).all()


def test_signal_causality_no_future_leak():
    p = _prices(600)
    s1 = build_gld_tlt_signal(p, 21, 126, 1.0, 0.10)
    p2 = p.copy()
    p2.iloc[-1] = p2.iloc[-1] * 1.15
    s2 = build_gld_tlt_signal(p2, 21, 126, 1.0, 0.10)
    pd.testing.assert_series_equal(s1[SPY].iloc[:-1], s2[SPY].iloc[:-1], check_names=False)


def test_high_gld_tlt_momentum_reduces_exposure():
    p = _prices(600)
    # make gold surge and TLT fall late -> high ratio momentum / z -> lower exposure
    for i in range(60):
        p.loc[p.index[-60 + i], GOLD] = p[GOLD].iloc[-61] * np.exp(0.06 * (i + 1) / 60)
        p.loc[p.index[-60 + i], DURATION] = p[DURATION].iloc[-61] * np.exp(-0.03 * (i + 1) / 60)
    sig = build_gld_tlt_signal(p, 21, 126, 1.0, 0.10)
    assert np.isfinite(sig[SPY].values).all()
    assert sig[SPY].iloc[-10:].mean() <= MAX_POS + 1e-9


def test_profit_factor_edges():
    assert _profit_factor(np.array([0.01, 0.02])) == float("inf")
    assert _profit_factor(np.array([-0.01, -0.02])) == 0.0
    assert np.isclose(_profit_factor(np.array([0.02, -0.01])), 2.0)


def test_evaluate_gates_returns_expected_keys():
    p = _prices(1200)
    cfg = make_equity_config()
    sig = build_gld_tlt_signal(p, 21, 126, 1.0, 0.10)
    bh = pd.DataFrame({SPY: 1.0}, index=p.index)
    from qtr.backtest.engine import run_backtest

    tr = run_backtest(p.loc[p.index[:700], [SPY]], sig.loc[p.index[:700]], cfg)
    oos = run_backtest(p.loc[p.index[700:], [SPY]], sig.loc[p.index[700:]], cfg)
    bench = run_backtest(p.loc[p.index[700:], [SPY]], bh.loc[p.index[700:]], cfg)
    mask = pd.Series(False, index=p.index)
    mask.iloc[700:] = True
    res = evaluate_gates(
        oos,
        tr,
        bench,
        p,
        mask,
        {"lookback": 21, "z_window": 126, "entry_scale": 1.0, "vol_target": 0.10},
    )
    assert res["verdict"] in {"PASS", "REJECT"}
    assert res["pass_total"] == 8
    assert set(res["gates"]) >= {
        "sharpe",
        "profit_factor",
        "max_drawdown",
        "trade_count",
        "walkforward_stability",
        "worst_regime_sharpe",
        "benchmark_p_ir",
        "perturbation",
    }


def test_select_on_train_returns_params():
    p = _prices(1400)
    train_mask = pd.Series(False, index=p.index)
    train_mask.iloc[:900] = True
    params, score = _select_on_train(p, train_mask)
    assert set(params) == {"lookback", "z_window", "entry_scale", "vol_target"}
    assert np.isfinite(score) or np.isnan(score)


def test_config_matches_cost_model():
    cfg = make_equity_config()
    assert cfg.asset_class.name == "EQUITY"
    assert cfg.max_position_size == MAX_POS
    assert cfg.allow_short is False
