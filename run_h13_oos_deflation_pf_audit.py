#!/usr/bin/env python3
"""H13: OOS-level deflation & PF-margin fragility audit.

H12 deflated the *Val* (selection-metric) Sharpe of the H10
selected config and certified it against selection bias. Two
bounded follow-ups remain, both artifact-reuse-only (no new
engine code, no new signal machinery, expected < 0.1 CPU-h):

  1. OOS worst-case deflation. The Deflated Sharpe Ratio of
     the selected config's OOS Sharpe (1.275759) under the
     worst-case assumption that OOS had been the selection
     metric with N=13,824 trials. Moments: the OOS-Sharpe
     distribution mean/SD from the H12 artifact
     grid_oos_metrics.parquet (the 13,824-combo re-run), and
     the OOS-return skew/kurtosis/n from the H10 artifact
     returns.parquet on the OOS mask. Reported both at the
     worst-case N=13,824 (a conservative "peeking" bound --
     the config was actually selected on Val) and at the
     single-peek N=1 (the true deflation of a single OOS
     evaluation; E[max SR | null, N=1] = 0, so the DSR
     reduces to the non-normality-corrected Sharpe
     significance test, Bailey & Lopez de Prado 2014 Eq. 4
     with SR0 = 0).

  2. PF-margin fragility decomposition of the pooled OOS
     profit factor (1.304, margin +0.004 over the 1.3 gate):
       (a) net per-symbol OOS profit factors via the H11
           per-symbol net-return decomposition
           (per_symbol_contributions: gross P&L minus
           per-symbol transaction costs, reconstructed from the
           engine's post-constraint positions; the sum over
           symbols reconstructs the engine's net returns);
       (b) bootstrap 95% CI of the OOS PF (2,000 seeded i.i.d.
           resamples of the OOS net returns, the same scheme
           as the H11 Sharpe bootstrap);
       (c) PF under the H11 shifted splits (50/25/25, 60/20/20,
           45/30/25 -- positions fixed, only the OOS mask
           changes), confirmed against the original H11 E4a
           values, with per-symbol and per-VIX-regime
           attribution of the shortfall;
       (d) the cost multiplier at which the selected config's
           OOS PF crosses 1.3 (fine sweep + bisection; H11
           estimated 1.5418x by linear interpolation on a
           4-point grid -- verified here against the H12 re-run
           positions; costs do not affect the position path).

Null (H0, pre-registered in HYPOTHESIS.md): the OOS edge is
fragile -- (i) worst-case DSR-adjusted OOS Sharpe < 1.0, OR
(ii) OOS PF bootstrap 95% CI lower bound < 1.3, OR (iii) at
least one symbol is indispensable (its removal drops pooled
OOS PF < 1.3). PASS iff all three nulls are rejected.

Constraints: no live trading, no secrets, no paid data, Test
never enters selection, <= 4 CPU-h per experiment, reuse
existing engine / tracking / validation infrastructure.
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

# Reuse H10 constants (universe, gates, seeds, cost defaults).
from run_h10_intraday_tsmom_pfopt_experiment import (
    FUTURES_UNIVERSE,
    GATES,
    SEED,
    VIX_SYMBOL,
    make_futures_config,
    regime_labels,
)

# Reuse the H11 public API (frozen-config position builder,
# net per-symbol decomposition, cost-stressed configs).
from run_h11_robustness_experiment import (
    FROZEN_CONFIG,
    _build_exit_inputs,
    build_positions,
    make_cost_stressed_config,
    per_symbol_contributions,
)

# Reuse H12 machinery (DSR, expected-max-Sharpe, cached data,
# splits, period metrics, trade counting -- single source of
# truth for the deflation math and the H10 window).
from run_h12_selection_bias_audit import (
    N_GRID,
    PERIODS_PER_YEAR,
    SEL,
    _count_in,
    _expected_max_sharpe,
    _load_cached_data,
    _period_metrics,
    _splits,
    deflated_sharpe_ratio,
)

EXPERIMENT_NAME = "h13_oos_deflation_pf_audit"
EXPERIMENT_DESC = (
    "H13: OOS-level deflation (worst-case N=13,824 peeking "
    "bound and single-peek N=1 DSR) and PF-margin fragility "
    "decomposition (net per-symbol PF, bootstrap PF CI, "
    "shifted-split PF with symbol/regime attribution, cost "
    "break-even verification)"
)

# H12 artifact (per-combo OOS metrics for all 13,824 configs).
H12_ARTIFACT_DIR = Path(".experiments/artifacts/exp_2026-10-13T12-51-06-515939Z")
H12_GRID_PARQUET = H12_ARTIFACT_DIR / "grid_oos_metrics.parquet"

# Original H11 experiment (E4a shifted splits to confirm).
H11_ORIGINAL_ARTIFACT_DIR = Path(".experiments/artifacts/exp_2026-10-11T18-40-37-427062Z")
H11_ORIGINAL_SUMMARY = H11_ORIGINAL_ARTIFACT_DIR / "summary.json"

# H11 E4a shifted split boundaries (train/val/test fractions).
SHIFTED_SPLITS = [
    ("50/25/25", 0.50, 0.25),
    ("60/20/20", 0.60, 0.20),
    ("45/30/25", 0.45, 0.30),
]

# Bootstrap of the OOS PF (same scheme as the H11 Sharpe
# bootstrap: i.i.d. resampling with replacement, seeded).
N_BOOTSTRAP = 2000

# Cost break-even bisection tolerance (in cost-multiplier units).
COST_BREAKEVEN_TOL = 0.002
COST_SWEEP = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]

MIN_PF = GATES["min_profit_factor"]
MIN_SR = GATES["min_sharpe"]


# ---------------------------------------------------------------------------
# DSR for a single-peek (N=1) OOS evaluation
# ---------------------------------------------------------------------------
def deflated_sharpe_ratio_single_peek(observed_sr, n_obs, var_trials, skewness, kurtosis):
    """DSR of a single OOS evaluation (N=1 trial).

    With one trial there is no selection, so the deflation
    benchmark is E[max SR | null, N=1] = 0 (the expectation
    of a single null Sharpe estimate). The test statistic is
    the Bailey & Lopez de Prado (2014) Eq. 4 statistic with
    SR0 = 0, retaining the non-normality (skew/kurtosis)
    correction, which is scale-invariant in SR units.

    Returns (dsr_value, p_value) with p = P(true SR > 0).
    """
    sr_per_bar = observed_sr / np.sqrt(PERIODS_PER_YEAR)
    numerator = sr_per_bar * np.sqrt(n_obs - 1.0)
    skew_term = 1.0 - skewness * sr_per_bar
    kurt_term = (kurtosis - 1.0) / 4.0 * sr_per_bar**2
    denom = float(np.sqrt(max(1e-12, skew_term + kurt_term)))
    dsr_adj = numerator / denom
    p = float(stats.norm.cdf(dsr_adj))
    return float(observed_sr * p), float(1.0 - p)


# ---------------------------------------------------------------------------
# Profit-factor helpers
# ---------------------------------------------------------------------------
def _profit_factor(returns):
    """Profit factor of a net-return series (gross profit /
    gross loss; +inf if no losing bars)."""
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) == 0:
        return float("nan")
    gp = float(r[r > 0].sum())
    gl = float(abs(r[r < 0].sum()))
    return gp / gl if gl > 0 else float("inf")


def _shifted_splits(prices, train_frac, val_frac):
    """Split masks under shifted boundaries (positions are
    fixed; only the OOS mask changes, exactly as H11 E4a)."""
    n = len(prices)
    train_end = prices.index[int(n * train_frac)]
    val_end = prices.index[int(n * (train_frac + val_frac))]
    train_mask = prices.index <= train_end
    val_mask = (prices.index > train_end) & (prices.index <= val_end)
    test_mask = prices.index > val_end
    return train_mask, val_mask, test_mask


def bootstrap_profit_factor_distribution(returns, seed=SEED, n_bootstrap=N_BOOTSTRAP):
    """Bootstrap distribution of the profit factor.

    Deterministic given ``seed`` (i.i.d. resampling with
    replacement -- the same scheme as the H11 Sharpe
    bootstrap).
    """
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    rng = np.random.default_rng(seed)
    out = np.empty(n_bootstrap, dtype=float)
    for i in range(n_bootstrap):
        idx = rng.integers(0, len(r), size=len(r))
        out[i] = _profit_factor(r[idx])
    return out


def _per_symbol_pf(contrib, mask):
    """Net profit factor of each symbol's contribution on a mask."""
    return {sym: _profit_factor(contrib[sym][mask]) for sym in contrib.columns}


def _leave_one_out_pf(contrib, mask):
    """Pooled PF with each symbol removed (dispensability)."""
    pooled = contrib.sum(axis=1)
    return {sym: _profit_factor(pooled[mask] - contrib[sym][mask]) for sym in contrib.columns}


def _regime_pf(pooled_returns, regimes, mask):
    """Pooled PF within each VIX regime on a mask."""
    out = {}
    for reg in ("bull", "sideways", "bear"):
        m = mask & (regimes == reg)
        out[reg] = _profit_factor(pooled_returns[m])
        out[f"{reg}_bars"] = int(m.sum())
    return out


def _oos_pf_of_positions(positions, prices, volumes, cfg, oos_mask):
    """Run the engine on fixed positions with ``cfg`` and
    return (OOS PF, OOS Sharpe, OOS trades)."""
    res = run_backtest(prices=prices, signals=positions, volumes=volumes, config=cfg)
    oos_ret = res.returns[oos_mask]
    om = _period_metrics(oos_ret, _count_in(res.trades, oos_mask, prices))
    return om["profit_factor"], om["sharpe"], om["trades"]


def _cost_breakeven(positions, prices, volumes, oos_mask, lo, hi, tol=COST_BREAKEVEN_TOL):
    """Bisect the cost multiplier at which OOS PF = 1.3.

    ``lo`` must keep PF >= 1.3 and ``hi`` must drop below;
    PF is monotone non-increasing in the cost multiplier
    (all cost components scale together, position path
    fixed).
    """
    pf_lo, _, _ = _oos_pf_of_positions(
        positions, prices, volumes, make_cost_stressed_config(lo), oos_mask
    )
    pf_hi, _, _ = _oos_pf_of_positions(
        positions, prices, volumes, make_cost_stressed_config(hi), oos_mask
    )
    assert pf_lo >= MIN_PF >= pf_hi, (lo, pf_lo, hi, pf_hi)
    while hi - lo > tol:
        mid = (lo + hi) / 2.0
        pf_mid, _, _ = _oos_pf_of_positions(
            positions, prices, volumes, make_cost_stressed_config(mid), oos_mask
        )
        if pf_mid >= MIN_PF:
            lo, pf_lo = mid, pf_mid
        else:
            hi, pf_hi = mid, pf_mid
    return (lo + hi) / 2.0, pf_lo, pf_hi


def _selected_row(grid_meta):
    """Row of the frozen selected config in a re-run grid."""
    smooth = "none" if SEL["smooth_span"] is None else str(SEL["smooth_span"])
    mask = (
        (grid_meta["vol_window_long"] == SEL["vol_window_long"])
        & (grid_meta["smooth_span"] == smooth)
        & (grid_meta["regime_scaling"] == SEL["regime_scaling"])
        & (grid_meta["min_trade_interval"] == SEL["min_trade_interval"])
        & (grid_meta["trailing_mult"] == SEL["trailing_mult"])
        & (grid_meta["max_hold_bars"] == SEL["max_hold_bars"])
        & (grid_meta["vol_limit_mult"] == SEL["vol_limit_mult"])
        & (grid_meta["vol_floor_fraction"] == SEL["vol_floor_fraction"])
    )
    assert mask.sum() == 1, f"expected 1 selected row, got {mask.sum()}"
    return grid_meta.loc[mask].iloc[0]


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
            "gates": GATES,
            "seed": SEED,
            "h10_selected_config": SEL,
            "frozen_config": FROZEN_CONFIG,
            "n_trials_worst_case": N_GRID,
            "n_bootstrap": N_BOOTSTRAP,
            "shifted_splits": [s[0] for s in SHIFTED_SPLITS],
            "cost_sweep": COST_SWEEP,
            "cost_breakeven_tol": COST_BREAKEVEN_TOL,
        },
        data_sources={
            "source": "h10_h12_artifact_cache",
            "symbols": FUTURES_UNIVERSE,
            "vix": VIX_SYMBOL,
            "interval": "1h",
            "h10_artifact": ".experiments/artifacts/exp_2026-10-11T17-41-18-169363Z",
            "h12_artifact": str(H12_ARTIFACT_DIR),
        },
        compute_budget={"max_cpu_hours": 4.0},
        random_seeds={"numpy": SEED, "python": SEED},
    )
    print(f"[H13] started {exp_id}")

    try:
        # =================================================================
        # Data: H10 cached window + H12 grid re-run artifacts
        # =================================================================
        prices, volumes, vix_hourly, h10_returns = _load_cached_data()
        val_mask, test_mask = _splits(prices)
        oos_mask = val_mask | test_mask
        grid_oos = pd.read_parquet(H12_GRID_PARQUET)
        sel_grid_row = _selected_row(grid_oos)

        oos_ret = h10_returns[oos_mask]
        n_obs = len(oos_ret)
        skew = float(stats.skew(oos_ret.values))
        kurt = float(stats.kurtosis(oos_ret.values, fisher=False))

        # OOS-Sharpe distribution moments (the 13,824-combo re-run).
        oos_sr_dist = grid_oos["oos_sharpe"].astype(float)
        var_trials_oos = float(oos_sr_dist.var(ddof=1))
        mean_trials_oos = float(oos_sr_dist.mean())
        std_trials_oos = float(oos_sr_dist.std(ddof=1))

        # Selected config's OOS Sharpe (H12 re-run / H10 artifact).
        sel_oos_sharpe = float(sel_grid_row["oos_sharpe"])
        sel_oos_pf = float(sel_grid_row["oos_profit_factor"])
        h12_summary = json.loads((H12_ARTIFACT_DIR / "summary.json").read_text())
        assert abs(sel_oos_sharpe - h12_summary["rerun_oos_metrics"]["selected_oos_sharpe"]) < 1e-12
        assert (
            abs(sel_oos_pf - h12_summary["rerun_oos_metrics"]["selected_oos_profit_factor"]) < 1e-12
        )
        print(
            f"[H13] window: {prices.shape} OOS bars={n_obs} "
            f"selected OOS SR={sel_oos_sharpe:.6f} PF={sel_oos_pf:.6f}"
        )
        print(
            f"[H13] OOS-Sharpe grid: mean={mean_trials_oos:.6f} "
            f"SD={std_trials_oos:.6f} var={var_trials_oos:.6f}"
        )
        print(f"[H13] OOS return moments: skew={skew:.4f} kurtosis={kurt:.4f}")

        # =================================================================
        # 1. OOS deflation: worst-case (N=13,824) and single-peek (N=1)
        # =================================================================
        print("[H13] --- 1. OOS deflation (DSR) ---")
        sr0_wc_per_bar, max_z_wc = _expected_max_sharpe(N_GRID, var_trials_oos / PERIODS_PER_YEAR)
        sr0_wc_annual = sr0_wc_per_bar * np.sqrt(PERIODS_PER_YEAR)
        dsr_wc, p_wc = deflated_sharpe_ratio(
            sel_oos_sharpe, N_GRID, n_obs, var_trials_oos, skew, kurt
        )
        dsr_1, p_1 = deflated_sharpe_ratio_single_peek(
            sel_oos_sharpe, n_obs, var_trials_oos, skew, kurt
        )
        print(f"  worst-case N={N_GRID}: E[max SR | null] = {sr0_wc_annual:.4f} (annualized)")
        print(f"  DSR (worst-case) = {dsr_wc:.4f}  p = {p_wc:.6f}")
        print(f"  DSR (single-peek N=1) = {dsr_1:.4f}  p = {p_1:.6f}")

        # =================================================================
        # Frozen pipeline: one backtest, bit-exact reproduction check
        # =================================================================
        atr, vol_exit = _build_exit_inputs(prices)
        positions = build_positions(prices, atr, vol_exit, vix_hourly, **FROZEN_CONFIG)
        cfg = make_futures_config()
        res = run_backtest(prices=prices, signals=positions, volumes=volumes, config=cfg)
        max_ret_diff = float((res.returns - h10_returns).abs().max())
        assert max_ret_diff < 1e-9, max_ret_diff
        print(
            f"[H13] frozen pipeline reproduces the H10 artifact "
            f"returns (max |diff| = {max_ret_diff:.2e})"
        )

        # =================================================================
        # 2a. Net per-symbol OOS decomposition
        # =================================================================
        print("[H13] --- 2a. Net per-symbol OOS PF ---")
        contrib = per_symbol_contributions(res, prices, cfg)
        pooled = contrib.sum(axis=1)
        recon_max_diff = float((pooled[oos_mask] - res.returns[oos_mask]).abs().max())
        assert recon_max_diff < 1e-9, recon_max_diff
        sym_pf = _per_symbol_pf(contrib, oos_mask)
        sym_pnl = {sym: float(contrib[sym][oos_mask].sum()) for sym in contrib.columns}
        total_pnl = float(pooled[oos_mask].sum())
        sym_share = {sym: sym_pnl[sym] / total_pnl for sym in contrib.columns}
        lou_pf = _leave_one_out_pf(contrib, oos_mask)
        print(f"  reconstruction max |diff| = {recon_max_diff:.2e}")
        for sym in contrib.columns:
            print(
                f"  {sym}: net PF={sym_pf[sym]:.4f} "
                f"P&L={sym_pnl[sym]:+.4f} (share {sym_share[sym]:.3f}) "
                f"leave-one-out PF={lou_pf[sym]:.4f}"
            )

        # =================================================================
        # 2b. Bootstrap 95% CI of the OOS PF
        # =================================================================
        print("[H13] --- 2b. OOS PF bootstrap CI ---")
        pf_boot = bootstrap_profit_factor_distribution(
            res.returns[oos_mask].values, seed=SEED, n_bootstrap=N_BOOTSTRAP
        )
        ci_lo = float(np.percentile(pf_boot, 2.5))
        ci_hi = float(np.percentile(pf_boot, 97.5))
        pf_boot_median = float(np.median(pf_boot))
        pf_pass_frac = float((pf_boot >= MIN_PF).mean())
        print(
            f"  OOS PF bootstrap 95% CI = [{ci_lo:.4f}, {ci_hi:.4f}] "
            f"(median {pf_boot_median:.4f}, P(PF >= 1.3) = "
            f"{pf_pass_frac:.4%})"
        )

        # =================================================================
        # 2c. Shifted splits (confirm H11 E4a + attribution)
        # =================================================================
        print("[H13] --- 2c. Shifted splits ---")
        regimes = regime_labels(vix_hourly)
        base_regime_pf = _regime_pf(pooled, regimes, oos_mask)
        shifted_rows = []
        shifted_sym_rows = []
        shifted_regime_rows = []
        for label, train_frac, val_frac in SHIFTED_SPLITS:
            _, s_val, s_test = _shifted_splits(prices, train_frac, val_frac)
            s_oos = s_val | s_test
            om = _period_metrics(pooled[s_oos], _count_in(res.trades, s_oos, prices))
            spf = _per_symbol_pf(contrib, s_oos)
            srgp = _regime_pf(pooled, regimes, s_oos)
            shifted_rows.append(
                {
                    "split": label,
                    "train_frac": train_frac,
                    "val_frac": val_frac,
                    "oos_bars": int(s_oos.sum()),
                    "oos_sharpe": om["sharpe"],
                    "oos_profit_factor": om["profit_factor"],
                    "oos_max_drawdown": om["max_drawdown"],
                    "oos_trades": om["trades"],
                }
            )
            for sym in contrib.columns:
                shifted_sym_rows.append(
                    {
                        "split": label,
                        "symbol": sym,
                        "net_profit_factor": spf[sym],
                        "net_pnl": float(contrib[sym][s_oos].sum()),
                    }
                )
            for reg in ("bull", "sideways", "bear"):
                shifted_regime_rows.append(
                    {
                        "split": label,
                        "regime": reg,
                        "profit_factor": srgp[reg],
                        "bars": srgp[f"{reg}_bars"],
                        "base_profit_factor": base_regime_pf[reg],
                        "base_bars": base_regime_pf[f"{reg}_bars"],
                    }
                )
            print(
                f"  {label}: OOS bars={int(s_oos.sum())} "
                f"SR={om['sharpe']:.4f} PF={om['profit_factor']:.4f} "
                f"DD={om['max_drawdown']:.4f} trades={om['trades']}"
            )

        # Confirm against the original H11 E4a measurements.
        h11_e4a = {}
        if H11_ORIGINAL_SUMMARY.exists():
            h11_orig = json.loads(H11_ORIGINAL_SUMMARY.read_text())
            for row in h11_orig["e4_window_robustness"]["shifted_splits"]:
                h11_e4a[row["split"]] = float(row["oos_profit_factor"])
        for row in shifted_rows:
            if row["split"] in h11_e4a:
                diff = abs(row["oos_profit_factor"] - h11_e4a[row["split"]])
                assert diff < 1e-9, (row["split"], diff)
                print(
                    f"  {row['split']} PF reproduces H11 E4a "
                    f"({h11_e4a[row['split']]:.6f}, |diff|={diff:.2e})"
                )

        # Attribution: largest per-symbol and per-regime PF drops
        # vs the base OOS mask, for the gate-failing splits.
        attribution = {}
        for row in shifted_rows:
            if row["oos_profit_factor"] >= MIN_PF:
                continue
            label = row["split"]
            sym_deltas = {
                r["symbol"]: r["net_profit_factor"] - sym_pf[r["symbol"]]
                for r in shifted_sym_rows
                if r["split"] == label
            }
            reg_deltas = {
                r["regime"]: r["profit_factor"] - base_regime_pf[r["regime"]]
                for r in shifted_regime_rows
                if r["split"] == label
            }
            worst_sym = min(sym_deltas, key=sym_deltas.get)
            worst_reg = min(reg_deltas, key=reg_deltas.get)
            attribution[label] = {
                "worst_symbol": worst_sym,
                "worst_symbol_pf_delta": sym_deltas[worst_sym],
                "symbol_pf_deltas": sym_deltas,
                "worst_regime": worst_reg,
                "worst_regime_pf_delta": reg_deltas[worst_reg],
                "regime_pf_deltas": reg_deltas,
            }
            print(
                f"  {label} shortfall attribution: worst symbol "
                f"{worst_sym} (PF delta {sym_deltas[worst_sym]:+.4f}), "
                f"worst regime {worst_reg} "
                f"({reg_deltas[worst_reg]:+.4f})"
            )

        # =================================================================
        # 2d. Cost break-even verification
        # =================================================================
        print("[H13] --- 2d. Cost break-even ---")
        cost_rows = []
        for mult in COST_SWEEP:
            pf, sr, trades = _oos_pf_of_positions(
                positions, prices, volumes, make_cost_stressed_config(mult), oos_mask
            )
            cost_rows.append(
                {
                    "cost_multiplier": mult,
                    "oos_profit_factor": pf,
                    "oos_sharpe": sr,
                    "oos_trades": trades,
                }
            )
            print(f"  cost x{mult:.2f}: OOS PF={pf:.4f} SR={sr:.4f} trades={trades}")
        cost_df = pd.DataFrame(cost_rows)
        # Bracket the crossing from the sweep, then bisect.
        below = cost_df[cost_df.oos_profit_factor < MIN_PF]
        above = cost_df[cost_df.oos_profit_factor >= MIN_PF]
        lo = float(above.cost_multiplier.max())
        hi = float(below.cost_multiplier.min())
        breakeven, pf_lo, pf_hi = _cost_breakeven(positions, prices, volumes, oos_mask, lo, hi)
        h11_breakeven = None
        if H11_ORIGINAL_SUMMARY.exists():
            h11_orig = json.loads(H11_ORIGINAL_SUMMARY.read_text())
            h11_breakeven = float(
                h11_orig["e3_cost_stress"]["breakeven_cost_multiplier_for_pf_1_3"]
            )
        print(
            f"  break-even cost multiplier for PF = 1.3: "
            f"{breakeven:.4f} (bracket [{lo}, {hi}], "
            f"PF {pf_lo:.4f} / {pf_hi:.4f})"
        )
        if h11_breakeven is not None:
            print(
                f"  H11 interpolated estimate: {h11_breakeven:.4f} "
                f"(|diff| = {abs(breakeven - h11_breakeven):.4f})"
            )

        # =================================================================
        # Verdict (pre-registered)
        # =================================================================
        # H0: (i) worst-case DSR-adjusted OOS Sharpe < 1.0, OR
        # (ii) OOS PF bootstrap CI lower bound < 1.3, OR
        # (iii) at least one symbol is indispensable
        # (removal drops pooled OOS PF < 1.3).
        dsr_gate = bool(dsr_wc >= MIN_SR)
        ci_gate = bool(ci_lo >= MIN_PF)
        symbol_gate = bool(all(v >= MIN_PF for v in lou_pf.values()))
        all_pass = bool(dsr_gate and ci_gate and symbol_gate)
        verdict = "PASS" if all_pass else "REJECT"
        print(
            f"[H13] gates: worst-case DSR-adj OOS SR {dsr_wc:.4f} "
            f">= {MIN_SR} -> {'PASS' if dsr_gate else 'FAIL'}"
        )
        print(
            f"[H13] gates: PF bootstrap CI LB {ci_lo:.4f} "
            f">= {MIN_PF} -> {'PASS' if ci_gate else 'FAIL'}"
        )
        print(
            f"[H13] gates: all leave-one-out PF >= {MIN_PF} -> "
            f"{'PASS' if symbol_gate else 'FAIL'} "
            f"(min {min(lou_pf.values()):.4f})"
        )

        total_elapsed = time.time() - t_start
        summary = {
            "experiment_id": exp_id,
            "hypothesis": "H13",
            "h10_selected_config": SEL,
            "frozen_config": FROZEN_CONFIG,
            "oos_window": {
                "n_bars": n_obs,
                "return_skewness": skew,
                "return_kurtosis": kurt,
                "selected_oos_sharpe": sel_oos_sharpe,
                "selected_oos_profit_factor": sel_oos_pf,
            },
            "oos_deflation": {
                "n_trials_worst_case": N_GRID,
                "oos_sharpe_grid_mean": mean_trials_oos,
                "oos_sharpe_grid_std": std_trials_oos,
                "oos_sharpe_grid_var": var_trials_oos,
                "expected_max_sharpe_worst_case": float(sr0_wc_annual),
                "max_z_worst_case": float(max_z_wc),
                "dsr_adjusted_sharpe_worst_case": float(dsr_wc),
                "p_value_worst_case": float(p_wc),
                "dsr_adjusted_sharpe_single_peek": float(dsr_1),
                "p_value_single_peek": float(p_1),
            },
            "per_symbol_net_oos": {
                sym: {
                    "net_profit_factor": sym_pf[sym],
                    "net_pnl": sym_pnl[sym],
                    "pnl_share": sym_share[sym],
                    "leave_one_out_pooled_pf": lou_pf[sym],
                }
                for sym in contrib.columns
            },
            "pf_bootstrap": {
                "n_bootstrap": N_BOOTSTRAP,
                "seed": SEED,
                "ci_95_lower": ci_lo,
                "ci_95_upper": ci_hi,
                "median": pf_boot_median,
                "point_estimate": sel_oos_pf,
                "frac_ge_1_3": pf_pass_frac,
            },
            "shifted_splits": {
                "results": shifted_rows,
                "per_symbol": shifted_sym_rows,
                "per_regime": shifted_regime_rows,
                "h11_e4a_expected_pf": h11_e4a,
                "attribution": attribution,
            },
            "cost_breakeven": {
                "sweep": cost_rows,
                "bracket": [lo, hi],
                "breakeven_multiplier": float(breakeven),
                "pf_at_bracket": [float(pf_lo), float(pf_hi)],
                "tolerance": COST_BREAKEVEN_TOL,
                "h11_interpolated": h11_breakeven,
            },
            "reproduction_checks": {
                "returns_max_abs_diff_vs_h10": max_ret_diff,
                "per_symbol_reconstruction_max_abs_diff": recon_max_diff,
            },
            "gates": {
                "worst_case_dsr_adjusted_oos_sharpe_ge_1.0": dsr_gate,
                "pf_bootstrap_ci_lower_ge_1.3": ci_gate,
                "all_symbols_dispensable_lou_pf_ge_1.3": symbol_gate,
            },
            "all_pass": all_pass,
            "verdict": verdict,
            "total_elapsed_sec": float(round(total_elapsed, 1)),
            "compute_cpu_hours": float(round(total_elapsed / 3600, 3)),
        }

        tracker.log_dataframe(
            "per_symbol_net_oos",
            pd.DataFrame(
                {
                    "symbol": list(sym_pf.keys()),
                    "net_profit_factor": list(sym_pf.values()),
                    "net_pnl": [sym_pnl[s] for s in sym_pf],
                    "pnl_share": [sym_share[s] for s in sym_pf],
                    "leave_one_out_pooled_pf": [lou_pf[s] for s in sym_pf],
                }
            ),
        )
        tracker.log_dataframe(
            "pf_bootstrap",
            pd.DataFrame({"bootstrap_index": np.arange(N_BOOTSTRAP), "profit_factor": pf_boot}),
        )
        tracker.log_dataframe("shifted_splits", pd.DataFrame(shifted_rows))
        tracker.log_dataframe(
            "shifted_splits_per_symbol",
            pd.DataFrame(shifted_sym_rows),
        )
        tracker.log_dataframe(
            "shifted_splits_per_regime",
            pd.DataFrame(shifted_regime_rows),
        )
        tracker.log_dataframe("cost_sensitivity", cost_df)

        exp_dir = Path(tracker.log_dir) / "artifacts" / exp_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        with open(exp_dir / "summary.json", "w") as f:
            json.dump(
                summary,
                f,
                indent=2,
                default=lambda x: float(x) if isinstance(x, (np.integer, np.floating)) else str(x),
            )
        tracker.log_artifact("summary", exp_dir / "summary.json")
        tracker.finish_experiment(status="completed")

        print("\n" + "=" * 72)
        print("  H13 OOS deflation & PF-margin fragility audit:")
        print(
            f"    worst-case DSR-adj OOS Sharpe {dsr_wc:.4f} "
            f"(>= 1.0) -> {'PASS' if dsr_gate else 'FAIL'}"
        )
        print(f"    PF bootstrap CI LB {ci_lo:.4f} (>= 1.3) -> {'PASS' if ci_gate else 'FAIL'}")
        print(
            f"    all symbols dispensable (min LOO PF "
            f"{min(lou_pf.values()):.4f} >= 1.3) -> "
            f"{'PASS' if symbol_gate else 'FAIL'}"
        )
        print(
            f"  OVERALL: {verdict}  "
            f"({total_elapsed / 60:.1f} min, "
            f"{total_elapsed / 3600:.3f} CPU-h)"
        )
        print("=" * 72)
        return 0 if all_pass else 1
    except Exception as e:  # noqa: BLE001 -- top-level experiment harness: any failure must finish the tracker and return a verdict
        import traceback

        traceback.print_exc()
        tracker.finish_experiment(status="failed", error=str(e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
