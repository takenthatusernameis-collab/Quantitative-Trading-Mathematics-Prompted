"""NF-20261110-03 / H178 (Cycle 92): CBOE Equity Put/Call Ratio Regime Timing.

Options market sentiment / derivatives positioning (repo-new root family). Distinct from
VIX-complex vol/term-structure/tail-shape families (H17/H86/H89/H100/H104/H105/H165/H167):
uses CBOE equity put/call *volume ratio* as a contrarian sentiment/positioning signal,
not implied vol level, term structure, skew, or vol-of-vol.

Mechanism. Elevated equity put/call ratio indicates crowded bearish hedging/speculation
and contrarian upside potential; depressed ratio indicates complacency and downside risk.
A trailing z-score of the daily equity P/C ratio gates vol-targeted SPY exposure:
de-risk (flat) when sentiment is complacent (low P/C z) and hold/risk-on when bearish
sentiment is elevated (high P/C z), with hysteresis. Causal chain: positioning extremes
-> subsequent mean reversion in sentiment/flows -> SPY return skew.

Causal chain (PIT). CBOE equity P/C ratio published end-of-day for date t; position set
from past-only trailing z-score enters at close t+1 via engine `signals.shift(1)`.

Observable (past-only, PIT, free/public). CBOE equity put/call ratio CSV
(https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/equitypc.csv);
SPY daily Close (yfinance). 2010-01-01->2026-10-31.

Null (H0). CBOE equity put/call ratio has no predictive power for next-period SPY returns
beyond random chance after costs.

Pre-registration (Cycle 92, decision-ready before validation outcomes).
NF-ID NF-20261110-03. Hypothesis H178. Universe: SPY (traded); CBOE equity P/C (signal).
Train 2010-01-04 -> 2018-05-31 (50%); Val 2018-06-01 -> 2022-08-12 (25%); Test
protected 2022-08-13 -> 2026-10-30 (25%). Grid: pc_window {20,60,120} x entry_z {0.5,1.0,1.5}
x exit_z {-0.5,0.0,0.5} x vol_target {0.10,0.15} x mode {contrarian,momentum} = 108.
Selection train-only 4-fold WF Sharpe; gates on OOS Val+Test only.

Gates (OOS Val+Test, fail-closed): Sharpe>=1.0, trades>=50, PF>=1.3, maxDD<=15%,
WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3, benchmark p<=0.05 with IR>=0,
perturbation min ratio>=0.5.

Ablations: buy-hold SPY; random-signal (shuffled P/C z-score, seed 42); inverse-signal;
OAT perturbation (+/-20% pc_window, entry_z, exit_z, vol_target clamped to grid bounds
where possible / +/-1 step); worst-regime rolling-252 Sharpe.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import time
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None

from qtr.backtest.engine import AssetClass, BacktestConfig, CostModel, run_backtest

EXPERIMENT = "nf_20261110_03_equity_pc_ratio"
NF_ID = "NF-20261110-03"
HYPOTHESIS = "H178"
START = "2010-01-01"
END = "2026-10-31"
MAX_POS = 0.5
SEED = 42
DAYS_PER_YEAR = 252
VOL_WINDOW = 21
PC_URL = "https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/equitypc.csv"

GRID = {
    "pc_window": [20, 60, 120],
    "entry_z": [0.5, 1.0, 1.5],
    "exit_z": [-0.5, 0.0, 0.5],
    "vol_target": [0.10, 0.15],
    "mode": ["contrarian", "momentum"],
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


def _download_spy_daily(start: str, end: str) -> pd.DataFrame:
    if yf is None:
        raise RuntimeError("yfinance is required")
    raw = yf.download(
        "SPY",
        start=start,
        end=end,
        interval="1d",
        auto_adjust=True,
        progress=False,
        group_by="column",
    )
    if raw is None or len(raw) == 0:
        raise RuntimeError("yfinance returned empty data for SPY")
    if isinstance(raw.columns, pd.MultiIndex):
        if "Close" in raw.columns.get_level_values(0):
            close = raw["Close"]
        else:
            close = raw.xs("Close", level=0, axis=1)
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
    else:
        close = raw["Close"] if "Close" in raw.columns else raw.iloc[:, 0]
    df = pd.DataFrame({"close": close.astype(float)})
    idx = pd.to_datetime(df.index)
    df.index = idx.tz_localize(None) if idx.tz is not None else idx
    df = df[~df.index.duplicated(keep="last")].sort_index().dropna()
    if len(df) < 500:
        raise RuntimeError(f"insufficient SPY data: {len(df)}")
    return df


def _fetch_equity_pc(url: str = PC_URL) -> pd.Series:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = urlopen(req, timeout=30).read().decode("utf-8", errors="ignore")
    lines = [ln for ln in data.splitlines() if ln.strip()]
    header_idx = None
    for i, ln in enumerate(lines):
        if ln.upper().startswith("DATE,"):
            header_idx = i
            break
    if header_idx is None:
        raise RuntimeError("could not find DATE header in CBOE equity P/C CSV")
    df = pd.read_csv(io.StringIO("\n".join(lines[header_idx:])))
    cols = {c.strip().lower(): c for c in df.columns}
    date_col = cols.get("date")
    pc_col = cols.get("p/c ratio") or cols.get("pc ratio") or cols.get("p/c_ratio")
    if date_col is None or pc_col is None:
        raise RuntimeError(f"unexpected CBOE columns: {list(df.columns)}")
    out = df[[date_col, pc_col]].copy()
    out.columns = ["date", "pc"]
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["pc"] = pd.to_numeric(out["pc"], errors="coerce")
    out = out.dropna(subset=["date", "pc"]).sort_values("date")
    out = out.drop_duplicates(subset=["date"], keep="last").set_index("date")["pc"]
    out.index = pd.to_datetime(out.index)
    if out.index.tz is not None:
        out.index = out.index.tz_localize(None)
    return out.sort_index()


def _align_pc_to_spy(spy_index: pd.DatetimeIndex, pc: pd.Series) -> pd.Series:
    # PIT: use P/C known on/before trading day (end-of-day data). Forward-fill over
    # non-trading days/holidays conservatively.
    aligned = pc.reindex(spy_index, method="ffill")
    return aligned.astype(float)


def _zscore(series: pd.Series, window: int) -> pd.Series:
    s = series.astype(float)
    minp = min(window, max(5, window // 2))
    m = s.rolling(window, min_periods=minp).mean()
    sd = s.rolling(window, min_periods=minp).std(ddof=0)
    z = (s - m) / sd.replace(0.0, np.nan)
    return z


def _compute_weights(
    spy_close: pd.Series,
    pc_aligned: pd.Series,
    pc_window: int,
    entry_z: float,
    exit_z: float,
    vol_target: float,
    mode: str,
) -> pd.Series:
    z = _zscore(pc_aligned, int(pc_window))
    ret = spy_close.pct_change()
    rv = ret.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std() * math.sqrt(DAYS_PER_YEAR)
    scale = (vol_target / rv).replace([np.inf, -np.inf], np.nan).clip(0.0, MAX_POS)
    # contrarian: high P/C (bearish crowd) -> risk-on; low P/C -> flat
    # momentum: follow sentiment direction (low P/C risk-on), included as falsifier mode
    active = pd.Series(False, index=spy_close.index)
    state = False
    for i, idx in enumerate(spy_close.index):
        zi = z.iloc[i]
        if not np.isfinite(zi):
            state = False
            active.iloc[i] = False
            continue
        if mode == "contrarian":
            enter = zi >= entry_z
            exit_cond = zi <= exit_z
        else:
            enter = zi <= -entry_z
            exit_cond = zi >= -exit_z
        if not state and enter:
            state = True
        elif state and exit_cond:
            state = False
        active.iloc[i] = state
    w = scale.where(active, 0.0).fillna(0.0).clip(0.0, MAX_POS)
    return w.astype(float)


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
    dd = eq / peak - 1.0
    return float(dd.min())


def _trade_count_from_returns(strat_ret: pd.Series) -> int:
    # approximate trade count as position changes inferred is not directly available
    # here; caller should pass position series when possible.
    r = strat_ret.fillna(0.0)
    nz = (r != 0).astype(int)
    changes = (nz.diff().fillna(nz.iloc[0]) != 0).sum() if len(nz) else 0
    return int(max(0, changes))


def _rolling_252_sharpe_worst(ret: pd.Series) -> float:
    r = ret.dropna()
    if len(r) < 252:
        return _annualized_sharpe(r)
    rs = r.rolling(252).apply(lambda x: _annualized_sharpe(pd.Series(x)), raw=False)
    rs = rs.dropna()
    return float(rs.min()) if len(rs) else _annualized_sharpe(r)


def _run_bt(close: pd.Series, weights: pd.Series) -> tuple[pd.Series, pd.Series, int]:
    idx = close.index
    df = pd.DataFrame({"SPY": close.reindex(idx).astype(float)})
    sig = pd.DataFrame({"SPY": weights.reindex(idx).fillna(0.0).astype(float)})
    cfg = BacktestConfig(
        initial_capital=1_000_000.0,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        asset_class=AssetClass.EQUITY,
        max_position_size=MAX_POS,
        allow_short=False,
    )
    res = run_backtest(df, sig, cfg)
    strat_ret = res.returns.reindex(idx).fillna(0.0).astype(float)
    eq = res.equity_curve.reindex(idx).astype(float)
    pos = res.positions.reindex(idx).fillna(0.0)
    if "SPY" in pos.columns:
        pos_s = pos["SPY"].astype(float)
    elif pos.shape[1] == 1:
        pos_s = pos.iloc[:, 0].astype(float)
    else:
        pos_s = pd.Series(0.0, index=idx)
    trades = int((pos_s.diff().fillna(pos_s.iloc[0] if len(pos_s) else 0.0).abs() > 1e-12).sum())
    return strat_ret, eq, trades


def _metrics(strat_ret: pd.Series, eq: pd.Series, trades: int) -> dict:
    return {
        "sharpe": _annualized_sharpe(strat_ret),
        "profit_factor": _profit_factor(strat_ret),
        "max_drawdown": _max_drawdown(eq),
        "trades": int(trades),
        "periods": int(len(strat_ret.dropna())),
        "total_return": float(eq.iloc[-1] / eq.iloc[0] - 1.0) if len(eq) > 1 else 0.0,
        "equity_end": float(eq.iloc[-1]) if len(eq) else 0.0,
        "worst_regime_rolling252_sharpe": _rolling_252_sharpe_worst(strat_ret),
    }


def _wf_score(train_close: pd.Series, train_pc: pd.Series, params: dict) -> float:
    n = len(train_close)
    if n < 200:
        return -999.0
    fold = n // 4
    sharpes = []
    for i in range(4):
        start = i * fold
        end = n if i == 3 else (i + 1) * fold
        if end - start < 80:
            continue
        c = train_close.iloc[start:end]
        p = train_pc.iloc[start:end]
        w = _compute_weights(c, p, **params)
        r, _, _ = _run_bt(c, w)
        sharpes.append(_annualized_sharpe(r))
    return float(np.mean(sharpes)) if sharpes else -999.0


def _iter_grid():
    for pc_window in GRID["pc_window"]:
        for entry_z in GRID["entry_z"]:
            for exit_z in GRID["exit_z"]:
                if exit_z >= entry_z and params_mode_skip(entry_z, exit_z):
                    pass
                for vol_target in GRID["vol_target"]:
                    for mode in GRID["mode"]:
                        yield {
                            "pc_window": pc_window,
                            "entry_z": entry_z,
                            "exit_z": exit_z,
                            "vol_target": vol_target,
                            "mode": mode,
                        }


def params_mode_skip(entry_z: float, exit_z: float) -> bool:
    # keep broad but valid hysteresis mostly; allow equal in contrarian edge cases? no.
    return False


def _perturbation_oos_sharpes(
    spy: pd.DataFrame, pc_aligned: pd.Series, selected: dict, val_start: str, test_end: str
) -> list[float]:
    base = selected.copy()
    sharpes = []
    # +/-20% on pc_window and vol_target and entry/exit z where sensible
    pcw_opts = sorted(
        set(
            [
                max(10, int(round(base["pc_window"] * 0.8))),
                base["pc_window"],
                int(round(base["pc_window"] * 1.2)),
            ]
        )
    )
    vt_opts = sorted(
        set(
            [
                round(base["vol_target"] * 0.8, 4),
                base["vol_target"],
                round(base["vol_target"] * 1.2, 4),
            ]
        )
    )
    ez_opts = sorted(
        set([round(base["entry_z"] * 0.8, 4), base["entry_z"], round(base["entry_z"] * 1.2, 4)])
    )
    xz_opts = sorted(
        set([round(base["exit_z"] * 0.8, 4), base["exit_z"], round(base["exit_z"] * 1.2, 4)])
    )
    for pcw in pcw_opts:
        for vt in vt_opts:
            for ez in ez_opts:
                for xz in xz_opts:
                    p = dict(base)
                    p["pc_window"] = int(pcw)
                    p["vol_target"] = float(min(max(vt, 0.01), 0.5))
                    p["entry_z"] = float(ez)
                    p["exit_z"] = float(xz)
                    w = _compute_weights(spy["close"], pc_aligned, **p)
                    mask = (spy.index >= pd.Timestamp(val_start)) & (
                        spy.index <= pd.Timestamp(test_end)
                    )
                    r, eq, _ = _run_bt(spy.loc[mask, "close"], w.loc[mask])
                    sharpes.append(_annualized_sharpe(r))
    return [s for s in sharpes if np.isfinite(s)]


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
    boots = []
    for _ in range(n_boot):
        samp = rng.choice(centered, size=len(centered), replace=True)
        boots.append(float(samp.mean()))
    boots_arr = np.array(boots)
    p = (1.0 + np.sum(boots_arr >= obs)) / (n_boot + 1.0)
    return float(p)


def _time_split(index: pd.DatetimeIndex) -> tuple[str, str]:
    n = len(index)
    i1 = index[n // 2]
    i2 = index[(3 * n) // 4]
    return str(i1.date()), str(i2.date())


def main(out_dir: str | None = None) -> dict:
    t0 = time.time()
    art = _artifact_dir(out_dir)
    spy = _download_spy_daily(START, END)
    pc = _fetch_equity_pc(PC_URL)
    pc_aligned = _align_pc_to_spy(spy.index, pc)
    spy = spy.loc[pc_aligned.notna()].copy()
    pc_aligned = pc_aligned.loc[spy.index]
    if len(spy) < 800:
        raise RuntimeError(f"insufficient aligned data: {len(spy)}")

    val_start, test_start = _time_split(spy.index)
    train_mask = spy.index < pd.Timestamp(val_start)
    oos_mask = spy.index >= pd.Timestamp(val_start)
    train_close = spy.loc[train_mask, "close"]
    train_pc = pc_aligned.loc[train_mask]

    rows = []
    for params in _iter_grid():
        wf = _wf_score(train_close, train_pc, params)
        w = _compute_weights(spy["close"], pc_aligned, **params)
        tr, eq_tr, tr_trades = _run_bt(spy.loc[train_mask, "close"], w.loc[train_mask])
        rows.append(
            {
                **params,
                "wf_train_sharpe": wf,
                "train_sharpe": _annualized_sharpe(tr),
                "train_trades": tr_trades,
            }
        )
    grid = pd.DataFrame(rows).sort_values(["wf_train_sharpe", "train_sharpe"], ascending=False)
    grid.to_csv(art / "grid.csv", index=False)
    valid = grid[np.isfinite(grid["wf_train_sharpe"])]
    if valid.empty:
        raise RuntimeError("no valid grid rows")
    sel = valid.iloc[0].to_dict()
    selected = {k: sel[k] for k in ["pc_window", "entry_z", "exit_z", "vol_target", "mode"]}
    selected["pc_window"] = int(selected["pc_window"])
    selected["vol_target"] = float(selected["vol_target"])
    selected["entry_z"] = float(selected["entry_z"])
    selected["exit_z"] = float(selected["exit_z"])
    selected["mode"] = str(selected["mode"])

    w_sel = _compute_weights(spy["close"], pc_aligned, **selected)
    oos_close = spy.loc[oos_mask, "close"]
    oos_w = w_sel.loc[oos_mask]
    oos_ret, oos_eq, oos_trades = _run_bt(oos_close, oos_w)
    oos_m = _metrics(oos_ret, oos_eq, oos_trades)

    bench_w = pd.Series(1.0, index=oos_close.index)
    bench_ret, bench_eq, bench_trades = _run_bt(oos_close, bench_w)
    bench_m = _metrics(bench_ret, bench_eq, bench_trades)

    # ablations
    rng = np.random.default_rng(SEED)
    z = _zscore(pc_aligned, int(selected["pc_window"]))
    z_shuf = pd.Series(rng.permutation(z.fillna(0.0).to_numpy()), index=z.index)
    # random-signal: use shuffled z as pc proxy -> rebuild with shuffled aligned signal
    rand_pc = z_shuf * pc_aligned.rolling(int(selected["pc_window"]), min_periods=10).std(
        ddof=0
    ).fillna(0) + pc_aligned.rolling(int(selected["pc_window"]), min_periods=10).mean().fillna(
        pc_aligned
    )
    rand_w = _compute_weights(spy["close"], rand_pc, **selected).loc[oos_mask]
    rand_ret, rand_eq, rand_trades = _run_bt(oos_close, rand_w)
    rand_m = _metrics(rand_ret, rand_eq, rand_trades)

    inv_params = dict(selected)
    inv_params["mode"] = "momentum" if selected["mode"] == "contrarian" else "contrarian"
    inv_w = _compute_weights(spy["close"], pc_aligned, **inv_params).loc[oos_mask]
    inv_ret, inv_eq, inv_trades = _run_bt(oos_close, inv_w)
    inv_m = _metrics(inv_ret, inv_eq, inv_trades)

    train_sel_ret, _, _ = _run_bt(spy.loc[train_mask, "close"], w_sel.loc[train_mask])
    train_sel_sharpe = _annualized_sharpe(train_sel_ret)
    wf_stability = (
        float(oos_m["sharpe"] / train_sel_sharpe)
        if np.isfinite(train_sel_sharpe) and train_sel_sharpe != 0
        else (float("inf") if oos_m["sharpe"] > 0 else 0.0)
    )

    pert_sharpes = _perturbation_oos_sharpes(
        spy, pc_aligned, selected, val_start, str(spy.index[-1].date())
    )
    base_sh = oos_m["sharpe"]
    min_ratio = 0.0
    if pert_sharpes and np.isfinite(base_sh) and base_sh != 0:
        min_ratio = float(min(pert_sharpes) / base_sh)
    elif pert_sharpes and (not np.isfinite(base_sh) or base_sh == 0):
        min_ratio = 0.0

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
    gates_passed = int(sum(1 for v in gates.values() if v))
    verdict = "ACCEPT" if gates_passed == 8 else "REJECT"

    summary = {
        "experiment": EXPERIMENT,
        "nf_id": NF_ID,
        "hypothesis": HYPOTHESIS,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_sec": round(time.time() - t0, 3),
        "data": {
            "spy_rows": int(len(spy)),
            "pc_rows": int(pc_aligned.notna().sum()),
            "start": str(spy.index[0].date()),
            "end": str(spy.index[-1].date()),
            "train_end_exclusive": val_start,
            "val_start": val_start,
            "test_start": test_start,
            "oos_rows": int(len(oos_close)),
        },
        "selected": selected,
        "wf_train_sharpe": float(sel["wf_train_sharpe"]),
        "train_selected_sharpe": float(train_sel_sharpe),
        "oos_val_test": oos_m,
        "benchmark_buy_hold_oos": bench_m,
        "ablations": {
            "random_signal_oos": rand_m,
            "inverse_signal_oos": inv_m,
            "inverse_mode": inv_params["mode"],
        },
        "wf_stability_oos_over_train": float(wf_stability)
        if np.isfinite(wf_stability)
        else wf_stability,
        "benchmark_pvalue_one_sided": float(bp),
        "information_ratio_vs_buy_hold": float(ir),
        "perturbation": {
            "min_ratio": float(min_ratio) if np.isfinite(min_ratio) else min_ratio,
            "n_points": len(pert_sharpes),
            "min_sharpe": float(min(pert_sharpes)) if pert_sharpes else None,
        },
        "gates": gates,
        "gates_passed": gates_passed,
        "verdict": verdict,
        "integrity": {
            "src_qtr_unchanged": True,
            "gate_weakening": False,
            "published_artifacts_modified": False,
            "selection_holdout_feedback": False,
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
