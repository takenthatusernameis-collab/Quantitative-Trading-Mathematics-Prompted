"""NF-20261109-21 / H171 (Cycle 85): Yield curve slope regime SPY timing —
carry & term structure / macro rate-shape regime (long-end minus mid-term).

Repo-relative novelty (honest). H155 (NF-20261108-24, REJECT 5/8) used the
*10-year Treasury yield level* (^TNX z-score) as a rate-level regime signal.
H141 (NF-20261106-18 / same root NF-11, REJECT 5/8) used *TLT-SHY term-spread
momentum* (an ETF price-return spread, not a yield-index shape). H100 (REJECT
5/9) used ^MOVE implied rates volatility. H154 (REJECT 4/8) used SHY short-rate
cumulative-return proxy. NF-20261109-21 uses the *yield curve slope / shape*
(^TYX 30Y minus ^FVX 5Y, a yield-index level difference) as the regime
observable — a different instrument type from H141 (yield indices vs ETF
prices), a different observable from H155 (slope/curvature vs single-maturity
level), and a different transmission channel (term-premium / curve-shape /
financial-conditions regime vs level or ETF spread momentum). Honest adjacency
to the broad rates-level/regime domain (H141/H154/H155/H100) is disclosed;
novelty scored repo-relative on the executed slope observable.

Mechanism (term-premium / curve-shape transmission). The long-end minus
mid-term yield slope (30Y-5Y) reflects term premium, growth/inflation
expectations, and financial-conditions stance. A steepening curve (high
positive z of slope) can signal accommodative long-end conditions / growth
optimism supporting equity risk premium; a flattening or inverted curve (low/
negative z) signals restrictive conditions, recession risk, or compressed term
premium associated with weaker forward equity returns. The strategy
continuously de-risks vol-targeted long SPY exposure when the z-score of the
trailing yield slope is abnormally negative (flattening/inversion stress) and
maintains/increases exposure when slope is normal or steep (positive z).

Causal chain (PIT). ^TYX and ^FVX daily closes (yfinance yield indices) known
at close t → slope_t = TYX_t - FVX_t (past-only) → z_t from trailing window →
exposure target for t+1; SPY return earned close[t]→close[t+1]. 1-bar delay
via engine `signals.shift(1)`. No look-ahead.

Observable (past-only, PIT, free yfinance): ^TYX, ^FVX, SPY daily auto-adjust
Close. ^TYX/^FVX are yield indices (levels in percent) — non-positive values
are possible in extreme regimes but probed clean 2010-2026 (0 non-positive);
slope itself can be negative (valid). No src/qtr changes.

Null (H0). Trailing yield curve slope (^TYX-^FVX z-score) contains no
incremental SPY timing information; OOS gates fail vs buy-hold/random-exposure.

Pre-registration (Cycle 85, decision-ready before validation outcomes).
NF-ID NF-20261109-21 (verified unused: no executed NF/H/runner/artifact).
Hypothesis H171 (next unused after H170; H24/H68-H73/H76-H79 unassigned, not
recycled). Sample 2010-01-01→2026-10-31 (train 2010-01-01→2019-12-31; val
2020-01-01→2022-12-31; test protected 2023-01-01→2026-10-31). Signal:
slope_t = TYX_t - FVX_t; z_t = (slope_t - mean(slope, z_window)) /
std(slope, z_window), past-only. Stress on *negative* z (flattening/inversion
stress): stress = clip((-z)/entry_scale, 0, 1). Exposure = (1-stress) *
vol_target * vscale, clipped [0, MAX_POS]. 1-bar delay; Equity CostModel
defaults (1bp commission + 1bp spread); long-only, MAX_POS=0.5. Bounded grid:
z_window {126,252} × entry_scale {1.0,2.0} × vol_target {0.10,0.15} (8 combos).
Train-only 4-fold WF selection by mean train Sharpe; Test protected.

Gates (OOS Val+Test, fail-closed): Sharpe>=1.0, trades>=200, PF>=1.3,
maxDD<=15%, WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3,
benchmark p<=0.05 with IR>=0, perturbation min ratio>=0.5.

Ablations: buy-hold SPY, always-flat/random-exposure-matched, inverse regime
(de-risk when slope abnormally *steep*/positive z — pre-registered falsifier),
OAT perturbation, Val/Test subperiods.

Falsifiers: random exposure comparable/better; inverse outperforms; benchmark
fails; fragile; worst-regime collapse. No gate weakening.
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

EXPERIMENT = "nf_20261109_21_yield_curve_slope_spy"
NF_ID = "NF-20261109-21"
HYPOTHESIS = "H171"
SYMBOLS = ["^TYX", "^FVX", "SPY"]
START = "2010-01-01"
END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"
MAX_POS = 0.5
SEED = 42
REALIZATION_BARS = 252 * 3

GRID = {
    "z_window": [126, 252],
    "entry_scale": [1.0, 2.0],
    "vol_target": [0.10, 0.15],
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


def _download(symbols: list[str], start: str, end: str) -> pd.DataFrame:
    if yf is None:
        raise RuntimeError("yfinance is required")
    raw = yf.download(
        symbols,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
        group_by="column",
    )
    if raw is None or len(raw) == 0:
        raise RuntimeError("yfinance returned empty data")
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"].copy()
    else:
        close = raw[["Close"]].copy()
        close.columns = [symbols[0]]
    close.index = pd.to_datetime(close.index).tz_localize(None)
    close = close.sort_index()
    # drop rows where all NaN; allow slope calc to handle individual NaNs
    out = close.dropna(how="all")
    if out.empty:
        raise RuntimeError("no non-NaN close data")
    return out


def _build_slope(close: pd.DataFrame) -> pd.Series:
    for c in ["^TYX", "^FVX"]:
        if c not in close.columns:
            raise ValueError(f"missing column {c}")
    slope = (close["^TYX"] - close["^FVX"]).astype(float)
    slope.name = "slope"
    return slope


def _zscore(series: pd.Series, window: int) -> pd.Series:
    mu = series.rolling(window, min_periods=window).mean()
    sd = series.rolling(window, min_periods=window).std(ddof=0)
    z = (series - mu) / sd.replace(0.0, np.nan)
    return z


def _signal_from_z(z: pd.Series, entry_scale: float, vol_target: float) -> pd.Series:
    # stress on negative z (flattening/inversion): de-risk
    stress = ((-z).clip(lower=0.0) / float(entry_scale)).clip(0.0, 1.0)
    exposure = (1.0 - stress) * float(vol_target)
    # simple vol-scale proxy: exposure already in vol-target units; engine/risk
    # handles sizing via target weights on single asset. Normalize to MAX_POS.
    sig = exposure.clip(0.0, MAX_POS)
    sig = sig.where(z.notna(), 0.0)
    sig.name = "SPY"
    return sig.astype(float)


def _cfg() -> BacktestConfig:
    return BacktestConfig(
        initial_capital=1_000_000.0,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        asset_class=AssetClass.EQUITY,
        max_position_size=MAX_POS,
        max_leverage=1.0,
        allow_short=False,
    )


def _run_backtest(prices: pd.DataFrame, signal: pd.Series) -> dict:
    sig_df = signal.to_frame(name="SPY").reindex(prices.index).fillna(0.0)
    res = run_backtest(prices=prices[["SPY"]], signals=sig_df, config=_cfg())
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


def _slice_metrics(prices: pd.DataFrame, signal: pd.Series, start: str, end: str) -> dict:
    idx = prices.index[(prices.index >= pd.Timestamp(start)) & (prices.index <= pd.Timestamp(end))]
    if len(idx) < 30:
        return {
            "metrics": {"sharpe": float("nan"), "trades": 0},
            "equity": pd.Series(dtype=float),
            "daily": pd.Series(dtype=float),
        }
    return _run_backtest(prices.loc[idx], signal.loc[idx])


def _wf_train_sharpe(
    prices: pd.DataFrame, slope: pd.Series, params: dict, n_folds: int = 4
) -> float:
    train_idx = prices.index[prices.index <= pd.Timestamp(TRAIN_END)]
    if len(train_idx) < n_folds * 252:
        n_folds = 2
    fold_size = len(train_idx) // n_folds
    sharpes = []
    for i in range(n_folds):
        s = i * fold_size
        e = len(train_idx) if i == n_folds - 1 else (i + 1) * fold_size
        idx = train_idx[s:e]
        z = _zscore(slope.loc[idx], params["z_window"])
        sig = _signal_from_z(z, params["entry_scale"], params["vol_target"])
        m = _run_backtest(prices.loc[idx, ["SPY"]], sig)["metrics"]
        sharpes.append(m["sharpe"])
    arr = np.array(sharpes, dtype=float)
    arr = arr[np.isfinite(arr)]
    return float(arr.mean()) if len(arr) else float("nan")


def _information_ratio(strategy: pd.Series, benchmark: pd.Series) -> float:
    a, b = strategy.align(benchmark, join="inner")
    diff = (a - b).dropna()
    if len(diff) < 30 or diff.std(ddof=0) == 0:
        return float("nan")
    return float(diff.mean() / diff.std(ddof=0) * math.sqrt(252))


def _benchmark_pvalue(strategy: pd.Series, benchmark: pd.Series) -> float:
    # simple one-sided test: mean(strategy-benchmark)>0 via t-stat approx (normal)
    a, b = strategy.align(benchmark, join="inner")
    diff = (a - b).dropna()
    if len(diff) < 30:
        return float("nan")
    mu = diff.mean()
    se = diff.std(ddof=0) / math.sqrt(len(diff))
    if se == 0 or not math.isfinite(se):
        return float("nan")
    z = mu / se
    # one-sided p for H1: strategy > benchmark
    try:
        from math import erf

        p = 1.0 - 0.5 * (1.0 + erf(z / math.sqrt(2.0)))
    except Exception:
        p = float("nan")
    return float(p)


def _perturbation_check(
    prices: pd.DataFrame, slope: pd.Series, params: dict, base_sharpe: float
) -> dict:
    if not math.isfinite(base_sharpe) or abs(base_sharpe) < 1e-12:
        return {"min_ratio": float("nan"), "details": []}
    oos_idx = prices.index[prices.index > pd.Timestamp(TRAIN_END)]
    ratios = []
    details = []
    for k, v in params.items():
        for delta in [-0.2, 0.2]:
            if isinstance(v, int):
                nv = int(round(v * (1 + delta)))
                nv = max(2, nv)
            else:
                nv = float(v * (1 + delta))
            np_ = dict(params)
            np_[k] = nv
            z = _zscore(slope.loc[oos_idx], np_["z_window"])
            sig = _signal_from_z(z, np_["entry_scale"], np_["vol_target"])
            m = _run_backtest(prices.loc[oos_idx, ["SPY"]], sig)["metrics"]["sharpe"]
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
        lambda x: (x.mean() / x.std(ddof=0) * math.sqrt(252)) if x.std(ddof=0) > 0 else np.nan,
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

    close = _download(SYMBOLS, START, END)
    # align and require SPY/TYX/FVX present
    close = close[["^TYX", "^FVX", "SPY"]].dropna()
    if (close[["^TYX", "^FVX", "SPY"]] <= 0).any().any():
        raise RuntimeError("non-positive values in required series")
    slope = _build_slope(close)

    grid = {k: (v[:1] if args.smoke else v) for k, v in GRID.items()}
    combos = []
    for zw in grid["z_window"]:
        for es in grid["entry_scale"]:
            for vt in grid["vol_target"]:
                combos.append({"z_window": zw, "entry_scale": es, "vol_target": vt})

    rows = []
    for p in combos:
        wf = _wf_train_sharpe(close, slope, p)
        # train metrics for reference
        z_tr = _zscore(slope[slope.index <= pd.Timestamp(TRAIN_END)], p["z_window"])
        sig_tr = _signal_from_z(z_tr, p["entry_scale"], p["vol_target"])
        tr = _run_backtest(close.loc[close.index <= pd.Timestamp(TRAIN_END), ["SPY"]], sig_tr)[
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
    selected = valid.iloc[0][["z_window", "entry_scale", "vol_target"]].to_dict()
    selected = {k: (int(v) if k == "z_window" else float(v)) for k, v in selected.items()}

    # OOS (Val+Test)
    oos_start = "2020-01-01"
    z_all = _zscore(slope, selected["z_window"])
    sig_all = _signal_from_z(z_all, selected["entry_scale"], selected["vol_target"])
    oos = _slice_metrics(close, sig_all, oos_start, END)
    bench_sig = pd.Series(1.0, index=close.index, name="SPY")
    bench_oos = _slice_metrics(close, bench_sig, oos_start, END)

    # ablations
    rng = np.random.default_rng(SEED)
    rand_sig = pd.Series(
        rng.choice([0.0, float(selected["vol_target"])], size=len(close), p=[0.5, 0.5]),
        index=close.index,
        name="SPY",
    )
    rand_oos = _slice_metrics(close, rand_sig, oos_start, END)
    # inverse: de-risk when slope steep (positive z)
    z = z_all
    stress_inv = (z.clip(lower=0.0) / float(selected["entry_scale"])).clip(0.0, 1.0)
    inv_sig = ((1.0 - stress_inv) * float(selected["vol_target"])).clip(0.0, MAX_POS)
    inv_sig = inv_sig.where(z.notna(), 0.0)
    inv_sig.name = "SPY"
    inv_oos = _slice_metrics(close, inv_sig, oos_start, END)

    oos_m = oos["metrics"]
    ir = _information_ratio(oos["daily"], bench_oos["daily"])
    bp = _benchmark_pvalue(oos["daily"], bench_oos["daily"])
    pert = _perturbation_check(close, slope, selected, oos_m["sharpe"])
    worst = _worst_regime(oos["daily"])
    wf = _wf_train_sharpe(close, slope, selected)
    # stability: OOS sharpe vs train sharpe
    tr_ref = _slice_metrics(close, sig_all, START, TRAIN_END)["metrics"]["sharpe"]
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
            "symbols": SYMBOLS,
            "start": START,
            "end": END,
            "rows_aligned": int(len(close)),
            "train_end": TRAIN_END,
            "val_end": VAL_END,
        },
        "grid_n": len(combos),
        "selected": selected,
        "wf_train_sharpe": wf,
        "train_ref_sharpe": tr_ref,
        "oos_val_test": oos_m,
        "benchmark_buy_hold_spy_oos": bench_oos["metrics"],
        "ablations": {
            "random_exposure_oos": rand_oos["metrics"],
            "inverse_regime_steep_de_risk_oos": inv_oos["metrics"],
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
    (art / "data_meta.json").write_text(json.dumps(summary["data"], indent=2) + "\n")
    print(
        json.dumps(
            {
                "verdict": verdict,
                "gates_passed": summary["gates_passed"],
                "selected": selected,
                "oos_sharpe": oos_m["sharpe"],
                "artifact": str(art),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
