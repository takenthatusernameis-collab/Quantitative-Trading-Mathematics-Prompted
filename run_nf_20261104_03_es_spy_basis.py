"""NF-20261104-03 / H181 (Cycle 95): ES-SPY cash-futures basis mean-reversion timing.

Broad mechanism category: relative value / cash-futures basis convergence (index arbitrage).
Repo-new root family relative to executed H1-H180: all prior futures work (H1/H7-H12/H21-H23/H25)
tested directional TSMOM on futures; H180 tested ex-dividend microstructure; no executed H-ID
trades the ES=F-vs-SPY basis as a mean-reverting relative-value/convergence signal.

Mechanism. ES=F and SPY are linked by cost-of-carry/index-arbitrage. The basis
(ES/SPY - 1) mean-reverts when it deviates from rolling fair value because
arbitrage capital trades rich/cheap futures vs cash. A trailing z-score of the
basis gates vol-targeted SPY exposure as a minimal decisive test of the
convergence signal (long SPY when basis is rich/positive-z and expected to
compress toward SPY, flat/reduced when cheap/negative-z), using only free daily
closes.

Causal chain (PIT). ES=F and SPY daily closes known at close t -> basis/z from
past-only trailing window -> position for t->t+1 via engine signals.shift(1).
No same-bar or future information.

Null (H0). Trailing ES-SPY basis z-score has no predictive power for next-period
SPY returns beyond random chance after costs.

Pre-registration (Cycle 95, decision-ready before validation outcomes).
NF-ID NF-20261104-03 (repo-new execution; earlier register proposal, never
executed/pre-registered as H). Hypothesis H181 (next unused after H180;
H24/H68-H73/H76-H79 unassigned, not recycled). Sample 2010-01-04->2026-10-30
(common ES=F/SPY history). Train 2010-01-04->2018-12-31; Val 2019-01-01->
2022-12-31; Test protected 2023-01-01->2026-10-30. Selection train-only 4-fold
WF Sharpe. OOS gates on Val+Test only. Grid (bounded, 36): basis_window
{21,63,126} x entry_z {1.0,1.5,2.0} x exit_z {0.0,0.5} x vol_target {0.10,0.15}.
MAX_POS 0.5, Equity CostModel defaults (1bp+1bp), 1-bar delay, vol targeting
(VOL_WINDOW=21d).

Gates (OOS Val+Test, fail-closed): Sharpe>=1.0, trades>=50, PF>=1.3,
maxDD<=15%, WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3,
benchmark p<=0.05 with IR>=0, perturbation min ratio>=0.5.

Ablations/falsifiers: buy-hold SPY; random-signal control (same active count,
random dates, seed 42); inverse-basis signal; OAT perturbation (+/-20% bounded).
No gate weakening. Free/public yfinance only. src/qtr unchanged.
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

EXPERIMENT = "nf_20261104_03_es_spy_basis"
NF_ID = "NF-20261104-03"
HYPOTHESIS = "H181"
START = "2010-01-01"
END = "2026-10-31"
TRAIN_END = "2018-12-31"
VAL_END = "2022-12-31"
MAX_POS = 0.5
SEED = 42
DAYS_PER_YEAR = 252
VOL_WINDOW = 21

GRID = {
    "basis_window": [21, 63, 126],
    "entry_z": [1.0, 1.5, 2.0],
    "exit_z": [0.0, 0.5],
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


def _download_close(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    if yf is None:
        raise RuntimeError("yfinance is required")
    raw = yf.download(
        tickers,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    if raw is None or len(raw) == 0:
        raise RuntimeError("yfinance returned empty data")
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"].copy()
    else:
        col = "Close" if "Close" in raw.columns else raw.columns[0]
        close = raw[[col]].copy()
        close.columns = [tickers[0]]
    idx = pd.to_datetime(close.index)
    close.index = idx.tz_localize(None) if idx.tz is not None else idx
    close = close[~close.index.duplicated(keep="last")].sort_index()
    close = close[tickers].astype(float).dropna()
    if len(close) < 500:
        raise RuntimeError(f"insufficient aligned data: {len(close)}")
    if (close <= 0).any().any():
        raise RuntimeError("non-positive close prices found")
    return close


def _zscore(series: pd.Series, window: int) -> pd.Series:
    m = series.rolling(window, min_periods=window).mean()
    s = series.rolling(window, min_periods=window).std(ddof=0)
    return (series - m) / s.replace(0.0, np.nan)


def _compute_weights(
    prices: pd.DataFrame,
    basis_z: pd.Series,
    basis_window: int,
    entry_z: float,
    exit_z: float,
    vol_target: float,
) -> pd.DataFrame:
    # basis_window kept for grid identity; basis_z should be precomputed with it.
    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    z = basis_z.reindex(prices.index)
    w = pd.Series(0.0, index=prices.index, dtype=float)
    pos = 0.0
    for i in range(len(prices.index)):
        zv = z.iloc[i]
        if not np.isfinite(zv):
            w.iloc[i] = pos
            continue
        if pos == 0.0:
            if zv >= entry_z:
                pos = 1.0
            elif zv <= -entry_z:
                pos = 0.0
        else:  # pos == 1.0, long SPY when basis rich
            if zv <= exit_z:
                pos = 0.0
        w.iloc[i] = pos

    ret = prices["SPY"].pct_change()
    vol = ret.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std() * np.sqrt(DAYS_PER_YEAR)
    scale = (vol_target / vol.replace(0.0, np.nan)).clip(0.0, 3.0).fillna(0.0)
    w = (w * scale).clip(-MAX_POS, MAX_POS)
    weights["SPY"] = w
    if "ES=F" in weights.columns:
        weights["ES=F"] = 0.0
    return weights


def _run_bt(close: pd.DataFrame, weights: pd.DataFrame) -> tuple[pd.Series, pd.Series, int]:
    cfg = BacktestConfig(
        initial_capital=1_000_000.0,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        asset_class=AssetClass.EQUITY,
        max_position_size=MAX_POS,
        allow_short=False,
    )
    res = run_backtest(close[["SPY"]], weights[["SPY"]], cfg)
    strat_ret = res.returns.reindex(close.index).fillna(0.0).astype(float)
    eq = res.equity_curve.reindex(close.index).astype(float)
    pos = res.positions.reindex(close.index).fillna(0.0)
    trades = int((pos.diff().abs() > 1e-12).sum().sum())
    return strat_ret, eq, trades


def _annualized_sharpe(ret: pd.Series) -> float:
    r = ret.dropna()
    if len(r) < 20:
        return 0.0
    sd = r.std(ddof=0)
    if sd <= 0 or not np.isfinite(sd):
        return 0.0
    return float(r.mean() / sd * math.sqrt(DAYS_PER_YEAR))


def _profit_factor(ret: pd.Series) -> float:
    r = ret.dropna()
    pos = r[r > 0].sum()
    neg = -r[r < 0].sum()
    if neg <= 0:
        return float("inf") if pos > 0 else 0.0
    return float(pos / neg)


def _max_drawdown(equity: pd.Series) -> float:
    eq = equity.dropna()
    if len(eq) == 0:
        return 0.0
    peak = eq.cummax()
    return float((eq / peak - 1.0).min())


def _rolling_252_sharpe_worst(ret: pd.Series) -> float:
    r = ret.dropna()
    if len(r) < 252:
        return _annualized_sharpe(r)
    vals = r.to_numpy(dtype=float)
    worst = float("inf")
    for i in range(251, len(vals)):
        w = vals[i - 251 : i + 1]
        sd = w.std(ddof=0)
        if sd <= 0 or not np.isfinite(sd):
            continue
        sh = float(w.mean() / sd * math.sqrt(DAYS_PER_YEAR))
        if sh < worst:
            worst = sh
    return worst if np.isfinite(worst) else _annualized_sharpe(r)


def _metrics(strat_ret: pd.Series, eq: pd.Series, trades: int) -> dict:
    return {
        "sharpe": _annualized_sharpe(strat_ret),
        "profit_factor": _profit_factor(strat_ret),
        "max_drawdown": _max_drawdown(eq),
        "trades": int(trades),
        "periods": int(len(strat_ret.dropna())),
        "total_return": float(eq.iloc[-1] / eq.iloc[0] - 1.0) if len(eq) > 1 else 0.0,
        "worst_regime_rolling252_sharpe": _rolling_252_sharpe_worst(strat_ret),
    }


def _basis_z(prices: pd.DataFrame, window: int) -> pd.Series:
    basis = prices["ES=F"] / prices["SPY"] - 1.0
    return _zscore(basis.astype(float), window)


def _wf_score(train_close: pd.DataFrame, params: dict, n_folds: int = 4) -> float:
    n = len(train_close)
    if n < 300:
        return -999.0
    fold = n // n_folds
    sharpes = []
    z_full = _basis_z(train_close, params["basis_window"])
    for i in range(n_folds):
        start = i * fold
        end = n if i == n_folds - 1 else (i + 1) * fold
        if end - start < 120:
            continue
        c = train_close.iloc[start:end]
        z = z_full.iloc[start:end]
        w = _compute_weights(c, z, **params)
        r, _, _ = _run_bt(c, w)
        sharpes.append(_annualized_sharpe(r))
    return float(np.mean(sharpes)) if sharpes else -999.0


def _information_ratio(strat: pd.Series, bench: pd.Series) -> float:
    a, b = strat.align(bench, join="inner")
    diff = (a - b).dropna()
    sd = diff.std(ddof=0)
    if len(diff) < 20 or sd <= 0 or not np.isfinite(sd):
        return 0.0
    return float(diff.mean() / sd * math.sqrt(DAYS_PER_YEAR))


def _benchmark_pvalue(strat: pd.Series, bench: pd.Series, n_boot: int = 2000) -> float:
    a, b = strat.align(bench, join="inner")
    diff = (a - b).dropna().to_numpy()
    if len(diff) < 20:
        return 1.0
    obs = diff.mean()
    if not np.isfinite(obs):
        return 1.0
    rng = np.random.default_rng(SEED)
    centered = diff - obs
    boots = [
        float(rng.choice(centered, size=len(centered), replace=True).mean()) for _ in range(n_boot)
    ]
    boots_arr = np.array(boots)
    return float((1.0 + np.sum(boots_arr >= obs)) / (n_boot + 1.0))


def _perturbation_oos_sharpes(
    prices: pd.DataFrame, selected: dict, val_start: str, test_end: str
) -> list[float]:
    base = selected.copy()
    sharpes = []
    bw_opts = sorted(
        set(
            [
                max(5, int(round(base["basis_window"] * 0.8))),
                int(base["basis_window"]),
                int(round(base["basis_window"] * 1.2)),
            ]
        )
    )
    ez_opts = sorted(
        set(
            [
                round(base["entry_z"] * 0.8, 4),
                float(base["entry_z"]),
                round(base["entry_z"] * 1.2, 4),
            ]
        )
    )
    xz_opts = sorted(
        set([round(base["exit_z"] * 0.8, 4), float(base["exit_z"]), round(base["exit_z"] * 1.2, 4)])
    )
    vt_opts = sorted(
        set(
            [
                round(base["vol_target"] * 0.8, 4),
                float(base["vol_target"]),
                round(base["vol_target"] * 1.2, 4),
            ]
        )
    )
    mask = (prices.index >= pd.Timestamp(val_start)) & (prices.index <= pd.Timestamp(test_end))
    for bw in bw_opts:
        z = _basis_z(prices, int(bw))
        for ez in ez_opts:
            for xz in xz_opts:
                if xz > ez:
                    continue
                for vt in vt_opts:
                    p = {
                        "basis_window": int(bw),
                        "entry_z": float(ez),
                        "exit_z": float(xz),
                        "vol_target": float(min(max(vt, 0.02), 0.5)),
                    }
                    w = _compute_weights(prices, z, **p)
                    r, _, _ = _run_bt(prices.loc[mask], w.loc[mask])
                    sharpes.append(_annualized_sharpe(r))
    return [s for s in sharpes if np.isfinite(s)]


def _iter_grid():
    for basis_window in GRID["basis_window"]:
        for entry_z in GRID["entry_z"]:
            for exit_z in GRID["exit_z"]:
                if exit_z > entry_z:
                    continue
                for vol_target in GRID["vol_target"]:
                    yield {
                        "basis_window": basis_window,
                        "entry_z": float(entry_z),
                        "exit_z": float(exit_z),
                        "vol_target": float(vol_target),
                    }


def main(out: str | None = None) -> dict:
    t0 = time.time()
    art = _artifact_dir(out)
    prices = _download_close(["ES=F", "SPY"], START, END)
    # Align to common range
    prices = prices.loc[(prices.index >= START) & (prices.index <= END)]
    train = prices.loc[prices.index <= TRAIN_END]
    val = prices.loc[(prices.index > TRAIN_END) & (prices.index <= VAL_END)]
    test = prices.loc[(prices.index > VAL_END) & (prices.index <= END)]
    oos = prices.loc[prices.index > TRAIN_END]
    val_start = str(val.index[0].date()) if len(val) else str(oos.index[0].date())

    rows = []
    for params in _iter_grid():
        wf = _wf_score(train, params)
        z_tr = _basis_z(train, params["basis_window"])
        w_tr = _compute_weights(train, z_tr, **params)
        r_tr, _, _ = _run_bt(train, w_tr)
        rows.append({**params, "wf_train_sharpe": wf, "train_sharpe": _annualized_sharpe(r_tr)})
    grid = pd.DataFrame(rows).sort_values("wf_train_sharpe", ascending=False)
    grid.to_csv(art / "grid.csv", index=False)
    valid = grid[np.isfinite(grid["wf_train_sharpe"])]
    if valid.empty:
        raise RuntimeError("no valid grid rows")
    sel = valid.iloc[0].to_dict()
    selected = {
        "basis_window": int(sel["basis_window"]),
        "entry_z": float(sel["entry_z"]),
        "exit_z": float(sel["exit_z"]),
        "vol_target": float(sel["vol_target"]),
    }

    z_all = _basis_z(prices, selected["basis_window"])
    w_sel = _compute_weights(prices, z_all, **selected)
    oos_ret, oos_eq, oos_trades = _run_bt(oos, w_sel.loc[oos.index])
    oos_m = _metrics(oos_ret, oos_eq, oos_trades)

    bench_w = pd.DataFrame({"SPY": 1.0}, index=oos.index)
    bench_ret, bench_eq, _ = _run_bt(oos, bench_w)
    bench_m = _metrics(bench_ret, bench_eq, 0)

    # Ablation: random signal (same number of active days on OOS, random dates)
    rng = np.random.default_rng(SEED)
    sel_oos_w = w_sel.loc[oos.index, "SPY"]
    n_active = int((sel_oos_w.abs() > 1e-12).sum())
    rand_w = pd.DataFrame({"SPY": 0.0}, index=oos.index)
    if n_active > 0:
        idx = rng.choice(len(oos.index), size=min(n_active, len(oos.index)), replace=False)
        rand_w.iloc[idx, 0] = 1.0
        # apply same vol scaling baseline
        ret = oos["SPY"].pct_change()
        vol = ret.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std() * np.sqrt(DAYS_PER_YEAR)
        scale = (selected["vol_target"] / vol.replace(0.0, np.nan)).clip(0.0, 3.0).fillna(0.0)
        rand_w["SPY"] = (rand_w["SPY"] * scale).clip(-MAX_POS, MAX_POS)
    rand_ret, rand_eq, rand_tr = _run_bt(oos, rand_w)
    rand_m = _metrics(rand_ret, rand_eq, rand_tr)

    # Ablation: inverse signal (long when basis cheap/negative)
    inv_raw = pd.Series(0.0, index=prices.index)
    zv = z_all
    pos = 0.0
    for i in range(len(prices.index)):
        v = zv.iloc[i]
        if not np.isfinite(v):
            inv_raw.iloc[i] = pos
            continue
        if pos == 0.0:
            if v <= -selected["entry_z"]:
                pos = 1.0
            elif v >= selected["entry_z"]:
                pos = 0.0
        else:
            if v >= -selected["exit_z"]:
                pos = 0.0
        inv_raw.iloc[i] = pos
    ret_spy = prices["SPY"].pct_change()
    vol_spy = ret_spy.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std() * np.sqrt(DAYS_PER_YEAR)
    inv_scale = (selected["vol_target"] / vol_spy.replace(0.0, np.nan)).clip(0.0, 3.0).fillna(0.0)
    inv_w = pd.DataFrame({"SPY": (inv_raw * inv_scale).clip(-MAX_POS, MAX_POS)}, index=prices.index)
    inv_ret, inv_eq, inv_tr = _run_bt(oos, inv_w.loc[oos.index])
    inv_m = _metrics(inv_ret, inv_eq, inv_tr)

    z_tr_sel = _basis_z(train, selected["basis_window"])
    tr_ret_sel, _, _ = _run_bt(train, _compute_weights(train, z_tr_sel, **selected))
    train_sel_sharpe = _annualized_sharpe(tr_ret_sel)
    wf_stability = (
        float(oos_m["sharpe"] / train_sel_sharpe)
        if np.isfinite(train_sel_sharpe) and train_sel_sharpe != 0
        else (float("inf") if oos_m["sharpe"] > 0 else 0.0)
    )

    pert = _perturbation_oos_sharpes(prices, selected, val_start, str(prices.index[-1].date()))
    base_sh = oos_m["sharpe"]
    min_ratio = (
        float(min(pert) / base_sh) if pert and np.isfinite(base_sh) and base_sh != 0 else 0.0
    )
    ir = _information_ratio(oos_ret, bench_ret)
    bp = _benchmark_pvalue(oos_ret, bench_ret)

    gates = {
        "sharpe_ge_1": bool(np.isfinite(oos_m["sharpe"]) and oos_m["sharpe"] >= 1.0),
        "trades_ge_50": bool(oos_m["trades"] >= 50),
        "pf_ge_1_3": bool(np.isfinite(oos_m["profit_factor"]) and oos_m["profit_factor"] >= 1.3),
        "maxdd_le_15pct": bool(
            np.isfinite(oos_m["max_drawdown"]) and oos_m["max_drawdown"] >= -0.15
        ),
        "wf_stability_ge_0_7": bool(np.isfinite(wf_stability) and wf_stability >= 0.7),
        "worst_regime_ge_0_3": bool(
            np.isfinite(oos_m["worst_regime_rolling252_sharpe"])
            and oos_m["worst_regime_rolling252_sharpe"] >= 0.3
        ),
        "benchmark_p_le_0_05_and_ir_ge_0": bool(
            np.isfinite(bp) and bp <= 0.05 and np.isfinite(ir) and ir >= 0.0
        ),
        "perturbation_min_ratio_ge_0_5": bool(np.isfinite(min_ratio) and min_ratio >= 0.5),
    }
    gates_passed = int(sum(gates.values()))
    verdict = "ACCEPT" if gates_passed == 8 else "REJECT"

    summary = {
        "experiment": EXPERIMENT,
        "nf_id": NF_ID,
        "hypothesis": HYPOTHESIS,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_sec": round(time.time() - t0, 3),
        "data": {
            "tickers": ["ES=F", "SPY"],
            "rows": int(len(prices)),
            "start": str(prices.index[0].date()),
            "end": str(prices.index[-1].date()),
            "train_end": TRAIN_END,
            "val_end": VAL_END,
            "oos_rows": int(len(oos)),
            "note": "yfinance daily auto_adjusted closes (ES=F, SPY), free/public PIT",
        },
        "selected": selected,
        "wf_train_sharpe": float(sel["wf_train_sharpe"]),
        "train_selected_sharpe": float(train_sel_sharpe),
        "oos_val_test": oos_m,
        "benchmark_buy_hold_spy_oos": bench_m,
        "ablations": {"random_signal_oos": rand_m, "inverse_signal_oos": inv_m},
        "wf_stability_oos_over_train": float(wf_stability)
        if np.isfinite(wf_stability)
        else wf_stability,
        "benchmark_pvalue_one_sided": float(bp),
        "information_ratio_vs_buy_hold": float(ir),
        "perturbation": {
            "min_ratio": float(min_ratio) if np.isfinite(min_ratio) else min_ratio,
            "n_points": len(pert),
            "min_sharpe": float(min(pert)) if pert else None,
        },
        "gates": gates,
        "gates_passed": gates_passed,
        "gates_total": len(gates),
        "verdict": verdict,
        "integrity": {
            "src_qtr_unchanged": True,
            "gate_weakening": False,
            "published_artifacts_modified": False,
            "selection_holdout_feedback": False,
            "real_data": True,
        },
    }
    (art / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(
        json.dumps(
            {
                "verdict": verdict,
                "gates_passed": gates_passed,
                "artifact": str(art),
                "oos_sharpe": oos_m["sharpe"],
            },
            indent=2,
        )
    )
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    main(args.out)
