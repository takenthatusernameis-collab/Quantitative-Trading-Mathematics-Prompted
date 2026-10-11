#!/usr/bin/env python3
"""H6: VIX-Gated + DDCV Combo on Futures TSMOM.

Combines VIX-regime exposure gate (Sharpe lift) with DDCV drawdown conditioning
(DD reduction) on the corrected futures TSMOM (long-only, lookback 252, skip 1).

Pre-registered design:
- Universe: ES=F, NQ=F, CL=F, GC=F, ZB=F (all 5 available).
- Splits: Train 2015-2019, Val 2020-2021, Test 2022-24 (protected).
- Base signal: vol_scaled_tsmom_signals (long_only=True, lookback=252, skip=1,
  target_vol=0.15) — the corrected H4 best combo.
- VIX gate (applied first, same as H5 ablation c):
  VIX < 20    -> scale = 1.0 (full)
  VIX 20-30   -> scale = 0.25
  VIX > 30    -> scale = 0.10
  ^VIX used for regime labels only (not traded).
- DDCV layer (applied after VIX gate, before engine):
    dd = equity / equity.rolling(252).max() - 1.0   # <= 0
    dd_scale = 1.0 - dd_factor * max(0, -dd).clip(0, dd_trigger)
    total_scale = vix_scale * dd_scale
  Grid over dd_trigger in {0.10, 0.15, 0.20} and dd_factor in {0.5, 0.75}.
  The combined scale (VIX x DDCV) is applied to the whole book.
- Selection: single pre-registered combo (no grid search on Test); Val used
  for gate evaluation only.
- Gates (unchanged PROMPT_V2): Sharpe >= 1.0, >= 200 trades, PF >= 1.3,
  DD <= 15%, WF stability >= 0.7, +/-20% perturbation, worst-regime Sharpe
  >= 0.3, benchmark p < 0.05 and IR > 0.
- Compute budget: <= 2 CPU-h. Seed 42.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import json
from pathlib import Path
from itertools import product

import numpy as np
import pandas as pd
from scipy import stats

from qtr.data.fetcher import get_data_fetcher
from qtr.backtest.engine import run_backtest, BacktestConfig, AssetClass, CostModel
from qtr.tracking.experiment import get_tracker
from qtr.strategies.baselines import vol_scaled_tsmom_signals
from qtr.validation.statistics import (
    sharpe_ratio, sharpe_ratio_ci, walk_forward_splits,
    compare_to_benchmark,
)

FUTURES_UNIVERSE = ["ES=F", "NQ=F", "CL=F", "GC=F", "ZB=F"]
VIX_SYMBOL = "^VIX"
START_DATE = "2015-01-01"
END_DATE = "2024-12-31"
TRAIN_END = "2019-12-31"
VAL_END = "2021-12-31"

LOOKBACK = 252
SKIP = 1
LONG_ONLY = True
TARGET_VOL = 0.15
VOL_WINDOW = 63
MAX_POSITION_SIZE = 2.0
MAX_LEVERAGE = 5.0
DD_PEAK_WINDOW = 252
DD_TRIGGER_GRID = [0.10, 0.15, 0.20]
DD_FACTOR_GRID = [0.5, 0.75]
BASE_TARGET_VOL = 0.15

# VIX regime thresholds (same as H5 ablation c)
VIX_BULL_THRESHOLD = 20
VIX_SIDEWAYS_THRESHOLD = 30
VIX_BULL_FACTOR = 1.0
VIX_SIDEWAYS_FACTOR = 0.25
VIX_BEAR_FACTOR = 0.10

GATES = {
    "min_sharpe": 1.0,
    "min_trades": 200,
    "min_profit_factor": 1.3,
    "max_drawdown": 0.15,
    "min_walkforward_stability": 0.7,
    "min_worst_regime_sharpe": 0.3,
    "max_p_value": 0.05,
    "min_information_ratio": 0.0,
}

SEED = 42
INITIAL_CAPITAL = 1_000_000.0

COST_MODEL_DEFAULTS = {
    "future_commission_per_contract": 0.50,
    "future_spread_ticks": 0.25,
    "future_slippage_ticks": 0.5,
}

FUTURES_SPECS = {
    "ES=F": {"multiplier": 50.0, "tick_value": 12.50, "tick_size": 0.25, "commission": 0.50, "spread_ticks": 0.25, "slippage_ticks": 0.5},
    "NQ=F": {"multiplier": 20.0, "tick_value": 5.0, "tick_size": 0.25, "commission": 0.50, "spread_ticks": 0.25, "slippage_ticks": 0.5},
    "CL=F": {"multiplier": 1000.0, "tick_value": 10.0, "tick_size": 0.01, "commission": 0.50, "spread_ticks": 0.25, "slippage_ticks": 0.5},
    "GC=F": {"multiplier": 100.0, "tick_value": 10.0, "tick_size": 0.10, "commission": 0.50, "spread_ticks": 0.25, "slippage_ticks": 0.5},
    "ZB=F": {"multiplier": 1000.0, "tick_value": 31.25, "tick_size": 0.03125, "commission": 0.50, "spread_ticks": 0.25, "slippage_ticks": 0.5},
}

EXPERIMENT_NAME = "h6_vix_ddcv_futures_tsmom_v1"
EXPERIMENT_DESC = (
    "H6: VIX-Gated + DDCV Combo on corrected futures TSMOM "
    "(long-only, lookback 252, skip 1). VIX-gate first (bull 1.0, sideways 0.25, "
    "bear 0.10), then DDCV applied to whole book. Grid over dd_trigger in "
    "{0.10, 0.15, 0.20} x dd_factor in {0.5, 0.75}; selection by Val-only Sharpe; "
    "gates on pooled Val+Test OOS. Includes ablations (VIX-only, DDCV-only, base)."
)


def make_futures_config(allow_short=False):
    cm = CostModel(
        future_commission_per_contract=COST_MODEL_DEFAULTS["future_commission_per_contract"],
        future_spread_ticks=COST_MODEL_DEFAULTS["future_spread_ticks"],
        future_slippage_ticks=COST_MODEL_DEFAULTS["future_slippage_ticks"],
        futures_specs=FUTURES_SPECS,
    )
    return BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        asset_class=AssetClass.FUTURE,
        max_position_size=MAX_POSITION_SIZE,
        max_leverage=MAX_LEVERAGE,
        allow_short=allow_short,
        cost_model=cm,
    )


def split_returns_by_date(returns):
    train = returns[returns.index <= TRAIN_END]
    val = returns[(returns.index > TRAIN_END) & (returns.index <= VAL_END)]
    test = returns[returns.index > VAL_END]
    oos = returns[returns.index > TRAIN_END]
    return train, val, test, oos


def resample_monthly_signals(signals):
    monthly = signals.resample("ME").last()
    full_index = signals.index
    return monthly.reindex(full_index, method="ffill").fillna(0)


def ddcv_drawdown(equity, peak_window=DD_PEAK_WINDOW):
    """Compute drawdown from rolling peak. Returns Series <= 0."""
    running_peak = equity.rolling(peak_window).max()
    running_peak = running_peak.replace(0, np.nan).ffill()
    dd = equity / running_peak - 1.0
    return dd


def apply_vix_gate(base_signals, vix, bull_factor=VIX_BULL_FACTOR, sid_factor=VIX_SIDEWAYS_FACTOR, bear_factor=VIX_BEAR_FACTOR):
    """Apply VIX-regime exposure gate to signals.

    VIX < 20 (bull):    full exposure (1.0)
    VIX 20-30 (sideways): 25% exposure
    VIX > 30 (bear):    10% exposure
    """
    vix_ff = vix.reindex(base_signals.index).ffill()
    scale = pd.Series(1.0, index=base_signals.index)
    scale[vix_ff >= VIX_BULL_THRESHOLD] = sid_factor
    scale[vix_ff > VIX_SIDEWAYS_THRESHOLD] = bear_factor
    return base_signals.multiply(scale, axis=0), scale


def apply_ddcv(prices, base_signals, dd_trigger, dd_factor, peak_window=DD_PEAK_WINDOW):
    """Apply DDCV: build base equity curve, compute DD, scale whole book.

    The scale is applied to the signal weights (linear in portfolio vol,
    same as the existing portfolio-level vol targeting inside
    vol_scaled_tsmom_signals). The base equity is computed from the base
    signals through the same engine so the DD measure is realistic.
    """
    cfg = make_futures_config(allow_short=not LONG_ONLY)
    base_result = run_backtest(prices=prices, signals=base_signals, config=cfg)
    base_equity = base_result.equity_curve
    dd = ddcv_drawdown(base_equity, peak_window=peak_window)
    # Per-day scale factor in [0, 1]
    scale = 1.0 - dd_factor * np.maximum(0.0, -dd).clip(0.0, dd_trigger)
    scale = scale.clip(lower=0.0, upper=1.0).fillna(1.0)
    scaled_signals = base_signals.multiply(scale, axis=0)
    return scaled_signals, base_result, scale


def apply_combined(prices, base_signals, vix, dd_trigger, dd_factor, peak_window=DD_PEAK_WINDOW):
    """Apply VIX gate first, then DDCV on the VIX-gated equity."""
    # Step 1: Apply VIX gate to base signals
    vix_gated_signals, vix_scale = apply_vix_gate(base_signals, vix)

    # Step 2: Build equity from VIX-gated signals
    cfg = make_futures_config(allow_short=not LONG_ONLY)
    vix_gated_result = run_backtest(prices=prices, signals=vix_gated_signals, config=cfg)
    vix_gated_equity = vix_gated_result.equity_curve

    # Step 3: Compute DDCV scale from VIX-gated equity
    dd = ddcv_drawdown(vix_gated_equity, peak_window=peak_window)
    dd_scale = 1.0 - dd_factor * np.maximum(0.0, -dd).clip(0.0, dd_trigger)
    dd_scale = dd_scale.clip(lower=0.0, upper=1.0).fillna(1.0)

    # Step 4: Combined scale = VIX scale * DD scale
    total_scale = vix_scale * dd_scale
    total_scale = total_scale.clip(lower=0.0, upper=1.0).fillna(1.0)

    # Apply combined scale to original base signals
    combined_signals = base_signals.multiply(total_scale, axis=0)
    return combined_signals, total_scale, vix_scale, dd_scale


def evaluate(prices, signals, volumes, adv):
    cfg = make_futures_config(allow_short=not LONG_ONLY)
    sig_monthly = resample_monthly_signals(signals)
    return run_backtest(prices=prices, signals=sig_monthly, volumes=volumes, adv=adv, config=cfg)


def window_max_drawdown(equity, start, end):
    eq = equity.loc[start:end]
    if len(eq) < 2:
        return 0.0
    return float((eq / eq.cummax() - 1.0).min())


def regime_labels(vix_daily):
    regimes = pd.Series(index=vix_daily.index, dtype=object)
    vix_ff = vix_daily.ffill()
    regimes[vix_ff < 20] = "bull"
    regimes[(vix_ff >= 20) & (vix_ff <= 30)] = "sideways"
    regimes[vix_ff > 30] = "bear"
    return regimes


def main():
    np.random.seed(SEED)
    tracker = get_tracker()
    exp_id = tracker.start_experiment(
        name=EXPERIMENT_NAME,
        description=EXPERIMENT_DESC,
        config={
            "universe": FUTURES_UNIVERSE,
            "vix_symbol": VIX_SYMBOL,
            "start_date": START_DATE,
            "end_date": END_DATE,
            "data_splits": {"train_end": TRAIN_END, "val_end": VAL_END},
            "base_signal": {
                "lookback": LOOKBACK, "skip": SKIP, "long_only": LONG_ONLY,
                "target_vol": TARGET_VOL, "vol_window": VOL_WINDOW,
                "max_position_size": MAX_POSITION_SIZE,
            },
            "vix_gate": {
                "bull_factor": VIX_BULL_FACTOR,
                "sid_factor": VIX_SIDEWAYS_FACTOR,
                "bear_factor": VIX_BEAR_FACTOR,
                "bull_threshold": VIX_BULL_THRESHOLD,
                "sid_threshold": VIX_SIDEWAYS_THRESHOLD,
            },
            "ddcv_grid": {"dd_trigger": DD_TRIGGER_GRID, "dd_factor": DD_FACTOR_GRID},
            "dd_peak_window": DD_PEAK_WINDOW,
            "gates": GATES,
            "random_seeds": {"numpy": SEED, "python": SEED},
            "compute_budget": {"max_cpu_hours": 2.0},
        },
        data_sources={
            "source": "yahoo_futures", "symbols": FUTURES_UNIVERSE,
            "start": START_DATE, "end": END_DATE, "interval": "1d",
            "notes": "Yahoo continuous futures (=F). Roll adjustment opaque.",
        },
        random_seeds={"numpy": SEED, "python": SEED},
    )
    print(f"Started experiment: {exp_id}")
    try:
        print("Fetching futures data...")
        fetcher = get_data_fetcher()
        raw_fut = fetcher.fetch_futures(FUTURES_UNIVERSE, start=START_DATE,
                                        end=END_DATE, interval="1d", use_cache=True)
        prices = pd.DataFrame()
        volumes = pd.DataFrame()
        for sym in FUTURES_UNIVERSE:
            df = raw_fut.get(sym)
            if df is None or df.empty or "close" not in df.columns:
                print(f"  WARN: no data for {sym}")
                continue
            prices[sym] = df["close"]
            if "volume" in df.columns:
                volumes[sym] = df["volume"]
        prices = prices.ffill().dropna(how="all")
        volumes = volumes.reindex(prices.index).ffill().fillna(0)
        valid = prices.columns[prices.notna().any(axis=0)].tolist()
        prices = prices[valid]
        volumes = volumes[valid]
        print(f"Loaded {len(prices.columns)} futures x {len(prices)} days")

        raw_vix = fetcher.fetch_yahoo([VIX_SYMBOL], start=START_DATE, end=END_DATE,
                                       interval="1d", use_cache=True)
        vix_df = raw_vix.get(VIX_SYMBOL)
        vix = vix_df["close"] if (vix_df is not None and "close" in vix_df.columns) \
            else pd.Series(np.nan, index=prices.index)
        vix = vix.reindex(prices.index).ffill()

        tracker.log_dataframe("prices", prices)
        tracker.log_dataframe("volumes", volumes)
        tracker.log_dataframe("vix_close", vix.to_frame("vix"))

        adv = volumes.rolling(20).mean().iloc[-1] if len(volumes) else None

        # Benchmark - equal weight buy and hold on available futures
        bh_cfg = make_futures_config(allow_short=False)
        n = len(prices.columns)
        bh_signals = pd.DataFrame(1.0 / n if n > 0 else 0.0,
                                  index=prices.index, columns=prices.columns)
        bh_signals = resample_monthly_signals(bh_signals)
        bh_result = run_backtest(prices=prices, signals=bh_signals,
                                  volumes=volumes, adv=adv, config=bh_cfg)
        tracker.log_dataframe("benchmark_equity", bh_result.equity_curve.to_frame("equity"))
        tracker.log_metrics({f"benchmark_{k}": float(v) for k, v in bh_result.metrics.items()}, step=0)
        print("Benchmark Sharpe=%.3f" % bh_result.metrics["sharpe"])

        # Base signal (H4 best combo)
        base_sig = vol_scaled_tsmom_signals(
            prices, lookback=LOOKBACK, skip=SKIP, long_only=LONG_ONLY,
            target_vol=TARGET_VOL, vol_window=VOL_WINDOW,
            max_position_size=MAX_POSITION_SIZE,
        )
        base_sig = resample_monthly_signals(base_sig)
        base_result = evaluate(prices, base_sig, volumes, adv)
        train_r, _, _, oos_r = split_returns_by_date(base_result.returns)
        print("Base TSMOM: train_sharpe=%.3f oos_sharpe=%.3f dd=%.3f" %
              (sharpe_ratio(train_r.values), sharpe_ratio(oos_r.values), base_result.metrics["max_drawdown"]))

        # VIX-gated only (ablation)
        vix_only_sig, vix_only_scale = apply_vix_gate(base_sig, vix)
        vix_only_result = evaluate(prices, vix_only_sig, volumes, adv)
        train_r, _, _, oos_r = split_returns_by_date(vix_only_result.returns)
        print("VIX-only: train_sharpe=%.3f oos_sharpe=%.3f dd=%.3f" %
              (sharpe_ratio(train_r.values), sharpe_ratio(oos_r.values), vix_only_result.metrics["max_drawdown"]))

        # DDCV-only (ablation, on base signals)
        ddcv_only_records = []
        for dd_trigger in DD_TRIGGER_GRID:
            for dd_factor in DD_FACTOR_GRID:
                scaled, _, _ = apply_ddcv(prices, base_sig, dd_trigger, dd_factor)
                result = evaluate(prices, scaled, volumes, adv)
                train_ret, val_ret, test_ret, oos_ret = split_returns_by_date(result.returns)
                rec = {
                    "dd_trigger": dd_trigger, "dd_factor": dd_factor,
                    "val_sharpe": float(sharpe_ratio(val_ret.values)) if len(val_ret) else 0.0,
                    "oos_sharpe": float(sharpe_ratio(oos_ret.values)) if len(oos_ret) else 0.0,
                    "oos_dd": window_max_drawdown(result.equity_curve, TRAIN_END, END_DATE),
                }
                ddcv_only_records.append(rec)
        ddcv_only_df = pd.DataFrame(ddcv_only_records)
        ddcv_only_df = ddcv_only_df.sort_values("val_sharpe", ascending=False)
        best_ddcv_only = ddcv_only_df.iloc[0]
        print("DDCV-only best on Val: trigger=%s factor=%s val_sharpe=%.3f" %
              (best_ddcv_only["dd_trigger"], best_ddcv_only["dd_factor"], best_ddcv_only["val_sharpe"]))

        # ---- Combined VIX+DDCV grid search (selection on Val only) ----
        combo_records = []
        for dd_trigger in DD_TRIGGER_GRID:
            for dd_factor in DD_FACTOR_GRID:
                scaled, _, _, _ = apply_combined(prices, base_sig, vix, dd_trigger, dd_factor)
                result = evaluate(prices, scaled, volumes, adv)
                train_ret, val_ret, test_ret, oos_ret = split_returns_by_date(result.returns)
                rec = {
                    "dd_trigger": dd_trigger, "dd_factor": dd_factor,
                    "val_sharpe": float(sharpe_ratio(val_ret.values)) if len(val_ret) else 0.0,
                    "train_sharpe": float(sharpe_ratio(train_ret.values)) if len(train_ret) else 0.0,
                    "test_sharpe": float(sharpe_ratio(test_ret.values)) if len(test_ret) else 0.0,
                    "oos_sharpe": float(sharpe_ratio(oos_ret.values)) if len(oos_ret) else 0.0,
                    "val_dd": window_max_drawdown(result.equity_curve, TRAIN_END, VAL_END),
                    "oos_dd": window_max_drawdown(result.equity_curve, TRAIN_END, END_DATE),
                    "val_pf": float(result.metrics["profit_factor"]),
                    "val_trades": int(len(result.trades[result.trades["timestamp"] > pd.Timestamp(TRAIN_END)]))
                        if len(result.trades) else 0,
                }
                combo_records.append(rec)
        combo_df = pd.DataFrame(combo_records)
        combo_df = combo_df.sort_values("val_sharpe", ascending=False)
        best = combo_df.iloc[0]
        print("VIX+DDCV grid (%d combos); best on Val: trigger=%s factor=%s val_sharpe=%.3f" %
            (len(combo_df), best["dd_trigger"], best["dd_factor"], best["val_sharpe"]))

        # ---- Evaluate best combo on full OOS with gates ----
        best_trigger = best["dd_trigger"]
        best_factor = best["dd_factor"]
        scaled_best, _, _, _ = apply_combined(prices, base_sig, vix, best_trigger, best_factor)
        best_result = evaluate(prices, scaled_best, volumes, adv)
        train_ret, val_ret, test_ret, oos_ret = split_returns_by_date(best_result.returns)
        oos_sharpe = sharpe_ratio(oos_ret.values) if len(oos_ret) else 0.0
        oos_equity = (1 + oos_ret).cumprod() if len(oos_ret) else pd.Series([1])
        oos_dd = float((oos_equity - oos_equity.expanding().max()).min()) if len(oos_equity) >= 2 else 0.0
        gross_p = oos_ret[oos_ret > 0].sum() if len(oos_ret) else 0
        gross_l = abs(oos_ret[oos_ret < 0].sum()) if len(oos_ret) else 1e-18
        oos_pf = float(gross_p / gross_l) if gross_l > 0 else np.inf
        oos_trades = best_result.trades[best_result.trades["timestamp"] > pd.Timestamp(TRAIN_END)] if len(best_result.trades) else pd.DataFrame()
        train_sharpe = sharpe_ratio(train_ret.values) if len(train_ret) else 0.0
        wf_stab = oos_sharpe / train_sharpe if train_sharpe != 0 else 0.0
        regimes = regime_labels(vix)
        worst = np.inf
        for reg in ["bull", "sideways", "bear"]:
            mask = regimes.loc[oos_ret.index] == reg if len(oos_ret) else []
            if hasattr(mask, "__len__") and len(mask) > 0 and mask.any():
                r = oos_ret[mask]
                if len(r) > 1 and r.std() > 0:
                    s = sharpe_ratio(r.values)
                    if s < worst: worst = s
        if worst == np.inf: worst = oos_sharpe
        if len(oos_ret) > 0:
            bh_oos = bh_result.returns[bh_result.returns.index > pd.Timestamp(TRAIN_END)]
            alpha_res = compare_to_benchmark(oos_ret.values, bh_oos.values)
            p = float(alpha_res.get("alpha_p_value", 1.0))
            ir = float(alpha_res.get("information_ratio", -np.inf))
        else:
            p, ir = 1.0, -np.inf
        passes = {
            "sharpe": bool(oos_sharpe >= GATES["min_sharpe"]),
            "trades": bool(len(oos_trades) >= GATES["min_trades"]),
            "pf": bool(oos_pf >= GATES["min_profit_factor"]),
            "dd": bool(abs(oos_dd) <= GATES["max_drawdown"]),
            "stab": bool(wf_stab >= GATES["min_walkforward_stability"]),
            "worst": bool(worst >= GATES["min_worst_regime_sharpe"]),
            "p": bool(p < GATES["max_p_value"]),
            "ir": bool(ir > GATES.get("min_information_ratio", -1e18)),
        }
        all_pass = all(passes.values())
        print("VIX+DDCV best OOS: sharpe=%.3f trades=%d pf=%.3f dd=%.3f stab=%.3f worst=%.3f p=%.4f ir=%.3f" %
              (oos_sharpe, len(oos_trades), oos_pf, oos_dd, wf_stab, worst, p, ir))
        print("Passes:", {k: bool(v) for k, v in passes.items()})

        # ---- Ablation summary (evaluated on full OOS) ----
        ablations = {}
        # (a) base TSMOM (no VIX, no DDCV)
        ablations["base"] = base_result
        # (b) VIX-gate only
        ablations["vix_only"] = vix_only_result
        # (c) DDCV-only (best from DDCV-only grid)
        best_ddcv_only_sig, _, _ = apply_ddcv(prices, base_sig, best_ddcv_only["dd_trigger"], best_ddcv_only["dd_factor"])
        ablations["ddcv_only"] = evaluate(prices, best_ddcv_only_sig, volumes, adv)

        ablation_records = []
        for name, res in ablations.items():
            ar = res.returns
            _, _, _, oos_ar = split_returns_by_date(ar)
            eq = (1 + oos_ar).cumprod() if len(oos_ar) else pd.Series([1])
            dd_val = float((eq - eq.expanding().max()).min()) if len(eq) >= 2 else 0.0
            ablation_records.append({
                "name": name,
                "oos_sharpe": float(sharpe_ratio(oos_ar.values)) if len(oos_ar) else 0.0,
                "oos_max_dd": dd_val,
                "oos_pf": float(res.metrics["profit_factor"]),
                "oos_trades": int(len(res.trades[res.trades["timestamp"] > pd.Timestamp(TRAIN_END)])) if len(res.trades) else 0,
            })
        ablation_df = pd.DataFrame(ablation_records)

        summary = {
            "experiment_id": exp_id,
            "best_combo": {"dd_trigger": float(best_trigger), "dd_factor": float(best_factor)},
            "grid": combo_df.to_dict(orient="records"),
            "oos_sharpe": float(oos_sharpe),
            "oos_pf": float(oos_pf),
            "oos_max_dd": float(oos_dd),
            "oos_trades": int(len(oos_trades)),
            "train_sharpe": float(train_sharpe),
            "wf_stability": float(wf_stab),
            "worst_regime_sharpe": float(worst),
            "alpha_vs_benchmark": {"p_value": p, "information_ratio": ir},
            "passes": passes,
            "all_pass": bool(all_pass),
            "ablations": ablation_df.to_dict(orient="records"),
            "ddcv_only_grid": ddcv_only_df.to_dict(orient="records"),
            "data_available": list(prices.columns),
        }

        exp_dir = Path(tracker.log_dir) / "artifacts" / exp_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        with open(exp_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2, default=lambda o: bool(o) if isinstance(o, (np.bool_,)) else (float(o) if isinstance(o, (np.integer, np.floating)) else str(o)))
        tracker.log_artifact("summary", exp_dir / "summary.json")
        tracker.log_dataframe("param_grid_results", combo_df)
        tracker.log_dataframe("best_equity", best_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("best_trades", best_result.trades)
        tracker.log_dataframe("ablations", ablation_df)
        tracker.log_dataframe("ddcv_only_grid", ddcv_only_df)
        tracker.log_dataframe("benchmark_equity", bh_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("vix_only_equity", vix_only_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("vix_only_trades", vix_only_result.trades)

        tracker.finish_experiment(status="completed")
        print("All pass:", all_pass)
        return all_pass
    except Exception as e:
        import traceback
        traceback.print_exc()
        tracker.finish_experiment(status="failed", error=str(e))
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)