"""H22: Multi-Contract Intraday Futures TSMOM — Vol-Targeting Gap Test.

Generalizes the H10/H11 certified intraday TSMOM edge (vol-scaled, path-dependent
exits) across a diversified basket of 5 liquid futures contracts (ES=F, NQ=F,
CL=F, GC=F, ZB=F) with risk-parity aggregation. 8-combo grid (target_vol x
max_pos; scale_rule and n_assets are fixed inert dimensions), Val-selected,
Test-protected, same gates as H9-H11 plus the perturbation gate.

Grid (all Val-only selection; Test never enters selection):
  - target_vol_mult   in {1.25, 1.5, 1.75, 2.0}  (multiplier on base 15% ann vol)
  - max_pos           in {0.5, 1.0}
  - scale_rule        in {"equal"}                 (fixed)
  - n_assets          in {5}                      (fixed)

The H10 selected signal/exit config (vol_window_long=1008, trailing_mult=2.0,
max_hold_bars=60, vol_limit_mult=1.5, vol_floor_fraction=0.25) is frozen; only
the vol-targeting envelope varies. 8-combo grid.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import json
import time
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

from qtr.backtest.engine import run_backtest
from qtr.data.fetcher import get_data_fetcher
from qtr.tracking.experiment import get_tracker
from qtr.validation.statistics import sharpe_ratio

# Reuse H10/H11 constants / primitives (single source of truth for universe,
# costs, gates, exit logic).
from run_h10_intraday_tsmom_pfopt_experiment import (
    FUTURES_UNIVERSE,
    GATES,
    INITIAL_CAPITAL,  # noqa: F401 - re-exported for test-pinning of constants
    SEED,
    VIX_SYMBOL,
    _count_in,
    _daily_target_from_hourly,
    _full_gate_eval,
    _period_metrics,
    _splits,
    apply_exits_hourly,
    build_hourly_target,
    make_futures_config,
    regime_factor_hourly,
    regime_labels,  # noqa: F401 - re-exported for regime-label test pinning
    vol_scaled_tsmom_hourly,
)

EXPERIMENT_NAME = "h22_futures_tsmom_voltarget"
EXPERIMENT_DESC = "H22: Vol-targeting expansion test on H21 basket; 8-combo grid (target_vol x max_pos; scale_rule and n_assets are fixed inert dimensions), Val-selected, Test-protected, same gates as H10/H11"

# H10 selected config (frozen for H21 signal generation per contract).
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
TARGET_VOL_BASE = 0.15  # H10 base; grid scales this
VOL_WINDOW_SHORT_RATIO = 4

# Fixed dates matching the cached hourly futures + VIX so the run is offline.
DATA_START = "2024-10-12"
DATA_END = "2026-10-11"

# Grid (per H22 pre-registration).
TARGET_VOLS = [
    0.50,
    0.75,
    1.0,
    1.5,
]  # multiplier on base 15% -> 7.5%, 11.25%, 15%, 22.5% annualized
MAX_POSITIONS = [0.5, 1.0]
SCALE_RULES = ["equal"]  # fixed per H22 (inert dim fixed)
N_ASSETS_CHOICES = [5]  # fixed per H22 (inert dim fixed)

# Exit-internal fixed parameters (identical to H10).
EXIT_VOL_WINDOW = 20
EXIT_VOL_FLOOR_DEFAULT = 0.5
EXIT_TRAILING_DEFAULT = 2.0
EXIT_MAX_HOLD_DEFAULT = 120
EXIT_VOL_LIMIT_DEFAULT = 2.0


def _build_data(fetcher, start, end):
    """Load cached hourly futures + VIX, tz-normalized exactly like H10."""
    data = fetcher.fetch_futures(FUTURES_UNIVERSE, start=start, end=end, interval="1h")
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
    volumes = (
        pd.concat(volumes_list, axis=1, sort=True)
        .sort_index()
        .reindex(prices.index)
        .fillna(0)
    )

    vix_df = fetcher.fetch_yahoo([VIX_SYMBOL], start=start, end=end, interval="1h")
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
    vol_exit = pct.rolling(
        EXIT_VOL_WINDOW, min_periods=EXIT_VOL_WINDOW // 2
    ).std() * np.sqrt(252 * 6.5)
    vol_exit = vol_exit.replace(0, np.nan).ffill()
    return atr, vol_exit


def _build_per_contract_base_signals(prices):
    """Build the H10 base signal per contract (same vol window for all)."""
    base_signals = {}
    for sym in prices.columns:
        px = prices[[sym]]
        base_signals[sym] = vol_scaled_tsmom_hourly(
            px,
            vol_window_long=SEL["vol_window_long"],
            vol_window_short=SEL["vol_window_long"] // VOL_WINDOW_SHORT_RATIO,
        )
    return base_signals


def _apply_exits_and_aggregate(
    prices,
    volumes,
    vix_hourly,
    atr,
    vol_exit,
    base_signals,
    target_vol_mult,
    max_pos,
    scale_rule,
    n_assets,
    min_trade_interval=0,
):
    """Apply exits per contract, then aggregate cross-sectionally.

    Returns:
        per_contract_positions: DataFrame of hourly positions per contract (for backtest)
        agg_positions: DataFrame with single 'BASKET' column (for reporting)
        selected_per_contract: DataFrame of hourly positions for selected assets only
    """
    # Select asset subset
    if n_assets == 3:
        assets = ["ES=F", "NQ=F", "CL=F"]
    else:
        assets = list(prices.columns)

    # Build hourly targets per contract (using H10 pipeline)
    hourly_targets = {}
    for sym in assets:
        bt = build_hourly_target(
            base_signals[sym],
            SEL["smooth_span"],
            SEL["vol_window_long"],
            SEL["regime_scaling"],
            vix_hourly,
            prices.index,
        )
        hourly_targets[sym] = bt[sym]

    # Apply exits per contract
    per_contract_positions = {}
    for sym in assets:
        pos = apply_exits_hourly(
            hourly_targets[sym].to_frame(sym),
            prices[[sym]],
            atr[[sym]],
            vol_exit[[sym]],
            trailing_mult=SEL["trailing_mult"],
            max_hold_bars=SEL["max_hold_bars"],
            vol_limit_mult=SEL["vol_limit_mult"],
            vol_floor_fraction=SEL["vol_floor_fraction"],
            target_vol=TARGET_VOL_BASE * target_vol_mult,
            min_trade_interval=min_trade_interval,
        )
        per_contract_positions[sym] = pos[sym]

    per_contract_df = pd.DataFrame(per_contract_positions, index=prices.index).fillna(
        0.0
    )

    # Cross-sectional aggregation for reporting (BASKET)
    if scale_rule == "equal":
        # Equal weight across active contracts (sign preserved, magnitude normalized)
        signs = np.sign(per_contract_df[assets])
        active = (per_contract_df[assets] != 0).any(axis=1)
        agg_pos = pd.Series(0.0, index=prices.index)
        agg_pos[active] = (signs[active] * (1.0 / len(assets)) * max_pos).sum(axis=1)
    elif scale_rule == "inverse_vol":
        # Risk-parity: weight inversely proportional to realized vol
        rets = prices[assets].pct_change().fillna(0)
        realized_vol = rets.rolling(252, min_periods=126).std() * np.sqrt(252 * 6.5)
        realized_vol = realized_vol.replace(0, np.nan).ffill().fillna(0.15)
        inv_vol = 1.0 / realized_vol
        total_inv_vol = inv_vol.sum(axis=1).replace(0, np.nan)
        weights = inv_vol.div(total_inv_vol, axis=0) * max_pos
        weights = weights.fillna(0.0)
        agg_pos = (np.sign(per_contract_df[assets]) * weights.abs()).sum(axis=1)
    else:
        raise ValueError(f"Unknown scale_rule: {scale_rule}")

    agg_pos = agg_pos.clip(-max_pos, max_pos)

    # Return per-contract positions for backtest (aligned to all 5 contracts, zeros for unused)
    full_per_contract = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    full_per_contract[assets] = per_contract_df[assets]

    agg_positions = pd.DataFrame({"BASKET": agg_pos}, index=prices.index)
    return full_per_contract, agg_positions, per_contract_df[assets]


def perturbation_eval(
    selected_config: dict,
    prices: pd.DataFrame,
    vix_hourly: pd.Series,
    base_signals: dict,
    volumes: pd.DataFrame,
    atr,
    vol_exit,
    n_assets_sel: int,
    oos_mask,
    cfg,
    opt_oos_sharpe: float,
):
    """OAT +/-20% perturbation on target_vol_mult and max_pos."""
    variants = {}
    params = ["target_vol_mult", "max_pos"]
    for param in params:
        base = selected_config[param]
        for factor in (0.8, 1.2):
            v = base * factor
            if abs(v - base) < 1e-12:
                continue
            pert_cfg = dict(selected_config)
            pert_cfg[param] = float(v)
            # evaluate this perturbed config
            per_contract_positions, _, _ = _apply_exits_and_aggregate(
                prices,
                volumes,
                vix_hourly,
                atr,
                vol_exit,
                base_signals,
                pert_cfg["target_vol_mult"],
                pert_cfg["max_pos"],
                pert_cfg["scale_rule"],
                pert_cfg["n_assets"],
                min_trade_interval=0,
            )
            res = run_backtest(
                prices=prices,
                signals=per_contract_positions,
                volumes=volumes,
                config=cfg,
            )
            oos_r = res.returns[oos_mask].dropna()
            sr = float(sharpe_ratio(oos_r.values)) if len(oos_r) > 1 else 0.0
            variants[f"{param}={v:.3f}"] = sr
    if opt_oos_sharpe > 0 and variants:
        min_ratio = float(min(variants.values()) / opt_oos_sharpe)
    else:
        min_ratio = 0.0
    return {"variants": variants, "min_perturbed_sharpe_ratio": min_ratio}


def main():
    np.random.seed(SEED)
    t_start = time.time()
    tracker = get_tracker()
    grid_size = (
        len(TARGET_VOLS) * len(MAX_POSITIONS) * len(SCALE_RULES) * len(N_ASSETS_CHOICES)
    )
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
            "grid": {
                "target_vol_mult": TARGET_VOLS,
                "max_pos": MAX_POSITIONS,
                "scale_rule": SCALE_RULES,
                "n_assets": N_ASSETS_CHOICES,
            },
            "grid_size": grid_size,
        },
        data_sources={
            "source": "yahoo_futures_cached",
            "symbols": FUTURES_UNIVERSE,
            "vix": VIX_SYMBOL,
            "interval": "1h",
        },
        compute_budget={"max_cpu_hours": 2.0, "grid_size": grid_size},
        random_seeds={"numpy": SEED, "python": SEED},
    )
    print(f"[H22] started {exp_id}  grid_size={grid_size}")

    try:
        fetcher = get_data_fetcher()
        prices, volumes, vix_hourly = _build_data(fetcher, DATA_START, DATA_END)

        train_mask, val_mask, test_mask = _splits(prices)
        oos_mask = val_mask | test_mask
        print(
            f"[H22] prices={prices.shape} train/val/test="
            f"{int(train_mask.sum())}/{int(val_mask.sum())}/{int(test_mask.sum())}"
        )

        # --- precomputed exit inputs (price-derived, config-independent) ---
        atr, vol_exit = _build_exit_inputs(prices)

        # --- build base signals per contract (H10 config) ---
        base_signals = _build_per_contract_base_signals(prices)

        cfg = make_futures_config()
        # Benchmark: vol-weighted buy-and-hold of the basket
        rets = prices.pct_change().fillna(0)
        realized_vol = rets.rolling(252, min_periods=126).std() * np.sqrt(252 * 6.5)
        realized_vol = realized_vol.replace(0, np.nan).ffill().fillna(0.15)
        inv_vol = 1.0 / realized_vol
        bench_weights = inv_vol.div(inv_vol.sum(axis=1), axis=0).fillna(0.0)
        bh_result = run_backtest(
            prices=prices, signals=bench_weights, volumes=volumes, config=cfg
        )

        # --- grid search ---
        grid_rows = []
        best_val_sharpe = -np.inf
        best_config = None
        n_eval = 0
        t_grid = time.time()

        for target_vol_mult, max_pos, scale_rule, n_assets in product(
            TARGET_VOLS, MAX_POSITIONS, SCALE_RULES, N_ASSETS_CHOICES
        ):
            per_contract_positions, _, _ = _apply_exits_and_aggregate(
                prices,
                volumes,
                vix_hourly,
                atr,
                vol_exit,
                base_signals,
                target_vol_mult,
                max_pos,
                scale_rule,
                n_assets,
                min_trade_interval=0,  # fixed per H10
            )

            res = run_backtest(
                prices=prices,
                signals=per_contract_positions,
                volumes=volumes,
                config=cfg,
            )
            val_ret = res.returns[val_mask]
            val_tr = _count_in(res.trades, val_mask, prices)
            vm = _period_metrics(val_ret, val_tr)

            row = {
                "target_vol_mult": target_vol_mult,
                "max_pos": max_pos,
                "scale_rule": scale_rule,
                "n_assets": n_assets,
                "val_sharpe": vm["sharpe"],
                "val_profit_factor": vm["profit_factor"],
                "val_max_drawdown": vm["max_drawdown"],
                "val_trades": vm["trades"],
            }
            grid_rows.append(row)
            n_eval += 1

            if n_eval % 10 == 0:
                elapsed = time.time() - t_grid
                print(
                    f"[H22] grid progress {n_eval}/{grid_size} "
                    f"({n_eval / grid_size * 100:.0f}%) {elapsed:.0f}s elapsed "
                    f"best_val_sr={best_val_sharpe:.3f}",
                    flush=True,
                )

            if vm["sharpe"] > best_val_sharpe:
                best_val_sharpe = vm["sharpe"]
                best_config = (target_vol_mult, max_pos, scale_rule, n_assets)

        grid_elapsed = time.time() - t_grid
        print(
            f"[H22] grid eval {n_eval} combos in {grid_elapsed:.1f}s ({grid_elapsed / 60:.1f} min)"
        )

        grid_df = pd.DataFrame(grid_rows)
        tracker.log_dataframe("grid_results", grid_df)

        # --- evaluate the SELECTED (best Val Sharpe) config fully ---
        target_vol_mult, max_pos, scale_rule, n_assets = best_config
        sel_per_contract, sel_agg, sel_per_contract_selected = (
            _apply_exits_and_aggregate(
                prices,
                volumes,
                vix_hourly,
                atr,
                vol_exit,
                base_signals,
                target_vol_mult,
                max_pos,
                scale_rule,
                n_assets,
                min_trade_interval=0,
            )
        )
        sel_result = run_backtest(
            prices=prices, signals=sel_per_contract, volumes=volumes, config=cfg
        )

        gate = _full_gate_eval(
            sel_result, oos_mask, val_mask, test_mask, prices, vix_hourly, bh_result
        )
        # H22: add perturbation gate (+/-20% on target_vol_mult and max_pos)
        pert = perturbation_eval(
            {
                "target_vol_mult": target_vol_mult,
                "max_pos": max_pos,
                "scale_rule": scale_rule,
                "n_assets": n_assets,
            },
            prices,
            vix_hourly,
            base_signals,
            volumes,
            atr,
            vol_exit,
            n_assets,
            oos_mask,
            cfg,
            gate["oos_metrics"]["sharpe"],
        )
        if "passes" not in gate:
            gate["passes"] = {}
        gate["passes"]["perturbation"] = (
            pert["min_perturbed_sharpe_ratio"] >= GATES["min_perturbed_sharpe_ratio"]
        )
        gate["perturbation"] = pert
        gate["all_pass"] = all(gate["passes"].values())
        gate["verdict"] = "PASS" if gate["all_pass"] else "REJECT"

        # --- ablations (OOS, Test-protected) ---
        ablations = {}
        ablation_equity = {}

        def _ablation(name, positions):
            r = run_backtest(
                prices=prices, signals=positions, volumes=volumes, config=cfg
            )
            oos_ret = r.returns[oos_mask]
            test_ret = r.returns[test_mask]
            om = _period_metrics(oos_ret, _count_in(r.trades, oos_mask, prices))
            tm = _period_metrics(test_ret, _count_in(r.trades, test_mask, prices))
            ablations[name] = {
                "oos_sharpe": om["sharpe"],
                "oos_profit_factor": om["profit_factor"],
                "oos_max_drawdown": om["max_drawdown"],
                "oos_trades": om["trades"],
                "test_sharpe": tm["sharpe"],
            }
            ablation_equity[name] = r.equity_curve

        # A1: single-contract ES only (H10 config on ES)
        es_target = build_hourly_target(
            base_signals["ES=F"],
            SEL["smooth_span"],
            SEL["vol_window_long"],
            SEL["regime_scaling"],
            vix_hourly,
            prices.index,
        )
        a1_pos = apply_exits_hourly(
            es_target,
            prices[["ES=F"]],
            atr[["ES=F"]],
            vol_exit[["ES=F"]],
            trailing_mult=SEL["trailing_mult"],
            max_hold_bars=SEL["max_hold_bars"],
            vol_limit_mult=SEL["vol_limit_mult"],
            vol_floor_fraction=SEL["vol_floor_fraction"],
            target_vol=TARGET_VOL_BASE * target_vol_mult,
            min_trade_interval=0,
        )
        # Create full per-contract DataFrame for backtest
        a1_full = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
        a1_full["ES=F"] = a1_pos["ES=F"]
        _ablation("es_only_h10", a1_full)

        # A2: random per-contract sign (shuffled)
        rng = np.random.default_rng(42)
        shuffled_positions = sel_per_contract.copy()
        for sym in shuffled_positions.columns:
            shuffled_positions[sym] = rng.permutation(shuffled_positions[sym].values)
        _ablation("random_sign_shuffled", shuffled_positions)

        # A3: constant position (long-only on all contracts equally)
        const_pos = pd.DataFrame(
            0.5 / len(prices.columns), index=prices.index, columns=prices.columns
        )
        _ablation("constant_0.5", const_pos)

        # A4: daily-frequency TSMOM per contract (H8 best: vol_scaled_tsmom on daily)
        # Fetch daily data for the same universe
        daily_data = fetcher.fetch_futures(
            FUTURES_UNIVERSE, start=DATA_START, end=DATA_END, interval="1d"
        )
        daily_prices_list = []
        for sym in FUTURES_UNIVERSE:
            df = daily_data.get(sym, pd.DataFrame())
            if len(df) == 0:
                continue
            if hasattr(df.index, "tz_convert") and df.index.tzinfo is not None:
                df.index = df.index.tz_convert(None)
            else:
                df.index = pd.to_datetime(df.index)
            daily_prices_list.append(df["close"].rename(sym))
        daily_prices = (
            pd.concat(daily_prices_list, axis=1, sort=True).sort_index().ffill().bfill()
        )
        daily_prices = daily_prices.reindex(
            prices.index.date
        ).ffill()  # align to hourly dates
        daily_prices.index = prices.index

        # Use vol_scaled_tsmom_signals from baselines (daily TSMOM)
        from qtr.strategies.baselines import vol_scaled_tsmom_signals

        daily_signal = vol_scaled_tsmom_signals(
            daily_prices,
            lookback=252,
            skip=1,
            long_only=True,
            target_vol=0.15,
            vol_window=63,
            max_position_size=2.0,
        )
        daily_signal.index = prices.index  # align
        daily_positions = daily_signal
        if n_assets == 3:
            daily_positions = daily_positions[["ES=F", "NQ=F", "CL=F"]]
        # Create full per-contract DataFrame for backtest
        daily_full = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
        for sym in daily_positions.columns:
            daily_full[sym] = daily_positions[sym]
        _ablation("daily_tsmom", daily_full)
        # A5: under-vol-targeted H21 config baseline (tv_mult=0.5)
        h21_per_contract, _, _ = _apply_exits_and_aggregate(
            prices,
            volumes,
            vix_hourly,
            atr,
            vol_exit,
            base_signals,
            0.5,
            max_pos,
            scale_rule,
            n_assets,
            min_trade_interval=0,
        )
        _ablation("h21_baseline_tv05", h21_per_contract)

        # log ablation equity curves + results
        for name, eq in ablation_equity.items():
            tracker.log_dataframe(f"ablations__{name}__equity", eq.to_frame("equity"))

        # --- log selected config artifacts ---
        tracker.log_dataframe("prices", prices)
        tracker.log_dataframe("volumes", volumes)
        tracker.log_dataframe("vix_hourly", vix_hourly.to_frame("vix"))
        tracker.log_dataframe("hourly_signal_h10", base_signals["ES=F"])
        tracker.log_dataframe(
            "daily_target_h10", _daily_target_from_hourly(base_signals["ES=F"])
        )
        tracker.log_dataframe(
            "hourly_target_selected",
            build_hourly_target(
                base_signals["ES=F"],
                SEL["smooth_span"],
                SEL["vol_window_long"],
                SEL["regime_scaling"],
                vix_hourly,
                prices.index,
            ),
        )
        tracker.log_dataframe("positions", sel_per_contract)
        tracker.log_dataframe("basket_positions", sel_agg)
        tracker.log_dataframe("per_contract_positions", sel_per_contract_selected)
        tracker.log_dataframe("equity", sel_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("returns", sel_result.returns.to_frame("returns"))
        tracker.log_dataframe("trades", sel_result.trades)
        tracker.log_dataframe(
            "benchmark_equity", bh_result.equity_curve.to_frame("equity")
        )
        tracker.log_dataframe(
            "benchmark_returns", bh_result.returns.to_frame("returns")
        )
        tracker.log_dataframe(
            "regime_factors", regime_factor_hourly(vix_hourly).to_frame("factor")
        )

        total_elapsed = time.time() - t_start
        summary = {
            "experiment_id": exp_id,
            "hypothesis": "H22",
            "selected_config": {
                "target_vol_mult": target_vol_mult,
                "max_pos": max_pos,
                "scale_rule": scale_rule,
                "n_assets": n_assets,
                "h10_base_config": SEL,
            },
            "grid_size": grid_size,
            "n_evaluated": n_eval,
            "grid_elapsed_sec": float(round(grid_elapsed, 1)),
            "total_elapsed_sec": float(round(total_elapsed, 1)),
            "compute_cpu_hours": float(round(total_elapsed / 3600, 3)),
            "metrics": {
                "train_sharpe": gate["train_sharpe"],
                "val_sharpe": gate["val_metrics"]["sharpe"]
                if "val_metrics" in gate
                else gate["val_sharpe"]
                if "val_sharpe" in gate
                else (gate["oos_metrics"]["sharpe"]),
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
                "ablations": ablations,
            },
            "passes": gate["passes"],
            "all_pass": gate["all_pass"],
            "verdict": gate["verdict"],
            "perturbation": gate.get("perturbation"),
            "selection_rule": "best Val Sharpe; Test protected (not used for selection); gates on OOS Val+Test",
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
        tracker.finish_experiment(status="completed")

        print("\n" + "=" * 72)
        p = gate["passes"]
        print(f"  gates passed: {int(sum(p.values()))}/8  ->  {summary['verdict']}")
        print(
            f"  sharpe={p['sharpe']} trades={p['trades']} pf={p['pf']} dd={p['dd']} "
            f"stab={p['stab']} worst={p['worst']} p={p['p']} ir={p['ir']}"
        )
        om = gate["oos_metrics"]
        print(
            f"  OOS Sharpe={om['sharpe']:.3f} PF={om['profit_factor']:.3f} "
            f"DD={om['max_drawdown']:.3f} Trades={om['trades']}"
        )
        print(
            f"  Test Sharpe={gate['test_metrics']['sharpe']:.3f} | "
            f"WF stab={gate['wf_stability']:.3f} | worst-regime={gate['worst_regime_sharpe']:.3f}"
        )
        print(f"  Selected: {summary['selected_config']}")
        print(
            f"  Grid {n_eval} combos in {grid_elapsed / 60:.1f} min | total {total_elapsed / 60:.1f} min "
            f"({total_elapsed / 3600:.2f} CPU-h)"
        )
        print("=" * 72)
        return 0 if gate["all_pass"] else 1
    except Exception as e:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        tracker.finish_experiment(status="failed", error=str(e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
