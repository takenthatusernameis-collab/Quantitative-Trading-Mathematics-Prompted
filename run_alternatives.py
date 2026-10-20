#!/usr/bin/env python3
"""
Test alternative baseline strategies on SPY.

Experiment: H-20261010-004
Test EMA crossover and momentum strategies.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import json
from pathlib import Path

import numpy as np
import pandas as pd

from qtr.backtest.engine import AssetClass, BacktestConfig, run_backtest
from qtr.data.fetcher import get_data_fetcher
from qtr.strategies import run_strategy
from qtr.tracking.experiment import get_tracker


def main():
    EXPERIMENT_NAME = "alternative_strategies_v1"
    EXPERIMENT_DESC = """
    Test alternative baseline strategies on SPY:
    - EMA crossover (multiple spans)
    - Momentum (12-1 skip 1 month)
    - Mean reversion (Bollinger bands)
    Period: 2015-01-01 to 2024-12-31.
    """

    CONFIG = {
        "symbols": ["SPY"],
        "start_date": "2015-01-01",
        "end_date": "2024-12-31",
        "interval": "1d",
        "strategies": {
            "ewma_crossover": [
                {"fast_span": 12, "slow_span": 26},
                {"fast_span": 20, "slow_span": 50},
                {"fast_span": 50, "slow_span": 200},
            ],
            "momentum": [
                {"lookback": 252, "skip": 21, "n_top": 1},
                {"lookback": 126, "skip": 21, "n_top": 1},
                {"lookback": 63, "skip": 5, "n_top": 1},
            ],
            "mean_reversion": [
                {"window": 20, "num_std": 2.0},
                {"window": 20, "num_std": 1.5},
                {"window": 50, "num_std": 2.0},
            ],
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
        "random_seeds": {"numpy": 42, "python": 42},
        "compute_budget": {"max_cpu_hours": 2.0},
    }

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
        # Fetch data
        print("Fetching data...")
        fetcher = get_data_fetcher()
        raw_data = fetcher.fetch_yahoo(
            symbols=CONFIG["symbols"],
            start=CONFIG["start_date"],
            end=CONFIG["end_date"],
            interval=CONFIG["interval"],
            use_cache=True,
        )

        prices = pd.DataFrame()
        volumes = pd.DataFrame()
        for sym, df in raw_data.items():
            if not df.empty and "close" in df.columns:
                prices[sym] = df["close"]
                if "volume" in df.columns:
                    volumes[sym] = df["volume"]

        prices = prices.ffill().dropna(how="all").dropna(axis=1, how="all")
        volumes = volumes.reindex(prices.index).ffill().fillna(0)

        tracker.log_dataframe("prices", prices)
        tracker.log_dataframe("volumes", volumes)

        # Backtest config
        bt_config = BacktestConfig(
            initial_capital=CONFIG["backtest"]["initial_capital"],
            asset_class=AssetClass.EQUITY,
            max_position_size=CONFIG["backtest"]["max_position_size"],
            max_leverage=CONFIG["backtest"]["max_leverage"],
            allow_short=CONFIG["backtest"]["allow_short"],
        )
        bt_config.cost_model.equity_commission_bps = CONFIG["backtest"]["cost_model"][
            "equity_commission_bps"
        ]
        bt_config.cost_model.equity_spread_bps = CONFIG["backtest"]["cost_model"][
            "equity_spread_bps"
        ]
        bt_config.cost_model.equity_impact_bps_per_pct_adv = CONFIG["backtest"]["cost_model"][
            "equity_impact_bps_per_pct_adv"
        ]

        adv = volumes.rolling(20).mean().iloc[-1]

        # Buy-and-hold benchmark
        bh_signals = run_strategy(prices, "buy_and_hold", weight=1.0)
        bh_result = run_backtest(
            prices=prices,
            signals=bh_signals,
            volumes=volumes,
            adv=adv,
            config=bt_config,
        )

        print(
            f"Benchmark (Buy-and-Hold): Sharpe={bh_result.metrics['sharpe']:.3f}, "
            f"Ret={bh_result.metrics['annualized_return']:.2%}, DD={bh_result.metrics['max_drawdown']:.2%}"
        )

        # Test each strategy
        all_results = []
        best_sharpe = -np.inf
        best_name = None
        best_result = None

        for strat_name, param_list in CONFIG["strategies"].items():
            for params in param_list:
                print(f"  Testing {strat_name} {params}...", end=" ", flush=True)

                signals = run_strategy(prices, strat_name, **params)

                # Check if signals have any variation
                if signals.abs().sum().sum() == 0:
                    print("No signals generated")
                    continue

                result = run_backtest(
                    prices=prices,
                    signals=signals,
                    volumes=volumes,
                    adv=adv,
                    config=bt_config,
                )

                sharpe = result.metrics["sharpe"]
                max_dd = result.metrics["max_drawdown"]
                n_trades = result.metrics["num_trades"]
                ann_return = result.metrics["annualized_return"]

                all_results.append(
                    {
                        "strategy": strat_name,
                        "params": params,
                        "sharpe": sharpe,
                        "max_drawdown": max_dd,
                        "num_trades": n_trades,
                        "annualized_return": ann_return,
                        "annualized_volatility": result.metrics["annualized_volatility"],
                        "profit_factor": result.metrics["profit_factor"],
                    }
                )

                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_name = strat_name
                    best_result = result
                    best_params = params

                print(
                    f"Sharpe={sharpe:.3f}, DD={max_dd:.2%}, Trades={n_trades}, Ret={ann_return:.2%}"
                )

        # Log results
        results_df = pd.DataFrame(all_results)
        tracker.log_dataframe("strategy_results", results_df)

        if best_result is not None:
            tracker.log_dataframe("best_equity_curve", best_result.equity_curve.to_frame("equity"))
            tracker.log_dataframe("best_trades", best_result.trades)

        tracker.log_metrics({"benchmark_sharpe": bh_result.metrics["sharpe"]}, step=0)
        tracker.log_metrics({"benchmark_return": bh_result.metrics["annualized_return"]}, step=0)
        tracker.log_metrics({"benchmark_max_dd": bh_result.metrics["max_drawdown"]}, step=0)

        # Save summary
        summary = {
            "experiment_id": exp_id,
            "all_results": all_results,
            "best_strategy": best_name,
            "best_params": best_params,
            "best_sharpe": float(best_sharpe) if best_sharpe != -np.inf else None,
            "benchmark": {
                "sharpe": bh_result.metrics["sharpe"],
                "annualized_return": bh_result.metrics["annualized_return"],
                "max_drawdown": bh_result.metrics["max_drawdown"],
            },
            "config": CONFIG,
        }

        exp_dir = Path(tracker.log_dir) / "artifacts" / exp_id
        with open(exp_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2, default=str)

        tracker.log_artifact("summary", exp_dir / "summary.json")

        # Print summary
        print("\n" + "=" * 70)
        print("ALTERNATIVE STRATEGY RESULTS")
        print("=" * 70)
        print(f"Experiment ID: {exp_id}")
        print()
        print("ALL RESULTS:")
        for r in all_results:
            params_str = ", ".join(f"{k}={v}" for k, v in r["params"].items())
            print(
                f"  {r['strategy']} ({params_str}): "
                f"Sharpe={r['sharpe']:.3f}, DD={r['max_drawdown']:.2%}, "
                f"Trades={r['num_trades']}, Ret={r['annualized_return']:.2%}"
            )

        print()
        print("BENCHMARK (Buy-and-Hold):")
        print(f"  Sharpe: {bh_result.metrics['sharpe']:.3f}")
        print(f"  Return: {bh_result.metrics['annualized_return']:.2%}")
        print(f"  Max DD: {bh_result.metrics['max_drawdown']:.2%}")

        print()
        print("BEST STRATEGY:")
        if best_name:
            params_str = ", ".join(f"{k}={v}" for k, v in best_params.items())
            print(f"  {best_name} ({params_str})")
            print(f"  Sharpe: {best_sharpe:.3f}")
            print(f"  Return: {best_result.metrics['annualized_return']:.2%}")
            print(f"  Max DD: {best_result.metrics['max_drawdown']:.2%}")
            print(f"  Trades: {best_result.metrics['num_trades']}")
            print(
                f"  Beats benchmark: {'YES' if best_sharpe > bh_result.metrics['sharpe'] else 'NO'}"
            )

        print("=" * 70)

        tracker.finish_experiment(status="completed")

        return best_sharpe > bh_result.metrics["sharpe"]

    except Exception as e:  # noqa: BLE001 -- top-level experiment harness: any failure must finish the tracker and return a verdict
        print(f"Experiment failed: {e}")
        import traceback

        traceback.print_exc()
        tracker.finish_experiment(status="failed", error=str(e))
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
