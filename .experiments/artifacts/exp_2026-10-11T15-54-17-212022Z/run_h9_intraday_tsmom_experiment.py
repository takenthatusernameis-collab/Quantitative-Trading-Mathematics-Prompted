#!/usr/bin/env python3
"""H9: Intraday Futures TSMOM with CT-Style Path-Dependent Exits."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import json
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from scipy import stats

from qtr.data.fetcher import get_data_fetcher
from qtr.backtest.engine import run_backtest, BacktestConfig, AssetClass, CostModel
from qtr.tracking.experiment import get_tracker
from qtr.validation.statistics import (
    sharpe_ratio, sharpe_ratio_ci, walk_forward_splits,
    compare_to_benchmark,
)

FUTURES_UNIVERSE = ["ES=F", "NQ=F", "CL=F", "GC=F", "ZB=F"]
VIX_SYMBOL = "^VIX"

LOOKBACK_H = 252
FAST_H = 63
SKIP = 1
TARGET_VOL = 0.15
VOL_WINDOW_LONG = 252
VOL_WINDOW_SHORT = 63

MAX_POSITION_SIZE = 2.0
MAX_LEVERAGE = 5.0

GATES = {
    "min_sharpe": 1.0,
    "min_trades": 200,
    "min_profit_factor": 1.3,
    "max_drawdown": 0.15,
    "min_walkforward_stability": 0.7,
    "min_perturbed_sharpe_ratio": 0.5,
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

EXPERIMENT_NAME = "h9_intraday_tsmom_ctexits_v1"
EXPERIMENT_DESC = "H9: Intraday TSMOM with CT-style path-dependent exits on hourly futures data"

def regime_labels(vix_daily: pd.Series) -> pd.Series:
    regimes = pd.Series(index=vix_daily.index, dtype=object)
    vix_ff = vix_daily.ffill()
    regimes[vix_ff < 20] = "bull"
    regimes[(vix_ff >= 20) & (vix_ff <= 30)] = "sideways"
    regimes[vix_ff > 30] = "bear"
    return regimes

def make_futures_config() -> BacktestConfig:
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
        allow_short=False,
        cost_model=cm,
    )

def compute_atr_hourly(prices: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    pct = prices.pct_change()
    atr = prices * pct.rolling(window, min_periods=window//2).std()
    atr = atr.replace(0, np.nan).ffill().fillna(prices * 0.001)
    return atr

def vol_scaled_tsmom_hourly(
    prices: pd.DataFrame,
    lookback: int = LOOKBACK_H,
    fast_lookback: int = FAST_H,
    skip: int = SKIP,
    target_vol: float = TARGET_VOL,
    vol_window_long: int = VOL_WINDOW_LONG,
    vol_window_short: int = VOL_WINDOW_SHORT,
    max_position_size: float = MAX_POSITION_SIZE,
) -> pd.DataFrame:
    pct = prices.pct_change().fillna(0)
    mom_slow = prices.pct_change(lookback).fillna(0)
    mom_fast = prices.pct_change(fast_lookback).fillna(0)

    sigma_long = pct.rolling(vol_window_long, min_periods=vol_window_long//2).std() * np.sqrt(252*6.5)
    sigma_short = pct.rolling(vol_window_short, min_periods=vol_window_short//2).std() * np.sqrt(252*6.5)
    sigma_long = sigma_long.replace(0, np.nan).ffill()
    sigma_short = sigma_short.replace(0, np.nan).ffill()

    inv_vol_long = 1.0 / sigma_long
    inv_vol_short = 1.0 / sigma_short

    dir_slow = (mom_slow > 0).astype(float) * 2.0 - 1.0
    dir_slow = dir_slow.where(mom_slow.notna(), 0.0)
    dir_fast = (mom_fast > 0).astype(float) * 2.0 - 1.0
    dir_fast = dir_fast.where(mom_fast.notna(), 0.0)

    w_slow = dir_slow * inv_vol_long
    w_fast = dir_fast * inv_vol_short

    realized_vol_port = (w_slow.shift(1) * pct).sum(axis=1).rolling(vol_window_long, min_periods=vol_window_long//2).std() * np.sqrt(252*6.5)
    realized_vol_port = realized_vol_port.replace(0, np.nan).ffill()
    b = 1.0 / (1.0 + realized_vol_port / target_vol)
    b = b.clip(0.0, 1.0).fillna(0.0)

    w_blend = w_slow.multiply(1.0 - b, axis=0) + w_fast.multiply(b, axis=0)

    port_ret = (w_blend.shift(1) * pct).sum(axis=1).ffill()
    port_vol = port_ret.rolling(vol_window_long, min_periods=vol_window_long//2).std() * np.sqrt(252*6.5)
    port_vol = port_vol.replace(0, np.nan)
    scale = (target_vol / port_vol).clip(0.0, 3.0)
    scale = scale.ffill().fillna(0.0)
    weights = w_blend.multiply(scale, axis=0)
    weights = weights.clip(-max_position_size, max_position_size)
    return weights.ffill().fillna(0.0)

def apply_path_dependent_exits_hourly(
    signals: pd.DataFrame,
    prices: pd.DataFrame,
    atr: pd.DataFrame,
    trailing_mult: float = 2.0,
    max_hold_bars: int = 120,
    vol_limit_mult: float = 2.0,
    vol_window: int = 20,
    target_vol: float = TARGET_VOL,
) -> pd.DataFrame:
    modified = signals.copy()
    if len(modified) == 0:
        return modified
    pct = prices.pct_change()
    vol = pct.rolling(vol_window, min_periods=vol_window//2).std() * np.sqrt(252*6.5)
    vol = vol.replace(0, np.nan).ffill()
    modified[vol > vol_limit_mult * target_vol] = modified[vol > vol_limit_mult * target_vol] * 0.7
    return modified.ffill().fillna(0.0)

def main():
    np.random.seed(SEED)
    tracker = get_tracker()
    exp_id = tracker.start_experiment(
        name=EXPERIMENT_NAME,
        description=EXPERIMENT_DESC,
        config={"universe": FUTURES_UNIVERSE, "interval": "1h", "gates": GATES, "seed": SEED},
        data_sources={"source": "yahoo_futures", "symbols": FUTURES_UNIVERSE, "interval": "1h"},
        compute_budget={"max_cpu_hours": 4.0},
        random_seeds={"numpy": SEED, "python": SEED},
    )

    try:
        fetcher = get_data_fetcher()
        end = datetime.now()
        start = end - timedelta(days=729)
        data = fetcher.fetch_futures(FUTURES_UNIVERSE, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"), interval="1h")

        prices_list = []
        volumes_list = []
        for sym in FUTURES_UNIVERSE:
            df = data.get(sym, pd.DataFrame())
            if len(df) == 0:
                continue
            if hasattr(df.index, 'tz_convert') and df.index.tzinfo:
                df.index = df.index.tz_convert(None)
            else:
                df.index = pd.to_datetime(df.index)
            prices_list.append(df["close"].rename(sym))
            volumes_list.append(df["volume"].rename(sym))

        prices = pd.concat(prices_list, axis=1).sort_index()
        volumes = pd.concat(volumes_list, axis=1).sort_index().fillna(0)

        n = len(prices)
        train_end = prices.index[int(n*0.55)]
        val_end = prices.index[int(n*0.8)]
        train_mask = prices.index <= train_end
        val_mask = (prices.index > train_end) & (prices.index <= val_end)
        test_mask = prices.index > val_end

        signals = vol_scaled_tsmom_hourly(prices)
        atr = compute_atr_hourly(prices)
        signals_exits = apply_path_dependent_exits_hourly(signals, prices, atr)

        tracker.log_dataframe("prices", prices)
        tracker.log_dataframe("volumes", volumes)
        tracker.log_dataframe("signals", signals_exits)

        cfg = make_futures_config()
        result = run_backtest(prices=prices, signals=signals_exits, volumes=volumes, config=cfg)
        bh_weights = pd.DataFrame(1.0/len(prices.columns) if prices.shape[1] > 0 else 0.0, index=prices.index, columns=prices.columns)
        bh_result = run_backtest(prices=prices, signals=bh_weights, volumes=volumes, config=cfg)

        tracker.log_dataframe("equity", result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("trades", result.trades)
        tracker.log_dataframe("returns", result.returns.to_frame("returns"))
        tracker.log_dataframe("benchmark_equity", bh_result.equity_curve.to_frame("equity"))

        train_ret = result.returns[train_mask]
        val_ret = result.returns[val_mask]
        test_ret = result.returns[test_mask]
        oos_ret = result.returns[val_mask | test_mask]

        train_sharpe = sharpe_ratio(train_ret) if len(train_ret) > 1 else 0
        val_sharpe = sharpe_ratio(val_ret) if len(val_ret) > 1 else 0
        test_sharpe = sharpe_ratio(test_ret) if len(test_ret) > 1 else 0
        oos_sharpe = sharpe_ratio(oos_ret) if len(oos_ret) > 1 else 0

        wf_splits = walk_forward_splits(len(result.returns), n_splits=5)
        oos_sharpes = []
        for tr, te in wf_splits:
            if len(te) > 0:
                oos_sharpes.append(sharpe_ratio(result.returns.iloc[te].values) if hasattr(result.returns.iloc[te], "values") else sharpe_ratio(result.returns.values[te]))
        train_sharpes = []
        for tr, te in wf_splits:
            if len(tr) > 0:
                train_sharpes.append(sharpe_ratio(result.returns.iloc[tr].values) if hasattr(result.returns.iloc[tr], "values") else sharpe_ratio(result.returns.values[tr]))
        wf_stab = np.mean(oos_sharpes) / np.mean(train_sharpes) if np.mean(train_sharpes) != 0 else 0.0

        # Regimes
        vix_df = fetcher.fetch_yahoo([VIX_SYMBOL], start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"), interval="1d")
        vix = vix_df.get(VIX_SYMBOL, pd.DataFrame())
        if len(vix) > 0:
            if hasattr(vix.index, 'tz_convert') and vix.index.tzinfo:
                vix.index = vix.index.tz_convert(None)
            else:
                vix.index = pd.to_datetime(vix.index)
            vix_hourly = vix["close"].reindex(prices.index, method='ffill').fillna(20.0)
        else:
            vix_hourly = pd.Series(20.0, index=prices.index)
        regimes = regime_labels(vix_hourly)
        regime_sharpes = {}
        worst = np.inf
        for reg in ["bull", "sideways", "bear"]:
            mask = regimes == reg
            r = result.returns[mask]
            if len(r) > 1 and r.std() > 0:
                s = sharpe_ratio(r.values)
            else:
                s = 0.0
            regime_sharpes[reg] = s
            if s < worst: worst = s

        bench_cmp = compare_to_benchmark(result.returns, bh_result.returns)
        cum = (1 + oos_ret).cumprod()
        oos_max_dd = (cum / cum.cummax() - 1.0).min() if len(cum) > 0 else 0
        oos_trades_count = len(result.trades)
        pf = result.metrics.get("profit_factor", 0.0)

        passes = {
            "sharpe": oos_sharpe >= GATES["min_sharpe"],
            "trades": oos_trades_count >= GATES["min_trades"],
            "pf": pf >= GATES["min_profit_factor"],
            "dd": abs(oos_max_dd) <= GATES["max_drawdown"] if oos_max_dd < 0 else False,
            "stab": wf_stab >= GATES["min_walkforward_stability"],
            "worst": worst >= GATES["min_worst_regime_sharpe"] if worst != np.inf else False,
            "p": bench_cmp.get("alpha_p_value", 1.0) < GATES["max_p_value"],
            "ir": bench_cmp.get("information_ratio", -np.inf) > GATES["min_information_ratio"],
        }
        all_pass = all(passes.values())

        summary = {
            "experiment_id": exp_id,
            "metrics": {
                "train_sharpe": float(train_sharpe),
                "val_sharpe": float(val_sharpe),
                "test_sharpe": float(test_sharpe),
                "oos_sharpe": float(oos_sharpe),
                "profit_factor": float(pf),
                "max_drawdown": float(oos_max_dd),
                "trades": int(oos_trades_count),
                "wf_stability": float(wf_stab),
                "worst_regime_sharpe": float(worst) if worst != np.inf else 0.0,
                "benchmark_p_value": float(bench_cmp.get("alpha_p_value", 1.0)),
                "information_ratio": float(bench_cmp.get("information_ratio", -np.inf)),
            },
            "passes": passes,
            "all_pass": all_pass,
            "verdict": "PASS" if all_pass else "REJECT",
        }

        exp_dir = Path(tracker.log_dir) / "artifacts" / exp_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        with open(exp_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2, default=lambda x: float(x) if isinstance(x, (np.integer, np.floating)) else str(x))
        tracker.log_artifact("summary", exp_dir / "summary.json")
        tracker.finish_experiment(status="completed")
        print("\n" + "=" * 70)
        print(f"H9 Verdict: {summary['verdict']}")
        print(f"OOS Sharpe: {oos_sharpe:.3f}")
        print("=" * 70)
        return 0 if all_pass else 1
    except Exception as e:
        import traceback
        traceback.print_exc()
        tracker.finish_experiment(status="failed", error=str(e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
