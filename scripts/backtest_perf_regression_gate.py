#!/usr/bin/env python3
"""
Backtest engine performance regression gate.

Fails (exit != 0) if a 100-symbol x 252-bar equity backtest exceeds 5.0s.
This is the CI/CD hardening item from STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md
§6 fallback path: "CI/CD hardening - performance regression gate".

The gate is intentionally conservative: local baseline for 100 symbols x 252
bars is ~2.5s, so the 5.0s threshold has ~2x headroom and only triggers on a
real regression (e.g. an accidental O(n^2) path in the engine).

Does not touch src/qtr, tests, frozen contracts, or any published artifact.
"""

import gc
import sys
import time
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from qtr.backtest.engine import AssetClass, BacktestConfig, CostModel, run_backtest

# Threshold in seconds for a 100-symbol x 252-bar backtest.
MAX_ELAPSED_SECONDS = 5.0
N_SYMBOLS = 100
N_BARS = 252


def generate_data(n_symbols: int, n_bars: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(42)
    dates = pd.date_range("2020-01-01", periods=n_bars, freq="1D")
    symbols = [f"SYM{i:04d}" for i in range(n_symbols)]
    returns = rng.normal(0.0, 0.01, size=(n_bars, n_symbols))
    market = rng.normal(0.0, 0.005, size=n_bars)
    for i in range(n_symbols):
        returns[:, i] += market * 0.3
    prices = pd.DataFrame(100.0 * np.exp(np.cumsum(returns, axis=0)), index=dates, columns=symbols)
    volumes = pd.DataFrame(
        np.random.default_rng(7).lognormal(15, 0.5, size=(n_bars, n_symbols)).astype(int),
        index=dates,
        columns=symbols,
    )
    return prices, volumes


def main() -> int:
    prices, volumes = generate_data(N_SYMBOLS, N_BARS)
    signals = pd.DataFrame(
        np.clip(
            np.cumsum(np.random.default_rng(123).normal(0.0, 0.1, size=(N_BARS, N_SYMBOLS)), axis=0)
            * 0.01,
            -1.0,
            1.0,
        ),
        index=prices.index,
        columns=prices.columns,
    )
    adv = volumes.rolling(20).mean().iloc[-1]

    config = BacktestConfig(
        initial_capital=1_000_000.0,
        asset_class=AssetClass.EQUITY,
        max_position_size=1.0,
        max_leverage=1.0,
        allow_short=False,
    )
    config.cost_model = CostModel(
        equity_commission_bps=1.0,
        equity_spread_bps=1.0,
        equity_impact_bps_per_pct_adv=0.1,
    )

    gc.collect()
    tracemalloc.start()
    start = time.perf_counter()
    result = run_backtest(prices=prices, signals=signals, volumes=volumes, adv=adv, config=config)
    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    trades = result.metrics.get("num_trades", 0)
    print(
        f"PERF GATE: {N_SYMBOLS} symbols x {N_BARS} bars -> "
        f"{elapsed:.3f}s (limit {MAX_ELAPSED_SECONDS:.0f}s), "
        f"{peak / (1024 * 1024):.1f}MB peak, {trades:.0f} trades"
    )

    if elapsed > MAX_ELAPSED_SECONDS:
        print(f"PERF GATE FAILED: {elapsed:.3f}s > {MAX_ELAPSED_SECONDS:.0f}s limit")
        return 1
    print("PERF GATE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
