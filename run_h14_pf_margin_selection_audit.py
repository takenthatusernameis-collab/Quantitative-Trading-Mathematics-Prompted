#!/usr/bin/env python3
"""H14: PF-Margin-Targeted Selection Audit.

H13 established that the H10 config's PF margin is fragile. The open question:
is the fragility a property of the *selection* or of the *family* (no config in
the 13,824-combo grid has a robust PF margin on this window)?

Pre-registration (from NEXT_TASK):
- Rank by Val PF margin (val_profit_factor - 1.3), take top K=50 configs
  excluding the frozen H10 config, from H10 grid artifact.
- Re-run the K configs logging per-combo OOS returns (reuse machinery).
- Apply H13 fragility gates per config: OOS PF bootstrap 95% CI lower bound
  (2,000 seeded resamples), worst-case DSR-adj OOS Sharpe (at N=K trials),
  leave-one-out symbol dispensability.
- Null (H0): no config in the top-K-by-Val-PF-margin set passes all three
  H13 fragility gates.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from qtr.backtest.engine import run_backtest
from qtr.tracking.experiment import get_tracker
from qtr.validation.statistics import sharpe_ratio
from run_h10_intraday_tsmom_pfopt_experiment import (
    GATES,
    INITIAL_CAPITAL,
    SEED,
    make_futures_config,
)
from run_h11_robustness_experiment import (
    _build_exit_inputs,
    per_symbol_contributions,
)
from run_h12_selection_bias_audit import (
    PERIODS_PER_YEAR,
    SEL,
    _count_in,
    _expected_max_sharpe,
    _load_cached_data,
    _period_metrics,
    _splits,
    deflated_sharpe_ratio,
)
from run_h13_oos_deflation_pf_audit import (
    N_BOOTSTRAP,
    _leave_one_out_pf,
    _profit_factor,
    bootstrap_profit_factor_distribution,
)

EXPERIMENT_NAME = "h14_pf_margin_selection_audit"
EXPERIMENT_DESC = (
    "H14: PF-margin-targeted selection audit. Rank H10 grid by Val PF margin "
    "(val_profit_factor - 1.3), test top K=50 excluding H10; apply H13 "
    "fragility gates (PF bootstrap CI LB>=1.3, worst-case DSR-adj OOS Sharpe>=1.0 "
    "at N=K, all symbols dispensable)."
)

K_TOP = 50
H10_GRID_PARQUET = Path(
    ".experiments/artifacts/exp_2026-10-11T17-41-18-169363Z/grid_results.parquet"
)
H10_ARTIFACT_DIR = H10_GRID_PARQUET.parent

DATA_START = "2024-10-12"
DATA_END = "2026-10-11"

def _select_top_by_val_pf_margin(grid_df: pd.DataFrame, k: int = K_TOP) -> pd.DataFrame:
    """Select top k configs by val_profit_factor margin over 1.3,
    excluding the frozen H10 config (exactly)."""
    frozen_mask = (
        (grid_df["vol_window_long"] == SEL["vol_window_long"])
        & ((grid_df["smooth_span"] == "none") | (pd.isna(grid_df["smooth_span"]) if False else (grid_df["smooth_span"].astype(str) == str(SEL["smooth_span"]) if SEL["smooth_span"] is not None else False)))  # handle carefully
    )
    # easier exact match by values
    frozen_mask = (
        (grid_df["vol_window_long"] == 1008)
        & (grid_df["smooth_span"].astype(str) == "none")
        & (grid_df["regime_scaling"] == False)
        & (grid_df["min_trade_interval"] == 0)
        & (grid_df["trailing_mult"] == 2.0)
        & (grid_df["max_hold_bars"] == 60)
        & (grid_df["vol_limit_mult"] == 1.5)
        & (grid_df["vol_floor_fraction"] == 0.25)
    )
    candidates = grid_df[~frozen_mask].copy()
    candidates["val_pf_margin"] = candidates["val_profit_factor"] - 1.3
    topk = candidates.sort_values("val_pf_margin", ascending=False).head(k).copy()
    topk["combo_index"] = range(len(topk))
    return topk


def _rebuild_grid_oos_for_subset(prices, volumes, vix_hourly, cfg, masks, subset_df):
    """Re-run a subset of configs (from subset_df) and return OOS matrix.
    subset_df has the param columns.
    """
    pct = prices.pct_change().fillna(0)
    atr = prices * pct.rolling(14, min_periods=7).std()
    atr = atr.replace(0, np.nan).ffill().fillna(prices * 0.001)
    vol_exit = pct.rolling(20, min_periods=10).std() * np.sqrt(252 * 6.5)
    vol_exit = vol_exit.replace(0, np.nan).ffill()

    oos_mask = masks["oos"]
    oos_index = prices.index[oos_mask]
    T_oos = int(oos_mask.sum())
    N = len(subset_df)

    from run_h10_intraday_tsmom_pfopt_experiment import (
        apply_exits_hourly,
        build_hourly_target,
        vol_scaled_tsmom_hourly,
    )
    base_signals = {}
    for vw in [252, 504, 1008]:
        base_signals[vw] = vol_scaled_tsmom_hourly(
            prices, vol_window_long=vw, vol_window_short=vw // 4
        )

    from run_h10_intraday_tsmom_pfopt_experiment import (
        vol_scaled_tsmom_hourly,
    )
    # build targets on-the-fly for needed combos (small N)
    targets_cache = {}
    meta_cols = [
        "vol_window_long", "smooth_span", "regime_scaling", "min_trade_interval",
        "trailing_mult", "max_hold_bars", "vol_limit_mult", "vol_floor_fraction",
        "val_sharpe", "val_profit_factor", "val_pf_margin", "oos_sharpe", "oos_profit_factor", "oos_trades",
    ]
    meta = {c: np.empty(N, dtype=object if c == "smooth_span" else float) for c in meta_cols}
    oos_matrix = np.empty((N, T_oos), dtype=np.float32)

    t0 = time.time()
    for i, row in subset_df.reset_index(drop=True).iterrows():
        vw = int(row["vol_window_long"])
        smooth_span = None if (str(row["smooth_span"]) == "none" or pd.isna(row["smooth_span"])) else int(row["smooth_span"])
        regime = bool(row["regime_scaling"])
        min_int = int(row["min_trade_interval"])
        tm = float(row["trailing_mult"])
        mhb = int(row["max_hold_bars"])
        vlm = float(row["vol_limit_mult"])
        vff = float(row["vol_floor_fraction"])
        key = (vw, smooth_span, regime)
        if key not in targets_cache:
            targets_cache[key] = build_hourly_target(
                base_signals[vw], smooth_span, vw, regime, vix_hourly, prices.index
            )
        hourly_target = targets_cache[key]
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
        meta["smooth_span"][i] = "none" if smooth_span is None else str(smooth_span)
        meta["regime_scaling"][i] = regime
        meta["min_trade_interval"][i] = min_int
        meta["trailing_mult"][i] = tm
        meta["max_hold_bars"][i] = mhb
        meta["vol_limit_mult"][i] = vlm
        meta["vol_floor_fraction"][i] = vff
        meta["val_sharpe"][i] = float(row["val_sharpe"])
        meta["val_profit_factor"][i] = float(row["val_profit_factor"])
        meta["val_pf_margin"][i] = float(row["val_pf_margin"])
        meta["oos_sharpe"][i] = om["sharpe"]
        meta["oos_profit_factor"][i] = om["profit_factor"]
        meta["oos_trades"][i] = om["trades"]
        oos_matrix[i, :] = oos_ret.to_numpy(dtype=np.float32)
        if (i + 1) % 10 == 0 or (i + 1) == N:
            print(f"    subset {i+1}/{N} ({(time.time()-t0)/60:.2f} min)", flush=True)
    grid_meta = pd.DataFrame(meta)
    return grid_meta, oos_matrix, oos_index

def main():
    t_start = time.time()
    tracker = get_tracker()
    tracker.start_experiment(EXPERIMENT_NAME, EXPERIMENT_DESC)

    try:
        # Load data
        prices, volumes, vix_hourly, returns = _load_cached_data()
        _, val_mask, test_mask = _splits(prices)
        oos_mask = val_mask | test_mask
        masks = {"train": ~val_mask & ~test_mask, "val": val_mask, "oos": oos_mask, "test": test_mask}

        cfg = make_futures_config()

        # Load grid and select top K by Val PF margin
        grid_df = pd.read_parquet(H10_GRID_PARQUET)
        topk_df = _select_top_by_val_pf_margin(grid_df, K_TOP)

        print(f"H14: selected top {len(topk_df)} configs by Val PF margin (excluding frozen H10)")
        print(f"  top1 val_pf_margin={topk_df['val_pf_margin'].iloc[0]:.4f}, val_pf={topk_df['val_profit_factor'].iloc[0]:.4f}")

        # Rebuild OOS for subset
        print("Re-running subset to get per-combo OOS returns...")
        grid_meta, oos_matrix, oos_index = _rebuild_grid_oos_for_subset(
            prices, volumes, vix_hourly, cfg, masks, topk_df
        )

        # Build per-symbol net contributions for the frozen config on OOS (to compute LOO PF)
        # Get frozen positions and contribs
        exits = _build_exit_inputs(prices)
        atr_e, vol_exit_e = exits
        from run_h10_intraday_tsmom_pfopt_experiment import (
            apply_exits_hourly,
            build_hourly_target,
            vol_scaled_tsmom_hourly,
        )
        base = vol_scaled_tsmom_hourly(prices, vol_window_long=1008, vol_window_short=252)
        hourly_target = build_hourly_target(base, None, 1008, False, vix_hourly, prices.index)
        positions = apply_exits_hourly(
            hourly_target, prices, atr_e, vol_exit_e,
            trailing_mult=2.0, max_hold_bars=60, vol_limit_mult=1.5, vol_floor_fraction=0.25,
            target_vol=0.15, min_trade_interval=0,
        )
        contrib_frozen = per_symbol_contributions(run_backtest(prices=prices, signals=positions, volumes=volumes, config=cfg), prices, cfg)

        results = []
        min_pf_gate = GATES["min_profit_factor"]
        min_sr_gate = GATES["min_sharpe"]

        # Get OOS return series for frozen (sum of contribs gives per-bar net return in engine units? check)
        # per_symbol_contributions returns per-bar $ P&L contributions? Or returns. Let us look up.
        frozen_oos_pnl = contrib_frozen.sum(axis=1)
        # Convert to returns if needed - look up how used
        frozen_oos_ret = frozen_oos_pnl / INITIAL_CAPITAL if False else frozen_oos_pnl  # but need to be consistent with engine returns scale
        # Actually engine returns are per-bar net returns (frac). Contribs from H11: per_symbol_contributions gives contributions - check units.
        # From H11: it uses res.returns and positions; easier to get frozen returns from engine
        res_frozen = run_backtest(prices=prices, signals=positions, volumes=volumes, config=cfg)
        frozen_oos_ret_series = res_frozen.returns[oos_mask]

        for i in range(len(grid_meta)):
            cfg_row = grid_meta.iloc[i]
            oos_ret = pd.Series(oos_matrix[i, :], index=oos_index)
            # bootstrap PF CI
            pf_boot = bootstrap_profit_factor_distribution(oos_ret.values, seed=SEED + i, n_bootstrap=N_BOOTSTRAP)
            pf_ci_lb = float(np.percentile(pf_boot, 2.5))
            pf_ci_ub = float(np.percentile(pf_boot, 97.5))
            pf_med = float(np.median(pf_boot))
            pf_ge_13 = float(np.mean(pf_boot >= 1.3))

            # DSR at N=K_TOP (worst-case N trials = K)
            sr_oos = float(sharpe_ratio(oos_ret))
            n_obs = len(oos_ret)
            var_trials = float(np.var(grid_meta["oos_sharpe"].values, ddof=1)) if len(grid_meta) > 1 else 0.0
            # compute moments of oos_ret
            skew = float(stats.skew(oos_ret.values))
            kurt = float(stats.kurtosis(oos_ret.values, fisher=False))
            # worst-case DSR at N=K
            sr0_k, _ = _expected_max_sharpe(K_TOP, var_trials / PERIODS_PER_YEAR)
            # deflated using formula with sr0 = E[max SR | N trials] scaled appropriately
            dsr_adj_k, p_k = deflated_sharpe_ratio(sr_oos, K_TOP, n_obs, var_trials, skew, kurt)
            # recompute properly: deflated_sharpe_ratio takes observed_sr annualized, n_trials, n_obs, var_trials (annualized var of trials?), skew/kurt of returns
            # but deflated_sharpe_ratio expects var_trials as variance of per-trial Sharpe estimates
            dsr_adj_k, p_k = deflated_sharpe_ratio(sr_oos, K_TOP, n_obs, float(np.var(grid_meta["oos_sharpe"].values, ddof=1)), skew, kurt)

            # LOO dispensability on frozen contribs? Or better compute contribs for this config?
            # Easier: rebuild positions for this config and compute contribs
            vw = int(cfg_row["vol_window_long"])
            smooth_span = None if str(cfg_row["smooth_span"]) == "none" else int(cfg_row["smooth_span"])
            regime = bool(cfg_row["regime_scaling"])
            min_int = int(cfg_row["min_trade_interval"])
            tm = float(cfg_row["trailing_mult"])
            mhb = int(cfg_row["max_hold_bars"])
            vlm = float(cfg_row["vol_limit_mult"])
            vff = float(cfg_row["vol_floor_fraction"])
            key_t = (vw, smooth_span, regime)
            from run_h10_intraday_tsmom_pfopt_experiment import (
                apply_exits_hourly,
                build_hourly_target,
                vol_scaled_tsmom_hourly,
            )
            # build if needed
            if not hasattr(_rebuild_grid_oos_for_subset, '_targets'):
                _rebuild_grid_oos_for_subset._targets = {}
            if key_t not in _rebuild_grid_oos_for_subset._targets:
                base_s = vol_scaled_tsmom_hourly(prices, vol_window_long=vw, vol_window_short=vw // 4)
                _rebuild_grid_oos_for_subset._targets[key_t] = build_hourly_target(base_s, smooth_span, vw, regime, vix_hourly, prices.index)
            pos_c = apply_exits_hourly(
                _rebuild_grid_oos_for_subset._targets[key_t], prices, atr_e, vol_exit_e,
                trailing_mult=tm, max_hold_bars=mhb, vol_limit_mult=vlm, vol_floor_fraction=vff,
                target_vol=0.15, min_trade_interval=min_int,
            )
            contrib_c = per_symbol_contributions(run_backtest(prices=prices, signals=pos_c, volumes=volumes, config=cfg), prices, cfg)
            loo_pf = _leave_one_out_pf(contrib_c, oos_mask)
            all_disp = all(v >= min_pf_gate for v in loo_pf.values())

            res = {
                "combo_index": int(cfg_row["combo_index"]) if "combo_index" in cfg_row else i,
                "val_pf_margin": float(cfg_row["val_pf_margin"]),
                "val_profit_factor": float(cfg_row["val_profit_factor"]),
                "val_sharpe": float(cfg_row["val_sharpe"]),
                "oos_sharpe": sr_oos,
                "oos_profit_factor": _profit_factor(oos_ret.values),
                "pf_boot_ci_lb": pf_ci_lb,
                "pf_boot_ci_ub": pf_ci_ub,
                "pf_boot_median": pf_med,
                "pf_boot_geq_1_3": pf_ge_13,
                "dsr_adj_sharpe_at_k": float(dsr_adj_k),
                "p_at_k": float(p_k),
                "loo_pf": {k: float(v) for k, v in loo_pf.items()},
                "all_symbols_dispensable": bool(all_disp),
            }
            results.append(res)
        results_df = pd.DataFrame(results)

        # Find passing configs
        passes = results_df[
            (results_df["pf_boot_ci_lb"] >= min_pf_gate)
            & (results_df["dsr_adj_sharpe_at_k"] >= min_sr_gate)
            & (results_df["all_symbols_dispensable"])
        ]
        all_pass_flag = len(passes) >= 1

        summary = {
            "experiment_id": tracker.current_experiment.experiment_id if tracker.current_experiment else "unknown",
            "hypothesis": "H14",
            "k_top": K_TOP,
            "n_trials_family_k": K_TOP,
            "topk_count": len(topk_df),
            "configs_evaluated": len(results_df),
            "min_pf_gate": min_pf_gate,
            "min_sr_gate": min_sr_gate,
            "n_passing": len(passes),
            "all_pass": bool(all_pass_flag),
            "verdict": "PASS" if all_pass_flag else "REJECT",
            "null_h0": "no config in top-K-by-Val-PF-margin passes all three gates",
            "passes": passes.to_dict(orient="records") if len(passes) > 0 else [],
        }

        exp_dir = Path(tracker.log_dir) / "artifacts" / (tracker.current_experiment.experiment_id if tracker.current_experiment else "unknown")
        exp_dir.mkdir(parents=True, exist_ok=True)
        results_df.to_parquet(exp_dir / "h14_results.parquet", index=False)
        topk_df.to_parquet(exp_dir / "topk_selected.parquet", index=False)
        grid_meta.to_parquet(exp_dir / "subset_oos_metrics.parquet", index=False)
        with open(exp_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        tracker.log_artifact("summary", exp_dir / "summary.json")
        tracker.log_artifact("results", exp_dir / "h14_results.parquet")
        tracker.finish_experiment(status="completed")

        total_elapsed = time.time() - t_start
        print("\n" + "=" * 72)
        print("  H14 PF-margin-targeted selection audit:")
        print(f"    Top K={K_TOP} by Val PF margin tested")
        print(f"    Passing configs: {len(passes)}")
        print(f"    Verdict: {summary['verdict']} (H0 {'' if all_pass_flag else 'NOT '}rejected)")
        print(f"    Time: {total_elapsed/60:.1f} min")
        print("=" * 72)
        return 0 if all_pass_flag else 1
    except Exception as e:
        import traceback
        traceback.print_exc()
        tracker.finish_experiment(status="failed", error=str(e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
