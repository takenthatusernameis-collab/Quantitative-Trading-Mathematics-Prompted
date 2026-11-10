"""NF-20261106-34 / H117 (pre-registered, Cycle 31): Cross-sectional sector
correlation regime timing for SPY.

Feasibility adjustment (documented, pre-registered "verify before execution"):
use 9 GICS sector ETFs with full 2010+ history (XLK,XLF,XLE,XLV,XLI,XLY,
XLP,XLU,XLB); exclude XLC (2018 inception) and XLRE (2015) to avoid truncating
the pre-registered sample/splits. 4233 aligned rows each, 0 non-positive,
2010-01-04..2026-10-30 via DataFetcher/cache. No src/qtr change.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import numpy as np
import pandas as pd

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
    walk_forward_splits,
)

EXPERIMENT_NAME = "nf_20261106_34_sector_corr_regime"
EXPERIMENT_DESC = (
    "NF-20261106-34/H117: cross-sectional sector correlation regime timing for "
    "SPY. Signal = z-score of trailing average pairwise sector return "
    "correlation (lookback window) over z_window. When correlation regime is "
    "abnormally high (contagion/risk-off), reduce vol-targeted long SPY "
    "exposure continuously, 1-bar delay. 9 sectors with full 2010+ history "
    "(XLC/XLRE excluded for feasibility). Train-only WF selection; Test "
    "protected; OOS gates."
)

SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB"]
SPY = "SPY"
UNIVERSE = SECTORS + [SPY]

DATA_START = "2010-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"

SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5

LOOKBACKS = [21, 63]
Z_WINDOWS = [126, 252]
ENTRY_SCALES = [1.0, 1.5, 2.0]
VOL_TARGETS = [0.10, 0.15]
WF_FOLDS_SELECTION = 4

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
        allow_short=False,
    )


def _align_prices(fetcher: DataFetcher, symbols, start: str, end: str) -> pd.DataFrame:
    raw = fetcher.fetch_yahoo(symbols, start=start, end=end)
    if not isinstance(raw, dict):
        raise RuntimeError(f"fetch_yahoo returned {type(raw)}, expected dict")
    frames = {}
    for s in symbols:
        df = raw.get(s)
        if df is None or df.empty:
            raise RuntimeError(f"Data fetch failed for {s}")
        col = (
            "adj_close"
            if "adj_close" in df.columns
            else (
                "close"
                if "close" in df.columns
                else ("Close" if "Close" in df.columns else df.columns[0])
            )
        )
        c = df[col].astype(float)
        if (c <= 0).any():
            raise RuntimeError(f"Non-positive prices in {s}")
        frames[s] = c.rename(s)
    prices = pd.concat(frames.values(), axis=1).dropna()
    if prices.empty:
        raise RuntimeError("No aligned data")
    return prices


def _splits(prices: pd.DataFrame):
    train_mask = prices.index <= pd.Timestamp(TRAIN_END)
    val_mask = (prices.index > pd.Timestamp(TRAIN_END)) & (prices.index <= pd.Timestamp(VAL_END))
    test_mask = prices.index > pd.Timestamp(VAL_END)
    return train_mask, val_mask, test_mask


def _avg_pairwise_corr(rets: pd.DataFrame, lookback: int) -> pd.Series:
    """Trailing average pairwise correlation of sector returns (past-only)."""
    n = rets.shape[1]
    denom = n * n - n
    if denom <= 0:
        return pd.Series(0.0, index=rets.index)
    vals = np.full(len(rets), np.nan)
    arr = rets.values
    for i in range(lookback, len(rets) + 1):
        w = arr[i - lookback : i]
        # handle any NaNs in window
        valid = ~np.isnan(w).any(axis=1)
        if valid.sum() < max(10, lookback // 2):
            continue
        c = np.corrcoef(w[valid], rowvar=False)
        if c.ndim != 2:
            continue
        vals[i - 1] = (c.sum() - np.trace(c)) / denom
    return pd.Series(vals, index=rets.index)


def build_sector_corr_signal(
    prices: pd.DataFrame,
    lookback: int,
    z_window: int,
    entry_scale: float,
    vol_target: float,
) -> pd.DataFrame:
    for sym in UNIVERSE:
        if sym not in prices.columns:
            raise ValueError(f"Missing {sym}")
    sector_rets = prices[SECTORS].pct_change()
    avg_corr = _avg_pairwise_corr(sector_rets, lookback)
    mu = avg_corr.rolling(z_window, min_periods=max(30, z_window // 2)).mean()
    sigma = avg_corr.rolling(z_window, min_periods=max(30, z_window // 2)).std(ddof=0)
    z = (avg_corr - mu) / sigma.replace(0.0, np.nan)
    z = z.fillna(0.0)

    spy_ret = prices[SPY].pct_change()
    realized_vol = spy_ret.rolling(63, min_periods=21).std() * np.sqrt(252)
    vol_scale = (vol_target / realized_vol.replace(0.0, np.nan)).clip(0.0, 1.0)
    vol_scale = vol_scale.fillna(0.0)

    # Pre-registered mapping: high correlation regime (contagion/risk-off) =>
    # reduce SPY exposure continuously.
    stress = (z - entry_scale).clip(0.0, 1.0)
    exposure = MAX_POS * (1.0 - stress) * vol_scale
    sig = pd.DataFrame({SPY: exposure.astype(float).clip(0.0, MAX_POS)}, index=prices.index)
    warmup = max(z_window, 63) + lookback
    sig.iloc[:warmup] = 0.0
    sig[sig.isna()] = 0.0
    return sig


def _profit_factor(returns: np.ndarray) -> float:
    gains = returns[returns > 0].sum()
    losses = -returns[returns < 0].sum()
    if losses <= 1e-12:
        return float("inf") if gains > 0 else 0.0
    return float(gains / losses)


def evaluate_gates(oos_res, train_res, benchmark_oos, prices, oos_mask, selected_params, cfg):
    oos_rets = oos_res.returns.fillna(0.0).values
    train_rets = train_res.returns.fillna(0.0).values
    metrics = oos_res.metrics
    sharpe = float(metrics.get("sharpe", 0.0))
    trades = int(metrics.get("num_trades", 0))
    pf = _profit_factor(oos_rets)
    max_dd_abs = abs(float(metrics.get("max_drawdown", 1.0)))

    wf_stab = 0.0
    if len(train_rets) > 0 and np.std(train_rets) > 1e-12:
        train_sh = float(sharpe_ratio(train_rets))
        if abs(train_sh) > 1e-12:
            wf_stab = float(sharpe / train_sh)
        elif abs(sharpe) < 1e-12:
            wf_stab = 1.0

    roll_window = 252
    s = pd.Series(oos_rets)
    roll = s.rolling(roll_window).apply(
        lambda x: sharpe_ratio(x.values) if np.std(x) > 1e-12 else 0.0, raw=False
    )
    worst_reg = float(roll.dropna().min()) if roll.notna().any() else 0.0

    try:
        cmp = compare_to_benchmark(
            oos_res.returns.fillna(0.0),
            benchmark_oos.returns.fillna(0.0),
        )
        pval = float(cmp.get("alpha_p_value", 1.0))
        ir = float(cmp.get("information_ratio", -1.0))
    except Exception:
        cmp = {}
        pval, ir = 1.0, -1.0

    base_sh = sharpe if abs(sharpe) > 1e-12 else 1e-12
    pert_ratios = []
    for mult in (0.8, 1.2):
        for key in ("lookback", "z_window", "entry_scale", "vol_target"):
            p = dict(selected_params)
            p[key] = type(p[key])(p[key] * mult)
            if key in ("lookback", "z_window"):
                p[key] = max(5, int(round(p[key])))
            try:
                sig = build_sector_corr_signal(prices, **p)
                res = run_backtest(prices.loc[oos_mask, [SPY]], sig.loc[oos_mask], cfg)
                pert_ratios.append(float(res.metrics.get("sharpe", 0.0)) / base_sh)
            except Exception:
                pert_ratios.append(0.0)
    pert = float(np.min(pert_ratios)) if pert_ratios else 0.0

    pass_sh = sharpe >= GATES["min_sharpe"]
    pass_tr = trades >= GATES["min_trades"]
    pass_pf = pf >= GATES["min_profit_factor"]
    pass_dd = max_dd_abs <= GATES["max_drawdown"]
    pass_wf = (wf_stab >= GATES["min_walkforward_stability"]) if np.isfinite(wf_stab) else False
    pass_reg = worst_reg >= GATES["min_worst_regime_sharpe"] if np.isfinite(worst_reg) else False
    pass_bench = (
        (benchmark_significance_gate(pval, ir, GATES["max_p_value"]))
        if (np.isfinite(pval) and np.isfinite(ir))
        else False
    )
    pass_pert = pert >= GATES["min_perturbed_sharpe_ratio"]

    gates = {
        "sharpe_ge_1_0": {
            "value": sharpe,
            "threshold": GATES["min_sharpe"],
            "pass": pass_sh,
        },
        "trades_ge_200": {
            "value": trades,
            "threshold": GATES["min_trades"],
            "pass": pass_tr,
        },
        "profit_factor_ge_1_3": {
            "value": pf,
            "threshold": GATES["min_profit_factor"],
            "pass": pass_pf,
        },
        "max_drawdown_le_15pct": {
            "value": max_dd_abs,
            "threshold": GATES["max_drawdown"],
            "pass": pass_dd,
        },
        "walkforward_stability_ge_0_7": {
            "value": wf_stab,
            "threshold": GATES["min_walkforward_stability"],
            "pass": pass_wf,
        },
        "worst_regime_rolling252_sharpe_ge_0_3": {
            "value": worst_reg,
            "threshold": GATES["min_worst_regime_sharpe"],
            "pass": pass_reg,
        },
        "benchmark_p_le_0_05_ir_ge_0": {
            "value": {"p_value": pval, "information_ratio": ir},
            "threshold": {"p": GATES["max_p_value"], "ir": GATES["min_information_ratio"]},
            "pass": pass_bench,
        },
        "perturbation_min_ratio_ge_0_5": {
            "value": pert,
            "threshold": GATES["min_perturbed_sharpe_ratio"],
            "pass": pass_pert,
        },
    }
    passed = sum(1 for g in gates.values() if g["pass"])
    verdict = "PASS" if passed == len(gates) else "REJECT"
    return {
        "verdict": verdict,
        "passed": passed,
        "total": len(gates),
        "gates": gates,
        "comparison": cmp,
    }


def _select_on_train(prices: pd.DataFrame, train_mask: pd.Series, cfg: BacktestConfig):
    tr_prices = prices.loc[train_mask, [SPY]]
    rows = []
    for lb in LOOKBACKS:
        for zw in Z_WINDOWS:
            for es in ENTRY_SCALES:
                for vt in VOL_TARGETS:
                    params = {
                        "lookback": lb,
                        "z_window": zw,
                        "entry_scale": es,
                        "vol_target": vt,
                    }
                    try:
                        sig = build_sector_corr_signal(prices, **params)
                    except Exception:
                        continue
                    try:
                        tr_rets = (
                            run_backtest(tr_prices, sig.loc[train_mask], cfg)
                            .returns.fillna(0.0)
                            .values
                        )
                    except Exception:
                        continue
                    fold_sh = []
                    try:
                        for tr_i, te_i in walk_forward_splits(
                            len(tr_rets), n_splits=WF_FOLDS_SELECTION
                        ):
                            if len(te_i) < 30:
                                continue
                            fold_sh.append(float(sharpe_ratio(tr_rets[te_i])))
                    except Exception:
                        continue
                    rows.append(
                        {
                            **params,
                            "wf_mean_sharpe": float(np.mean(fold_sh)) if fold_sh else -9.0,
                        }
                    )
    if not rows:
        raise RuntimeError("No valid train-selection candidates")
    df = pd.DataFrame(rows).sort_values("wf_mean_sharpe", ascending=False)
    return df.iloc[0].to_dict(), df


def main():
    np.random.seed(SEED)
    tracker = get_tracker()
    t0 = time.time()
    try:
        tracker.start_experiment(EXPERIMENT_NAME, EXPERIMENT_DESC)
    except Exception:
        pass
    try:
        tracker.log_params(
            {
                "hypothesis_id": "H117",
                "nf_id": "NF-20261106-34",
                "universe": UNIVERSE,
                "sectors": SECTORS,
                "feasibility_note": "XLC/XLRE excluded (2018/2015 inception) to preserve 2010+ sample",
                "data_start": DATA_START,
                "data_end": DATA_END,
                "train_end": TRAIN_END,
                "val_end": VAL_END,
                "grid_size": len(LOOKBACKS) * len(Z_WINDOWS) * len(ENTRY_SCALES) * len(VOL_TARGETS),
                "selection": "best_train_4fold_walkforward_sharpe",
                "gates": GATES,
                "seed": SEED,
                "max_position": MAX_POS,
            }
        )
    except Exception:
        pass

    fetcher = DataFetcher(DataCache(Path(".cache/data")))
    prices = _align_prices(fetcher, UNIVERSE, DATA_START, DATA_END)
    train_mask, val_mask, test_mask = _splits(prices)
    oos_mask = val_mask | test_mask

    cfg = make_equity_config()
    selected, grid_df = _select_on_train(prices, train_mask, cfg)
    params = {
        "lookback": int(selected["lookback"]),
        "z_window": int(selected["z_window"]),
        "entry_scale": float(selected["entry_scale"]),
        "vol_target": float(selected["vol_target"]),
    }
    sig = build_sector_corr_signal(prices, **params)
    tr_res = run_backtest(prices.loc[train_mask, [SPY]], sig.loc[train_mask], cfg)
    oos_res = run_backtest(prices.loc[oos_mask, [SPY]], sig.loc[oos_mask], cfg)
    bh_oos = run_backtest(
        prices.loc[oos_mask, [SPY]],
        pd.DataFrame({SPY: 1.0}, index=prices.loc[oos_mask].index),
        cfg,
    )
    gate_res = evaluate_gates(oos_res, tr_res, bh_oos, prices, oos_mask, params, cfg)

    rng = np.random.default_rng(SEED)
    oos_rets = oos_res.returns.fillna(0.0).values
    exp_levels = sig.loc[oos_mask, SPY].fillna(0.0).values
    rnd = np.zeros_like(oos_rets)
    for i in range(len(oos_rets)):
        rnd[i] = rng.choice(oos_rets) * (exp_levels[i] / MAX_POS)
    inv_sig = pd.DataFrame({SPY: (MAX_POS - sig[SPY]).clip(0.0, MAX_POS)}, index=prices.index)
    inv_res = run_backtest(prices.loc[oos_mask, [SPY]], inv_sig.loc[oos_mask], cfg)
    ablations = {
        "buy_hold_spy_oos": bh_oos.metrics,
        "random_exposure_matched_oos": {
            "sharpe": float(sharpe_ratio(rnd)),
            "profit_factor": _profit_factor(rnd),
            "max_drawdown": float(
                run_backtest(
                    prices.loc[oos_mask, [SPY]],
                    pd.DataFrame({SPY: exp_levels / MAX_POS}, index=prices.loc[oos_mask].index),
                    cfg,
                ).metrics.get("max_drawdown", 0.0)
            ),
            "num_trades": int(np.sum(np.abs(np.diff(exp_levels)) > 1e-8)),
        },
        "inverse_stress_long_oos": inv_res.metrics,
    }

    summary = {
        "experiment": EXPERIMENT_NAME,
        "description": EXPERIMENT_DESC,
        "hypothesis_id": "H117",
        "nf_id": "NF-20261106-34",
        "selected_params": params,
        "selection_score_wf_mean_sharpe": float(selected.get("wf_mean_sharpe", float("nan"))),
        "train_metrics": tr_res.metrics,
        "oos_val_test_metrics": oos_res.metrics,
        "gate_evaluation": gate_res,
        "ablations": ablations,
        "data": {
            "start": str(prices.index[0].date()),
            "end": str(prices.index[-1].date()),
            "rows": int(len(prices)),
            "train_rows": int(train_mask.sum()),
            "val_rows": int(val_mask.sum()),
            "test_rows": int(test_mask.sum()),
            "sectors_used": SECTORS,
            "feasibility_note": "XLC/XLRE excluded (2018/2015 inception); 9 sectors + SPY, 0 non-positive",
        },
        "elapsed_s": round(time.time() - t0, 3),
    }
    out = Path(".experiments") / "nf_runs" / EXPERIMENT_NAME
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    (out / "grid.csv").write_text(grid_df.to_csv(index=False))
    try:
        tracker.log_metrics(
            {
                "oos_sharpe": gate_res["gates"]["sharpe_ge_1_0"]["value"],
                "oos_trades": gate_res["gates"]["trades_ge_200"]["value"],
                "oos_pf": gate_res["gates"]["profit_factor_ge_1_3"]["value"],
                "verdict_pass_count": gate_res["passed"],
            }
        )
        tracker.end_experiment(status="completed")
    except Exception:
        pass
    print(
        json.dumps(
            {
                "verdict": gate_res["verdict"],
                "passed": gate_res["passed"],
                "total": gate_res["total"],
                "summary": str(out / "summary.json"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
