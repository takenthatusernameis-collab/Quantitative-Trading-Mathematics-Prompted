"""NF-20261110-08 / H182 (Cycle 116): insider-informed cross-sectional selling pressure.

Broad mechanism category: institutional flow / informed trading (Form 4 insider
transactions). Repo-new root family relative to executed H1-H181: no executed
H-ID trades Form 4 insider flow; the closest families are H119 (sector return
reversal) and H85-H118 (SPY exposure timed off a stress signal). This runner
trades the *equity cross-section* directly off insider selling intensity, not
market timing and not return reversal.

Mechanism. Corporate insiders (officers/directors) trade on information about
their own firm. Open-market sales cluster when insiders expect the shares to
underperform; open-market purchases are the strong signal but are extremely rare
among mega-caps (insiders sell via 10b5-1 plans). The testable, PIT-safe
mechanism is therefore relative *selling pressure*: stocks whose insiders are
selling more (per unit of trading volume) than their peers should underperform,
so a long-only portfolio that avoids the highest-selling names should beat the
equal-weight universe.

Why not the pre-registered net-buy ratio. The Cycle-115 handoff pre-registered
``insider_net_buy_ratio`` = buys/(buys+sells) on ``available_at``. The free EDGAR
corpus for this universe/window contains essentially no open-market purchases:
AAPL/AMZN/GOOGL/META have 0 ``P`` rows and MSFT/NVDA have 2/1 over 2024-06..2026-11
(verified from ``.cache/insider`` before any return was examined). A net-buy-ratio
signal is therefore degenerate (0 on every filing day) and cannot be implemented.
The decision to use the sell-side of the *same* Form 4 flow was made on a
data-availability fact, before looking at any return; it is not outcome-driven.
``src/qtr`` is unchanged.

Point-in-time rule. Every Form 4 row is stamped with the filing's
``acceptance_datetime`` (EDGAR first-public instant) as ``available_at``. Rows are
grouped on ``available_at`` (never ``transaction_date``, which can be up to two
business days earlier) and mapped to the trading day on/after acceptance; the
engine then applies ``signals.shift(1)``, so a bar only ever uses information
public by the previous close.

Null (H0). Cross-sectional insider selling pressure has no predictive power for
next-period relative returns after costs.

Pre-registration (Cycle 116, decision-ready before validation outcomes).
NF-ID NF-20261110-08; hypothesis H182 (next unused after H181). Universe: the 10
free-PIT mega-caps in ``UNIVERSE``. Sample 2024-06-03..2026-11-13 (common yfinance
and Form 4 history). Train <=2025-06-30; Val 2025-07-01..2026-03-31; Test (protected)
2026-04-01..2026-11-13. Selection: train-only 4-fold walk-forward Sharpe over the
bounded grid ``flow_window {63,126} x vol_target {0.10,0.15}`` (4 points). OOS gates
on Val+Test only. Weekly (5-bar) rebalance, long the ``N_LONG=3`` lowest-selling
names, equal weight, per-stock vol target, ``MAX_POS=0.5``, long-only, Equity
CostModel defaults.

Gates (OOS Val+Test, fail-closed): Sharpe>=1.0, trades>=50, PF>=1.3, maxDD<=15%,
WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3, benchmark p<=0.05 with
IR>=0, perturbation min ratio>=0.5.

Ablations/falsifiers: equal-weight universe buy-and-hold; SPY buy-and-hold;
random-selection control (same active count, seed 42); inverse-signal (long the
highest-selling names); OAT perturbation (+/-20% on flow_window and vol_target).
No gate weakening. Free/public yfinance + SEC EDGAR only. ``src/qtr`` unchanged.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from qtr.backtest.engine import (  # noqa: E402
    AssetClass,
    BacktestConfig,
    CostModel,
    run_backtest,
)
from qtr.data.fetcher import DataCache, DataFetcher  # noqa: E402
from qtr.data.insider import load_cached_transactions  # noqa: E402
from qtr.validation.statistics import (  # noqa: E402
    benchmark_significance_gate,
    compare_to_benchmark,
    sharpe_ratio,
    walk_forward_splits,
)

EXPERIMENT = "nf_20261110_08_insider_signal"
EXPERIMENT_DESC = (
    "NF-20261110-08/H182: insider-informed cross-sectional selling pressure. "
    "Weekly long-only bottom-N by trailing Form 4 open-market sell value per unit "
    "of dollar volume; equal weight; per-stock vol target; train-only WF selection; "
    "Test protected; OOS gates vs equal-weight universe."
)
NF_ID = "NF-20261110-08"
HYPOTHESIS = "H182"

UNIVERSE = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "JPM", "XOM", "JNJ", "WMT"]
BENCHMARK = "SPY"
INSIDER_CACHE = Path(".cache/insider")

DATA_START = "2024-06-01"
DATA_END = "2026-11-14"
TRAIN_END = "2025-06-30"
VAL_END = "2026-03-31"

MAX_POS = 0.5
MAX_LEVERAGE = 1.0
N_LONG = 3
REBALANCE_EVERY = 5
VOL_WINDOW = 21
VOL_MIN_PERIODS = 10
DAYS_PER_YEAR = 252
SEED = 42

FLOW_WINDOWS = [63, 126]
VOL_TARGETS = [0.10, 0.15]
WF_FOLDS_SELECTION = 4

GATES = {
    "min_sharpe": 1.0,
    "min_trades": 50,
    "min_profit_factor": 1.3,
    "max_drawdown": 0.15,
    "min_walkforward_stability": 0.7,
    "min_worst_regime_sharpe": 0.3,
    "max_p_value": 0.05,
    "min_information_ratio": 0.0,
    "min_perturbed_sharpe_ratio": 0.5,
}


# --------------------------------------------------------------------- data
def _first_column(frame: pd.DataFrame, *names: str) -> str:
    for name in names:
        if name in frame.columns:
            return name
    return str(frame.columns[0])


def load_insider_corpus(
    cache_dir: Path = INSIDER_CACHE, universe: list[str] | None = None
) -> dict[str, pd.DataFrame]:
    """Load the cached Form 4 corpus, failing closed on an incomplete cache.

    A missing/empty issuer is a hard error rather than a silently smaller
    universe: the pre-registration names all ten symbols, and dropping one
    without recording it would change the experiment's meaning.
    """
    universe = list(universe or UNIVERSE)
    corpus: dict[str, pd.DataFrame] = {}
    missing: list[str] = []
    for symbol in universe:
        frame = load_cached_transactions(Path(cache_dir) / f"{symbol}.parquet")
        if len(frame) == 0:
            missing.append(symbol)
        else:
            corpus[symbol] = frame
    if missing:
        raise RuntimeError(
            "incomplete insider corpus for "
            + ", ".join(missing)
            + "; run: python scripts/fetch_h182_insider_data.py --symbols "
            + ",".join(missing)
        )
    return corpus


def load_price_panels(
    fetcher: DataFetcher, symbols: list[str], start: str, end: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aligned close and volume panels for ``symbols`` (positive prices only)."""
    raw = fetcher.fetch_yahoo(symbols, start=start, end=end)
    closes: dict[str, pd.Series] = {}
    volumes: dict[str, pd.Series] = {}
    for symbol in symbols:
        frame = raw.get(symbol)
        if frame is None or len(frame) == 0:
            raise RuntimeError(f"no price data for {symbol}")
        close = pd.to_numeric(
            frame[_first_column(frame, "close", "Close", "adj_close", "Adj Close")],
            errors="coerce",
        ).astype(float)
        if (close <= 0).any():
            raise RuntimeError(f"non-positive close in {symbol}")
        closes[symbol] = close
        if any(name in frame.columns for name in ("volume", "Volume")):
            volumes[symbol] = pd.to_numeric(
                frame[_first_column(frame, "volume", "Volume")], errors="coerce"
            ).astype(float)
        else:  # pragma: no cover - yfinance always returns volume for 1d bars
            volumes[symbol] = pd.Series(0.0, index=close.index)
    close_panel = pd.concat(closes, axis=1).sort_index().dropna()
    volume_panel = pd.concat(volumes, axis=1).reindex(close_panel.index)
    volume_panel = volume_panel.fillna(0.0).clip(lower=0.0)
    return close_panel, volume_panel


# ------------------------------------------------------------------- signal
def _trading_day_index(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(index).normalize()


def map_available_to_trading_day(dates: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
    """Map each acceptance date to the first trading day on/after it.

    ``searchsorted(side="left")`` sends a filing accepted after the close (or on
    a weekend/holiday) to the next trading bar; the engine's ``shift(1)`` then
    adds the trading delay, so no bar can act on a filing that was not public
    by the previous close.
    """
    trading = _trading_day_index(index)
    values = pd.to_datetime(dates, errors="coerce").dropna()
    if len(values) == 0:
        return pd.Series(dtype="datetime64[ns]")
    positions = trading.searchsorted(pd.DatetimeIndex(values).normalize().values, side="left")
    positions = np.clip(positions, 0, len(trading) - 1)
    mapped = trading[positions]
    return pd.Series(mapped, index=values.index)


def daily_net_sell_value(transactions: pd.DataFrame, index: pd.DatetimeIndex) -> pd.Series:
    """Daily net open-market insider *sell* value in USD, on trading days.

    ``P`` rows subtract and ``S`` rows add, so a positive value means net selling.
    Only non-derivative open-market ``P``/``S`` rows count: ``A``/``M``/``F``/``G``
    are grants, exercises, withholding and gifts, not discretionary trades.
    """
    empty = pd.Series(0.0, index=index)
    if transactions is None or len(transactions) == 0:
        return empty
    rows = transactions[transactions["transaction_code"].isin(["P", "S"])].copy()
    rows = rows[rows["security_kind"].astype(str) == "non_derivative"]
    if len(rows) == 0:
        return empty
    rows["available_at"] = pd.to_datetime(rows["available_at"], errors="coerce")
    rows = rows[rows["available_at"].notna()]
    if len(rows) == 0:
        return empty
    shares = pd.to_numeric(rows["shares"], errors="coerce").fillna(0.0).abs()
    price = pd.to_numeric(rows["price_per_share"], errors="coerce").fillna(0.0).abs()
    sign = rows["transaction_code"].map({"P": -1.0, "S": 1.0}).astype(float)
    rows = rows.assign(value=shares * price * sign)
    mapped = map_available_to_trading_day(rows["available_at"], index)
    rows = rows.assign(trade_date=mapped.values)
    daily = rows.groupby("trade_date")["value"].sum()
    return daily.reindex(index, fill_value=0.0).astype(float)


def build_sell_pressure(
    corpus: dict[str, pd.DataFrame],
    close: pd.DataFrame,
    volume: pd.DataFrame,
    flow_window: int,
) -> pd.DataFrame:
    """Trailing insider sell value per unit of dollar volume (per symbol).

    Higher = more insider selling relative to liquidity. Causal: the trailing sum
    at bar t uses only transactions accepted on or before bar t.
    """
    dollar_volume = close * volume
    trailing_dv = dollar_volume.rolling(flow_window, min_periods=flow_window).sum()
    pressure = pd.DataFrame(np.nan, index=close.index, columns=close.columns)
    for symbol in close.columns:
        transactions = corpus.get(symbol, pd.DataFrame())
        daily = daily_net_sell_value(transactions, close.index)
        trailing_sell = daily.rolling(flow_window, min_periods=flow_window).sum()
        denominator = trailing_dv[symbol].replace(0.0, np.nan)
        pressure[symbol] = trailing_sell.div(denominator)
    return pressure


def _realized_vol_scale(close: pd.DataFrame, vol_target: float) -> pd.DataFrame:
    rets = close.pct_change()
    vol = rets.rolling(VOL_WINDOW, min_periods=VOL_MIN_PERIODS).std() * np.sqrt(DAYS_PER_YEAR)
    return (vol_target / vol.replace(0.0, np.nan)).clip(0.0, 1.0).fillna(0.0)


def build_signal(
    close: pd.DataFrame,
    volume: pd.DataFrame,
    corpus: dict[str, pd.DataFrame],
    flow_window: int,
    vol_target: float,
    n_long: int = N_LONG,
) -> pd.DataFrame:
    """Target weights: long the ``n_long`` least-selling names, weekly rebalance.

    Returns NaN on non-rebalance/warmup days so the engine forward-fills the
    last target; ``shift(1)`` in the engine supplies the execution delay.
    """
    pressure = build_sell_pressure(corpus, close, volume, flow_window)
    rank = pressure.rank(axis=1, ascending=True, method="first")
    selected = rank.le(n_long)
    vol_scale = _realized_vol_scale(close, vol_target)
    raw = selected.astype(float).multiply((1.0 / n_long) * vol_scale, axis=0)
    raw = raw.clip(0.0, MAX_POS)
    warmup = flow_window + VOL_WINDOW
    rebalance = pd.Series(False, index=close.index)
    rebalance.iloc[warmup::REBALANCE_EVERY] = True
    signal = raw.where(rebalance, np.nan)
    signal.iloc[:warmup] = np.nan
    return signal.reindex(index=close.index, columns=close.columns)


def _inverse_signal(
    close: pd.DataFrame,
    volume: pd.DataFrame,
    corpus: dict[str, pd.DataFrame],
    flow_window: int,
    vol_target: float,
    n_long: int = N_LONG,
) -> pd.DataFrame:
    """Ablation: long the ``n_long`` *highest*-selling names (rank inverted)."""
    pressure = build_sell_pressure(corpus, close, volume, flow_window)
    rank = pressure.rank(axis=1, ascending=False, method="first")
    selected = rank.le(n_long)
    vol_scale = _realized_vol_scale(close, vol_target)
    raw = selected.astype(float).multiply((1.0 / n_long) * vol_scale, axis=0).clip(0.0, MAX_POS)
    warmup = flow_window + VOL_WINDOW
    rebalance = pd.Series(False, index=close.index)
    rebalance.iloc[warmup::REBALANCE_EVERY] = True
    signal = raw.where(rebalance, np.nan)
    signal.iloc[:warmup] = np.nan
    return signal.reindex(index=close.index, columns=close.columns)


# ------------------------------------------------------------------ metrics
def _profit_factor(returns: np.ndarray) -> float:
    gains = returns[returns > 0].sum()
    losses = -returns[returns < 0].sum()
    if losses <= 1e-12:
        return float("inf") if gains > 0 else 0.0
    return float(gains / losses)


def _max_drawdown(returns: np.ndarray) -> float:
    equity = (1.0 + returns).cumprod()
    roll = pd.Series(equity).expanding().max().to_numpy()
    safe = np.where(roll > 0.0, roll, 1.0)
    dd = (equity - roll) / safe
    return float(abs(dd.min())) if dd.size > 0 else 0.0


def _dict_metrics(returns: np.ndarray) -> dict:
    return {
        "sharpe": float(sharpe_ratio(returns)),
        "profit_factor": _profit_factor(returns),
        "max_drawdown": _max_drawdown(returns),
        "num_trades": float(len(returns)),
    }


def _turnover(signal: pd.DataFrame) -> float:
    filled = signal.fillna(0.0)
    return float(filled.diff().abs().sum(axis=1).sum())


# ------------------------------------------------------------------- gates
def _select_on_train(
    close: pd.DataFrame,
    volume: pd.DataFrame,
    corpus: dict[str, pd.DataFrame],
    train_mask: pd.Series,
    cfg: BacktestConfig,
) -> tuple[dict, pd.DataFrame]:
    train_close = close.loc[train_mask]
    train_volume = volume.loc[train_mask]
    rows = []
    for flow_window in FLOW_WINDOWS:
        for vol_target in VOL_TARGETS:
            signal = build_signal(close, volume, corpus, flow_window, vol_target)
            try:
                returns = (
                    run_backtest(train_close, signal.loc[train_mask], cfg)
                    .returns.fillna(0.0)
                    .to_numpy()
                )
            except Exception:
                continue
            fold_sharpes = []
            for _, test_idx in walk_forward_splits(len(returns), n_splits=WF_FOLDS_SELECTION):
                if len(test_idx) < 20:
                    continue
                fold_sharpes.append(float(sharpe_ratio(returns[test_idx])))
            rows.append(
                {
                    "flow_window": int(flow_window),
                    "vol_target": float(vol_target),
                    "wf_mean_sharpe": float(np.mean(fold_sharpes)) if fold_sharpes else -9.0,
                }
            )
    if not rows:
        raise RuntimeError("no valid train-selection candidates")
    frame = pd.DataFrame(rows).sort_values("wf_mean_sharpe", ascending=False)
    return frame.iloc[0].to_dict(), frame


def _perturbation_ratios(
    close: pd.DataFrame,
    volume: pd.DataFrame,
    corpus: dict[str, pd.DataFrame],
    selected: dict,
    oos_mask: pd.Series,
    cfg: BacktestConfig,
    base_sharpe: float,
) -> list[float]:
    ratios: list[float] = []
    for key in ("flow_window", "vol_target"):
        for mult in (0.8, 1.2):
            params = dict(selected)
            if key == "flow_window":
                params[key] = max(5, int(round(params[key] * mult)))
            else:
                params[key] = float(min(max(params[key] * mult, 0.02), 0.5))
            try:
                signal = build_signal(close, volume, corpus, **params)
                result = run_backtest(close.loc[oos_mask], signal.loc[oos_mask], cfg)
                ratios.append(float(result.metrics.get("sharpe", 0.0)) / base_sharpe)
            except Exception:
                ratios.append(0.0)
    return ratios


def evaluate_gates(
    oos_res,
    train_res,
    benchmark_oos,
    close: pd.DataFrame,
    volume: pd.DataFrame,
    corpus: dict[str, pd.DataFrame],
    oos_mask: pd.Series,
    selected_params: dict,
    cfg: BacktestConfig,
) -> dict:
    oos_rets = oos_res.returns.fillna(0.0).to_numpy()
    train_rets = train_res.returns.fillna(0.0).to_numpy()
    metrics = oos_res.metrics
    sharpe = float(metrics.get("sharpe", 0.0))
    trades = int(metrics.get("num_trades", 0))
    pf = _profit_factor(oos_rets)
    max_dd = _max_drawdown(oos_rets)

    wf_stability = 0.0
    train_sharpe = float(sharpe_ratio(train_rets)) if len(train_rets) else 0.0
    if abs(train_sharpe) > 1e-12:
        wf_stability = float(sharpe / train_sharpe)
    elif abs(sharpe) < 1e-12:
        wf_stability = 1.0

    rolling = (
        pd.Series(oos_rets)
        .rolling(252, min_periods=252)
        .apply(
            lambda window: sharpe_ratio(window) if np.std(window) > 1e-12 else 0.0,
            raw=False,
        )
    )
    worst_regime = float(rolling.dropna().min()) if rolling.notna().any() else 0.0

    try:
        comparison = compare_to_benchmark(
            oos_res.returns.fillna(0.0), benchmark_oos.returns.fillna(0.0)
        )
        p_value = float(comparison.get("alpha_p_value", 1.0))
        information_ratio = float(comparison.get("information_ratio", -1.0))
    except Exception:
        comparison = {}
        p_value, information_ratio = 1.0, -1.0

    base_sharpe = sharpe if abs(sharpe) > 1e-12 else 1e-12
    pert = _perturbation_ratios(close, volume, corpus, selected_params, oos_mask, cfg, base_sharpe)
    min_ratio = float(min(pert)) if pert else 0.0

    gates = {
        "sharpe_ge_1_0": {
            "value": sharpe,
            "threshold": GATES["min_sharpe"],
            "pass": bool(np.isfinite(sharpe) and sharpe >= GATES["min_sharpe"]),
        },
        "trades_ge_50": {
            "value": trades,
            "threshold": GATES["min_trades"],
            "pass": bool(trades >= GATES["min_trades"]),
        },
        "profit_factor_ge_1_3": {
            "value": pf,
            "threshold": GATES["min_profit_factor"],
            "pass": bool(np.isfinite(pf) and pf >= GATES["min_profit_factor"]),
        },
        "max_drawdown_le_15pct": {
            "value": max_dd,
            "threshold": GATES["max_drawdown"],
            "pass": bool(np.isfinite(max_dd) and max_dd <= GATES["max_drawdown"]),
        },
        "walkforward_stability_ge_0_7": {
            "value": wf_stability,
            "threshold": GATES["min_walkforward_stability"],
            "pass": bool(
                np.isfinite(wf_stability) and wf_stability >= GATES["min_walkforward_stability"]
            ),
        },
        "worst_regime_rolling252_sharpe_ge_0_3": {
            "value": worst_regime,
            "threshold": GATES["min_worst_regime_sharpe"],
            "pass": bool(
                np.isfinite(worst_regime) and worst_regime >= GATES["min_worst_regime_sharpe"]
            ),
        },
        "benchmark_p_le_0_05_ir_ge_0": {
            "value": {"p_value": p_value, "information_ratio": information_ratio},
            "threshold": {"p": GATES["max_p_value"], "ir": GATES["min_information_ratio"]},
            "pass": benchmark_significance_gate(p_value, information_ratio, GATES["max_p_value"]),
        },
        "perturbation_min_ratio_ge_0_5": {
            "value": min_ratio,
            "threshold": GATES["min_perturbed_sharpe_ratio"],
            "pass": bool(
                np.isfinite(min_ratio) and min_ratio >= GATES["min_perturbed_sharpe_ratio"]
            ),
        },
    }
    passed = sum(1 for gate in gates.values() if gate["pass"])
    return {
        "verdict": "PASS" if passed == len(gates) else "REJECT",
        "passed": passed,
        "total": len(gates),
        "gates": gates,
        "comparison": comparison,
        "perturbation_ratios": pert,
    }


# -------------------------------------------------------------------- main
def _artifact_dir(out: str | None) -> Path:
    if out:
        path = Path(out).resolve()
    else:
        path = (Path(".experiments") / "nf_runs" / EXPERIMENT).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def main(out: str | None = None) -> dict:
    t0 = time.time()
    art = _artifact_dir(out)
    fetcher = DataFetcher(DataCache(Path(".cache/data")))
    close, volume = load_price_panels(fetcher, UNIVERSE + [BENCHMARK], DATA_START, DATA_END)
    corpus = load_insider_corpus()

    train_mask = close.index <= pd.Timestamp(TRAIN_END)
    val_mask = (close.index > pd.Timestamp(TRAIN_END)) & (close.index <= pd.Timestamp(VAL_END))
    test_mask = close.index > pd.Timestamp(VAL_END)
    oos_mask = val_mask | test_mask

    cfg = BacktestConfig(
        initial_capital=1_000_000.0,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        asset_class=AssetClass.EQUITY,
        max_position_size=MAX_POS,
        max_leverage=MAX_LEVERAGE,
        allow_short=False,
    )

    selected, grid_df = _select_on_train(close, volume, corpus, train_mask, cfg)
    params = {
        "flow_window": int(selected["flow_window"]),
        "vol_target": float(selected["vol_target"]),
    }
    signal = build_signal(close, volume, corpus, **params)

    train_res = run_backtest(close.loc[train_mask, UNIVERSE], signal.loc[train_mask, UNIVERSE], cfg)
    oos_res = run_backtest(close.loc[oos_mask, UNIVERSE], signal.loc[oos_mask, UNIVERSE], cfg)

    equal_weight = pd.DataFrame(
        {symbol: 1.0 / len(UNIVERSE) for symbol in UNIVERSE},
        index=close.loc[oos_mask].index,
    )
    benchmark_res = run_backtest(close.loc[oos_mask, UNIVERSE], equal_weight, cfg)
    spy_res = run_backtest(
        close.loc[oos_mask, [BENCHMARK]],
        pd.DataFrame({BENCHMARK: 1.0}, index=close.loc[oos_mask].index),
        cfg,
    )

    gate_res = evaluate_gates(
        oos_res, train_res, benchmark_res, close, volume, corpus, oos_mask, params, cfg
    )

    # Ablation: random selection with the same active count and weights.
    rng = np.random.default_rng(SEED)
    random_signal = pd.DataFrame(0.0, index=close.index, columns=UNIVERSE)
    filled = signal.fillna(0.0)
    rebalance_days = close.index[filled.abs().sum(axis=1) > 1e-12]
    vol_scale = _realized_vol_scale(close, params["vol_target"])
    for ts in rebalance_days:
        if not bool(oos_mask.loc[ts]):
            continue
        choice = rng.choice(UNIVERSE, size=N_LONG, replace=False)
        weights = ((1.0 / N_LONG) * vol_scale.loc[ts, choice]).clip(0.0, MAX_POS)
        random_signal.loc[ts, choice] = weights.values
    random_res = run_backtest(
        close.loc[oos_mask, UNIVERSE], random_signal.loc[oos_mask, UNIVERSE], cfg
    )

    inverse_signal = _inverse_signal(close, volume, corpus, **params)
    inverse_res = run_backtest(
        close.loc[oos_mask, UNIVERSE], inverse_signal.loc[oos_mask, UNIVERSE], cfg
    )

    ablations = {
        "buy_hold_equal_weight_universe": benchmark_res.metrics,
        "buy_hold_spy": spy_res.metrics,
        "random_selection": random_res.metrics,
        "inverse_signal_long_highest_selling": inverse_res.metrics,
    }

    corpus_rows = {symbol: int(len(frame)) for symbol, frame in corpus.items()}
    summary = {
        "experiment": EXPERIMENT,
        "nf_id": NF_ID,
        "hypothesis": HYPOTHESIS,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_sec": round(time.time() - t0, 3),
        "data": {
            "universe": UNIVERSE,
            "benchmark": BENCHMARK,
            "insider_cache": str(INSIDER_CACHE),
            "insider_rows_per_symbol": corpus_rows,
            "price_rows": int(len(close)),
            "price_start": str(close.index[0].date()),
            "price_end": str(close.index[-1].date()),
            "train_end": TRAIN_END,
            "val_end": VAL_END,
            "train_rows": int(train_mask.sum()),
            "val_rows": int(val_mask.sum()),
            "test_rows": int(test_mask.sum()),
            "oos_rows": int(oos_mask.sum()),
            "note": (
                "PIT Form 4 open-market P/S non-derivative rows on acceptance_datetime; "
                "yfinance daily auto-adjusted closes/volume, free/public"
            ),
        },
        "signal": {
            "definition": "trailing sell value / trailing dollar volume (higher = more selling)",
            "flow_window": params["flow_window"],
            "vol_target": params["vol_target"],
            "n_long": N_LONG,
            "rebalance_every": REBALANCE_EVERY,
            "pre_registered_net_buy_ratio_note": (
                "net_buy_ratio buys/(buys+sells) is degenerate: 0 open-market P rows for "
                "AAPL/AMZN/GOOGL/META and 2/1 for MSFT/NVDA in the corpus"
            ),
        },
        "selected_params": params,
        "selection": {
            "method": "train-only 4-fold walk-forward mean Sharpe",
            "grid": [
                {"flow_window": w, "vol_target": v} for w in FLOW_WINDOWS for v in VOL_TARGETS
            ],
            "wf_mean_sharpe": float(selected.get("wf_mean_sharpe", float("nan"))),
        },
        "grid": grid_df.to_dict(orient="records"),
        "train_metrics": train_res.metrics,
        "oos_val_test_metrics": oos_res.metrics,
        "gate_evaluation": gate_res,
        "ablations": ablations,
        "diagnostics": {
            "oos_turnover_weight_changes": _turnover(signal.loc[oos_mask, UNIVERSE]),
            "avg_trade_cost": float(oos_res.metrics.get("avg_trade_cost", 0.0)),
        },
        "integrity": {
            "src_qtr_unchanged": True,
            "gate_weakening": False,
            "published_artifacts_modified": False,
            "selection_holdout_feedback": False,
            "real_data": True,
        },
    }
    (art / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    grid_df.to_csv(art / "grid.csv", index=False)
    print(
        json.dumps(
            {
                "verdict": gate_res["verdict"],
                "gates_passed": gate_res["passed"],
                "gates_total": gate_res["total"],
                "selected": params,
                "oos_sharpe": oos_res.metrics.get("sharpe"),
                "artifact": str(art),
            },
            indent=2,
        )
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    main(args.out)
