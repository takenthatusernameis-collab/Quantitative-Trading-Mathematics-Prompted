"""Statistical validation utilities for quantitative trading research."""
from qtr.validation.statistics import (
    bootstrap_confidence_interval,
    capacity_estimate,
    compare_to_benchmark,
    multiple_testing_correction,
    parameter_sensitivity,
    regime_analysis,
    sharpe_ratio,
    sharpe_ratio_ci,
    statistical_power_analysis,
    stressed_cost_test,
    validate_strategy,
    walk_forward_splits,
)

__all__ = [
    "bootstrap_confidence_interval",
    "capacity_estimate",
    "compare_to_benchmark",
    "multiple_testing_correction",
    "parameter_sensitivity",
    "regime_analysis",
    "sharpe_ratio",
    "sharpe_ratio_ci",
    "statistical_power_analysis",
    "stressed_cost_test",
    "validate_strategy",
    "walk_forward_splits",
]