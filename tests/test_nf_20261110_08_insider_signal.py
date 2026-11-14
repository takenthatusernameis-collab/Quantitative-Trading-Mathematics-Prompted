"""Focused tests for NF-20261110-08 / H182 insider-selling cross-section runner."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from run_nf_20261110_08_insider_signal import (  # noqa: E402
    BENCHMARK,
    FLOW_WINDOWS,
    GATES,
    HYPOTHESIS,
    MAX_LEVERAGE,
    MAX_POS,
    N_LONG,
    NF_ID,
    REBALANCE_EVERY,
    UNIVERSE,
    VOL_TARGETS,
    build_sell_pressure,
    build_signal,
    daily_net_sell_value,
    evaluate_gates,
    load_insider_corpus,
    map_available_to_trading_day,
    _dict_metrics,
    _inverse_signal,
    _max_drawdown,
    _profit_factor,
    _select_on_train,
    _turnover,
)

TRANSACTION_COLUMNS = [
    "cik",
    "accession_number",
    "form",
    "issuer_name",
    "issuer_trading_symbol",
    "reporting_owner",
    "officer_title",
    "is_director",
    "is_officer",
    "is_ten_percent_owner",
    "is_other",
    "security_kind",
    "security_title",
    "transaction_date",
    "transaction_code",
    "transaction_form_type",
    "shares",
    "price_per_share",
    "acquired_disposed",
    "direct_or_indirect",
    "nature_of_ownership",
    "accepted_at",
    "available_at",
]


def _tx(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    for column in TRANSACTION_COLUMNS:
        if column not in frame.columns:
            frame[column] = np.nan
    return frame[TRANSACTION_COLUMNS]


def _prices(n: int = 800, seed: int = 11) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    index = pd.bdate_range("2024-01-02", periods=n)
    common = rng.normal(0.0003, 0.009, n)
    data = {}
    for i, symbol in enumerate(UNIVERSE):
        idio = rng.normal(0.0, 0.006 + 0.0005 * (i % 4), n)
        data[symbol] = 100.0 * np.exp(np.cumsum(0.7 * common + 0.5 * idio))
    return pd.DataFrame(data, index=index)


def _volume(close: pd.DataFrame, seed: int = 5) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {symbol: rng.uniform(1e6, 5e6, len(close.index)) for symbol in close.columns},
        index=close.index,
    )


def _corpus(close: pd.DataFrame, *, sells_per_symbol: int = 20, seed: int = 3) -> dict:
    rng = np.random.default_rng(seed)
    index = close.index
    corpus = {}
    for symbol in close.columns:
        dates = rng.choice(index, size=sells_per_symbol, replace=False)
        rows = [
            {
                "transaction_code": "S",
                "security_kind": "non_derivative",
                "shares": float(rng.uniform(100, 10_000)),
                "price_per_share": float(close.loc[date, symbol]),
                "available_at": date + pd.Timedelta(hours=22),
            }
            for date in dates
        ]
        corpus[symbol] = _tx(rows)
    return corpus


def test_constants_and_gates():
    assert NF_ID == "NF-20261110-08"
    assert HYPOTHESIS == "H182"
    assert BENCHMARK == "SPY"
    assert len(UNIVERSE) == 10
    assert N_LONG == 3 and REBALANCE_EVERY == 5
    assert FLOW_WINDOWS == [63, 126]
    assert VOL_TARGETS == [0.10, 0.15]
    assert GATES["min_sharpe"] == 1.0
    assert GATES["min_trades"] == 50
    assert GATES["min_profit_factor"] == 1.3
    assert GATES["max_drawdown"] == 0.15
    assert GATES["min_walkforward_stability"] == 0.7
    assert GATES["min_worst_regime_sharpe"] == 0.3
    assert GATES["max_p_value"] == 0.05
    assert GATES["min_information_ratio"] == 0.0
    assert GATES["min_perturbed_sharpe_ratio"] == 0.5


def test_map_available_to_trading_day_rolls_weekend_forward():
    index = pd.bdate_range("2025-01-01", periods=10)
    # 2025-01-04 is a Saturday -> next trading day is Monday 2025-01-06.
    dates = pd.Series([pd.Timestamp("2025-01-03"), pd.Timestamp("2025-01-04")])
    mapped = map_available_to_trading_day(dates, index)
    assert list(mapped) == [pd.Timestamp("2025-01-03"), pd.Timestamp("2025-01-06")]


def test_daily_net_sell_value_signs_and_empty():
    index = pd.bdate_range("2025-01-01", periods=5)
    rows = _tx(
        [
            {
                "transaction_code": "S",
                "security_kind": "non_derivative",
                "shares": 100.0,
                "price_per_share": 10.0,
                "available_at": index[1] + pd.Timedelta(hours=22),
            },
            {
                "transaction_code": "P",
                "security_kind": "non_derivative",
                "shares": 40.0,
                "price_per_share": 10.0,
                "available_at": index[1] + pd.Timedelta(hours=22),
            },
            # Non-open-market rows must not count.
            {
                "transaction_code": "A",
                "security_kind": "non_derivative",
                "shares": 1e6,
                "price_per_share": 10.0,
                "available_at": index[2] + pd.Timedelta(hours=22),
            },
        ]
    )
    daily = daily_net_sell_value(rows, index)
    assert len(daily) == len(index)
    assert daily.iloc[1] == 100.0 * 10.0 - 40.0 * 10.0
    assert daily.iloc[2] == 0.0
    assert daily.iloc[0] == 0.0


def test_daily_net_sell_value_empty_frame():
    index = pd.bdate_range("2025-01-01", periods=3)
    daily = daily_net_sell_value(_tx([]), index)
    assert (daily == 0.0).all()


def test_sell_pressure_causal_no_future_leak():
    close = _prices(400)
    volume = _volume(close)
    corpus = _corpus(close)
    base = build_sell_pressure(corpus, close, volume, 63)
    # Inject a huge sale on the last day; earlier pressure must not move.
    last = close.index[-1]
    extra = _tx(
        [
            {
                "transaction_code": "S",
                "security_kind": "non_derivative",
                "shares": 1e9,
                "price_per_share": 1000.0,
                "available_at": last + pd.Timedelta(hours=22),
            }
        ]
    )
    changed = dict(corpus)
    changed[UNIVERSE[0]] = pd.concat([corpus[UNIVERSE[0]], extra], ignore_index=True)
    after = build_sell_pressure(changed, close, volume, 63)
    pd.testing.assert_frame_equal(
        base.iloc[:-1], after.iloc[:-1], check_names=False, check_exact=False
    )


def test_signal_shape_warmup_and_bounds():
    close = _prices()
    volume = _volume(close)
    corpus = _corpus(close)
    signal = build_signal(close, volume, corpus, 63, 0.10)
    assert list(signal.columns) == list(close.columns)
    warmup = 63 + 21
    assert signal.iloc[:warmup].isna().all().all()
    filled = signal.fillna(0.0)
    assert (filled >= -1e-12).all().all()
    assert (filled <= MAX_POS + 1e-12).all().all()
    assert (filled.sum(axis=1) <= MAX_LEVERAGE + 1e-12).all()


def test_signal_changes_only_on_rebalance_days():
    close = _prices(500)
    volume = _volume(close)
    corpus = _corpus(close)
    signal = build_signal(close, volume, corpus, 63, 0.10).fillna(0.0)
    changed = (signal.diff().abs().sum(axis=1) > 1e-8).to_numpy().copy()
    changed[: 63 + 21] = False
    gaps = np.diff(np.flatnonzero(changed))
    assert len(gaps) == 0 or ((gaps == REBALANCE_EVERY) | (gaps == 0)).all()


def test_inverse_signal_bounds_and_difference():
    close = _prices(500)
    volume = _volume(close)
    corpus = _corpus(close)
    inverse = _inverse_signal(close, volume, corpus, 63, 0.10).fillna(0.0)
    assert (inverse >= 0.0).all().all()
    assert (inverse <= MAX_POS + 1e-12).all().all()


def test_profit_factor_and_drawdown_edges():
    assert _profit_factor(np.array([0.01, 0.02])) == float("inf")
    assert _profit_factor(np.array([-0.01, -0.02])) == 0.0
    assert np.isclose(_profit_factor(np.array([0.02, -0.01])), 2.0)
    assert _max_drawdown(np.array([0.0, -0.1, 0.05])) >= 0.0


def test_dict_metrics_keys():
    metrics = _dict_metrics(np.random.default_rng(1).normal(0.001, 0.01, 100))
    assert set(metrics) == {"sharpe", "profit_factor", "max_drawdown", "num_trades"}


def test_select_on_train_returns_row_and_frame():
    close = _prices(700)
    volume = _volume(close)
    corpus = _corpus(close)
    train_mask = pd.Series(np.arange(len(close)) < 450, index=close.index)

    from qtr.backtest.engine import AssetClass, BacktestConfig, CostModel

    cfg = BacktestConfig(
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        asset_class=AssetClass.EQUITY,
        max_position_size=MAX_POS,
        max_leverage=MAX_LEVERAGE,
        allow_short=False,
    )
    best, frame = _select_on_train(close, volume, corpus, train_mask, cfg)
    assert not frame.empty
    assert best["flow_window"] in FLOW_WINDOWS
    assert best["vol_target"] in VOL_TARGETS


def test_evaluate_gates_keys_and_verdict():
    close = _prices(700)
    volume = _volume(close)
    corpus = _corpus(close)
    from qtr.backtest.engine import AssetClass, BacktestConfig, CostModel, run_backtest

    cfg = BacktestConfig(
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        asset_class=AssetClass.EQUITY,
        max_position_size=MAX_POS,
        max_leverage=MAX_LEVERAGE,
        allow_short=False,
    )
    params = {"flow_window": 63, "vol_target": 0.10}
    signal = build_signal(close, volume, corpus, **params)
    cut = 450
    train_mask = pd.Series(np.arange(len(close)) < cut, index=close.index)
    oos_mask = ~train_mask
    train_res = run_backtest(close.loc[train_mask], signal.loc[train_mask], cfg)
    oos_res = run_backtest(close.loc[oos_mask], signal.loc[oos_mask], cfg)
    benchmark = run_backtest(
        close.loc[oos_mask],
        pd.DataFrame(
            {symbol: 1.0 / len(UNIVERSE) for symbol in UNIVERSE},
            index=close.loc[oos_mask].index,
        ),
        cfg,
    )
    result = evaluate_gates(
        oos_res, train_res, benchmark, close, volume, corpus, oos_mask, params, cfg
    )
    assert result["verdict"] in {"PASS", "REJECT"}
    assert result["passed"] <= result["total"]
    assert set(result["gates"]) == {
        "sharpe_ge_1_0",
        "trades_ge_50",
        "profit_factor_ge_1_3",
        "max_drawdown_le_15pct",
        "walkforward_stability_ge_0_7",
        "worst_regime_rolling252_sharpe_ge_0_3",
        "benchmark_p_le_0_05_ir_ge_0",
        "perturbation_min_ratio_ge_0_5",
    }


def test_turnover_nonnegative():
    close = _prices(400)
    volume = _volume(close)
    corpus = _corpus(close)
    signal = build_signal(close, volume, corpus, 63, 0.10)
    assert _turnover(signal) >= 0.0


def test_load_insider_corpus_missing_raises(tmp_path):
    try:
        load_insider_corpus(cache_dir=tmp_path, universe=UNIVERSE)
    except RuntimeError as error:
        assert "incomplete insider corpus" in str(error)
        return
    raise AssertionError("expected RuntimeError for an empty cache")