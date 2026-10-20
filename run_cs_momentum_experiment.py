#!/usr/bin/env python3
"""
Cross-sectional momentum experiment on 10 equity ETFs (Hypothesis H2).

Implements the hypothesis from HYPOTHESIS_SPEC.md (H2): a cross-sectional
momentum strategy (top-N vs bottom-N) on 10 liquid equity ETFs, vol-scaled,
long/short dollar-neutral, with the same strict PROMPT_V2 evidence gates.

Mechanism: Asness, Moskowitz & Pedersen (2013) - relative-performance momentum.
Under-reaction to earnings/news causes recent winners to keep outperforming.

Pre-registered:
  * Universe: 10 equity ETFs (SPY, QQQ, IWM, EFA, EEM, VWO, EWJ, EWZ, INDA, VNQ)
  * Splits: Train 2015-2019, Val 2020-2021, Test 2022-2024 (protected).
  * Signal: 12-month momentum (pct_change(lookback).shift(skip)), dollar-neutral
    rank-based (top-N long, bottom-N short), volatility-scaled to 15% target,
    monthly rebalance.
  * Parameter selection: grid over (lookback, skip, n_top, long_only) scored by
    internal walk-forward Sharpe on TRAIN only. Selection NOT using Val/Test.
  * Evidence gates: identical strict PROMPT_V2 gates as the TSMOM experiment.
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
# PRE-REGISTERED CONFIGURATION
# ============================================================
UNIVERSE = ["SPY", "QQQ", "IWM", "EFA", "EEM", "VWO", "EWJ", "EWZ", "INDA", "VNQ"]
VIX_SYMBOL = "^VIX"

START_DATE = "2015-01-01"
END_DATE = "2024-12-31"
TRAIN_END = "2019-12-31"
VAL_END = "2021-12-31"  # Test = 2022-2024 (protected)

LOOKBACKS = [63, 126, 252]
SKIPS = [1, 5, 21]
N_TOP_CHOICES = [1, 3, 5]
LONG_ONLY_CHOICES = [True, False]
TARGET_VOL = 0.15
VOL_WINDOW = 63

GATES = {
    "min_sharpe": 1.0,
    "min_trades": 200,
    "min_profit_factor": 1.3,
    "max_drawdown": 0.15,
    "min_walkforward_stability": 0.7,
    "min_perturbed_sharpe_ratio": 0.5,
    "min_worst_regime_sharpe": 0.3,
    "max_p_value": 0.05,
    "alpha_multiple_testing": "benjamini_hochberg",
}

SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_LEVERAGE = 5.0
MAX_POSITION_SIZE = 2.0
COST_MODEL = {
    "equity_commission_bps": 1.0,
    "equity_spread_bps": 1.0,
    "equity_impact_bps_per_pct_adv": 0.1,
}

EXPERIMENT_NAME = "cs_momentum_10etf_v1"
EXPERIMENT_DESC = (
    "Volatility-scaled cross-sectional momentum (Asness Moskowitz Pedersen 2013) "
    "on 10 equity ETFs. Train 2015-2019, Val 2020-2021, Test 2022-2024 protected. "
    "Grid selection on TRAIN walk-forward only; gates on pooled Val+Test OOS."
)


def split_returns_by_date(returns):
    train = returns[returns.index <= TRAIN_END]
    val = returns[(returns.index > TRAIN_END) & (returns.index <= VAL_END)]
    test = returns[returns.index > VAL_END]
    oos = returns[returns.index > TRAIN_END]
    return train, val, test, oos


def make_config(allow_short):
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


def resample_monthly_signals(signals):
    monthly = signals.resample("ME").last()
    return monthly.reindex(signals.index, method="ffill").fillna(0)


def cs_momentum_vol_scaled(
    prices, lookback, skip, long_only, target_vol=TARGET_VOL, vol_window=VOL_WINDOW
):
    """Cross-sectional momentum with portfolio-level vol targeting.

    Base signal: direction from 12-month return (skip-period). For long/short the
    rank-based top/bottom-N from run_strategy is used; here we build the direction
    per asset (sign of momentum) and apply inverse-vol risk-parity + portfolio
    vol targeting so the construction remains comparable to H1.
    """
    pct = prices.pct_change()
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
    port_ret = (w_raw.shift(1) * pct).sum(axis=1).ffill()
    port_vol = port_ret.rolling(vol_window).std() * np.sqrt(252)
    port_vol = port_vol.replace(0, np.nan)
    scale = (target_vol / port_vol).clip(0.0, 3.0).ffill().fillna(0.0)
    w = w_raw.multiply(scale, axis=0).clip(-MAX_POSITION_SIZE, MAX_POSITION_SIZE)
    return w.ffill().fillna(0.0)


def regime_labels(vix_daily):
    vix = vix_daily.ffill()
    reg = pd.Series(index=vix.index, dtype=object)
    reg[vix < 20] = "bull"
    reg[(vix >= 20) & (vix <= 30)] = "sideways"
    reg[vix > 30] = "bear"
    return reg


def wf_oos_sharpes(train_returns, n_splits=4):
    vals = train_returns.values
    folds = walk_forward_splits(len(vals), n_splits=n_splits)
    out = []
    for tr_idx, te_idx in folds:
        te = vals[te_idx]
        if len(te) > 1 and te.std() > 0:
            out.append(sharpe_ratio(te))
    return out


def main():
    np.random.seed(SEED)
    tracker = get_tracker()
    exp_id = tracker.start_experiment(
        name=EXPERIMENT_NAME,
        description=EXPERIMENT_DESC,
        config={
            "universe": UNIVERSE,
            "start_date": START_DATE,
            "end_date": END_DATE,
            "data_splits": {
                "train_end": TRAIN_END,
                "val_end": VAL_END,
                "test_start": "2022-01-01",
            },
            "lookbacks": LOOKBACKS,
            "skips": SKIPS,
            "n_top_choices": N_TOP_CHOICES,
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
        print("Fetching data...")
        fetcher = get_data_fetcher()
        raw = fetcher.fetch_yahoo(
            UNIVERSE + [VIX_SYMBOL], START_DATE, END_DATE, "1d", use_cache=True
        )
        prices = pd.DataFrame({s: raw[s]["close"] for s in UNIVERSE})
        vol = pd.DataFrame({s: raw[s]["volume"] for s in UNIVERSE})
        prices = prices.ffill().dropna(how="all")
        vol = vol.reindex(prices.index).ffill().fillna(0)
        vix_df = raw.get(VIX_SYMBOL)
        vix = (
            vix_df["close"]
            if vix_df is not None and not vix_df.empty
            else pd.Series(np.nan, index=prices.index)
        )
        vix = vix.reindex(prices.index).ffill()
        adv = vol.rolling(20).mean().iloc[-1]
        print(f"Loaded {len(prices.columns)} assets x {len(prices)} days")
        tracker.log_dataframe("prices", prices)
        tracker.log_dataframe("volumes", vol)
        tracker.log_dataframe("vix_close", vix.to_frame("vix"))

        # Benchmark: equal-weight buy-and-hold (vol-scaled) on the 10 ETFs
        print("Benchmark equal-weight...")
        bh_cfg = make_config(False)
        bh_signals = run_strategy(
            prices, "buy_and_hold", weight=1.0 / len(prices.columns)
        )
        bh_signals = resample_monthly_signals(bh_signals)
        bh_result = run_backtest(
            prices=prices, signals=bh_signals, volumes=vol, adv=adv, config=bh_cfg
        )
        tracker.log_dataframe(
            "benchmark_equity", bh_result.equity_curve.to_frame("equity")
        )

        grid = list(
            itertools.product(LONG_ONLY_CHOICES, LOOKBACKS, SKIPS, N_TOP_CHOICES)
        )
        print(f"Grid search on TRAIN period ({len(grid)} combos)...")
        records = []
        for i, (long_only, lb, sk, n_top) in enumerate(grid):
            allow_short = not long_only
            sig = cs_momentum_vol_scaled(prices, lb, sk, long_only)
            sig_m = resample_monthly_signals(sig)
            cfg = make_config(allow_short)
            res = run_backtest(
                prices=prices, signals=sig_m, volumes=vol, adv=adv, config=cfg
            )
            tr, va, te, oo = split_returns_by_date(res.returns)
            train_sr = sharpe_ratio(tr.values)
            wf = wf_oos_sharpes(tr)
            sel = float(np.mean(wf)) if wf else -np.inf
            rec = {
                "long_only": bool(long_only),
                "lookback": lb,
                "skip": sk,
                "n_top": n_top,
                "train_sharpe": float(train_sr),
                "wf_oos_mean_sharpe": sel,
                "wf_oos_sharpes": [float(x) for x in wf],
                "val_sharpe": float(sharpe_ratio(va.values)),
                "test_sharpe": float(sharpe_ratio(te.values)),
                "oos_sharpe": float(sharpe_ratio(oo.values)),
                "oos_trades": int(
                    (res.trades["timestamp"] > pd.Timestamp(TRAIN_END)).sum()
                ),
                "full_sharpe": float(res.metrics["sharpe"]),
                "full_dd": float(res.metrics["max_drawdown"]),
                "full_pf": float(res.metrics["profit_factor"]),
            }
            records.append(rec)
            print(
                f"  [{i + 1}/{len(grid)}] lo={long_only} lb={lb} sk={sk} top={n_top}: "
                f"train={train_sr:.3f} wfOOS={sel:.3f} val={rec['val_sharpe']:.3f} test={rec['test_sharpe']:.3f}"
            )

        combos = pd.DataFrame(records)
        tracker.log_dataframe("param_grid_results", combos)
        # Multiple-testing correction on train wf p-values
        pvals = []
        for r in records:
            sf = np.array(r["wf_oos_sharpes"])
            sf = sf[~np.isnan(sf)]
            if len(sf) > 1 and sf.std() > 0:
                _, p = stats.ttest_1samp(sf, 0.0)
                pvals.append(float(p))
            else:
                pvals.append(1.0)
        rej, adj = multiple_testing_correction(
            np.array(pvals), method="benjamini_hochberg", alpha=0.05
        )
        for r, ap, j in zip(records, adj, rej):
            r["wf_oos_adj_pvalue"] = float(ap)
            r["wf_oos_significant"] = bool(j)
        combos = pd.DataFrame(records)
        combos_sorted = combos.sort_values(
            ["wf_oos_mean_sharpe", "train_sharpe"], ascending=[False, False]
        )
        best = combos_sorted.iloc[0]
        sel_lo = bool(best["long_only"])
        sel_lb = int(best["lookback"])
        sel_sk = int(best["skip"])
        sel_allow_short = not sel_lo
        print(
            f"\nSELECTED: long_only={sel_lo} lb={sel_lb} sk={sel_sk} (wfOOS={best['wf_oos_mean_sharpe']:.3f}, train={best['train_sharpe']:.3f})"
        )

        # Final run with selected params
        sig = cs_momentum_vol_scaled(prices, sel_lb, sel_sk, sel_lo)
        sig_m = resample_monthly_signals(sig)
        cfg = make_config(sel_allow_short)
        final = run_backtest(
            prices=prices, signals=sig_m, volumes=vol, adv=adv, config=cfg
        )
        tr, va, te, oo = split_returns_by_date(final.returns)
        tracker.log_dataframe("selected_signals", sig_m)
        tracker.log_dataframe("selected_equity", final.equity_curve.to_frame("equity"))
        tracker.log_dataframe("selected_trades", final.trades)

        oos_returns = oo
        oos_sharpe = sharpe_ratio(oos_returns.values)
        sharpe_ci = sharpe_ratio_ci(
            oos_returns.values, n_bootstrap=1000, random_state=SEED
        )
        oos_trades = final.trades[final.trades["timestamp"] > pd.Timestamp(TRAIN_END)]
        oos_eq = (1 + oos_returns).cumprod()
        oos_dd = float((oos_eq / oos_eq.expanding().max()).min() - 1)
        gp = oos_returns[oos_returns > 0].sum()
        gl = abs(oos_returns[oos_returns < 0].sum())
        oos_pf = float(gp / gl) if gl > 0 else np.inf
        train_sharpe = sharpe_ratio(tr.values)
        wf_stab = oos_sharpe / train_sharpe if train_sharpe != 0 else 0.0
        # regimes
        oos_vix = vix.loc[oos_returns.index]
        reg = regime_labels(oos_vix)
        regime_metrics = {}
        worst = np.inf
        for r in ["bull", "sideways", "bear"]:
            rr = oos_returns[reg == r]
            if len(rr) > 1 and rr.std() > 0:
                s = sharpe_ratio(rr.values)
                regime_metrics[r] = {"sharpe": float(s), "n": len(rr)}
                worst = min(worst, s)
            else:
                regime_metrics[r] = {"sharpe": 0.0, "n": len(rr)}
        worst = worst if np.isfinite(worst) else 0.0

        # perturbation
        def pert(lb, sk):
            s2 = cs_momentum_vol_scaled(prices, lb, sk, sel_lo)
            s2m = resample_monthly_signals(s2)
            cfg2 = make_config(sel_allow_short)
            r2 = run_backtest(
                prices=prices, signals=s2m, volumes=vol, adv=adv, config=cfg2
            )
            _, _, _, oo2 = split_returns_by_date(r2.returns)
            return sharpe_ratio(oo2.values)

        lbp = max(1, round(sel_lb * 1.2))
        lbm = max(1, round(sel_lb * 0.8))
        skp = max(1, round(sel_sk * 1.2))
        skm = max(1, round(sel_sk * 0.8))
        perturbs = {
            "lookback+20%": pert(lbp, sel_sk),
            "lookback-20%": pert(lbm, sel_sk),
            "skip+20%": pert(sel_lb, skp),
            "skip-20%": pert(sel_lb, skm),
        }
        min_pert = min(perturbs.values()) if min(perturbs.values()) != 0 else 0.0
        # benchmark test
        bench = bh_result.returns.reindex(oos_returns.index).ffill()
        oos_arr = oos_returns.values
        b_arr = bench.values
        m = ~(np.isnan(oos_arr) | np.isnan(b_arr))
        oos_arr = oos_arr[m]
        b_arr = b_arr[m]
        cmp = compare_to_benchmark(oos_arr, b_arr)
        excess = oos_arr - b_arr
        _, alpha_p = stats.ttest_1samp(excess, 0.0) if excess.std() > 0 else (0.0, 1.0)

        def ir_func(x):
            b = b_arr[: len(x)]
            e = x - b
            return float(e.mean() / e.std() * np.sqrt(252)) if e.std() > 0 else 0.0

        ir_ci = bootstrap_confidence_interval(
            oos_arr - b_arr, ir_func, n_bootstrap=1000, random_state=SEED
        )
        ir_ci = (float(ir_ci[0]), float(ir_ci[1]))

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
                "value": round(wf_stab, 4),
                "threshold": GATES["min_walkforward_stability"],
                "pass": bool(wf_stab >= GATES["min_walkforward_stability"]),
            },
            "param_perturbation": {
                "value": round(min_pert, 4),
                "threshold": round(oos_sharpe * GATES["min_perturbed_sharpe_ratio"], 4),
                "pass": bool(
                    min_pert >= oos_sharpe * GATES["min_perturbed_sharpe_ratio"]
                ),
                "details": {k: round(float(v), 4) for k, v in perturbs.items()},
            },
            "regime_stability": {
                "value": round(worst, 4),
                "threshold": GATES["min_worst_regime_sharpe"],
                "pass": bool(worst >= GATES["min_worst_regime_sharpe"]),
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
            },
        }
        all_pass = all(g["pass"] for g in gates.values())
        tracker.log_metrics({"all_gates_pass": all_pass}, step=0)
        tracker.log_metrics(gates, step=0)

        print("\n" + "=" * 72)
        print("CROSS-SECTIONAL MOMENTUM -- EVIDENCE GATES (OOS: Val+Test)")
        print("=" * 72)
        print(f"Selected: long_only={sel_lo} lb={sel_lb} sk={sel_sk}")
        print(
            f"OOS Sharpe={oos_sharpe:.3f} (CI [{sharpe_ci[0]:.3f}, {sharpe_ci[1]:.3f}])"
        )
        print(
            f"Train={train_sharpe:.3f} Val={sharpe_ratio(va.values):.3f} Test={sharpe_ratio(te.values):.3f}"
        )
        print(
            f"OOS trades={len(oos_trades)} PF={oos_pf:.3f} DD={oos_dd:.2%} WF={wf_stab:.3f} worst_regime={worst:.3f} IR={cmp['information_ratio']:.3f} p={alpha_p:.4f}"
        )
        for n, g in gates.items():
            print(
                f"  [{'PASS' if g['pass'] else 'FAIL'}] {n}: {g['value']} (threshold {g['threshold']})"
            )
        print(f"  ALL GATES PASSED: {'YES' if all_pass else 'NO'}")
        print("=" * 72)

        summary = {
            "experiment_id": exp_id,
            "selected_params": {
                "long_only": sel_lo,
                "lookback": sel_lb,
                "skip": sel_sk,
                "target_vol": TARGET_VOL,
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
                "val_sharpe": round(sharpe_ratio(va.values), 4),
                "test_sharpe": round(sharpe_ratio(te.values), 4),
                "oos_sharpe": round(oos_sharpe, 4),
            },
            "benchmark_comparison": {
                "information_ratio": round(float(cmp["information_ratio"]), 4),
                "information_ratio_ci": [round(ir_ci[0], 4), round(ir_ci[1], 4)],
                "alpha_p_value": round(float(alpha_p), 6),
            },
            "regime_metrics": regime_metrics,
            "perturbations": {k: round(float(v), 4) for k, v in perturbs.items()},
            "param_grid_summary": {
                "n_combos": len(records),
                "selection_metric": "mean walk-forward OOS Sharpe on TRAIN",
                "benjamini_hochberg_significant": int(
                    sum(1 for r in records if r.get("wf_oos_significant"))
                ),
            },
        }
        exp_dir = Path(tracker.log_dir) / "artifacts" / exp_id
        with open(exp_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2, default=str)
        tracker.log_artifact("summary", exp_dir / "summary.json")
        tracker.log_dataframe("param_grid_results", combos)
        tracker.finish_experiment(status="completed")
        print(f"\nExperiment ID: {exp_id} | All gates passed: {all_pass}")
        return all_pass
    except Exception as e:  # noqa: BLE001 -- top-level experiment harness: any failure must finish the tracker and return a verdict
        import traceback

        traceback.print_exc()
        tracker.finish_experiment(status="failed", error=str(e))
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
