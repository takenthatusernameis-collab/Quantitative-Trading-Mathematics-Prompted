"""NF-20261106-26 / H113 (pre-registered): VIX9D/VIX short-term volatility
term-structure timing for SPY.
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

EXPERIMENT_NAME = "nf_20261106_26_vix9d_vix_termstructure"
EXPERIMENT_DESC = (
    "NF-20261106-26/H113: VIX9D/VIX short-term term-structure timing SPY. "
    "Continuous vol-targeted long SPY exposure reduced when trailing "
    "VIX9D/VIX ratio momentum z-score is abnormally high (front-end stress), "
    "1-bar delay. Train-only WF selection; Test protected; OOS gates."
)

VIX9D = "^VIX9D"
VIX = "^VIX"
SPY = "SPY"
UNIVERSE = [VIX9D, VIX, SPY]

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


def _splits(prices: pd.DataFrame):
    train_mask = prices.index <= pd.Timestamp(TRAIN_END)
    val_mask = (prices.index > pd.Timestamp(TRAIN_END)) & (prices.index <= pd.Timestamp(VAL_END))
    test_mask = prices.index > pd.Timestamp(VAL_END)
    return train_mask, val_mask, test_mask


def _align_prices(fetcher: DataFetcher, symbols, start, end) -> pd.DataFrame:
    raw = fetcher.fetch_yahoo(symbols, start=start, end=end)
    if not isinstance(raw, dict):
        raise RuntimeError(f"fetch_yahoo returned {type(raw)}, expected dict")
    closes = {}
    for s in symbols:
        df = raw.get(s)
        if df is None or df.empty:
            raise RuntimeError(f"Data fetch failed for {s}")
        col = (
            "close"
            if "close" in df.columns
            else ("Close" if "Close" in df.columns else df.columns[0])
        )
        close = df[col].astype(float)
        if (close <= 0).any():
            raise RuntimeError(f"Non-positive prices in {s}")
        closes[s] = close.rename(s)
    return pd.concat(closes, axis=1).sort_index().ffill().dropna()


def build_vix_termstructure_signal(
    prices: pd.DataFrame,
    lookback: int,
    z_window: int,
    entry_scale: float,
    vol_target: float,
) -> pd.DataFrame:
    missing = [s for s in [VIX9D, VIX, SPY] if s not in prices.columns]
    if missing:
        raise ValueError(f"Missing symbols: {missing}")
    ratio = (prices[VIX9D] / prices[VIX]).replace([np.inf, -np.inf], np.nan)
    lr = np.log(ratio).shift(1)  # past-only
    mom = lr.rolling(lookback, min_periods=lookback).mean()
    mu = mom.rolling(z_window, min_periods=z_window).mean()
    sd = mom.rolling(z_window, min_periods=z_window).std(ddof=0).replace(0.0, np.nan)
    z = ((mom - mu) / sd).fillna(0.0)
    stress = np.clip((z - entry_scale) / entry_scale, 0.0, 1.0)
    calm = 1.0 - 0.5 * stress
    spy_ret = prices[SPY].pct_change()
    rv = spy_ret.rolling(21, min_periods=21).std() * np.sqrt(252)
    scale = (vol_target / rv).replace([np.inf, -np.inf], np.nan).clip(0.0, 1.5)
    scale = scale.fillna(0.0)
    pos = (scale * calm).clip(0.0, MAX_POS)
    warmup = max(lookback, z_window, 22) + 1
    pos.iloc[:warmup] = 0.0
    return pd.DataFrame({SPY: pos.astype(float)}, index=prices.index)


def _profit_factor(returns: np.ndarray) -> float:
    gains = returns[returns > 0].sum()
    losses = -returns[returns < 0].sum()
    if losses <= 1e-12:
        return float("inf") if gains > 0 else 0.0
    return float(gains / losses)


def _regime_sharpes(returns: np.ndarray, window: int = 252):
    if len(returns) < window:
        return np.nan
    sharpes = []
    for i in range(window, len(returns) + 1):
        seg = returns[i - window : i]
        if seg.std(ddof=0) < 1e-18:
            continue
        sharpes.append(float(np.mean(seg) / seg.std(ddof=0) * np.sqrt(252)))
    if not sharpes:
        return np.nan
    return float(np.min(sharpes))


def evaluate_gates(oos_res, train_res, bench_res, prices, oos_mask, params, cfg):
    rets = oos_res.returns.fillna(0.0).values
    bench_rets = bench_res.returns.fillna(0.0).values
    sr_oos = float(sharpe_ratio(rets))
    trades = int(getattr(oos_res, "metrics", {}).get("num_trades", 0))
    pf = _profit_factor(rets)
    dd = float(oos_res.metrics.get("max_drawdown", 0.0))
    sr_train = float(sharpe_ratio(train_res.returns.fillna(0.0).values))
    wf_stab = (sr_oos / sr_train) if sr_train > 1e-12 else 0.0
    regime = _regime_sharpes(rets)
    cmp = compare_to_benchmark(rets, bench_rets)
    pval = cmp.get("alpha_p_value") if isinstance(cmp, dict) else None
    ir = cmp.get("information_ratio") if isinstance(cmp, dict) else None
    if pval is None:
        pval = 1.0
    if ir is None:
        ir = -np.inf

    rng = np.random.default_rng(SEED)
    pert_ratios = []
    base_sr = sr_oos if sr_oos > 1e-12 else -np.inf
    for _ in range(10):
        pret = run_backtest(
            prices.loc[oos_mask, [SPY]],
            pd.DataFrame(
                {
                    SPY: np.clip(
                        oos_res.positions[SPY].values * (1 + rng.uniform(-0.1, 0.1, len(rets))),
                        0,
                        MAX_POS,
                    )
                },
                index=prices.loc[oos_mask].index,
            ),
            cfg,
        )
        psr = float(sharpe_ratio(pret.returns.fillna(0.0).values))
        if base_sr > 1e-12:
            pert_ratios.append(psr / base_sr)
        else:
            pert_ratios.append(0.0)
    pert = float(np.min(pert_ratios)) if pert_ratios else 0.0

    pass_sr = sr_oos >= GATES["min_sharpe"]
    pass_tr = trades >= GATES["min_trades"]
    pass_pf = pf >= GATES["min_profit_factor"]
    pass_dd = dd <= GATES["max_drawdown"]
    pass_wf = wf_stab >= GATES["min_walkforward_stability"] if sr_train > 0 else wf_stab >= 0
    pass_reg = (regime >= GATES["min_worst_regime_sharpe"]) if not np.isnan(regime) else False
    pass_bench = pval <= GATES["max_p_value"] and ir >= GATES["min_information_ratio"]
    pass_pert = pert >= GATES["min_perturbed_sharpe_ratio"]

    gates = {
        "oos_sharpe_ge_1_0": {"value": sr_oos, "threshold": GATES["min_sharpe"], "pass": pass_sr},
        "trades_ge_200": {"value": trades, "threshold": GATES["min_trades"], "pass": pass_tr},
        "profit_factor_ge_1_3": {
            "value": pf,
            "threshold": GATES["min_profit_factor"],
            "pass": pass_pf,
        },
        "max_drawdown_le_0_15": {"value": dd, "threshold": GATES["max_drawdown"], "pass": pass_dd},
        "walkforward_stability_ge_0_7": {
            "value": wf_stab,
            "threshold": GATES["min_walkforward_stability"],
            "pass": pass_wf,
        },
        "worst_regime_sharpe_ge_0_3": {
            "value": regime,
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
                    params = {"lookback": lb, "z_window": zw, "entry_scale": es, "vol_target": vt}
                    try:
                        sig = build_vix_termstructure_signal(prices, **params)
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
                "hypothesis_id": "H113",
                "nf_id": "NF-20261106-26",
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
    sig = build_vix_termstructure_signal(prices, **params)

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
    try:
        exp_id = tracker.current_experiment.experiment_id if tracker.current_experiment else None
    except Exception:
        exp_id = None

    summary = {
        "experiment": EXPERIMENT_NAME,
        "nf_id": "NF-20261106-26",
        "hypothesis": "H113",
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
