"""NF-20261109-30 / H175 (Cycle 89): TIP-vs-IEF inflation-compensation
relative-momentum regime timing for SPY.

Mechanism (macro / inflation-expectations transmission; repo-new executed
observable): TIP (TIPS) vs IEF (intermediate nominal Treasuries) relative
returns proxy changes in inflation compensation / breakeven expectations and
associated real-rate/inflation-risk-premium conditions. When TIP underperforms
IEF on a trailing window (negative relative momentum z-score) — consistent with
falling inflation compensation or tightening real-rate pressure relative to
nominals — de-risk a vol-targeted long SPY position. 1-bar execution delay.

Repo-relative novelty (honest): no executed H-ID tests TIP-vs-IEF relative
momentum as SPY timing. NF-09-03 (breakeven-inflation ^T5YIE/^T10YIE) was
deferred/data-limited on yfinance; H175 uses a materially different
instrument/observable (ETF price-return spread, TIP/IEF, free/PIT) — different
construction and executed root. H94 used HYG-IEF credit (different pair).
H141/H151/H153/H92 used TLT/TLT-SHY (different duration/instrument/observable).
Honest adjacency to relmom/z-score de-risking construction class
(H144/H145/H152/H157) and to broad rates/macro families is disclosed; novelty
scored repo-relative on the executed TIP-IEF inflation-compensation observable.

Data (free, PIT): SPY, TIP, IEF daily auto-adjust Close via yfinance.
Splits: Train 2010-01-04→2018-05-31, Val 2018-06-01→2022-08-12, Test (protected)
2022-08-13→2026-10-30. Selection = train-only 4-fold walk-forward Sharpe; gates
on OOS Val+Test only. No holdout feedback.
"""

from __future__ import annotations

import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from qtr.backtest.engine import AssetClass, BacktestConfig, CostModel, run_backtest

EXPERIMENT = "nf_20261109_30_tip_ief_inflation_spy"
HYPOTHESIS = "H175"
NF_ID = "NF-20261109-30"
SYMBOLS = ["SPY", "TIP", "IEF"]
START = "2010-01-01"
END = "2026-11-01"
TRAIN_END = "2018-05-31"
VAL_END = "2022-08-12"
MAX_POS = 0.5
DAYS_PER_YEAR = 252


def fetch_prices() -> pd.DataFrame:
    raw = yf.download(
        SYMBOLS, start=START, end=END, auto_adjust=True, progress=False
    )
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"].copy()
    else:
        close = raw[["Close"]].copy()
        close.columns = SYMBOLS[:1]
    close = close.dropna(how="all")
    close = close[SYMBOLS].dropna()
    close.index = pd.to_datetime(close.index)
    return close.astype(float)


def split_index(
    idx: pd.DatetimeIndex,
) -> tuple[pd.DatetimeIndex, pd.DatetimeIndex, pd.DatetimeIndex]:
    train = idx[idx <= pd.Timestamp(TRAIN_END)]
    val = idx[(idx > pd.Timestamp(TRAIN_END)) & (idx <= pd.Timestamp(VAL_END))]
    test = idx[idx > pd.Timestamp(VAL_END)]
    return train, val, test


def rolling_z(series: pd.Series, window: int) -> pd.Series:
    mu = series.rolling(window, min_periods=window).mean()
    sd = series.rolling(window, min_periods=window).std(ddof=0)
    return (series - mu) / sd.replace(0.0, np.nan)


def build_signal(
    prices: pd.DataFrame,
    mom_window: int,
    z_window: int,
    entry_scale: float,
    vol_target: float,
) -> pd.DataFrame:
    ret_tip = prices["TIP"].pct_change(mom_window)
    ret_ief = prices["IEF"].pct_change(mom_window)
    relmom = ret_tip - ret_ief
    z = rolling_z(relmom, z_window)
    # pre-registered: de-risk when TIP underperforms IEF (negative z)
    stress = ((-z).clip(lower=0.0) / entry_scale).clip(upper=1.0)
    spy_ret = prices["SPY"].pct_change()
    rv = spy_ret.rolling(21, min_periods=21).std(ddof=0) * math.sqrt(DAYS_PER_YEAR)
    vol_scale = (vol_target / rv).clip(upper=1.0)
    raw = (1.0 - stress.fillna(0.0)) * vol_scale.fillna(0.0)
    exposure = raw.clip(lower=0.0, upper=1.0) * MAX_POS
    sig = pd.DataFrame(0.0, index=prices.index, columns=["SPY"])
    sig["SPY"] = exposure
    sig.loc[z.isna(), "SPY"] = 0.0
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


def max_dd(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(dd.min()) if len(dd) else 0.0


def worst_regime_sharpe(returns: pd.Series, window: int = 252) -> float:
    if len(returns) < window:
        return float("nan")
    roll = returns.rolling(window).apply(
        lambda x: (x.mean() / x.std(ddof=0) * math.sqrt(DAYS_PER_YEAR))
        if x.std(ddof=0) > 0
        else 0.0,
        raw=False,
    )
    return float(roll.min())


def profit_factor(returns: pd.Series) -> float:
    gains = returns[returns > 0].sum()
    losses = -returns[returns < 0].sum()
    if losses <= 0:
        return float("inf") if gains > 0 else 0.0
    return float(gains / losses)


def _run_backtest_daily(prices: pd.DataFrame, signal: pd.DataFrame) -> dict:
    res = run_backtest(prices=prices, signals=signal, config=_cfg())
    m = res.metrics
    equity = res.equity_curve
    rets = equity.pct_change().dropna()
    if isinstance(m, dict):
        sharpe = float(m.get("sharpe", float("nan")))
        pf = float(m.get("profit_factor", float("nan")))
        mdd = float(m.get("max_drawdown", float("nan")))
        trades = int(m.get("num_trades", 0))
    else:
        sharpe = float(
            getattr(m, "sharpe_ratio", getattr(m, "sharpe", float("nan")))
        )
        pf = float(getattr(m, "profit_factor", float("nan")))
        mdd = float(getattr(m, "max_drawdown", float("nan")))
        trades = int(getattr(m, "trades_count", getattr(m, "num_trades", 0)))
    if not math.isfinite(pf):
        pf = profit_factor(rets)
    return {
        "sharpe": sharpe,
        "profit_factor": pf,
        "max_drawdown": mdd,
        "trades": trades,
        "worst_regime_sharpe_252": worst_regime_sharpe(rets),
        "equity": equity,
        "returns": rets,
    }


def walkforward_mean_sharpe(
    prices: pd.DataFrame, params: dict, train_idx: pd.DatetimeIndex, folds: int = 4
) -> float:
    n = len(train_idx)
    fold_size = n // (folds + 1)
    sharpes = []
    for i in range(folds):
        start = i * fold_size
        end = start + 2 * fold_size
        if end > n:
            break
        sub = train_idx[start:end]
        sub_prices = prices.loc[sub]
        sig = build_signal(sub_prices, **params)
        ev = _run_backtest_daily(sub_prices[["SPY"]], sig)
        sharpes.append(float(ev["sharpe"]) if math.isfinite(ev["sharpe"]) else 0.0)
    return float(np.mean(sharpes)) if sharpes else 0.0


def benchmark_ir_p(strategy: pd.Series, benchmark: pd.Series) -> tuple[float, float]:
    aligned = pd.concat([strategy, benchmark], axis=1).dropna()
    if len(aligned) < 30:
        return 0.0, 1.0
    diff = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    sd = diff.std(ddof=0)
    if sd <= 0:
        return 0.0, 1.0
    ir = float(diff.mean() / sd * math.sqrt(DAYS_PER_YEAR))
    from math import erf, sqrt

    z = diff.mean() / (sd / sqrt(len(diff)))
    p = 1.0 - 0.5 * (1.0 + erf(z / sqrt(2.0)))
    return ir, float(p)


def perturbation_min_ratio(
    prices: pd.DataFrame, base: dict, base_sharpe: float, oos_idx: pd.DatetimeIndex
) -> float:
    if base_sharpe == 0 or not math.isfinite(base_sharpe):
        return 0.0
    ratios = []
    variants = [
        {**base, "mom_window": max(5, int(base["mom_window"] * 0.8))},
        {**base, "mom_window": max(5, int(base["mom_window"] * 1.2))},
        {**base, "z_window": max(21, int(base["z_window"] * 0.8))},
        {**base, "z_window": max(21, int(base["z_window"] * 1.2))},
        {**base, "entry_scale": max(0.1, base["entry_scale"] * 0.8)},
        {**base, "entry_scale": base["entry_scale"] * 1.2},
        {**base, "vol_target": max(0.01, base["vol_target"] * 0.8)},
        {**base, "vol_target": base["vol_target"] * 1.2},
    ]
    for v in variants:
        sig = build_signal(prices, **v).loc[oos_idx]
        ev = _run_backtest_daily(prices.loc[oos_idx, ["SPY"]], sig)
        ratios.append(ev["sharpe"] / base_sharpe)
    return float(min(ratios)) if ratios else 0.0


def _pack(ev: dict, extra: dict | None = None) -> dict:
    d = {
        "sharpe": ev["sharpe"],
        "profit_factor": ev["profit_factor"],
        "max_drawdown": ev["max_drawdown"],
        "trades": ev["trades"],
        "worst_regime_sharpe_252": ev.get("worst_regime_sharpe_252"),
    }
    if extra:
        d.update(extra)
    return d


def main() -> None:
    t0 = time.time()
    prices = fetch_prices()
    train_idx, val_idx, test_idx = split_index(prices.index)
    oos_idx = prices.index[(prices.index > pd.Timestamp(TRAIN_END))]

    grid = []
    for mom_window in [21, 63, 126]:
        for z_window in [126, 252]:
            if z_window < mom_window:
                continue
            for entry_scale in [1.0, 2.0]:
                for vol_target in [0.10, 0.15]:
                    grid.append(
                        dict(
                            mom_window=mom_window,
                            z_window=z_window,
                            entry_scale=entry_scale,
                            vol_target=vol_target,
                        )
                    )

    rows = []
    for params in grid:
        wf = walkforward_mean_sharpe(prices, params, train_idx)
        sig = build_signal(prices, **params)
        tr = _run_backtest_daily(prices.loc[train_idx, ["SPY"]], sig.loc[train_idx])
        rows.append(
            {
                **params,
                "wf_sharpe": wf,
                "train_sharpe": tr["sharpe"],
                "train_trades": tr["trades"],
            }
        )
    grid_df = pd.DataFrame(rows).sort_values(
        ["wf_sharpe", "train_sharpe"], ascending=False
    )
    best = grid_df.iloc[0].to_dict()
    selected = {
        "mom_window": int(best["mom_window"]),
        "z_window": int(best["z_window"]),
        "entry_scale": float(best["entry_scale"]),
        "vol_target": float(best["vol_target"]),
    }

    sig = build_signal(prices, **selected)
    tr_ev = _run_backtest_daily(prices.loc[train_idx, ["SPY"]], sig.loc[train_idx])
    va_ev = _run_backtest_daily(prices.loc[val_idx, ["SPY"]], sig.loc[val_idx])
    te_ev = _run_backtest_daily(prices.loc[test_idx, ["SPY"]], sig.loc[test_idx])
    oos_ev = _run_backtest_daily(prices.loc[oos_idx, ["SPY"]], sig.loc[oos_idx])

    bh = prices.loc[oos_idx, "SPY"].pct_change().dropna()
    bh_eq = (1 + bh).cumprod()
    bh_sharpe = float("nan")
    if bh.std(ddof=0) > 0:
        bh_sharpe = float(bh.mean() / bh.std(ddof=0) * math.sqrt(DAYS_PER_YEAR))
    bh_stats = {
        "sharpe": bh_sharpe,
        "profit_factor": profit_factor(bh),
        "max_drawdown": max_dd(bh_eq),
        "trades": 1,
    }
    ir, p = benchmark_ir_p(oos_ev["returns"], bh)

    rng = np.random.default_rng(42)
    rand_sig = pd.DataFrame(0.0, index=oos_idx, columns=["SPY"])
    active = (sig.loc[oos_idx, "SPY"] > 0).to_numpy()
    rand_active = active.copy()
    rng.shuffle(rand_active)
    rand_sig["SPY"] = np.where(rand_active, sig.loc[oos_idx, "SPY"].to_numpy(), 0.0)
    rand_ev = _run_backtest_daily(prices.loc[oos_idx, ["SPY"]], rand_sig)

    inv_sig = pd.DataFrame(0.0, index=prices.index, columns=["SPY"])
    ret_tip = prices["TIP"].pct_change(selected["mom_window"])
    ret_ief = prices["IEF"].pct_change(selected["mom_window"])
    z = rolling_z(ret_tip - ret_ief, selected["z_window"])
    inv_stress = (z.clip(lower=0.0) / selected["entry_scale"]).clip(upper=1.0)
    spy_ret = prices["SPY"].pct_change()
    rv = spy_ret.rolling(21, min_periods=21).std(ddof=0) * math.sqrt(DAYS_PER_YEAR)
    vol_scale = (selected["vol_target"] / rv).clip(upper=1.0)
    inv_raw = (1.0 - inv_stress.fillna(0.0)) * vol_scale.fillna(0.0)
    inv_sig["SPY"] = inv_raw.clip(lower=0.0, upper=1.0) * MAX_POS
    inv_sig.loc[z.isna(), "SPY"] = 0.0
    inv_ev = _run_backtest_daily(prices.loc[oos_idx, ["SPY"]], inv_sig.loc[oos_idx])

    wf_stab = (
        float(oos_ev["sharpe"] / best["wf_sharpe"])
        if best["wf_sharpe"]
        and math.isfinite(best["wf_sharpe"])
        and best["wf_sharpe"] > 0
        and math.isfinite(oos_ev["sharpe"])
        else 0.0
    )
    pert = perturbation_min_ratio(prices, selected, oos_ev["sharpe"], oos_idx)

    gates = {
        "sharpe_ge_1": bool(
            math.isfinite(oos_ev["sharpe"]) and oos_ev["sharpe"] >= 1.0
        ),
        "profit_factor_ge_1_3": bool(
            math.isfinite(oos_ev["profit_factor"]) and oos_ev["profit_factor"] >= 1.3
        ),
        "max_dd_le_15pct": bool(
            math.isfinite(oos_ev["max_drawdown"]) and oos_ev["max_drawdown"] >= -0.15
        ),
        "trades_ge_200": bool(oos_ev["trades"] >= 200),
        "wf_stability_ge_0_7": bool(math.isfinite(wf_stab) and wf_stab >= 0.7),
        "worst_regime_ge_0_3": bool(
            math.isfinite(oos_ev["worst_regime_sharpe_252"])
            and oos_ev["worst_regime_sharpe_252"] >= 0.3
        ),
        "benchmark_p_le_0_05_ir_ge_0": bool(p <= 0.05 and ir >= 0.0),
        "perturbation_min_ratio_ge_0_5": bool(
            math.isfinite(pert) and pert >= 0.5
        ),
    }
    passed = sum(1 for v in gates.values() if v)
    verdict = "ACCEPT" if passed == 8 else "REJECT"

    summary = {
        "experiment": EXPERIMENT,
        "hypothesis": HYPOTHESIS,
        "nf_id": NF_ID,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "data": {
            "symbols": SYMBOLS,
            "start": str(prices.index.min().date()),
            "end": str(prices.index.max().date()),
            "rows": int(len(prices)),
            "train": [
                str(train_idx.min().date()),
                str(train_idx.max().date()),
                int(len(train_idx)),
            ],
            "val": [
                str(val_idx.min().date()),
                str(val_idx.max().date()),
                int(len(val_idx)),
            ],
            "test": [
                str(test_idx.min().date()),
                str(test_idx.max().date()),
                int(len(test_idx)),
            ],
        },
        "selected": {**selected, "train_wf_sharpe": best["wf_sharpe"]},
        "grid_size": len(grid),
        "train": _pack(tr_ev),
        "val": _pack(va_ev),
        "test": _pack(te_ev),
        "oos_val_test": _pack(
            oos_ev,
            {
                "wf_stability": wf_stab,
                "benchmark_ir": ir,
                "benchmark_p": p,
                "perturbation_min_ratio": pert,
            },
        ),
        "gates": gates,
        "gates_passed": passed,
        "verdict": verdict,
        "ablations": {
            "buy_hold_spy": bh_stats,
            "random_exposure_matched": _pack(rand_ev),
            "inverse_signal": _pack(inv_ev),
        },
        "runtime_seconds": round(time.time() - t0, 2),
        "notes": [
            "TIP-IEF inflation-compensation relative momentum; de-risk on negative z (TIP underperforms IEF).",
            "Honest adjacency to relmom/z-score construction class (H144/H145/H152/H157) and NF-09-03 breakeven concept (different instrument/observable: ETF spread, free/PIT).",
            "Pre-registered OOS gates on Val+Test only; train-only WF selection; protected test; 1-bar delay via engine signals.shift(1).",
        ],
    }

    out_dir = (
        Path(".experiments/nf_runs")
        / f"{EXPERIMENT}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    grid_df.to_csv(out_dir / "grid.csv", index=False)
    print(
        json.dumps(
            {
                "verdict": verdict,
                "gates_passed": passed,
                "oos": summary["oos_val_test"],
                "selected": selected,
                "out_dir": str(out_dir),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
