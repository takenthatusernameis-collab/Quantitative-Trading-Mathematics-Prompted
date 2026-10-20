"""Statistical validation utilities for quantitative trading research."""

from qtr.validation.statistics import (
    annualized_sharpe,
    bars_per_year,
    bootstrap_confidence_interval,
    capacity_estimate,
    combinatorial_purged_cv,
    compare_to_benchmark,
    multiple_testing_correction,
    parameter_sensitivity,
    purged_kfold_splits,
    regime_analysis,
    sharpe_ratio,
    sharpe_ratio_ci,
    statistical_power_analysis,
    stressed_cost_test,
    validate_strategy,
    walk_forward_splits,
)

__all__ = [
    "annualized_sharpe",
    "bars_per_year",
    "bootstrap_confidence_interval",
    "capacity_estimate",
    "combinatorial_purged_cv",
    "compare_to_benchmark",
    "multiple_testing_correction",
    "parameter_sensitivity",
    "purged_kfold_splits",
    "regime_analysis",
    "sharpe_ratio",
    "sharpe_ratio_ci",
    "statistical_power_analysis",
    "stressed_cost_test",
    "validate_strategy",
    "walk_forward_splits",
]
