"""Strategies package for QTR."""

from qtr.strategies.baselines import (
    moving_average_crossover_signals,
    buy_and_hold_signals,
    ewma_crossover_signals,
    momentum_signals,
    mean_reversion_signals,
    time_series_momentum_signals,
    carry_signals,
    STRATEGY_REGISTRY,
    get_strategy,
    run_strategy,
)

__all__ = [
    "moving_average_crossover_signals",
    "buy_and_hold_signals",
    "ewma_crossover_signals",
    "momentum_signals",
    "mean_reversion_signals",
    "time_series_momentum_signals",
    "carry_signals",
    "STRATEGY_REGISTRY",
    "get_strategy",
    "run_strategy",
]