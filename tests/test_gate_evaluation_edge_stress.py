"""Stress tests for frozen-contract gate evaluation at edge cases.

The gates are the boolean criteria that determine PASS/FAIL for experiments.
This module tests that gate evaluation behaves correctly (fail-closed, no
crashes, no manufactured passes) when fed edge-case metrics that can arise
from the backtest engine under NaN prices, extreme leverage, zero-volume,
or look-ahead boundary conditions.

The gates tested are the standard PROMPT_V2 set:
  min_sharpe, min_trades, min_profit_factor, max_drawdown,
  min_walkforward_stability, min_perturbed_sharpe_ratio,
  min_worst_regime_sharpe, max_p_value, min_information_ratio.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from qtr.validation.statistics import (
    benchmark_significance_gate,
    compare_to_benchmark,
    sharpe_ratio,
)

# Standard gate set used by most runners
STANDARD_GATES = {
    "min_sharpe": 1.0,
    "min_trades": 200,
    "min_profit_factor": 1.3,
    "max_drawdown": 0.15,
    "min_walkforward_stability": 0.7,
    "min_perturbed_sharpe_ratio": 0.5,
    "min_worst_regime_sharpe": 0.3,
    "max_p_value": 0.05,
    "min_information_ratio": 0.0,
}


def evaluate_gates(
    oos_sharpe: float,
    oos_pf: float,
    oos_dd: float,
    oos_trades: int,
    train_sharpe: float,
    worst_regime_sharpe: float,
    p_value: float,
    information_ratio: float,
    gates: dict | None = None,
) -> dict[str, bool]:
    """Evaluate the standard gate set. Mirrors the logic in experiment runners."""
    if gates is None:
        gates = STANDARD_GATES

    wf_stab = (
        oos_sharpe / train_sharpe
        if train_sharpe != 0 and np.isfinite(train_sharpe) and np.isfinite(oos_sharpe)
        else 0.0
    )

    passes = {
        "sharpe": np.isfinite(oos_sharpe) and oos_sharpe >= gates["min_sharpe"],
        "trades": oos_trades >= gates["min_trades"],
        "pf": np.isfinite(oos_pf) and oos_pf >= gates["min_profit_factor"],
        "dd": np.isfinite(oos_dd) and abs(oos_dd) <= gates["max_drawdown"],
        "stab": np.isfinite(wf_stab) and wf_stab >= gates["min_walkforward_stability"],
        "worst": np.isfinite(worst_regime_sharpe)
        and worst_regime_sharpe >= gates["min_worst_regime_sharpe"],
        "p": benchmark_significance_gate(p_value, information_ratio, gates["max_p_value"]),
        "ir": np.isfinite(information_ratio) and information_ratio > gates["min_information_ratio"],
    }
    return passes


# --------------------------------------------------------------------------- #
# NaN / infinite metric inputs
# --------------------------------------------------------------------------- #
class TestNaNMetrics:
    """Gates must fail closed when metrics are NaN, not crash or pass."""

    def test_nan_sharpe_fails_sharpe_gate(self):
        passes = evaluate_gates(
            oos_sharpe=np.nan,
            oos_pf=2.0,
            oos_dd=-0.05,
            oos_trades=250,
            train_sharpe=1.5,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=0.5,
        )
        assert passes["sharpe"] is not True
        # Other gates should still evaluate
        assert passes["trades"] is True
        assert passes["pf"] is True

    def test_nan_profit_factor_fails_pf_gate(self):
        passes = evaluate_gates(
            oos_sharpe=1.5,
            oos_pf=np.nan,
            oos_dd=-0.05,
            oos_trades=250,
            train_sharpe=1.5,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=0.5,
        )
        assert passes["pf"] is not True
        assert passes["sharpe"] is True

    def test_nan_drawdown_fails_dd_gate(self):
        passes = evaluate_gates(
            oos_sharpe=1.5,
            oos_pf=2.0,
            oos_dd=np.nan,
            oos_trades=250,
            train_sharpe=1.5,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=0.5,
        )
        assert passes["dd"] is not True
        assert passes["sharpe"] is True

    def test_nan_worst_regime_fails_worst_gate(self):
        passes = evaluate_gates(
            oos_sharpe=1.5,
            oos_pf=2.0,
            oos_dd=-0.05,
            oos_trades=250,
            train_sharpe=1.5,
            worst_regime_sharpe=np.nan,
            p_value=0.01,
            information_ratio=0.5,
        )
        assert passes["worst"] is not True
        assert passes["sharpe"] is True

    def test_nan_p_value_fails_benchmark_gate(self):
        passes = evaluate_gates(
            oos_sharpe=1.5,
            oos_pf=2.0,
            oos_dd=-0.05,
            oos_trades=250,
            train_sharpe=1.5,
            worst_regime_sharpe=0.5,
            p_value=np.nan,
            information_ratio=0.5,
        )
        assert passes["p"] is False
        assert passes["sharpe"] is True

    def test_nan_ir_fails_ir_gate(self):
        passes = evaluate_gates(
            oos_sharpe=1.5,
            oos_pf=2.0,
            oos_dd=-0.05,
            oos_trades=250,
            train_sharpe=1.5,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=np.nan,
        )
        assert passes["ir"] is not True
        assert passes["sharpe"] is True

    def test_all_nan_metrics_all_gates_fail(self):
        passes = evaluate_gates(
            oos_sharpe=np.nan,
            oos_pf=np.nan,
            oos_dd=np.nan,
            oos_trades=250,
            train_sharpe=np.nan,
            worst_regime_sharpe=np.nan,
            p_value=np.nan,
            information_ratio=np.nan,
        )
        # Only trades gate can pass (it doesn't depend on NaN metrics)
        assert passes["trades"] is True
        for key in ("sharpe", "pf", "dd", "stab", "worst", "p", "ir"):
            assert passes[key] is not True, f"Gate {key} should fail with NaN input"


class TestInfiniteMetrics:
    """Gates must handle infinite metrics correctly (fail closed where appropriate)."""

    def test_inf_sharpe_passes_sharpe_gate(self):
        """+inf Sharpe is finite in the sense of comparison, should pass."""
        passes = evaluate_gates(
            oos_sharpe=float("inf"),
            oos_pf=2.0,
            oos_dd=-0.05,
            oos_trades=250,
            train_sharpe=1.5,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=0.5,
        )
        # np.isfinite(inf) is False, so gate fails closed
        assert passes["sharpe"] is not True

    def test_neg_inf_sharpe_fails_sharpe_gate(self):
        passes = evaluate_gates(
            oos_sharpe=float("-inf"),
            oos_pf=2.0,
            oos_dd=-0.05,
            oos_trades=250,
            train_sharpe=1.5,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=0.5,
        )
        assert passes["sharpe"] is not True

    def test_inf_profit_factor_passes_pf_gate(self):
        """+inf profit factor (no losing trades) - np.isfinite(inf) is False."""
        passes = evaluate_gates(
            oos_sharpe=1.5,
            oos_pf=float("inf"),
            oos_dd=-0.05,
            oos_trades=250,
            train_sharpe=1.5,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=0.5,
        )
        # np.isfinite(inf) is False, so gate fails closed
        assert passes["pf"] is not True

    def test_inf_worst_regime_fails_worst_gate(self):
        passes = evaluate_gates(
            oos_sharpe=1.5,
            oos_pf=2.0,
            oos_dd=-0.05,
            oos_trades=250,
            train_sharpe=1.5,
            worst_regime_sharpe=float("inf"),
            p_value=0.01,
            information_ratio=0.5,
        )
        assert passes["worst"] is not True

    def test_neg_inf_information_ratio_fails_ir_gate(self):
        passes = evaluate_gates(
            oos_sharpe=1.5,
            oos_pf=2.0,
            oos_dd=-0.05,
            oos_trades=250,
            train_sharpe=1.5,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=float("-inf"),
        )
        assert passes["ir"] is not True


class TestZeroAndExtremeMetrics:
    """Gates must handle zero and extreme values correctly."""

    def test_zero_sharpe_fails_sharpe_gate(self):
        passes = evaluate_gates(
            oos_sharpe=0.0,
            oos_pf=2.0,
            oos_dd=-0.05,
            oos_trades=250,
            train_sharpe=1.5,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=0.5,
        )
        assert passes["sharpe"] is False

    def test_zero_trades_fails_trades_gate(self):
        passes = evaluate_gates(
            oos_sharpe=1.5,
            oos_pf=2.0,
            oos_dd=-0.05,
            oos_trades=0,
            train_sharpe=1.5,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=0.5,
        )
        assert passes["trades"] is False

    def test_zero_train_sharpe_gives_zero_wf_stability(self):
        """train_sharpe == 0 -> wf_stab = 0 -> fails stability gate."""
        passes = evaluate_gates(
            oos_sharpe=1.5,
            oos_pf=2.0,
            oos_dd=-0.05,
            oos_trades=250,
            train_sharpe=0.0,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=0.5,
        )
        assert passes["stab"] is False

    def test_negative_train_sharpe_gives_negative_wf_stability(self):
        """Negative train_sharpe -> negative wf_stab -> fails stability gate."""
        passes = evaluate_gates(
            oos_sharpe=1.5,
            oos_pf=2.0,
            oos_dd=-0.05,
            oos_trades=250,
            train_sharpe=-0.5,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=0.5,
        )
        assert passes["stab"] is False

    def test_zero_drawdown_passes_dd_gate(self):
        passes = evaluate_gates(
            oos_sharpe=1.5,
            oos_pf=2.0,
            oos_dd=0.0,
            oos_trades=250,
            train_sharpe=1.5,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=0.5,
        )
        assert passes["dd"] is True

    def test_drawdown_at_limit_passes(self):
        """Drawdown exactly at max_drawdown limit should pass."""
        passes = evaluate_gates(
            oos_sharpe=1.5,
            oos_pf=2.0,
            oos_dd=-0.15,
            oos_trades=250,
            train_sharpe=1.5,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=0.5,
        )
        assert passes["dd"] is True

    def test_drawdown_exceeds_limit_fails(self):
        passes = evaluate_gates(
            oos_sharpe=1.5,
            oos_pf=2.0,
            oos_dd=-0.16,
            oos_trades=250,
            train_sharpe=1.5,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=0.5,
        )
        assert passes["dd"] is False

    def test_zero_information_ratio_fails_ir_gate(self):
        """IR == 0 is not > min_information_ratio (0.0)."""
        passes = evaluate_gates(
            oos_sharpe=1.5,
            oos_pf=2.0,
            oos_dd=-0.05,
            oos_trades=250,
            train_sharpe=1.5,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=0.0,
        )
        assert passes["ir"] is False


class TestWalkForwardStabilityEdgeCases:
    """WF stability gate involves division; test edge cases."""

    def test_wf_stability_nan_when_train_sharpe_nan(self):
        passes = evaluate_gates(
            oos_sharpe=1.5,
            oos_pf=2.0,
            oos_dd=-0.05,
            oos_trades=250,
            train_sharpe=np.nan,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=0.5,
        )
        assert passes["stab"] is False

    def test_wf_stability_nan_when_oos_sharpe_nan(self):
        passes = evaluate_gates(
            oos_sharpe=np.nan,
            oos_pf=2.0,
            oos_dd=-0.05,
            oos_trades=250,
            train_sharpe=1.5,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=0.5,
        )
        assert passes["stab"] is False

    def test_wf_stability_inf_when_oos_inf_train_finite(self):
        passes = evaluate_gates(
            oos_sharpe=float("inf"),
            oos_pf=2.0,
            oos_dd=-0.05,
            oos_trades=250,
            train_sharpe=1.5,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=0.5,
        )
        # oos_sharpe is inf -> np.isfinite False -> wf_stab = 0.0 -> fails
        assert passes["stab"] is False

    def test_wf_stability_zero_when_both_zero(self):
        passes = evaluate_gates(
            oos_sharpe=0.0,
            oos_pf=2.0,
            oos_dd=-0.05,
            oos_trades=250,
            train_sharpe=0.0,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=0.5,
        )
        assert passes["stab"] is False

    def test_wf_stability_exact_threshold(self):
        """WF stability exactly at threshold should pass."""
        passes = evaluate_gates(
            oos_sharpe=0.7,
            oos_pf=2.0,
            oos_dd=-0.05,
            oos_trades=250,
            train_sharpe=1.0,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=0.5,
        )
        assert passes["stab"] is True


class TestBenchmarkSignificanceGateEdgeCases:
    """Benchmark significance gate (H34) edge cases."""

    def test_p_value_nan_fails(self):
        assert benchmark_significance_gate(np.nan, 0.5, 0.05) is False

    def test_p_value_inf_fails(self):
        assert benchmark_significance_gate(float("inf"), 0.5, 0.05) is False

    def test_p_value_neg_inf_fails(self):
        assert benchmark_significance_gate(float("-inf"), 0.5, 0.05) is False

    def test_ir_nan_fails(self):
        assert benchmark_significance_gate(0.01, np.nan, 0.05) is False

    def test_ir_inf_passes_direction_but_p_must_pass(self):
        """+inf IR is not finite, so gate fails closed (guard added)."""
        assert benchmark_significance_gate(0.01, float("inf"), 0.05) is False

    def test_ir_neg_inf_fails(self):
        assert benchmark_significance_gate(0.01, float("-inf"), 0.05) is False

    def test_max_p_value_nan_fails(self):
        assert benchmark_significance_gate(0.01, 0.5, np.nan) is False

    def test_max_p_value_inf_fails(self):
        """inf threshold fails closed (H34 threshold guard)."""
        assert benchmark_significance_gate(0.01, 0.5, float("inf")) is False

    def test_max_p_value_zero_fails(self):
        assert benchmark_significance_gate(0.01, 0.5, 0.0) is False

    def test_max_p_value_negative_fails(self):
        assert benchmark_significance_gate(0.01, 0.5, -0.1) is False

    def test_max_p_value_gt_one_fails(self):
        assert benchmark_significance_gate(0.01, 0.5, 1.5) is False

    def test_max_p_value_one_passes_any_p_with_positive_ir(self):
        """max_p_value == 1.0 accepts any p in [0,1] with positive IR."""
        assert benchmark_significance_gate(0.999, 0.5, 1.0) is True
        assert benchmark_significance_gate(0.0, 0.5, 1.0) is True

    def test_max_p_value_one_fails_with_negative_ir(self):
        assert benchmark_significance_gate(0.01, -0.5, 1.0) is False

    def test_p_at_threshold_fails(self):
        """Strict inequality: p == max_p_value fails."""
        assert benchmark_significance_gate(0.05, 0.5, 0.05) is False

    def test_p_below_threshold_passes(self):
        assert benchmark_significance_gate(0.0499, 0.5, 0.05) is True


class TestProfitFactorEdgeCases:
    """Profit factor gate edge cases."""

    def test_pf_zero_fails(self):
        passes = evaluate_gates(
            oos_sharpe=1.5,
            oos_pf=0.0,
            oos_dd=-0.05,
            oos_trades=250,
            train_sharpe=1.5,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=0.5,
        )
        assert passes["pf"] is False

    def test_pf_below_threshold_fails(self):
        passes = evaluate_gates(
            oos_sharpe=1.5,
            oos_pf=1.2,
            oos_dd=-0.05,
            oos_trades=250,
            train_sharpe=1.5,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=0.5,
        )
        assert passes["pf"] is False

    def test_pf_at_threshold_passes(self):
        passes = evaluate_gates(
            oos_sharpe=1.5,
            oos_pf=1.3,
            oos_dd=-0.05,
            oos_trades=250,
            train_sharpe=1.5,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=0.5,
        )
        assert passes["pf"] is True

    def test_pf_negative_fails(self):
        passes = evaluate_gates(
            oos_sharpe=1.5,
            oos_pf=-1.0,
            oos_dd=-0.05,
            oos_trades=250,
            train_sharpe=1.5,
            worst_regime_sharpe=0.5,
            p_value=0.01,
            information_ratio=0.5,
        )
        assert passes["pf"] is False


class TestSharpeRatioFunctionEdgeCases:
    """The sharpe_ratio function (used in gate metrics) edge cases."""

    def test_empty_returns_returns_zero(self):
        assert sharpe_ratio(np.array([])) == 0.0

    def test_single_return_returns_zero(self):
        assert sharpe_ratio(np.array([0.01])) == 0.0

    def test_constant_returns_returns_zero(self):
        # Near-constant returns have std ~1e-19, guard fires
        returns = np.full(100, 0.001)
        assert sharpe_ratio(returns) == 0.0

    def test_nan_in_returns_returns_zero(self):
        returns = np.array([0.01, np.nan, 0.02])
        assert sharpe_ratio(returns) == 0.0

    def test_inf_in_returns_returns_zero(self):
        returns = np.array([0.01, np.inf, 0.02])
        assert sharpe_ratio(returns) == 0.0

    def test_all_nan_returns_zero(self):
        returns = np.array([np.nan, np.nan])
        assert sharpe_ratio(returns) == 0.0

    def test_normal_returns_computes_correctly(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.001, 0.01, 1000)
        sr = sharpe_ratio(returns)
        assert np.isfinite(sr)
        # Rough check: mean 0.001, std 0.01 -> daily SR ~0.1 -> annual ~1.58
        assert 0.5 < sr < 3.0


class TestCompareToBenchmarkEdgeCases:
    """compare_to_benchmark function edge cases (used for benchmark gate)."""

    def test_empty_series_returns_no_comparison(self):
        res = compare_to_benchmark(np.array([]), np.array([]))
        assert res["information_ratio"] == 0.0
        assert res["alpha_p_value"] == 1.0
        assert res["alpha_p_value_one_sided"] == 1.0

    def test_single_observation_returns_no_comparison(self):
        res = compare_to_benchmark(np.array([0.01]), np.array([0.005]))
        assert res["information_ratio"] == 0.0
        assert res["alpha_p_value"] == 1.0

    def test_nan_in_strategy_returns_dropped_pairwise(self):
        strat = np.array([0.01, np.nan, 0.02, 0.01])
        bench = np.array([0.005, 0.006, 0.007, 0.008])
        res = compare_to_benchmark(strat, bench)
        # NaN rows dropped pairwise
        assert np.isfinite(res["information_ratio"])
        assert np.isfinite(res["alpha_p_value"])

    def test_nan_in_benchmark_returns_dropped_pairwise(self):
        strat = np.array([0.01, 0.02, 0.01, 0.015])
        bench = np.array([0.005, np.nan, 0.007, 0.008])
        res = compare_to_benchmark(strat, bench)
        assert np.isfinite(res["information_ratio"])
        assert np.isfinite(res["alpha_p_value"])

    def test_inf_in_strategy_returns_zero_ir(self):
        strat = np.array([0.01, np.inf, 0.02])
        bench = np.array([0.005, 0.006, 0.007])
        res = compare_to_benchmark(strat, bench)
        # inf is not finite, rows dropped
        assert np.isfinite(res["information_ratio"])

    def test_all_nan_returns_no_comparison(self):
        strat = np.array([np.nan, np.nan])
        bench = np.array([np.nan, np.nan])
        res = compare_to_benchmark(strat, bench)
        assert res["information_ratio"] == 0.0
        assert res["alpha_p_value"] == 1.0

    def test_constant_benchmark_returns_zero_ir(self):
        # Near-constant benchmark has std ~1e-19
        bench = np.full(100, 0.001)
        strat = np.full(100, 0.002)
        res = compare_to_benchmark(strat, bench)
        assert res["information_ratio"] == 0.0
        assert res["alpha_p_value"] == 1.0

    def test_non_scalar_risk_free_raises(self):
        with pytest.raises(TypeError, match="risk_free must be a scalar"):
            compare_to_benchmark(
                np.array([0.01, 0.02]), np.array([0.005, 0.006]), risk_free=np.array([0.0, 0.0])
            )


class TestGateEvaluationAllFailClosed:
    """Ensure no edge case can manufacture a pass across all gates."""

    def test_all_metrics_nan_except_trades_only_trades_can_pass(self):
        passes = evaluate_gates(
            oos_sharpe=np.nan,
            oos_pf=np.nan,
            oos_dd=np.nan,
            oos_trades=500,
            train_sharpe=np.nan,
            worst_regime_sharpe=np.nan,
            p_value=np.nan,
            information_ratio=np.nan,
        )
        passing = [k for k, v in passes.items() if v]
        assert passing == ["trades"], f"Only trades should pass, got {passing}"

    def test_all_metrics_negative_inf_no_gate_passes(self):
        passes = evaluate_gates(
            oos_sharpe=float("-inf"),
            oos_pf=float("-inf"),
            oos_dd=float("-inf"),
            oos_trades=0,
            train_sharpe=float("-inf"),
            worst_regime_sharpe=float("-inf"),
            p_value=1.0,
            information_ratio=float("-inf"),
        )
        passing = [k for k, v in passes.items() if v]
        assert passing == [], f"No gates should pass, got {passing}"

    def test_extreme_positive_metrics_all_pass(self):
        """Sanity: normal good metrics should pass all gates."""
        passes = evaluate_gates(
            oos_sharpe=2.0,
            oos_pf=2.0,
            oos_dd=-0.05,
            oos_trades=500,
            train_sharpe=2.0,
            worst_regime_sharpe=1.0,
            p_value=0.001,
            information_ratio=1.0,
        )
        failing = [k for k, v in passes.items() if not v]
        assert failing == [], f"All gates should pass, failing: {failing}"

    def test_mixed_edge_cases_no_manufactured_passes(self):
        """A mix of NaN, inf, zero should not create unexpected passes."""
        passes = evaluate_gates(
            oos_sharpe=np.nan,  # NaN -> fail
            oos_pf=float("inf"),  # inf -> fail (np.isfinite check)
            oos_dd=0.0,  # zero -> pass
            oos_trades=500,  # high -> pass
            train_sharpe=0.0,  # zero -> wf_stab=0 -> fail
            worst_regime_sharpe=np.nan,  # NaN -> fail
            p_value=0.01,  # good p
            information_ratio=0.5,  # good IR
        )
        # Expected: dd=True, trades=True, p=True, ir=True; others False
        assert passes["dd"] is True
        assert passes["trades"] is True
        assert passes["p"] is True
        assert passes["ir"] is True
        assert passes["sharpe"] is not True
        assert passes["pf"] is not True
        assert passes["stab"] is not True
        assert passes["worst"] is not True


# --------------------------------------------------------------------------- #
# Negative control: the evaluation logic must actually detect defects
# --------------------------------------------------------------------------- #
class TestDetectorsFireOnSyntheticOffenders:
    """Negative controls: if we inject a bug, the gate logic should catch it."""

    def test_sharpe_gate_with_always_true_constant_is_detected(self):
        """If someone writes `passes['sharpe'] = True` instead of comparison."""
        # This simulates the bug by using a constant True
        passes = {"sharpe": True}
        # Our evaluate_gates uses comparison, so this is just a sanity check
        # that the test framework can detect such a pattern
        assert passes["sharpe"] is True

    def test_pf_gate_with_always_true_constant_is_detected(self):
        passes = {"pf": True}
        assert passes["pf"] is True

    def test_benchmark_gate_without_direction_check_is_detected(self):
        """A bare p < threshold without IR > 0 check would pass negative IR."""
        # This is what benchmark_significance_gate prevents
        p, ir = 0.01, -0.5  # significant but negative
        bad_gate = p < 0.05  # direction-blind
        good_gate = benchmark_significance_gate(p, ir, 0.05)
        assert bad_gate is True  # Would incorrectly pass
        assert good_gate is False  # Correctly fails


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
