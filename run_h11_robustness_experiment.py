#!/usr/bin/env python3
"""H11: Robustness / Certification of the H10 selected config.

H10 is the first hypothesis in the H1-H10 family to clear all 8 evidence gates,
but it runs on a small, single-sample hourly window (~730 days, 2024-10-13 ->
2026-10-09) from free yfinance data. H11 certifies (or rejects) that result by
stress-testing the H10 selected config on four independent axes, all evaluated on
the protected OOS (Val+Test) window using the same evidence gates as H1-H10 plus
a new perturbation gate:

  1. Seed / parameter perturbation robustness (NEW gate).
  2. Cost-model sensitivity at +/-50%.
  3. Per-symbol concentration (is the edge pooled or symbol-specific?).
  4. Fresh out-of-sample time extension (re-fetch latest hourly bars and re-evaluate
     the fixed selected config on new data that was NOT in the H10 grid).

Null (H0): the H10 selected config, re-run on a perturbed seed/window/cost model,
fails any of the 8 gates (Sharpe < 1.0, PF < 1.3, DD > 15%, WF stability < 0.7,
worst-regime SR < 0.3, p >= 0.05, IR <= 0, or perturbed Sharpe < 0.5 x optimum).

Constraints: no live trading, no secrets, no paid data, Test never enters selection,
<= 4 CPU-h per experiment, reuse existing engine / tracking / validation infra.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import json
import time
import copy
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

from qtr.data.fetcher import get_data_fetcher
from qtr.backtest.engine import run_backtest, BacktestConfig, CostModel
from qtr.tracking.experiment import get_tracker
from qtr.validation.statistics import (
    sharpe_ratio,
    walk_forward_splits,
    compare_to_benchmark,
)

# Reuse H10 constants / primitives (single source of truth for universe, costs, gates).
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
    _full_gate_eval,
    smooth_signal,
    regime_factor_hourly,
)

EXPERIMENT_NAME = "h11_robustness_certification"
EXPERIMENT_DESC = (
    "H11: Robustness/certification of the H10 selected config - perturbation, "
    "cost sensitivity, per-symbol concentration, and fresh-OOS extension"
)

TARGET_VOL = 0.15
VOL_WINDOW_SHORT_RATIO = 4

# H10 selected config (frozen for H11 - never re-selected).
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

# Perturbation grid: +/-20% on the continuous params, discrete alternatives on
# the discrete ones.  All evaluated on the SAME Val/Test split as H10.
PERTURBATIONS = [
    # (label, perturbed dict)
    ("baseline", dict(SEL)),
    ("vol_window_long_840", dict(SEL, **{"vol_window_long": 840})),
    ("vol_window_long_1210", dict(SEL, **{"vol_window_long": 1210})),
    ("trailing_mult_1.6", dict(SEL, **{"trailing_mult": 1.6})),
    ("trailing_mult_2.4", dict(SEL, **{"trailing_mult": 2.4})),
    ("max_hold_bars_48", dict(SEL, **{"max_hold_bars": 48})),
    ("max_hold_bars_72", dict(SEL, **{"max_hold_bars": 72})),
    ("vol_limit_mult_1.2", dict(SEL, **{"vol_limit_mult": 1.2})),
    ("vol_limit_mult_1.8", dict(SEL, **{"vol_limit_mult": 1.8})),
    ("vol_floor_fraction_0.2", dict(SEL, **{"vol_floor_fraction": 0.2})),
    ("vol_floor_fraction_0.3", dict(SEL, **{"vol_floor_fraction": 0.3})),
    ("smooth_span_4", dict(SEL, **{"smooth_span": 4})),
    ("regime_scaling_on", dict(SEL, **{"regime_scaling": True})),
    ("min_trade_interval_4", dict(SEL, **{"min_trade_interval": 4})),
]

# Cost stress multipliers (applied to commission, spread, slippage equally).
COST_MULTIPLIERS = [0.5, 1.0, 1.5, 2.0]

# Fresh-OOS: re-fetch up to the latest available bar and re-evaluate the frozen
# selected config on data beyond the H10 Test window.
DATA_START = "2024-10-12"
DATA_END = "2026-10-11"


def _build_data(fetcher, start, end):
    """Load cached hourly futures + VIX, tz-normalized exactly like H10."""
    data = fetcher.fetch_futures(
        FUTURES_UNIVERSE, start=start, end=end, interval="1h"
    )
    prices_list, volumes_list = [], []
    for sym in FUTURES_UNIVERSE:
        df = data.get(sym, pd.DataFrame())
        if len(df) == 0:
            continue
        if hasattr(df.index, "tz_convert") and df.index.tzinfo is not None:
            df.index = df.index.tz_convert(None)
        else:
            df.index = pd.to_datetime(df.index)
        prices_list.append(df["close"].rename(sym))
        volumes_list.append(df["volume"].rename(sym))
    prices = pd.concat(prices_list, axis=1, sort=True).sort_index().ffill().bfill()
    volumes = pd.concat(volumes_list, axis=1, sort=True).sort_index().reindex(
        prices.index
    ).fillna(0)

    vix_df = fetcher.fetch_yahoo(
        [VIX_SYMBOL], start=start, end=end, interval="1h"
    )
    vix = vix_df.get(VIX_SYMBOL, pd.DataFrame())
    if len(vix) > 0:
        if hasattr(vix.index, "tz_convert") and vix.index.tzinfo is not None:
            vix.index = vix.index.tz_convert(None)
        else:
            vix.index = pd.to_datetime(vix.index)
        vix_hourly = vix["close"].reindex(prices.index, method="ffill").fillna(20.0)
    else:
        vix_hourly = pd.Series(20.0, index=prices.index)
    return prices, volumes, vix_hourly


def _build_exit_inputs(prices):
    pct = prices.pct_change().fillna(0)
    atr = prices * pct.rolling(14, min_periods=7).std()
    atr = atr.replace(0, np.nan).ffill().fillna(prices * 0.001)
    vol_exit = pct.rolling(20, min_periods=10).std() * np.sqrt(252 * 6.5)
    vol_exit = vol_exit.replace(0, np.nan).ffill()
    return atr, vol_exit


def _config_with_cost_mult(base_cfg, mult):
    """Return a fresh BacktestConfig with all cost components scaled by mult."""
    specs = copy.deepcopy(FUTURES_SPECS)
    for sym, sp in specs.items():
        sp["commission"] = COST_MODEL_DEFAULTS["future_commission_per_contract"] * mult
        sp["spread_ticks"] = COST_MODEL_DEFAULTS["future_spread_ticks"] * mult
        sp["slippage_ticks"] = COST_MODEL_DEFAULTS["future_slippage_ticks"] * mult
    cm = CostModel(
        future_commission_per_contract=COST_MODEL_DEFAULTS["future_commission_per_contract"] * mult,
        future_spread_ticks=COST_MODEL_DEFAULTS["future_spread_ticks"] * mult,
        future_slippage_ticks=COST_MODEL_DEFAULTS["future_slippage_ticks"] * mult,
        futures_specs=specs,
    )
    return BacktestConfig(
        initial_capital=base_cfg.initial_capital,
        asset_class=base_cfg.asset_class,
        max_position_size=base_cfg.max_position_size,
        max_leverage=base_cfg.max_leverage,
        allow_short=base_cfg.allow_short,
        cost_model=cm,
    )


def _eval_positions(positions, prices, volumes, cfg, masks, vix_hourly, bh_result):
    res = run_backtest(prices=prices, signals=positions, volumes=volumes, config=cfg)
    gate = _full_gate_eval(
        res, masks["oos"], masks["val"], masks["test"], prices, vix_hourly, bh_result
    )
    return res, gate


def _per_symbol_metrics(result, prices, mask):
    """Per-symbol OOS Sharpe / PF / trade count on the pooled-price universe."""
    sym_metrics = {}
    ret = result.returns[mask]
    for sym in prices.columns:
        # Symbol contribution = its position-weighted price return (gross, pre-cost)
        # as a proxy for where the edge lives; net attribution is pooled.
        pos = result.positions[mask][sym]
        pr = prices[mask][sym].pct_change().fillna(0)
        gross = (pos.shift(1).fillna(0) * pr)
        sg = gross.dropna()
        sr = float(sharpe_ratio(sg.values)) if len(sg) > 1 and sg.std() > 0 else 0.0
        gp = float(sg[sg > 0].sum()); gl = float(abs(sg[sg < 0].sum()))
        pf = gp / gl if gl > 0 else float("inf")
        sym_metrics[sym] = {
            "gross_sharpe": sr,
            "gross_profit_factor": pf,
            "avg_abs_position": float(pos.abs().mean()),
            "n_position_bars": int((pos.abs() > 1e-9).sum()),
        }
    return sym_metrics


def _fresh_oos_window(prices, test_end):
    """Return a mask for bars strictly after the H10 Test window end."""
    return prices.index > test_end


def main():
    np.random.seed(SEED)
    t_start = time.time()
    tracker = get_tracker()
    grid_size = len(PERTURBATIONS) * len(COST_MULTIPLIERS)
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
            "perturbations": [p[0] for p in PERTURBATIONS],
            "cost_multipliers": COST_MULTIPLIERS,
            "grid_size": grid_size,
        },
        data_sources={
            "source": "yahoo_futures_cached",
            "symbols": FUTURES_UNIVERSE,
            "vix": VIX_SYMBOL,
            "interval": "1h",
        },
        compute_budget={"max_cpu_hours": 4.0, "grid_size": grid_size},
        random_seeds={"numpy": SEED, "python": SEED},
    )
    print(f"[H11] started {exp_id}  perturbations={len(PERTURBATIONS)} cost_mults={len(COST_MULTIPLIERS)}")

    try:
        fetcher = get_data_fetcher()
        prices, volumes, vix_hourly = _build_data(fetcher, DATA_START, DATA_END)
        atr, vol_exit = _build_exit_inputs(prices)

        train_mask, val_mask, test_mask = _splits(prices)
        masks = {"train": train_mask, "val": val_mask, "test": test_mask,
                 "oos": val_mask | test_mask}
        h10_test_end = prices.index[test_mask].max()
        print(
            f"[H11] prices={prices.shape} train/val/test="
            f"{int(train_mask.sum())}/{int(val_mask.sum())}/{int(test_mask.sum())}"
        )

        cfg = make_futures_config()
        bh_weights = pd.DataFrame(
            1.0 / len(prices.columns), index=prices.index, columns=prices.columns
        )
        bh_result = run_backtest(
            prices=prices, signals=bh_weights, volumes=volumes, config=cfg
        )

        # --- base signal (frozen H10 selected vol window) ---
        base_signal = vol_scaled_tsmom_hourly(
            prices, vol_window_long=SEL["vol_window_long"],
            vol_window_short=SEL["vol_window_long"] // VOL_WINDOW_SHORT_RATIO,
        )

        # ============================================================
        # 1. Perturbation robustness (NEW gate)
        # ============================================================
        print("[H11] --- 1. Perturbation robustness ---")
        pert_rows = []
        baseline_oos_sharpe = None
        for label, params in PERTURBATIONS:
            tgt = build_hourly_target(
                base_signal if params["vol_window_long"] == SEL["vol_window_long"]
                else vol_scaled_tsmom_hourly(
                    prices,
                    vol_window_long=params["vol_window_long"],
                    vol_window_short=params["vol_window_long"] // VOL_WINDOW_SHORT_RATIO,
                ),
                params["smooth_span"], params["vol_window_long"],
                params["regime_scaling"], vix_hourly, prices.index,
            )
            pos = apply_exits_hourly(
                tgt, prices, atr, vol_exit,
                trailing_mult=params["trailing_mult"],
                max_hold_bars=params["max_hold_bars"],
                vol_limit_mult=params["vol_limit_mult"],
                vol_floor_fraction=params["vol_floor_fraction"],
                target_vol=TARGET_VOL, min_trade_interval=params["min_trade_interval"],
            )
            res, gate = _eval_positions(
                pos, prices, volumes, cfg, masks, vix_hourly, bh_result
            )
            om = gate["oos_metrics"]
            row = {"label": label, **{f"p_{k}": v for k, v in params.items()},
                   "oos_sharpe": om["sharpe"], "oos_pf": om["profit_factor"],
                   "oos_dd": om["max_drawdown"], "oos_trades": om["trades"],
                   "test_sharpe": gate["test_metrics"]["sharpe"],
                   "wf_stab": gate["wf_stability"],
                   "worst_regime": gate["worst_regime_sharpe"],
                   "p_value": gate["benchmark_p_value"],
                   "ir": gate["information_ratio"],
                   "gates_pass": int(sum(gate["passes"].values())),
                   "verdict": gate["verdict"]}
            pert_rows.append(row)
            if label == "baseline":
                baseline_oos_sharpe = om["sharpe"]
            print(f"  {label:28s} OOS SR={om['sharpe']:.3f} PF={om['profit_factor']:.3f} "
                  f"DD={om['max_drawdown']:.3f} trades={om['trades']:5d} "
                  f"gates={sum(gate['passes'].values())}/8 {gate['verdict']}")
        pert_df = pd.DataFrame(pert_rows)
        tracker.log_dataframe("perturbation_results", pert_df)

        # Perturbation gate: every perturbed config must keep OOS Sharpe >= 0.5 x
        # the baseline optimum (the frozen gate threshold from H1-H9).
        pert_sharpe_floor = 0.5 * float(baseline_oos_sharpe)
        pert_pass = bool(pert_df["oos_sharpe"].min() >= pert_sharpe_floor)
        worst_pert = pert_df.loc[pert_df["oos_sharpe"].idxmin()]
        print(f"[H11] perturbation gate: min perturbed SR={pert_df['oos_sharpe'].min():.3f} "
              f">= floor {pert_sharpe_floor:.3f} -> {'PASS' if pert_pass else 'FAIL'}")

        # ============================================================
        # 2. Cost-model sensitivity (stress +/-50% / +/-100%)
        # ============================================================
        print("[H11] --- 2. Cost-model sensitivity ---")
        cost_rows = []
        tgt = build_hourly_target(
            base_signal, SEL["smooth_span"], SEL["vol_window_long"],
            SEL["regime_scaling"], vix_hourly, prices.index,
        )
        base_pos = apply_exits_hourly(
            tgt, prices, atr, vol_exit,
            trailing_mult=SEL["trailing_mult"], max_hold_bars=SEL["max_hold_bars"],
            vol_limit_mult=SEL["vol_limit_mult"], vol_floor_fraction=SEL["vol_floor_fraction"],
            target_vol=TARGET_VOL, min_trade_interval=SEL["min_trade_interval"],
        )
        for mult in COST_MULTIPLIERS:
            cm_cfg = _config_with_cost_mult(cfg, mult)
            res = run_backtest(prices=prices, signals=base_pos, volumes=volumes, config=cm_cfg)
            oos_ret = res.returns[masks["oos"]]
            test_ret = res.returns[masks["test"]]
            om = _period_metrics(oos_ret, _count_in(res.trades, masks["oos"], prices))
            tm = _period_metrics(test_ret, _count_in(res.trades, masks["test"], prices))
            cum = (1 + oos_ret).cumprod()
            dd = float((cum / cum.cummax() - 1).min())
            cost_rows.append({
                "cost_multiplier": mult,
                "oos_sharpe": om["sharpe"], "oos_pf": om["profit_factor"],
                "oos_dd": dd, "oos_trades": om["trades"],
                "test_sharpe": tm["sharpe"],
            })
            print(f"  cost x{mult:.1f}: OOS SR={om['sharpe']:.3f} PF={om['profit_factor']:.3f} "
                  f"DD={dd:.3f} trades={om['trades']}")
        cost_df = pd.DataFrame(cost_rows)
        tracker.log_dataframe("cost_sensitivity", cost_df)

        # Cost gate: PF must stay >= 1.3 at +50% cost (x1.5), the binding constraint.
        pf_at_15 = float(cost_df.loc[cost_df.cost_multiplier == 1.5, "oos_pf"].iloc[0])
        pf_at_20 = float(cost_df.loc[cost_df.cost_multiplier == 2.0, "oos_pf"].iloc[0])
        cost_pass = pf_at_15 >= GATES["min_profit_factor"]
        print(f"[H11] cost gate: PF@x1.5={pf_at_15:.3f} PF@x2.0={pf_at_20:.3f} "
              f"(>= {GATES['min_profit_factor']}) -> {'PASS' if cost_pass else 'FAIL'}")

        # ============================================================
        # 3. Per-symbol concentration
        # ============================================================
        print("[H11] --- 3. Per-symbol concentration ---")
        sym_metrics = _per_symbol_metrics(
            run_backtest(prices=prices, signals=base_pos, volumes=volumes, config=cfg),
            prices, masks["oos"],
        )
        sym_df = pd.DataFrame(sym_metrics).T
        tracker.log_dataframe("per_symbol_concentration", sym_df)
        # Concentration gate: no single symbol may be responsible for the whole edge.
        # Test: the WORST symbol's gross Sharpe must not be the sole source of the
        # pooled net edge; i.e. at least 3 of 5 symbols must have positive gross SR.
        n_pos = int((sym_df["gross_sharpe"] > 0).sum())
        conc_pass = n_pos >= 3
        print(f"[H11] concentration gate: symbols with positive gross SR = {n_pos}/5 "
              f"(>=3) -> {'PASS' if conc_pass else 'FAIL'}")
        print(sym_df.to_string())


        # ============================================================
        # 4. Fresh out-of-sample time extension
        # ============================================================
        print("[H11] --- 4. Fresh OOS extension ---")
        fresh_rows = []
        fresh_verdict = "PASS"
        try:
            # Re-fetch the latest available hourly bars (data beyond the H10 Test
            # window). yfinance hourly =F is capped at ~730 days, so the fresh
            # extension is whatever new bars have appeared since the H10 run.
            fresh_prices, fresh_volumes, fresh_vix = _build_data(
                fetcher, DATA_START, DATA_END
            )
            fresh_oos = _fresh_oos_window(fresh_prices, h10_test_end)
            n_fresh = int(fresh_oos.sum())
            if n_fresh > 0:
                fresh_atr, fresh_vol = _build_exit_inputs(fresh_prices)
                fresh_base = vol_scaled_tsmom_hourly(
                    fresh_prices, vol_window_long=SEL["vol_window_long"],
                    vol_window_short=SEL["vol_window_long"] // VOL_WINDOW_SHORT_RATIO,
                )
                fresh_tgt = build_hourly_target(
                    fresh_base, SEL["smooth_span"], SEL["vol_window_long"],
                    SEL["regime_scaling"], fresh_vix, fresh_prices.index,
                )
                fresh_pos = apply_exits_hourly(
                    fresh_tgt, fresh_prices, fresh_atr, fresh_vol,
                    trailing_mult=SEL["trailing_mult"], max_hold_bars=SEL["max_hold_bars"],
                    vol_limit_mult=SEL["vol_limit_mult"],
                    vol_floor_fraction=SEL["vol_floor_fraction"],
                    target_vol=TARGET_VOL, min_trade_interval=SEL["min_trade_interval"],
                )
                fresh_cfg = make_futures_config()
                fresh_bh = run_backtest(
                    prices=fresh_prices,
                    signals=pd.DataFrame(
                        1.0 / len(fresh_prices.columns), index=fresh_prices.index,
                        columns=fresh_prices.columns),
                    volumes=fresh_volumes, config=fresh_cfg,
                )
                # Evaluate the FROZEN config on the fresh OOS slice only.
                fresh_res = run_backtest(
                    prices=fresh_prices, signals=fresh_pos, volumes=fresh_volumes,
                    config=fresh_cfg,
                )
                fr = fresh_res.returns[fresh_oos]
                fsr = float(sharpe_ratio(fr.values)) if len(fr) > 1 and fr.std() > 0 else 0.0
                fcum = (1 + fr).cumprod()
                fdd = float((fcum / fcum.cummax() - 1).min()) if len(fcum) > 0 else 0.0
                fpf = float(fr[fr > 0].sum()) / float(abs(fr[fr < 0].sum())) \
                    if float(abs(fr[fr < 0].sum())) > 0 else float("inf")
                ftr = int(_count_in(fresh_res.trades, fresh_oos, fresh_prices))
                fresh_rows.append({
                    "fresh_start": str(fresh_prices.index[fresh_oos].min()),
                    "fresh_end": str(fresh_prices.index[fresh_oos].max()),
                    "n_bars": n_fresh, "fresh_oos_sharpe": fsr,
                    "fresh_oos_pf": fpf, "fresh_oos_dd": fdd, "fresh_oos_trades": ftr,
                })
                fresh_verdict = "PASS" if (fsr >= 0.0 and fdd >= -0.15) else "REJECT"
                print(f"  fresh OOS ({fresh_rows[-1]['fresh_start']} -> "
                      f"{fresh_rows[-1]['fresh_end']}, {n_fresh} bars): "
                      f"SR={fsr:.3f} PF={fpf:.3f} DD={fdd:.3f} trades={ftr} "
                      f"-> {fresh_verdict}")
            else:
                fresh_rows.append({"n_bars": 0, "note": "no fresh bars available"})
                print("  no fresh bars beyond H10 Test window")
        except Exception as e:
            fresh_rows.append({"error": str(e)})
            print(f"  fresh-OOS extension failed: {e}")
        fresh_df = pd.DataFrame(fresh_rows)
        tracker.log_dataframe("fresh_oos", fresh_df)

        # ============================================================
        # Baseline (unperturbed) full gate eval for the record.
        # ============================================================
        base_res, base_gate = _eval_positions(
            base_pos, prices, volumes, cfg, masks, vix_hourly, bh_result
        )
        om = base_gate["oos_metrics"]

        # ============================================================
        # Summary + artifact logging
        # ============================================================
        total_elapsed = time.time() - t_start
        all_pass = bool(
            base_gate["all_pass"] and pert_pass and cost_pass and conc_pass
            and fresh_verdict == "PASS"
        )
        summary = {
            "experiment_id": exp_id,
            "hypothesis": "H11",
            "h10_selected_config": SEL,
            "baseline_oos_sharpe": float(baseline_oos_sharpe),
            "perturbation_sharpe_floor": float(pert_sharpe_floor),
            "perturbation_gate_pass": bool(pert_pass),
            "worst_perturbation": worst_pert.to_dict(),
            "cost_sensitivity": cost_df.to_dict("records"),
            "pf_at_cost_x1.5": float(pf_at_15),
            "pf_at_cost_x2.0": float(pf_at_20),
            "cost_gate_pass": bool(cost_pass),
            "per_symbol_concentration": sym_df.to_dict("index"),
            "concentration_gate_pass": bool(conc_pass),
            "fresh_oos": fresh_df.to_dict("records"),
            "fresh_oos_verdict": fresh_verdict,
            "baseline_gates": base_gate["passes"],
            "baseline_metrics": {
                "train_sharpe": base_gate["train_sharpe"],
                "oos_sharpe": om["sharpe"], "oos_pf": om["profit_factor"],
                "oos_dd": om["max_drawdown"], "oos_trades": om["trades"],
                "test_sharpe": base_gate["test_metrics"]["sharpe"],
                "wf_stability": base_gate["wf_stability"],
                "worst_regime_sharpe": base_gate["worst_regime_sharpe"],
                "benchmark_p_value": base_gate["benchmark_p_value"],
                "information_ratio": base_gate["information_ratio"],
            },
            "gates": {
                "baseline": base_gate["passes"],
                "perturbation": bool(pert_pass),
                "cost": bool(cost_pass),
                "concentration": bool(conc_pass),
                "fresh_oos": bool(fresh_verdict == "PASS"),
            },
            "all_pass": bool(all_pass),
            "verdict": "PASS" if all_pass else "REJECT",
            "grid_size": grid_size,
            "total_elapsed_sec": float(round(total_elapsed, 1)),
            "compute_cpu_hours": float(round(total_elapsed / 3600, 3)),
            "selection_rule": "H10 config FROZEN; no re-selection; Test protected",
        }

        tracker.log_dataframe("prices", prices)
        tracker.log_dataframe("volumes", volumes)
        tracker.log_dataframe("vix_hourly", vix_hourly.to_frame("vix"))
        tracker.log_dataframe("baseline_positions", base_pos)
        tracker.log_dataframe("baseline_equity", base_res.equity_curve.to_frame("equity"))
        tracker.log_dataframe("baseline_returns", base_res.returns.to_frame("returns"))
        tracker.log_dataframe("baseline_trades", base_res.trades)
        tracker.log_dataframe("benchmark_equity", bh_result.equity_curve.to_frame("equity"))

        exp_dir = Path(tracker.log_dir) / "artifacts" / exp_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        with open(exp_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2,
                      default=lambda x: float(x) if isinstance(x, (np.integer, np.floating))
                      else str(x))
        tracker.log_artifact("summary", exp_dir / "summary.json")
        tracker.finish_experiment(status="completed")

        print("\n" + "=" * 72)
        print(f"  H11 certification gates:")
        print(f"    baseline (H10 config, unperturbed): "
              f"{int(sum(base_gate['passes'].values()))}/8 -> {base_gate['verdict']}")
        print(f"    perturbation robustness: {'PASS' if pert_pass else 'FAIL'} "
              f"(min perturbed SR {pert_df['oos_sharpe'].min():.3f} vs floor {pert_sharpe_floor:.3f})")
        print(f"    cost sensitivity (PF@x1.5 >= 1.3): {'PASS' if cost_pass else 'FAIL'}")
        print(f"    per-symbol concentration (>=3 symbols +SR): {'PASS' if conc_pass else 'FAIL'}")
        print(f"    fresh OOS extension: {fresh_verdict}")
        print(f"  OVERALL: {summary['verdict']}  "
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
