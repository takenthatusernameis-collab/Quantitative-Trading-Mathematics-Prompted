#!/usr/bin/env python3
"""
Time-Series Momentum experiment on 20 liquid ETFs (Phase 3 -> 4 -> 5 executable).

Implements the hypothesis from HYPOTHESIS_SPEC.md (H1) using the vol-scaled
time-series momentum mechanism of Moskowitz, Ooi & Pedersen (2012) with
volatility scaling per Kim, Liew & Moulang (2016).

Design (pre-registered, no test-set feedback):
  * Universe: 20 liquid ETFs across 5 asset classes (+ ^VIX for regime labels).
  * Splits: Train 2015-2019, Val 2020-2021, Test 2022-2024 (protected).
  * Signal: 12-month (252-day) / 1-month (21-day) TSMOM, skip-period to avoid
    short-horizon reversal, volatility-scaled to 15% annual target, monthly
    rebalance (signals resampled to month-end, then ffilled).
  * Parameter selection: grid over (lookback, skip, long_only) scored by
    *internal* walk-forward Sharpe on the TRAIN period only. Best combo applied
    fixed to Val + Test. Test is never used for selection.
  * Evidence gates applied to pooled OOS (Val + Test):
      - Net OOS Sharpe >= 1.0 (PROMPT_V2 acceptance criterion)
      - >= 200 pooled OOS trades
      - Profit factor >= 1.3
      - Max drawdown <= 15%
      - Walk-forward stability (OOS >= 0.7 x train Sharpe)
      - Parameter perturbation (+/-20%) OOS Sharpe >= 0.5 x optimum
      - Worst regime Sharpe >= 0.3 (VIX bull/sideways/bear)
      - p < 0.05 vs equal-weight benchmark (bootstrap t-test on daily alpha)

Realistic equity cost model: 1 bp commission + 1 bp spread + 0.1 bp per 1% ADV.
No live trading. No API keys. Data: Yahoo Finance (cached).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from qtr.backtest.engine import AssetClass, BacktestConfig, run_backtest
from qtr.data.fetcher import get_data_fetcher
from qtr.strategies import run_strategy
from qtr.tracking.experiment import get_tracker
from qtr.validation.statistics import (
    benchmark_significance_gate,
    bootstrap_confidence_interval,
    compare_to_benchmark,
    multiple_testing_correction,
    sharpe_ratio,
    sharpe_ratio_ci,
    walk_forward_splits,
)

# ============================================================
# PRE-REGISTERED CONFIGURATION (frozen before results seen)
# ============================================================
UNIVERSE = [
    # Equities (6)
    "SPY",
    "QQQ",
    "IWM",
    "EFA",
    "EEM",
    "VWO",
    # Bonds (3)
    "TLT",
    "AGG",
    "HYG",
    # Commodities (4)
    "GLD",
    "USO",
    "PDBC",
    "GSG",
    # Currencies (3)
    "UUP",
    "FXE",
    "FXY",
    # International / Real Estate (4)
    "VNQ",
    "EWJ",
    "EWZ",
    "INDA",
]
VIX_SYMBOL = "^VIX"

START_DATE = "2015-01-01"
END_DATE = "2024-12-31"

TRAIN_END = "2019-12-31"
VAL_END = "2021-12-31"  # Test = 2022-2024 (protected holdout)

# Parameter grid for selection
LOOKBACKS = [63, 126, 252]  # ~1M, 6M, 12M
SKIPS = [1, 5, 21]  # 1d, 1w, 1m skip to avoid reversal
LONG_ONLY_CHOICES = [True, False]
TARGET_VOL = 0.15  # annualized vol target (Kim et al. 2016)

# Evidence gates (union of PROMPT_V2 + HYPOTHESIS_SPEC; stricter wins)
GATES = {
    "min_sharpe": 1.0,
    "min_trades": 200,
    "min_profit_factor": 1.3,
    "max_drawdown": 0.15,
    "min_walkforward_stability": 0.7,
    "min_perturbed_sharpe_ratio": 0.5,  # OOS Sharpe >= 0.5 x optimum under +/-20%
    "min_worst_regime_sharpe": 0.3,
    "max_p_value": 0.05,
    "alpha_multiple_testing": "benjamini_hochberg",
}

SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_LEVERAGE = (
    5.0  # headroom; portfolio-level vol targeting sets scale (engine won't bind)
)
MAX_POSITION_SIZE = 2.0  # per-asset cap enforced both here and in the engine

COST_MODEL = {
    "equity_commission_bps": 1.0,
    "equity_spread_bps": 1.0,
    "equity_impact_bps_per_pct_adv": 0.1,
}

EXPERIMENT_NAME = "ts_momentum_20etf_v1"
EXPERIMENT_DESC = (
    "Volatility-scaled time-series momentum (Moskowitz Ooi Pedersen 2012; "
    "Kim Liew Moulang 2016) on 20 liquid ETFs across 5 asset classes. "
    "Train 2015-2019, Val 2020-2021, Test 2022-2024 protected. "
    "Grid selection on TRAIN walk-forward only; gates on pooled Val+Test OOS."
)


# ============================================================
# HELPERS
# ============================================================
def split_returns_by_date(returns: pd.Series):
    """Split a return series by the pre-registered date boundaries."""
    train = returns[returns.index <= TRAIN_END]
    val = returns[(returns.index > TRAIN_END) & (returns.index <= VAL_END)]
    test = returns[returns.index > VAL_END]
    oos = returns[returns.index > TRAIN_END]  # Val + Test pooled OOS
    return train, val, test, oos


def make_config(allow_short: bool) -> BacktestConfig:
    cfg = BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        asset_class=AssetClass.EQUITY,
        max_position_size=MAX_POSITION_SIZE,
        max_leverage=MAX_LEVERAGE,
        allow_short=allow_short,
    )
    cfg.cost_model.equity_commission_bps = COST_MODEL["equity_commission_bps"]
    cfg.cost_model.equity_spread_bps = COST_MODEL["equity_spread_bps"]
    cfg.cost_model.equity_impact_bps_per_pct_adv = COST_MODEL[
        "equity_impact_bps_per_pct_adv"
    ]
    return cfg


def resample_monthly_signals(signals: pd.DataFrame) -> pd.DataFrame:
    """Resample daily signals to month-end rebalancing (ffill within month).

    Month-end value is taken, then forward filled. This is the standard TSMOM
    rebalancing cadence and prevents look-ahead (each month uses only data
    available at month-end).
    """
    monthly = signals.resample("ME").last()
    # Reindex onto the business-day index of the prices via ffill
    full_index = signals.index
    monthly = monthly.reindex(full_index, method="ffill").fillna(0)
    return monthly


def vol_scaled_tsmom_signals(
    prices: pd.DataFrame,
    lookback: int = 252,
    skip: int = 21,
    long_only: bool = True,
    target_vol: float = 0.15,
    vol_window: int = 63,
) -> pd.DataFrame:
    """Faithful AQR/Moskowitz-style volatility-scaled time-series momentum.

    1. Direction: sign(pct_change(lookback).shift(skip))  -- lookahead-safe.
    2. Risk-parity weighting: w_i_raw = direction_i / sigma_i  (inverse vol).
    3. Portfolio-level volatility targeting: scale the whole book so realized
       portfolio vol ~ target_vol (linear in scale). This is the correct
       multi-asset generalisation of Kim, Liew & Moulang (2016) vol-scaling,
       unlike per-asset scaling which would over-lever a 20-asset book.
    4. Per-asset cap at +/- MAX_POSITION_SIZE.

    All scaling uses only data available at time t (rolling windows, shift).
    """
    pct = prices.pct_change()
    # Momentum = 12-month return, shifted by skip months to avoid short-horizon
    # reversal (Moskowitz, Ooi & Pedersen 2012).
    mom = prices.pct_change(lookback).shift(skip)
    if long_only:
        direction = (mom > 0).astype(float)
    else:
        direction = (mom > 0).astype(float) * 2.0 - 1.0
        direction = direction.where(mom.notna(), 0.0)

    sigma = pct.rolling(vol_window).std() * np.sqrt(252)
    sigma = sigma.replace(0, np.nan).ffill()
    inv_vol = 1.0 / sigma

    w_raw = direction * inv_vol
    w_raw = w_raw.replace([np.inf, -np.inf], np.nan).ffill().fillna(0.0)

    # Portfolio-level vol targeting (scale is linear in portfolio vol).
    # Upper cap limits over-leverage in low-vol regimes; lower bound is ~0 so
    # exposure is genuinely reduced during volatility spikes (the whole point of
    # vol targeting). A fixed non-zero floor would *inflate* crisis exposure.
    port_ret = (w_raw.shift(1) * pct).sum(axis=1).ffill()
    port_vol = port_ret.rolling(vol_window).std() * np.sqrt(252)
    port_vol = port_vol.replace(0, np.nan)
    scale = (target_vol / port_vol).clip(lower=0.0, upper=3.0)
    scale = scale.ffill().fillna(0.0)
    weights = w_raw.multiply(scale, axis=0)

    # Per-asset cap (also enforced by the engine).
    weights = weights.clip(-MAX_POSITION_SIZE, MAX_POSITION_SIZE)
    return weights.ffill().fillna(0.0)


def evaluate_combo(prices, volumes, adv, allow_short, lookback, skip):
    """Run a single param combo over the full price series (no lookahead bias).

    Returns the BacktestResult and the (monthly, resampled) signal DataFrame.
    """
    cfg = make_config(allow_short)
    long_only = not allow_short
    sig = vol_scaled_tsmom_signals(
        prices,
        lookback=lookback,
        skip=skip,
        long_only=long_only,
        target_vol=TARGET_VOL,
    )
    sig_monthly = resample_monthly_signals(sig)
    result = run_backtest(
        prices=prices,
        signals=sig_monthly,
        volumes=volumes,
        adv=adv,
        config=cfg,
    )
    return result, sig_monthly


def selection_metric(train_returns, fold_sharpes):
    """Mean walk-forward OOS Sharpe on train (primary selection metric)."""
    return float(np.mean(fold_sharpes)) if len(fold_sharpes) else -np.inf


def wf_oos_sharpes(train_returns, n_splits=4):
    """Internal walk-forward OOS Sharpe per fold on the train period."""
    train_vals = train_returns.values
    folds = walk_forward_splits(len(train_vals), n_splits=n_splits)
    sharpes = []
    for tr_idx, te_idx in folds:
        te_vals = train_vals[te_idx]
        if len(te_vals) > 1 and te_vals.std() > 0:
            sharpes.append(sharpe_ratio(te_vals))
    return sharpes


def regime_labels(vix_daily: pd.Series) -> pd.Series:
    """VIX-based regime labels aligned to daily index."""
    regimes = pd.Series(index=vix_daily.index, dtype=object)
    vix_ff = vix_daily.ffill()
    regimes[vix_ff < 20] = "bull"
    regimes[(vix_ff >= 20) & (vix_ff <= 30)] = "sideways"
    regimes[vix_ff > 30] = "bear"
    return regimes


# ============================================================
# MAIN
# ============================================================
def main():
    np.random.seed(SEED)

    tracker = get_tracker()
    exp_id = tracker.start_experiment(
        name=EXPERIMENT_NAME,
        description=EXPERIMENT_DESC,
        config={
            "universe": UNIVERSE,
            "vix_symbol": VIX_SYMBOL,
            "start_date": START_DATE,
            "end_date": END_DATE,
            "data_splits": {
                "train_end": TRAIN_END,
                "val_end": VAL_END,
                "test_start": VAL_END.replace("-12-31", "-01-01"),
            },
            "target_lookbacks": LOOKBACKS,
            "target_skips": SKIPS,
            "long_only_choices": LONG_ONLY_CHOICES,
            "target_vol": TARGET_VOL,
            "max_leverage": MAX_LEVERAGE,
            "max_position_size": MAX_POSITION_SIZE,
            "cost_model": COST_MODEL,
            "gates": GATES,
            "random_seeds": {"numpy": SEED, "python": SEED},
            "compute_budget": {"max_cpu_hours": 2.0},
        },
        data_sources={
            "source": "yahoo",
            "symbols": UNIVERSE + [VIX_SYMBOL],
            "start": START_DATE,
            "end": END_DATE,
            "interval": "1d",
        },
        compute_budget={"max_cpu_hours": 2.0},
        random_seeds={"numpy": SEED, "python": SEED},
    )
    print(f"Started experiment: {exp_id}")

    try:
        # ------------------------------------------------------------
        # 1. FETCH DATA
        # ------------------------------------------------------------
        print("Fetching data...")
        fetcher = get_data_fetcher()
        raw = fetcher.fetch_yahoo(
            symbols=UNIVERSE + [VIX_SYMBOL],
            start=START_DATE,
            end=END_DATE,
            interval="1d",
            use_cache=True,
        )

        prices = pd.DataFrame()
        volumes = pd.DataFrame()
        for sym in UNIVERSE:
            df = raw.get(sym)
            if df is None or df.empty or "close" not in df.columns:
                print(f"  WARN: no data for {sym}, dropping")
                continue
            prices[sym] = df["close"]
            if "volume" in df.columns:
                volumes[sym] = df["volume"]

        prices = prices.ffill().dropna(how="all")
        volumes = volumes.reindex(prices.index).ffill().fillna(0)
        # Drop any asset that failed entirely
        valid_assets = prices.columns[prices.notna().any(axis=0)].tolist()
        prices = prices[valid_assets]
        volumes = volumes[valid_assets]
        print(
            f"Loaded {len(prices.columns)} traded assets x {len(prices)} days "
            f"({prices.index[0].date()} -> {prices.index[-1].date()})"
        )

        vix_df = raw.get(VIX_SYMBOL)
        vix = (
            vix_df["close"]
            if (vix_df is not None and not vix_df.empty and "close" in vix_df.columns)
            else pd.Series(np.nan, index=prices.index)
        )
        vix = vix.reindex(prices.index).ffill()

        tracker.log_dataframe("prices", prices)
        tracker.log_dataframe("volumes", volumes)
        tracker.log_dataframe("vix_close", vix.to_frame("vix"))

        adv = volumes.rolling(20).mean().iloc[-1]
        tracker.log_metric("n_assets", len(prices.columns), step=0)

        # ------------------------------------------------------------
        # 2. BENCHMARK: equal-weight buy-and-hold (long-only)
        # ------------------------------------------------------------
        print("Building equal-weight benchmark...")
        bh_cfg = make_config(allow_short=False)
        bh_signals = run_strategy(
            prices, "buy_and_hold", weight=1.0 / len(prices.columns)
        )
        bh_signals = resample_monthly_signals(bh_signals)
        bh_result = run_backtest(
            prices=prices, signals=bh_signals, volumes=volumes, adv=adv, config=bh_cfg
        )
        tracker.log_dataframe(
            "benchmark_equity", bh_result.equity_curve.to_frame("equity")
        )
        tracker.log_dataframe("benchmark_trades", bh_result.trades)
        tracker.log_metrics(
            {f"benchmark_{k}": float(v) for k, v in bh_result.metrics.items()}, step=0
        )
        print(
            f"  Benchmark equal-weight Sharpe={bh_result.metrics['sharpe']:.3f} "
            f"Ret={bh_result.metrics['annualized_return']:.2%} Trades={bh_result.metrics['num_trades']}"
        )

        # ------------------------------------------------------------
        # 3. PARAMETER GRID SEARCH -- TRAIN ONLY (internal walk-forward)
        # ------------------------------------------------------------
        print("Grid search on TRAIN period (walk-forward selection)...")
        grid = list(itertools.product(LONG_ONLY_CHOICES, LOOKBACKS, SKIPS))
        print(f"  {len(grid)} combinations")

        combo_records = []
        for i, (long_only, lookback, skip) in enumerate(grid):
            allow_short = not long_only
            result, _ = evaluate_combo(
                prices, volumes, adv, allow_short, lookback, skip
            )
            train_ret, val_ret, test_ret, oos_ret = split_returns_by_date(
                result.returns
            )

            # Internal walk-forward on train
            train_sharpes = wf_oos_sharpes(train_ret, n_splits=4)
            sel = selection_metric(train_ret, train_sharpes)

            # Train Sharpe
            train_sharpe = sharpe_ratio(train_ret.values)

            rec = {
                "long_only": bool(long_only),
                "lookback": lookback,
                "skip": skip,
                "train_sharpe": float(train_sharpe),
                "wf_oos_mean_sharpe": float(sel),
                "wf_oos_sharpes": [float(s) for s in train_sharpes],
                "val_sharpe": float(sharpe_ratio(val_ret.values)),
                "test_sharpe": float(sharpe_ratio(test_ret.values)),
                "oos_sharpe": float(sharpe_ratio(oos_ret.values)),
                "oos_trades": int(
                    (result.trades["timestamp"] > pd.Timestamp(TRAIN_END)).sum()
                ),
                "train_trades": int(
                    (result.trades["timestamp"] <= pd.Timestamp(TRAIN_END)).sum()
                ),
                "full_sharpe": float(result.metrics["sharpe"]),
                "full_max_dd": float(result.metrics["max_drawdown"]),
                "full_pf": float(result.metrics["profit_factor"]),
                "full_trades": int(result.metrics["num_trades"]),
            }
            combo_records.append(rec)
            tracker.log_metrics(rec, step=i)
            print(
                f"  [{i + 1}/{len(grid)}] long_only={long_only} lb={lookback} skip={skip}: "
                f"train Sharpe={train_sharpe:.3f} wfOOS={sel:.3f} val={rec['val_sharpe']:.3f} test={rec['test_sharpe']:.3f}"
            )

        combos_df = pd.DataFrame(combo_records)
        tracker.log_dataframe("param_grid_results", combos_df)

        # Select: maximize internal walk-forward OOS Sharpe (train only), tie-break on train Sharpe.
        combos_df_sorted = combos_df.sort_values(
            ["wf_oos_mean_sharpe", "train_sharpe"], ascending=[False, False]
        )
        best = combos_df_sorted.iloc[0]
        sel_long_only = bool(best["long_only"])
        sel_lookback = int(best["lookback"])
        sel_skip = int(best["skip"])
        sel_allow_short = not sel_long_only
        print(
            f"\nSELECTED: long_only={sel_long_only} lookback={sel_lookback} skip={sel_skip} "
            f"(wfOOS Sharpe={best['wf_oos_mean_sharpe']:.3f}, train Sharpe={best['train_sharpe']:.3f})"
        )

        # Multiple testing correction for the grid (Benjamini-Hochberg on walk-forward p-values).
        # Per-fold Sharpe sign test -> p-value of wf_oos_mean_sharpe > 0
        pvals = []
        for rec in combo_records:
            sf = np.array(rec["wf_oos_sharpes"])
            sf = sf[~np.isnan(sf)]
            if len(sf) > 1 and sf.std() > 0:
                _, p = stats.ttest_1samp(sf, 0.0)
                pvals.append(float(p))
            else:
                pvals.append(1.0)
        rejected, adj_pvals = multiple_testing_correction(
            np.array(pvals), method="benjamini_hochberg", alpha=0.05
        )
        for rec, ap, rej in zip(combo_records, adj_pvals, rejected):
            rec["wf_oos_adj_pvalue"] = float(ap)
            rec["wf_oos_significant"] = bool(rej)
        tracker.log_dataframe("param_grid_results", pd.DataFrame(combo_records))

        # ------------------------------------------------------------
        # 4. FINAL STRATEGY with selected params (applied to Val + Test)
        # ------------------------------------------------------------
        print("\nRunning selected strategy on Val + Test...")
        final_result, final_signals = evaluate_combo(
            prices, volumes, adv, sel_allow_short, sel_lookback, sel_skip
        )
        train_ret, val_ret, test_ret, oos_ret = split_returns_by_date(
            final_result.returns
        )

        tracker.log_dataframe("selected_signals", final_signals)
        tracker.log_dataframe(
            "selected_equity", final_result.equity_curve.to_frame("equity")
        )
        tracker.log_dataframe("selected_trades", final_result.trades)

        # ------------------------------------------------------------
        # 5. EVIDENCE GATES (on pooled OOS = Val + Test)
        # ------------------------------------------------------------
        print("\nApplying evidence gates on OOS (Val+Test)...")
        oos_returns = oos_ret
        oos_sharpe = sharpe_ratio(oos_returns.values)
        oos_returns_arr = oos_returns.values
        sharpe_ci = sharpe_ratio_ci(
            oos_returns_arr, n_bootstrap=1000, random_state=SEED
        )

        # Trades split
        oos_trades = final_result.trades[
            final_result.trades["timestamp"] > pd.Timestamp(TRAIN_END)
        ]

        # Profit factor / drawdown on OOS equity
        oos_equity = (1 + oos_returns).cumprod()
        oos_dd = (oos_equity - oos_equity.expanding().max()).min()
        gross_p = oos_returns[oos_returns > 0].sum()
        gross_l = abs(oos_returns[oos_returns < 0].sum())
        oos_pf = float(gross_p / gross_l) if gross_l > 0 else np.inf

        # Walk-forward stability: OOS Sharpe vs Train Sharpe
        train_sharpe = sharpe_ratio(train_ret.values)
        wf_stability = oos_sharpe / train_sharpe if train_sharpe != 0 else 0.0

        # Regime analysis (VIX) on OOS
        oos_vix = vix.loc[oos_returns.index]
        regimes = regime_labels(oos_vix)
        regime_metrics = {}
        worst_regime_sharpe = np.inf
        for reg in ["bull", "sideways", "bear"]:
            mask = regimes == reg
            r = oos_returns[mask]
            if len(r) > 1 and r.std() > 0:
                s = sharpe_ratio(r.values)
                regime_metrics[reg] = {"sharpe": float(s), "n": len(r)}
                worst_regime_sharpe = min(worst_regime_sharpe, s)
            else:
                regime_metrics[reg] = {"sharpe": 0.0, "n": len(r)}

        # Parameter perturbation (+/-20%) on OOS
        def perturbed_sharpe(lb, sk):
            res, _ = evaluate_combo(prices, volumes, adv, sel_allow_short, lb, sk)
            _, _, _, oos_r = split_returns_by_date(res.returns)
            return sharpe_ratio(oos_r.values)

        # +/-20% around selected, clamped, nearest integer
        lb_p = max(1, round(sel_lookback * 1.2))
        lb_m = max(1, round(sel_lookback * 0.8))
        sk_p = max(1, round(sel_skip * 1.2))
        sk_m = max(1, round(sel_skip * 0.8))
        perturbations = {
            "lookback+20%": perturbed_sharpe(lb_p, sel_skip),
            "lookback-20%": perturbed_sharpe(lb_m, sel_skip),
            "skip+20%": perturbed_sharpe(sel_lookback, sk_p),
            "skip-20%": perturbed_sharpe(sel_lookback, sk_m),
        }
        min_perturbed = min(perturbations.values())
        if not np.isfinite(min_perturbed) or min_perturbed == 0:
            min_perturbed = 0.0

        # Benchmark significance (t-test on daily alpha vs equal-weight benchmark)
        bench_full = bh_result.returns.reindex(oos_returns.index).ffill()
        oos_returns_arr = oos_returns.values
        bench_arr = bench_full.values
        # drop any residual NaNs from misalignment
        mask = ~(np.isnan(oos_returns_arr) | np.isnan(bench_arr))
        oos_returns_arr = oos_returns_arr[mask]
        bench_arr = bench_arr[mask]
        cmp = compare_to_benchmark(oos_returns_arr, bench_arr)

        # Bootstrap CI for Information Ratio
        def ir_func(x):
            b = bench_arr[: len(x)]
            excess = x - b
            return (
                float(excess.mean() / excess.std() * np.sqrt(252))
                if excess.std() > 0
                else 0.0
            )

        ir_ci = bootstrap_confidence_interval(
            oos_returns_arr - bench_arr, ir_func, n_bootstrap=1000, random_state=SEED
        )
        ir_ci = (float(ir_ci[0]), float(ir_ci[1]))
        # alpha p-value (two-sided t-test on daily excess returns)
        excess = oos_returns_arr - bench_arr
        if excess.std() > 0:
            _, alpha_p = stats.ttest_1samp(excess, 0.0)
        else:
            alpha_p = 1.0

        # ------------------------------------------------------------
        # 6. GATE EVALUATION
        # ------------------------------------------------------------
        gates = {
            "net_oos_sharpe": {
                "value": round(oos_sharpe, 4),
                "threshold": GATES["min_sharpe"],
                "pass": bool(oos_sharpe >= GATES["min_sharpe"]),
            },
            "oos_trades": {
                "value": len(oos_trades),
                "threshold": GATES["min_trades"],
                "pass": bool(len(oos_trades) >= GATES["min_trades"]),
            },
            "profit_factor": {
                "value": round(oos_pf, 4),
                "threshold": GATES["min_profit_factor"],
                "pass": bool(oos_pf >= GATES["min_profit_factor"]),
            },
            "max_drawdown": {
                "value": round(oos_dd, 4),
                "threshold": GATES["max_drawdown"],
                "pass": bool(oos_dd >= -GATES["max_drawdown"]),
            },
            "walkforward_stability": {
                "value": round(wf_stability, 4),
                "threshold": GATES["min_walkforward_stability"],
                "pass": bool(wf_stability >= GATES["min_walkforward_stability"]),
            },
            "param_perturbation": {
                "value": round(min_perturbed, 4),
                "threshold": round(oos_sharpe * GATES["min_perturbed_sharpe_ratio"], 4),
                "pass": bool(
                    min_perturbed >= oos_sharpe * GATES["min_perturbed_sharpe_ratio"]
                ),
                "details": {k: round(float(v), 4) for k, v in perturbations.items()},
            },
            "regime_stability": {
                "value": round(worst_regime_sharpe, 4),
                "threshold": GATES["min_worst_regime_sharpe"],
                "pass": bool(worst_regime_sharpe >= GATES["min_worst_regime_sharpe"]),
                "regimes": regime_metrics,
            },
            "benchmark_significance": {
                "value": round(float(alpha_p), 4),
                "threshold": GATES["max_p_value"],
                # Direction-aware (H34): significance must be in the POSITIVE
                # direction -- a significantly negative alpha is evidence of
                # underperformance, not of beating the benchmark.
                "pass": benchmark_significance_gate(
                    alpha_p, cmp["information_ratio"], GATES["max_p_value"]
                ),
                "information_ratio": round(float(cmp["information_ratio"]), 4),
                "alpha_p_value": round(float(alpha_p), 4),
            },
        }
        all_pass = all(g["pass"] for g in gates.values())

        # Multiple-testing correction for the benchmark test across the family of
        # grid combos is approximated by BH on the grid's walk-forward p-values;
        # the selected-combo significance uses the raw p-value (single hypothesis
        # now that params were chosen, reported with BH-adjusted grid p-values
        # above). We record both.
        tracker.log_metrics({"all_gates_pass": all_pass}, step=0)
        tracker.log_metrics(gates, step=0)

        # ----------------------------------------------- PRINT
        print("\n" + "=" * 72)
        print("TIME-SERIES MOMENTUM EXPERIMENT -- EVIDENCE GATES (OOS: Val+Test)")
        print("=" * 72)
        print(
            f"Selected: long_only={sel_long_only} lookback={sel_lookback} skip={sel_skip} vol_target={TARGET_VOL}"
        )
        print(
            f"OOS Sharpe={oos_sharpe:.3f} (95% CI [{sharpe_ci[0]:.3f}, {sharpe_ci[1]:.3f}])"
        )
        print(
            f"Train Sharpe={train_sharpe:.3f}  Val Sharpe={sharpe_ratio(val_ret.values):.3f}  Test Sharpe={sharpe_ratio(test_ret.values):.3f}"
        )
        print(
            f"OOS trades={len(oos_trades)}  Profit factor={oos_pf:.3f}  Max DD={oos_dd:.2%}"
        )
        print(
            f"WF stability={wf_stability:.3f}  Worst regime Sharpe={worst_regime_sharpe:.3f}"
        )
        print(f"Benchmark IR={cmp['information_ratio']:.3f}  alpha p={alpha_p:.4f}")
        print()
        for name, g in gates.items():
            flag = "PASS" if g["pass"] else "FAIL"
            print(f"  [{flag}] {name}: {g['value']} (threshold {g['threshold']})")
        print()
        print(f"  ALL GATES PASSED: {'YES' if all_pass else 'NO'}")
        print("=" * 72)

        # ----------------------------------------------- SAVE SUMMARY
        summary = {
            "experiment_id": exp_id,
            "selected_params": {
                "long_only": sel_long_only,
                "lookback": sel_lookback,
                "skip": sel_skip,
                "target_vol": TARGET_VOL,
                "volatility_scale": True,
            },
            "gates": gates,
            "all_gates_pass": all_pass,
            "oos_metrics": {
                "sharpe": round(oos_sharpe, 4),
                "sharpe_ci": [round(sharpe_ci[0], 4), round(sharpe_ci[1], 4)],
                "n_trades": len(oos_trades),
                "profit_factor": round(oos_pf, 4),
                "max_drawdown": round(oos_dd, 4),
            },
            "split_metrics": {
                "train_sharpe": round(train_sharpe, 4),
                "val_sharpe": round(sharpe_ratio(val_ret.values), 4),
                "test_sharpe": round(sharpe_ratio(test_ret.values), 4),
                "oos_sharpe": round(oos_sharpe, 4),
            },
            "benchmark_comparison": {
                "information_ratio": round(float(cmp["information_ratio"]), 4),
                "information_ratio_ci": [round(ir_ci[0], 4), round(ir_ci[1], 4)],
                "alpha_annualized": round(float(cmp["alpha_annualized"]), 4),
                "alpha_p_value": round(float(alpha_p), 6),
                "alpha_t_stat": round(float(cmp["alpha_t_stat"]), 4),
            },
            "regime_metrics": regime_metrics,
            "perturbations": {k: round(float(v), 4) for k, v in perturbations.items()},
            "param_grid_summary": {
                "n_combos": len(combo_records),
                "selection_metric": "mean walk-forward OOS Sharpe on TRAIN",
                "benjamini_hochberg_significant": int(
                    sum(1 for r in combo_records if r.get("wf_oos_significant"))
                ),
            },
            "gates_spec": GATES,
        }
        exp_dir = Path(tracker.log_dir) / "artifacts" / exp_id
        with open(exp_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2, default=str)
        tracker.log_artifact("summary", exp_dir / "summary.json")

        tracker.log_dataframe("param_grid_results", combos_df)
        tracker.log_dataframe(
            "selected_equity", final_result.equity_curve.to_frame("equity")
        )
        tracker.log_dataframe("selected_trades", final_result.trades)
        tracker.log_dataframe(
            "benchmark_equity", bh_result.equity_curve.to_frame("equity")
        )

        tracker.finish_experiment(status="completed")

        print(f"\nExperiment ID: {exp_id}")
        print(f"All gates passed: {all_pass}")
        return all_pass

    except Exception as e:  # noqa: BLE001 -- top-level experiment harness: any failure must finish the tracker and return a verdict
        import traceback

        traceback.print_exc()
        tracker.finish_experiment(status="failed", error=str(e))
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
