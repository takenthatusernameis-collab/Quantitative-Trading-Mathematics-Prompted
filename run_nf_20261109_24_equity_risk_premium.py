"""NF-20261109-24 / H173 (Cycle 87): Equity Risk Premium / Fed Model SPY timing.
Valuation / equity risk premium transmission (repo-new root family; distinct from
H154 short-rate level, H155 10Y yield level, H171 yield-curve slope — all
bond-yield-only families; H173 uses the equity-minus-bond yield spread).

Mechanism (valuation / ERP). The SPY trailing dividend yield minus the 10Y
Treasury yield is the classic "Fed model" equity risk premium. When the spread
is wide (equities cheap vs bonds) expected SPY returns are elevated; when it
narrows or inverts (equities expensive) expected returns are depressed. A
vol-targeted long SPY position scaled by the z-score of the trailing spread
targets net OOS (Val+Test) Sharpe >= 1.0.

Causal chain (PIT). SPY dividends are historical actuals whose ex-dates are
known at close t; ^TNX close is known at close t; trailing dividend yield and
ERP are computed from past-only data; position at close t earns return t->t+1
via engine `signals.shift(1)`. No look-ahead.

Observable (past-only, PIT, free yfinance): SPY daily Close + dividends;
^TNX daily Close. Daily frequency; no src/qtr changes.

Null (H0). The equity-minus-bond yield spread has no predictive power for
next-day SPY returns beyond random chance after costs.

Pre-registration (Cycle 87, decision-ready before validation outcomes).
NF-ID NF-20261109-24 (verified unused). Hypothesis H173 (next unused after
H172; H24/H68-H73/H76-H79 unassigned, not recycled). Sample: SPY + ^TNX +
SPY dividends yfinance daily 2010-01-01 -> 2026-10-31. Train first 50%, Val
next 25%, Test protected final 25% (by time). Signal: ERP z-score >= entry_z
=> vol-targeted long SPY, else flat. Grid: div_lookback {126,252} x
z_window {126,252} x entry_z {0.0,0.5,1.0} x vol_target {0.10,0.15,0.20} =
36 combos. Train-only 4-fold WF selection by mean train Sharpe; Test protected.

Gates (OOS Val+Test, fail-closed): Sharpe>=1.0, trades>=200, PF>=1.3,
maxDD<=15%, WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3,
benchmark p<=0.05 with IR>=0, perturbation min ratio>=0.5.

Ablations: buy-hold SPY, always-flat/random-regime control, inverse-signal,
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

EXPERIMENT = "nf_20261109_24_equity_risk_premium"
NF_ID = "NF-20261109-24"
HYPOTHESIS = "H173"
SPY_SYMBOL = "SPY"
TNX_SYMBOL = "^TNX"
START = "2010-01-01"
END = "2026-10-31"
MAX_POS = 0.5
SEED = 42
DAYS_PER_YEAR = 252
VOL_WINDOW = 63  # Fixed realized-vol window for vol targeting (not a grid param).

# Bounded grid (pre-registered).
GRID = {
    "div_lookback": [126, 252],
    "z_window": [126, 252],
    "entry_z": [0.0, 0.5, 1.0],
    "vol_target": [0.10, 0.15, 0.20],
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


def _download_daily(symbol: str, start: str, end: str) -> pd.DataFrame:
    if yf is None:
        raise RuntimeError("yfinance is required")
    raw = yf.download(
        symbol,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=True,
        progress=False,
        group_by="column",
    )
    if raw is None or len(raw) == 0:
        raise RuntimeError(f"yfinance returned empty data for {symbol}")
    if isinstance(raw.columns, pd.MultiIndex):
        df = raw[["Close"]].copy()
        df.columns = ["Close"]
    else:
        df = raw[["Close"]].copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    df = df.dropna()
    if df.empty:
        raise RuntimeError(f"no valid daily data for {symbol}")
    return df


def _download_dividends(symbol: str, start: str, end: str) -> pd.Series:
    if yf is None:
        raise RuntimeError("yfinance is required")
    tk = yf.Ticker(symbol)
    div = tk.dividends
    if div is None or len(div) == 0:
        raise RuntimeError(f"yfinance returned no dividends for {symbol}")
    div = div.rename("dividend")
    div.index = pd.to_datetime(div.index)
    # yfinance dividends are tz-aware; normalize to tz-naive daily dates to align
    # with the price index. Dividends are historical actuals (PIT-safe).
    if getattr(div.index, "tz", None) is not None:
        div.index = div.index.tz_convert("UTC").tz_localize(None)
    div.index = div.index.normalize()
    div = div.sort_index()
    div = div[(div.index >= pd.Timestamp(start)) & (div.index <= pd.Timestamp(end))]
    return div


def _compute_trailing_div_yield(
    prices: pd.DataFrame, dividends: pd.Series, lookback: int
) -> pd.Series:
    """Trailing dividend yield = sum of dividends over trailing lookback days / Close."""
    # Align dividends to the daily price index (0 where no dividend ex-date).
    daily_div = dividends.reindex(prices.index).fillna(0.0)
    trailing_div = daily_div.rolling(lookback, min_periods=lookback).sum()
    div_yield = trailing_div / prices["Close"]
    div_yield.name = "div_yield"
    return div_yield


def _compute_erp(div_yield: pd.Series, tnx_close: pd.Series) -> pd.Series:
    """Equity risk premium = dividend yield - TNX/100 (TNX in percent)."""
    tnx = tnx_close.reindex(div_yield.index)
    erp = div_yield - (tnx / 100.0)
    erp.name = "erp"
    return erp


def _build_signal(
    erp: pd.Series,
    spy_ret: pd.Series,
    div_lookback: int,
    z_window: int,
    entry_z: float,
    vol_target: float,
    vol_window: int,
) -> pd.Series:
    """Build daily signal: vol-targeted long SPY when ERP z >= entry_z, else 0."""
    # ERP z-score (past-only).
    erp_mean = erp.rolling(z_window, min_periods=z_window).mean()
    erp_std = erp.rolling(z_window, min_periods=z_window).std(ddof=0)
    erp_z = (erp - erp_mean) / erp_std.replace(0, np.nan)

    # Base signal: 1 when ERP z >= entry_z (equities cheap vs bonds), else 0.
    base_signal = (erp_z >= entry_z).astype(float)

    # Vol targeting: scale by inverse of trailing realized vol.
    daily_vol_target = vol_target / math.sqrt(DAYS_PER_YEAR)
    realized_vol = spy_ret.rolling(vol_window, min_periods=vol_window).std(ddof=0)
    vol_scale = (daily_vol_target / realized_vol.replace(0, np.nan)).clip(0.0, 3.0)

    signal = base_signal * vol_scale
    signal = signal.clip(0.0, MAX_POS)
    signal = signal.where(base_signal > 0, 0.0)
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


def _run_backtest_daily(prices: pd.DataFrame, signal: pd.DataFrame) -> dict:
    res = run_backtest(prices=prices, signals=signal, config=_cfg())
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


def _slice_metrics(prices: pd.DataFrame, signal: pd.DataFrame, start: str, end: str) -> dict:
    idx = prices.index[(prices.index >= pd.Timestamp(start)) & (prices.index <= pd.Timestamp(end))]
    if len(idx) < 30:
        return {
            "metrics": {"sharpe": float("nan"), "trades": 0},
            "equity": pd.Series(dtype=float),
            "daily": pd.Series(dtype=float),
        }
    return _run_backtest_daily(prices.loc[idx], signal.loc[idx])


def _information_ratio(strategy: pd.Series, benchmark: pd.Series) -> float:
    a, b = strategy.align(benchmark, join="inner")
    diff = (a - b).dropna()
    if len(diff) < 30 or diff.std(ddof=0) == 0:
        return float("nan")
    return float(diff.mean() / diff.std(ddof=0) * math.sqrt(DAYS_PER_YEAR))


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
    signal_df: pd.DataFrame,
    params: dict,
    base_sharpe: float,
    oos_start: str,
) -> dict:
    if not math.isfinite(base_sharpe) or abs(base_sharpe) < 1e-12:
        return {"min_ratio": float("nan"), "details": []}
    oos_idx = prices.index[prices.index > pd.Timestamp(oos_start)]
    ratios = []
    details = []
    numeric_params = {k: v for k, v in params.items() if k != "hour_window"}
    for k, v in numeric_params.items():
        for delta in [-0.2, 0.2]:
            if isinstance(v, int):
                nv = int(round(v * (1 + delta)))
                nv = max(2, nv)
            else:
                nv = float(v * (1 + delta))
            np_ = dict(params)
            np_[k] = nv
            # Rebuild signal with perturbed params using precomputed erp/spy_ret columns.
            sig = _build_signal(
                signal_df["erp"],
                signal_df["spy_ret"],
                np_["div_lookback"],
                np_["z_window"],
                np_["entry_z"],
                np_["vol_target"],
                np_["vol_window"],
            )
            sig_df = sig.to_frame(name="SPY").reindex(index=prices.loc[oos_idx].index).fillna(0.0)
            m = _run_backtest_daily(prices.loc[oos_idx], sig_df)["metrics"]["sharpe"]
            ratio = float(m / base_sharpe) if math.isfinite(m) else float("nan")
            ratios.append(ratio)
            details.append({"param": k, "delta": delta, "value": nv, "sharpe": m, "ratio": ratio})
    arr = np.array(ratios, dtype=float)
    arr = arr[np.isfinite(arr)]
    return {"min_ratio": float(arr.min()) if len(arr) else float("nan"), "details": details}


def _worst_regime(daily: pd.Series, window: int = 252) -> float:
    if daily is None or len(daily) < window + 10:
        return float("nan")
    roll = daily.rolling(window).apply(
        lambda x: (
            (x.mean() / x.std(ddof=0) * math.sqrt(DAYS_PER_YEAR)) if x.std(ddof=0) > 0 else np.nan
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

    # Download daily data.
    spy = _download_daily(SPY_SYMBOL, START, END)
    tnx = _download_daily(TNX_SYMBOL, START, END)
    dividends = _download_dividends(SPY_SYMBOL, START, END)

    # Align on common index.
    common_idx = spy.index.intersection(tnx.index)
    spy = spy.loc[common_idx]
    tnx = tnx.loc[common_idx]
    prices = spy[["Close"]].copy()

    # SPY daily returns.
    spy_ret = (prices["Close"] / prices["Close"].shift(1) - 1.0).fillna(0.0)
    spy_ret.name = "spy_ret"

    # Precompute erp for each grid combo depends on div_lookback/z_window, so build per combo.
    grid = {k: (v[:1] if args.smoke else v) for k, v in GRID.items()}
    combos = []
    for dl in grid["div_lookback"]:
        for zw in grid["z_window"]:
            for ez in grid["entry_z"]:
                for vt in grid["vol_target"]:
                    combos.append(
                        {"div_lookback": dl, "z_window": zw, "entry_z": ez, "vol_target": vt}
                    )

    # Train/Val/Test splits by time (50/25/25).
    n = len(prices)
    train_end_idx = n // 2
    val_end_idx = train_end_idx + n // 4
    train_end = str(prices.index[train_end_idx].date())
    val_end = str(prices.index[val_end_idx].date())
    oos_start = str(prices.index[train_end_idx].date())

    rows = []
    for p in combos:
        # Recompute div yield / erp / erp_z for this combo's div_lookback/z_window.
        div_yield = _compute_trailing_div_yield(prices, dividends, p["div_lookback"])
        erp = _compute_erp(div_yield, tnx["Close"])
        sig_full = _build_signal(
            erp,
            spy_ret,
            p["div_lookback"],
            p["z_window"],
            p["entry_z"],
            p["vol_target"],
            p["vol_window"],
        )
        # WF train Sharpe over expanding folds.
        train_idx = prices.index[prices.index <= pd.Timestamp(train_end)]
        sig_train = sig_full.loc[sig_full.index <= pd.Timestamp(train_end)]
        wf = _wf_train_sharpe_simple(prices, sig_train, train_end)
        sig_df = sig_full.to_frame(name="SPY").reindex(index=prices.index).fillna(0.0)
        tr = _run_backtest_daily(
            prices[prices.index <= pd.Timestamp(train_end)],
            sig_df.loc[prices.index <= pd.Timestamp(train_end)],
        )["metrics"]
        rows.append(
            {**p, "wf_train_sharpe": wf, "train_sharpe": tr["sharpe"], "train_trades": tr["trades"]}
        )

    grid_df = pd.DataFrame(rows).sort_values("wf_train_sharpe", ascending=False)
    grid_df.to_csv(art / "grid.csv", index=False)
    valid = grid_df[np.isfinite(grid_df["wf_train_sharpe"])]
    if valid.empty:
        raise RuntimeError("no valid grid rows")
    selected = valid.iloc[0].to_dict()

    # Rebuild selected signal on full sample.
    div_yield = _compute_trailing_div_yield(prices, dividends, int(selected["div_lookback"]))
    erp = _compute_erp(div_yield, tnx["Close"])
    sig_full = _build_signal(
        erp,
        spy_ret,
        int(selected["div_lookback"]),
        int(selected["z_window"]),
        float(selected["entry_z"]),
        float(selected["vol_target"]),
        int(selected["vol_window"]),
    )
    sig_df = sig_full.to_frame(name="SPY").reindex(index=prices.index).fillna(0.0)
    # Attach erp/spy_ret for perturbation reuse.
    sig_df["erp"] = erp
    sig_df["spy_ret"] = spy_ret

    # OOS (Val+Test).
    oos = _slice_metrics(prices, sig_df[["SPY"]], oos_start, END)
    bench_sig = pd.Series(1.0, index=prices.index, name="SPY")
    bench_df = bench_sig.to_frame(name="SPY").reindex(index=prices.index).fillna(1.0)
    bench_oos = _slice_metrics(prices, bench_df, oos_start, END)

    # Ablations.
    rng = np.random.default_rng(SEED)
    # Random-regime control: same number of active days, randomly chosen.
    n_active = int((sig_full[sig_full.index > pd.Timestamp(oos_start)] > 0).sum())
    all_days = sig_full.index[sig_full.index > pd.Timestamp(oos_start)]
    rand_days = rng.choice(all_days, size=min(n_active, len(all_days)), replace=False)
    rand_sig = pd.Series(0.0, index=prices.index, name="SPY")
    rand_sig.loc[rand_days] = 1.0
    # Apply vol targeting to random regime using selected vol params.
    rand_sig = _apply_vol_target(
        rand_sig, spy_ret, float(selected["vol_target"]), int(selected["vol_window"])
    )
    rand_oos = _slice_metrics(prices, rand_sig.to_frame(name="SPY"), oos_start, END)

    # Inverse-signal: flat when ERP z high, long when ERP z low (direction falsifier).
    div_yield = _compute_trailing_div_yield(prices, dividends, int(selected["div_lookback"]))
    erp = _compute_erp(div_yield, tnx["Close"])
    erp_mean = erp.rolling(int(selected["z_window"]), min_periods=int(selected["z_window"])).mean()
    erp_std = erp.rolling(int(selected["z_window"]), min_periods=int(selected["z_window"])).std(
        ddof=0
    )
    erp_z = (erp - erp_mean) / erp_std.replace(0, np.nan)
    inv_base = (erp_z < float(selected["entry_z"])).astype(float)
    inv_sig = inv_base * 1.0
    inv_sig = _apply_vol_target(
        inv_sig, spy_ret, float(selected["vol_target"]), int(selected["vol_window"])
    )
    inv_sig = inv_sig.clip(0.0, MAX_POS).fillna(0.0)
    inv_oos = _slice_metrics(prices, inv_sig.to_frame(name="SPY"), oos_start, END)

    oos_m = oos["metrics"]
    ir = _information_ratio(oos["daily"], bench_oos["daily"])
    bp = _benchmark_pvalue(oos["daily"], bench_oos["daily"])
    pert = _perturbation_check(prices, sig_df, dict(selected), oos_m["sharpe"], oos_start)
    worst = _worst_regime(oos["daily"])
    wf = _wf_train_sharpe_simple(prices, sig_full, train_end)
    tr_ref = _slice_metrics(prices, sig_df[["SPY"]], START, train_end)["metrics"]["sharpe"]
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
            "spy_symbol": SPY_SYMBOL,
            "tnx_symbol": TNX_SYMBOL,
            "start": START,
            "end": END,
            "rows": int(len(prices)),
            "train_end": train_end,
            "val_end": val_end,
        },
        "grid_n": len(combos),
        "selected": {
            k: (int(v) if k in ("div_lookback", "z_window", "vol_window") else float(v))
            for k, v in selected.items()
            if k in ("div_lookback", "z_window", "entry_z", "vol_target")
        },
        "wf_train_sharpe": wf,
        "train_ref_sharpe": tr_ref,
        "oos_val_test": oos_m,
        "benchmark_buy_hold_spy_oos": bench_oos["metrics"],
        "ablations": {
            "random_regime_oos": rand_oos["metrics"],
            "inverse_signal_oos": inv_oos["metrics"],
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
                "selected": summary["selected"],
                "oos_sharpe": oos_m["sharpe"],
                "artifact": str(art),
            },
            indent=2,
        )
    )
    return 0


def _wf_train_sharpe_simple(
    prices: pd.DataFrame, signal: pd.Series, train_end: str, n_folds: int = 4
) -> float:
    train_idx = prices.index[prices.index <= pd.Timestamp(train_end)]
    if len(train_idx) < n_folds * 30:
        n_folds = 2
    fold_size = len(train_idx) // n_folds
    sharpes = []
    for i in range(n_folds):
        s = i * fold_size
        e = len(train_idx) if i == n_folds - 1 else (i + 1) * fold_size
        idx = train_idx[s:e]
        sig_df = (
            signal.loc[idx].to_frame(name="SPY").reindex(index=prices.loc[idx].index).fillna(0.0)
        )
        m = _run_backtest_daily(prices.loc[idx], sig_df)["metrics"]
        sharpes.append(m["sharpe"])
    arr = np.array(sharpes, dtype=float)
    arr = arr[np.isfinite(arr)]
    return float(arr.mean()) if len(arr) else float("nan")


def _apply_vol_target(
    base_signal: pd.Series, spy_ret: pd.Series, vol_target: float, vol_window: int
) -> pd.Series:
    daily_vol_target = vol_target / math.sqrt(DAYS_PER_YEAR)
    realized_vol = spy_ret.rolling(vol_window, min_periods=vol_window).std(ddof=0)
    vol_scale = (daily_vol_target / realized_vol.replace(0, np.nan)).clip(0.0, 3.0)
    signal = base_signal * vol_scale
    signal = signal.clip(0.0, MAX_POS)
    signal = signal.where(base_signal > 0, 0.0)
    signal = signal.fillna(0.0)
    signal.name = "SPY"
    return signal.astype(float)


if __name__ == "__main__":
    raise SystemExit(main())
