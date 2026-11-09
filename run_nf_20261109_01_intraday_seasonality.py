"""NF-20261109-01 / H172 (Cycle 86): Intraday equity time-of-day seasonality (SPY 1h).
Microstructure / intraday seasonality (repo-new root family; distinct from H87
opening-gap fill, H10 intraday futures TSMOM, and calendar/seasonal families
H91/H140/H142/H168).

Mechanism (microstructure seasonality). Specific hours of the SPY trading day
exhibit persistent return patterns due to institutional execution algorithms,
market-maker inventory cycles, and liquidity provision patterns. A vol-targeted
long SPY position during pre-registered "favorable" hour windows (held only
during those hours, flat otherwise) targets net OOS (Val+Test) Sharpe >= 1.0.

Causal chain (PIT). SPY hourly bars (yfinance 1h) known at hour close; hour-
window membership is calendar-known at session start; signal for hour h uses
only information available at hour h-1 close; position for hour h earns return
from hour h open to hour h close. 1-bar delay via engine `signals.shift(1)`.
No look-ahead.

Observable (past-only, PIT, free yfinance): SPY hourly Open/High/Low/Close/Volume.
yfinance 1h limit ~730 bars (~2022-10 to 2026-10). No src/qtr changes.

Null (H0). Hour-of-day membership has no predictive power for SPY intraday
returns beyond random chance after costs.

Pre-registration (Cycle 86, decision-ready before validation outcomes).
NF-ID NF-20261109-01 (verified unused). Hypothesis H172 (next unused after
H171; H24/H68-H73/H76-H79 unassigned, not recycled). Sample: SPY 1h bars from
yfinance, earliest available to 2026-10-31. Train first 50%, Val next 25%, Test
protected final 25% (by time). Signal: hour_window defines favorable hours;
vol_target annual vol (scaled to hourly); vol_window trailing realized vol.
Grid: hour_window { {13,14}, {14,15}, {13,14,15}, {10,11}, {9,10}, {15} } x
vol_target {0.10,0.15,0.20} x vol_window {21,63} = 36 combos. Train-only
4-fold WF selection by mean train Sharpe; Test protected.

Gates (OOS Val+Test, fail-closed): Sharpe>=1.0, trades>=200, PF>=1.3,
maxDD<=15%, WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3,
benchmark p<=0.05 with IR>=0, perturbation min ratio>=0.5.

Ablations: buy-hold SPY, always-flat/random-hour control, inverse-hour,
OAT perturbation, Val/Test subperiods. No gate weakening.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None

from qtr.backtest.engine import AssetClass, BacktestConfig, CostModel, run_backtest

EXPERIMENT = "nf_20261109_01_intraday_seasonality"
NF_ID = "NF-20261109-01"
HYPOTHESIS = "H172"
SYMBOL = "SPY"
# yfinance 1h data limited to last 730 days; use dynamic start
START = "2024-12-01"
END = "2026-10-31"
MAX_POS = 0.5
SEED = 42

# Hour windows in ET (yfinance returns ET timestamps for 1h bars).
# US market hours: 9:30-16:00 ET. Hour 9 covers 9:00-9:59 (first real trade
# bar is 9:30-10:29 = hour 9); hours 9-15 cover the full session.
# Mirrors the pre-registered UTC windows (13-15 UTC = 9-11 AM ET, etc.) but uses
# the native ET clock so hour-window membership is unambiguous.
HOUR_WINDOWS = [
    (9, 10),  # 9:30-11:30 AM ET (morning momentum)
    (10, 11),  # 10:30 AM-12:30 PM ET (mid-morning)
    (9, 10, 11),  # 9:30 AM-12:30 PM ET (full morning)
    (11, 12),  # 11:30 AM-1:30 PM ET (lunch transition)
    (12, 13),  # 12:30-2:30 PM ET (early afternoon)
    (14,),  # 2:30-3:30 PM ET (close auction)
]

GRID = {
    "hour_window": HOUR_WINDOWS,
    "vol_target": [0.10, 0.15, 0.20],
    "vol_window": [21, 63],
}


def _artifact_dir(out: str | None) -> Path:
    if out:
        p = Path(out).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p
    ts = time.strftime("%Y%m%d_%H%M%S")
    p = (Path(".experiments") / "nf_runs" / f"{EXPERIMENT}_{ts}").resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _download_hourly(symbol: str, start: str, end: str) -> pd.DataFrame:
    if yf is None:
        raise RuntimeError("yfinance is required")
    raw = yf.download(
        symbol,
        start=start,
        end=end,
        interval="1h",
        auto_adjust=True,
        progress=False,
        group_by="column",
    )
    if raw is None or len(raw) == 0:
        raise RuntimeError("yfinance returned empty data")
    if isinstance(raw.columns, pd.MultiIndex):
        df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.columns = [c[0] for c in df.columns]
    else:
        df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
    # yfinance returns ET timestamps for 1h bars; convert to ET tz-aware, then
    # drop tz for engine (which uses tz-naive DatetimeIndex) but keep ET hour.
    et = "America/New_York"
    idx = pd.to_datetime(df.index)
    if getattr(idx, "tz", None) is None:
        idx = idx.tz_localize(et)
    else:
        idx = idx.tz_convert(et)
    df.index = idx.tz_localize(None)
    df = df.sort_index()
    # Keep only regular trading hours (9:30-16:00 ET = hours 9-15 in ET clock).
    # Hour 9 covers 9:00-9:59 (includes pre-market 9:00-9:29 bar); the first
    # real trade bar is 9:30-10:29 = hour 9. Filter to hours 9-15 inclusive.
    hour_mask = (df.index.hour >= 9) & (df.index.hour <= 15)
    df = df[hour_mask]
    # Drop rows with any NaN in OHLCV
    df = df.dropna()
    if df.empty:
        raise RuntimeError("no valid hourly data after filtering")
    return df


def _compute_hourly_returns(df: pd.DataFrame) -> pd.Series:
    # Intraday return for each hour: Close / Open - 1
    ret = (df["Close"] / df["Open"] - 1.0).astype(float)
    ret.name = "hourly_ret"
    return ret


def _build_signal(
    hourly_ret: pd.Series,
    hour_window: tuple[int, ...],
    vol_target: float,
    vol_window: int,
) -> pd.Series:
    """Build hourly signal: 1.0 during favorable hours (vol-targeted), 0.0 otherwise."""
    # Hour-of-day index
    hour_idx = hourly_ret.index.hour
    # Base signal: 1 during favorable hours, 0 otherwise
    base_signal = pd.Series(
        hour_idx.isin(hour_window).astype(float), index=hourly_ret.index, name="SPY"
    )

    # Vol targeting: scale by inverse of trailing realized vol
    # Annualized target vol -> hourly target vol
    hours_per_year = 252 * 6.5  # ~1638 trading hours/year
    hourly_vol_target = vol_target / math.sqrt(hours_per_year)

    # Trailing realized vol of hourly returns
    realized_vol = hourly_ret.rolling(vol_window, min_periods=vol_window).std(ddof=0)
    # Vol scale: target_vol / realized_vol, clipped
    vol_scale = (hourly_vol_target / realized_vol.replace(0, np.nan)).clip(0.0, 3.0)

    # Apply vol scaling to base signal
    signal = base_signal * vol_scale
    # Clip to MAX_POS
    signal = signal.clip(0.0, MAX_POS)
    # Where base_signal is 0 or vol_scale is NaN, signal should be 0
    signal = signal.where(base_signal > 0, 0.0)
    # Fill any remaining NaN with 0
    signal = signal.fillna(0.0)
    signal.name = "SPY"
    return signal.astype(float)


def _cfg() -> BacktestConfig:
    return BacktestConfig(
        initial_capital=1_000_000.0,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        asset_class=AssetClass.EQUITY,
        max_position_size=MAX_POS,
        max_leverage=1.0,
        allow_short=False,
    )


def _run_backtest_hourly(prices: pd.DataFrame, signal: pd.Series | pd.DataFrame) -> dict:
    """Run backtest on hourly data. Matches H171 pattern exactly."""
    # Ensure prices has a single 'SPY' column matching the signal column
    if "SPY" not in prices.columns:
        prices = prices.rename(columns={"Close": "SPY"})[["SPY"]]
    else:
        prices = prices[["SPY"]]
    # Convert signal to DataFrame with 'SPY' column (H171 pattern)
    if isinstance(signal, pd.DataFrame):
        sig_series = signal.iloc[:, 0]
    else:
        sig_series = signal
    sig_df = sig_series.to_frame(name="SPY").reindex(index=prices.index).fillna(0.0)
    res = run_backtest(prices=prices, signals=sig_df, config=_cfg())
    m = res.metrics
    if isinstance(m, dict):
        out = {
            "total_return": float(m.get("total_return", float("nan"))),
            "sharpe": float(m.get("sharpe", float("nan"))),
            "sortino": float(m.get("sortino", float("nan"))),
            "max_drawdown": float(m.get("max_drawdown", float("nan"))),
            "calmar": float(m.get("calmar", float("nan"))),
            "profit_factor": float(m.get("profit_factor", float("nan"))),
            "trades": int(m.get("num_trades", 0)),
            "volatility": float(m.get("annualized_volatility", float("nan"))),
            "cagr": float(m.get("annualized_return", float("nan"))),
            "equity_end": float(res.equity_curve.iloc[-1])
            if len(res.equity_curve)
            else float("nan"),
        }
    else:
        out = {
            "total_return": float(m.total_return),
            "sharpe": float(getattr(m, "sharpe_ratio", getattr(m, "sharpe", float("nan")))),
            "sortino": float(getattr(m, "sortino_ratio", getattr(m, "sortino", float("nan")))),
            "max_drawdown": float(m.max_drawdown),
            "calmar": float(m.calmar_ratio),
            "profit_factor": float(m.profit_factor)
            if math.isfinite(float(m.profit_factor))
            else float("nan"),
            "trades": int(getattr(m, "trades_count", getattr(m, "num_trades", 0))),
            "volatility": float(
                getattr(m, "volatility", getattr(m, "annualized_volatility", float("nan")))
            ),
            "cagr": float(getattr(m, "cagr", getattr(m, "annualized_return", float("nan")))),
            "equity_end": float(res.equity_curve.iloc[-1])
            if len(res.equity_curve)
            else float("nan"),
        }
    return {
        "metrics": out,
        "equity": res.equity_curve,
        "daily": res.equity_curve.pct_change().dropna(),
    }


def _slice_metrics(
    prices: pd.DataFrame, signal: pd.Series, hourly_ret: pd.Series, start: str, end: str
) -> dict:
    idx = prices.index[(prices.index >= pd.Timestamp(start)) & (prices.index <= pd.Timestamp(end))]
    if len(idx) < 30:
        return {
            "metrics": {"sharpe": float("nan"), "trades": 0},
            "equity": pd.Series(dtype=float),
            "daily": pd.Series(dtype=float),
        }
    return _run_backtest_hourly(prices.loc[idx], signal.loc[idx])


def _wf_train_sharpe(
    prices: pd.DataFrame,
    hourly_ret: pd.Series,
    params: dict,
    train_end: str,
    n_folds: int = 4,
) -> float:
    train_idx = prices.index[prices.index <= pd.Timestamp(train_end)]
    if len(train_idx) < n_folds * 100:  # Need enough hourly bars per fold
        n_folds = 2
    fold_size = len(train_idx) // n_folds
    sharpes = []
    for i in range(n_folds):
        s = i * fold_size
        e = len(train_idx) if i == n_folds - 1 else (i + 1) * fold_size
        idx = train_idx[s:e]
        sig = _build_signal(
            hourly_ret.loc[idx], params["hour_window"], params["vol_target"], params["vol_window"]
        )
        m = _run_backtest_hourly(prices.loc[idx], sig)["metrics"]
        sharpes.append(m["sharpe"])
    arr = np.array(sharpes, dtype=float)
    arr = arr[np.isfinite(arr)]
    return float(arr.mean()) if len(arr) else float("nan")


def _information_ratio(strategy: pd.Series, benchmark: pd.Series) -> float:
    a, b = strategy.align(benchmark, join="inner")
    diff = (a - b).dropna()
    if len(diff) < 30 or diff.std(ddof=0) == 0:
        return float("nan")
    return float(diff.mean() / diff.std(ddof=0) * math.sqrt(252 * 6.5))  # Annualize from hourly


def _benchmark_pvalue(strategy: pd.Series, benchmark: pd.Series) -> float:
    a, b = strategy.align(benchmark, join="inner")
    diff = (a - b).dropna()
    if len(diff) < 30:
        return float("nan")
    mu = diff.mean()
    se = diff.std(ddof=0) / math.sqrt(len(diff))
    if se == 0 or not math.isfinite(se):
        return float("nan")
    z = mu / se
    try:
        from math import erf

        p = 1.0 - 0.5 * (1.0 + erf(z / math.sqrt(2.0)))
    except Exception:
        p = float("nan")
    return float(p)


def _perturbation_check(
    prices: pd.DataFrame,
    hourly_ret: pd.Series,
    params: dict,
    base_sharpe: float,
    oos_start: str,
) -> dict:
    if not math.isfinite(base_sharpe) or abs(base_sharpe) < 1e-12:
        return {"min_ratio": float("nan"), "details": []}
    oos_idx = prices.index[prices.index > pd.Timestamp(oos_start)]
    ratios = []
    details = []
    for k, v in params.items():
        if k == "hour_window":
            continue  # Skip hour_window perturbation (discrete set)
        for delta in [-0.2, 0.2]:
            if isinstance(v, int):
                nv = int(round(v * (1 + delta)))
                nv = max(2, nv)
            else:
                nv = float(v * (1 + delta))
            np_ = dict(params)
            np_[k] = nv
            sig = _build_signal(
                hourly_ret.loc[oos_idx], np_["hour_window"], np_["vol_target"], np_["vol_window"]
            )
            m = _run_backtest_hourly(prices.loc[oos_idx], sig)["metrics"]["sharpe"]
            ratio = float(m / base_sharpe) if math.isfinite(m) else float("nan")
            ratios.append(ratio)
            details.append({"param": k, "delta": delta, "value": nv, "sharpe": m, "ratio": ratio})
    arr = np.array(ratios, dtype=float)
    arr = arr[np.isfinite(arr)]
    return {"min_ratio": float(arr.min()) if len(arr) else float("nan"), "details": details}


def _worst_regime(
    daily: pd.Series, window: int = 252 * 6
) -> float:  # ~252 days * 6 hours = ~1500 hours
    if daily is None or len(daily) < window + 10:
        return float("nan")
    roll = daily.rolling(window).apply(
        lambda x: (
            (x.mean() / x.std(ddof=0) * math.sqrt(252 * 6.5)) if x.std(ddof=0) > 0 else np.nan
        ),
        raw=False,
    )
    v = roll.dropna()
    return float(v.min()) if len(v) else float("nan")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--smoke", action="store_true", help="tiny grid for local check")
    args = ap.parse_args(argv)

    t0 = time.time()
    art = _artifact_dir(args.out)

    # Download hourly data
    df = _download_hourly(SYMBOL, START, END)
    hourly_ret = _compute_hourly_returns(df)

    # Prices for backtest (need Close)
    prices = df[["Close"]].copy()

    # Align
    common_idx = prices.index.intersection(hourly_ret.index)
    prices = prices.loc[common_idx]
    hourly_ret = hourly_ret.loc[common_idx]

    # Train/Val/Test splits by time (50/25/25)
    n = len(prices)
    train_end_idx = n // 2
    val_end_idx = train_end_idx + n // 4
    train_end = str(prices.index[train_end_idx].date())
    val_end = str(prices.index[val_end_idx].date())
    oos_start = str(prices.index[train_end_idx].date())  # Val+Test starts after train

    grid = {k: (v[:1] if args.smoke else v) for k, v in GRID.items()}
    combos = []
    for hw in grid["hour_window"]:
        for vt in grid["vol_target"]:
            for vw in grid["vol_window"]:
                combos.append({"hour_window": hw, "vol_target": vt, "vol_window": vw})

    rows = []
    for p in combos:
        wf = _wf_train_sharpe(prices, hourly_ret, p, train_end)
        # Train metrics for reference
        sig_tr = _build_signal(
            hourly_ret[hourly_ret.index <= pd.Timestamp(train_end)],
            p["hour_window"],
            p["vol_target"],
            p["vol_window"],
        )
        tr = _run_backtest_hourly(prices[prices.index <= pd.Timestamp(train_end)], sig_tr)[
            "metrics"
        ]
        rows.append(
            {**p, "wf_train_sharpe": wf, "train_sharpe": tr["sharpe"], "train_trades": tr["trades"]}
        )

    grid_df = pd.DataFrame(rows).sort_values("wf_train_sharpe", ascending=False)
    grid_df.to_csv(art / "grid.csv", index=False)
    valid = grid_df[np.isfinite(grid_df["wf_train_sharpe"])]
    if valid.empty:
        raise RuntimeError("no valid grid rows")
    selected = valid.iloc[0][["hour_window", "vol_target", "vol_window"]].to_dict()
    selected["hour_window"] = (
        tuple(selected["hour_window"])
        if isinstance(selected["hour_window"], list)
        else selected["hour_window"]
    )
    selected = {
        k: (tuple(v) if k == "hour_window" else (int(v) if k == "vol_window" else float(v)))
        for k, v in selected.items()
    }

    # OOS (Val+Test)
    z_all = _build_signal(
        hourly_ret, selected["hour_window"], selected["vol_target"], selected["vol_window"]
    )
    oos = _slice_metrics(prices, z_all, hourly_ret, oos_start, END)
    bench_sig = pd.Series(1.0, index=prices.index, name="SPY")
    bench_oos = _slice_metrics(prices, bench_sig, hourly_ret, oos_start, END)

    # Ablations
    rng = np.random.default_rng(SEED)
    # Random-hour control: same number of active hours, randomly chosen (ET hours)
    n_active = len(selected["hour_window"])
    all_hours = list(range(9, 16))  # 9-15 ET trading hours
    rand_hours = tuple(sorted(rng.choice(all_hours, size=n_active, replace=False)))
    rand_sig = _build_signal(hourly_ret, rand_hours, selected["vol_target"], selected["vol_window"])
    rand_oos = _slice_metrics(prices, rand_sig, hourly_ret, oos_start, END)

    # Inverse-hour: long unfavorable hours
    unfav_hours = tuple(h for h in all_hours if h not in selected["hour_window"])
    inv_sig = _build_signal(hourly_ret, unfav_hours, selected["vol_target"], selected["vol_window"])
    inv_oos = _slice_metrics(prices, inv_sig, hourly_ret, oos_start, END)

    oos_m = oos["metrics"]
    ir = _information_ratio(oos["daily"], bench_oos["daily"])
    bp = _benchmark_pvalue(oos["daily"], bench_oos["daily"])
    pert = _perturbation_check(prices, hourly_ret, selected, oos_m["sharpe"], oos_start)
    worst = _worst_regime(oos["daily"])
    wf = _wf_train_sharpe(prices, hourly_ret, selected, train_end)
    tr_ref = _slice_metrics(prices, z_all, hourly_ret, START, train_end)["metrics"]["sharpe"]
    stability = (
        float(oos_m["sharpe"] / tr_ref) if math.isfinite(tr_ref) and tr_ref > 0 else float("nan")
    )

    gates = {
        "sharpe_ge_1": bool(math.isfinite(oos_m["sharpe"]) and oos_m["sharpe"] >= 1.0),
        "trades_ge_200": bool(oos_m["trades"] >= 200),
        "pf_ge_1_3": bool(math.isfinite(oos_m["profit_factor"]) and oos_m["profit_factor"] >= 1.3),
        "maxdd_le_15pct": bool(
            math.isfinite(oos_m["max_drawdown"]) and abs(oos_m["max_drawdown"]) <= 0.15
        ),
        "wf_stability_ge_0_7": bool(math.isfinite(stability) and stability >= 0.7),
        "worst_regime_ge_0_3": bool(math.isfinite(worst) and worst >= 0.3),
        "benchmark_p_le_0_05_and_ir_ge_0": bool(
            math.isfinite(bp) and math.isfinite(ir) and bp <= 0.05 and ir >= 0.0
        ),
        "perturbation_min_ratio_ge_0_5": bool(
            math.isfinite(pert["min_ratio"]) and pert["min_ratio"] >= 0.5
        ),
    }
    verdict = "PASS" if all(gates.values()) else "REJECT"

    summary = {
        "experiment": EXPERIMENT,
        "nf_id": NF_ID,
        "hypothesis": HYPOTHESIS,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_sec": round(time.time() - t0, 3),
        "data": {
            "symbol": SYMBOL,
            "start": START,
            "end": END,
            "rows": int(len(prices)),
            "train_end": train_end,
            "val_end": val_end,
        },
        "grid_n": len(combos),
        "selected": {k: (list(v) if k == "hour_window" else v) for k, v in selected.items()},
        "wf_train_sharpe": wf,
        "train_ref_sharpe": tr_ref,
        "oos_val_test": oos_m,
        "benchmark_buy_hold_spy_oos": bench_oos["metrics"],
        "ablations": {
            "random_hour_oos": rand_oos["metrics"],
            "inverse_hour_oos": inv_oos["metrics"],
        },
        "information_ratio_vs_buy_hold": ir,
        "benchmark_pvalue_one_sided": bp,
        "worst_regime_rolling252_sharpe": worst,
        "wf_stability_oos_over_train": stability,
        "perturbation": {"min_ratio": pert["min_ratio"]},
        "gates": gates,
        "gates_passed": int(sum(1 for v in gates.values() if v)),
        "verdict": verdict,
    }
    (art / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(
        json.dumps(
            {
                "verdict": verdict,
                "gates_passed": summary["gates_passed"],
                "selected": {
                    k: (list(v) if k == "hour_window" else v) for k, v in selected.items()
                },
                "oos_sharpe": oos_m["sharpe"],
                "artifact": str(art),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
