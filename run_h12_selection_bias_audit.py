#!/usr/bin/env python3
"""H12: Selection-Bias Audit of the H10-selected intraday TSMOM config.

H11 certified the H10 config as robust to seeds, perturbations, costs and split
shifts. The remaining question is whether a 13,824-combo grid search can
manufacture a "passing" config by chance alone. H12 applies the standard
selection-bias corrections of Bailey & Lopez de Prado (2014) and Bailey,
Borwein, Lopez de Prado & Zhu (2014):

  1. Deflated Sharpe Ratio (DSR). The H10 grid searched N=13,824 configurations,
     selected on Val Sharpe. The DSR tests whether the best-of-N Val Sharpe is
     distinguishable from the expected maximum of N random trials. Inputs are
     the preserved per-combo Val-Sharpe distribution
     (`.experiments/artifacts/exp_2026-10-11T17-41-18-169363Z/grid_results.parquet`,
     column `val_sharpe` -- no new backtests needed for this component).

  2. Probability of Backtest Overfitting (PBO) via Combinatorially-Symmetric
     Cross-Validation (CSCV). The H10 run logged only Val metrics per combo, so
     we re-run the H10 grid logging per-combo OOS (Val+Test) returns, then compute
     PBO with S=12 combinatorially-symmetric blocks over the OOS window.

  3. Family-wide multiple-testing audit. Pool the trial counts of every grid
     search in the H1-H12 family (~14,389) and recompute the deflated Sharpe /
     Bonferroni- and FDR-adjusted significance of the H10 OOS benchmark
     p-value (4.79e-10) under the pooled trial count.

  4. PF-margin sensitivity (diagnostic). Using the H10 grid artifact, report the
     distribution of `val_profit_factor` and the fraction of combos with PF >= 1.3
     -- quantifies how much of the PF "pass" is selection pressure vs genuine edge.

Null (H0): the H10 selected config's edge does NOT survive selection-bias
correction -- DSR-adjusted Sharpe < 1.0, or PBO >= 0.5, or the benchmark alpha is
not significant after family-wide multiple-testing correction.

Constraints: no live trading, no secrets, no paid data, Test never enters
selection, <= 4 CPU-h per experiment, reuse existing engine / tracking /
validation infrastructure, all regression tests passing.
"""

import sys
import os
import json
import time
import copy
import itertools
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from qtr.data.fetcher import get_data_fetcher
from qtr.backtest.engine import run_backtest, BacktestConfig, CostModel
from qtr.tracking.experiment import get_tracker
from qtr.validation.statistics import (
    sharpe_ratio,
    walk_forward_splits,
    compare_to_benchmark,
)

# Reuse H10 constants / primitives (single source of truth for universe, costs,
# gates, signal + exit machinery).
from run_h10_intraday_tsmom_pfopt_experiment import (
    FUTURES_UNIVERSE,
    VIX_SYMBOL,
    SEED,
    INITIAL_CAPITAL,
    GATES,
    COST_MODEL_DEFAULTS,
    FUTURES_SPECS,
    make_futures_config,
    regime_labels,
    vol_scaled_tsmom_hourly,
    _daily_target_from_hourly,
    build_hourly_target,
    apply_exits_hourly,
    _splits,
    _period_metrics,
    _count_in,
    smooth_signal,
    regime_factor_hourly,
)

EXPERIMENT_NAME = "h12_selection_bias_audit"
EXPERIMENT_DESC = (
    "H12: Selection-bias audit of the H10-selected intraday TSMOM config -- "
    "Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014), Probability of "
    "Backtest Overfitting via CSCV (Bailey et al. 2014), family-wide "
    "multiple-testing correction, PF-margin sensitivity"
)

DATA_START = "2024-10-12"
DATA_END = "2026-10-11"
PERIODS_PER_YEAR = 252
EMC = 0.5772156649  # Euler-Mascheroni constant

# H10 selected config (frozen for H12 -- never re-selected).
SEL = {
    "vol_window_long": 1008,
    "smooth_span": None,
    "regime_scaling": False,
    "min_trade_interval": 0,
    "trailing_mult": 2.0,
    "max_hold_bars": 60,
    "vol_limit_mult": 1.5,
    "vol_floor_fraction": 0.25,
}

# H10 grid artifact (single source of truth for the selection distribution).
H10_GRID_PARQUET = Path(
    ".experiments/artifacts/exp_2026-10-11T17-41-18-169363Z/grid_results.parquet"
)

# Family-wide trial counts (H1-H11 grid sizes, from NEXT_TASK / pre-registration).
FAMILY_TRIAL_COUNTS = {
    "H1": 18, "H2": 54, "H3": 108, "H4": 18, "H5": 6,
    "H6": 6, "H8": 5, "H10": 13824, "H11": 350,
}
FAMILY_TOTAL = sum(FAMILY_TRIAL_COUNTS.values())

# H10 grid size (number of configurations searched and selected on).
N_GRID = 13824

# CSCV block count S. The OOS window is trimmed to the largest multiple
# of S so the CSCV blocks are combinatorially symmetric.
CSCV_S = 12

# Benchmark p-value from H11 (bit-exact reproduction of the H10 artifact).
BENCHMARK_P_VALUE = 4.790305556723297e-10


# ---------------------------------------------------------------------------
# DSR (Bailey & Lopez de Prado 2014, Eqs 2-4)
# ---------------------------------------------------------------------------
def _expected_max_sharpe(n_trials, var_trials):
    """Expected maximum Sharpe under the null of zero skill across N trials.

    E[max SR] = sqrt(V) * [(1-g) * Phi^-1(1 - 1/N) + g * Phi^-1(1 - 1/(N*e))]
    where g is the Euler-Mascheroni constant and V is the variance of the
    per-trial Sharpe estimates (here the preserved Val-Sharpe distribution).
    """
    max_z = (
        (1.0 - EMC) * stats.norm.ppf(1.0 - 1.0 / n_trials)
        + EMC * stats.norm.ppf(1.0 - 1.0 / (n_trials * np.e))
    )
    return float(np.sqrt(var_trials) * max_z), float(max_z)


def deflated_sharpe_ratio(
    observed_sr, n_trials, n_obs, var_trials, skewness, kurtosis
):
    """Deflated Sharpe Ratio and one-sided p-value.

    All Sharpe inputs are ANNUALIZED. The test statistic is evaluated at bar
    frequency (divide by sqrt(periods_per_year)) so the non-normality
    correction (which is scale-invariant in SR units) is correct.

    Returns (dsr_value, p_value) where p_value = P(true SR > 0 | selection).
    """
    sr_per_bar = observed_sr / np.sqrt(PERIODS_PER_YEAR)
    sr0_per_bar, _ = _expected_max_sharpe(n_trials, var_trials / PERIODS_PER_YEAR)
    numerator = (sr_per_bar - sr0_per_bar) * np.sqrt(n_obs - 1.0)
    skew_term = 1.0 - skewness * sr_per_bar
    kurt_term = (kurtosis - 1.0) / 4.0 * sr_per_bar ** 2
    denom = float(np.sqrt(max(1e-12, skew_term + kurt_term)))
    dsr_adj = numerator / denom
    p = float(stats.norm.cdf(dsr_adj))
    return float(observed_sr * p), float(1.0 - p)


def _moments(returns):
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 2:
        return 0.0, 0.0, 0.0, 0.0, 0.0
    return (
        float(sharpe_ratio(r)),
        float(stats.skew(r)),
        float(stats.kurtosis(r, fisher=False)),
        float(len(r)),
        float(np.var(r, ddof=1)),
    )


# ---------------------------------------------------------------------------
# PBO via CSCV (Bailey, Borwein, Lopez de Prado & Zhu 2014)
# ---------------------------------------------------------------------------
def _cscv_pbo_multi(performance_matrix, n_blocks):
    """CSCV PBO for N strategies evaluated over T periods.

    performance_matrix: (T, N) array -- row t = per-bar return of each of the N
        strategies at time t. Columns are the H10 grid configs; the IS-optimal
        column is selected per CSCV combination and its OOS rank is recorded.

    Returns dict with pbo, n_combinations, and the rank distribution.
    """
    T, N = performance_matrix.shape
    if T % n_blocks != 0:
        raise ValueError(
            f"CSCV requires T divisible by S; got T={T}, S={n_blocks}"
        )
    block_size = T // n_blocks
    blocks = [
        performance_matrix[i * block_size:(i + 1) * block_size, :]
        for i in range(n_blocks)
    ]
    half = n_blocks // 2
    ranks = []
    is_opt_oos_means = []
    for combo in itertools.combinations(range(n_blocks), half):
        is_idx = list(combo)
        oos_idx = [b for b in range(n_blocks) if b not in combo]
        is_mat = np.concatenate([blocks[b] for b in is_idx], axis=0)
        oos_mat = np.concatenate([blocks[b] for b in oos_idx], axis=0)
        is_means = is_mat.mean(axis=0)
        oos_means = oos_mat.mean(axis=0)
        best_is = int(np.argmax(is_means))
        # Rank of the IS-optimal strategy by OOS mean (1 = best).
        order = np.argsort(-oos_means)  # descending
        ranks_of = {int(j): int(r) + 1 for r, j in enumerate(order)}
        rank = ranks_of[best_is]
        ranks.append(rank)
        is_opt_oos_means.append(float(oos_means[best_is]))
    ranks = np.asarray(ranks)
    # PBO = P(IS-optimal ranks below the OOS median | IS-optimal).
    # Rank 1 is the BEST OOS rank, so "below the median" (worse
    # than median) corresponds to rank > median rank.
    median_rank = (N + 1) / 2.0
    pbo = float(np.mean(ranks > median_rank))
    return {
        "pbo": pbo,
        "n_combinations": int(len(ranks)),
        "n_blocks": int(n_blocks),
        "n_strategies": int(N),
        "mean_is_opt_oos_rank": float(ranks.mean()),
        "median_is_opt_oos_rank": float(np.median(ranks)),
        "rank_distribution": {int(k): int(v) for k, v in zip(*np.unique(ranks, return_counts=True))},
        "is_opt_oos_means": is_opt_oos_means,
    }


# ---------------------------------------------------------------------------
# Data + grid re-run (logs per-combo OOS returns for the PBO audit)
# ---------------------------------------------------------------------------
def _rebuild_grid_oos(prices, volumes, vix_hourly, cfg, masks):
    """Re-run the H10 grid, logging per-combo OOS (Val+Test) returns.

    Returns (grid_meta_df, oos_matrix, oos_index) where:
      - grid_meta_df: one row per combo with scalar OOS metrics (no returns).
      - oos_matrix: (N, T_oos) float32 array of per-bar net OOS returns.
      - oos_index: the DatetimeIndex of the OOS window.
    """
    # price-derived exit inputs (config-independent)
    pct = prices.pct_change().fillna(0)
    atr = prices * pct.rolling(14, min_periods=7).std()
    atr = atr.replace(0, np.nan).ffill().fillna(prices * 0.001)
    vol_exit = pct.rolling(20, min_periods=10).std() * np.sqrt(252 * 6.5)
    vol_exit = vol_exit.replace(0, np.nan).ffill()

    oos_mask = masks["oos"]
    oos_index = prices.index[oos_mask]
    T_oos = int(oos_mask.sum())
    N = 13824

    base_signals = {}
    for vw in [252, 504, 1008]:
        base_signals[vw] = vol_scaled_tsmom_hourly(
            prices, vol_window_long=vw, vol_window_short=vw // 4
        )

    targets = {}
    for vw in [252, 504, 1008]:
        for smooth_span in [None, 4, 8, 16]:
            for regime in [False, True]:
                targets[(vw, smooth_span, regime)] = build_hourly_target(
                    base_signals[vw], smooth_span, vw, regime, vix_hourly, prices.index
                )

    meta_cols = [
        "vol_window_long", "smooth_span", "regime_scaling", "min_trade_interval",
        "trailing_mult", "max_hold_bars", "vol_limit_mult", "vol_floor_fraction",
        "oos_sharpe", "oos_profit_factor", "oos_max_drawdown", "oos_trades",
    ]
    meta = {c: np.empty(N, dtype=object if c == "smooth_span" else float) for c in meta_cols}
    oos_matrix = np.empty((N, T_oos), dtype=np.float32)

    combos = list(itertools.product(
        [252, 504, 1008], [None, 4, 8, 16], [False, True],
        [0, 4, 8, 24],
        [1.5, 2.0, 2.5, 3.0], [60, 120, 240, 480], [1.5, 2.0, 2.5], [0.25, 0.5, 0.75],
    ))
    assert len(combos) == N, len(combos)

    t0 = time.time()
    for i, (vw, smooth_span, regime, min_int, tm, mhb, vlm, vff) in enumerate(combos):
        hourly_target = targets[(vw, smooth_span, regime)]
        positions = apply_exits_hourly(
            hourly_target, prices, atr, vol_exit,
            trailing_mult=tm, max_hold_bars=mhb,
            vol_limit_mult=vlm, vol_floor_fraction=vff,
            target_vol=0.15, min_trade_interval=min_int,
        )
        res = run_backtest(prices=prices, signals=positions, volumes=volumes, config=cfg)
        oos_ret = res.returns[oos_mask].reindex(oos_index).fillna(0.0)
        om = _period_metrics(oos_ret, _count_in(res.trades, oos_mask, prices))
        meta["vol_window_long"][i] = vw
        meta["smooth_span"][i] = (str(smooth_span) if smooth_span is not None else "none")
        meta["regime_scaling"][i] = regime
        meta["min_trade_interval"][i] = min_int
        meta["trailing_mult"][i] = tm
        meta["max_hold_bars"][i] = mhb
        meta["vol_limit_mult"][i] = vlm
        meta["vol_floor_fraction"][i] = vff
        meta["oos_sharpe"][i] = om["sharpe"]
        meta["oos_profit_factor"][i] = om["profit_factor"]
        meta["oos_max_drawdown"][i] = om["max_drawdown"]
        meta["oos_trades"][i] = om["trades"]
        oos_matrix[i, :] = oos_ret.to_numpy(dtype=np.float32)
        if (i + 1) % 2000 == 0:
            print(f"    grid re-run {i+1}/{N} ({(time.time()-t0)/60:.1f} min)", flush=True)
    grid_meta = pd.DataFrame(meta)
    return grid_meta, oos_matrix, oos_index


def _build_exit_inputs(prices):
    """Price-derived exit inputs (config-independent, as in H9-H11)."""
    pct = prices.pct_change().fillna(0)
    atr = prices * pct.rolling(14, min_periods=7).std()
    atr = atr.replace(0, np.nan).ffill().fillna(prices * 0.001)
    vol_exit = pct.rolling(20, min_periods=10).std() * np.sqrt(252 * 6.5)
    vol_exit = vol_exit.replace(0, np.nan).ffill()
    return atr, vol_exit


def _load_cached_data():
    """Load the H10 artifact data (offline, bit-consistent with H10).

    Uses the preserved H10 experiment artifacts (prices / volumes /
    hourly VIX / selected-config net returns) so the audit is fully
    reproducible without network access.
    """
    artifact_dir = H10_GRID_PARQUET.parent
    prices = pd.read_parquet(artifact_dir / "prices.parquet")
    volumes = pd.read_parquet(artifact_dir / "volumes.parquet")
    vix_hourly = pd.read_parquet(artifact_dir / "vix_hourly.parquet")["vix"]
    returns = pd.read_parquet(artifact_dir / "returns.parquet")["returns"]
    return prices, volumes, vix_hourly, returns


def _selected_row(grid):
    """Row of the (frozen) H10 selected config in the grid artifact."""
    smooth = "none" if SEL["smooth_span"] is None else str(SEL["smooth_span"])
    mask = (
        (grid["vol_window_long"] == SEL["vol_window_long"])
        & (grid["smooth_span"] == smooth)
        & (grid["regime_scaling"] == SEL["regime_scaling"])
        & (grid["min_trade_interval"] == SEL["min_trade_interval"])
        & (grid["trailing_mult"] == SEL["trailing_mult"])
        & (grid["max_hold_bars"] == SEL["max_hold_bars"])
        & (grid["vol_limit_mult"] == SEL["vol_limit_mult"])
        & (grid["vol_floor_fraction"] == SEL["vol_floor_fraction"])
    )
    assert mask.sum() == 1, f"expected exactly 1 selected row, got {mask.sum()}"
    return grid.loc[mask].iloc[0]


def main():
    np.random.seed(SEED)
    t_start = time.time()
    tracker = get_tracker()
    exp_id = tracker.start_experiment(
        name=EXPERIMENT_NAME,
        description=EXPERIMENT_DESC,
        config={
            "universe": FUTURES_UNIVERSE,
            "interval": "1h",
            "data_start": DATA_START,
            "data_end": DATA_END,
            "gates": GATES,
            "seed": SEED,
            "h10_selected_config": SEL,
            "n_trials_h10": N_GRID,
            "family_trial_counts": FAMILY_TRIAL_COUNTS,
            "family_total_trials": FAMILY_TOTAL,
            "cscv_blocks": CSCV_S,
            "benchmark_p_value": BENCHMARK_P_VALUE,
        },
        data_sources={
            "source": "h10_artifact_cache",
            "symbols": FUTURES_UNIVERSE,
            "vix": VIX_SYMBOL,
            "interval": "1h",
            "h10_artifact": str(H10_GRID_PARQUET.parent),
        },
        compute_budget={"max_cpu_hours": 4.0, "grid_size": N_GRID},
        random_seeds={"numpy": SEED, "python": SEED},
    )
    print(f"[H12] started {exp_id}  N_h10={N_GRID} family_N={FAMILY_TOTAL} S={CSCV_S}")

    try:
        prices, volumes, vix_hourly, h10_returns = _load_cached_data()
        atr, vol_exit = _build_exit_inputs(prices)
        train_mask, val_mask, test_mask = _splits(prices)
        masks = {
            "train": train_mask, "val": val_mask, "test": test_mask,
            "oos": val_mask | test_mask,
        }
        cfg = make_futures_config()
        grid = pd.read_parquet(H10_GRID_PARQUET)
        sel_row = _selected_row(grid)

        # Consistency: the selected config's Val Sharpe in the grid
        # must equal the Sharpe of the preserved Val-window returns.
        val_ret = h10_returns[val_mask]
        val_sharpe_check = float(sharpe_ratio(val_ret.values))
        observed_sr = float(sel_row["val_sharpe"])
        assert abs(val_sharpe_check - observed_sr) < 1e-9, (
            val_sharpe_check, observed_sr
        )
        print(f"[H12] data: prices={prices.shape} val_bars={len(val_ret)} "
              f"val_sharpe(selected)={observed_sr:.6f} (grid max "
              f"{grid['val_sharpe'].max():.6f})")

        # Return moments of the SELECTED config on the Val window
        # (the selection metric's distributional inputs).
        skew = float(stats.skew(val_ret.values))
        kurt = float(stats.kurtosis(val_ret.values, fisher=False))
        n_obs = int(len(val_ret))
        var_trials = float(grid["val_sharpe"].var(ddof=1))
        print(f"[H12] val return moments: skew={skew:.4f} kurt={kurt:.4f} "
              f"trial SR var={var_trials:.6f}")

        # ============================================================
        # 1. Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014)
        # ============================================================
        print("[H12] --- 1. Deflated Sharpe Ratio ---")
        dsr_h10, p_h10 = deflated_sharpe_ratio(
            observed_sr, N_GRID, n_obs, var_trials, skew, kurt
        )
        sr0_h10, _ = _expected_max_sharpe(N_GRID, var_trials / PERIODS_PER_YEAR)
        sr0_h10_annual = sr0_h10 * np.sqrt(PERIODS_PER_YEAR)
        print(f"  E[max SR | N={N_GRID}] = {sr0_h10_annual:.4f} (annualized)")
        print(f"  observed best-of-N Val SR = {observed_sr:.4f}")
        print(f"  DSR (H10 trials) = {dsr_h10:.4f}  p-value = {p_h10:.6f}")

        # ============================================================
        # 2. PBO via CSCV (Bailey, Borwein, Lopez de Prado & Zhu 2014)
        # ============================================================
        print("[H12] --- 2. PBO via CSCV (grid re-run, per-combo OOS) ---")
        grid_meta, oos_matrix, oos_index = _rebuild_grid_oos(
            prices, volumes, vix_hourly, cfg, masks
        )
        T_oos = int(oos_matrix.shape[1])
        T_cscv = (T_oos // CSCV_S) * CSCV_S
        if T_cscv != T_oos:
            # CSCV requires T divisible by S: trim the remainder bars
            # (0.2% of the OOS window) so the blocks are symmetric.
            oos_matrix = oos_matrix[:, :T_cscv]
            oos_index = oos_index[:T_cscv]
        pbo_result = _cscv_pbo_multi(oos_matrix.T, CSCV_S)
        print(f"  CSCV: S={CSCV_S} blocks, T={T_cscv} bars, "
              f"{pbo_result['n_combinations']} combinations, "
              f"N={pbo_result['n_strategies']} configs")
        print(f"  PBO = {pbo_result['pbo']:.4f}  "
              f"(mean rank of IS-optimal = {pbo_result['mean_is_opt_oos_rank']:.2f}, "
              f"median = {pbo_result['median_is_opt_oos_rank']:.2f})")
        print(f"  rank distribution: {pbo_result['rank_distribution']}")

        # OOS metrics of the re-run grid (diagnostics + gate inputs).
        oos_sharpe = grid_meta["oos_sharpe"].to_numpy()
        oos_pf = grid_meta["oos_profit_factor"].to_numpy()
        sel_idx = int(
            grid_meta.index[
                (grid_meta["vol_window_long"] == SEL["vol_window_long"])
                & (grid_meta["smooth_span"] == "none")
                & (grid_meta["regime_scaling"] == SEL["regime_scaling"])
                & (grid_meta["min_trade_interval"] == SEL["min_trade_interval"])
                & (grid_meta["trailing_mult"] == SEL["trailing_mult"])
                & (grid_meta["max_hold_bars"] == SEL["max_hold_bars"])
                & (grid_meta["vol_limit_mult"] == SEL["vol_limit_mult"])
                & (grid_meta["vol_floor_fraction"] == SEL["vol_floor_fraction"])
            ][0]
        )
        sel_oos_sharpe = float(oos_sharpe[sel_idx])
        sel_oos_pf = float(oos_pf[sel_idx])
        # Bit-consistency: the re-run OOS metrics of the selected config
        # must reproduce the H10 artifact's OOS metrics.
        h10_summary = json.loads(
            (H10_GRID_PARQUET.parent / "summary.json").read_text()
        )
        h10_oos_sharpe = float(h10_summary["metrics"]["oos_sharpe"])
        h10_oos_pf = float(h10_summary["metrics"]["profit_factor"])
        assert abs(sel_oos_sharpe - h10_oos_sharpe) < 1e-9, (
            sel_oos_sharpe, h10_oos_sharpe
        )
        assert abs(sel_oos_pf - h10_oos_pf) < 1e-9, (sel_oos_pf, h10_oos_pf)
        print(f"  re-run OOS metrics of selected config reproduce H10 "
              f"(SR={sel_oos_sharpe:.6f}, PF={sel_oos_pf:.6f})")

        # ============================================================
        # 3. Family-wide multiple-testing audit
        # ============================================================
        print("[H12] --- 3. Family-wide multiple-testing audit ---")
        dsr_family, p_family = deflated_sharpe_ratio(
            observed_sr, FAMILY_TOTAL, n_obs, var_trials, skew, kurt
        )
        sr0_family, _ = _expected_max_sharpe(
            FAMILY_TOTAL, var_trials / PERIODS_PER_YEAR
        )
        sr0_family_annual = sr0_family * np.sqrt(PERIODS_PER_YEAR)
        # Bonferroni and Benjamini-Hochberg adjustment of the H10 OOS
        # benchmark p-value under the pooled family trial count. With a
        # single ranked hypothesis (rank 1 of m), the BH-adjusted p is
        # min(1, m * p) -- coinciding with Bonferroni.
        bonferroni_p = min(1.0, BENCHMARK_P_VALUE * FAMILY_TOTAL)
        bh_p = min(1.0, FAMILY_TOTAL * BENCHMARK_P_VALUE / 1.0)
        print(f"  pooled N = {FAMILY_TOTAL} trials")
        print(f"  E[max SR | N={FAMILY_TOTAL}] = {sr0_family_annual:.4f}")
        print(f"  DSR (family) = {dsr_family:.4f}  p-value = {p_family:.6f}")
        print(f"  benchmark p = {BENCHMARK_P_VALUE:.3e} -> "
              f"Bonferroni {bonferroni_p:.3e}, BH-FDR {bh_p:.3e} "
              f"(gate < {GATES['max_p_value']})")

        # ============================================================
        # 4. PF-margin sensitivity (diagnostic)
        # ============================================================
        print("[H12] --- 4. PF-margin sensitivity ---")
        val_pf = grid["val_profit_factor"]
        pf_pass_frac_val = float((val_pf >= GATES["min_profit_factor"]).mean())
        pf_pass_frac_oos = float((oos_pf >= GATES["min_profit_factor"]).mean())
        sharpe_pass_frac_oos = float((oos_sharpe >= GATES["min_sharpe"]).mean())
        sel_val_pf = float(sel_row["val_profit_factor"])
        sel_val_pf_rank = int((val_pf > sel_val_pf).sum()) + 1
        pf_quantiles = {
            str(q): float(val_pf.quantile(q))
            for q in (0.05, 0.25, 0.50, 0.75, 0.95)
        }
        sr_quantiles = {
            str(q): float(grid["val_sharpe"].quantile(q))
            for q in (0.05, 0.25, 0.50, 0.75, 0.95)
        }
        print(f"  val PF: selected={sel_val_pf:.4f} (rank {sel_val_pf_rank}"
              f"/{N_GRID}), quantiles={pf_quantiles}")
        print(f"  fraction of combos with PF >= {GATES['min_profit_factor']}: "
              f"Val {pf_pass_frac_val:.4%}, OOS {pf_pass_frac_oos:.4%}")
        print(f"  fraction of combos with OOS Sharpe >= "
              f"{GATES['min_sharpe']}: {sharpe_pass_frac_oos:.4%}")

        # ============================================================
        # Verdict (pre-registered)
        # ============================================================
        # H0: the H10 edge does NOT survive selection-bias correction --
        # DSR-adjusted Sharpe < 1.0, OR PBO >= 0.5, OR the benchmark
        # alpha is not significant after family-wide correction.
        dsr_gate = bool(dsr_family >= GATES["min_sharpe"])
        pbo_gate = bool(pbo_result["pbo"] < 0.5)
        family_gate = bool(bonferroni_p < GATES["max_p_value"])
        all_pass = bool(dsr_gate and pbo_gate and family_gate)
        verdict = "PASS" if all_pass else "REJECT"

        total_elapsed = time.time() - t_start
        summary = {
            "experiment_id": exp_id,
            "hypothesis": "H12",
            "h10_selected_config": SEL,
            "n_obs_val_bars": n_obs,
            "val_return_skewness": skew,
            "val_return_kurtosis": kurt,
            "trial_sharpe_variance": var_trials,
            "observed_val_sharpe": observed_sr,
            "dsr": {
                "n_trials_h10": N_GRID,
                "expected_max_sharpe_h10": float(sr0_h10_annual),
                "dsr_adjusted_sharpe_h10": float(dsr_h10),
                "p_value_h10": float(p_h10),
                "n_trials_family": FAMILY_TOTAL,
                "family_trial_counts": FAMILY_TRIAL_COUNTS,
                "expected_max_sharpe_family": float(sr0_family_annual),
                "dsr_adjusted_sharpe_family": float(dsr_family),
                "p_value_family": float(p_family),
            },
            "pbo": {
                **{k: v for k, v in pbo_result.items()
                   if k != "is_opt_oos_means"},
                "t_oos_bars": T_cscv,
                "t_oos_bars_trimmed": T_oos - T_cscv,
            },
            "family_wide": {
                "pooled_trials": FAMILY_TOTAL,
                "benchmark_p_value": BENCHMARK_P_VALUE,
                "bonferroni_p": float(bonferroni_p),
                "bh_fdr_p": float(bh_p),
                "significance_gate": GATES["max_p_value"],
            },
            "pf_margin": {
                "selected_val_profit_factor": sel_val_pf,
                "selected_val_pf_rank": sel_val_pf_rank,
                "val_pf_quantiles": pf_quantiles,
                "val_sharpe_quantiles": sr_quantiles,
                "frac_val_pf_pass": pf_pass_frac_val,
                "frac_oos_pf_pass": pf_pass_frac_oos,
                "frac_oos_sharpe_pass": sharpe_pass_frac_oos,
            },
            "rerun_oos_metrics": {
                "selected_oos_sharpe": sel_oos_sharpe,
                "selected_oos_profit_factor": sel_oos_pf,
                "h10_artifact_oos_sharpe": h10_oos_sharpe,
                "h10_artifact_oos_profit_factor": h10_oos_pf,
                "oos_sharpe_mean": float(oos_sharpe.mean()),
                "oos_sharpe_std": float(oos_sharpe.std()),
                "oos_sharpe_max": float(oos_sharpe.max()),
                "oos_pf_mean": float(oos_pf.mean()),
                "oos_pf_max": float(oos_pf.max()),
            },
            "gates": {
                "dsr_adjusted_sharpe_ge_1.0": dsr_gate,
                "pbo_lt_0.5": pbo_gate,
                "family_corrected_p_lt_0.05": family_gate,
            },
            "all_pass": all_pass,
            "verdict": verdict,
            "total_elapsed_sec": float(round(total_elapsed, 1)),
            "compute_cpu_hours": float(round(total_elapsed / 3600, 3)),
        }

        tracker.log_dataframe("grid_oos_metrics", grid_meta)
        tracker.log_dataframe("cscv_rank_distribution", pd.DataFrame(
            {"rank": pbo_result["rank_distribution"].keys(),
             "count": pbo_result["rank_distribution"].values()}
        ))
        tracker.log_dataframe("val_sharpe_distribution", grid[["val_sharpe"]])

        exp_dir = Path(tracker.log_dir) / "artifacts" / exp_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        with open(exp_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2,
                      default=lambda x: float(x) if isinstance(x, (np.integer, np.floating))
                      else str(x))
        tracker.log_artifact("summary", exp_dir / "summary.json")
        tracker.finish_experiment(status="completed")

        print("\n" + "=" * 72)
        print("  H12 selection-bias audit:")
        print(f"    DSR-adjusted Sharpe (family N={FAMILY_TOTAL}): "
              f"{dsr_family:.4f} (>= 1.0) -> {'PASS' if dsr_gate else 'FAIL'}")
        print(f"    PBO (CSCV, S={CSCV_S}): {pbo_result['pbo']:.4f} "
              f"(< 0.5) -> {'PASS' if pbo_gate else 'FAIL'}")
        print(f"    Family-corrected benchmark p: {bonferroni_p:.3e} "
              f"(< 0.05) -> {'PASS' if family_gate else 'FAIL'}")
        print(f"  OVERALL: {verdict}  "
              f"({total_elapsed/60:.1f} min, {total_elapsed/3600:.3f} CPU-h)")
        print("=" * 72)
        return 0 if all_pass else 1
    except Exception as e:
        import traceback
        traceback.print_exc()
        tracker.finish_experiment(status="failed", error=str(e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
