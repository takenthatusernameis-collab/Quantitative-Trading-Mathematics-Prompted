"""NF-20261105-19 / H98 (pre-registered): Post-earnings announcement drift (PEAD)
cross-sectional long/short.

Mechanism: stocks with a positive earnings surprise (reported EPS > estimate)
drift upward for ~20 trading days post-announcement; negative surprises drift
downward. Long positive-surprise / short negative-surprise, equal-weight,
held over the drift window.

Data: yfinance earnings dates + EPS estimate/reported (free) for a fixed
large-cap universe; daily prices yfinance.

DATA RANGE NOTE: the pre-registered windows are retained, but free yfinance data
only provides announced earnings (estimate/reported EPS) from ~2020 onward, so
the 2015-2019 train window contains no earnings events and no positions. The OOS
Val+Test windows (2020-2022 / 2023-2026) are fully populated. Results reflect
the available earnings history only and should be treated as preliminary pending
a longer earnings history.

Timing/causality: signal formed at close of announcement day; positions entered
next open; hold 20 trading days; no same-day look-ahead. Engine shift(1).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import numpy as np
import pandas as pd
import yfinance as yf

from qtr.backtest.engine import (
    AssetClass,
    BacktestConfig,
    CostModel,
    run_backtest,
)
from qtr.data.fetcher import DataCache, DataFetcher
from qtr.tracking.experiment import get_tracker
from qtr.validation.statistics import (
    benchmark_significance_gate,
    compare_to_benchmark,
    sharpe_ratio,
)

EXPERIMENT_NAME = "nf_20261105_19_pead"
EXPERIMENT_DESC = (
    "NF-20261105-19/H98: post-earnings announcement drift (PEAD) "
    "cross-sectional long/short. Long positive-surprise / short negative-surprise "
    "equities, equal-weight, held 20 trading days after the announcement close "
    "(next-open execution via engine shift(1)). Net of costs on OOS Val+Test."
)

# Fixed large-cap US equity universe.
UNIVERSE = [
    "AAPL",
    "MSFT",
    "AMZN",
    "GOOGL",
    "META",
    "NVDA",
    "TSLA",
    "JPM",
    "JNJ",
    "V",
    "PG",
    "UNH",
    "HD",
    "MA",
    "DIS",
    "PYPL",
    "ADBE",
    "NFLX",
    "XOM",
    "PEP",
]

# Pre-registered windows; free yfinance earnings data only covers ~2020 onward,
# so the 2015-2019 train window carries no positions (see DATA RANGE NOTE).
DATA_START = "2015-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"

HOLD_DAYS = 20
SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5

GATES = {
    "min_sharpe": 1.0,
    "min_trades": 200,
    "min_profit_factor": 1.3,
    "max_drawdown": 0.15,
    "min_walkforward_stability": 0.7,
    "min_worst_regime_sharpe": 0.3,
    "max_p_value": 0.05,
    "min_information_ratio": 0.0,
    "min_perturbed_sharpe_ratio": 0.5,
}


def make_equity_config() -> BacktestConfig:
    return BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        cost_model=CostModel(),
        asset_class=AssetClass.EQUITY,
        max_position_size=MAX_POS,
        max_leverage=1.0,
        allow_short=True,
    )


def _splits(prices: pd.DataFrame):
    train_mask = prices.index <= pd.Timestamp(TRAIN_END)
    val_mask = (prices.index > pd.Timestamp(TRAIN_END)) & (prices.index <= pd.Timestamp(VAL_END))
    test_mask = prices.index > pd.Timestamp(VAL_END)
    return train_mask, val_mask, test_mask


def _period_metrics(ret: pd.Series, n_trades: int) -> dict:
    r = ret.dropna()
    sr = float(sharpe_ratio(r.values)) if len(r) > 1 else 0.0
    cum = (1 + r).cumprod()
    dd = float((cum / cum.cummax() - 1.0).min()) if len(cum) > 0 else 0.0
    gp = float(r[r > 0].sum())
    gl = float(abs(r[r < 0].sum()))
    pf = gp / gl if gl > 0 else float("inf")
    return {
        "sharpe": sr,
        "max_drawdown": dd,
        "profit_factor": pf,
        "trades": int(n_trades),
        "gross_profit": gp,
        "gross_loss": gl,
        "n_periods": len(r),
    }


def _count_in(trades: pd.DataFrame, mask, prices) -> int:
    if trades is None or len(trades) == 0:
        return 0
    ts = pd.to_datetime(trades["timestamp"])
    if len(prices.index[mask]) == 0:
        return 0
    lo = prices.index[mask].min()
    hi = prices.index[mask].max()
    return int(((ts >= lo) & (ts <= hi)).sum())


def fetch_earnings_events(universe: list[str]) -> dict[str, pd.DataFrame]:
    """Fetch announced earnings events per symbol.

    Returns a dict symbol -> DataFrame indexed by announcement date (tz-naive
    midnight) with columns ``surprise_pct`` and ``sign`` (+1 / -1 / 0). Only
    events with a reported EPS are kept (future announcements are excluded).
    """
    events: dict[str, pd.DataFrame] = {}
    for sym in universe:
        try:
            ed = yf.Ticker(sym).earnings_dates
        except Exception:
            continue
        if ed is None or len(ed) == 0:
            continue
        df = ed.copy()
        df = df.reset_index(names=["ann_date"])
        df["ann_date"] = pd.to_datetime(df["ann_date"]).dt.tz_localize(None)
        reported = pd.to_numeric(df["Reported EPS"], errors="coerce")
        estimate = pd.to_numeric(df["EPS Estimate"], errors="coerce")
        surprise = pd.to_numeric(df["Surprise(%)"], errors="coerce")
        have = reported.notna() & estimate.notna()
        df = df[have].copy()
        if len(df) == 0:
            continue
        reported = reported[have]
        estimate = estimate[have]
        surprise = surprise[have]
        sign = np.sign(surprise.fillna(reported - estimate)).astype(float)
        df["surprise_pct"] = surprise.values
        df["sign"] = sign
        df = df.set_index("ann_date").sort_index()
        events[sym] = df[["surprise_pct", "sign"]]
    return events


def build_pead_targets(
    prices: pd.DataFrame,
    events: dict[str, pd.DataFrame],
    hold_days: int = HOLD_DAYS,
    per_event_weight: float | None = None,
) -> pd.DataFrame:
    """Cross-sectional PEAD targets.

    For each earnings event at close of ``ann_date``, set the target for that
    symbol to ``sign * per_event_weight`` for the next ``hold_days`` trading
    days (entered next open). Engine applies signals.shift(1), so the target at
    the announcement close earns the return to the next day. Overlapping events
    for the same symbol accumulate and are clipped to ``[-MAX_POS, MAX_POS]``.
    """
    idx = prices.index
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    targets = pd.DataFrame(0.0, index=idx, columns=UNIVERSE, dtype=float)
    if per_event_weight is None:
        per_event_weight = MAX_POS / max(1, len(UNIVERSE))
    hold_days = int(max(1, hold_days))
    price_dates = idx
    n = len(price_dates)
    for sym in UNIVERSE:
        ev = events.get(sym)
        if ev is None or len(ev) == 0:
            continue
        col = targets[sym]
        for ann_ts, row in ev.iterrows():
            ann_day = pd.Timestamp(ann_ts)
            if ann_ts.tzinfo is not None:
                ann_day = ann_ts.tz_localize(None)
            start = price_dates.searchsorted(ann_day, side="right")
            if start >= n:
                continue
            end = min(start + hold_days, n)
            sign = float(row["sign"])
            if sign == 0.0:
                continue
            col.iloc[start:end] += sign * per_event_weight
        targets[sym] = col
    return targets.clip(lower=-MAX_POS, upper=MAX_POS)


def full_gate_eval(result, oos_mask, val_mask, test_mask, prices, bench_result):
    rets = result.returns
    oos_r = rets[oos_mask].dropna()
    train_r = rets[prices.index <= pd.Timestamp(TRAIN_END)].dropna()
    val_r = rets[val_mask].dropna()
    test_r = rets[test_mask].dropna()

    oos_m = _period_metrics(oos_r, _count_in(result.trades, oos_mask, prices))
    train_m = _period_metrics(
        train_r, _count_in(result.trades, prices.index <= pd.Timestamp(TRAIN_END), prices)
    )
    test_m = _period_metrics(test_r, _count_in(result.trades, test_mask, prices))
    train_sharpe = train_m["sharpe"]
    test_sharpe = test_m["sharpe"]
    wf_stab = (test_sharpe / train_sharpe) if train_sharpe > 0 else 0.0

    bench_p = 1.0
    ir = 0.0
    try:
        cmp = compare_to_benchmark(rets, bench_result.returns)
        bench_p = float(cmp.get("alpha_p_value", 1.0))
        ir = float(cmp.get("information_ratio", 0.0))
    except Exception:
        pass

    if len(oos_r) >= 252:
        roll = oos_r.rolling(252).apply(lambda x: sharpe_ratio(x.values), raw=False)
        worst_regime = float(roll.min()) if roll.notna().any() else 0.0
    else:
        worst_regime = oos_m["sharpe"]

    passes = {
        "sharpe": oos_m["sharpe"] >= GATES["min_sharpe"],
        "trades": oos_m["trades"] >= GATES["min_trades"],
        "profit_factor": oos_m["profit_factor"] >= GATES["min_profit_factor"],
        "max_drawdown": oos_m["max_drawdown"] >= -GATES["max_drawdown"],
        "walkforward_stability": wf_stab >= GATES["min_walkforward_stability"],
        "worst_regime_sharpe": worst_regime >= GATES["min_worst_regime_sharpe"],
        "p_value": benchmark_significance_gate(bench_p, ir, GATES["max_p_value"]),
        "information_ratio": ir >= GATES["min_information_ratio"],
    }
    return {
        "oos_metrics": oos_m,
        "train_sharpe": train_sharpe,
        "val_sharpe": float(sharpe_ratio(val_r.values)) if len(val_r) > 1 else 0.0,
        "test_metrics": test_m,
        "wf_stability": wf_stab,
        "worst_regime_sharpe": worst_regime,
        "benchmark_p": bench_p,
        "information_ratio": ir,
        "passes": passes,
        "gate_pass_count": sum(passes.values()),
    }


def main() -> int:
    t0 = time.time()
    run_dir = Path(".experiments") / "nf_runs" / EXPERIMENT_NAME
    run_dir.mkdir(parents=True, exist_ok=True)
    cache = DataCache(cache_dir=run_dir / "cache")
    fetcher = DataFetcher(cache=cache)
    raw = fetcher.fetch_yahoo(UNIVERSE, start=DATA_START, end=DATA_END)
    if not isinstance(raw, dict):
        raise RuntimeError(f"fetch_yahoo returned {type(raw)}, expected dict")

    def _close(df):
        c = df.get("adj_close") if "adj_close" in df.columns else df.get("close")
        if c is None:
            c = df.get("Close")
        if c is None:
            raise KeyError(f"no close column: {df.columns.tolist()}")
        return c.astype(float)

    prices = pd.DataFrame({sym: _close(df) for sym, df in raw.items()}).sort_index()
    prices = prices.ffill().dropna(how="all")
    if prices.index.tz is not None:
        prices.index = prices.index.tz_localize(None)

    train_mask, val_mask, test_mask = _splits(prices)
    oos_mask = val_mask | test_mask

    bench_pos = pd.DataFrame(1.0, index=prices.index, columns=UNIVERSE)
    bench_result = run_backtest(prices, bench_pos, make_equity_config())

    events = fetch_earnings_events(UNIVERSE)
    pos = build_pead_targets(prices, events)
    res = run_backtest(prices, pos, make_equity_config())
    gate = full_gate_eval(res, oos_mask, val_mask, test_mask, prices, bench_result)

    # Perturbation: hold window +/-20% and position weight +/-20%.
    pert_rows = []
    for hd in sorted({max(1, int(round(HOLD_DAYS * m))) for m in [0.8, 1.2]}):
        p = build_pead_targets(prices, events, hold_days=hd)
        r = run_backtest(prices, p, make_equity_config())
        pm = _period_metrics(r.returns[oos_mask].dropna(), _count_in(r.trades, oos_mask, prices))
        pert_rows.append({"hold_days": hd, **pm})
    for wm in [0.8, 1.2]:
        pw = MAX_POS / max(1, len(UNIVERSE)) * wm
        p = build_pead_targets(prices, events, per_event_weight=pw)
        r = run_backtest(prices, p, make_equity_config())
        pm = _period_metrics(r.returns[oos_mask].dropna(), _count_in(r.trades, oos_mask, prices))
        pert_rows.append({"per_event_weight": round(pw, 4), **pm})
    opt_sr = gate["oos_metrics"]["sharpe"]
    pert_sharpes = [r["sharpe"] for r in pert_rows]
    min_ratio = (min(pert_sharpes) / opt_sr) if (opt_sr > 0 and pert_sharpes) else 0.0
    gate["passes"]["perturbation"] = min_ratio >= GATES["min_perturbed_sharpe_ratio"]
    gate["gate_pass_count"] = sum(gate["passes"].values())
    gate["perturbation"] = {"rows": pert_rows, "min_sharpe_ratio": min_ratio}

    rng = np.random.default_rng(SEED)
    active = (res.positions.abs().sum(axis=1) > 0).astype(float)
    rand_side = pd.Series(
        rng.choice([0.0, 1.0], size=len(prices), p=[0.5, 0.5]), index=prices.index
    )
    rand_pos = pd.DataFrame({UNIVERSE[0]: active * rand_side}, index=prices.index)
    # Matched random exposure across universe: random sign per active symbol-day.
    rand_pos = pd.DataFrame(0.0, index=prices.index, columns=UNIVERSE, dtype=float)
    for sym in UNIVERSE:
        rand_pos[sym] = active * rng.choice([0.0, 1.0], size=len(prices), p=[0.5, 0.5])
    rand_res = run_backtest(prices, rand_pos, make_equity_config())
    rand_m = _period_metrics(
        rand_res.returns[oos_mask].dropna(), _count_in(rand_res.trades, oos_mask, prices)
    )
    bench_m = _period_metrics(
        bench_result.returns[oos_mask].dropna(),
        _count_in(bench_result.trades, oos_mask, prices),
    )
    gate["ablations"] = {
        "random_exposure_matched": rand_m,
        "equal_weight_buy_hold_universe": bench_m,
    }

    # Inverse-signal falsifier: flip the surprise sign.
    inv_pos = build_pead_targets(prices, events, hold_days=HOLD_DAYS)
    inv_pos = -inv_pos
    inv_res = run_backtest(prices, inv_pos, make_equity_config())
    inv_m = _period_metrics(
        inv_res.returns[oos_mask].dropna(), _count_in(inv_res.trades, oos_mask, prices)
    )
    gate["ablations"]["inverse_surprise_sign"] = inv_m

    verdict = "PASS" if gate["gate_pass_count"] == len(gate["passes"]) else "REJECT"
    summary = {
        "experiment": EXPERIMENT_NAME,
        "hypothesis": "H98/NF-20261105-19 PEAD cross-sectional long/short",
        "seed": SEED,
        "data": {
            "start": DATA_START,
            "end": DATA_END,
            "symbols": UNIVERSE,
            "note": "free yfinance earnings data covers ~2020 onward; the 2015-2019 "
            "train window carries no earnings events or positions",
            "rows": int(len(prices)),
            "symbols_with_earnings": sorted(events.keys()),
        },
        "splits": {
            "train_end": TRAIN_END,
            "val_end": VAL_END,
            "note": "pre-registered Train 2015-2019 / Val 2020-2022 / Test 2023-2026; "
            "train window carries no earnings events (data starts ~2020)",
        },
        "hold_days": HOLD_DAYS,
        "max_pos": MAX_POS,
        "n_symbols": len(UNIVERSE),
        "n_events_total": int(sum(len(ev) for ev in events.values())),
        "gate_eval_oos_val_test": gate,
        "verdict": verdict,
        "duration_seconds": round(time.time() - t0, 3),
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")

    tracker = get_tracker()
    exp_id = tracker.start_experiment(
        name=EXPERIMENT_NAME,
        description=EXPERIMENT_DESC,
        config={
            "universe": UNIVERSE,
            "hold_days": HOLD_DAYS,
            "max_pos": MAX_POS,
            "initial_capital": INITIAL_CAPITAL,
            "data_start": DATA_START,
            "data_end": DATA_END,
            "train_end": TRAIN_END,
            "val_end": VAL_END,
            "seed": SEED,
        },
        data_sources=[f"yfinance:{s}" for s in UNIVERSE] + ["yfinance:earnings_dates"],
        compute_budget="<=2 CPU-h (expected << 1 min)",
        random_seeds=[SEED],
    )
    tracker.log_metrics(
        {
            "oos_sharpe": gate["oos_metrics"]["sharpe"],
            "oos_profit_factor": gate["oos_metrics"]["profit_factor"],
            "oos_max_drawdown": gate["oos_metrics"]["max_drawdown"],
            "oos_trades": float(gate["oos_metrics"]["trades"]),
            "gate_pass_count": float(gate["gate_pass_count"]),
        }
    )
    tracker.log_artifact("summary", run_dir / "summary.json")
    tracker.finish_experiment(status="completed")
    print(
        json.dumps(
            {"exp_id": exp_id, "verdict": verdict, "summary": str(run_dir / "summary.json")},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
