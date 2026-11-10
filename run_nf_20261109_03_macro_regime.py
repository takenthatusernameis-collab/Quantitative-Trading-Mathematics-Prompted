"""NF-20261109-03 / H175 (Cycle 89): Cross-Asset Macro Regime Timing (Growth/Inflation Proxies -> SPY).
Macro factor regime (repo-new root family; distinct from yield-level H154/H155/H171,
yield-curve-slope H171/H11r, ERP H173, credit H94/H108, USD H95, realized-correlation H96,
rates-vol H100, copper-gold single-ratio H101, and all directional/vol/dispersion/calendar
families tested in H1-H174).

Mechanism (composite macro regime). Market-based growth (copper/gold HG=F/GC=F ratio:
industrial demand vs safe haven) and inflation-expectations (TIPS vs nominal Treasuries
TIP/IEF ratio = breakeven inflation proxy) proxies define a macro regime for SPY exposure.
A favorable regime (strong growth relative to safe haven, contained inflation expectations)
supports the equity risk premium -> vol-targeted long SPY; an unfavorable regime -> flat.

Causal chain (PIT). HG=F, GC=F, TIP, IEF, SPY closes are known at daily close t. Growth and
inflation proxies and their trailing z-scores are computed from past-only data at close t;
the regime score classifies the position for t+1 (engine `signals.shift(1)`). No look-ahead.

Observable (past-only, PIT, free yfinance). SPY daily Close (traded); HG=F, GC=F,
TIP, IEF daily Close (signals). Daily frequency; no src/qtr changes.

Null (H0). The composite growth/inflation macro regime has no predictive power for
next-period SPY returns beyond random chance after costs.

Pre-registration (Cycle 89, decision-ready before validation outcomes).
NF-ID NF-20261109-03 (deferred candidate in Cycles 86-88, never executed). Hypothesis H175
(next unused after H174; H24/H68-H73/H76-H79 unassigned, not recycled). Sample: SPY + HG=F,
GC=F, TIP, IEF yfinance daily 2010-01-01 -> 2026-10-31. Train first 50%, Val next 25%, Test
protected final 25% (by time). Signal: regime = z(log(HG=F/GC=F), L) - z(log(TIP/IEF), L);
regime >= entry_z => long SPY vol-targeted, regime <= exit_z => flat, hysteresis between.
Grid: lookback {63,126,252} x entry_z {0.5,1.0,1.5} x exit_z {0.0,0.5} x vol_target
{0.10,0.15} = 36 combos. Train-only 4-fold WF selection; Test protected.

Gates (OOS Val+Test, fail-closed): Sharpe>=1.0, trades>=200, PF>=1.3, maxDD<=15%,
WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3, benchmark p<=0.05 with IR>=0,
perturbation min ratio>=0.5.

Ablations: buy-hold SPY benchmark; random-regime control; inverse-regime (direction
falsifier); OAT perturbation (+/-20% on lookback, entry_z, exit_z, vol_target);
Val/Test subperiods; worst-regime rolling-252 Sharpe. No gate weakening.
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

EXPERIMENT = "nf_20261109_03_macro_regime"
NF_ID = "NF-20261109-03"
HYPOTHESIS = "H175"
START = "2010-01-01"
END = "2026-10-31"
MAX_POS = 0.5
SEED = 42
DAYS_PER_YEAR = 252
VOL_WINDOW = 21  # Fixed realized-vol window for vol targeting (not a grid param).

# Bounded grid (pre-registered).
GRID = {
    "lookback": [63, 126, 252],
    "entry_z": [0.5, 1.0, 1.5],
    "exit_z": [0.0, 0.5],
    "vol_target": [0.10, 0.15],
}

SYMBOLS = ["SPY", "HG=F", "GC=F", "TIP", "IEF"]


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
        df = raw.xs("Close", level=0, axis=1)
        if symbol in df.columns:
            df = df[[symbol]].rename(columns={symbol: "Close"})
        else:
            df = df.iloc[:, [0]].rename(columns={df.columns[0]: "Close"})
    else:
        df = raw[["Close"]].copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    df = df.dropna()
    if df.empty:
        raise RuntimeError(f"no valid daily data for {symbol}")
    return df


def _build_regime_signal(
    hg: pd.Series,
    gc: pd.Series,
    tip: pd.Series,
    ief: pd.Series,
    spy_ret: pd.Series,
    lookback: int,
    entry_z: float,
    exit_z: float,
    vol_target: float,
    vol_window: int,
) -> pd.Series:
    """Build daily SPY signal from the composite macro regime score."""
    growth = np.log(hg / gc).rename("growth")
    inflation = np.log(tip / ief).rename("inflation")

    # Trailing rolling z-scores (past-only, min_periods=lookback).
    g_mean = growth.rolling(lookback, min_periods=lookback).mean()
    g_std = growth.rolling(lookback, min_periods=lookback).std(ddof=0)
    i_mean = inflation.rolling(lookback, min_periods=lookback).mean()
    i_std = inflation.rolling(lookback, min_periods=lookback).std(ddof=0)
    g_z = (growth - g_mean) / g_std.replace(0, np.nan)
    i_z = (inflation - i_mean) / i_std.replace(0, np.nan)
    regime = g_z.fillna(0.0) - i_z.fillna(0.0)

    # Hysteresis state machine:
    # - regime >= entry_z -> long SPY (favorable macro regime)
    # - regime <= exit_z -> flat (unfavorable macro regime)
    # - between thresholds -> hold prior state
    signal = pd.Series(0.0, index=regime.index, dtype=float)
    state = 0  # 0=flat, 1=long

    for i in range(len(regime)):
        r = regime.iloc[i] if math.isfinite(regime.iloc[i]) else 0.0
        if state == 0:
            if r >= entry_z:
                state = 1
        elif state == 1:
            if r <= exit_z:
                state = 0
        signal.iloc[i] = float(state)

    # Vol targeting off trailing SPY realized vol.
    daily_vol_target = vol_target / math.sqrt(DAYS_PER_YEAR)
    realized_vol = spy_ret.rolling(vol_window, min_periods=vol_window).std(ddof=0)
    vol_scale = (daily_vol_target / realized_vol.replace(0, np.nan)).clip(0.0, 3.0)

    signal = signal * vol_scale
    signal = signal.clip(0.0, MAX_POS)
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
    hg: pd.Series,
    gc: pd.Series,
    tip: pd.Series,
    ief: pd.Series,
    spy_ret: pd.Series,
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
        for delta in [-0.2, 0.2]:
            if isinstance(v, int) or (isinstance(v, float) and v.is_integer()):
                nv = int(round(v * (1 + delta)))
                nv = max(2, nv)
            else:
                nv = float(v * (1 + delta))
            np_ = dict(params)
            np_[k] = nv
            sig = _build_regime_signal(
                hg,
                gc,
                tip,
                ief,
                spy_ret,
                int(np_["lookback"]),
                float(np_["entry_z"]),
                float(np_["exit_z"]),
                float(np_["vol_target"]),
                VOL_WINDOW,
            )
            sig_df = pd.DataFrame({"SPY": sig}).reindex(index=prices.loc[oos_idx].index).fillna(0.0)
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


def _wf_train_sharpe_simple(
    prices: pd.DataFrame, signal: pd.DataFrame, train_end: str, n_folds: int = 4
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
        sig_df = signal.loc[idx].reindex(index=prices.loc[idx].index).fillna(0.0)
        m = _run_backtest_daily(prices.loc[idx], sig_df)["metrics"]
        sharpes.append(m["sharpe"])
    arr = np.array(sharpes, dtype=float)
    arr = arr[np.isfinite(arr)]
    return float(arr.mean()) if len(arr) else float("nan")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--smoke", action="store_true", help="tiny grid for local check")
    args = ap.parse_args(argv)

    t0 = time.time()
    art = _artifact_dir(args.out)

    # Download daily price data.
    price_data = {}
    for sym in SYMBOLS:
        price_data[sym] = _download_daily(sym, START, END)

    # Align on common index.
    common_idx = price_data[SYMBOLS[0]].index
    for sym in SYMBOLS[1:]:
        common_idx = common_idx.intersection(price_data[sym].index)
    for sym in SYMBOLS:
        price_data[sym] = price_data[sym].loc[common_idx]

    prices = pd.DataFrame({sym: price_data[sym]["Close"] for sym in SYMBOLS}, index=common_idx)
    prices = prices.dropna()

    hg = prices["HG=F"]
    gc = prices["GC=F"]
    tip = prices["TIP"]
    ief = prices["IEF"]
    spy = prices["SPY"]
    returns = prices.pct_change().fillna(0.0)
    spy_ret = returns["SPY"]

    # Grid.
    grid = {k: (v[:1] if args.smoke else v) for k, v in GRID.items()}
    combos = []
    for lb in grid["lookback"]:
        for ez in grid["entry_z"]:
            for exz in grid["exit_z"]:
                for vt in grid["vol_target"]:
                    combos.append(
                        {
                            "lookback": lb,
                            "entry_z": ez,
                            "exit_z": exz,
                            "vol_target": vt,
                        }
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
        sig = _build_regime_signal(
            hg,
            gc,
            tip,
            ief,
            spy_ret,
            int(p["lookback"]),
            float(p["entry_z"]),
            float(p["exit_z"]),
            float(p["vol_target"]),
            VOL_WINDOW,
        )
        sig_df = pd.DataFrame({"SPY": sig}).reindex(index=prices.index).fillna(0.0)

        # WF train Sharpe.
        wf = _wf_train_sharpe_simple(prices, sig_df, train_end)

        # Train metrics.
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
    sig = _build_regime_signal(
        hg,
        gc,
        tip,
        ief,
        spy_ret,
        int(selected["lookback"]),
        float(selected["entry_z"]),
        float(selected["exit_z"]),
        float(selected["vol_target"]),
        VOL_WINDOW,
    )
    sig_df = pd.DataFrame({"SPY": sig}).reindex(index=prices.index).fillna(0.0)

    # OOS (Val+Test).
    oos = _slice_metrics(prices, sig_df, oos_start, END)

    # Benchmark: buy-hold SPY.
    bench_sig = pd.DataFrame({"SPY": 1.0}, index=prices.index)
    bench_oos = _slice_metrics(prices, bench_sig, oos_start, END)

    # Ablations.
    rng = np.random.default_rng(SEED)
    oos_mask = prices.index > pd.Timestamp(oos_start)
    n_active = int((sig_df.loc[oos_mask].abs().sum(axis=1) > 0).sum())
    all_days = prices.index[oos_mask]
    if n_active > 0 and len(all_days) > 0:
        rand_days = rng.choice(all_days, size=min(n_active, len(all_days)), replace=False)
        rand_sym_sig = pd.Series(0.0, index=prices.index)
        rand_sym_sig.loc[rand_days] = 1.0
        realized_vol = spy_ret.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std(ddof=0)
        daily_vol_target = float(selected["vol_target"]) / math.sqrt(DAYS_PER_YEAR)
        vol_scale = (daily_vol_target / realized_vol.replace(0, np.nan)).clip(0.0, 3.0)
        rand_sym_sig = rand_sym_sig * vol_scale
        rand_sym_sig = rand_sym_sig.clip(0.0, MAX_POS).fillna(0.0)
        rand_sig = pd.DataFrame({"SPY": rand_sym_sig})
        rand_oos = _slice_metrics(prices, rand_sig, oos_start, END)
    else:
        rand_oos = {
            "metrics": {
                "sharpe": float("nan"),
                "trades": 0,
                "profit_factor": float("nan"),
                "max_drawdown": float("nan"),
            }
        }

    # Inverse-regime: flat when favorable, long when unfavorable (direction falsifier).
    growth = np.log(hg / gc)
    inflation = np.log(tip / ief)
    g_z = (
        growth
        - growth.rolling(int(selected["lookback"]), min_periods=int(selected["lookback"])).mean()
    ) / (
        growth.rolling(int(selected["lookback"]), min_periods=int(selected["lookback"]))
        .std(ddof=0)
        .replace(0, np.nan)
    )
    i_z = (
        inflation
        - inflation.rolling(int(selected["lookback"]), min_periods=int(selected["lookback"])).mean()
    ) / (
        inflation.rolling(int(selected["lookback"]), min_periods=int(selected["lookback"]))
        .std(ddof=0)
        .replace(0, np.nan)
    )
    regime = g_z.fillna(0.0) - i_z.fillna(0.0)
    entry_z = float(selected["entry_z"])
    exit_z = float(selected["exit_z"])
    inv_signal = pd.Series(0.0, index=regime.index, dtype=float)
    state = 0
    for i in range(len(regime)):
        r = regime.iloc[i] if math.isfinite(regime.iloc[i]) else 0.0
        if state == 0:
            if r <= exit_z:
                state = 1
        elif state == 1:
            if r >= entry_z:
                state = 0
        inv_signal.iloc[i] = float(state)
    daily_vol_target = float(selected["vol_target"]) / math.sqrt(DAYS_PER_YEAR)
    realized_vol = spy_ret.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std(ddof=0)
    vol_scale = (daily_vol_target / realized_vol.replace(0, np.nan)).clip(0.0, 3.0)
    inv_signal = inv_signal * vol_scale
    inv_signal = inv_signal.clip(0.0, MAX_POS).fillna(0.0)
    inv_sig_df = pd.DataFrame({"SPY": inv_signal})
    inv_oos = _slice_metrics(prices, inv_sig_df, oos_start, END)

    oos_m = oos["metrics"]
    ir = _information_ratio(oos["daily"], bench_oos["daily"])
    bp = _benchmark_pvalue(oos["daily"], bench_oos["daily"])
    pert = _perturbation_check(
        prices, hg, gc, tip, ief, spy_ret, dict(selected), oos_m["sharpe"], oos_start
    )
    worst = _worst_regime(oos["daily"])
    wf = _wf_train_sharpe_simple(prices, sig_df, train_end)
    tr_ref = _slice_metrics(prices, sig_df, START, train_end)["metrics"]["sharpe"]
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
            "symbols": ["SPY"],
            "signal_symbols": ["HG=F", "GC=F", "TIP", "IEF"],
            "start": START,
            "end": END,
            "rows": int(len(prices)),
            "train_end": train_end,
            "val_end": val_end,
            "nav_source": "n/a",
        },
        "grid_n": len(combos),
        "selected": {
            k: (int(v) if k == "lookback" else float(v))
            for k, v in selected.items()
            if k in ("lookback", "entry_z", "exit_z", "vol_target")
        },
        "wf_train_sharpe": wf,
        "train_ref_sharpe": tr_ref,
        "oos_val_test": oos_m,
        "benchmark_buy_hold_oos": bench_oos["metrics"],
        "ablations": {
            "random_regime_oos": rand_oos["metrics"],
            "inverse_regime_oos": inv_oos["metrics"],
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


if __name__ == "__main__":
    raise SystemExit(main())
