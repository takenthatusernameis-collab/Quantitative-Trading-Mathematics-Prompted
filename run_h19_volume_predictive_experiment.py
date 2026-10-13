"""
H19: Volume-Predictive Return Decomposition.

Implements the pre-registered H19 hypothesis in HYPOTHESIS_SPEC.md:
decomposing daily volume into anticipated / unanticipated components
and trading directionally on the unanticipated (surprise) component.

Faithfulness notes:
  * Universe: SPY (primary, traded); QQQ/IWM (cross-validation);
    ^VIX (regime labels only).
  * Sample: 2009-01-01 → 2026-10-08 (~4,200 daily bars).
  * Splits: Train 2009-01-01 → 2014-12-31; Val 2015-01-01 → 2019-12-31;
    Test 2020-01-01 → 2026-10-08 (protected). OOS = Val+Test.
  * Signal (causal, 1-day lag): volume at close of day t sets position
    for the return from t → t+1.  All rolling statistics are shifted
    by 1 to exclude the current observation (no lookahead).
  * Grid: 3 decomposition methods × 3 threshold types = 9 combos;
    selection by Val Sharpe; Test protected.
  * Gates: unchanged PROMPT_V2 set + ±20% perturbation gate, on OOS.
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent / "src"))

from qtr.backtest.engine import (
    AssetClass,
    BacktestConfig,
    CostModel,
    run_backtest,
)
from qtr.data.fetcher import get_data_fetcher
from qtr.tracking.experiment import get_tracker
from qtr.validation.statistics import (
    compare_to_benchmark,
    sharpe_ratio,
    walk_forward_splits,
)

EXPERIMENT_NAME = "h19_volume_predictive"
EXPERIMENT_DESC = (
    "H19: Volume-predictive return decomposition "
    "(anticipated vs unanticipated volume surprise)"
)

# Symbols
SPY_SYMBOL = "SPY"
QQQ_SYMBOL = "QQQ"
IWM_SYMBOL = "IWM"
VIX_SYMBOL = "^VIX"

# Splits (pre-registered)
DATA_START = "2009-01-01"
DATA_END = "2026-10-08"
TRAIN_END = "2014-12-31"
VAL_END = "2019-12-31"

SEED = 42
INITIAL_CAPITAL = 1_000_000.0

LOOKBACK = 21
ADAPTIVE_Z_THRESHOLD = 0.5

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

# Grid
VOLUME_DECOMP_METHODS = ["simple_lagged", "vol_scaled", "price_volume_residual"]
THRESHOLD_TYPES = ["zero", "median", "adaptive"]

WF_FOLDS_STABILITY = 5


def regime_labels(vix_daily: pd.Series) -> pd.Series:
    """VIX regime labels: bull < 20, sideways 20-30, bear > 30."""
    regimes = pd.Series(index=vix_daily.index, dtype=object)
    vix_ff = vix_daily.ffill()
    regimes[vix_ff < 20] = "bull"
    regimes[(vix_ff >= 20) & (vix_ff <= 30)] = "sideways"
    regimes[vix_ff > 30] = "bear"
    return regimes


def build_targets(
    spy_close: pd.Series,
    spy_volume: pd.Series,
    volume_decomp_method: str,
    threshold_type: str,
    lookback: int = LOOKBACK,
    adaptive_z_threshold: float = ADAPTIVE_Z_THRESHOLD,
) -> pd.DataFrame:
    """
    Build daily target weights for SPY based on volume decomposition.

    Causal: all rolling statistics use .shift(1) to exclude the current
    day.  The engine applies signals.shift(1) internally, so a target
    set on date t earns the return of date t+1.

    Returns a DataFrame with column "SPY" containing weights in [0, 1].
    """
    vol = spy_volume.ffill()
    daily_ret = spy_close.pct_change()
    abs_ret = daily_ret.abs()

    # Lagged volume (exclude today)
    vol_lag = vol.shift(1)

    vol_mean = vol_lag.rolling(lookback).mean()
    vol_std = vol_lag.rolling(lookback).std()

    if volume_decomp_method == "simple_lagged":
        unanticipated = vol - vol_mean

    elif volume_decomp_method == "vol_scaled":
        # Z-score: (actual - expected) / expected_std
        # Guard against zero std
        unanticipated = (vol - vol_mean) / vol_std.replace(0.0, np.nan)

    elif volume_decomp_method == "price_volume_residual":
        # OLS regression of volume on |return| over rolling window of past data
        abs_ret_lag = abs_ret.shift(1)
        absret_mean = abs_ret_lag.rolling(lookback).mean()
        # Rolling covariance and variance (shifted to exclude current day)
        cov = (vol_lag * abs_ret_lag).rolling(lookback).mean() - vol_mean * absret_mean
        var = (abs_ret_lag**2).rolling(lookback).mean() - absret_mean**2
        beta = cov / var.replace(0.0, np.nan)
        alpha = vol_mean - beta * absret_mean
        # Expected volume at time t uses today's |r_t| (known at close)
        # but coefficients are estimated from past data only
        expected = alpha + beta * abs_ret
        unanticipated = vol - expected

    else:
        raise ValueError(f"Unknown volume_decomp_method: {volume_decomp_method}")

    # Threshold (computed on lagged unanticipated to avoid lookahead)
    unant_lag = unanticipated.shift(1)
    if threshold_type == "zero":
        threshold = 0.0
    elif threshold_type == "median":
        threshold = unant_lag.rolling(lookback).median()
    elif threshold_type == "adaptive":
        threshold = (
            unant_lag.rolling(lookback).mean()
            + adaptive_z_threshold * unant_lag.rolling(lookback).std()
        )
    else:
        raise ValueError(f"Unknown threshold_type: {threshold_type}")

    # Signal: long when unanticipated > threshold
    signal = (unanticipated > threshold).astype(float)

    targets = pd.DataFrame(index=spy_close.index)
    targets["SPY"] = signal.fillna(0.0)
    return targets


def _splits(prices_idx: pd.Index):
    train_mask = prices_idx <= pd.Timestamp(TRAIN_END)
    val_mask = (prices_idx > pd.Timestamp(TRAIN_END)) & (
        prices_idx <= pd.Timestamp(VAL_END)
    )
    test_mask = prices_idx > pd.Timestamp(VAL_END)
    return train_mask, val_mask, test_mask


def _count_in(trades: pd.DataFrame, mask, prices) -> int:
    if trades is None or len(trades) == 0:
        return 0
    ts = pd.to_datetime(trades["timestamp"])
    lo = prices.index[mask].min()
    hi = prices.index[mask].max()
    return int(((ts >= lo) & (ts <= hi)).sum())


def _period_metrics(ret: pd.Series, n_trades: int) -> dict:
    r = ret.dropna()
    if len(r) > 1:
        sr = float(sharpe_ratio(r.values))
    else:
        sr = 0.0
    cum = (1 + r).cumprod()
    dd = float((cum / cum.cummax() - 1.0).min()) if len(cum) > 0 else 0.0
    gp = float(r[r > 0].sum())
    gl = float(abs(r[r < 0].sum()))
    pf = gp / gl if gl > 0 else float("inf")
    return {
        "sharpe": sr,
        "max_drawdown": dd,
        "profit_factor": pf,
        "trades": int(n_trades),
        "gross_profit": gp,
        "gross_loss": gl,
        "n_periods": len(r),
    }


def full_gate_eval(
    result,
    oos_mask,
    val_mask,
    test_mask,
    prices,
    vix,
    bench_result,
):
    """The 9 pre-registered gates on OOS (Val+Test)."""
    prices_idx = prices.index

    train_mask = prices_idx <= pd.Timestamp(TRAIN_END)

    oos_ret = result.returns[oos_mask]
    test_ret = result.returns[test_mask]
    _ = result.equity_curve[oos_mask]  # accessed for potential future use
    n_oos_trades = _count_in(result.trades, oos_mask, prices)

    oos_m = _period_metrics(oos_ret, n_oos_trades)
    test_m = _period_metrics(test_ret, _count_in(result.trades, test_mask, prices))

    # Walk-forward stability (full series)
    wf_splits = walk_forward_splits(len(result.returns), n_splits=WF_FOLDS_STABILITY)
    oos_sharpes, train_sharpes = [], []
    for tr_idx, te_idx in wf_splits:
        tr_r = result.returns.iloc[tr_idx].dropna()
        te_r = result.returns.iloc[te_idx].dropna()
        if len(te_r) > 1:
            oos_sharpes.append(sharpe_ratio(te_r.values))
        if len(tr_r) > 1:
            train_sharpes.append(sharpe_ratio(tr_r.values))
    wf_stab = (
        float(np.mean(oos_sharpes) / np.mean(train_sharpes))
        if np.mean(train_sharpes) != 0
        else 0.0
    )

    # Regime sharpes on the OOS window
    regimes = regime_labels(vix.reindex(prices_idx))[oos_mask]
    oos_ret_r = oos_ret
    regime_sharpes = {}
    worst = np.inf
    for reg in ["bull", "sideways", "bear"]:
        m = regimes == reg
        r = oos_ret_r[m] if len(m) == len(oos_ret_r) else oos_ret_r.iloc[m.values]
        if len(r) > 1 and r.std() > 0:
            s = float(sharpe_ratio(r.values))
        else:
            s = 0.0
        regime_sharpes[reg] = s
        worst = min(worst, s)

    bench = compare_to_benchmark(
        oos_ret.dropna().values,
        bench_result.returns[oos_mask].dropna().values,
    )
    passes = {
        "sharpe": oos_m["sharpe"] >= GATES["min_sharpe"],
        "trades": oos_m["trades"] >= GATES["min_trades"],
        "pf": oos_m["profit_factor"] >= GATES["min_profit_factor"],
        "dd": abs(oos_m["max_drawdown"]) <= GATES["max_drawdown"]
        if oos_m["max_drawdown"] < 0
        else False,
        "stab": wf_stab >= GATES["min_walkforward_stability"],
        "worst": worst >= GATES["min_worst_regime_sharpe"]
        if worst != np.inf
        else False,
        "p": float(bench.get("alpha_p_value", 1.0)) < GATES["max_p_value"],
        "ir": float(bench.get("information_ratio", -np.inf))
        > GATES["min_information_ratio"],
    }
    all_pass = all(passes.values())
    return {
        "oos_metrics": oos_m,
        "test_metrics": test_m,
        "train_sharpe": float(sharpe_ratio(result.returns[train_mask].dropna().values))
        if train_mask.sum() > 1
        else 0.0,
        "val_sharpe": float(sharpe_ratio(result.returns[val_mask].dropna().values))
        if val_mask.sum() > 1
        else 0.0,
        "wf_stability": float(wf_stab),
        "worst_regime_sharpe": float(worst) if worst != np.inf else 0.0,
        "regime_sharpes": regime_sharpes,
        "benchmark_p_value": float(bench.get("alpha_p_value", 1.0)),
        "information_ratio": float(bench.get("information_ratio", -np.inf)),
        "benchmark_alpha_annual": float(bench.get("alpha_annualized", 0.0)),
        "passes": passes,
        "all_pass": all_pass,
        "verdict": "PASS" if all_pass else "REJECT",
    }


def perturbation_eval(
    selected: dict,
    prices: pd.DataFrame,
    spy_volume: pd.Series,
    vix: pd.Series,
    oos_mask,
    cfg,
    opt_oos_sharpe: float,
):
    """OAT +/-20% perturbation of the lookback window and (if adaptive)
    the z-score threshold."""
    variants = {}
    lookback_base = selected["lookback"]
    params = {"lookback": lookback_base}
    if selected.get("threshold_type") == "adaptive":
        params["adaptive_z_threshold"] = selected.get(
            "adaptive_z_threshold", ADAPTIVE_Z_THRESHOLD
        )

    for param, base in params.items():
        for factor in (0.8, 1.2):
            v = base * factor
            if param == "lookback":
                v = max(2, round(v))
            elif param == "adaptive_z_threshold":
                v = round(v, 4)
            if v == base:
                continue
            kw = dict(selected)
            kw[param] = v
            targets = build_targets(
                prices["SPY"],
                spy_volume,
                kw["volume_decomp_method"],
                kw["threshold_type"],
                kw["lookback"],
                kw.get("adaptive_z_threshold", ADAPTIVE_Z_THRESHOLD),
            )
            res = run_backtest(prices=prices, signals=targets, config=cfg)
            r = res.returns[oos_mask].dropna()
            variants[f"{param}={v}"] = (
                float(sharpe_ratio(r.values)) if len(r) > 1 else 0.0
            )
    if opt_oos_sharpe > 0:
        min_ratio = float(min(variants.values()) / opt_oos_sharpe) if variants else 0.0
    else:
        min_ratio = 0.0
    return {"variants": variants, "min_perturbed_sharpe_ratio": min_ratio}


def make_config() -> BacktestConfig:
    return BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        cost_model=CostModel(),
        asset_class=AssetClass.EQUITY,
        max_position_size=1.0,
        max_leverage=1.0,
        allow_short=False,
    )


def main():
    np.random.seed(SEED)
    t_start = time.time()
    tracker = get_tracker()
    grid_size = len(VOLUME_DECOMP_METHODS) * len(THRESHOLD_TYPES)
    exp_id = tracker.start_experiment(
        name=EXPERIMENT_NAME,
        description=EXPERIMENT_DESC,
        config={
            "universe": [SPY_SYMBOL],
            "cross_validation": [QQQ_SYMBOL, IWM_SYMBOL],
            "regime_labels": VIX_SYMBOL,
            "interval": "1d",
            "data_start": DATA_START,
            "data_end": DATA_END,
            "splits": {
                "train": ["2009-01-01", TRAIN_END],
                "val": ["2015-01-01", VAL_END],
                "test": ["2020-01-01", DATA_END],
            },
            "gates": GATES,
            "seed": SEED,
            "grid": {
                "volume_decomp_method": VOLUME_DECOMP_METHODS,
                "threshold_type": THRESHOLD_TYPES,
            },
            "grid_size": grid_size,
            "selection": "argmax Val Sharpe; Test 2020-2026 protected (never used for selection); gates on OOS Val+Test",
            "lookback": LOOKBACK,
            "adaptive_z_threshold": ADAPTIVE_Z_THRESHOLD,
        },
        data_sources={
            "source": "yahoo_daily_cached",
            "symbols": [SPY_SYMBOL, QQQ_SYMBOL, IWM_SYMBOL, VIX_SYMBOL],
            "interval": "1d",
        },
        compute_budget={"max_cpu_hours": 2.0, "grid_size": grid_size},
        random_seeds={"numpy": SEED, "python": SEED},
    )
    print(f"[H19] started {exp_id}  grid_size={grid_size}")

    try:
        fetcher = get_data_fetcher()
        data = fetcher.fetch_yahoo(
            [SPY_SYMBOL, QQQ_SYMBOL, IWM_SYMBOL, VIX_SYMBOL],
            start=DATA_START,
            end=DATA_END,
            interval="1d",
        )
        spy_df = data.get(SPY_SYMBOL, pd.DataFrame())
        if spy_df.empty:
            raise RuntimeError(f"no data for {SPY_SYMBOL}")

        # Align all series to SPY trading days
        common = spy_df.index
        spy_close = spy_df["close"]
        spy_volume = spy_df["volume"]
        qqq_close = (
            data.get(QQQ_SYMBOL, pd.DataFrame())
            .get("close", pd.Series(index=common))
            .reindex(common)
        )
        iwm_close = (
            data.get(IWM_SYMBOL, pd.DataFrame())
            .get("close", pd.Series(index=common))
            .reindex(common)
        )
        vix = (
            data.get(VIX_SYMBOL, pd.DataFrame())
            .get("close", pd.Series(index=common))
            .reindex(common)
        )

        # Backtest price frame: SPY only
        prices = pd.DataFrame({"SPY": spy_close.values}, index=common)
        volumes = pd.DataFrame({"SPY": spy_volume.values}, index=common)

        train_mask, val_mask, test_mask = _splits(prices.index)
        oos_mask = ~train_mask
        print(
            f"[H19] prices={prices.shape} train/val/test="
            f"{int(train_mask.sum())}/{int(val_mask.sum())}/{int(test_mask.sum())}"
        )

        cfg = make_config()

        # Benchmark: buy-and-hold SPY
        bench_signals = pd.DataFrame({"SPY": 1.0}, index=prices.index)
        bench_result = run_backtest(prices=prices, signals=bench_signals, config=cfg)

        # --- 9-combo grid: selection on Val Sharpe ---
        grid_rows = []
        grid_results = {}
        t_grid = time.time()
        for method in VOLUME_DECOMP_METHODS:
            for threshold_type in THRESHOLD_TYPES:
                combo_name = f"{method}_{threshold_type}"
                print(f"  Testing {combo_name}...")

                targets = build_targets(
                    spy_close,
                    spy_volume,
                    method,
                    threshold_type,
                    lookback=LOOKBACK,
                    adaptive_z_threshold=ADAPTIVE_Z_THRESHOLD,
                )
                res = run_backtest(prices=prices, signals=targets, config=cfg)

                train_r = res.returns[train_mask].dropna()
                train_sr = (
                    float(sharpe_ratio(train_r.values)) if len(train_r) > 1 else 0.0
                )
                val_r = res.returns[val_mask].dropna()
                val_sr = float(sharpe_ratio(val_r.values)) if len(val_r) > 1 else 0.0
                test_r = res.returns[test_mask].dropna()
                test_sr = float(sharpe_ratio(test_r.values)) if len(test_r) > 1 else 0.0
                oos_r = res.returns[oos_mask].dropna()
                oos_sr = float(sharpe_ratio(oos_r.values)) if len(oos_r) > 1 else 0.0

                grid_results[(method, threshold_type)] = res
                grid_rows.append(
                    {
                        "volume_decomp_method": method,
                        "threshold_type": threshold_type,
                        "combo_name": combo_name,
                        "lookback": LOOKBACK,
                        "adaptive_z_threshold": ADAPTIVE_Z_THRESHOLD
                        if threshold_type == "adaptive"
                        else None,
                        "train_sharpe": train_sr,
                        "val_sharpe": val_sr,
                        "test_sharpe": test_sr,
                        "oos_sharpe": oos_sr,
                    }
                )
        grid_df = pd.DataFrame(grid_rows).sort_values("val_sharpe", ascending=False)
        grid_elapsed = time.time() - t_grid
        print(
            f"[H19] grid {len(grid_rows)} combos in {grid_elapsed:.1f}s; "
            f"best val Sharpe={grid_df.iloc[0]['val_sharpe']:.4f}"
        )

        # --- selection: best Val Sharpe (Test never used) ---
        best_row = grid_df.iloc[0]
        sel_key = (best_row["volume_decomp_method"], best_row["threshold_type"])
        sel_result = grid_results[sel_key]
        selected = {
            "volume_decomp_method": sel_key[0],
            "threshold_type": sel_key[1],
            "lookback": LOOKBACK,
            "adaptive_z_threshold": ADAPTIVE_Z_THRESHOLD
            if sel_key[1] == "adaptive"
            else None,
        }

        # --- full gate evaluation on protected OOS (Val+Test) ---
        gate = full_gate_eval(
            sel_result, oos_mask, val_mask, test_mask, prices, vix, bench_result
        )

        # --- perturbation gate (OAT +/-20%) ---
        pert = perturbation_eval(
            selected,
            prices,
            spy_volume,
            vix,
            oos_mask,
            cfg,
            gate["oos_metrics"]["sharpe"],
        )
        gate["passes"]["perturbation"] = (
            pert["min_perturbed_sharpe_ratio"] >= GATES["min_perturbed_sharpe_ratio"]
        )
        gate["perturbation"] = pert
        gate["all_pass"] = all(gate["passes"].values())
        gate["verdict"] = "PASS" if gate["all_pass"] else "REJECT"

        # --- ablations (OOS) ---
        ablations = {}
        # (a) BH SPY (already computed as bench_result)
        ablations["bh_spy"] = {
            "oos_metrics": _period_metrics(
                bench_result.returns[oos_mask],
                _count_in(bench_result.trades, oos_mask, prices),
            ),
        }
        # (b) random volume-based signal (shuffle volume, recompute signal)
        rng = np.random.RandomState(SEED)
        shuffled_vol = pd.Series(
            rng.permutation(spy_volume.values), index=spy_volume.index
        )
        random_targets = build_targets(
            spy_close,
            shuffled_vol,
            selected["volume_decomp_method"],
            selected["threshold_type"],
            lookback=LOOKBACK,
            adaptive_z_threshold=ADAPTIVE_Z_THRESHOLD,
        )
        random_res = run_backtest(prices=prices, signals=random_targets, config=cfg)
        ablations["random_volume_signal"] = {
            "oos_metrics": _period_metrics(
                random_res.returns[oos_mask],
                _count_in(random_res.trades, oos_mask, prices),
            ),
        }
        # (c) constant 0.5 position
        const_signals = pd.DataFrame({"SPY": 0.5}, index=prices.index)
        const_res = run_backtest(prices=prices, signals=const_signals, config=cfg)
        ablations["constant_0.5_position"] = {
            "oos_metrics": _period_metrics(
                const_res.returns[oos_mask],
                _count_in(const_res.trades, oos_mask, prices),
            ),
        }

        # --- cross-validation on QQQ/IWM (same signal, different returns) ---
        sel_targets = build_targets(
            spy_close,
            spy_volume,
            selected["volume_decomp_method"],
            selected["threshold_type"],
            lookback=selected["lookback"],
            adaptive_z_threshold=selected.get("adaptive_z_threshold")
            or ADAPTIVE_Z_THRESHOLD,
        )
        cross_val = {}
        for sym, close_cv in [("QQQ", qqq_close), ("IWM", iwm_close)]:
            if close_cv.isna().all():
                continue
            cv_ret = close_cv.pct_change()[oos_mask].dropna()
            if len(cv_ret) > 1:
                cv_sr = float(sharpe_ratio(cv_ret.values))
            else:
                cv_sr = 0.0
            # Apply the selected SPY signal to the cross-val asset returns
            sig_oos = sel_targets["SPY"][oos_mask]
            cv_oos_ret = (
                (sig_oos.shift(1) * close_cv.pct_change())
                .reindex(cv_ret.index)
                .dropna()
            )
            if len(cv_oos_ret) > 1:
                cv_strat_sr = float(sharpe_ratio(cv_oos_ret.values))
            else:
                cv_strat_sr = 0.0
            cross_val[sym] = {
                "bh_sharpe": cv_sr,
                "signal_sharpe": cv_strat_sr,
            }

        # --- artifacts ---
        tracker.log_dataframe("prices", prices)
        tracker.log_dataframe("volumes", volumes)
        tracker.log_dataframe("vix_close", vix.rename("close").to_frame())
        tracker.log_dataframe("param_grid_results", grid_df)
        tracker.log_dataframe("selected_signals", sel_result.positions)
        tracker.log_dataframe("best_equity", sel_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("best_trades", sel_result.trades)
        tracker.log_dataframe(
            "benchmark_equity", bench_result.equity_curve.to_frame("equity")
        )
        tracker.log_dataframe(
            "benchmark_returns", bench_result.returns.to_frame("returns")
        )
        for name, ab in ablations.items():
            tracker.log_metrics(
                {f"ablation_{name}_oos_sharpe": ab["oos_metrics"]["sharpe"]}
            )

        total_elapsed = time.time() - t_start
        summary = {
            "experiment_id": exp_id,
            "hypothesis": "H19",
            "selected_config": selected,
            "selection_rule": (
                "argmax Val Sharpe; Test 2020-2026 protected (never used for selection); "
                "gates on OOS Val+Test"
            ),
            "grid_size": grid_size,
            "n_evaluated": len(grid_rows),
            "grid_elapsed_sec": float(round(grid_elapsed, 1)),
            "total_elapsed_sec": float(round(total_elapsed, 1)),
            "compute_cpu_hours": float(round(total_elapsed / 3600, 3)),
            "lookback": LOOKBACK,
            "adaptive_z_threshold": ADAPTIVE_Z_THRESHOLD,
            "metrics": {
                "train_sharpe": gate["train_sharpe"],
                "val_sharpe": gate["val_sharpe"],
                "test_sharpe": gate["test_metrics"]["sharpe"],
                "oos_sharpe": gate["oos_metrics"]["sharpe"],
                "profit_factor": gate["oos_metrics"]["profit_factor"],
                "max_drawdown": gate["oos_metrics"]["max_drawdown"],
                "trades": gate["oos_metrics"]["trades"],
                "wf_stability": gate["wf_stability"],
                "worst_regime_sharpe": gate["worst_regime_sharpe"],
                "regime_sharpes": gate["regime_sharpes"],
                "benchmark_p_value": gate["benchmark_p_value"],
                "information_ratio": gate["information_ratio"],
                "benchmark_alpha_annual": gate["benchmark_alpha_annual"],
                "perturbation": pert,
                "ablations": ablations,
                "cross_validation": cross_val,
            },
            "passes": gate["passes"],
            "all_pass": gate["all_pass"],
            "verdict": gate["verdict"],
        }

        exp_dir = Path(tracker.log_dir) / "artifacts" / exp_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        with open(exp_dir / "summary.json", "w") as f:
            json.dump(
                summary,
                f,
                indent=2,
                default=lambda x: (
                    float(x) if isinstance(x, (np.integer, np.floating)) else str(x)
                ),
            )
        tracker.log_artifact("summary", exp_dir / "summary.json")

        # Save metadata
        end_time = time.time()
        metadata = {
            "run_id": exp_id,
            "script": "run_h19_volume_predictive_experiment.py",
            "start_time": t_start,
            "end_time": end_time,
            "duration_seconds": end_time - t_start,
            "duration_cpu_hours": (end_time - t_start) / 3600.0,
            "timestamp_start": pd.Timestamp.fromtimestamp(t_start).isoformat(),
            "timestamp_end": pd.Timestamp.fromtimestamp(end_time).isoformat(),
        }
        metadata_path = exp_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)
        tracker.log_artifact("metadata", metadata_path)

        tracker.finish_experiment(status="completed")

        print("\n" + "=" * 72)
        p = gate["passes"]
        print(f"  gates passed: {int(sum(p.values()))}/{len(p)}  ->  {gate['verdict']}")
        print(
            f"  sharpe={p['sharpe']} trades={p['trades']} pf={p['pf']} "
            f"dd={p['dd']} stab={p['stab']} worst={p['worst']} "
            f"p={p['p']} ir={p['ir']} perturb={p['perturbation']}"
        )
        om = gate["oos_metrics"]
        print(
            f"  OOS Sharpe={om['sharpe']:.3f} PF={om['profit_factor']:.3f} "
            f"DD={om['max_drawdown']:.3f} Trades={om['trades']}"
        )
        print(
            f"  Train={gate['train_sharpe']:.3f} Val={gate['val_sharpe']:.3f} "
            f"Test={gate['test_metrics']['sharpe']:.3f} | "
            f"WF stab={gate['wf_stability']:.3f} | worst-regime={gate['worst_regime_sharpe']:.3f}"
        )
        print(
            f"  Benchmark: p={gate['benchmark_p_value']:.4f} IR={gate['information_ratio']:.3f}"
        )
        print(f"  Perturbation min ratio={pert['min_perturbed_sharpe_ratio']:.3f}")
        print(f"  Selected: {selected}")
        print(
            f"  Grid {len(grid_rows)} combos in {grid_elapsed:.1f}s | "
            f"total {total_elapsed / 60:.1f} min ({total_elapsed / 3600:.2f} CPU-h)"
        )
        print("=" * 72)
        return 0 if gate["all_pass"] else 1
    except Exception as e:  # broad catch for experiment-level error reporting  # noqa: BLE001
        import traceback

        traceback.print_exc()
        tracker.finish_experiment(status="failed", error=str(e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
