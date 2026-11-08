"""NF-20261106-22 / H111 (pre-registered): SMH/QQQ semiconductor capex-cycle
leadership timing for SPY.

Mechanism: semiconductor relative strength (SMH, upstream AI/capex-sensitive
supply chain) vs broad Nasdaq-100 technology (QQQ) transmits technology
capex/infrastructure-cycle expectations into equity risk premia. When SMH
leads QQQ (capex cycle supported), maintain vol-targeted SPY exposure; when
SMH is abnormally weak vs QQQ (capex-cycle stress / semiconductor leadership
breakdown), reduce SPY exposure. This tests whether semiconductor capex-cycle
leadership provides a point-in-time timing signal for SPY, net of costs.

New family dimension (technology capex-cycle / innovation-supply-chain
leadership transmission), distinct from H110 (consumer demand-cycle via
XLY/XLP), H109 (energy supply-shock via XOP/XLE), H107 (bank intermediation
via KRE), H94/H108 (credit), H101 (HG/GC commodity growth ratio), H98 (oil RV
stress), H2/H16 (cross-sectional factor/momentum portfolio ranking), and
vol/rates/FX families.

Causality / timing (pre-registered): trailing SMH/QQQ ratio lookback-return
z-score for day t uses prices through close t only (trailing windows,
min_periods). Signals are shifted by 1 bar (engine signals.shift(1)); target
at close t earns return t -> t+1.

Data: yfinance daily SMH, QQQ, SPY adjusted close (free), 2010-01-01 ->
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

EXPERIMENT_NAME = "nf_20261106_22_smh_qqq_semicapex"
EXPERIMENT_DESC = (
    "NF-20261106-22/H111: SMH/QQQ semiconductor capex-cycle leadership "
    "timing SPY. Continuous vol-targeted long SPY exposure reduced when "
    "trailing SMH/QQQ ratio momentum z-score is abnormally weak (semiconductor "
    "capex-cycle stress), 1-bar delay. Train-only WF selection; Test protected; "
    "OOS gates."
)

SMH = "SMH"
QQQ = "QQQ"
SPY = "SPY"
UNIVERSE = [SMH, QQQ, SPY]

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


def build_smh_qqq_signal(
    prices: pd.DataFrame,
    lookback: int,
    z_window: int,
    entry_scale: float,
    vol_target: float,
) -> pd.DataFrame:
    if SMH not in prices.columns or QQQ not in prices.columns or SPY not in prices.columns:
        raise ValueError(f"Need {SMH}, {QQQ}, {SPY}")
    ratio = np.log(prices[SMH] / prices[QQQ])
    mom = ratio - ratio.shift(lookback)
    mu = mom.rolling(z_window, min_periods=z_window).mean()
    sd = mom.rolling(z_window, min_periods=z_window).std(ddof=0).replace(0.0, np.nan)
    z = ((mom - mu) / sd).fillna(0.0)
    # Semis weak vs QQQ (z <= -entry_scale) -> stress -> reduce exposure.
    stress = np.clip((-z - entry_scale) / entry_scale, 0.0, 1.0)
    calm = 1.0 - 0.5 * stress
    spy_ret = prices[SPY].pct_change()
    rv = spy_ret.rolling(21, min_periods=21).std() * np.sqrt(252)
    scale = (vol_target / rv).replace([np.inf, -np.inf], np.nan).clip(0.0, 1.5).fillna(0.0)
    pos = (scale * calm).clip(0.0, MAX_POS)
    warmup = max(lookback, z_window, 22)
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
        return {}
    s = pd.Series(returns)
    roll = s.rolling(window).mean() / (s.rolling(window).std(ddof=0) + 1e-12) * np.sqrt(252)
    valid = roll.dropna()
    if valid.empty:
        return {}
    low, high = valid.quantile(0.25), valid.quantile(0.75)
    return {
        "worst_quartile": float(valid[valid <= low].mean()),
        "best_quartile": float(valid[valid >= high].mean()),
        "min": float(valid.min()),
    }


def _perturbation(prices: pd.DataFrame, params: dict, cfg: BacktestConfig):
    base_sig = build_smh_qqq_signal(prices, **params)
    base = run_backtest(prices[[SPY]], base_sig, cfg).metrics["sharpe"]
    ratios = []
    for dlb in (-5, 5):
        for dzw in (-21, 21):
            for des in (-0.25, 0.25):
                lb = max(5, params["lookback"] + dlb)
                zw = max(63, params["z_window"] + dzw)
                es = max(0.25, params["entry_scale"] + des)
                sig = build_smh_qqq_signal(prices, lb, zw, es, params["vol_target"])
                sh = run_backtest(prices[[SPY]], sig, cfg).metrics["sharpe"]
                if base and not np.isnan(base) and base > 0:
                    ratios.append(float(sh / base))
    return {
        "base_sharpe": float(base),
        "min_ratio": float(min(ratios)) if ratios else 0.0,
        "mean_ratio": float(np.mean(ratios)) if ratios else 0.0,
        "n": len(ratios),
    }


def evaluate_gates(oos_result, train_result, bench_oos, prices, oos_mask, params, cfg) -> dict:
    m = oos_result.metrics
    oos_rets = oos_result.returns.fillna(0.0).values
    pf = _profit_factor(oos_rets)
    regime = _regime_sharpes(oos_rets)
    train_sh = train_result.metrics["sharpe"]
    oos_sh = m["sharpe"]
    if train_sh and not np.isnan(train_sh) and train_sh > 0:
        wf_stab = float(oos_sh / train_sh)
    else:
        wf_stab = 0.0
    cmp = compare_to_benchmark(oos_result.returns, bench_oos.returns)
    ir = cmp.get("information_ratio")
    ir = 0.0 if ir is None or (isinstance(ir, float) and np.isnan(ir)) else float(ir)
    pval = cmp.get("alpha_p_value")
    pval = 1.0 if pval is None or (isinstance(pval, float) and np.isnan(pval)) else float(pval)
    pert = _perturbation(prices.loc[oos_mask], params, cfg)
    pass_sh = bool(oos_sh >= GATES["min_sharpe"])
    pass_tr = bool(m["num_trades"] >= GATES["min_trades"])
    pass_pf = bool(pf >= GATES["min_profit_factor"])
    pass_dd = bool(abs(m["max_drawdown"]) <= GATES["max_drawdown"])
    pass_wf = bool(wf_stab >= GATES["min_walkforward_stability"])
    pass_reg = bool(regime.get("min", -9) >= GATES["min_worst_regime_sharpe"])
    pass_bench = bool((pval <= GATES["max_p_value"]) and (ir >= GATES["min_information_ratio"]))
    pass_pert = bool(pert["min_ratio"] >= GATES["min_perturbed_sharpe_ratio"])
    gates = {
        "oos_sharpe_gte_1_0": {"value": oos_sh, "threshold": GATES["min_sharpe"], "pass": pass_sh},
        "trades_gte_200": {
            "value": m["num_trades"],
            "threshold": GATES["min_trades"],
            "pass": pass_tr,
        },
        "profit_factor_gte_1_3": {
            "value": pf,
            "threshold": GATES["min_profit_factor"],
            "pass": pass_pf,
        },
        "max_drawdown_lte_15pct": {
            "value": abs(m["max_drawdown"]),
            "threshold": GATES["max_drawdown"],
            "pass": pass_dd,
        },
        "wf_stability_gte_0_7": {
            "value": wf_stab,
            "threshold": GATES["min_walkforward_stability"],
            "pass": pass_wf,
        },
        "worst_regime_sharpe_gte_0_3": {
            "value": regime,
            "threshold": GATES["min_worst_regime_sharpe"],
            "pass": pass_reg,
        },
        "benchmark_p_le_0_05_ir_ge_0": {
            "value": {"p_value": pval, "information_ratio": ir},
            "threshold": {"p": GATES["max_p_value"], "ir": GATES["min_information_ratio"]},
            "pass": bool(pass_bench),
        },
        "perturbation_min_ratio_gte_0_5": {
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
    tr = prices.loc[train_mask, [SPY]]
    rows = []
    for lb in LOOKBACKS:
        for zw in Z_WINDOWS:
            for es in ENTRY_SCALES:
                for vt in VOL_TARGETS:
                    params = {"lookback": lb, "z_window": zw, "entry_scale": es, "vol_target": vt}
                    try:
                        sig = build_smh_qqq_signal(prices.loc[train_mask], **params)
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
    tracker.start_experiment(EXPERIMENT_NAME, EXPERIMENT_DESC)
    try:
        tracker.log_params(
            {
                "hypothesis_id": "H111",
                "nf_id": "NF-20261106-22",
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
    sig = build_smh_qqq_signal(prices, **params)

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
        "nf_id": "NF-20261106-22",
        "hypothesis": "H111",
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
