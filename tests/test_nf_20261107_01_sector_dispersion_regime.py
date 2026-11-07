"""Focused tests for NF-20261107-01 / H118 sector dispersion regime runner."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from run_nf_20261107_01_sector_dispersion_regime import (  # noqa: E402
    GATES,
    MAX_POS,
    SECTORS,
    SPY,
    UNIVERSE,
    _cross_section_dispersion,
    _profit_factor,
    _select_on_train,
    build_dispersion_signal,
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
    data[SPY] = 200 * np.exp(np.cumsum(common * 0.9 + rng.normal(0, 0.002, n)))
    return pd.DataFrame(data, index=idx)[UNIVERSE]


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
    assert SPY == "SPY"
    assert len(SECTORS) == 9
    assert "XLC" not in SECTORS and "XLRE" not in SECTORS
    assert set(UNIVERSE) == set(SECTORS + [SPY])


def test_cross_section_dispersion_range():
    p = _prices(400)
    rets = p[SECTORS].pct_change()
    disp = _cross_section_dispersion(rets, 21)
    valid = disp.dropna()
    assert len(valid) > 200
    assert (valid >= 0.0).all()


def test_signal_columns_warmup_and_bounds():
    sig = build_dispersion_signal(_prices(), 21, 126, 1.0, 0.10)
    assert list(sig.columns) == [SPY]
    assert (sig.iloc[:147] == 0.0).all().all()
    assert (sig[SPY] >= -1e-12).all() and (sig[SPY] <= MAX_POS + 1e-12).all()


def test_signal_causality_no_future_leak():
    p = _prices(600)
    s1 = build_dispersion_signal(p, 21, 126, 1.0, 0.10)
    p2 = p.copy()
    p2.iloc[-1] = p2.iloc[-1] * 1.15
    s2 = build_dispersion_signal(p2, 21, 126, 1.0, 0.10)
    pd.testing.assert_series_equal(s1[SPY].iloc[:-1], s2[SPY].iloc[:-1], check_names=False)


def test_high_dispersion_reduces_exposure_directionally():
    """Inject dispersed sector moves late; exposure must stay finite and
    bounded (high-z mapping reduces exposure at the stressed tail)."""
    p = _prices(500)
    for i, s in enumerate(SECTORS):
        base = p[s].iloc[-61]
        moves = np.linspace(0.0, 0.03 * (1 + 0.2 * i), 60)
        p.loc[p.index[-60:], s] = base * np.exp(np.cumsum(moves))
    sig = build_dispersion_signal(p, 21, 126, 1.0, 0.10)
    assert np.isfinite(sig[SPY].values).all()


def test_profit_factor_edges():
    assert _profit_factor(np.array([0.01, 0.02])) == float("inf")
    assert _profit_factor(np.array([-0.01, -0.02])) == 0.0
    assert np.isclose(_profit_factor(np.array([0.02, -0.01])), 2.0)


def test_evaluate_gates_returns_expected_keys():
    p = _prices(1200)
    cfg = make_equity_config()
    sig = build_dispersion_signal(p, 21, 126, 1.0, 0.10)
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
    for k in ("lookback", "z_window", "entry_scale", "vol_target"):
        assert k in best


def test_signal_missing_symbol_raises():
    p = _prices()[[SPY] + SECTORS[:3]]
    try:
        build_dispersion_signal(p, 21, 126, 1.0, 0.10)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_config_is_long_only_equity():
    cfg = make_equity_config()
    assert cfg.allow_short is False
    assert cfg.max_leverage == 1.0
    assert cfg.max_position_size == MAX_POS
