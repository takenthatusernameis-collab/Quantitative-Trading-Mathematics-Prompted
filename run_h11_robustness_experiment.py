#!/usr/bin/env python3
"""H11: Robustness / Certification of the H10-selected intraday TSMOM config.

PRE-REGISTRATION (HYPOTHESIS_SPEC.md, H11 section — written before execution):

Null (H0): the H10 selected config, re-run on a perturbed seed/window/cost
model, fails any of the 8 gates (Sharpe < 1.0, PF < 1.3, DD > 15%,
WF stability < 0.7, worst-regime SR < 0.3, p >= 0.05, IR <= 0) or the
perturbation gate (min perturbed OOS Sharpe < 0.5 x optimum).

Experiments (frozen H10 config — no re-selection, Test never enters
selection):
  F1  Re-verify all 8 gates on the cached data (identical window to H10)
      and compare against the H10 artifact exp_2026-10-11T17-41-18-169363Z.
  E1  Seed robustness: full pipeline re-run under seeds {42, 7, 123, 2026}
      (determinism: bit-identical equity) + bootstrap OOS Sharpe CI
      (2,000 resamples) under seeds {42, 7, 123}.
  E2  +/-20% one-at-a-time parameter perturbations (10 OAT + 2 joint).
      Gate: min perturbed OOS Sharpe >= 0.5 x frozen OOS Sharpe
      (GATES["min_perturbed_sharpe_ratio"], never evaluated in H10).
  E3  Cost-model stress: commission/spread/slippage x {0.5,...,2.0}.
      Gate: PF >= 1.3 at both 0.5x and 1.5x costs.
  E4  Window robustness: shifted split boundaries, rolling 25%-of-sample
      window scan, and a shifted-window (50/25/25) coarse-grid re-selection.
  E5  Per-symbol concentration decomposition of OOS net returns.

Constraints (unchanged): no live trading, no secrets, no paid data, Test
never enters selection, preserve negative results, <= 4 CPU-h per
experiment, reuse existing engine / tracking / validation infrastructure.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from qtr.data.fetcher import get_data_fetcher
from qtr.backtest.engine import (
    run_backtest,
    BacktestConfig,
    AssetClass,
    CostModel,
)
from qtr.tracking.experiment import get_tracker
from qtr.validation.statistics import (
    sharpe_ratio,
    walk_forward_splits,
    compare_to_benchmark,
)

from run_h9_intraday_tsmom_experiment import (
    MAX_POSITION_SIZE,
    MAX_LEVERAGE,
)

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
    smooth_signal,
    regime_factor_hourly,
    build_hourly_target,
    apply_exits_hourly,
    _splits,
    _period_metrics,
    _count_in,
    _full_gate_eval,
    TARGET_VOL,
    VOL_WINDOW_SHORT_RATIO,
    EXIT_VOL_WINDOW,
    DATA_START,
    DATA_END,
)

EXPERIMENT_NAME = "h11_robustness_certification"
EXPERIMENT_DESC = (
    "H11: Robustness / certification of the H10-selected intraday TSMOM "
    "config — seed determinism, +/-20% parameter perturbation, +/-50% "
    "cost-model stress, shifted-window analysis, per-symbol concentration"
)

H10_ARTIFACT_ID = "exp_2026-10-11T17-41-18-169363Z"

H10_REFERENCE_METRICS = {
    "oos_sharpe": 1.2757590680990518,
    "profit_factor": 1.3041645169434146,
    "max_drawdown": -0.05842847204487622,
    "trades": 2416,
    "wf_stability": 0.7805709265313979,
    "worst_regime_sharpe": 1.045717651017743,
    "benchmark_p_value": 4.790305556723297e-10,
    "information_ratio": 0.9247889169803807,
}

FROZEN_CONFIG = {
    "vol_window_long": 1008,
    "smooth_span": None,
    "regime_scaling": False,
    "min_trade_interval": 0,
    "trailing_mult": 2.0,
    "max_hold_bars": 60,
    "vol_limit_mult": 1.5,
    "vol_floor_fraction": 0.25,
    "target_vol": TARGET_VOL,
}

SEED_SET = [42, 7, 123, 2026]
BOOTSTRAP_SEEDS = [42, 7, 123]
N_BOOTSTRAP = 2000

PERTURBATIONS = [
    ("vol_window_long", 806),
    ("vol_window_long", 1210),
    ("trailing_mult", 1.6),
    ("trailing_mult", 2.4),
    ("max_hold_bars", 48),
    ("max_hold_bars", 72),
    ("vol_limit_mult", 1.2),
    ("vol_limit_mult", 1.8),
    ("vol_floor_fraction", 0.2),
    ("vol_floor_fraction", 0.3),
    ("target_vol", 0.12),
    ("target_vol", 0.18),
]
JOINT_PERTURBATIONS = [
    (
        "joint_all_low",
        {"vol_window_long": 806, "trailing_mult": 1.6, "max_hold_bars": 48,
         "vol_limit_mult": 1.2, "vol_floor_fraction": 0.2, "target_vol": 0.12},
    ),
    (
        "joint_all_high",
        {"vol_window_long": 1210, "trailing_mult": 2.4, "max_hold_bars": 72,
         "vol_limit_mult": 1.8, "vol_floor_fraction": 0.3, "target_vol": 0.18},
    ),
]

COST_MULTIPLIERS = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]

SHIFTED_SPLITS = {
    "50/25/25": (0.50, 0.75),
    "60/20/20": (0.60, 0.80),
    "45/30/25": (0.45, 0.75),
}

E4C_VOL_WINDOWS = [252, 504, 1008]
E4C_TRAILING_MULTS = [1.5, 2.0, 2.5, 3.0]
E4C_MAX_HOLD_BARS = [60, 120, 240]
E4C_VOL_LIMIT_MULTS = [1.5, 2.0, 2.5]
E4C_VOL_FLOOR_FRACTIONS = [0.25, 0.5, 0.75]


def build_positions(
    prices, atr, vol_exit, vix_hourly,
    vol_window_long, smooth_span, regime_scaling, min_trade_interval,
    trailing_mult, max_hold_bars, vol_limit_mult, vol_floor_fraction,
    target_vol,
):
    """Signal + exit pipeline for one config (H10 machinery, frozen)."""
    signal = vol_scaled_tsmom_hourly(
        prices,
        vol_window_long=vol_window_long,
        vol_window_short=vol_window_long // VOL_WINDOW_SHORT_RATIO,
        target_vol=target_vol,
    )
    hourly_target = build_hourly_target(
        signal, smooth_span, vol_window_long, regime_scaling,
        vix_hourly, prices.index,
    )
    return apply_exits_hourly(
        hourly_target, prices, atr, vol_exit,
        trailing_mult=trailing_mult, max_hold_bars=max_hold_bars,
        vol_limit_mult=vol_limit_mult, vol_floor_fraction=vol_floor_fraction,
        target_vol=target_vol, min_trade_interval=min_trade_interval,
    )


def oos_metrics(result, oos_mask, prices):
    """OOS Sharpe / DD / PF / trades for a backtest result."""
    oos_ret = result.returns[oos_mask]
    return _period_metrics(oos_ret, _count_in(result.trades, oos_mask, prices))


def make_cost_stressed_config(multiplier: float) -> BacktestConfig:
    """Futures config with commission/spread/slippage scaled by ``multiplier``."""
    specs = {}
    for sym, s in FUTURES_SPECS.items():
        specs[sym] = {
            "multiplier": s["multiplier"],
            "tick_value": s["tick_value"],
            "tick_size": s["tick_size"],
            "commission": s["commission"] * multiplier,
            "spread_ticks": s["spread_ticks"] * multiplier,
            "slippage_ticks": s["slippage_ticks"] * multiplier,
        }
    cm = CostModel(
        future_commission_per_contract=COST_MODEL_DEFAULTS["future_commission_per_contract"] * multiplier,
        future_spread_ticks=COST_MODEL_DEFAULTS["future_spread_ticks"] * multiplier,
        future_slippage_ticks=COST_MODEL_DEFAULTS["future_slippage_ticks"] * multiplier,
        futures_specs=specs,
    )
    return BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        asset_class=AssetClass.FUTURE,
        max_position_size=MAX_POSITION_SIZE,
        max_leverage=MAX_LEVERAGE,
        allow_short=False,
        cost_model=cm,
    )


def bootstrap_sharpe_distribution(returns: pd.Series, seed: int, n_bootstrap: int) -> np.ndarray:
    """Bootstrap distribution of the (repo-convention) Sharpe ratio."""
    rng = np.random.default_rng(seed)
    vals = returns.values
    n = len(vals)
    sharpes = np.empty(n_bootstrap, dtype=float)
    for i in range(n_bootstrap):
        sample = vals[rng.integers(0, n, n)]
        sharpes[i] = sharpe_ratio(sample)
    return sharpes


def per_symbol_contributions(result, prices: pd.DataFrame, config: BacktestConfig) -> pd.DataFrame:
    """Decompose net returns into per-symbol gross P&L minus per-symbol costs.

    Reconstructs the engine's own computation from the post-constraint
    positions (``result.positions``); the per-symbol contributions sum
    exactly to ``result.returns`` (asserted by the caller).
    """
    signals = result.positions
    position_changes = signals.diff().fillna(signals.iloc[0])
    price_returns = prices.pct_change().fillna(0)

    contributions = {}
    for sym in prices.columns:
        gross = signals[sym].shift(1) * price_returns[sym]
        changes = position_changes[sym].abs()
        contract_cost = config.cost_model.future_cost_per_contract(sym)
        multiplier = config.cost_model.get_future_contract_multiplier(sym)
        contracts_traded = changes * config.initial_capital / (prices[sym] * multiplier)
        symbol_costs = contracts_traded.abs() * contract_cost / config.initial_capital
        contributions[sym] = (gross - symbol_costs).fillna(0.0)

    return pd.DataFrame(contributions, index=prices.index).fillna(0.0)


def probe_live_extension(fetcher) -> dict:
    """Live (uncached) probe: do fresh hourly bars exist beyond the cached window?"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    probe = {"today": today, "cached_last_bar": "2026-10-09", "symbols": {}}
    try:
        data = fetcher.fetch_futures(
            FUTURES_UNIVERSE, start="2026-10-01", end=today, interval="1h",
            use_cache=False,
        )
        freshest = None
        for sym in FUTURES_UNIVERSE:
            df = data.get(sym, pd.DataFrame())
            if len(df) == 0:
                probe["symbols"][sym] = None
                continue
            idx = pd.to_datetime(df.index)
            if hasattr(idx, "tz_convert") and idx.tzinfo is not None:
                idx = idx.tz_convert(None)
            last = str(idx.max())
            probe["symbols"][sym] = last
            ts = pd.Timestamp(last)
            if freshest is None or ts > freshest:
                freshest = ts
        probe["freshest_bar"] = (str(freshest) if freshest is not None else None)
        probe["fresh_bars_beyond_cached"] = bool(
            freshest is not None and freshest > pd.Timestamp("2026-10-09 16:00:00")
        )
    except Exception as e:
        probe["error"] = str(e)
        probe["fresh_bars_beyond_cached"] = False
    return probe


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
            "frozen_config": {k: (str(v) if v is None else v) for k, v in FROZEN_CONFIG.items()},
            "seed_set": SEED_SET,
            "bootstrap_seeds": BOOTSTRAP_SEEDS,
            "n_bootstrap": N_BOOTSTRAP,
            "perturbations": [[p, v] for p, v in PERTURBATIONS],
            "joint_perturbations": [n for n, _ in JOINT_PERTURBATIONS],
            "cost_multipliers": COST_MULTIPLIERS,
            "shifted_splits": {k: list(v) for k, v in SHIFTED_SPLITS.items()},
            "e4c_grid": {
                "vol_window_long": E4C_VOL_WINDOWS,
                "trailing_mult": E4C_TRAILING_MULTS,
                "max_hold_bars": E4C_MAX_HOLD_BARS,
                "vol_limit_mult": E4C_VOL_LIMIT_MULTS,
                "vol_floor_fraction": E4C_VOL_FLOOR_FRACTIONS,
            },
        },
        data_sources={
            "source": "yahoo_futures_cached",
            "symbols": FUTURES_UNIVERSE,
            "vix": VIX_SYMBOL,
            "interval": "1h",
        },
        compute_budget={"max_cpu_hours": 4.0},
        random_seeds={"numpy": SEED, "python": SEED},
    )
    print(f"[H11] started {exp_id}")
    print(f"[H11] frozen config: {FROZEN_CONFIG}")

    try:
        fetcher = get_data_fetcher()

        # --- data (cached, identical window to H10) ---
        data = fetcher.fetch_futures(
            FUTURES_UNIVERSE, start=DATA_START, end=DATA_END, interval="1h"
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
        prices = pd.concat(prices_list, axis=1, sort=True).sort_index()
        volumes = pd.concat(volumes_list, axis=1, sort=True).sort_index().fillna(0)
        prices = prices.ffill().bfill()
        volumes = volumes.reindex(prices.index).fillna(0)

        vix_df = fetcher.fetch_yahoo(
            [VIX_SYMBOL], start=DATA_START, end=DATA_END, interval="1h"
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

        train_mask, val_mask, test_mask = _splits(prices)
        oos_mask = val_mask | test_mask
        print(
            f"[H11] prices={prices.shape} train/val/test="
            f"{int(train_mask.sum())}/{int(val_mask.sum())}/{int(test_mask.sum())}"
        )

        # --- precomputed exit inputs (price-derived, config-independent) ---
        pct = prices.pct_change().fillna(0)
        atr = prices * pct.rolling(14, min_periods=7).std()
        atr = atr.replace(0, np.nan).ffill().fillna(prices * 0.001)
        vol_exit = pct.rolling(EXIT_VOL_WINDOW, min_periods=EXIT_VOL_WINDOW // 2).std() * np.sqrt(252 * 6.5)
        vol_exit = vol_exit.replace(0, np.nan).ffill()

        cfg = make_futures_config()
        bh_weights = pd.DataFrame(
            1.0 / len(prices.columns), index=prices.index, columns=prices.columns
        )
        bh_result = run_backtest(prices=prices, signals=bh_weights, volumes=volumes, config=cfg)

        # =================================================================
        # F1 — gate re-verification on the frozen config
        # =================================================================
        frozen_positions = build_positions(
            prices, atr, vol_exit, vix_hourly, **FROZEN_CONFIG
        )
        frozen_result = run_backtest(
            prices=prices, signals=frozen_positions, volumes=volumes, config=cfg
        )
        gate = _full_gate_eval(
            frozen_result, oos_mask, val_mask, test_mask, prices, vix_hourly, bh_result
        )

        reference_check = {}
        for key, ref_val in H10_REFERENCE_METRICS.items():
            if key == "trades":
                actual = int(gate["oos_metrics"]["trades"])
            elif key == "oos_sharpe":
                actual = float(gate["oos_metrics"]["sharpe"])
            elif key == "profit_factor":
                actual = float(gate["oos_metrics"]["profit_factor"])
            elif key == "max_drawdown":
                actual = float(gate["oos_metrics"]["max_drawdown"])
            else:
                actual = float(gate.get(key, np.nan))
            reference_check[key] = {
                "h10_artifact": ref_val,
                "h11_rerun": actual,
                "abs_diff": abs(float(actual) - float(ref_val)),
                "reproduced": abs(float(actual) - float(ref_val)) < 1e-9,
            }
        f1_reproduced = all(v["reproduced"] for v in reference_check.values())
        print(f"[H11] F1 gate re-verification: {int(sum(gate['passes'].values()))}/8 "
              f"passes; metrics reproduced vs H10 artifact: {f1_reproduced}")

        frozen_oos_sharpe = float(gate["oos_metrics"]["sharpe"])

        # =================================================================
        # E1 — seed robustness (determinism + bootstrap CI)
        # =================================================================
        seed_rows = []
        for seed in SEED_SET:
            np.random.seed(seed)
            pos = build_positions(
                prices, atr, vol_exit, vix_hourly, **FROZEN_CONFIG
            )
            res = run_backtest(
                prices=prices, signals=pos, volumes=volumes, config=cfg
            )
            m = oos_metrics(res, oos_mask, prices)
            max_diff = float(
                np.max(np.abs(res.equity_curve.values - frozen_result.equity_curve.values))
            )
            seed_rows.append({
                "seed": seed,
                "oos_sharpe": m["sharpe"],
                "oos_profit_factor": m["profit_factor"],
                "oos_max_drawdown": m["max_drawdown"],
                "oos_trades": m["trades"],
                "max_equity_abs_diff_vs_seed42": max_diff,
            })
        seed_df = pd.DataFrame(seed_rows)
        determinism_holds = bool(
            (seed_df["max_equity_abs_diff_vs_seed42"] == 0.0).all()
        )
        print(f"[H11] E1 determinism across seeds {SEED_SET}: "
              f"{'HOLDS (bit-identical)' if determinism_holds else 'VIOLATED'}")

        bootstrap_rows = []
        bootstrap_distributions = {}
        for seed in BOOTSTRAP_SEEDS:
            sharpes = bootstrap_sharpe_distribution(
                frozen_result.returns[oos_mask], seed, N_BOOTSTRAP
            )
            bootstrap_distributions[seed] = sharpes
            bootstrap_rows.append({
                "seed": seed,
                "n_bootstrap": N_BOOTSTRAP,
                "mean": float(np.mean(sharpes)),
                "std": float(np.std(sharpes)),
                "ci_lo": float(np.percentile(sharpes, 2.5)),
                "ci_hi": float(np.percentile(sharpes, 97.5)),
                "min": float(np.min(sharpes)),
                "frac_sharpe_ge_1": float(np.mean(sharpes >= 1.0)),
            })
        bootstrap_df = pd.DataFrame(bootstrap_rows)
        print(f"[H11] E1 bootstrap OOS Sharpe CI (seed {BOOTSTRAP_SEEDS[0]}): "
              f"[{bootstrap_rows[0]['ci_lo']:.3f}, {bootstrap_rows[0]['ci_hi']:.3f}], "
              f"P(Sharpe>=1.0)={bootstrap_rows[0]['frac_sharpe_ge_1']:.3f}")

        # =================================================================
        # E2 — +/-20% parameter perturbations (OAT + joint)
        # =================================================================
        perturbation_rows = []

        def _eval_variant(name, params):
            pos = build_positions(prices, atr, vol_exit, vix_hourly, **params)
            res = run_backtest(
                prices=prices, signals=pos, volumes=volumes, config=cfg
            )
            m = oos_metrics(res, oos_mask, prices)
            g = _full_gate_eval(
                res, oos_mask, val_mask, test_mask, prices, vix_hourly, bh_result
            )
            row = {"variant": name, **{k: v for k, v in params.items()}}
            row.update({
                "oos_sharpe": m["sharpe"],
                "oos_profit_factor": m["profit_factor"],
                "oos_max_drawdown": m["max_drawdown"],
                "oos_trades": m["trades"],
                "gates_passed": int(sum(g["passes"].values())),
                "gates": g["passes"],
            })
            perturbation_rows.append(row)
            return m

        for param, value in PERTURBATIONS:
            params = dict(FROZEN_CONFIG)
            params[param] = value
            direction = "low" if value < FROZEN_CONFIG[param] else "high"
            m = _eval_variant(f"{param}={value} ({direction} 20%)", params)
            print(f"[H11] E2 perturb {param:20s} {direction:4s} -> OOS Sharpe "
                  f"{m['sharpe']:.3f} PF {m['profit_factor']:.3f}")

        for name, overrides in JOINT_PERTURBATIONS:
            params = dict(FROZEN_CONFIG)
            params.update(overrides)
            m = _eval_variant(name, params)
            print(f"[H11] E2 perturb {name} -> OOS Sharpe {m['sharpe']:.3f} "
                  f"PF {m['profit_factor']:.3f}")

        perturbation_df = pd.DataFrame(perturbation_rows)
        perturbed_sharpes = perturbation_df["oos_sharpe"].astype(float).values
        min_perturbed_sharpe = float(np.min(perturbed_sharpes))
        perturbation_ratio = min_perturbed_sharpe / frozen_oos_sharpe
        perturbation_gate = bool(
            perturbation_ratio >= GATES["min_perturbed_sharpe_ratio"]
        )
        print(f"[H11] E2 perturbation gate: min perturbed Sharpe {min_perturbed_sharpe:.3f} "
              f"= {perturbation_ratio:.3f} x optimum (gate >= "
              f"{GATES['min_perturbed_sharpe_ratio']}) -> "
              f"{'PASS' if perturbation_gate else 'FAIL'}")

        # =================================================================
        # E3 — cost-model stress (+/-50% and beyond)
        # =================================================================
        cost_rows = []
        for mult in COST_MULTIPLIERS:
            stress_cfg = make_cost_stressed_config(mult)
            res = run_backtest(
                prices=prices, signals=frozen_positions, volumes=volumes,
                config=stress_cfg,
            )
            m = oos_metrics(res, oos_mask, prices)
            cost_rows.append({
                "cost_multiplier": mult,
                "commission_per_contract": COST_MODEL_DEFAULTS["future_commission_per_contract"] * mult,
                "spread_ticks": COST_MODEL_DEFAULTS["future_spread_ticks"] * mult,
                "slippage_ticks": COST_MODEL_DEFAULTS["future_slippage_ticks"] * mult,
                "oos_sharpe": m["sharpe"],
                "oos_profit_factor": m["profit_factor"],
                "oos_max_drawdown": m["max_drawdown"],
                "oos_trades": m["trades"],
                "total_cost_bps_of_equity": float(res.returns.values.sum() - frozen_result.returns.values.sum()),
            })
        cost_df = pd.DataFrame(cost_rows)

        def _pf_at(mult):
            row = cost_df[cost_df["cost_multiplier"] == mult]
            return float(row["oos_profit_factor"].iloc[0])

        pf_low = _pf_at(0.5)
        pf_high = _pf_at(1.5)
        cost_gate = bool(pf_low >= GATES["min_profit_factor"] and pf_high >= GATES["min_profit_factor"])

        pf_series = cost_df["oos_profit_factor"].astype(float).values
        mult_series = cost_df["cost_multiplier"].astype(float).values
        order = np.argsort(mult_series)
        breakeven = None
        for i in range(len(order) - 1):
            m0, m1 = mult_series[order][i], mult_series[order][i + 1]
            p0, p1 = pf_series[order][i], pf_series[order][i + 1]
            if (p0 - 1.3) * (p1 - 1.3) <= 0 and p0 != p1:
                breakeven = float(m0 + (1.3 - p0) * (m1 - m0) / (p1 - p0))
                break
        if breakeven is None and np.min(pf_series) >= 1.3:
            breakeven = float("inf")
        print(f"[H11] E3 cost stress: PF(0.5x)={pf_low:.3f} PF(1.0x)={_pf_at(1.0):.3f} "
              f"PF(1.5x)={pf_high:.3f} PF(2.0x)={_pf_at(2.0):.3f}; "
              f"break-even cost multiplier for PF=1.3: "
              f"{'>2.0' if breakeven == float('inf') else (f'{breakeven:.3f}' if breakeven else '<0.5')}")
        print(f"[H11] E3 cost gate (PF >= 1.3 at +/-50%): "
              f"{'PASS' if cost_gate else 'FAIL'}")

        # =================================================================
        # E4 — window robustness
        # =================================================================
        # E4a — shifted split boundaries (frozen positions, OOS mask varies)
        split_rows = []
        for split_name, (train_frac, val_end_frac) in SHIFTED_SPLITS.items():
            s_train_end = prices.index[int(len(prices) * train_frac)]
            s_val_end = prices.index[int(len(prices) * val_end_frac)]
            s_train = prices.index <= s_train_end
            s_val = (prices.index > s_train_end) & (prices.index <= s_val_end)
            s_test = prices.index > s_val_end
            s_oos = s_val | s_test
            m = oos_metrics(frozen_result, s_oos, prices)
            split_rows.append({
                "split": split_name,
                "train_frac": train_frac,
                "val_frac": val_end_frac - train_frac,
                "test_frac": 1.0 - val_end_frac,
                "oos_bars": int(s_oos.sum()),
                "oos_sharpe": m["sharpe"],
                "oos_profit_factor": m["profit_factor"],
                "oos_max_drawdown": m["max_drawdown"],
                "oos_trades": m["trades"],
            })
        split_df = pd.DataFrame(split_rows)
        print("[H11] E4a shifted splits:")
        for _, r in split_df.iterrows():
            print(f"      {r['split']}: Sharpe {r['oos_sharpe']:.3f} PF {r['oos_profit_factor']:.3f} "
                  f"DD {r['oos_max_drawdown']:.3f} trades {int(r['oos_trades'])}")

        # E4b — rolling 25%-of-sample window scan (step 5%)
        n = len(prices)
        window_len = int(n * 0.25)
        step = max(1, int(n * 0.05))
        rolling_rows = []
        for start in range(0, n - window_len + 1, step):
            end = start + window_len
            mask = pd.Series(False, index=prices.index)
            mask.iloc[start:end] = True
            m = oos_metrics(frozen_result, mask, prices)
            rolling_rows.append({
                "window_start": str(prices.index[start]),
                "window_end": str(prices.index[end - 1]),
                "oos_sharpe": m["sharpe"],
                "oos_profit_factor": m["profit_factor"],
                "oos_max_drawdown": m["max_drawdown"],
                "oos_trades": m["trades"],
            })
        rolling_df = pd.DataFrame(rolling_rows)
        rolling_sharpes = rolling_df["oos_sharpe"].astype(float).values
        print(f"[H11] E4b rolling 25% windows ({len(rolling_df)}): Sharpe "
              f"min {np.min(rolling_sharpes):.3f} / mean {np.mean(rolling_sharpes):.3f} / "
              f"max {np.max(rolling_sharpes):.3f}; "
              f"{int(np.mean(rolling_sharpes >= 1.0) * 100)}% of windows >= 1.0")

        # E4c — shifted-window (50/25/25) coarse-grid re-selection
        c_train_end = prices.index[int(len(prices) * 0.50)]
        c_val_end = prices.index[int(len(prices) * 0.75)]
        c_val_mask = (prices.index > c_train_end) & (prices.index <= c_val_end)
        c_test_mask = prices.index > c_val_end
        c_oos_mask = c_val_mask | c_test_mask

        e4c_rows = []
        best_val_sharpe = -np.inf
        best_c = None
        for vw in E4C_VOL_WINDOWS:
            signal = vol_scaled_tsmom_hourly(
                prices, vol_window_long=vw, vol_window_short=vw // VOL_WINDOW_SHORT_RATIO
            )
            hourly_target = build_hourly_target(
                signal, None, vw, False, vix_hourly, prices.index
            )
            for tm in E4C_TRAILING_MULTS:
                for mhb in E4C_MAX_HOLD_BARS:
                    for vlm in E4C_VOL_LIMIT_MULTS:
                        for vff in E4C_VOL_FLOOR_FRACTIONS:
                            pos = apply_exits_hourly(
                                hourly_target, prices, atr, vol_exit,
                                trailing_mult=tm, max_hold_bars=mhb,
                                vol_limit_mult=vlm, vol_floor_fraction=vff,
                                target_vol=TARGET_VOL, min_trade_interval=0,
                            )
                            res = run_backtest(
                                prices=prices, signals=pos, volumes=volumes, config=cfg
                            )
                            val_ret = res.returns[c_val_mask]
                            val_tr = _count_in(res.trades, c_val_mask, prices)
                            vm = _period_metrics(val_ret, val_tr)
                            e4c_rows.append({
                                "vol_window_long": vw,
                                "trailing_mult": tm,
                                "max_hold_bars": mhb,
                                "vol_limit_mult": vlm,
                                "vol_floor_fraction": vff,
                                "shifted_val_sharpe": vm["sharpe"],
                                "shifted_val_profit_factor": vm["profit_factor"],
                            })
                            if vm["sharpe"] > best_val_sharpe:
                                best_val_sharpe = vm["sharpe"]
                                best_c = (vw, tm, mhb, vlm, vff)
        e4c_df = pd.DataFrame(e4c_rows)
        best_vw_counts = e4c_df.groupby("vol_window_long")["shifted_val_sharpe"].max()
        c_vw, c_tm, c_mhb, c_vlm, c_vff = best_c
        c_signal = vol_scaled_tsmom_hourly(
            prices, vol_window_long=c_vw, vol_window_short=c_vw // VOL_WINDOW_SHORT_RATIO
        )
        c_target = build_hourly_target(
            c_signal, None, c_vw, False, vix_hourly, prices.index
        )
        c_positions = apply_exits_hourly(
            c_target, prices, atr, vol_exit,
            trailing_mult=c_tm, max_hold_bars=c_mhb,
            vol_limit_mult=c_vlm, vol_floor_fraction=c_vff,
            target_vol=TARGET_VOL, min_trade_interval=0,
        )
        c_result = run_backtest(
            prices=prices, signals=c_positions, volumes=volumes, config=cfg
        )
        c_gate = _full_gate_eval(
            c_result, c_oos_mask, c_val_mask, c_test_mask, prices, vix_hourly, bh_result
        )
        print(f"[H11] E4c shifted 50/25/25 re-selection: best shifted-Val Sharpe "
              f"{best_val_sharpe:.3f} at vw={c_vw} tm={c_tm} mhb={c_mhb} vlm={c_vlm} vff={c_vff}")
        print(f"[H11] E4c shifted-window selected config OOS: Sharpe "
              f"{c_gate['oos_metrics']['sharpe']:.3f} PF {c_gate['oos_metrics']['profit_factor']:.3f} "
              f"-> {c_gate['verdict']} ({int(sum(c_gate['passes'].values()))}/8 gates)")
        print(f"[H11] E4c best Val Sharpe by vol window: "
              + ", ".join(f"{vw}:{v:.3f}" for vw, v in best_vw_counts.items()))

        # =================================================================
        # E5 — per-symbol concentration
        # =================================================================
        contributions = per_symbol_contributions(frozen_result, prices, cfg)
        recon_diff = float(
            np.max(np.abs(contributions.sum(axis=1).values - frozen_result.returns.values))
        )
        oos_contrib = contributions[oos_mask]
        per_symbol_rows = []
        for sym in prices.columns:
            r = oos_contrib[sym]
            sr = float(sharpe_ratio(r.values)) if len(r) > 1 and r.std() > 0 else 0.0
            gp = float(r[r > 0].sum())
            gl = float(abs(r[r < 0].sum()))
            pf = gp / gl if gl > 0 else float("inf")
            pnl = float(r.sum())
            trades_in_oos = int(
                (frozen_result.positions[sym].diff().fillna(0) != 0)[oos_mask].sum()
            )
            per_symbol_rows.append({
                "symbol": sym,
                "oos_sharpe": sr,
                "oos_profit_factor": pf,
                "oos_pnl": pnl,
                "oos_gross_profit": gp,
                "oos_gross_loss": gl,
                "oos_trades": trades_in_oos,
            })
        per_symbol_df = pd.DataFrame(per_symbol_rows)
        total_pnl = per_symbol_df["oos_pnl"].sum()
        per_symbol_df["pnl_share"] = per_symbol_df["oos_pnl"] / total_pnl
        per_symbol_df["abs_pnl_share"] = per_symbol_df["oos_pnl"].abs() / per_symbol_df["oos_pnl"].abs().sum()
        per_symbol_df["gross_profit_share"] = per_symbol_df["oos_gross_profit"] / per_symbol_df["oos_gross_profit"].sum()
        hhi_abs = float((per_symbol_df["abs_pnl_share"] ** 2).sum())
        hhi_gp = float((per_symbol_df["gross_profit_share"] ** 2).sum())
        max_gp_share = float(per_symbol_df["gross_profit_share"].max())
        worst_sym_sharpe = float(per_symbol_df["oos_sharpe"].min())
        concentration_flag = bool(max_gp_share > 0.60 or worst_sym_sharpe < 0)
        print(f"[H11] E5 per-symbol decomposition (reconstruction max|diff|={recon_diff:.2e}):")
        for _, r in per_symbol_df.iterrows():
            print(f"      {r['symbol']}: Sharpe {r['oos_sharpe']:.3f} PF {r['oos_profit_factor']:.3f} "
                  f"P&L {r['oos_pnl']:.4f} (share {r['pnl_share']:.3f}) trades {int(r['oos_trades'])}")
        print(f"[H11] E5 HHI(|P&L| shares)={hhi_abs:.3f} HHI(gross-profit shares)={hhi_gp:.3f} "
              f"max gross-profit share={max_gp_share:.3f} worst symbol Sharpe={worst_sym_sharpe:.3f}")

        # =================================================================
        # Live-extension probe (OOS time-extension feasibility)
        # =================================================================
        extension_probe = probe_live_extension(fetcher)
        print(f"[H11] live-extension probe: freshest bar={extension_probe.get('freshest_bar')} "
              f"fresh_bars_beyond_cached={extension_probe.get('fresh_bars_beyond_cached')}")

        # =================================================================
        # Verdict (pre-registered rule)
        # =================================================================
        f1_gates_pass = bool(all(gate["passes"].values()))
        verdict_pass = bool(
            f1_gates_pass and perturbation_gate and cost_gate and determinism_holds
        )
        total_elapsed = time.time() - t_start

        summary = {
            "experiment_id": exp_id,
            "hypothesis": "H11",
            "h10_artifact_id": H10_ARTIFACT_ID,
            "frozen_config": {k: (str(v) if v is None else v) for k, v in FROZEN_CONFIG.items()},
            "f1": {
                "gates": gate["passes"],
                "gates_passed": int(sum(gate["passes"].values())),
                "all_pass": f1_gates_pass,
                "oos_metrics": gate["oos_metrics"],
                "test_metrics": gate["test_metrics"],
                "train_sharpe": gate["train_sharpe"],
                "wf_stability": gate["wf_stability"],
                "worst_regime_sharpe": gate["worst_regime_sharpe"],
                "regime_sharpes": gate["regime_sharpes"],
                "benchmark_p_value": gate["benchmark_p_value"],
                "information_ratio": gate["information_ratio"],
                "reproduced_vs_h10_artifact": reference_check,
                "metrics_reproduced": f1_reproduced,
            },
            "e1_seed_robustness": {
                "determinism_holds": determinism_holds,
                "seeds": seed_rows,
                "bootstrap": bootstrap_rows,
            },
            "e2_perturbation": {
                "gate": "min_perturbed_oos_sharpe >= 0.5 x frozen_oos_sharpe",
                "frozen_oos_sharpe": frozen_oos_sharpe,
                "min_perturbed_sharpe": min_perturbed_sharpe,
                "perturbation_ratio": perturbation_ratio,
                "gate_threshold": GATES["min_perturbed_sharpe_ratio"],
                "passes": perturbation_gate,
                "variants": perturbation_rows,
            },
            "e3_cost_stress": {
                "gate": "PF >= 1.3 at 0.5x and 1.5x costs",
                "pf_at_0_5x": pf_low,
                "pf_at_1_0x": _pf_at(1.0),
                "pf_at_1_5x": pf_high,
                "pf_at_2_0x": _pf_at(2.0),
                "breakeven_cost_multiplier_for_pf_1_3": (
                    ">2.0" if breakeven == float("inf") else (breakeven if breakeven else "<0.5")
                ),
                "passes": cost_gate,
                "variants": cost_rows,
            },
            "e4_window_robustness": {
                "shifted_splits": split_rows,
                "rolling_window_summary": {
                    "n_windows": len(rolling_df),
                    "min_sharpe": float(np.min(rolling_sharpes)),
                    "mean_sharpe": float(np.mean(rolling_sharpes)),
                    "max_sharpe": float(np.max(rolling_sharpes)),
                    "frac_windows_sharpe_ge_1": float(np.mean(rolling_sharpes >= 1.0)),
                },
                "rolling_windows": rolling_rows,
                "shifted_reselection": {
                    "split": "50/25/25",
                    "grid_size": len(e4c_rows),
                    "best_shifted_val_sharpe": best_val_sharpe,
                    "selected_config": {
                        "vol_window_long": c_vw,
                        "trailing_mult": c_tm,
                        "max_hold_bars": c_mhb,
                        "vol_limit_mult": c_vlm,
                        "vol_floor_fraction": c_vff,
                    },
                    "best_val_sharpe_by_vol_window": {
                        str(vw): float(v) for vw, v in best_vw_counts.items()
                    },
                    "oos_metrics": c_gate["oos_metrics"],
                    "gates": c_gate["passes"],
                    "verdict": c_gate["verdict"],
                },
                "note": (
                    "Longer intraday history is not available from the free "
                    "yfinance source (hourly =F limited to ~730 days; live probe "
                    "returns no bars beyond 2026-10-09). Shifted splits, rolling "
                    "windows and a shifted-window re-selection are the feasible "
                    "offline analogues of the pre-registered shifted-window re-run."
                ),
            },
            "e5_per_symbol": {
                "reconstruction_max_abs_diff": recon_diff,
                "per_symbol": per_symbol_rows,
                "hhi_abs_pnl_shares": hhi_abs,
                "hhi_gross_profit_shares": hhi_gp,
                "max_gross_profit_share": max_gp_share,
                "worst_symbol_sharpe": worst_sym_sharpe,
                "concentration_flag": concentration_flag,
            },
            "live_extension_probe": extension_probe,
            "total_elapsed_sec": float(round(total_elapsed, 1)),
            "compute_cpu_hours": float(round(total_elapsed / 3600, 3)),
            "verdict_components": {
                "f1_gates_pass": f1_gates_pass,
                "determinism_holds": determinism_holds,
                "perturbation_gate_passes": perturbation_gate,
                "cost_stress_gate_passes": cost_gate,
            },
            "all_pass": verdict_pass,
            "verdict": "PASS" if verdict_pass else "REJECT",
        }

        exp_dir = Path(tracker.log_dir) / "artifacts" / exp_id
        exp_dir.mkdir(parents=True, exist_ok=True)

        tracker.log_dataframe("seed_determinism", seed_df)
        tracker.log_dataframe("bootstrap_sharpe", bootstrap_df)
        tracker.log_dataframe("perturbation_results", perturbation_df.drop(columns=["gates"]))
        tracker.log_dataframe("cost_stress_results", cost_df)
        tracker.log_dataframe("split_shift_results", split_df)
        tracker.log_dataframe("rolling_window_results", rolling_df)
        tracker.log_dataframe("shifted_grid_results", e4c_df)
        tracker.log_dataframe("per_symbol_results", per_symbol_df)
        tracker.log_dataframe("frozen_equity", frozen_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("frozen_returns", frozen_result.returns.to_frame("returns"))
        tracker.log_dataframe("frozen_positions", frozen_positions)
        tracker.log_dataframe("frozen_trades", frozen_result.trades)
        tracker.log_dataframe("per_symbol_contributions", contributions)
        tracker.log_dataframe("benchmark_equity", bh_result.equity_curve.to_frame("equity"))

        with open(exp_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2,
                      default=lambda x: float(x) if isinstance(x, (np.integer, np.floating))
                      else str(x))
        tracker.log_artifact("summary", exp_dir / "summary.json")
        tracker.finish_experiment(status="completed")

        print("\n" + "=" * 72)
        print(f"  H11 VERDICT: {summary['verdict']}")
        print(f"  F1 gate re-verification: {int(sum(gate['passes'].values()))}/8 "
              f"(reproduced vs H10 artifact: {f1_reproduced})")
        print(f"  E1 determinism: {'HOLDS' if determinism_holds else 'VIOLATED'}")
        print(f"  E2 perturbation gate: {'PASS' if perturbation_gate else 'FAIL'} "
              f"(ratio {perturbation_ratio:.3f} >= {GATES['min_perturbed_sharpe_ratio']})")
        print(f"  E3 cost stress gate: {'PASS' if cost_gate else 'FAIL'} "
              f"(PF 0.5x={pf_low:.3f}, 1.5x={pf_high:.3f})")
        print(f"  E4/E5 diagnostics: shifted-split Sharpe range "
              f"{split_df['oos_sharpe'].min():.3f}-{split_df['oos_sharpe'].max():.3f}; "
              f"rolling-window min {np.min(rolling_sharpes):.3f}; "
              f"HHI(|P&L|)={hhi_abs:.3f}")
        print(f"  Compute: {total_elapsed/3600:.3f} CPU-h (budget 4.0)")
        print("=" * 72)
        return 0 if verdict_pass else 1
    except Exception as e:
        import traceback
        traceback.print_exc()
        tracker.finish_experiment(status="failed", error=str(e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
