#!/usr/bin/env python3
"""H8: Roll-Adjusted Futures TSMOM — capturing roll-yield from futures rolls.

Pre-registered design (per NEXT_TASK.md):
- Universe: ES=F, NQ=F, CL=F, GC=F, ZB=F (Yahoo continuous =F front-month).
- Splits: Train 2015-2019, Val 2020-2021, Test 2022-2024 (protected). Test
  never enters selection.
- Roll detection: calendar-based last-business-day of roll months (ES/NQ/ZB
  quarterly Mar/Jun/Sep/Dec; CL/GC monthly) validated by volume spikes near
  month-end (> 3x 42-day median) and by overnight price gaps. Open interest
  is not available from free sources; volume shifts are the substitute.
- Roll carry: on each detected roll date, roll_carry = open / prev_close - 1
  (the overnight gap that captures the old-front-month -> new-front-month
  transition). This is the empirical proxy for
  (next_front_price - front_price) / front_price requested in NEXT_TASK.md.
- Roll-adjusted returns: R'_t = R_t + w * roll_carry_t on roll dates,
  R'_t = R_t otherwise. Grid over w in {0.0, 0.25, 0.5, 1.0, 2.0}; weight
  0.0 is the base (no roll adjustment). Selection by Val-only Sharpe.
- Roll-adjusted prices: P'_t = P_0 * cumprod(1 + R'_t) per symbol.
- Signal: vol-scaled TSMOM on P' via baselines.vol_scaled_tsmom_signals
  (long_only=True, lookback=252, skip=1, target_vol=0.15, vol_window=63,
  max_position_size=2.0) — the corrected H4 best combo. Monthly rebalance.
- Cost model: futures per-contract ($0.50 + 0.25 tick spread + 0.5 tick
  slippage) via BacktestConfig with futures_specs.
- Gates (unchanged PROMPT_V2): Sharpe >= 1.0, >= 200 trades, PF >= 1.3,
  DD <= 15%, WF stability >= 0.7, worst-regime Sharpe >= 0.3, benchmark
  p < 0.05 and IR > 0.
- Null: Roll-adjusted TSMOM OOS Sharpe <= 1.0 OR max DD > 15%.
- Compute budget: <= 2 CPU-h. Seed 42.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import json
from pathlib import Path

import numpy as np
import pandas as pd

from qtr.backtest.engine import AssetClass, BacktestConfig, CostModel, run_backtest
from qtr.data.fetcher import get_data_fetcher
from qtr.strategies.baselines import vol_scaled_tsmom_signals
from qtr.tracking.experiment import get_tracker
from qtr.validation.statistics import (
    compare_to_benchmark,
    sharpe_ratio,
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

# Roll-carry weight grid (0.0 = base, no adjustment)
ROLL_CARRY_WEIGHT_GRID = [0.0, 0.25, 0.5, 1.0, 2.0]

# Roll detection parameters
ROLL_VOLUME_MULTIPLIER = 3.0
ROLL_VOLUME_WINDOW = 42
ROLL_GAP_THRESHOLD = 0.005  # 0.5% overnight gap
ROLL_MAX_RETURN_CLIP = 0.50  # clip extreme daily returns (CL 2020 crash)

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
    "ES=F": {"multiplier": 50.0, "tick_value": 12.50, "tick_size": 0.25,
             "commission": 0.50, "spread_ticks": 0.25, "slippage_ticks": 0.5},
    "NQ=F": {"multiplier": 20.0, "tick_value": 5.0, "tick_size": 0.25,
             "commission": 0.50, "spread_ticks": 0.25, "slippage_ticks": 0.5},
    "CL=F": {"multiplier": 1000.0, "tick_value": 10.0, "tick_size": 0.01,
             "commission": 0.50, "spread_ticks": 0.25, "slippage_ticks": 0.5},
    "GC=F": {"multiplier": 100.0, "tick_value": 10.0, "tick_size": 0.10,
             "commission": 0.50, "spread_ticks": 0.25, "slippage_ticks": 0.5},
    "ZB=F": {"multiplier": 1000.0, "tick_value": 31.25, "tick_size": 0.03125,
             "commission": 0.50, "spread_ticks": 0.25, "slippage_ticks": 0.5},
}

# Futures roll schedules: which months roll for each symbol
# ES, NQ, ZB list quarterly (Mar/Jun/Sep/Dec); CL, GC list monthly (all 12)
ROLL_MONTHS = {
    "ES=F": [3, 6, 9, 12],
    "NQ=F": [3, 6, 9, 12],
    "CL=F": list(range(1, 13)),
    "GC=F": list(range(1, 13)),
    "ZB=F": [3, 6, 9, 12],
}

EXPERIMENT_NAME = "h8_roll_adjusted_futures_tsmom_v1"
EXPERIMENT_DESC = (
    "H8: Roll-Adjusted Futures TSMOM. Detects futures roll dates via calendar "
    "(last BD of roll months for ES/NQ/ZB quarterly, CL/GC monthly) validated by "
    "volume spikes and overnight gaps. Computes roll carry = open/prev_close - 1 "
    "on roll dates. Builds roll-adjusted returns R' = R + w*roll_carry. Grid over "
    "w in {0.0, 0.25, 0.5, 1.0, 2.0}; selection by Val-only Sharpe. Base signal: "
    "vol_scaled_tsmom_signals (long_only, lookback=252, skip=1). Gates on pooled "
    "Val+Test OOS per PROMPT_V2. Includes base TSMOM ablation."
)


# ============================================================
# Roll detection
# ============================================================
def detect_roll_dates_symbol(symbol, close, open_, volume):
    """Detect roll dates for a single futures continuous contract.

    Method (hybrid, per NEXT_TASK.md "volume/OI shifts or naive
    month-end/expiry-aware heuristics"):

    1. Calendar candidates: last business day of each roll month
       (quarterly for ES/NQ/ZB, monthly for CL/GC).
    2. Volume validation: dates where volume > 3x the 42-day rolling median,
       near month-end (within 5 calendar days of month-end).
    3. Gap confirmation: dates with an overnight gap (|open/prev_close - 1|
       exceeding ROLL_GAP_THRESHOLD) near month-end.

    A date is a confirmed roll date if it satisfies (1) OR (2) OR (3).
    The calendar signal is the primary; volume and gap provide robustness
    when the =F stitching does not align with the standard calendar.
    """
    roll_months = ROLL_MONTHS.get(symbol, [3, 6, 9, 12])
    is_roll = pd.Series(False, index=close.index)

    # (1) Calendar: last business day of roll months
    for d in close.index:
        if d.month in roll_months:
            next_bd = d + pd.offsets.BDay(1)
            if next_bd.month != d.month:
                is_roll.loc[d] = True

    # Month-end proximity (within 5 calendar days)
    month_ends = close.index.to_series().apply(lambda d: d + pd.offsets.MonthEnd(0))
    days_to_me = (month_ends - close.index.to_series()).dt.days
    near_month_end = (days_to_me >= 0) & (days_to_me <= 5)

    # (2) Volume spikes near month-end
    vol_med = volume.rolling(ROLL_VOLUME_WINDOW, min_periods=20).median()
    vol_ratio = volume / vol_med.replace(0, np.nan)
    vol_spikes = near_month_end & (vol_ratio > ROLL_VOLUME_MULTIPLIER)
    is_roll = is_roll | vol_spikes.fillna(False)

    # (3) Gaps near month-end (for non-back-adjusted contracts like CL/GC)
    gap = open_ / close.shift(1) - 1.0
    big_gaps = near_month_end & (gap.abs() > ROLL_GAP_THRESHOLD)
    is_roll = is_roll | big_gaps.fillna(False)

    return is_roll


def detect_all_roll_dates(prices, opens, volumes):
    """Detect roll dates for all symbols in the universe.

    Returns dict: symbol -> boolean Series on prices.index.
    """
    roll_masks = {}
    for sym in prices.columns:
        close_s = prices[sym]
        open_s = opens[sym] if sym in opens.columns else close_s
        vol_s = volumes[sym] if sym in volumes.columns else pd.Series(0, index=prices.index)
        mask = detect_roll_dates_symbol(sym, close_s, open_s, vol_s)
        roll_masks[sym] = mask
    return roll_masks


# ============================================================
# Roll carry computation
# ============================================================
def compute_roll_carry(prices, opens, roll_masks):
    """Compute the roll carry series for each symbol.

    On roll dates: roll_carry = open / prev_close - 1 (the overnight gap
    that captures the old-front -> new-front contract transition).
    On non-roll dates: 0.

    Returns a DataFrame of roll_carry (same shape as prices).
    """
    roll_carry = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    for sym in prices.columns:
        mask = roll_masks.get(sym, pd.Series(False, index=prices.index))
        if mask.sum() > 0:
            gap = (opens[sym] / prices[sym].shift(1) - 1.0)
            roll_carry.loc[mask, sym] = gap.loc[mask]
    return roll_carry


# ============================================================
# Roll-adjusted returns and prices
# ============================================================
def build_roll_adjusted_returns(prices, roll_carry, weight):
    """Build roll-adjusted daily returns.

    R'_t = R_t + weight * roll_carry_t  (on roll dates)
    R'_t = R_t                          (on non-roll dates)

    Returns a DataFrame of roll-adjusted returns.
    """
    raw_returns = prices.pct_change()
    roll_returns = raw_returns + weight * roll_carry
    # Clip extreme returns (CL 2020 negative-price crash etc.)
    roll_returns = roll_returns.clip(-ROLL_MAX_RETURN_CLIP, ROLL_MAX_RETURN_CLIP)
    return roll_returns


def build_roll_adjusted_prices(prices, roll_adjusted_returns):
    """Convert roll-adjusted returns to a price series.

    P'_t = P_0 * cumprod(1 + R'_t) per symbol.
    """
    P0 = prices.iloc[0]
    P_adj = P0 * (1 + roll_adjusted_returns.fillna(0)).cumprod()
    return P_adj


# ============================================================
# TSMOM on roll-adjusted prices
# ============================================================
def resample_monthly_signals(signals):
    """Resample signals to monthly frequency (end-of-month last value)."""
    monthly = signals.resample("ME").last()
    full_index = signals.index
    return monthly.reindex(full_index, method="ffill").fillna(0)


def build_tsmom_signals(prices_adj):
    """Build vol-scaled TSMOM signals on roll-adjusted prices."""
    sig = vol_scaled_tsmom_signals(
        prices_adj,
        lookback=LOOKBACK,
        skip=SKIP,
        long_only=LONG_ONLY,
        target_vol=TARGET_VOL,
        vol_window=VOL_WINDOW,
        max_position_size=MAX_POSITION_SIZE,
    )
    return resample_monthly_signals(sig)


def make_futures_config(allow_short=False):
    """Create BacktestConfig with futures cost model."""
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


# ============================================================
# Evaluation utilities
# ============================================================
def split_returns_by_date(returns):
    """Split a returns Series into train/val/test/oos by date."""
    train = returns[returns.index <= TRAIN_END]
    val = returns[(returns.index > TRAIN_END) & (returns.index <= VAL_END)]
    test = returns[returns.index > VAL_END]
    oos = returns[returns.index > TRAIN_END]
    return train, val, test, oos


def window_max_drawdown(equity, start, end):
    """Max drawdown over a date window."""
    eq = equity.loc[start:end]
    if len(eq) < 2:
        return 0.0
    return float((eq / eq.cummax() - 1.0).min())


def regime_labels(vix_daily):
    """Label market regimes by VIX level (for worst-regime gate)."""
    regimes = pd.Series(index=vix_daily.index, dtype=object)
    vix_ff = vix_daily.ffill()
    regimes[vix_ff < 20] = "bull"
    regimes[(vix_ff >= 20) & (vix_ff <= 30)] = "sideways"
    regimes[vix_ff > 30] = "bear"
    return regimes


def compute_gate_metrics(result, prices, vix, label=""):
    """Compute full gate metrics for a backtest result."""
    train_ret, val_ret, test_ret, oos_ret = split_returns_by_date(result.returns)

    oos_sharpe = sharpe_ratio(oos_ret.values) if len(oos_ret) > 0 else 0.0
    train_sharpe = sharpe_ratio(train_ret.values) if len(train_ret) > 0 else 0.0
    val_sharpe = sharpe_ratio(val_ret.values) if len(val_ret) > 0 else 0.0
    test_sharpe = sharpe_ratio(test_ret.values) if len(test_ret) > 0 else 0.0

    oos_eq = result.equity_curve[result.equity_curve.index > pd.Timestamp(TRAIN_END)]
    if len(oos_eq) >= 2:
        oos_dd = float((oos_eq / oos_eq.expanding().max() - 1.0).min())
    else:
        oos_dd = 0.0

    gross_p = oos_ret[oos_ret > 0].sum() if len(oos_ret) else 0
    gross_l = abs(oos_ret[oos_ret < 0].sum()) if len(oos_ret) else 1e-18
    oos_pf = float(gross_p / gross_l) if gross_l > 0 else np.inf

    oos_trades = result.trades[result.trades["timestamp"] > pd.Timestamp(TRAIN_END)] if len(result.trades) else pd.DataFrame()

    wf_stab = oos_sharpe / train_sharpe if abs(train_sharpe) > 1e-18 else 0.0

    # Worst-regime Sharpe
    regimes = regime_labels(vix.reindex(oos_ret.index))
    worst = oos_sharpe
    for reg in ["bull", "sideways", "bear"]:
        mask = regimes == reg
        if len(mask) > 0 and mask.any():
            r = oos_ret[mask]
            if len(r) > 1 and r.std() > 0:
                s = sharpe_ratio(r.values)
                worst = min(worst, s)

    # Benchmark comparison: equal-weight futures buy-and-hold
    bh_signals = pd.DataFrame(
        1.0 / len(prices.columns),
        index=prices.index, columns=prices.columns,
    )
    bh_signals = resample_monthly_signals(bh_signals)
    bh_cfg = make_futures_config(allow_short=not LONG_ONLY)
    bh_result = run_backtest(
        prices=prices, signals=bh_signals, config=bh_cfg
    )
    bh_oos = bh_result.returns[bh_result.returns.index > pd.Timestamp(TRAIN_END)]
    if len(oos_ret) > 0 and len(bh_oos) > 0:
        alpha_res = compare_to_benchmark(oos_ret.values[-len(bh_oos):], bh_oos.values)
        p_val = float(alpha_res.get("alpha_p_value", 1.0))
        ir = float(alpha_res.get("information_ratio", -np.inf))
    else:
        p_val, ir = 1.0, -np.inf

    passes = {
        "sharpe": bool(oos_sharpe >= GATES["min_sharpe"]),
        "trades": bool(len(oos_trades) >= GATES["min_trades"]),
        "pf": bool(oos_pf >= GATES["min_profit_factor"]),
        "dd": bool(abs(oos_dd) <= GATES["max_drawdown"]),
        "stab": bool(wf_stab >= GATES["min_walkforward_stability"]),
        "worst": bool(worst >= GATES["min_worst_regime_sharpe"]),
        "p": bool(p_val < GATES["max_p_value"]),
        "ir": bool(ir > GATES["min_information_ratio"]),
    }

    metrics = {
        "train_sharpe": float(train_sharpe),
        "val_sharpe": float(val_sharpe),
        "test_sharpe": float(test_sharpe),
        "oos_sharpe": float(oos_sharpe),
        "oos_pf": float(oos_pf),
        "oos_max_dd": float(oos_dd),
        "oos_trades": len(oos_trades),
        "wf_stability": float(wf_stab),
        "worst_regime_sharpe": float(worst),
        "benchmark_p_value": float(p_val),
        "information_ratio": float(ir),
        "passes": passes,
        "all_pass": bool(all(passes.values())),
    }
    return metrics


# ============================================================
# Main experiment
# ============================================================
def main():
    np.random.seed(SEED)
    tracker = get_tracker()
    exp_id = tracker.start_experiment(
        name=EXPERIMENT_NAME,
        description=EXPERIMENT_DESC.strip(),
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
            "roll_detection": {
                "method": "calendar(last_BD_of_roll_months)+volume+gap",
                "roll_months": ROLL_MONTHS,
                "volume_multiplier": ROLL_VOLUME_MULTIPLIER,
                "volume_window": ROLL_VOLUME_WINDOW,
                "gap_threshold": ROLL_GAP_THRESHOLD,
            },
            "roll_carry": {
                "formula": "(open_t / close_{t-1} - 1) on roll dates",
                "weight_grid": ROLL_CARRY_WEIGHT_GRID,
                "return_clip": ROLL_MAX_RETURN_CLIP,
            },
            "selection": "Val Sharpe (Val only, Test protected)",
            "gates": GATES,
            "compute_budget": {"max_cpu_hours": 2.0},
            "random_seeds": {"numpy": SEED, "python": SEED},
        },
        data_sources={
            "source": "yahoo_futures",
            "symbols": FUTURES_UNIVERSE,
            "start": START_DATE,
            "end": END_DATE,
            "interval": "1d",
            "vix_symbol": VIX_SYMBOL,
        },
        random_seeds={"numpy": SEED, "python": SEED},
    )
    print(f"Started experiment: {exp_id}")

    try:
        # ---- Fetch data ----
        print("Fetching futures data...")
        fetcher = get_data_fetcher()
        raw_fut = fetcher.fetch_futures(
            FUTURES_UNIVERSE, start=START_DATE, end=END_DATE,
            interval="1d", use_cache=True,
        )
        prices = pd.DataFrame()
        opens = pd.DataFrame()
        volumes = pd.DataFrame()
        for sym in FUTURES_UNIVERSE:
            df = raw_fut.get(sym)
            if df is None or df.empty or "close" not in df.columns:
                print(f"  WARN: no data for {sym}")
                continue
            prices[sym] = df["close"]
            if "open" in df.columns:
                opens[sym] = df["open"]
            else:
                opens[sym] = df["close"]
            if "volume" in df.columns:
                volumes[sym] = df["volume"]
            else:
                volumes[sym] = 0
        prices = prices.ffill().dropna(how="all")
        opens = opens.reindex(prices.index).ffill()
        volumes = volumes.reindex(prices.index).fillna(0)
        print(f"Loaded {len(prices.columns)} futures x {len(prices)} days")

        raw_vix = fetcher.fetch_yahoo(
            [VIX_SYMBOL], start=START_DATE, end=END_DATE,
            interval="1d", use_cache=True,
        )
        vix_df = raw_vix.get(VIX_SYMBOL)
        vix = vix_df["close"] if (vix_df is not None and "close" in vix_df.columns) \
            else pd.Series(np.nan, index=prices.index)
        vix = vix.reindex(prices.index).ffill()

        tracker.log_dataframe("prices", prices)
        tracker.log_dataframe("opens", opens)
        tracker.log_dataframe("volumes", volumes)
        tracker.log_dataframe("vix_close", vix.to_frame("vix"))

        # ---- Roll detection ----
        print("Detecting roll dates...")
        roll_masks = detect_all_roll_dates(prices, opens, volumes)
        for sym in prices.columns:
            n = int(roll_masks.get(sym, pd.Series(dtype=bool)).sum())
            print(f"  {sym}: {n} roll dates detected")

        # Log roll masks
        roll_mask_df = pd.DataFrame(
            {sym: roll_masks.get(sym, pd.Series(False, index=prices.index)) for sym in prices.columns}
        )
        tracker.log_dataframe("roll_dates", roll_mask_df)

        # ---- Roll carry ----
        roll_carry = compute_roll_carry(prices, opens, roll_masks)
        tracker.log_dataframe("roll_carry", roll_carry)

        # ---- Grid search over roll-carry weight ----
        print(f"Running roll-carry weight grid: {ROLL_CARRY_WEIGHT_GRID}")
        grid_records = []
        best_val_sharpe = -np.inf
        best_weight = None
        best_result = None

        for weight in ROLL_CARRY_WEIGHT_GRID:
            # Build roll-adjusted returns and prices
            R_adj = build_roll_adjusted_returns(prices, roll_carry, weight)
            P_adj = build_roll_adjusted_prices(prices, R_adj)
            tracker.log_dataframe(f"roll_adjusted_prices_w{weight}", P_adj)

            # Build TSMOM signals
            sig = build_tsmom_signals(P_adj)
            tracker.log_dataframe(f"signals_w{weight}", sig)

            # Run backtest
            cfg = make_futures_config(allow_short=not LONG_ONLY)
            result = run_backtest(
                prices=P_adj, signals=sig,
                volumes=volumes, adv=None, config=cfg,
            )

            train_ret, val_ret, test_ret, oos_ret = split_returns_by_date(result.returns)
            train_s = sharpe_ratio(train_ret.values) if len(train_ret) else 0.0
            val_s = sharpe_ratio(val_ret.values) if len(val_ret) else 0.0
            test_s = sharpe_ratio(test_ret.values) if len(test_ret) else 0.0
            oos_s = sharpe_ratio(oos_ret.values) if len(oos_ret) else 0.0

            oos_eq = result.equity_curve[result.equity_curve.index > pd.Timestamp(TRAIN_END)]
            oos_dd = float((oos_eq / oos_eq.expanding().max() - 1.0).min()) if len(oos_eq) >= 2 else 0.0
            gross_p = oos_ret[oos_ret > 0].sum() if len(oos_ret) else 0
            gross_l = abs(oos_ret[oos_ret < 0].sum()) if len(oos_ret) else 1e-18
            oos_pf = float(gross_p / gross_l) if gross_l > 0 else np.inf
            oos_trades = result.trades[result.trades["timestamp"] > pd.Timestamp(TRAIN_END)] if len(result.trades) else pd.DataFrame()

            rec = {
                "roll_carry_weight": float(weight),
                "train_sharpe": float(train_s),
                "val_sharpe": float(val_s),
                "test_sharpe": float(test_s),
                "oos_sharpe": float(oos_s),
                "oos_pf": float(oos_pf),
                "oos_dd": float(oos_dd),
                "oos_trades": len(oos_trades),
            }
            grid_records.append(rec)
            print(f"  w={weight:.2f}: train_SR={train_s:.3f}, val_SR={val_s:.3f}, "
                  f"test_SR={test_s:.3f}, OOS_SR={oos_s:.3f}, "
                  f"DD={oos_dd:.3f}, PF={oos_pf:.3f}, trades={len(oos_trades)}")

            # Selection by Val Sharpe (test never enters selection)
            if val_s > best_val_sharpe:
                best_val_sharpe = val_s
                best_weight = weight
                best_result = result

        grid_df = pd.DataFrame(grid_records)
        grid_df = grid_df.sort_values("val_sharpe", ascending=False)
        tracker.log_dataframe("param_grid_results", grid_df)

        print(f"\nBest weight (by Val Sharpe): w={best_weight:.2f} "
              f"(val_SR={best_val_sharpe:.3f})")

        # ---- Full gate evaluation on best config ----
        print("\nEvaluating gates on best config...")
        gate_metrics = compute_gate_metrics(best_result, prices, vix)

        # ---- Ablation: base TSMOM (weight=0, no roll adjustment) ----
        print("Running ablation (base TSMOM, no roll adjustment)...")
        R_base = build_roll_adjusted_returns(prices, roll_carry, 0.0)
        P_base = build_roll_adjusted_prices(prices, R_base)
        sig_base = build_tsmom_signals(P_base)
        cfg_base = make_futures_config(allow_short=not LONG_ONLY)
        base_result = run_backtest(
            prices=P_base, signals=sig_base,
            volumes=volumes, adv=None, config=cfg_base,
        )
        base_metrics = compute_gate_metrics(base_result, prices, vix, label="base")
        print(f"  Base: OOS_SR={base_metrics['oos_sharpe']:.3f}, "
              f"DD={base_metrics['oos_max_dd']:.3f}, "
              f"PF={base_metrics['oos_pf']:.3f}")

        # Benchmark
        bh_signals = pd.DataFrame(
            1.0 / len(prices.columns),
            index=prices.index, columns=prices.columns,
        )
        bh_signals = resample_monthly_signals(bh_signals)
        bh_cfg = make_futures_config(allow_short=False)
        bh_result = run_backtest(
            prices=prices, signals=bh_signals, config=bh_cfg,
        )
        print(f"  Benchmark (EW futures BH): Sharpe={bh_result.metrics['sharpe']:.3f}")
        tracker.log_dataframe("benchmark_equity", bh_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("benchmark_trades", bh_result.trades)

        # ---- Ablation summary ----
        ablations = []
        for _, row in grid_df.iterrows():
            w = row["roll_carry_weight"]
            rec = {
                "name": f"roll_adj_w{w:.2f}",
                "weight": float(w),
                "oos_sharpe": float(row["oos_sharpe"]),
                "oos_max_dd": float(row["oos_dd"]),
                "oos_pf": float(row["oos_pf"]),
                "oos_trades": int(row["oos_trades"]),
            }
            ablations.append(rec)
        ablations.append({
            "name": "base_tsmom_no_roll_adj",
            "weight": 0.0,
            "oos_sharpe": float(base_metrics["oos_sharpe"]),
            "oos_max_dd": float(base_metrics["oos_max_dd"]),
            "oos_pf": float(base_metrics["oos_pf"]),
            "oos_trades": int(base_metrics["oos_trades"]),
        })
        ablation_df = pd.DataFrame(ablations)
        tracker.log_dataframe("ablations", ablation_df)

        # ---- Best result artifacts ----
        tracker.log_dataframe(f"best_equity_w{best_weight}", best_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe(f"best_trades_w{best_weight}", best_result.trades)
        tracker.log_dataframe(f"best_returns_w{best_weight}", best_result.returns.to_frame("returns"))
        tracker.log_dataframe("base_equity", base_result.equity_curve.to_frame("equity"))

        # ---- Summary ----
        summary = {
            "experiment_id": exp_id,
            "best_weight": float(best_weight),
            "best_val_sharpe": float(best_val_sharpe),
            "grid": grid_df.to_dict(orient="records"),
            "gate_metrics": {
                "train_sharpe": gate_metrics["train_sharpe"],
                "val_sharpe": gate_metrics["val_sharpe"],
                "test_sharpe": gate_metrics["test_sharpe"],
                "oos_sharpe": gate_metrics["oos_sharpe"],
                "oos_pf": gate_metrics["oos_pf"],
                "oos_max_dd": gate_metrics["oos_max_dd"],
                "oos_trades": gate_metrics["oos_trades"],
                "wf_stability": gate_metrics["wf_stability"],
                "worst_regime_sharpe": gate_metrics["worst_regime_sharpe"],
                "benchmark_p_value": gate_metrics["benchmark_p_value"],
                "information_ratio": gate_metrics["information_ratio"],
            },
            "passes": gate_metrics["passes"],
            "all_pass": gate_metrics["all_pass"],
            "verdict": "PASS" if gate_metrics["all_pass"] else "REJECT",
            "ablations": ablation_df.to_dict(orient="records"),
            "base_metrics": base_metrics,
            "benchmark_sharpe": float(bh_result.metrics["sharpe"]),
            "benchmark_return": float(bh_result.metrics["annualized_return"]),
            "benchmark_max_dd": float(bh_result.metrics["max_drawdown"]),
            "data_available": list(prices.columns),
            "roll_dates_count": {sym: int(roll_masks[sym].sum()) for sym in prices.columns},
        }

        exp_dir = Path(tracker.log_dir) / "artifacts" / exp_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        with open(exp_dir / "summary.json", "w") as f:
            json.dump(
                summary, f, indent=2,
                default=lambda o: bool(o) if isinstance(o, (np.bool_,)) else
                              (float(o) if isinstance(o, (np.integer, np.floating)) else str(o)),
            )
        tracker.log_artifact("summary", exp_dir / "summary.json")

        tracker.finish_experiment(status="completed")

        print("\n" + "=" * 70)
        print(f"H8 Verdict: {summary['verdict']}")
        print(f"Best weight: {best_weight} (Val SR={best_val_sharpe:.3f})")
        print(f"OOS Sharpe: {gate_metrics['oos_sharpe']:.3f} (gate >= {GATES['min_sharpe']})")
        print(f"OOS Max DD: {gate_metrics['oos_max_dd']:.3f} (gate <= {GATES['max_drawdown']})")
        print(f"OOS PF: {gate_metrics['oos_pf']:.3f} (gate >= {GATES['min_profit_factor']})")
        print(f"OOS Trades: {gate_metrics['oos_trades']} (gate >= {GATES['min_trades']})")
        print(f"WF Stability: {gate_metrics['wf_stability']:.3f} (gate >= {GATES['min_walkforward_stability']})")
        print(f"Worst Regime SR: {gate_metrics['worst_regime_sharpe']:.3f} (gate >= {GATES['min_worst_regime_sharpe']})")
        print(f"Benchmark p: {gate_metrics['benchmark_p_value']:.4f} (gate < {GATES['max_p_value']})")
        print(f"Information Ratio: {gate_metrics['information_ratio']:.3f} (gate > {GATES['min_information_ratio']})")
        print(f"Base (w=0) OOS Sharpe: {base_metrics['oos_sharpe']:.3f}")
        print(f"Roll-adjusted OOS Sharpe: {gate_metrics['oos_sharpe']:.3f}")
        print(f"Artifacts at: {exp_dir}")
        print("=" * 70)

        return 0 if gate_metrics["all_pass"] else 1

    except Exception as e:  # noqa: BLE001 -- top-level experiment harness: any failure must finish the tracker and return a verdict
        import traceback
        traceback.print_exc()
        tracker.finish_experiment(status="failed", error=str(e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
