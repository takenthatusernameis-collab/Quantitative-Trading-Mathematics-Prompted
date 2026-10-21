"""Cross-module agreement between the engine and ``validate_strategy``.

**The problem.** The package computes several performance metrics twice: once
in ``qtr.backtest.engine.VectorizedBacktester._calculate_metrics`` and once in
``qtr.validation.statistics.validate_strategy``. The two implementations used
to disagree, and every published artifact shows it: each of the five artifacts
that carries engine-produced metrics publishes **two different Sharpes for one
run** -- the engine's under ``strategy_metrics`` and ``validate_strategy``'s
under ``validation``::

    exp_2026-10-10T17-05-58-697503Z
      strategy_metrics.sharpe =  0.6596071358231974   (sample std, ddof=1)
      validation.sharpe      =  0.6597383095613587   (population std, ddof=0)

The ratio is ``sqrt((n - 1) / n)`` in all five artifacts (n = 2,515 bars), i.e.
0.9998011730768697 -- the engine divided by the SAMPLE standard deviation
(pandas ``Series.std()``, ddof=1) while ``qtr.validation.statistics.sharpe_ratio``
divides by the POPULATION standard deviation (``numpy.ndarray.std()``, ddof=0).
This is the same class of defect as the ``total_return`` range of H38: one
package, one run, two numbers.

**The decision (and why this direction).** The record's convention is ddof=0.
The certified H10-H14 numbers come from the runners' ``sharpe_ratio`` calls,
and the gates are evaluated on those, so the *engine* is the side that had to
move; changing ``sharpe_ratio`` instead would move every certified number,
which is forbidden. The engine now divides by ``returns.std(ddof=0)``.

The change is a **uniform rescaling**: every Sharpe computed from the same
number of bars is multiplied by exactly ``sqrt(n / (n - 1))`` (1.000199 at
n = 2,515, i.e. +0.0199%). Therefore

* it cannot reorder two Sharpes compared on the same series (both sides get
  the same factor), so the runners' "beats benchmark" comparisons are
  unaffected; and
* no gate in the repository is evaluated on the engine's Sharpe (pinned by
  :class:`TestCertifiedNumbersUnaffected`), so no published verdict, gate
  threshold or certified number moves.

The published artifacts keep their pre-fix ``strategy_metrics`` values: they
are the historical record of the runs as executed, and they are pinned here
together with the exact formula of the difference.

**What this contract pins.**

* :class:`TestSharedMetricAgreement` -- the six metrics the package computes
  twice agree **exactly** between the engine and ``validate_strategy``.
* :class:`TestEngineOnlyMetrics` -- the metrics only the engine computes
  (Sortino, Calmar, max-drawdown duration, average trade cost) are pinned by
  their exact formula, and their absence from ``validate_strategy`` is
  asserted, so a second implementation appearing later is a visible change.
* :class:`TestSharpeConvention` -- the convention itself: the population-std
  formula, the exact ``sqrt(n / (n - 1))`` relation to the sample-std
  formula, the uniform-rescaling property, and the degenerate-series guard.
* :class:`TestPublishedArtifactAudit` -- the five artifacts pin both
  conventions, the ratio, the number of bars, and the reconstruction of each
  published Sharpe from the artifact's own equity curve.
* :class:`TestCertifiedNumbersUnaffected` -- the engine's Sharpe is not
  load-bearing for any published verdict.
* :class:`TestContractNegativeControl` -- the contract itself rejects the
  pre-fix convention, so it is not a tautology.
"""

from __future__ import annotations

import ast
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
ARTIFACTS = ROOT / ".experiments" / "artifacts"

from _utils_parquet import read_parquet_safe  # noqa: E402

from qtr.backtest.engine import (  # noqa: E402
    BacktestConfig,
    VectorizedBacktester,
    run_backtest,
)
from qtr.validation.statistics import (  # noqa: E402
    annualized_sharpe,
    bars_per_year,
    sharpe_ratio,
    validate_strategy,
)

# Artifacts whose summary.json carries engine-produced metrics.
MA_CROSSOVER = ARTIFACTS / "exp_2026-10-10T17-02-22-080026Z"
MA_CROSSOVER_2 = ARTIFACTS / "exp_2026-10-10T17-03-39-610858Z"
MA_CROSSOVER_3 = ARTIFACTS / "exp_2026-10-10T17-04-21-400695Z"
BUY_AND_HOLD = ARTIFACTS / "exp_2026-10-10T17-05-58-697503Z"
BUY_AND_HOLD_RERUN = ARTIFACTS / "exp_2026-10-14T08-26-02-537359Z"

ARTIFACT_DIRS = (MA_CROSSOVER, MA_CROSSOVER_2, MA_CROSSOVER_3, BUY_AND_HOLD, BUY_AND_HOLD_RERUN)

# H26's Sharpe-scale audit: it classified the standard-deviation convention
# of every audited family's published Sharpe, so the *direction* of the
# convention change is pinned to the committed record, not to an assertion
# made here.
H26_SUMMARY = ARTIFACTS / "h26_sharpe_scale" / "summary.json"
H9_ARTIFACT = ARTIFACTS / "exp_2026-10-11T16-52-38-694559Z"

# The metrics the package computes twice, under the same name in both places.
SHARED_METRICS = (
    "total_return",
    "annualized_return",
    "annualized_volatility",
    "sharpe",
    "max_drawdown",
    "profit_factor",
)

# The metrics only the engine computes. `validate_strategy` does not have them.
ENGINE_ONLY_METRICS = (
    "sortino",
    "calmar",
    "max_drawdown_duration",
    "avg_trade_cost",
)

# The runners whose published numbers are certified. None of them reads the
# engine's metrics: their Sharpes come from qtr.validation.statistics.
CERTIFIED_RUNNERS = (
    "run_h10_intraday_tsmom_pfopt_experiment.py",
    "run_h11_robustness_experiment.py",
    "run_h12_selection_bias_audit.py",
    "run_h13_oos_deflation_pf_audit.py",
    "run_h14_pf_margin_selection_audit.py",
    "run_h22_futures_tsmom_voltarget.py",
    "run_h25_futures_tsmom_pfmargin.py",
)


def _summary(directory: Path) -> dict:
    with open(directory / "summary.json") as f:
        return json.load(f)


def _equity(directory: Path, name: str = "equity_curve.parquet") -> pd.Series:
    df = read_parquet_safe(directory / name)
    return pd.Series(df[df.columns[0]].to_numpy(), index=df.index)


def _initial_capital(summary: dict) -> float:
    return float(summary["config"]["backtest"]["initial_capital"])


def _returns_from_equity(equity: pd.Series, initial_capital: float) -> pd.Series:
    """Reconstruct the engine's net return series from a published equity curve.

    The engine's curve is ``(1 + net_returns).cumprod() * initial_capital``, so
    the first bar's return is ``equity[0] / initial_capital - 1`` (the bar the
    pre-H38 metric dropped) and every later bar's return is its bar-over-bar
    growth.
    """
    returns = equity.pct_change()
    returns.iloc[0] = equity.iloc[0] / initial_capital - 1.0
    return returns


def _population_std_sharpe(returns: pd.Series) -> float:
    """The convention of qtr.validation.statistics.sharpe_ratio (ddof=0)."""
    values = np.asarray(returns.values, dtype=float)
    return float(values.mean() / values.std() * np.sqrt(252))


def _sample_std_sharpe(returns: pd.Series) -> float:
    """The engine's pre-fix convention (pandas Series.std(), ddof=1)."""
    return float(returns.mean() / returns.std() * np.sqrt(252))


def _assert_shared_metrics_agree(engine_metrics: dict, validation: dict) -> None:
    """The cross-module contract, as an executable function.

    It raises ``AssertionError`` on any disagreement, so the negative control
    can feed it the pre-fix metrics and require it to reject them.
    """
    for metric in SHARED_METRICS:
        assert metric in engine_metrics, f"engine does not compute {metric}"
        assert metric in validation, f"validate_strategy does not compute {metric}"
        engine_value = engine_metrics[metric]
        validation_value = validation[metric]
        if np.isnan(engine_value) and np.isnan(validation_value):
            continue
        if np.isfinite(engine_value) and np.isfinite(validation_value):
            assert engine_value == pytest.approx(validation_value, rel=1e-12, abs=1e-15), (
                f"{metric} disagrees: engine={engine_value!r}, validate_strategy={validation_value!r}"
            )
        else:
            assert engine_value == validation_value, (
                f"{metric} disagrees: engine={engine_value!r}, validate_strategy={validation_value!r}"
            )


def _engine_case(
    n: int = 60, drift: float = 0.001, seed: int = 12345, symbols: tuple[str, ...] = ("SPY",)
) -> tuple[pd.DataFrame, pd.DataFrame]:
    index = pd.bdate_range("2020-01-01", periods=n)
    rng = np.random.RandomState(seed)
    columns = {}
    for i, symbol in enumerate(symbols):
        rets = rng.normal(drift, 0.01, n)
        columns[symbol] = 100.0 * np.exp(np.cumsum(rets))
    prices = pd.DataFrame(columns, index=index)
    signals = pd.DataFrame({symbol: 1.0 for symbol in symbols}, index=index)
    return prices, signals


def _flat_case(n: int = 40) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A degenerate case: no price movement and no position at all."""
    index = pd.bdate_range("2020-01-01", periods=n)
    prices = pd.DataFrame({"SPY": 100.0}, index=index)
    signals = pd.DataFrame({"SPY": 0.0}, index=index)
    return prices, signals


def _run(
    prices: pd.DataFrame,
    signals: pd.DataFrame,
    capital: float = 1_000_000.0,
    allow_short: bool = False,
):
    config = BacktestConfig(initial_capital=capital, allow_short=allow_short)
    return run_backtest(prices=prices, signals=signals, config=config)


class TestSharedMetricAgreement:
    """Metrics computed by both the engine and validate_strategy must agree."""

    @pytest.mark.parametrize("seed", [1, 2, 3, 42, 123])
    def test_all_shared_metrics_agree_exactly(self, seed):
        prices, signals = _engine_case(seed=seed)
        result = _run(prices, signals)
        validation = validate_strategy(result.returns, result.trades, {})

        for metric in SHARED_METRICS:
            assert metric in result.metrics, f"Engine missing {metric}"
            assert metric in validation, f"validate_strategy missing {metric}"

        _assert_shared_metrics_agree(result.metrics, validation)

    @pytest.mark.parametrize("symbols", [("SPY",), ("SPY", "QQQ"), ("SPY", "QQQ", "IWM")])
    def test_agreement_holds_for_multi_symbol_portfolios(self, symbols):
        prices, signals = _engine_case(n=120, symbols=symbols, seed=7)
        result = _run(prices, signals)
        validation = validate_strategy(result.returns, result.trades, {})
        _assert_shared_metrics_agree(result.metrics, validation)

    def test_agreement_holds_for_a_short_portfolio(self):
        prices, signals = _engine_case(n=90, drift=-0.0005, seed=11)
        signals = -signals
        result = _run(prices, signals, allow_short=True)
        validation = validate_strategy(result.returns, result.trades, {})
        _assert_shared_metrics_agree(result.metrics, validation)

    def test_agreement_holds_for_a_degenerate_flat_series(self):
        """No movement and no position: every metric is a boundary value
        (zero volatility, infinite profit factor) and both implementations
        must return the same boundary."""
        prices, signals = _flat_case()
        result = _run(prices, signals)
        validation = validate_strategy(result.returns, result.trades, {})
        _assert_shared_metrics_agree(result.metrics, validation)
        assert result.metrics["sharpe"] == 0.0
        assert result.metrics["profit_factor"] == np.inf

    def test_agreement_holds_for_a_two_bar_series(self):
        """The smallest non-degenerate series (n = 2)."""
        prices, signals = _engine_case(n=2, seed=3)
        result = _run(prices, signals)
        validation = validate_strategy(result.returns, result.trades, {})
        _assert_shared_metrics_agree(result.metrics, validation)

    def test_agreement_holds_after_a_total_loss_bar(self):
        """A -100% bar drives the total return to -1 (gross == 0), the
        boundary of the annualization guard in both implementations.

        The bar is injected at the metric surface (`_calculate_metrics`),
        because a -100% *price* return needs a price of exactly zero, and
        the next bar's return would then be NaN or infinite.
        """
        backtester = VectorizedBacktester(BacktestConfig())
        empty_trades = pd.DataFrame(
            columns=["timestamp", "symbol", "side", "weight_change", "price", "cost"]
        )
        returns = pd.Series([0.001] * 9 + [-1.0] + [0.001] * 10)
        equity = (1.0 + returns).cumprod() * 1_000_000.0

        metrics = backtester._calculate_metrics(returns, equity, empty_trades)
        validation = validate_strategy(returns, empty_trades, {})

        _assert_shared_metrics_agree(metrics, validation)
        assert metrics["total_return"] == pytest.approx(-1.0, rel=1e-12)
        assert metrics["annualized_return"] == pytest.approx(-1.0, rel=1e-12)

    def test_num_trades_agrees_with_the_validation_counter(self):
        """`num_trades` (engine) and `n_trades` (validation) count the same
        rows of the same trades frame."""
        prices, signals = _engine_case(n=80, seed=5)
        signals.iloc[::20, 0] = 0.0  # a few round trips
        result = _run(prices, signals)
        validation = validate_strategy(result.returns, result.trades, {})
        assert result.metrics["num_trades"] == validation["n_trades"] == len(result.trades)


class TestEngineOnlyMetrics:
    """Metrics the engine computes alone are pinned by their exact formula."""

    def test_sortino_is_engine_only_and_pinned_by_its_formula(self):
        prices, signals = _engine_case(n=120, seed=13)
        result = _run(prices, signals)
        validation = validate_strategy(result.returns, result.trades, {})

        # The documented difference: `validate_strategy` has no Sortino.
        assert "sortino" in result.metrics
        assert "sortino" not in validation

        returns = result.returns
        shortfall = np.minimum(0, returns)
        downside_dev = float(np.sqrt(np.mean(shortfall**2)))
        assert downside_dev > 0
        expected = float(returns.mean() / downside_dev * np.sqrt(252))
        assert result.metrics["sortino"] == pytest.approx(expected, rel=1e-12)

    def test_sortino_denominator_is_the_population_style_downside_deviation(self):
        """The downside deviation is sqrt(mean(shortfall^2)) over the FULL
        series -- a population-style RMS, the same ddof convention as the
        Sharpe denominator -- not the standard deviation of the loss subset."""
        prices, signals = _engine_case(n=120, seed=17)
        result = _run(prices, signals)

        returns = result.returns
        downside_dev = float(np.sqrt(np.mean(np.minimum(0, returns) ** 2)))
        loss_std = float(returns[returns < 0].std())
        assert downside_dev != pytest.approx(loss_std, rel=1e-6)
        assert result.metrics["sortino"] == pytest.approx(
            float(returns.mean() / downside_dev * np.sqrt(252)), rel=1e-12
        )

    def test_calmar_is_engine_only_and_pinned_by_its_formula(self):
        prices, signals = _engine_case(n=90, seed=19)
        result = _run(prices, signals)
        validation = validate_strategy(result.returns, result.trades, {})

        assert "calmar" in result.metrics
        assert "calmar" not in validation

        expected = result.metrics["annualized_return"] / abs(result.metrics["max_drawdown"])
        assert result.metrics["calmar"] == pytest.approx(expected, rel=1e-12)

    def test_max_drawdown_duration_is_engine_only_and_pinned_by_its_formula(self):
        prices, signals = _engine_case(n=120, seed=23)
        result = _run(prices, signals)
        validation = validate_strategy(result.returns, result.trades, {})

        assert "max_drawdown_duration" in result.metrics
        assert "max_drawdown_duration" not in validation

        equity = result.equity_curve
        drawdown = (equity - equity.expanding().max()) / equity.expanding().max()
        in_dd = drawdown < 0
        groups = (in_dd != in_dd.shift()).cumsum()
        expected = int(in_dd.groupby(groups).sum().max()) if in_dd.any() else 0
        assert result.metrics["max_drawdown_duration"] == expected

    def test_avg_trade_cost_is_engine_only(self):
        prices, signals = _engine_case(n=60, seed=29)
        result = _run(prices, signals)
        validation = validate_strategy(result.returns, result.trades, {})

        assert "avg_trade_cost" in result.metrics
        assert "avg_trade_cost" not in validation
        assert result.metrics["avg_trade_cost"] == pytest.approx(
            float(result.trades["cost"].mean()), rel=1e-12
        )


class TestSharpeConvention:
    """The Sharpe convention itself, and the change that fixed it."""

    def test_engine_sharpe_uses_the_population_standard_deviation(self):
        prices, signals = _engine_case(n=120, seed=31)
        result = _run(prices, signals)

        returns = result.returns
        population = _population_std_sharpe(returns)
        sample = _sample_std_sharpe(returns)

        assert result.metrics["sharpe"] == pytest.approx(population, rel=1e-12)
        assert result.metrics["sharpe"] != pytest.approx(sample, rel=1e-9)

    def test_the_two_conventions_differ_by_exactly_sqrt_n_over_n_minus_1(self):
        prices, signals = _engine_case(n=120, seed=37)
        result = _run(prices, signals)

        returns = result.returns
        n = len(returns)
        population = _population_std_sharpe(returns)
        sample = _sample_std_sharpe(returns)

        assert population == pytest.approx(sample * math.sqrt(n / (n - 1)), rel=1e-12)

    def test_the_convention_change_is_a_uniform_rescaling(self):
        """The multiplier depends only on the number of bars, never on the
        returns, so every Sharpe of the same length is rescaled by the same
        factor and the ORDER of two Sharpes is preserved exactly."""
        rng = np.random.default_rng(41)
        for n in (30, 252, 2515):
            returns = pd.Series(rng.normal(0.0004, 0.01, n))
            population = _population_std_sharpe(returns)
            sample = _sample_std_sharpe(returns)
            assert population / sample == pytest.approx(math.sqrt(n / (n - 1)), rel=1e-12)

    def test_a_regression_can_never_reorder_two_sharpes_of_the_same_length(self):
        """The runners' "beats benchmark" comparison puts two engine Sharpes
        on either side; the convention change cannot flip it."""
        prices, signals = _engine_case(n=252, seed=43)
        benchmark = _run(prices, signals)

        weak_signals = signals.copy()
        weak_signals.iloc[::2, 0] = 0.0
        strategy = _run(prices, weak_signals)

        for engine_sharpe, returns in (
            (strategy.metrics["sharpe"], strategy.returns),
            (benchmark.metrics["sharpe"], benchmark.returns),
        ):
            assert len(returns) == len(benchmark.returns)

        assert (strategy.metrics["sharpe"] > benchmark.metrics["sharpe"]) == (
            _sample_std_sharpe(strategy.returns) > _sample_std_sharpe(benchmark.returns)
        )

    def test_a_degenerate_series_does_not_produce_a_garbage_sharpe(self):
        """A constant return series has a standard deviation of ~1e-19 from
        float noise, not exactly 0.0. The engine must apply the same
        tolerance guard as `sharpe_ratio` (1e-15) instead of dividing by
        ~1e-19 and reporting a Sharpe of ~1e16."""
        backtester = VectorizedBacktester(BacktestConfig())
        empty_trades = pd.DataFrame(
            columns=["timestamp", "symbol", "side", "weight_change", "price", "cost"]
        )
        returns = pd.Series([0.001] * 10)
        equity = (1.0 + returns).cumprod() * 1_000_000.0

        metrics = backtester._calculate_metrics(returns, equity, empty_trades)
        validation = validate_strategy(returns, empty_trades, {})

        assert metrics["sharpe"] == 0.0
        assert validation["sharpe"] == 0.0
        assert abs(metrics["sharpe"]) < 1e6  # not the ~7.3e16 garbage value

    def test_the_degenerate_series_agrees_with_validate_strategy(self):
        backtester = VectorizedBacktester(BacktestConfig())
        empty_trades = pd.DataFrame(
            columns=["timestamp", "symbol", "side", "weight_change", "price", "cost"]
        )
        for constant in (0.001, 0.002, 0.0005):
            returns = pd.Series([constant] * 20)
            equity = (1.0 + returns).cumprod() * 1_000_000.0
            metrics = backtester._calculate_metrics(returns, equity, empty_trades)
            validation = validate_strategy(returns, empty_trades, {})
            assert metrics["sharpe"] == validation["sharpe"] == 0.0


class TestAnnualizedSharpeVariant:
    """The package's third Sharpe: the bar-frequency annualization.

    ``qtr.validation.statistics.annualized_sharpe`` scales by the bar
    frequency implied by the index, while ``sharpe_ratio`` and the engine
    scale by a fixed 252. The two differ by exactly ``sqrt(bpy / 252)``; this
    is a documented difference, not a disagreement.
    """

    def test_annualized_sharpe_scales_by_the_index_bar_frequency(self):
        index = pd.bdate_range("2015-01-01", "2024-12-31")
        rng = np.random.default_rng(47)
        returns = pd.Series(rng.normal(0.0004, 0.01, len(index)), index=index)

        bpy = bars_per_year(index)
        span_days = (index[-1] - index[0]).total_seconds() / 86400.0
        assert bpy == pytest.approx(len(index) / (span_days / 365.25), rel=1e-12)
        assert annualized_sharpe(returns, index) == pytest.approx(
            sharpe_ratio(returns.values, periods_per_year=bpy), rel=1e-12
        )
        assert annualized_sharpe(returns, index) == pytest.approx(
            sharpe_ratio(returns.values, periods_per_year=252) * math.sqrt(bpy / 252), rel=1e-12
        )

    def test_the_documented_difference_is_bounded_for_the_published_horizon(self):
        """Over the artifacts' own horizon the two annualizations differ by
        less than 0.1%, so the choice of convention cannot move a verdict."""
        equity = _equity(MA_CROSSOVER)
        bpy = bars_per_year(equity.index)
        assert bpy == pytest.approx(251.672, abs=0.01)
        assert math.sqrt(bpy / 252) == pytest.approx(0.99935, abs=1e-4)
        assert abs(math.sqrt(bpy / 252) - 1.0) < 0.001


class TestPublishedArtifactAudit:
    """The committed artifacts pin both conventions and their disagreement."""

    @pytest.mark.parametrize("directory", ARTIFACT_DIRS, ids=lambda d: d.name)
    def test_each_artifact_publishes_two_sharpes_for_one_run(self, directory):
        summary = _summary(directory)
        published = summary["strategy_metrics"]["sharpe"]
        validation = summary["validation"]["sharpe"]

        assert published != validation

        returns = _returns_from_equity(_equity(directory), _initial_capital(summary))
        n = len(returns)
        assert n == 2515
        assert published / validation == pytest.approx(math.sqrt((n - 1) / n), rel=1e-12)
        assert published / validation == pytest.approx(0.9998011730768697, rel=1e-12)

    @pytest.mark.parametrize("directory", ARTIFACT_DIRS, ids=lambda d: d.name)
    def test_the_published_engine_sharpe_is_the_sample_std_convention(self, directory):
        """The pre-fix `strategy_metrics` value is reproducible ONLY with the
        sample standard deviation -- that is what the engine computed."""
        summary = _summary(directory)
        returns = _returns_from_equity(_equity(directory), _initial_capital(summary))
        published = summary["strategy_metrics"]["sharpe"]

        assert published == pytest.approx(_sample_std_sharpe(returns), rel=1e-12)
        assert published != pytest.approx(_population_std_sharpe(returns), rel=1e-9)

    @pytest.mark.parametrize("directory", ARTIFACT_DIRS, ids=lambda d: d.name)
    def test_the_published_validation_sharpe_is_the_population_std_convention(self, directory):
        """The `validation` block is reproducible ONLY with the population
        standard deviation -- the convention the engine now adopts."""
        summary = _summary(directory)
        returns = _returns_from_equity(_equity(directory), _initial_capital(summary))
        published = summary["validation"]["sharpe"]

        assert published == pytest.approx(_population_std_sharpe(returns), rel=1e-12)
        assert published != pytest.approx(_sample_std_sharpe(returns), rel=1e-9)

    @pytest.mark.parametrize("directory", ARTIFACT_DIRS, ids=lambda d: d.name)
    def test_the_convention_change_effect_on_the_published_sharpes_is_bounded(self, directory):
        """Re-running an artifact with the corrected engine would raise its
        Sharpe by exactly sqrt(n / (n - 1)) - 1 = 0.0199%. The published
        values stay as they are."""
        summary = _summary(directory)
        published = summary["strategy_metrics"]["sharpe"]
        n = 2515
        relative_change = math.sqrt(n / (n - 1)) - 1.0

        assert relative_change == pytest.approx(0.0001988, abs=1e-6)
        assert relative_change < 0.001  # bounded: 0.02% of the Sharpe
        assert summary["validation"]["sharpe"] == pytest.approx(
            published * (1.0 + relative_change), rel=1e-9
        )

    def test_the_benchmark_block_carries_the_pre_fix_convention(self):
        """The benchmark block has no validation counterpart, so its
        pre-fix Sharpe was invisible in the artifact."""
        summary = _summary(MA_CROSSOVER)
        capital = _initial_capital(summary)
        benchmark_equity = _equity(MA_CROSSOVER, "benchmark_equity.parquet")
        returns = _returns_from_equity(benchmark_equity, capital)
        published = summary["benchmark_metrics"]["sharpe"]

        assert published == pytest.approx(_sample_std_sharpe(returns), rel=1e-12)
        assert published != pytest.approx(_population_std_sharpe(returns), rel=1e-9)

    def test_the_published_volatility_keeps_the_sample_std_convention(self):
        """`annualized_volatility` is NOT changed: the record uses the sample
        standard deviation for it, and the artifacts agree with
        `validate_strategy` on it to the last digit."""
        for directory in ARTIFACT_DIRS:
            summary = _summary(directory)
            returns = _returns_from_equity(_equity(directory), _initial_capital(summary))
            published = summary["strategy_metrics"]["annualized_volatility"]

            assert published == pytest.approx(float(returns.std() * np.sqrt(252)), rel=1e-12)
            assert published == pytest.approx(
                summary["validation"]["annualized_volatility"], rel=1e-12
            )
            assert published != pytest.approx(
                float(np.asarray(returns.values).std() * np.sqrt(252)), rel=1e-9
            )


def _engine_sharpe_reads(node: ast.AST) -> bool:
    """True when the node reads ``<something>.metrics['sharpe']``."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Subscript) and ast.unparse(sub).endswith(".metrics['sharpe']"):
            return True
    return False


def _engine_sharpe_names(tree: ast.AST) -> set[str]:
    """Names assigned from an engine-Sharpe read inside the same module.

    The assignment chain is followed to a fixpoint, because the runners
    assign the metric to a local name and then to the accumulator
    (``sharpe = result.metrics["sharpe"]`` ... ``best_sharpe = sharpe``).
    """
    names: set[str] = set()
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            value_is_engine = _engine_sharpe_reads(node.value) or (
                isinstance(node.value, ast.Name) and node.value.id in names
            )
            if not value_is_engine:
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id not in names:
                    names.add(target.id)
                    changed = True
    return names


def _numeric_threshold(node: ast.AST) -> float | None:
    """The finite numeric threshold a node represents, if any.

    Infinities are sentinels -- e.g. the ``-np.inf`` a best-so-far
    accumulator starts at -- and are not thresholds: no convention change can
    flip a comparison against them.
    """
    value: float | None = None
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    ):
        value = float(node.value)
    elif (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, ast.USub)
        and isinstance(node.operand, ast.Constant)
        and isinstance(node.operand.value, (int, float))
        and not isinstance(node.operand.value, bool)
    ):
        value = -float(node.operand.value)
    if value is None or not math.isfinite(value):
        return None
    return value


class TestCertifiedNumbersUnaffected:
    """The engine's Sharpe must not be load-bearing for any published verdict."""

    def test_the_certified_runners_do_not_read_the_engine_sharpe(self):
        """The certified H10-H14/H22/H25 numbers come from
        `qtr.validation.statistics.sharpe_ratio` (ddof=0), never from the
        engine's metric, so the engine's convention cannot move them."""
        for name in CERTIFIED_RUNNERS:
            source = (ROOT / name).read_text()
            assert "metrics['sharpe']" not in source, f"{name} reads the engine's Sharpe"
            assert 'metrics["sharpe"]' not in source, f"{name} reads the engine's Sharpe"
            assert "sharpe_ratio" in source, f"{name} must use the record's sharpe_ratio"

    def test_the_published_family_sharpes_are_population_ddof0(self):
        """The direction of the convention change is pinned to the committed
        record: H26's audit classified the standard-deviation convention of
        every audited family's published Sharpe, and every one of them is the
        POPULATION (ddof=0) convention, bit-exactly. The engine was the only
        implementation in the package that did not use it."""
        with open(H26_SUMMARY) as f:
            summary = json.load(f)

        audited = summary["audited"]
        assert audited
        for entry in audited:
            check = entry["sharpe_convention_check"]
            assert check["published_convention"] == "population_ddof0", entry["family"]
            assert check["abs_diff_ddof0"] == 0.0, entry["family"]
            assert check["abs_diff_ddof1"] > 0.0, entry["family"]

        families = {entry["family"] for entry in audited}
        assert {"H10", "H21", "H22", "H23", "H25"} <= families

    def test_h9_is_the_one_published_sharpe_on_the_sample_convention(self):
        """Disclosure: H26 excluded H9 because its published OOS Sharpe
        reproduces only under the SAMPLE (ddof=1) convention -- it predates
        the library's switch to numpy. The gap is 1.03e-4 and H9's margin
        above its own 1.0 Sharpe gate is 55x larger, so the verdict cannot
        move; the published row is a REJECT on the profit factor anyway."""
        with open(H26_SUMMARY) as f:
            summary = json.load(f)

        excluded = {entry["family"]: entry for entry in summary["excluded"]}
        assert "H9" in excluded
        check = excluded["H9"]["sharpe_convention_check"]
        assert check["published_convention"] == "sample_ddof1"
        assert check["abs_diff_ddof1"] == 0.0
        assert check["abs_diff_ddof0"] == pytest.approx(0.00010261624157736904, rel=1e-9)

        # The margin above H9's pre-registered 1.0 Sharpe gate dwarfs the
        # convention gap, so neither convention can flip the gate.
        assert check["sharpe_population_ddof0"] - 1.0 > 10 * check["abs_diff_ddof0"]

        with open(H9_ARTIFACT / "summary.json") as f:
            h9 = json.load(f)
        assert h9["metrics"]["oos_sharpe"] == pytest.approx(check["sharpe_sample_ddof1"], rel=1e-9)
        assert h9["passes"]["pf"] is False
        assert h9["verdict"] == "REJECT"

    def test_no_runner_gates_on_the_engine_sharpe(self):
        """No runner compares an engine Sharpe against a finite numeric
        threshold, so the convention change cannot flip a gate."""
        offenders = []
        for runner in sorted(ROOT.glob("run_*.py")):
            tree = ast.parse(runner.read_text())
            names = _engine_sharpe_names(tree)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Compare):
                    continue
                sides = [node.left, *node.comparators]
                for left, right in zip(sides, sides[1:]):
                    for engine_side, other_side in ((left, right), (right, left)):
                        is_engine_value = _engine_sharpe_reads(engine_side) or (
                            isinstance(engine_side, ast.Name) and engine_side.id in names
                        )
                        if is_engine_value and _numeric_threshold(other_side) is not None:
                            offenders.append(f"{runner.name}:{node.lineno}")
        assert offenders == []

    def test_every_engine_sharpe_comparison_is_engine_against_engine(self):
        """The only comparisons of engine Sharpes put two of them on either
        side (the "beats benchmark" checks) or against an infinity sentinel
        (an uninitialised accumulator), so the uniform rescaling cannot flip
        them."""
        comparisons = []
        for runner in sorted(ROOT.glob("run_*.py")):
            tree = ast.parse(runner.read_text())
            names = _engine_sharpe_names(tree)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Compare):
                    continue
                sides = [node.left, *node.comparators]
                for left, right in zip(sides, sides[1:]):
                    left_is = _engine_sharpe_reads(left) or (
                        isinstance(left, ast.Name) and left.id in names
                    )
                    right_is = _engine_sharpe_reads(right) or (
                        isinstance(right, ast.Name) and right.id in names
                    )
                    if left_is or right_is:
                        other = right if left_is else left
                        comparisons.append(
                            (runner.name, node.lineno, left_is, right_is, _numeric_threshold(other))
                        )

        assert comparisons, "the comparison inventory is empty -- something changed"
        for name, lineno, left_is, right_is, threshold in comparisons:
            if left_is and right_is:
                continue
            assert threshold is None, f"{name}:{lineno} compares an engine Sharpe with a threshold"


class TestContractNegativeControl:
    """The contract must reject the pre-fix convention."""

    def test_the_contract_rejects_the_pre_fix_sharpe(self):
        prices, signals = _engine_case(n=120, seed=53)
        result = _run(prices, signals)
        validation = validate_strategy(result.returns, result.trades, {})

        # The contract holds for the corrected engine ...
        _assert_shared_metrics_agree(result.metrics, validation)

        # ... and rejects the pre-fix metric.
        pre_fix = dict(result.metrics)
        pre_fix["sharpe"] = _sample_std_sharpe(result.returns)
        assert pre_fix["sharpe"] != result.metrics["sharpe"]
        with pytest.raises(AssertionError, match="sharpe disagrees"):
            _assert_shared_metrics_agree(pre_fix, validation)

    def test_the_contract_rejects_a_pre_fix_total_return(self):
        """The H38 defect must also be caught by this contract."""
        prices, signals = _engine_case(n=120, seed=59)
        result = _run(prices, signals)
        validation = validate_strategy(result.returns, result.trades, {})

        pre_fix = dict(result.metrics)
        pre_fix["total_return"] = float(
            result.equity_curve.iloc[-1] / result.equity_curve.iloc[0] - 1.0
        )
        with pytest.raises(AssertionError, match="total_return disagrees"):
            _assert_shared_metrics_agree(pre_fix, validation)
