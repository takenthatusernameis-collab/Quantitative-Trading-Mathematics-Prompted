"""Statistical validation utilities for quantitative trading research."""
from qtr.validation.statistics import (
    bootstrap_sharpe_ci,
    bootstrap_metric_ci,
    walk_forward_splits,
    walk_forward_metrics,
    multiple_testing_correction,
    bonferroni_correction,
    benjamini_hochberg,
    paired_bootstrap_test,
    regime_classification,
    parameter_sensitivity,
    min_trades_for_sharpe,
)

__all__ = [
    "bootstrap_sharpe_ci",
    "bootstrap_metric_ci",
    "walk_forward_splits",
    "walk_forward_metrics",
    "multiple_testing_correction",
    "bonferroni_correction",
    "benjamini_hochberg",
    "paired_bootstrap_test",
    "regime_classification",
    "parameter_sensitivity",
    "min_trades_for_sharpe",
]
