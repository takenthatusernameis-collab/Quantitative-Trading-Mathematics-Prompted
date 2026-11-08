"""NF-20261106-16 / H107 (pre-registered): KRE regional-bank stress transmission timing for SPY.

Mechanism: KRE (regional bank ETF) underperformance can reflect
funding/liquidity stress, deposit/credit impairment, or balance-sheet/rate
risk concerns in the banking/intermediation sector. Such stress may propagate
to broader financial conditions and equity risk premia (systemic spillover).
A trailing KRE momentum z-score provides a point-in-time banking-stress proxy:
reduce SPY exposure when KRE is abnormally weak (stress) and increase exposure
when calm.

New family dimension (financial intermediation / regional-bank liquidity-stress
transmission), distinct from H94 (HYG-IEF credit spread/flight-to-quality;
credit-market observable), H96 (realized cross-asset correlation regime),
FX/rates/vol families (H95/H100/H103/H104/H105/H106), and H101 (HG/GC growth
regime). KRE captures bank-equity/intermediation stress, not credit spreads,
FX, or implied vol.

Causality / timing (pre-registered): trailing KRE lookback return z-score for
day t uses prices through close t only (trailing windows, min_periods).
Signals are shifted by 1 bar (engine signals.shift(1)); target at close t
earns return t -> t+1.

Data: yfinance daily KRE, SPY adjusted close (free), 2010-01-01 ->
2026-10-31.
Splits (pre-registered): Train 2010-01-01 -> 2019-12-31; Val 2020-01-01 ->
2022-12-31; Test 2023-01-01 -> 2026-10-31 (protected holdout).
Grid (bounded): lookback {21,63} x z_window {126,252} x entry_scale {1.0,1.5,2.0}
x vol_target {0.10,0.15} (24 combos). Selection = best train-only 4-fold
walk-forward Sharpe; Test protected; gates on OOS Val+Test.
Cost model: equity defaults.

Gates (OOS Val+Test): OOS Sharpe>=1.0, >=200 trades, PF>=1.3, max DD<=15%,
WF stability test>=0.7*train when train>0, worst-regime rolling-252 Sharpe>=0.3,
benchmark p<=0.05 with IR>=0, perturbation min ratio>=0.5.
Rejection: OOS Sharpe<0.5, PF<1.1, max DD>15%, <200 trades.
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

EXPERIMENT_NAME = "nf_20261106_16_kre_stress"
EXPERIMENT_DESC = (
    "NF-20261106-16/H107: KRE regional-bank stress transmission timing SPY. "
    "Continuous vol-targeted long SPY exposure reduced when trailing KRE "
    "momentum z-score is abnormally weak (banking/funding stress), 1-bar "
    "delay. Train-only WF selection; Test protected; OOS gates."
)

KRE = "KRE"
SPY = "SPY"
UNIVERSE = [KRE, SPY]

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


def build_kre_signal(
    prices: pd.DataFrame,
    lookback: int,
    z_window: int,
    entry_scale: float,
    vol_target: float,
) -> pd.DataFrame:
    """Continuous causal KRE banking-stress signal on SPY (no shift).

    Exposure is reduced when trailing KRE momentum z-score is abnormally weak
    (z <= -entry_scale indicates banking/funding stress). Uses only trailing
    data (min_periods). Engine applies signals.shift(1) for 1-bar execution
    delay.
    """
    if KRE not in prices.columns or SPY not in prices.columns:
        raise ValueError(f"prices must contain {KRE} and {SPY}")
    mom = prices[KRE].pct_change(lookback)
    mp = max(60, z_window // 2)
    z = (mom - mom.rolling(z_window, min_periods=mp).mean()) / mom.rolling(
        z_window, min_periods=mp
    ).std()
    # Stress when KRE weak: map z=-entry_scale -> 0 exposure, z>=0 -> full
    raw = (1.0 + (z.clip(upper=0.0) / entry_scale)).clip(0.0, 1.0)
    spy_ret = prices[SPY].pct_change()
    vol = spy_ret.rolling(21, min_periods=21).std() * np.sqrt(252)
    scale = (vol_target / vol.replace(0.0, np.nan)).clip(0.0, 1.0).fillna(0.0)
    sig = (raw * scale * MAX_POS).fillna(0.0)
    return pd.DataFrame({SPY: sig}, index=prices.index)


def _trade_count(result) -> int:
    return int(result.metrics.get("num_trades", 0))


def _worst_regime_sharpe(returns: pd.Series, window: int = 252) -> float:
    if len(returns) < window:
        return float("nan")
    rolling = returns.rolling(window).apply(lambda x: sharpe_ratio(x.values), raw=False)
    return float(rolling.min())


def _perturbation_ratio(
    prices: pd.DataFrame,
    oos_mask: pd.Series,
    best: dict,
    base_sharpe: float,
    cfg: BacktestConfig,
) -> float:
    if base_sharpe == 0 or not np.isfinite(base_sharpe):
        return 0.0
    ratios = []
    for key, deltas in [
        ("lookback", [-0.2, 0.2]),
        ("z_window", [-0.2, 0.2]),
        ("entry_scale", [-0.2, 0.2]),
        ("vol_target", [-0.2, 0.2]),
    ]:
        for d in deltas:
            p = dict(best)
            val = p[key]
            p[key] = type(val)(val * (1 + d)) if isinstance(val, int) else val * (1 + d)
            if key in ("lookback", "z_window"):
                p[key] = max(10, int(round(p[key])))
            try:
                sig = build_kre_signal(prices, **p)
                r = run_backtest(prices.loc[oos_mask, [SPY]], sig.loc[oos_mask], cfg)
                s = float(r.metrics.get("sharpe", 0.0))
                if np.isfinite(s):
                    ratios.append(s / base_sharpe)
            except Exception:
                pass
    return float(min(ratios)) if ratios else 0.0


def evaluate_gates(
    oos_result,
    train_result,
    bench_result,
    prices: pd.DataFrame,
    oos_mask: pd.Series,
    best: dict,
    cfg: BacktestConfig,
) -> dict:
    oos_sh = float(oos_result.metrics.get("sharpe", 0.0))
    train_sh = float(train_result.metrics.get("sharpe", 0.0))
    trades = _trade_count(oos_result)
    pf = float(oos_result.metrics.get("profit_factor", 0.0))
    max_dd = abs(float(oos_result.metrics.get("max_drawdown", 0.0)))
    cmp = compare_to_benchmark(oos_result.returns, bench_result.returns)
    ir = float(cmp.get("information_ratio", 0.0))
    pval = cmp.get("alpha_p_value")
    wf = oos_sh / train_sh if train_sh > 1e-12 else 0.0
    worst = _worst_regime_sharpe(oos_result.returns)
    pert = _perturbation_ratio(prices, oos_mask, best, oos_sh, cfg)

    pass_sh = oos_sh >= GATES["min_sharpe"]
    pass_tr = trades >= GATES["min_trades"]
    pass_pf = pf >= GATES["min_profit_factor"]
    pass_dd = max_dd <= GATES["max_drawdown"]
    pass_wf = (wf >= GATES["min_walkforward_stability"]) if train_sh > 0 else False
    pass_reg = (worst >= GATES["min_worst_regime_sharpe"]) if np.isfinite(worst) else False
    pass_bench = (
        pval is not None and pval <= GATES["max_p_value"] and ir >= GATES["min_information_ratio"]
    )
    pass_pert = pert >= GATES["min_perturbed_sharpe_ratio"]

    gates = {
        "oos_sharpe_gte_1": {
            "value": oos_sh,
            "threshold": GATES["min_sharpe"],
            "pass": bool(pass_sh),
        },
        "min_trades_gte_200": {
            "value": trades,
            "threshold": GATES["min_trades"],
            "pass": bool(pass_tr),
        },
        "profit_factor_gte_1_3": {
            "value": pf,
            "threshold": GATES["min_profit_factor"],
            "pass": bool(pass_pf),
        },
        "max_drawdown_lte_15pct": {
            "value": max_dd,
            "threshold": GATES["max_drawdown"],
            "pass": bool(pass_dd),
        },
        "walkforward_stability_gte_0_7": {
            "value": wf,
            "threshold": GATES["min_walkforward_stability"],
            "pass": bool(pass_wf),
            "note": "test/train when train>0",
        },
        "worst_regime_sharpe_gte_0_3": {
            "value": worst,
            "threshold": GATES["min_worst_regime_sharpe"],
            "pass": bool(pass_reg),
        },
        "benchmark_p_lte_0_05_ir_gte_0": {
            "value": {"p_value": pval, "information_ratio": ir},
            "threshold": {"p": GATES["max_p_value"], "ir": GATES["min_information_ratio"]},
            "pass": bool(pass_bench),
        },
        "perturbation_min_ratio_gte_0_5": {
            "value": pert,
            "threshold": GATES["min_perturbed_sharpe_ratio"],
            "pass": bool(pass_pert),
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
    tr = prices.loc[train_mask, [SPY]]
    rows = []
    for lb in LOOKBACKS:
        for zw in Z_WINDOWS:
            for es in ENTRY_SCALES:
                for vt in VOL_TARGETS:
                    params = {"lookback": lb, "z_window": zw, "entry_scale": es, "vol_target": vt}
                    try:
                        sig = build_kre_signal(prices.loc[train_mask], **params)
                    except Exception:
                        continue
                    tr_rets = run_backtest(tr, sig, cfg).returns.fillna(0.0).values
                    fold_sh = []
                    for tr_i, te_i in walk_forward_splits(
                        len(tr_rets), n_splits=WF_FOLDS_SELECTION
                    ):
                        if len(te_i) < 30:
                            continue
                        fold_sh.append(float(sharpe_ratio(tr_rets[te_i])))
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
    tracker.start_experiment(EXPERIMENT_NAME, EXPERIMENT_DESC)
    try:
        tracker.log_params(
            {
                "hypothesis_id": "H107",
                "nf_id": "NF-20261106-16",
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
    sig = build_kre_signal(prices, **params)

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
        "nf_id": "NF-20261106-16",
        "hypothesis": "H107",
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
    tracker.finish_experiment(eval_out["verdict"])

    print(
        json.dumps(
            {
                "verdict": eval_out["verdict"],
                "passed": summary["passed_gates"],
                "experiment_id": exp_id,
                "selected": params,
                "oos_sharpe": oos_res.metrics.get("sharpe"),
                "oos_trades": oos_res.metrics.get("num_trades"),
                "oos_pf": oos_res.metrics.get("profit_factor"),
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
