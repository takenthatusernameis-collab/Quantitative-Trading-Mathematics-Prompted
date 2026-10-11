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

# CSCV block count S (must divide the OOS window evenly).
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
    # PBO = P(IS-optimal ranks below the OOS median | IS-optimal)
    median_rank = (N + 1) / 2.0
    pbo = float(np.mean(ranks < median_rank))
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


def main():
    pass
