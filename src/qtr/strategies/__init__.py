"""Strategies package for QTR."""

from qtr.strategies.baselines import (
    STRATEGY_REGISTRY,
    buy_and_hold_signals,
    carry_signals,
    ewma_crossover_signals,
    get_strategy,
    mean_reversion_signals,
    momentum_signals,
    moving_average_crossover_signals,
    run_strategy,
    time_series_momentum_signals,
    vol_scaled_tsmom_signals,
)

__all__ = [
    "STRATEGY_REGISTRY",
    "buy_and_hold_signals",
    "carry_signals",
    "ewma_crossover_signals",
    "get_strategy",
    "mean_reversion_signals",
    "momentum_signals",
    "moving_average_crossover_signals",
    "run_strategy",
    "time_series_momentum_signals",
    "vol_scaled_tsmom_signals",
]