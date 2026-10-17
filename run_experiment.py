#!/usr/bin/env python3
"""
First baseline experiment: MA Crossover on US Equity ETFs.

Experiment: H-20261010-001
Hypothesis: Simple MA crossover (20/50) on liquid equity ETFs produces
positive risk-adjusted returns net of transaction costs.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import json
from pathlib import Path

import pandas as pd

from qtr.backtest.engine import AssetClass, BacktestConfig, run_backtest
from qtr.data.fetcher import get_data_fetcher
from qtr.strategies import run_strategy
from qtr.tracking.experiment import get_tracker
from qtr.validation.statistics import (
    sharpe_ratio,
    sharpe_ratio_ci,
    validate_strategy,
    walk_forward_splits,
)


def main():
    # ============================================================
    # EXPERIMENT CONFIGURATION (Pre-registered)
    # ============================================================
    EXPERIMENT_NAME = "ma_crossover_baseline_v1"
    EXPERIMENT_DESC = """
    Baseline MA Crossover (20/50) on SPY, QQQ, IWM, EFA, EEM.
    Period: 2015-01-01 to 2024-12-31 (10 years).
    Daily data from Yahoo Finance.
    Cost model: 1 bp commission + 1 bp spread (equities).
    Long-only, equal weight, no leverage.
    Train: 2015-2020, Val: 2021-2022, Test: 2023-2024 (protected holdout).
    """
    
    CONFIG = {
        "symbols": ["SPY", "QQQ", "IWM", "EFA", "EEM"],
        "start_date": "2015-01-01",
        "end_date": "2024-12-31",
        "interval": "1d",
        "strategy": "ma_crossover",
        "strategy_params": {
            "fast_window": 20,
            "slow_window": 50,
            "long_only": True,
        },
        "backtest": {
            "initial_capital": 1_000_000,
            "asset_class": "equity",
            "max_position_size": 1.0,
            "max_leverage": 1.0,
            "allow_short": False,
            "cost_model": {
                "equity_commission_bps": 1.0,
                "equity_spread_bps": 1.0,
                "equity_impact_bps_per_pct_adv": 0.1,
            },
        },
        "validation": {
            "min_sharpe": 1.0,
            "min_trades": 200,
            "min_profit_factor": 1.3,
            "max_drawdown": 0.15,
            "min_walkforward_stability": 0.7,
            "min_param_stability": 0.8,
        },
        "data_splits": {
            "train_end": "2020-12-31",
            "val_end": "2022-12-31",
            "test_start": "2023-01-01",
        },
        "random_seeds": {
            "numpy": 42,
            "python": 42,
        },
        "compute_budget": {
            "max_cpu_hours": 1.0,
        },
    }

    # ============================================================
    # START EXPERIMENT TRACKING
    # ============================================================
    tracker = get_tracker()
    exp_id = tracker.start_experiment(
        name=EXPERIMENT_NAME,
        description=EXPERIMENT_DESC.strip(),
        config=CONFIG,
        data_sources={
            "source": "yahoo",
            "symbols": CONFIG["symbols"],
            "start": CONFIG["start_date"],
            "end": CONFIG["end_date"],
            "interval": CONFIG["interval"],
        },
        compute_budget=CONFIG["compute_budget"],
        random_seeds=CONFIG["random_seeds"],
    )
    
    print(f"Started experiment: {exp_id}")
    
    try:
        # ============================================================
        # FETCH DATA
        # ============================================================
        print("Fetching data...")
        fetcher = get_data_fetcher()
        raw_data = fetcher.fetch_yahoo(
            symbols=CONFIG["symbols"],
            start=CONFIG["start_date"],
            end=CONFIG["end_date"],
            interval=CONFIG["interval"],
            use_cache=True,
        )
        
        # Combine into price DataFrame
        prices = pd.DataFrame()
        volumes = pd.DataFrame()
        for sym, df in raw_data.items():
            if not df.empty and "close" in df.columns:
                prices[sym] = df["close"]
                if "volume" in df.columns:
                    volumes[sym] = df["volume"]
        
        prices = prices.ffill().dropna(how="all").dropna(axis=1, how="all")
        volumes = volumes.reindex(prices.index).ffill().fillna(0)
        
        print(f"Loaded {len(prices.columns)} symbols, {len(prices)} days")
        print(f"Date range: {prices.index[0]} to {prices.index[-1]}")
        
        # Log data artifacts
        tracker.log_dataframe("prices", prices)
        tracker.log_dataframe("volumes", volumes)
        
        # ============================================================
        # GENERATE SIGNALS
        # ============================================================
        print("Generating signals...")
        signals = run_strategy(
            prices,
            CONFIG["strategy"],
            **CONFIG["strategy_params"],
        )
        
        # Buy-and-hold benchmark
        benchmark_signals = run_strategy(
            prices,
            "buy_and_hold",
            weight=1.0 / len(prices.columns),
        )
        
        tracker.log_dataframe("signals_ma_crossover", signals)
        tracker.log_dataframe("signals_buy_and_hold", benchmark_signals)
        
        # ============================================================
        # RUN BACKTESTS
        # ============================================================
        print("Running backtests...")
        
        bt_config = BacktestConfig(
            initial_capital=CONFIG["backtest"]["initial_capital"],
            asset_class=AssetClass.EQUITY,
            max_position_size=CONFIG["backtest"]["max_position_size"],
            max_leverage=CONFIG["backtest"]["max_leverage"],
            allow_short=CONFIG["backtest"]["allow_short"],
        )
        bt_config.cost_model.equity_commission_bps = CONFIG["backtest"]["cost_model"]["equity_commission_bps"]
        bt_config.cost_model.equity_spread_bps = CONFIG["backtest"]["cost_model"]["equity_spread_bps"]
        bt_config.cost_model.equity_impact_bps_per_pct_adv = CONFIG["backtest"]["cost_model"]["equity_impact_bps_per_pct_adv"]
        
        # Estimate ADV for impact model (rough: 20-day average volume)
        adv = volumes.rolling(20).mean().iloc[-1]
        
        # Strategy backtest
        result = run_backtest(
            prices=prices,
            signals=signals,
            volumes=volumes,
            adv=adv,
            config=bt_config,
        )
        
        # Benchmark backtest
        benchmark_result = run_backtest(
            prices=prices,
            signals=benchmark_signals,
            volumes=volumes,
            adv=adv,
            config=bt_config,
        )
        
        print(f"Strategy Sharpe: {result.metrics['sharpe']:.3f}")
        print(f"Benchmark Sharpe: {benchmark_result.metrics['sharpe']:.3f}")
        print(f"Strategy Trades: {result.metrics['num_trades']}")
        print(f"Max Drawdown: {result.metrics['max_drawdown']:.3f}")
        
        # ============================================================
        # VALIDATION
        # ============================================================
        print("Validating...")
        validation = validate_strategy(
            returns=result.returns.values,
            trades=result.trades,
            config=CONFIG["validation"],
        )
        
        # Bootstrap CI for Sharpe
        sharpe_ci = sharpe_ratio_ci(result.returns.values, n_bootstrap=1000, random_state=42)
        validation["sharpe_ci_lower"] = sharpe_ci[0]
        validation["sharpe_ci_upper"] = sharpe_ci[1]
        
        # Walk-forward analysis
        wf_splits = walk_forward_splits(len(result.returns), n_splits=5)
        wf_sharpes = []
        for train_idx, test_idx in wf_splits:
            train_sharpe = sharpe_ratio(result.returns.iloc[train_idx].values)
            test_sharpe = sharpe_ratio(result.returns.iloc[test_idx].values)
            wf_sharpes.append({"train": train_sharpe, "test": test_sharpe})
        
        validation["walkforward_folds"] = wf_sharpes
        
        # Train/Val/Test split metrics
        train_end = CONFIG["data_splits"]["train_end"]
        val_end = CONFIG["data_splits"]["val_end"]
        
        train_returns = result.returns[result.returns.index <= train_end]
        val_returns = result.returns[(result.returns.index > train_end) & (result.returns.index <= val_end)]
        test_returns = result.returns[result.returns.index > val_end]
        
        validation["train_sharpe"] = sharpe_ratio(train_returns.values)
        validation["val_sharpe"] = sharpe_ratio(val_returns.values)
        validation["test_sharpe"] = sharpe_ratio(test_returns.values)
        
        # ============================================================
        # LOG METRICS
        # ============================================================
        tracker.log_metrics(result.metrics, step=0)
        tracker.log_metrics({f"benchmark_{k}": v for k, v in benchmark_result.metrics.items()}, step=0)
        tracker.log_metrics(validation, step=1)
        
        # Log equity curves
        tracker.log_dataframe("equity_curve", result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("benchmark_equity", benchmark_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("trades", result.trades)
        
        # ============================================================
        # SAVE SUMMARY
        # ============================================================
        summary = {
            "experiment_id": exp_id,
            "strategy_metrics": result.metrics,
            "benchmark_metrics": benchmark_result.metrics,
            "validation": validation,
            "config": CONFIG,
        }
        
        # Save to experiment directory
        exp_dir = Path(tracker.log_dir) / "artifacts" / exp_id
        with open(exp_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2, default=str)
        
        tracker.log_artifact("summary", exp_dir / "summary.json")
        
        # ============================================================
        # PRINT RESULTS
        # ============================================================
        print("\n" + "="*60)
        print("EXPERIMENT RESULTS SUMMARY")
        print("="*60)
        print(f"Experiment ID: {exp_id}")
        print(f"Strategy: {CONFIG['strategy']} ({CONFIG['strategy_params']})")
        print(f"Period: {CONFIG['start_date']} to {CONFIG['end_date']}")
        print(f"Symbols: {CONFIG['symbols']}")
        print()
        print("PERFORMANCE METRICS:")
        print(f"  Net Sharpe:           {result.metrics['sharpe']:.3f} (CI: [{sharpe_ci[0]:.3f}, {sharpe_ci[1]:.3f}])")
        print(f"  Benchmark Sharpe:     {benchmark_result.metrics['sharpe']:.3f}")
        print(f"  Annualized Return:    {result.metrics['annualized_return']:.2%}")
        print(f"  Annualized Vol:       {result.metrics['annualized_volatility']:.2%}")
        print(f"  Max Drawdown:         {result.metrics['max_drawdown']:.2%}")
        print(f"  Profit Factor:        {result.metrics['profit_factor']:.3f}")
        print(f"  Number of Trades:     {result.metrics['num_trades']}")
        print(f"  Avg Trade Cost:       {result.metrics['avg_trade_cost']:.4f}")
        print()
        print("VALIDATION (PROMPT_V2.md criteria):")
        print(f"  Sharpe >= 1.0:        {'PASS' if validation['sharpe_pass'] else 'FAIL'} ({validation['sharpe']:.3f})")
        print(f"  Trades >= 200:        {'PASS' if validation['trades_pass'] else 'FAIL'} ({validation['n_trades']})")
        print(f"  Profit Factor >= 1.3: {'PASS' if validation['profit_factor_pass'] else 'FAIL'} ({validation['profit_factor']:.3f})")
        print(f"  Max DD <= 15%:        {'PASS' if validation['drawdown_pass'] else 'FAIL'} ({validation['max_drawdown']:.2%})")
        print(f"  WF Stability >= 0.7:  {'PASS' if validation['walkforward_pass'] else 'FAIL'} ({validation['walkforward_stability']:.3f})")
        print(f"  Train Sharpe:         {validation['train_sharpe']:.3f}")
        print(f"  Val Sharpe:           {validation['val_sharpe']:.3f}")
        print(f"  Test Sharpe:          {validation['test_sharpe']:.3f}")
        print()
        print(f"  ALL CRITERIA MET:     {'YES' if validation['all_pass'] else 'NO'}")
        print("="*60)
        
        # Finish experiment
        tracker.finish_experiment(status="completed")
        
        return validation["all_pass"]
        
    except Exception as e:
        print(f"Experiment failed: {e}")
        import traceback
        traceback.print_exc()
        tracker.finish_experiment(status="failed", error=str(e))
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)