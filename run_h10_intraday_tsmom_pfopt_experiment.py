#!/usr/bin/env python3
"""H10: Intraday TSMOM — Profit Factor Optimization.

Extends H9 (intraday futures TSMOM with CT-style path-dependent exits) with a
turnover-aware signal / exit configuration grid, selected on Val Sharpe, and
gate-evaluated on the protected OOS (Val+Test) window using the same evidence
gates as H1-H9.

Grid (all Val-only selection; Test never enters selection):
  signal:
    - smooth_span          in {None, 4, 8, 16}   (EWMA on hourly signal, pre-collapse)
    - vol_window_long      in {252, 504, 1008}   (h; short = long//4)
    - regime_scaling       in {False, True}      (VIX-regime exposure scaling)
  exit / turnover:
    - min_trade_interval   in {0, 4, 8, 24}      (h; 0 = disabled, H9 behaviour)
    - trailing_mult        in {1.5, 2.0, 2.5, 3.0}
    - max_hold_bars        in {60, 120, 240, 480}
    - vol_limit_mult       in {1.5, 2.0, 2.5}
    - vol_floor_fraction   in {0.25, 0.5, 0.75}

Cost model, universe, splits and gates are unchanged from H9. Data is cached
(yfinance hourly ``=F`` futures + hourly ^VIX + daily ^VIX); fixed dates are
used so the run is fully reproducible offline.
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
from qtr.validation.statistics import (
    benchmark_significance_gate,
    compare_to_benchmark,
    sharpe_ratio,
    walk_forward_splits,
)

# Reuse H9 constants / primitives (single source of truth for universe, costs, gates).
from run_h9_intraday_tsmom_experiment import (
    COST_MODEL_DEFAULTS,  # noqa: F401  (re-exported for run_h11/run_h13/run_h25)
    FUTURES_SPECS,  # noqa: F401  (re-exported for downstream modules)
    FUTURES_UNIVERSE,
    GATES,
    INITIAL_CAPITAL,  # noqa: F401  (re-exported for run_h21/run_h22/run_h25 test-pinning)
    SEED,
    VIX_SYMBOL,
    _daily_target_from_hourly,
    make_futures_config,
    regime_labels,
    vol_scaled_tsmom_hourly,
)

EXPERIMENT_NAME = "h10_intraday_tsmom_pfopt"
EXPERIMENT_DESC = (
    "H10: Intraday TSMOM turnover-aware signal + exit grid for profit-factor "
    "optimization; 13824-combo grid (smooth_span x vol_window_long x "
    "regime_scaling x min_trade_interval x trailing_mult x max_hold_bars x "
    "vol_limit_mult x vol_floor_fraction), Val-selected, Test-protected, "
    "same gates as H9"
)

TARGET_VOL = 0.15
VOL_WINDOW_SHORT_RATIO = 4  # H9 used 252 long / 63 short (4:1)

# Fixed dates matching the cached hourly futures + VIX so the run is offline.
DATA_START = "2024-10-12"
DATA_END = "2026-10-11"

# Grids (per NEXT_TASK / H10 pre-registration).
SMOOTH_SPANS = [None, 4, 8, 16]
VOL_WINDOWS_LONG = [252, 504, 1008]
REGIME_SCALING_FLAGS = [False, True]
MIN_TRADE_INTERVALS = [0, 4, 8, 24]
TRAILING_MULTS = [1.5, 2.0, 2.5, 3.0]
MAX_HOLD_BARS = [60, 120, 240, 480]
VOL_LIMIT_MULTS = [1.5, 2.0, 2.5]
VOL_FLOOR_FRACTIONS = [0.25, 0.5, 0.75]

# Exit-internal fixed parameters (not in the grid; identical to H9).
EXIT_VOL_WINDOW = 20
EXIT_VOL_FLOOR_DEFAULT = 0.5
EXIT_TRAILING_DEFAULT = 2.0
EXIT_MAX_HOLD_DEFAULT = 120
EXIT_VOL_LIMIT_DEFAULT = 2.0


def smooth_signal(hourly_signal: pd.DataFrame, span) -> pd.DataFrame:
    """EWMA smooth the hourly signal (causal, adjust=False)."""
    if span is None or span <= 1:
        return hourly_signal.copy()
    return hourly_signal.ewm(span=int(span), adjust=False).mean()


def regime_factor_hourly(vix_hourly: pd.Series) -> pd.Series:
    """Per-hour VIX-regime exposure factor (H6 style): bull 1.0, sideways 0.5,
    bear 0.25."""
    f = pd.Series(1.0, index=vix_hourly.index)
    vix_ff = vix_hourly.ffill()
    f[vix_ff >= 20] = 0.5
    f[vix_ff > 30] = 0.25
    return f


def build_hourly_target(
    hourly_signal: pd.DataFrame,
    smooth_span,
    vol_window_long: int,
    regime_scaling: bool,
    vix_hourly: pd.Series,
    prices_index: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Collapse an (optionally smoothed) hourly signal to an hourly target.

    Steps (per NEXT_TASK):
      1. EWMA-smooth the hourly signal (span may be None).
      2. Daily target collapse (last bar of day, ffilled).
      3. Expand back to the hourly grid.
      4. Optionally multiply by the per-hour VIX-regime exposure factor.
    """
    sig = smooth_signal(hourly_signal, smooth_span)
    daily_target = _daily_target_from_hourly(sig)
    hourly_target = daily_target.reindex(prices_index, method="ffill").fillna(0.0)
    if regime_scaling:
        factor = regime_factor_hourly(vix_hourly)
        hourly_target = hourly_target.multiply(factor, axis=0)
    return hourly_target


def apply_exits_hourly(
    hourly_target: pd.DataFrame,
    prices: pd.DataFrame,
    atr: pd.DataFrame,
    vol: pd.DataFrame,
    trailing_mult: float = EXIT_TRAILING_DEFAULT,
    max_hold_bars: int = EXIT_MAX_HOLD_DEFAULT,
    vol_limit_mult: float = EXIT_VOL_LIMIT_DEFAULT,
    vol_floor_fraction: float = EXIT_VOL_FLOOR_DEFAULT,
    target_vol: float = TARGET_VOL,
    min_trade_interval: int = 0,
) -> pd.DataFrame:
    """CT-style path-dependent exits on the hourly grid (H9 logic + min-trade
    interval).

    A ``min_trade_interval`` of 0 reproduces H9 exactly. >0 suppresses any
    position change (entry, exit, or vol-stop reduction) whose bar index is
    fewer than that many bars since the last actual trade on that symbol.
    """
    index = prices.index
    cols = prices.columns
    positions = pd.DataFrame(0.0, index=index, columns=cols, dtype=float)

    tgt = hourly_target.reindex(index, method="ffill").fillna(0.0)

    for sym in cols:
        px = prices[sym].to_numpy(dtype=float)
        tr = tgt[sym].to_numpy(dtype=float)
        v = vol[sym].to_numpy(dtype=float)
        atr_s = atr[sym].to_numpy(dtype=float)

        pos = np.zeros(len(index), dtype=float)
        in_pos = False
        entry_price = 0.0
        high_water = 0.0
        bars_held = 0
        cur_pos = 0.0
        last_trade_bar = -(10**9)  # far in the past

        for i in range(len(index)):
            cur_px = px[i]
            cur_tgt = tr[i]
            cur_vol = v[i] if not np.isnan(v[i]) else target_vol
            atr_i = atr_s[i]
            if np.isnan(atr_i):
                atr_i = cur_px * 0.001
            can_trade = (i - last_trade_bar) >= min_trade_interval

            # --- in-position exit checks (H9 semantics, gated by min interval) ---
            if in_pos and cur_pos > 0:
                high_water = max(high_water, cur_px)
                if (
                    can_trade
                    and cur_px < high_water - trailing_mult * atr_i
                    or can_trade
                    and bars_held >= max_hold_bars
                    and cur_px <= entry_price
                ):
                    cur_pos = 0.0
                    in_pos = False
                    last_trade_bar = i
                elif can_trade and cur_vol > vol_limit_mult * target_vol:
                    cur_pos = cur_pos * vol_floor_fraction
                    if cur_pos <= 1e-9:
                        cur_pos = 0.0
                        in_pos = False
                    last_trade_bar = i

            # --- entry / target-flip ---
            if (not in_pos) and cur_tgt > 0:
                if can_trade:
                    entry_price = cur_px
                    high_water = cur_px
                    bars_held = 0
                    cur_pos = float(cur_tgt)
                    in_pos = True
                    last_trade_bar = i
                # else: gated by min interval -> stay flat
            elif in_pos and cur_tgt <= 0 and can_trade:
                cur_pos = 0.0
                in_pos = False
                last_trade_bar = i

            if in_pos:
                bars_held += 1

            pos[i] = cur_pos

        positions[sym] = pos

    return positions.ffill().fillna(0.0)


def _splits(prices: pd.DataFrame):
    n = len(prices)
    train_end = prices.index[int(n * 0.55)]
    val_end = prices.index[int(n * 0.8)]
    train_mask = prices.index <= train_end
    val_mask = (prices.index > train_end) & (prices.index <= val_end)
    test_mask = prices.index > val_end
    return train_mask, val_mask, test_mask


def _period_metrics(ret: pd.Series, n_trades: int) -> dict:
    """Val/Test-style metrics: Sharpe, DD, PF, trades, IR-vs-B&H handled by caller."""
    r = ret.dropna()
    if len(r) > 1:
        sr = float(sharpe_ratio(r.values))
    else:
        sr = 0.0
    cum = (1 + r).cumprod()
    dd = float((cum / cum.cummax() - 1.0).min()) if len(cum) > 0 else 0.0
    gp = float(r[r > 0].sum())
    gl = float(abs(r[r < 0].sum()))
    pf = gp / gl if gl > 0 else float("inf")
    return {
        "sharpe": sr,
        "max_drawdown": dd,
        "profit_factor": pf,
        "trades": int(n_trades),
        "gross_profit": gp,
        "gross_loss": gl,
        "n_periods": len(r),
    }


def _count_in(trades: pd.DataFrame, mask, prices) -> int:
    if len(trades) == 0:
        return 0
    ts = pd.to_datetime(trades["timestamp"])
    lo = prices.index[mask].min()
    hi = prices.index[mask].max()
    return int(((ts >= lo) & (ts <= hi)).sum())


def _full_gate_eval(result, oos_mask, val_mask, test_mask, prices, vix_hourly, bh_result):
    """Compute the 8 H9-family gates on OOS (Val+Test) plus a Test-only sanity
    check."""
    train_mask = prices.index <= prices.index[int(len(prices) * 0.55)]

    oos_ret = result.returns[oos_mask]
    val_ret = result.returns[val_mask]
    test_ret = result.returns[test_mask]
    oos_m = _period_metrics(oos_ret, _count_in(result.trades, oos_mask, prices))
    val_m = _period_metrics(val_ret, _count_in(result.trades, val_mask, prices))
    test_m = _period_metrics(test_ret, _count_in(result.trades, test_mask, prices))

    # Walk-forward stability (5 folds over full series, like H9)
    wf_splits = walk_forward_splits(len(result.returns), n_splits=5)
    oos_sharpes, train_sharpes = [], []
    for tr_idx, te_idx in wf_splits:
        tr_r = result.returns.iloc[tr_idx].values
        te_r = result.returns.iloc[te_idx].values
        if len(te_r) > 1:
            oos_sharpes.append(sharpe_ratio(te_r))
        if len(tr_r) > 1:
            train_sharpes.append(sharpe_ratio(tr_r))
    wf_stab = (
        float(np.mean(oos_sharpes) / np.mean(train_sharpes)) if np.mean(train_sharpes) != 0 else 0.0
    )

    # Regime sharpes (worst) using hourly VIX ffill
    regimes = regime_labels(vix_hourly)
    regime_sharpes = {}
    worst = np.inf
    for reg in ["bull", "sideways", "bear"]:
        m = regimes == reg
        r = result.returns[m]
        if len(r) > 1 and r.std() > 0:
            s = float(sharpe_ratio(r.values))
        else:
            s = 0.0
        regime_sharpes[reg] = s
        worst = min(worst, s)

    bench = compare_to_benchmark(result.returns, bh_result.returns)
    oos_max_dd = oos_m["max_drawdown"]

    passes = {
        "sharpe": oos_m["sharpe"] >= GATES["min_sharpe"],
        "trades": oos_m["trades"] >= GATES["min_trades"],
        "pf": oos_m["profit_factor"] >= GATES["min_profit_factor"],
        "dd": abs(oos_max_dd) <= GATES["max_drawdown"] if oos_max_dd < 0 else False,
        "stab": wf_stab >= GATES["min_walkforward_stability"],
        "worst": worst >= GATES["min_worst_regime_sharpe"] if worst != np.inf else False,
        "p": benchmark_significance_gate(
            float(bench.get("alpha_p_value", 1.0)),
            float(bench.get("information_ratio", -np.inf)),
            GATES["max_p_value"],
        ),
        "ir": float(bench.get("information_ratio", -np.inf)) > GATES["min_information_ratio"],
    }
    all_pass = all(passes.values())
    return {
        "oos_metrics": {**oos_m, "sharpe": oos_m["sharpe"]},
        "test_metrics": test_m,
        "val_metrics": val_m,
        "train_sharpe": float(sharpe_ratio(result.returns[train_mask].values))
        if train_mask.sum() > 1
        else 0.0,
        "val_sharpe": val_m["sharpe"],
        "wf_stability": float(wf_stab),
        "worst_regime_sharpe": float(worst) if worst != np.inf else 0.0,
        "regime_sharpes": regime_sharpes,
        "benchmark_p_value": float(bench.get("alpha_p_value", 1.0)),
        "information_ratio": float(bench.get("information_ratio", -np.inf)),
        "passes": passes,
        "all_pass": all_pass,
        "verdict": "PASS" if all_pass else "REJECT",
    }


def main():
    np.random.seed(SEED)
    t_start = time.time()
    tracker = get_tracker()
    grid_size = (
        len(SMOOTH_SPANS)
        * len(VOL_WINDOWS_LONG)
        * len(REGIME_SCALING_FLAGS)
        * len(MIN_TRADE_INTERVALS)
        * len(TRAILING_MULTS)
        * len(MAX_HOLD_BARS)
        * len(VOL_LIMIT_MULTS)
        * len(VOL_FLOOR_FRACTIONS)
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
            "grid": {
                "smooth_span": SMOOTH_SPANS,
                "vol_window_long": VOL_WINDOWS_LONG,
                "regime_scaling": REGIME_SCALING_FLAGS,
                "min_trade_interval": MIN_TRADE_INTERVALS,
                "trailing_mult": TRAILING_MULTS,
                "max_hold_bars": MAX_HOLD_BARS,
                "vol_limit_mult": VOL_LIMIT_MULTS,
                "vol_floor_fraction": VOL_FLOOR_FRACTIONS,
            },
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
    print(f"[H10] started {exp_id}  grid_size={grid_size}")

    try:
        fetcher = get_data_fetcher()
        # --- data (cached) ---
        data = fetcher.fetch_futures(
            FUTURES_UNIVERSE, start=DATA_START, end=DATA_END, interval="1h"
        )
        prices_list, volumes_list = [], []
        for sym in FUTURES_UNIVERSE:
            df = data.get(sym, pd.DataFrame())
            if len(df) == 0:
                continue
            # yfinance futures return tz-aware (America/New_York) hourly indexes;
            # normalize to tz-naive UTC so they align with the tz-naive VIX index.
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

        # Hourly VIX (cached). yfinance ^VIX hourly comes back tz-naive; keep it
        # tz-naive so the reindex against the (now tz-naive) prices index works.
        vix_df = fetcher.fetch_yahoo([VIX_SYMBOL], start=DATA_START, end=DATA_END, interval="1h")
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
            f"[H10] prices={prices.shape} train/val/test="
            f"{int(train_mask.sum())}/{int(val_mask.sum())}/{int(test_mask.sum())}"
        )

        # --- precomputed exit inputs (price-derived, config-independent) ---
        pct = prices.pct_change().fillna(0)
        atr = prices * pct.rolling(14, min_periods=7).std()
        atr = atr.replace(0, np.nan).ffill().fillna(prices * 0.001)
        vol_exit = pct.rolling(EXIT_VOL_WINDOW, min_periods=EXIT_VOL_WINDOW // 2).std() * np.sqrt(
            252 * 6.5
        )
        vol_exit = vol_exit.replace(0, np.nan).ffill()

        cfg = make_futures_config()
        bh_weights = pd.DataFrame(
            1.0 / len(prices.columns), index=prices.index, columns=prices.columns
        )
        bh_result = run_backtest(prices=prices, signals=bh_weights, volumes=volumes, config=cfg)

        # --- build the 3 base signals (one per vol window) once ---
        base_signals = {}
        for vw in VOL_WINDOWS_LONG:
            base_signals[vw] = vol_scaled_tsmom_hourly(
                prices,
                vol_window_long=vw,
                vol_window_short=vw // VOL_WINDOW_SHORT_RATIO,
            )

        # --- build the signal-variant hourly targets (cached) ---
        targets = {}  # key -> hourly_target DataFrame
        for vw in VOL_WINDOWS_LONG:
            for smooth_span in SMOOTH_SPANS:
                for regime in REGIME_SCALING_FLAGS:
                    targets[(vw, smooth_span, regime)] = build_hourly_target(
                        base_signals[vw],
                        smooth_span,
                        vw,
                        regime,
                        vix_hourly,
                        prices.index,
                    )
        print(f"[H10] built {len(targets)} signal variants")

        # --- grid search ---
        grid_rows = []
        best_val_sharpe = -np.inf
        best_by_sharpe = None  # (target_key, min_int, exit_params)
        best_val_pf = -np.inf
        best_by_pf = None
        n_eval = 0
        t_grid = time.time()
        for (vw, smooth_span, regime), hourly_target in targets.items():
            for min_int in MIN_TRADE_INTERVALS:
                for tm, mhb, vlm, vff in product(
                    TRAILING_MULTS, MAX_HOLD_BARS, VOL_LIMIT_MULTS, VOL_FLOOR_FRACTIONS
                ):
                    positions = apply_exits_hourly(
                        hourly_target,
                        prices,
                        atr,
                        vol_exit,
                        trailing_mult=tm,
                        max_hold_bars=mhb,
                        vol_limit_mult=vlm,
                        vol_floor_fraction=vff,
                        target_vol=TARGET_VOL,
                        min_trade_interval=min_int,
                    )
                    res = run_backtest(
                        prices=prices, signals=positions, volumes=volumes, config=cfg
                    )
                    val_ret = res.returns[val_mask]
                    val_tr = _count_in(res.trades, val_mask, prices)
                    vm = _period_metrics(val_ret, val_tr)
                    row = {
                        "vol_window_long": vw,
                        "smooth_span": (str(smooth_span) if smooth_span is not None else "none"),
                        "regime_scaling": regime,
                        "min_trade_interval": min_int,
                        "trailing_mult": tm,
                        "max_hold_bars": mhb,
                        "vol_limit_mult": vlm,
                        "vol_floor_fraction": vff,
                        "val_sharpe": vm["sharpe"],
                        "val_profit_factor": vm["profit_factor"],
                        "val_max_drawdown": vm["max_drawdown"],
                        "val_trades": vm["trades"],
                    }
                    grid_rows.append(row)
                    n_eval += 1
                    if n_eval % 1000 == 0:
                        elapsed = time.time() - t_grid
                        rate = elapsed / n_eval
                        print(
                            f"[H10] grid progress {n_eval}/{grid_size} "
                            f"({n_eval / grid_size * 100:.0f}%) {elapsed:.0f}s elapsed "
                            f"~{rate * n_eval / 60:.1f}min so far, "
                            f"best_val_sr={best_val_sharpe:.3f} best_val_pf={best_val_pf:.3f}",
                            flush=True,
                        )
                    if vm["sharpe"] > best_val_sharpe:
                        best_val_sharpe = vm["sharpe"]
                        best_by_sharpe = (
                            (vw, smooth_span, regime),
                            min_int,
                            {
                                "trailing_mult": tm,
                                "max_hold_bars": mhb,
                                "vol_limit_mult": vlm,
                                "vol_floor_fraction": vff,
                            },
                        )
                    if vm["profit_factor"] > best_val_pf and vm["profit_factor"] != float("inf"):
                        best_val_pf = vm["profit_factor"]
                        best_by_pf = (
                            (vw, smooth_span, regime),
                            min_int,
                            {
                                "trailing_mult": tm,
                                "max_hold_bars": mhb,
                                "vol_limit_mult": vlm,
                                "vol_floor_fraction": vff,
                            },
                        )
        grid_elapsed = time.time() - t_grid
        print(
            f"[H10] grid eval {n_eval} combos in {grid_elapsed:.1f}s ({grid_elapsed / 60:.1f} min)"
        )

        grid_df = pd.DataFrame(grid_rows)
        tracker.log_dataframe("grid_results", grid_df)

        # --- evaluate the SELECTED (best Val Sharpe) config fully ---
        tk, min_int, exit_params = best_by_sharpe
        hourly_target = targets[tk]
        sel_positions = apply_exits_hourly(
            hourly_target,
            prices,
            atr,
            vol_exit,
            trailing_mult=exit_params["trailing_mult"],
            max_hold_bars=exit_params["max_hold_bars"],
            vol_limit_mult=exit_params["vol_limit_mult"],
            vol_floor_fraction=exit_params["vol_floor_fraction"],
            target_vol=TARGET_VOL,
            min_trade_interval=min_int,
        )
        sel_result = run_backtest(prices=prices, signals=sel_positions, volumes=volumes, config=cfg)

        gate = _full_gate_eval(
            sel_result, oos_mask, val_mask, test_mask, prices, vix_hourly, bh_result
        )

        # --- ablations (OOS, Test-protected) ---
        ablations = {}
        ablation_equity = {}

        def _ablation(name, positions):
            r = run_backtest(prices=prices, signals=positions, volumes=volumes, config=cfg)
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

        # A1: H9 baseline (vol 252, smooth none, no regime, min_int 0, H9 exits)
        h9_target = targets[(252, None, False)]
        a1_pos = apply_exits_hourly(
            h9_target,
            prices,
            atr,
            vol_exit,
            trailing_mult=EXIT_TRAILING_DEFAULT,
            max_hold_bars=EXIT_MAX_HOLD_DEFAULT,
            vol_limit_mult=EXIT_VOL_LIMIT_DEFAULT,
            vol_floor_fraction=EXIT_VOL_FLOOR_DEFAULT,
            target_vol=TARGET_VOL,
            min_trade_interval=0,
        )
        _ablation("h9_baseline", a1_pos)

        # A2: best signal-smoothing only (best smooth_span across vol=252, no regime,
        #     default exits, min_int 0)
        smooth_pfs = []
        for sp in SMOOTH_SPANS:
            ht = targets[(252, sp, False)]
            pos = apply_exits_hourly(
                ht,
                prices,
                atr,
                vol_exit,
                trailing_mult=EXIT_TRAILING_DEFAULT,
                max_hold_bars=EXIT_MAX_HOLD_DEFAULT,
                vol_limit_mult=EXIT_VOL_LIMIT_DEFAULT,
                vol_floor_fraction=EXIT_VOL_FLOOR_DEFAULT,
                target_vol=TARGET_VOL,
                min_trade_interval=0,
            )
            r = run_backtest(prices=prices, signals=pos, volumes=volumes, config=cfg)
            smooth_pfs.append(
                (
                    sp,
                    _count_in(r.trades, oos_mask, prices),
                    _period_metrics(r.returns[oos_mask], _count_in(r.trades, oos_mask, prices)),
                )
            )
        best_sp = max(smooth_pfs, key=lambda x: x[2]["profit_factor"])[0]
        a2_pos = targets[(252, best_sp, False)]
        a2_pos = apply_exits_hourly(
            a2_pos,
            prices,
            atr,
            vol_exit,
            trailing_mult=EXIT_TRAILING_DEFAULT,
            max_hold_bars=EXIT_MAX_HOLD_DEFAULT,
            vol_limit_mult=EXIT_VOL_LIMIT_DEFAULT,
            vol_floor_fraction=EXIT_VOL_FLOOR_DEFAULT,
            target_vol=TARGET_VOL,
            min_trade_interval=0,
        )
        _ablation(f"signal_smoothing_only(span={best_sp})", a2_pos)

        # A3: longer vol window only (best vw, smooth none, no regime, default exits)
        vw_pfs = []
        for vw in VOL_WINDOWS_LONG:
            ht = targets[(vw, None, False)]
            pos = apply_exits_hourly(
                ht,
                prices,
                atr,
                vol_exit,
                trailing_mult=EXIT_TRAILING_DEFAULT,
                max_hold_bars=EXIT_MAX_HOLD_DEFAULT,
                vol_limit_mult=EXIT_VOL_LIMIT_DEFAULT,
                vol_floor_fraction=EXIT_VOL_FLOOR_DEFAULT,
                target_vol=TARGET_VOL,
                min_trade_interval=0,
            )
            r = run_backtest(prices=prices, signals=pos, volumes=volumes, config=cfg)
            vw_pfs.append(
                (
                    vw,
                    _period_metrics(r.returns[oos_mask], _count_in(r.trades, oos_mask, prices)),
                )
            )
        best_vw = max(vw_pfs, key=lambda x: x[1]["profit_factor"])[0]
        a3_pos = apply_exits_hourly(
            targets[(best_vw, None, False)],
            prices,
            atr,
            vol_exit,
            trailing_mult=EXIT_TRAILING_DEFAULT,
            max_hold_bars=EXIT_MAX_HOLD_DEFAULT,
            vol_limit_mult=EXIT_VOL_LIMIT_DEFAULT,
            vol_floor_fraction=EXIT_VOL_FLOOR_DEFAULT,
            target_vol=TARGET_VOL,
            min_trade_interval=0,
        )
        _ablation(f"longer_vol_window_only(vw={best_vw})", a3_pos)

        # A4: regime scaling only (vol 252, smooth none, regime on, default exits)
        a4_pos = apply_exits_hourly(
            targets[(252, None, True)],
            prices,
            atr,
            vol_exit,
            trailing_mult=EXIT_TRAILING_DEFAULT,
            max_hold_bars=EXIT_MAX_HOLD_DEFAULT,
            vol_limit_mult=EXIT_VOL_LIMIT_DEFAULT,
            vol_floor_fraction=EXIT_VOL_FLOOR_DEFAULT,
            target_vol=TARGET_VOL,
            min_trade_interval=0,
        )
        _ablation("regime_scaling_only", a4_pos)

        # A5: min trade interval only (vol 252, smooth none, no regime, default exits)
        mi_pfs = []
        for mi in MIN_TRADE_INTERVALS:
            pos = apply_exits_hourly(
                targets[(252, None, False)],
                prices,
                atr,
                vol_exit,
                trailing_mult=EXIT_TRAILING_DEFAULT,
                max_hold_bars=EXIT_MAX_HOLD_DEFAULT,
                vol_limit_mult=EXIT_VOL_LIMIT_DEFAULT,
                vol_floor_fraction=EXIT_VOL_FLOOR_DEFAULT,
                target_vol=TARGET_VOL,
                min_trade_interval=mi,
            )
            r = run_backtest(prices=prices, signals=pos, volumes=volumes, config=cfg)
            mi_pfs.append(
                (
                    mi,
                    _period_metrics(r.returns[oos_mask], _count_in(r.trades, oos_mask, prices)),
                )
            )
        best_mi = max(mi_pfs, key=lambda x: x[1]["profit_factor"])[0]
        a5_pos = apply_exits_hourly(
            targets[(252, None, False)],
            prices,
            atr,
            vol_exit,
            trailing_mult=EXIT_TRAILING_DEFAULT,
            max_hold_bars=EXIT_MAX_HOLD_DEFAULT,
            vol_limit_mult=EXIT_VOL_LIMIT_DEFAULT,
            vol_floor_fraction=EXIT_VOL_FLOOR_DEFAULT,
            target_vol=TARGET_VOL,
            min_trade_interval=best_mi,
        )
        _ablation(f"min_trade_interval_only(mi={best_mi})", a5_pos)

        # A6: exit grid best (selected config already = exit grid best under best signal)
        #     Report the same selected config but isolate exit contribution:
        a6_pos = sel_positions
        _ablation("exit_grid_best", a6_pos)

        # log ablation equity curves + results
        for name, eq in ablation_equity.items():
            tracker.log_dataframe(f"ablations__{name}__equity", eq.to_frame("equity"))

        # --- log selected config artifacts ---
        tracker.log_dataframe("prices", prices)
        tracker.log_dataframe("volumes", volumes)
        tracker.log_dataframe("vix_hourly", vix_hourly.to_frame("vix"))
        if (252, None, False) in targets:
            tracker.log_dataframe("hourly_signal_h9", base_signals[252])
            tracker.log_dataframe("daily_target_h9", _daily_target_from_hourly(base_signals[252]))
        tracker.log_dataframe("hourly_target_selected", hourly_target)
        tracker.log_dataframe("positions", sel_positions)
        tracker.log_dataframe("equity", sel_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("returns", sel_result.returns.to_frame("returns"))
        tracker.log_dataframe("trades", sel_result.trades)
        tracker.log_dataframe("benchmark_equity", bh_result.equity_curve.to_frame("equity"))

        # exit events (CT-style) for selected config
        prev_pos = sel_positions.shift(1).fillna(0.0)
        flat = (prev_pos > 0) & (sel_positions <= 0)
        reduced = (prev_pos > 0) & (sel_positions > 0) & (sel_positions < prev_pos)
        exit_rows = []
        for sym in prices.columns:
            for idx in sel_positions.index[flat[sym]]:
                exit_rows.append(
                    {
                        "timestamp": idx,
                        "symbol": sym,
                        "type": "flatten",
                        "prev_position": float(prev_pos.loc[idx, sym]),
                        "new_position": 0.0,
                        "price": float(prices.loc[idx, sym]),
                    }
                )
            for idx in sel_positions.index[reduced[sym]]:
                exit_rows.append(
                    {
                        "timestamp": idx,
                        "symbol": sym,
                        "type": "reduce",
                        "prev_position": float(prev_pos.loc[idx, sym]),
                        "new_position": float(sel_positions.loc[idx, sym]),
                        "price": float(prices.loc[idx, sym]),
                    }
                )
        exit_events = pd.DataFrame(
            exit_rows,
            columns=[
                "timestamp",
                "symbol",
                "type",
                "prev_position",
                "new_position",
                "price",
            ],
        ).sort_values("timestamp")
        tracker.log_dataframe("exit_events", exit_events)
        tracker.log_dataframe("regime_factors", regime_factor_hourly(vix_hourly).to_frame("factor"))

        # param grid: also log best by Val PF for transparency
        best_pf_info = {}
        if best_by_pf is not None:
            tk2, mi2, ep2 = best_by_pf
            bp_pos = apply_exits_hourly(
                targets[tk2],
                prices,
                atr,
                vol_exit,
                trailing_mult=ep2["trailing_mult"],
                max_hold_bars=ep2["max_hold_bars"],
                vol_limit_mult=ep2["vol_limit_mult"],
                vol_floor_fraction=ep2["vol_floor_fraction"],
                target_vol=TARGET_VOL,
                min_trade_interval=mi2,
            )
            bp_res = run_backtest(prices=prices, signals=bp_pos, volumes=volumes, config=cfg)
            bp_gate = _full_gate_eval(
                bp_res, oos_mask, val_mask, test_mask, prices, vix_hourly, bh_result
            )
            best_pf_info = {
                "config": {
                    "vol_window_long": tk2[0],
                    "smooth_span": str(tk2[1]),
                    "regime_scaling": tk2[2],
                    "min_trade_interval": mi2,
                    **ep2,
                },
                "val_pf": best_val_pf,
                "oos_metrics": bp_gate["oos_metrics"],
                "test_metrics": bp_gate["test_metrics"],
                "gates": bp_gate["passes"],
                "verdict": bp_gate["verdict"],
            }

        total_elapsed = time.time() - t_start
        summary = {
            "experiment_id": exp_id,
            "hypothesis": "H10",
            "selected_config": {
                "vol_window_long": tk[0],
                "smooth_span": (str(tk[1]) if tk[1] is not None else "none"),
                "regime_scaling": tk[2],
                "min_trade_interval": min_int,
                **exit_params,
            },
            "grid_size": grid_size,
            "n_evaluated": n_eval,
            "grid_elapsed_sec": float(round(grid_elapsed, 1)),
            "total_elapsed_sec": float(round(total_elapsed, 1)),
            "compute_cpu_hours": float(round(total_elapsed / 3600, 3)),
            "metrics": {
                "train_sharpe": gate["train_sharpe"],
                "val_sharpe": None,  # not primary; OOS used
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
            "best_val_pf_config": best_pf_info,
            "passes": gate["passes"],
            "all_pass": gate["all_pass"],
            "verdict": gate["verdict"],
            "selection_rule": "best Val Sharpe; Test protected (not used for selection); gates on OOS Val+Test",
        }

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
        p = gate["passes"]
        print(f"  gates passed: {int(sum(p.values()))}/8  ->  {summary['verdict']}")
        p = gate["passes"]
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
        print(f"  Best Val-PF config OOS: PF={best_val_pf:.3f}")
        print(
            f"  Grid {n_eval} combos in {grid_elapsed / 60:.1f} min | total {total_elapsed / 60:.1f} min "
            f"({total_elapsed / 3600:.2f} CPU-h)"
        )
        print("=" * 72)
        return 0 if gate["all_pass"] else 1
    except Exception as e:  # noqa: BLE001 -- top-level experiment harness: any failure must finish the tracker and return a verdict
        import traceback

        traceback.print_exc()
        tracker.finish_experiment(status="failed", error=str(e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
