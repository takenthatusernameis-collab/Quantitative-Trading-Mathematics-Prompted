"""The engine's ``total_return`` must span every bar of the return series.

**The defect (fixed in ``src/qtr/backtest/engine.py``).** ``_calculate_metrics``
measured the total return from ``equity.iloc[0]`` to ``equity.iloc[-1]``. That
range covers only the *last* ``n - 1`` compounding periods: the first bar is
dropped, and the first bar is the only bar on which the engine charges the
initial entry cost (``position_changes = signals.diff().fillna(signals.iloc[0])``).
The metric therefore

1. disagreed with ``qtr.validation.statistics.validate_strategy`` on the very
   same return series (the engine covered ``n - 1`` returns, ``validate_strategy``
   covers ``n`` via ``(1 + returns).prod() - 1``), and
2. was blind to the dominant term of the cost model.

**Evidence (both points are pinned by the tests below).**

* *One artifact, two numbers.* ``exp_2026-10-10T17-05-58-697503Z`` publishes
  ``strategy_metrics.total_return = 1.863359741396068`` **and**
  ``validation.total_return = 1.7456586208201519`` for the *same* run: the
  first is the engine's (pre-fix) value, the second is ``validate_strategy``'s.
  They differ by 11.77 percentage points, and the difference is exactly the
  first bar's entry cost (4.11% of capital in that artifact).
* *Blind to the cost-model fix.* The same buy-and-hold run was re-executed on
  2026-10-14 (``exp_2026-10-14T08-26-02-537359Z``) after the cost-model fix
  cut the per-trade cost from 4.11% to 0.02% of capital. The published
  ``total_return`` (1.86335974139...) and ``annualized_return``
  (0.11116466309...) are *identical to 13 significant digits* in both
  artifacts, because the entire cost difference sits on the first bar, which
  the metric dropped. The corrected metric (from the initial capital) does
  see it: 1.7457 vs 1.8628, i.e. 11.77 percentage points apart.

**The correction.** ``total_return`` is now the total return of the strategy's
own equity curve measured from the initial capital:
``equity.iloc[-1] / initial_capital - 1``. That is exactly the value the
committed artifacts already publish under their ``validation`` block, so the
fix aligns the engine with the published record rather than contradicting it.
The pre-fix ``strategy_metrics``/``benchmark_metrics`` values of the five
affected artifacts are *history* -- they are left untouched and pinned here, so
that a silent change to either convention is caught.

**What is deliberately not changed.** ``run_h18_overnight_intraday_experiment.py``
carries its own copy of the pre-fix convention (``equity.iloc[-1] /
equity.iloc[0] - 1``) for the runner-local ``total_return`` it publishes. The
H18 artifacts are frozen, so the copy stays and is disclosed instead (see
``TestRemainingDisclosures``); H18's gates do not use ``total_return``.
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
H18 = ARTIFACTS / "exp_2026-10-13T22-14-50-729923Z"


def _summary(directory: Path) -> dict:
    with open(directory / "summary.json") as f:
        return json.load(f)


def _equity(directory: Path, name: str = "equity_curve.parquet") -> pd.Series:
    df = read_parquet_safe(directory / name)
    return pd.Series(df[df.columns[0]].to_numpy(), index=df.index)


def _initial_capital(summary: dict) -> float:
    return float(summary["config"]["backtest"]["initial_capital"])


def _engine_case(n: int = 60, drift: float = 0.001) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A fully invested, monotonically rising single-symbol case.

    The position is nonzero from the first bar, so the engine charges the
    entry cost (2 bps for equities without ADV data) on bar 0 -- the bar the
    pre-fix metric dropped.
    """
    index = pd.bdate_range("2020-01-01", periods=n)
    prices = pd.DataFrame({"SPY": 100.0 * (1.0 + drift) ** np.arange(n)}, index=index)
    signals = pd.DataFrame({"SPY": 1.0}, index=index)
    return prices, signals


def _run(prices: pd.DataFrame, signals: pd.DataFrame, capital: float = 1_000_000.0):
    config = BacktestConfig(initial_capital=capital)
    return run_backtest(prices=prices, signals=signals, config=config)


class TestEngineTotalReturnContract:
    """The engine's metric must agree with its own equity curve."""

    def test_total_return_is_measured_from_the_initial_capital(self):
        prices, signals = _engine_case()
        result = _run(prices, signals)

        equity = result.equity_curve
        expected = equity.iloc[-1] / result.config.initial_capital - 1.0
        assert result.metrics["total_return"] == pytest.approx(expected, rel=1e-12, abs=1e-15)

    def test_total_return_equals_the_full_return_product(self):
        """The metric must span *every* bar, i.e. the whole return series."""
        prices, signals = _engine_case()
        result = _run(prices, signals)

        expected = float((1.0 + result.returns).prod() - 1.0)
        assert result.metrics["total_return"] == pytest.approx(expected, rel=1e-12, abs=1e-15)

    def test_pre_fix_formula_is_detected(self):
        """Negative control: the pre-fix range (equity[0] -> equity[-1]) must
        NOT be what the engine reports, or the defect would be back."""
        prices, signals = _engine_case()
        result = _run(prices, signals)

        equity = result.equity_curve
        pre_fix = equity.iloc[-1] / equity.iloc[0] - 1.0
        assert result.metrics["total_return"] != pytest.approx(pre_fix, rel=1e-9, abs=1e-12)
        # ... and the difference is exactly the first bar's entry cost.
        entry_cost = 1.0 - equity.iloc[0] / result.config.initial_capital
        assert entry_cost == pytest.approx(0.0002, rel=1e-9)
        assert 1.0 + result.metrics["total_return"] == pytest.approx(
            (equity.iloc[0] / result.config.initial_capital) * (1.0 + pre_fix), rel=1e-12
        )

    def test_total_return_agrees_with_validate_strategy(self):
        """The two metric functions in the same package must not disagree."""
        prices, signals = _engine_case()
        result = _run(prices, signals)

        validation = validate_strategy(result.returns, result.trades, {})
        assert result.metrics["total_return"] == pytest.approx(
            validation["total_return"], rel=1e-12, abs=1e-15
        )

    def test_annualized_return_uses_the_same_horizon_as_total_return(self):
        """``annualized_return`` must be the n-period annualization of the
        n-period total return, so the pair is invertible."""
        prices, signals = _engine_case()
        result = _run(prices, signals)

        n_periods = len(result.returns)
        total = result.metrics["total_return"]
        ann = result.metrics["annualized_return"]

        assert ann == pytest.approx((1.0 + total) ** (252.0 / n_periods) - 1.0, rel=1e-12)
        assert (1.0 + ann) ** (n_periods / 252.0) == pytest.approx(1.0 + total, rel=1e-12)

    def test_zero_first_bar_signal_is_unaffected(self):
        """Control: when the first bar carries no position (no entry cost),
        both conventions coincide -- the metric is not over-strict."""
        prices, signals = _engine_case()
        signals.iloc[0, 0] = 0.0
        result = _run(prices, signals)

        equity = result.equity_curve
        pre_fix = equity.iloc[-1] / equity.iloc[0] - 1.0
        assert result.metrics["total_return"] == pytest.approx(pre_fix, rel=1e-12, abs=1e-15)


class TestPublishedArtifactAudit:
    """The committed artifacts pin both conventions and their disagreement."""

    def test_ma_crossover_artifacts_have_no_first_bar_entry_cost(self):
        """The MA-crossover artifacts start flat, so both conventions agree."""
        for directory in (MA_CROSSOVER, MA_CROSSOVER_2, MA_CROSSOVER_3):
            summary = _summary(directory)
            equity = _equity(directory)
            capital = _initial_capital(summary)

            assert equity.iloc[0] == pytest.approx(capital, rel=1e-12)
            assert summary["strategy_metrics"]["total_return"] == pytest.approx(
                summary["validation"]["total_return"], rel=1e-12, abs=1e-15
            )

    def test_buy_and_hold_artifacts_report_two_different_total_returns(self):
        """The buy-and-hold artifact publishes both conventions at once."""
        for directory, expected_gap in (
            (BUY_AND_HOLD, 0.117701120576),
            (BUY_AND_HOLD_RERUN, 0.000572950030532),
        ):
            summary = _summary(directory)
            equity = _equity(directory)
            capital = _initial_capital(summary)

            published = summary["strategy_metrics"]["total_return"]
            validation = summary["validation"]["total_return"]

            # Pre-fix convention (engine, pre-2026-10-20): equity[0] -> equity[-1].
            assert published == pytest.approx(
                equity.iloc[-1] / equity.iloc[0] - 1.0, rel=1e-12, abs=1e-15
            )
            # Corrected convention (validate_strategy, and the engine now):
            # initial capital -> equity[-1].
            assert validation == pytest.approx(
                equity.iloc[-1] / capital - 1.0, rel=1e-12, abs=1e-15
            )
            # The two differ by exactly the first bar's entry cost.
            assert published - validation == pytest.approx(expected_gap, rel=1e-9, abs=1e-12)

    def test_benchmark_metrics_carry_the_same_pre_fix_convention(self):
        """The benchmark block has no validation counterpart, so its
        pre-fix discrepancy was invisible in the artifact."""
        summary = _summary(MA_CROSSOVER)
        equity = _equity(MA_CROSSOVER, "benchmark_equity.parquet")
        capital = _initial_capital(summary)

        published = summary["benchmark_metrics"]["total_return"]
        assert published == pytest.approx(
            equity.iloc[-1] / equity.iloc[0] - 1.0, rel=1e-12, abs=1e-15
        )
        corrected = equity.iloc[-1] / capital - 1.0
        assert published - corrected == pytest.approx(0.044733117441114, rel=1e-9, abs=1e-12)

    def test_published_total_return_was_blind_to_the_cost_model_fix(self):
        """The cost-model fix moved the equity curve by 11.77 pp, but the
        published total_return/annualized_return did not move at all."""
        old = _summary(BUY_AND_HOLD)["strategy_metrics"]
        new = _summary(BUY_AND_HOLD_RERUN)["strategy_metrics"]

        # The per-trade cost changed by a factor of ~205.
        assert old["avg_trade_cost"] == pytest.approx(0.041105949376283715, rel=1e-12)
        assert new["avg_trade_cost"] == pytest.approx(0.00020009711746988646, rel=1e-12)
        # The published total_return is unchanged to 13 significant digits.
        assert old["total_return"] == pytest.approx(new["total_return"], rel=1e-12, abs=1e-13)
        assert old["annualized_return"] == pytest.approx(
            new["annualized_return"], rel=1e-12, abs=1e-13
        )
        # The corrected metric does see it.
        old_corrected = _equity(BUY_AND_HOLD).iloc[-1] / _initial_capital(_summary(BUY_AND_HOLD))
        new_corrected = _equity(BUY_AND_HOLD_RERUN).iloc[-1] / _initial_capital(
            _summary(BUY_AND_HOLD_RERUN)
        )
        assert new_corrected - old_corrected == pytest.approx(
            0.11712817054539659, rel=1e-9, abs=1e-12
        )


class TestRemainingDisclosures:
    """What is deliberately left as a disclosure rather than a rewrite."""

    def test_h18_runner_keeps_the_pre_fix_convention(self):
        """H18's runner computes its own published total_return with the
        pre-fix range; the artifact is frozen, so the copy stays."""
        summary = _summary(H18)
        combo = next(
            c
            for c in summary["all_combo_results"]
            if c["combo_name"] == "prior_5d_return_sign_next_intraday"
        )
        assert combo["combo_name"] == "prior_5d_return_sign_next_intraday"

        equity = _equity(H18 / combo["combo_name"], "equity.parquet")
        published = combo["total_return"]
        assert published == pytest.approx(
            equity.iloc[-1] / equity.iloc[0] - 1.0, rel=1e-12, abs=1e-15
        )
        # H18's initial capital is 100_000 (run_h18_...:471, :591), so the
        # corrected value is lower by the first bar's 2 bps entry cost.
        corrected = equity.iloc[-1] / 100_000.0 - 1.0
        assert equity.iloc[0] == pytest.approx(100_000.0 * (1.0 - 0.0002), rel=1e-12)
        assert published - corrected == pytest.approx(
            0.0002 * (1.0 + published), rel=1e-12, abs=1e-15
        )
        assert published - corrected == pytest.approx(0.0006339342884920107, rel=1e-12)

    def test_h18_gates_do_not_use_total_return(self):
        gates = _summary(H18)["gate_metrics"]
        assert "total_return" not in gates
        assert set(gates) == {
            "sharpe",
            "trades",
            "profit_factor",
            "max_drawdown",
            "walk_forward_stability",
            "worst_regime_sharpe",
            "benchmark_p",
            "information_ratio",
            "perturbation_ratio",
        }

    def test_no_runner_selects_on_the_engines_total_return(self):
        """The metric must not be load-bearing for any selection or verdict:
        a change to it cannot move a published number."""
        runners = sorted(ROOT.glob("run_*.py"))
        assert runners

        offenders = []
        for runner in runners:
            source = runner.read_text()
            if "total_return" not in source:
                continue
            # Only H18 computes a total_return of its own; no runner reads
            # the engine's metrics["total_return"].
            if runner.name != "run_h18_overnight_intraday_experiment.py":
                offenders.append(runner.name)
            assert 'metrics["total_return"]' not in source
            assert "metrics['total_return']" not in source
        assert offenders == []
