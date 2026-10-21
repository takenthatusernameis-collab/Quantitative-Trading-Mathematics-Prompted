"""Cross-module agreement between the engine and ``validate_strategy``.

This contract extends the H38 ``total_return`` fix: every metric the package
computes twice must agree exactly, or any documented difference must be pinned
with its exact formula and bounded effect.

The Sharpe/volatility convention was changed to population std (ddof=0) in
``src/qtr/backtest/engine.py`` to match ``qtr.validation.statistics.sharpe_ratio``
and ``validate_strategy`` (ddof=0). That matches the record convention used
by certified H10–H14 numbers; the change is uniform so it cannot flip
"beats benchmark" comparisons that compare two engine metrics.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
ARTIFACTS = ROOT / ".experiments" / "artifacts"

from _utils_parquet import read_parquet_safe  # noqa: E402

from qtr.backtest.engine import BacktestConfig, run_backtest  # noqa: E402
from qtr.validation.statistics import validate_strategy  # noqa: E402

# Artifacts whose summary.json carries engine-produced metrics.
MA_CROSSOVER = ARTIFACTS / "exp_2026-10-10T17-02-22-080026Z"
MA_CROSSOVER_2 = ARTIFACTS / "exp_2026-10-10T17-03-39-610858Z"
MA_CROSSOVER_3 = ARTIFACTS / "exp_2026-10-10T17-04-21-400695Z"
BUY_AND_HOLD = ARTIFACTS / "exp_2026-10-10T17-05-58-697503Z"
BUY_AND_HOLD_RERUN = ARTIFACTS / "exp_2026-10-14T08-26-02-537359Z"


def _summary(directory: Path) -> dict:
    with open(directory / "summary.json") as f:
        return json.load(f)


def _equity(directory: Path, name: str = "equity_curve.parquet") -> pd.Series:
    df = read_parquet_safe(directory / name)
    return pd.Series(df[df.columns[0]].to_numpy(), index=df.index)


def _initial_capital(summary: dict) -> float:
    return float(summary["config"]["backtest"]["initial_capital"])


def _engine_case(
    n: int = 60, drift: float = 0.001, seed: int = 12345
) -> tuple[pd.DataFrame, pd.DataFrame]:
    index = pd.bdate_range("2020-01-01", periods=n)
    rng = np.random.RandomState(seed)
    rets = rng.normal(drift, 0.01, n)
    prices = pd.DataFrame({"SPY": 100.0 * np.exp(np.cumsum(rets))}, index=index)
    signals = pd.DataFrame({"SPY": 1.0}, index=index)
    return prices, signals


def _run(prices: pd.DataFrame, signals: pd.DataFrame, capital: float = 1_000_000.0):
    config = BacktestConfig(initial_capital=capital)
    return run_backtest(prices=prices, signals=signals, config=config)


class TestMetricAgreement:
    """Metrics computed by both the engine and validate_strategy must agree."""

    @pytest.mark.parametrize("seed", [1, 2, 3, 42, 123])
    def test_all_shared_metrics_agree_exactly(self, seed):
        prices, signals = _engine_case(seed=seed)
        result = _run(prices, signals)
        validation = validate_strategy(result.returns, result.trades, {})

        # Metrics computed twice - must agree exactly
        shared_metrics = [
            "total_return",
            "annualized_return",
            "annualized_volatility",
            "sharpe",
            "max_drawdown",
            "profit_factor",
        ]
        for metric in shared_metrics:
            assert metric in result.metrics, f"Engine missing {metric}"
            assert metric in validation, f"validate_strategy missing {metric}"
            eng_val = result.metrics[metric]
            val_val = validation[metric]
            # Allow for float precision
            if np.isfinite(eng_val) and np.isfinite(val_val):
                assert eng_val == pytest.approx(val_val, rel=1e-12, abs=1e-15), (
                    f"{metric} disagrees: engine={eng_val}, validate_strategy={val_val}"
                )
            else:
                assert eng_val == val_val

    def test_sortino_only_in_engine_documented(self):
        """Sortino is computed only by the engine (not by validate_strategy)."""
        prices, signals = _engine_case()
        result = _run(prices, signals)
        validation = validate_strategy(result.returns, result.trades, {})
        assert "sortino" in result.metrics
        assert "sortino" not in validation
