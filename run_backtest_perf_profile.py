#!/usr/bin/env python3
"""
Performance profiling for the vectorized backtest engine.

Measures execution time and memory usage across varying universe sizes
and time periods to characterize engine scaling behavior.

This is an infrastructure auditing script per STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §6
fallback path: "Performance profiling of backtest engine on large universes".
"""

import gc
import os
import sys
import time
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from qtr.backtest.engine import AssetClass, BacktestConfig, CostModel, run_backtest


def generate_synthetic_data(
    n_symbols: int, n_bars: int, freq: str = "1D"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate synthetic price and volume data for benchmarking."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=n_bars, freq=freq)
    symbols = [f"SYM{i:04d}" for i in range(n_symbols)]

    # Generate correlated random walks
    returns = np.random.randn(n_bars, n_symbols) * 0.01
    # Add slight correlation structure
    market_factor = np.random.randn(n_bars) * 0.005
    for i in range(n_symbols):
        returns[:, i] += market_factor * 0.3

    # Build price series from returns
    prices = 100 * np.exp(np.cumsum(returns, axis=0))
    prices_df = pd.DataFrame(prices, index=dates, columns=symbols)

    # Generate volume data
    volumes = np.random.lognormal(15, 0.5, size=(n_bars, n_symbols)).astype(int)
    volumes_df = pd.DataFrame(volumes, index=dates, columns=symbols)

    return prices_df, volumes_df


def generate_signals(n_symbols: int, n_bars: int, dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Generate synthetic signals (random weights for stress testing)."""
    np.random.seed(123)
    symbols = [f"SYM{i:04d}" for i in range(n_symbols)]
    # Random walk signals with mean reversion
    signals = np.random.randn(n_bars, n_symbols) * 0.1
    signals = np.cumsum(signals, axis=0) * 0.01
    signals = np.clip(signals, -1.0, 1.0)
    signals_df = pd.DataFrame(signals, index=dates, columns=symbols)
    return signals_df


def run_benchmark(
    n_symbols: int,
    n_bars: int,
    asset_class: AssetClass = AssetClass.EQUITY,
    allow_short: bool = True,
    max_leverage: float = 1.0,
) -> dict:
    """Run a single backtest benchmark and return timing/memory metrics."""

    print(
        f"  Benchmarking: {n_symbols} symbols x {n_bars} bars ({asset_class.value})...",
        end=" ",
        flush=True,
    )

    # Generate data
    prices, volumes = generate_synthetic_data(n_symbols, n_bars)
    signals = generate_signals(n_symbols, n_bars, prices.index)

    # Configure backtest
    config = BacktestConfig(
        initial_capital=1_000_000.0,
        asset_class=asset_class,
        max_position_size=1.0,
        max_leverage=max_leverage,
        allow_short=allow_short,
    )

    # Equity cost model
    config.cost_model.equity_commission_bps = 1.0
    config.cost_model.equity_spread_bps = 1.0
    config.cost_model.equity_impact_bps_per_pct_adv = 0.1

    # Futures cost model
    config.cost_model.future_commission_per_contract = 0.5
    config.cost_model.future_tick_value = 12.5
    config.cost_model.future_spread_ticks = 0.25
    config.cost_model.future_slippage_ticks = 0.5

    # Crypto cost model
    config.cost_model.crypto_fee_bps = 5.0
    config.cost_model.crypto_spread_bps = 2.0
    config.cost_model.crypto_slippage_bps_per_pct_daily_vol = 0.0

    # ADV for equity impact cost
    adv = volumes.rolling(20).mean().iloc[-1]

    # Force garbage collection before measurement
    gc.collect()

    # Start memory tracing
    tracemalloc.start()

    # Time the backtest
    start_time = time.perf_counter()
    result = run_backtest(
        prices=prices,
        signals=signals,
        volumes=volumes,
        adv=adv,
        config=config,
    )
    end_time = time.perf_counter()

    # Get memory stats
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    elapsed = end_time - start_time
    peak_mb = peak / (1024 * 1024)

    metrics = {
        "n_symbols": n_symbols,
        "n_bars": n_bars,
        "asset_class": asset_class.value,
        "allow_short": allow_short,
        "max_leverage": max_leverage,
        "elapsed_seconds": elapsed,
        "peak_memory_mb": peak_mb,
        "trades": result.metrics["num_trades"],
        "sharpe": result.metrics["sharpe"],
        "total_return": result.metrics["total_return"],
    }

    print(f"{elapsed:.3f}s, {peak_mb:.1f}MB, {result.metrics['num_trades']:.0f} trades")
    return metrics


def main():
    print("=" * 70)
    print("BACKTEST ENGINE PERFORMANCE PROFILING")
    print("=" * 70)
    print()

    # Test matrix: (n_symbols, n_bars)
    test_matrix = [
        # Small
        (1, 252),  # 1 symbol, 1 year
        (5, 252),  # 5 symbols, 1 year
        (10, 252),  # 10 symbols, 1 year
        # Medium
        (20, 252),  # 20 symbols, 1 year
        (50, 252),  # 50 symbols, 1 year
        (100, 252),  # 100 symbols, 1 year
        # Large (1 year)
        (200, 252),  # 200 symbols, 1 year
        (500, 252),  # 500 symbols, 1 year
        # Longer timeframes
        (10, 1260),  # 10 symbols, 5 years
        (50, 1260),  # 50 symbols, 5 years
        (100, 1260),  # 100 symbols, 5 years
        (200, 1260),  # 200 symbols, 5 years
        # Very long
        (10, 2520),  # 10 symbols, 10 years
        (50, 2520),  # 50 symbols, 10 years
        (100, 2520),  # 100 symbols, 10 years
    ]

    results = []

    print("Running equity benchmarks (long-only)...")
    for n_sym, n_bar in test_matrix:
        try:
            metrics = run_benchmark(
                n_sym, n_bar, AssetClass.EQUITY, allow_short=False, max_leverage=1.0
            )
            results.append(metrics)
        except Exception as e:
            print(f"  FAILED: {e}")
            results.append({"n_symbols": n_sym, "n_bars": n_bar, "error": str(e)})

    print()
    print("Running equity benchmarks (long-short, 2x leverage)...")
    for n_sym, n_bar in test_matrix[:8]:  # Subset for long-short
        try:
            metrics = run_benchmark(
                n_sym, n_bar, AssetClass.EQUITY, allow_short=True, max_leverage=2.0
            )
            results.append(metrics)
        except Exception as e:
            print(f"  FAILED: {e}")
            results.append({"n_symbols": n_sym, "n_bars": n_bar, "error": str(e)})

    print()
    print("Running futures benchmarks...")
    futures_matrix = [(1, 252), (5, 252), (10, 252), (20, 252), (50, 252)]
    for n_sym, n_bar in futures_matrix:
        try:
            metrics = run_benchmark(
                n_sym, n_bar, AssetClass.FUTURE, allow_short=True, max_leverage=10.0
            )
            results.append(metrics)
        except Exception as e:
            print(f"  FAILED: {e}")
            results.append({"n_symbols": n_sym, "n_bars": n_bar, "error": str(e)})

    print()
    print("Running crypto benchmarks...")
    crypto_matrix = [(1, 252), (5, 252), (10, 252), (20, 252), (50, 252)]
    for n_sym, n_bar in crypto_matrix:
        try:
            metrics = run_benchmark(
                n_sym, n_bar, AssetClass.CRYPTO, allow_short=True, max_leverage=1.0
            )
            results.append(metrics)
        except Exception as e:
            print(f"  FAILED: {e}")
            results.append({"n_symbols": n_sym, "n_bars": n_bar, "error": str(e)})

    # Save results
    results_df = pd.DataFrame(results)
    output_path = Path(".experiments") / "backtest_perf_profile.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(output_path, index=False)

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Results saved to: {output_path}")
    print()
    print(
        results_df[
            ["n_symbols", "n_bars", "asset_class", "elapsed_seconds", "peak_memory_mb"]
        ].to_string(index=False)
    )

    # Quick scaling analysis
    print()
    print("SCALING ANALYSIS (equity, long-only, 1 year):")
    equity_1y = results_df[
        (results_df["asset_class"] == "equity")
        & (results_df["n_bars"] == 252)
        & (~results_df["allow_short"])
        & (results_df["elapsed_seconds"].notna())
    ].sort_values("n_symbols")
    if len(equity_1y) > 1:
        print(equity_1y[["n_symbols", "elapsed_seconds", "peak_memory_mb"]].to_string(index=False))
        # Check if roughly linear in symbols
        x = equity_1y["n_symbols"].values
        y = equity_1y["elapsed_seconds"].values
        if len(x) > 2:
            coeff = np.polyfit(x, y, 1)
            print(f"  Linear fit: time = {coeff[0]:.6f} * symbols + {coeff[1]:.4f}")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
