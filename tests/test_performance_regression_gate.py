"""Performance regression gate for the vectorized backtest engine.

Pins the profiling result from ``run_backtest_perf_profile.py``: an equity
long-only backtest over 100 symbols x 252 bars must complete in under 5
seconds with bounded peak memory. Any engine change that reintroduces a
quadratic (or worse) bottleneck fails this gate.

CI/CD hardening per STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §6 fallback path:
"CI/CD hardening — add performance regression gate (e.g., fail if
100-symbol backtest > 5s)". The gate runs on every push/PR through the
existing ``gates.yml`` pytest job (paths filter includes ``tests/**``).
"""

import gc
import sys
import time
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qtr.backtest.engine import AssetClass, BacktestConfig, run_backtest

# Regression gate thresholds, calibrated from run_backtest_perf_profile.py:
# 100 symbols x 252 bars (equity, long-only) measured ~2.3s / ~10MB locally.
MAX_ELAPSED_SECONDS = 5.0
MAX_PEAK_MEMORY_MB = 200.0


def _make_data(n_symbols: int, n_bars: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=n_bars, freq="1D")
    symbols = [f"SYM{i:04d}" for i in range(n_symbols)]

    returns = np.random.randn(n_bars, n_symbols) * 0.01
    market_factor = np.random.randn(n_bars) * 0.005
    for i in range(n_symbols):
        returns[:, i] += market_factor * 0.3
    prices = pd.DataFrame(100 * np.exp(np.cumsum(returns, axis=0)), index=dates, columns=symbols)

    signals = pd.DataFrame(
        np.clip(
            np.cumsum(np.random.randn(n_bars, n_symbols) * 0.1, axis=0) * 0.01,
            -1.0,
            1.0,
        ),
        index=dates,
        columns=symbols,
    )

    volumes = pd.DataFrame(
        np.random.lognormal(15, 0.5, size=(n_bars, n_symbols)).astype(int),
        index=dates,
        columns=symbols,
    )
    return prices, signals, volumes


def _config() -> BacktestConfig:
    config = BacktestConfig(
        initial_capital=1_000_000.0,
        asset_class=AssetClass.EQUITY,
        max_position_size=1.0,
        max_leverage=1.0,
        allow_short=False,
    )
    config.cost_model.equity_commission_bps = 1.0
    config.cost_model.equity_spread_bps = 1.0
    config.cost_model.equity_impact_bps_per_pct_adv = 0.1
    return config


def test_100_symbol_backtest_meets_performance_gate():
    """100 symbols x 252 bars must complete within the performance gate."""
    prices, signals, volumes = _make_data(100, 252)
    adv = volumes.rolling(20).mean().iloc[-1]
    config = _config()

    gc.collect()
    tracemalloc.start()
    start = time.perf_counter()
    result = run_backtest(prices=prices, signals=signals, volumes=volumes, adv=adv, config=config)
    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak / (1024 * 1024)
    assert elapsed < MAX_ELAPSED_SECONDS, (
        f"performance gate violated: {elapsed:.3f}s >= {MAX_ELAPSED_SECONDS}s"
    )
    assert peak_mb < MAX_PEAK_MEMORY_MB, (
        f"memory gate violated: {peak_mb:.1f}MB >= {MAX_PEAK_MEMORY_MB}MB"
    )
    assert result.metrics["num_trades"] > 0
