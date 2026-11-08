"""NF-20261106-29 / H115 (pre-registered): RSP/SPY market breadth/participation
leadership timing for SPY.
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
    compare_to_benchmark,
    sharpe_ratio,
    walk_forward_splits,
)

EXPERIMENT_NAME = "nf_20261106_29_rsp_spy_breadth"
EXPERIMENT_DESC = (
    "NF-20261106-29/H115: RSP/SPY market breadth/participation leadership timing SPY. "
    "Continuous vol-targeted long SPY exposure reduced when trailing "
    "RSP/SPY ratio momentum z-score is abnormally weak (breadth narrowing / "
    "cap-weight concentration), 1-bar delay. Train-only WF selection; Test protected; "
    "OOS gates."
)

RSP = "RSP"
SPY = "SPY"
UNIVERSE = [RSP, SPY]

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
            "close"
            if "close" in df.columns
            else ("Close" if "Close" in df.columns else df.columns[0])
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


def build_breadth_leadership_signal(
    prices: pd.DataFrame,
    lookback: int,
    z_window: int,
    entry_scale: float,
    vol_target: float,
) -> pd.DataFrame:
    for sym in (RSP, SPY):
        if sym not in prices.columns:
            raise ValueError(f"Missing {sym}")
    ratio = np.log(prices[RSP] / prices[SPY])
    mom = ratio.diff(lookback)
    mu = mom.rolling(z_window, min_periods=max(30, z_window // 2)).mean()
    sigma = mom.rolling(z_window, min_periods=max(30, z_window // 2)).std(ddof=0)
    z = (mom - mu) / sigma.replace(0.0, np.nan)
    z = z.fillna(0.0)

    spy_ret = prices[SPY].pct_change()
    realized_vol = spy_ret.rolling(63, min_periods=21).std() * np.sqrt(252)
    vol_scale = (vol_target / realized_vol.replace(0.0, np.nan)).clip(0.0, 1.0).fillna(0.0)

    stress = (-(z + entry_scale)).clip(0.0, 1.0)
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
                sig = build_breadth_leadership_signal(prices, **p)
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
        (pval <= GATES["max_p_value"] and ir >= GATES["min_information_ratio"])
        if (np.isfinite(pval) and np.isfinite(ir))
        else False
    )
    pass_pert = pert >= GATES["min_perturbed_sharpe_ratio"]

    gates = {
        "sharpe_ge_1_0": {"value": sharpe, "threshold": GATES["min_sharpe"], "pass": pass_sh},
        "trades_ge_200": {"value": trades, "threshold": GATES["min_trades"], "pass": pass_tr},
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
        "comparison": cmp if "cmp" in locals() else {},
    }


def _select_on_train(prices: pd.DataFrame, train_mask: pd.Series, cfg: BacktestConfig):
    tr_prices = prices.loc[train_mask, [SPY]]
    rows = []
    for lb in LOOKBACKS:
        for zw in Z_WINDOWS:
            for es in ENTRY_SCALES:
                for vt in VOL_TARGETS:
                    params = {"lookback": lb, "z_window": zw, "entry_scale": es, "vol_target": vt}
                    try:
                        sig = build_breadth_leadership_signal(prices, **params)
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
                        {**params, "wf_mean_sharpe": float(np.mean(fold_sh)) if fold_sh else -9.0}
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
                "hypothesis_id": "H115",
                "nf_id": "NF-20261106-29",
                "universe": UNIVERSE,
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

    best, selection_df = _select_on_train(prices, train_mask, cfg)
    params = {k: best[k] for k in ("lookback", "z_window", "entry_scale", "vol_target")}
    params["lookback"] = int(params["lookback"])
    params["z_window"] = int(params["z_window"])
    sig = build_breadth_leadership_signal(prices, **params)

    train_res = run_backtest(prices.loc[train_mask, [SPY]], sig.loc[train_mask], cfg)
    oos_res = run_backtest(prices.loc[oos_mask, [SPY]], sig.loc[oos_mask], cfg)
    bench_oos = run_backtest(
        prices.loc[oos_mask, [SPY]],
        pd.DataFrame({SPY: 1.0}, index=prices.loc[oos_mask].index),
        cfg,
    )

    rng = np.random.default_rng(SEED)
    oos_idx = prices.loc[oos_mask].index
    rand_pos = rng.uniform(0, MAX_POS, size=len(oos_idx))
    rand_res = run_backtest(
        prices.loc[oos_mask, [SPY]],
        pd.DataFrame({SPY: rand_pos}, index=oos_idx),
        cfg,
    )
    inv_sig = pd.DataFrame({SPY: (MAX_POS - sig[SPY]).clip(0, MAX_POS)}, index=prices.index)
    inv_res = run_backtest(prices.loc[oos_mask, [SPY]], inv_sig.loc[oos_mask], cfg)

    eval_out = evaluate_gates(oos_res, train_res, bench_oos, prices, oos_mask, params, cfg)
    elapsed = round(time.time() - t0, 2)
    exp_id = tracker.current_experiment.experiment_id if tracker.current_experiment else None

    summary = {
        "experiment": EXPERIMENT_NAME,
        "nf_id": "NF-20261106-29",
        "hypothesis": "H115",
        "verdict": eval_out["verdict"],
        "passed_gates": f"{eval_out['passed']}/{eval_out['total']}",
        "experiment_id": exp_id,
        "elapsed_s": elapsed,
        "data": {
            "rows": int(len(prices)),
            "train": int(train_mask.sum()),
            "val": int(val_mask.sum()),
            "test": int(test_mask.sum()),
            "start": str(prices.index.min().date()),
            "end": str(prices.index.max().date()),
        },
        "selected_params": params,
        "selection_wf_mean_sharpe": best["wf_mean_sharpe"],
        "train_metrics": train_res.metrics,
        "oos_metrics": oos_res.metrics,
        "benchmark_oos_metrics": bench_oos.metrics,
        "ablations": {
            "buy_hold_spy": bench_oos.metrics,
            "random_exposure_matched": rand_res.metrics,
            "inverse_stress_long": inv_res.metrics,
        },
        "gates": eval_out["gates"],
        "comparison": eval_out["comparison"],
        "selection_table_top10": selection_df.head(10).to_dict(orient="records"),
        "config": {
            "gates": GATES,
            "grid": {
                "lookbacks": LOOKBACKS,
                "z_windows": Z_WINDOWS,
                "entry_scales": ENTRY_SCALES,
                "vol_targets": VOL_TARGETS,
            },
        },
    }

    out_dir = Path(__file__).parent / ".experiments" / "nf_runs" / EXPERIMENT_NAME
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    try:
        tracker.finish_experiment(eval_out["verdict"])
    except Exception:
        pass

    print(
        json.dumps(
            {
                "verdict": eval_out["verdict"],
                "passed": summary["passed_gates"],
                "experiment_id": exp_id,
                "selected": params,
                "oos_sharpe": oos_res.metrics.get("sharpe"),
                "oos_trades": oos_res.metrics.get("num_trades"),
                "oos_pf": _profit_factor(oos_res.returns.fillna(0.0).values),
                "oos_dd": oos_res.metrics.get("max_drawdown"),
                "elapsed_s": elapsed,
            },
            indent=2,
            default=str,
        )
    )
    return summary


if __name__ == "__main__":
    main()
