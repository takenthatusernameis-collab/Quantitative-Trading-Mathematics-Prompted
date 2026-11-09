"""NF-20261109-11 / H168 (Cycle 82): SPY timing from S&P 500 index rebalance
structural flow pressure (mandatory index-fund rebalancing at quarterly effective dates).

Repo-relative novelty (honest). H91 (turn-of-month REJECT 3/9), H140 (monthly OPX
REJECT 4/8), H142 (turn-of-quarter REJECT 4/8), H90 (FOMC REJECT 1/9) use
calendar-seasonal windows as anomalies. H168 uses *structural index-fund
rebalancing flow pressure* at the known S&P 500 quarterly effective dates
(third Friday of Mar/Jun/Sep/Dec) — a genuinely different mechanism: predictable
supply/demand imbalance from mandatory index-fund trading, not a seasonal
pattern. Deterministic public calendar, SPY free yfinance, quarterly low
turnover, clean falsifiers (random-window, inverse).

Mechanism (structural flows / index rebalance). S&P 500 index changes
(additions/deletions) are announced ~5 weeks before quarterly effective date
(third Friday of Mar/Jun/Sep/Dec). Index-tracking funds must trade to match new
weights, creating concentrated buying in additions and selling in deletions
around the effective date. This predictable flow pressure can distort prices.
The pre-registered rule de-risks SPY during the ex-ante rebalance window (last
`end_days` trading days of quarter + first `start_days` of next quarter) to
avoid adverse flow-driven price impact, and holds at full exposure otherwise.
Calendar known at close t; 1-bar delay via engine `signals.shift(1)` ensures
no look-ahead.

Observable (past-only, PIT, free yfinance): SPY daily auto-adjust Close.
S&P 500 quarterly effective dates computed from date alone (third Friday of
Mar/Jun/Sep/Dec); no external data dependency.

Null (H0). Index rebalance window membership has no predictive power for
next-day SPY returns beyond random chance after costs.

Pre-registration (Cycle 82, decision-ready before validation outcomes).
NF-ID NF-20261109-11 (verified unused: no executed NF/H/runner/artifact).
Hypothesis H168 (next unused after H167; H24/H68-H73/H76-H79 unassigned, not
recycled). Universe SPY (traded), yfinance daily auto-adjust Close (free, PIT).
Sample 2010-01-01->2026-10-31 (train 2010-01-01->2019-12-31, val
2020-01-01->2022-12-31, test 2023-01-01->2026-10-31 protected). Signal:
vol-targeted long SPY reduced during ex-ante rebalance window (end_days trading
days before quarter-end + start_days after quarter-start); 1-bar delay.
Equity CostModel defaults (1bp commission + 1bp spread); long-only, max
exposure scaled to MAX_POS=0.5. Bounded grid: end_days {1,2,3,4,5} x
start_days {1,2,3,4,5} x vol_target {0.10,0.15} (75 combos); train-only
4-fold WF selection by mean train Sharpe; Test protected. No src/qtr change.
All gates fail-closed on pre-registered OOS Val+Test.

Gates (OOS Val+Test): Sharpe>=1.0, trades>=200, PF>=1.3, maxDD<=15%,
WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3, benchmark p<=0.05
with IR>=0, perturbation min ratio>=0.5.

Ablations: buy-hold SPY, random-window control (same-frequency random
windows), always-flat, inverse window (more exposure in rebalance window),
OAT perturbation, Val/Test subperiods.

Falsifiers: random-window comparable or better; inverse outperforms;
benchmark fails; fragile; worst-regime collapse.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from qtr.backtest.engine import (  # noqa: E402
    AssetClass,
    BacktestConfig,
    CostModel,
    run_backtest,
)
from qtr.validation.statistics import sharpe_ratio  # noqa: E402

EXPERIMENT_DESC = (
    "NF-20261109-11/H168 (Cycle 82): SPY timing from S&P 500 index rebalance "
    "structural flow pressure. Vol-targeted long SPY reduced during ex-ante "
    "quarterly rebalance window. 1-bar delay. Train-only WF selection; Test "
    "protected; OOS Val+Test gates."
)

SPY = "SPY"
UNIVERSE = [SPY]
DATA_START = "2010-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"
SEED = 168
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5
WF_FOLDS_SELECTION = 4

END_DAYS = [1, 2, 3, 4, 5]
START_DAYS = [1, 2, 3, 4, 5]
VOL_TARGETS = [0.10, 0.15]


def _fetch() -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download(UNIVERSE, start=DATA_START, end=DATA_END, progress=False, auto_adjust=True)
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"][UNIVERSE]
    else:
        close = raw[UNIVERSE]
    df = close.dropna().sort_index()
    df = df[(df > 0).all(axis=1)]
    if df.empty:
        raise RuntimeError("empty price data")
    return df


def _splits(index: pd.DatetimeIndex):
    train = pd.Series(index <= pd.Timestamp(TRAIN_END), index=index)
    val = pd.Series(
        (index > pd.Timestamp(TRAIN_END)) & (index <= pd.Timestamp(VAL_END)), index=index
    )
    test = pd.Series(index > pd.Timestamp(VAL_END), index=index)
    return train, val, test


def _sp500_rebalance_dates(index: pd.DatetimeIndex) -> pd.Series:
    """Return boolean series marking days in the ex-ante rebalance window.

    S&P 500 quarterly effective dates are the third Friday of Mar, Jun, Sep, Dec.
    The rebalance window is: last `end_days` trading days of quarter + first
    `start_days` trading days of next quarter.
    """
    # Compute third Friday of Mar, Jun, Sep, Dec for each year in the index
    years = index.year.unique()
    rebalance_dates = []
    for year in years:
        for month in [3, 6, 9, 12]:
            # Find third Friday
            first_day = pd.Timestamp(year=year, month=month, day=1)
            # Day of week: Monday=0, Friday=4
            first_friday = first_day + pd.Timedelta(days=(4 - first_day.weekday()) % 7)
            third_friday = first_friday + pd.Timedelta(days=14)
            if third_friday in index:
                rebalance_dates.append(third_friday)

    rebalance_dates = sorted(set(rebalance_dates))

    # Mark window around each rebalance date
    in_window = pd.Series(False, index=index)
    for rb_date in rebalance_dates:
        # Find position in index
        pos = index.get_indexer([rb_date], method="nearest")[0]
        if pos >= 0:
            # We'll parameterize end_days and start_days in make_signals
            pass
    return pd.Series(False, index=index)  # Placeholder, actual logic in make_signals


def _is_in_rebalance_window(index: pd.DatetimeIndex, end_days: int, start_days: int) -> pd.Series:
    """Mark trading days in the ex-ante rebalance window around S&P 500 effective dates."""
    # Compute third Friday of Mar, Jun, Sep, Dec for each year
    years = index.year.unique()
    rebalance_dates = []
    for year in years:
        for month in [3, 6, 9, 12]:
            first_day = pd.Timestamp(year=year, month=month, day=1)
            first_friday = first_day + pd.Timedelta(days=(4 - first_day.weekday()) % 7)
            third_friday = first_friday + pd.Timedelta(days=14)
            if third_friday in index:
                rebalance_dates.append(third_friday)

    rebalance_dates = sorted(set(rebalance_dates))
    in_window = pd.Series(False, index=index)

    # For each rebalance date, mark the window
    for rb_date in rebalance_dates:
        try:
            pos = index.get_loc(rb_date)
        except KeyError:
            continue
        if pos >= 0:
            # end_days before (including the rebalance date itself as day 0)
            start_idx = max(0, pos - end_days + 1)
            # start_days after (starting from next trading day)
            end_idx = min(len(index) - 1, pos + start_days)
            in_window.iloc[start_idx : end_idx + 1] = True

    return in_window


def _vol_scale(prices: pd.DataFrame, vol_target: float) -> pd.Series:
    ret = prices[SPY].pct_change()
    rv = ret.rolling(21, min_periods=21).std(ddof=0) * np.sqrt(252.0)
    return (vol_target / rv.replace(0.0, np.nan)).clip(0.0, 1.0)


def make_signals(prices: pd.DataFrame, params: dict) -> pd.DataFrame:
    in_window = _is_in_rebalance_window(prices.index, params["end_days"], params["start_days"])
    # In window: reduce exposure; out of window: full exposure
    # Exposure = (1 - in_window) * vol_target * vscale
    vscale = _vol_scale(prices, params["vol_target"])
    w = ((~in_window).astype(float) * params["vol_target"] * vscale).clip(0.0, MAX_POS)
    sig = pd.DataFrame(0.0, index=prices.index, columns=UNIVERSE)
    sig[SPY] = w.fillna(0.0)
    return sig


def make_inverse_signals(prices: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Falsifier: MORE exposure in rebalance window (inverse logic)."""
    in_window = _is_in_rebalance_window(prices.index, params["end_days"], params["start_days"])
    vscale = _vol_scale(prices, params["vol_target"])
    # Inverse: full exposure in window, reduced out of window
    w = (in_window.astype(float) * params["vol_target"] * vscale).clip(0.0, MAX_POS)
    sig = pd.DataFrame(0.0, index=prices.index, columns=UNIVERSE)
    sig[SPY] = w.fillna(0.0)
    return sig


def make_always_flat(prices: pd.DataFrame) -> pd.DataFrame:
    """Falsifier: always flat (zero exposure)."""
    sig = pd.DataFrame(0.0, index=prices.index, columns=UNIVERSE)
    return sig


def _cfg() -> BacktestConfig:
    return BacktestConfig(
        asset_class=AssetClass.EQUITY,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        initial_capital=INITIAL_CAPITAL,
        max_position_size=MAX_POS,
    )


def _pf(returns: pd.Series) -> float:
    r = returns.dropna()
    gain = r[r > 0].sum()
    loss = -r[r < 0].sum()
    if loss <= 0:
        return float("inf") if gain > 0 else 0.0
    return float(gain / loss)


def _maxdd(equity: pd.Series) -> float:
    peak = equity.cummax()
    return float(((equity - peak) / peak).min())


def evaluate(prices: pd.DataFrame, signals: pd.DataFrame, mask: pd.Series) -> dict:
    p = prices.loc[mask]
    s = signals.loc[mask]
    if len(p) < 60 or s[SPY].abs().sum() < 1e-12:
        return {"sharpe": float("nan"), "profit_factor": 0.0, "max_drawdown": 0.0, "trades": 0}
    res = run_backtest(p, s, _cfg())
    eq = res.equity_curve
    ret = eq.pct_change().dropna()
    trades = res.trades
    ntr = 0
    if trades is not None and len(trades) > 0:
        if hasattr(trades, "empty") and not trades.empty:
            if "date" in trades.columns:
                ntr = int(pd.to_datetime(trades["date"]).isin(eq.index).sum())
            else:
                ntr = int(len(trades))
        elif not hasattr(trades, "empty"):
            ntr = int(len(trades))
    return {
        "sharpe": float(sharpe_ratio(ret)),
        "profit_factor": _pf(ret),
        "max_drawdown": _maxdd(eq),
        "trades": ntr,
    }


def benchmark_buy_hold(prices: pd.DataFrame, mask: pd.Series) -> dict:
    sig = pd.DataFrame(0.0, index=prices.index, columns=UNIVERSE)
    sig[SPY] = 1.0
    return evaluate(prices, sig, mask)


def _wf_selection_mean(prices: pd.DataFrame, train_mask: pd.Series, params: dict) -> float:
    train_idx = prices.index[train_mask]
    if len(train_idx) < WF_FOLDS_SELECTION * 252:
        ev = evaluate(prices, make_signals(prices, params), train_mask)
        return ev["sharpe"] if np.isfinite(ev["sharpe"]) else float("-inf")
    fold = len(train_idx) // WF_FOLDS_SELECTION
    sharpes = []
    for i in range(WF_FOLDS_SELECTION):
        end = (i + 1) * fold if i < WF_FOLDS_SELECTION - 1 else len(train_idx)
        idx = train_idx[:end]
        if len(idx) < 252:
            continue
        m = pd.Series(False, index=prices.index)
        m.loc[idx] = True
        ev = evaluate(prices, make_signals(prices, params), m)
        if np.isfinite(ev["sharpe"]):
            sharpes.append(ev["sharpe"])
    return float(np.mean(sharpes)) if sharpes else float("-inf")


def select_params(prices: pd.DataFrame, train_mask: pd.Series) -> tuple[dict, list[dict]]:
    rows = []
    for end_days in END_DAYS:
        for start_days in START_DAYS:
            for vol_target in VOL_TARGETS:
                params = {
                    "end_days": end_days,
                    "start_days": start_days,
                    "vol_target": vol_target,
                }
                wf = _wf_selection_mean(prices, train_mask, params)
                rows.append({**params, "wf_train_mean_sharpe": wf})
    rows.sort(key=lambda r: r["wf_train_mean_sharpe"], reverse=True)
    best = {k: rows[0][k] for k in ("end_days", "start_days", "vol_target")}
    return best, rows


def worst_regime_sharpe(returns: pd.Series, window: int = 252) -> float:
    r = returns.dropna()
    if len(r) < window:
        return float(sharpe_ratio(r))
    roll = r.rolling(window).apply(lambda x: float(sharpe_ratio(x)), raw=False)
    return float(roll.min())


def perturbation_ratio(prices: pd.DataFrame, oos_mask: pd.Series, best: dict) -> float:
    base = evaluate(prices, make_signals(prices, best), oos_mask)["sharpe"]
    if not np.isfinite(base) or abs(base) < 1e-12:
        return 0.0
    ratios = []
    for de, ds, dv in [
        (0.25, 0.0, 0.0),
        (-0.25, 0.0, 0.0),
        (0.0, 0.25, 0.0),
        (0.0, -0.25, 0.0),
        (0.0, 0.0, 0.02),
        (0.0, 0.0, -0.02),
    ]:
        p = {
            "end_days": int(np.clip(best["end_days"] + de, 1, 10)),
            "start_days": int(np.clip(best["start_days"] + ds, 1, 10)),
            "vol_target": float(np.clip(best["vol_target"] + dv, 0.05, 0.30)),
        }
        s = evaluate(prices, make_signals(prices, p), oos_mask)["sharpe"]
        if np.isfinite(s):
            ratios.append(s / base)
    return float(min(ratios)) if ratios else 0.0


def random_exposure(prices: pd.DataFrame, base_sig: pd.DataFrame, mask: pd.Series) -> dict:
    rng = np.random.default_rng(SEED)
    m = mask[mask].index
    vals = base_sig.loc[m, SPY].to_numpy().copy()
    rng.shuffle(vals)
    sig = base_sig.copy()
    sig.loc[m, SPY] = vals
    return evaluate(prices, sig, mask)


def random_window_control(prices: pd.DataFrame, params: dict, mask: pd.Series) -> dict:
    """Falsifier: same-frequency random windows (matched trade count)."""
    rng = np.random.default_rng(SEED)
    in_window = _is_in_rebalance_window(prices.index, params["end_days"], params["start_days"])
    n_window = int(in_window.sum())
    if n_window == 0:
        return {"sharpe": float("nan"), "profit_factor": 0.0, "max_drawdown": 0.0, "trades": 0}
    # Randomly select n_window days
    all_idx = prices.index[in_window | ~in_window]
    rand_idx = rng.choice(all_idx, size=n_window, replace=False)
    rand_window = pd.Series(False, index=prices.index)
    rand_window.loc[rand_idx] = True
    # Use the same signal construction but with random window
    vscale = _vol_scale(prices, params["vol_target"])
    w = ((~rand_window).astype(float) * params["vol_target"] * vscale).clip(0.0, MAX_POS)
    sig = pd.DataFrame(0.0, index=prices.index, columns=UNIVERSE)
    sig[SPY] = w.fillna(0.0)
    return evaluate(prices, sig, mask)


def _oos_returns(prices: pd.DataFrame, signals: pd.DataFrame, mask: pd.Series) -> pd.Series:
    res = run_backtest(prices.loc[mask], signals.loc[mask], _cfg())
    return res.equity_curve.pct_change().dropna()


def _benchmark_compare(strat_ret: pd.Series, bench_ret: pd.Series) -> tuple[float, float]:
    a = pd.concat([strat_ret.rename("s"), bench_ret.rename("b")], axis=1).dropna()
    if len(a) < 30:
        return 1.0, 0.0
    diff = a["s"] - a["b"]
    ir = float(diff.mean() / diff.std(ddof=0) * np.sqrt(252.0)) if diff.std(ddof=0) > 0 else 0.0
    rng = np.random.default_rng(SEED)
    obs = diff.mean()
    count = 0
    n = len(diff)
    vals = diff.to_numpy()
    for _ in range(2000):
        signs = rng.choice([-1.0, 1.0], size=n)
        if float((vals * signs).mean()) >= obs:
            count += 1
    p = (count + 1) / 2001
    return float(p), ir


def main() -> None:
    t0 = time.time()
    print(f"[{EXPERIMENT_DESC}]")
    prices = _fetch()
    train, val, test = _splits(prices.index)
    oos = val | test
    best, grid_rows = select_params(prices, train)
    sig = make_signals(prices, best)
    oos_ev = evaluate(prices, sig, oos)
    train_ev = evaluate(prices, sig, train)
    wf_stab = (
        float(oos_ev["sharpe"] / train_ev["sharpe"])
        if np.isfinite(train_ev["sharpe"]) and abs(train_ev["sharpe"]) > 1e-12
        else 0.0
    )
    strat_ret = _oos_returns(prices, sig, oos)
    bench_sig = pd.DataFrame(0.0, index=prices.index, columns=UNIVERSE)
    bench_sig[SPY] = 1.0
    bench_ret = _oos_returns(prices, bench_sig, oos)
    bench_p, ir = _benchmark_compare(strat_ret, bench_ret)
    pert = perturbation_ratio(prices, oos, best)
    oos_ev["wf_stability"] = wf_stab
    oos_ev["worst_regime_sharpe"] = worst_regime_sharpe(strat_ret)
    oos_ev["benchmark_p"] = bench_p
    oos_ev["information_ratio"] = ir
    oos_ev["perturbation_ratio"] = pert
    oos_ev["n"] = int(oos.sum())
    gates = {
        "sharpe_ge_1": oos_ev["sharpe"] >= 1.0,
        "trades_ge_200": oos_ev["trades"] >= 200,
        "pf_ge_1_3": oos_ev["profit_factor"] >= 1.3,
        "maxdd_le_15pct": oos_ev["max_drawdown"] >= -0.15,
        "wf_stability_ge_0_7": wf_stab >= 0.7,
        "worst_regime_ge_0_3": oos_ev["worst_regime_sharpe"] >= 0.3,
        "benchmark_p_le_0_05_ir_ge_0": bench_p <= 0.05 and ir >= 0.0,
        "perturbation_ge_0_5": pert >= 0.5,
    }
    pass_count = sum(1 for v in gates.values() if v)
    verdict = "PASS" if pass_count == 8 else "REJECT"
    out = {
        "nf_id": "NF-20261109-11",
        "h_id": "H168",
        "verdict": verdict,
        "gates": f"{pass_count}/8",
        "gate_detail": gates,
        "best": best,
        "train": train_ev,
        "oos": oos_ev,
        "ablations": {
            "buy_hold_spy": benchmark_buy_hold(prices, oos),
            "always_flat": evaluate(prices, make_always_flat(prices), oos),
            "random_exposure_matched": random_exposure(prices, sig, oos),
            "random_window_matched": random_window_control(prices, best, oos),
            "inverse_regime": evaluate(prices, make_inverse_signals(prices, best), oos),
        },
        "elapsed_s": round(time.time() - t0, 2),
    }
    out_dir = ROOT / ".experiments" / "nf_runs" / "nf_20261109_11_spy_index_rebalance"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(out, indent=2, default=str) + "\n")
    pd.DataFrame(grid_rows).to_csv(out_dir / "grid.csv", index=False)
    meta = {
        "nf_id": "NF-20261109-11",
        "h_id": "H168",
        "universe": UNIVERSE,
        "data_start": DATA_START,
        "data_end": DATA_END,
        "rows": int(len(prices)),
        "train_end": TRAIN_END,
        "val_end": VAL_END,
        "seed": SEED,
        "grid_n": len(grid_rows),
        "selection": "best train-only 4-fold WF mean Sharpe; gates on OOS Val+Test",
    }
    (out_dir / "data_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(
        json.dumps(
            {"verdict": verdict, "gates": out["gates"], "oos": oos_ev, "best": best},
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
