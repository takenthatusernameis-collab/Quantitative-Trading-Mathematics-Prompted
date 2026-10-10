"""Statistical validation utilities for quantitative trading research."""
from qtr.validation.statistics import (
    bootstrap_confidence_interval,
    sharpe_ratio,
    sharpe_ratio_ci,
    walk_forward_splits,
    multiple_testing_correction,
    parameter_sensitivity,
    regime_analysis,
    stressed_cost_test,
    capacity_estimate,
    compare_to_benchmark,
    statistical_power_analysis,
    validate_strategy,
)

__all__ = [
    "bootstrap_confidence_interval",
    "sharpe_ratio",
    "sharpe_ratio_ci",
    "walk_forward_splits",
    "multiple_testing_correction",
    "parameter_sensitivity",
    "regime_analysis",
    "stressed_cost_test",
    "capacity_estimate",
    "compare_to_benchmark",
    "statistical_power_analysis",
    "validate_strategy",
]