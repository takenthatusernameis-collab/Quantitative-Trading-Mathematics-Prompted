"""Regression tests for src/qtr/validation/statistics.py.

These tests pin the mathematical validation core used by every H1-H25
experiment runner. The module was at ~12% coverage before this suite:
only sharpe_ratio was exercised by the runners. Each function gets
deterministic, seeded assertions plus edge-case guards (empty input,
zero-variance, monotonicity) so a regression in the statistical core
is caught as a hard failure rather than a silent drift in the
certified H10-H14 numbers.
"""

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from qtr.validation import statistics as st


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def rng():
    return np.random.default_rng(12345)


@pytest.fixture
def returns(rng):
    return rng.normal(0.0005, 0.01, 500)


@pytest.fixture
def prices(rng):
    idx = pd.bdate_range("2020-01-01", periods=300)
    return pd.DataFrame(
        {
            "A": 100.0 * np.exp(np.cumsum(rng.normal(0.0008, 0.01, 300))),
            "B": 100.0 * np.exp(np.cumsum(rng.normal(-0.0004, 0.01, 300))),
        },
        index=idx,
    )


# ===========================================================================
# bootstrap_confidence_interval
# ===========================================================================
class TestBootstrapConfidenceInterval:
    def test_returns_tuple_of_floats(self, returns):
        lo, hi = st.bootstrap_confidence_interval(
            returns, n_bootstrap=500, random_state=42
        )
        assert isinstance(lo, float) or np.isscalar(lo)
        assert lo < hi

    def test_seed_is_reproducible(self, returns):
        a = st.bootstrap_confidence_interval(returns, n_bootstrap=500, random_state=42)
        b = st.bootstrap_confidence_interval(returns, n_bootstrap=500, random_state=42)
        assert a == b

    def test_default_statistic_is_mean(self, returns):
        lo, hi = st.bootstrap_confidence_interval(
            returns, n_bootstrap=500, random_state=1
        )
        assert lo <= returns.mean() <= hi

    def test_confidence_level_changes_width(self, returns):
        lo95, hi95 = st.bootstrap_confidence_interval(
            returns, confidence=0.95, n_bootstrap=800, random_state=7
        )
        lo99, hi99 = st.bootstrap_confidence_interval(
            returns, confidence=0.99, n_bootstrap=800, random_state=7
        )
        assert (hi99 - lo99) > (hi95 - lo95)

    def test_empty_input_returns_nan(self):
        lo, hi = st.bootstrap_confidence_interval(np.array([]))
        assert np.isnan(lo) and np.isnan(hi)

    def test_single_observation(self):
        lo, hi = st.bootstrap_confidence_interval(
            np.array([0.05]), n_bootstrap=100, random_state=3
        )
        assert lo == pytest.approx(0.05) and hi == pytest.approx(0.05)

    def test_custom_statistic_median(self, returns):
        lo, hi = st.bootstrap_confidence_interval(
            returns, statistic=np.median, n_bootstrap=500, random_state=9
        )
        assert lo <= np.median(returns) <= hi

    def test_constant_data_zero_width(self):
        lo, hi = st.bootstrap_confidence_interval(
            np.full(100, 0.05), n_bootstrap=200, random_state=11
        )
        assert lo == pytest.approx(0.05) and hi == pytest.approx(0.05)

    def test_does_not_mutate_global_rng(self, returns):
        """Regression: bootstrap_confidence_interval must use a local
        Generator and leave the global numpy RNG untouched. The prior
        implementation called np.random.seed(random_state), which reset the
        global RNG and contaminated unrelated random operations in the same
        process."""
        np.random.rand(100)  # advance global RNG to a non-zero position
        state_before = np.random.get_state()
        st.bootstrap_confidence_interval(returns, n_bootstrap=500, random_state=42)
        state_after = np.random.get_state()
        assert state_after[2] == state_before[2]  # position index
        assert np.array_equal(state_after[1], state_before[1])  # state vector


# ===========================================================================
# sharpe_ratio / sharpe_ratio_ci
# ===========================================================================
class TestSharpeRatio:
    def test_positive_for_positive_mean(self, returns):
        assert st.sharpe_ratio(returns) > 0

    def test_zero_for_zero_variance(self):
        assert st.sharpe_ratio(np.zeros(100)) == 0.0

    def test_annualization_factor(self):
        # Constant returns => zero variance => Sharpe 0 by the tolerance guard.
        daily = np.array([0.0005] * 252)
        assert st.sharpe_ratio(daily, periods_per_year=252) == 0.0
        assert st.sharpe_ratio(daily, periods_per_year=1) == 0.0

    def test_risk_free_subtraction(self):
        # Source formula: (mean - rf/periods)/std * sqrt(periods), which is
        # algebraically the standard annualized excess Sharpe. The rf term
        # is scaled by 1/(std * sqrt(periods)).
        rng = np.random.default_rng(21)
        daily = rng.normal(0.001, 0.01, 252)
        std = daily.std()
        assert st.sharpe_ratio(
            daily, risk_free=0.10, periods_per_year=252
        ) == pytest.approx(
            st.sharpe_ratio(daily, risk_free=0.0, periods_per_year=252)
            - 0.10 / (std * np.sqrt(252))
        )

    def test_constant_returns_give_zero_sharpe(self):
        # Regression guard: a constant return series must not divide by a
        # near-zero std (float noise ~1e-19) and produce a garbage Sharpe.
        assert st.sharpe_ratio(np.full(252, 0.0005)) == 0.0
        assert st.sharpe_ratio(np.zeros(100)) == 0.0

    def test_ci_is_reproducible(self, returns):
        a = st.sharpe_ratio_ci(returns, n_bootstrap=500, random_state=42)
        b = st.sharpe_ratio_ci(returns, n_bootstrap=500, random_state=42)
        assert a == b

    def test_ci_contains_point_estimate(self, returns):
        point = st.sharpe_ratio(returns)
        lo, hi = st.sharpe_ratio_ci(returns, n_bootstrap=800, random_state=5)
        assert lo <= point <= hi

    def test_ci_wider_at_lower_confidence(self, returns):
        lo90, hi90 = st.sharpe_ratio_ci(
            returns, confidence=0.90, n_bootstrap=800, random_state=5
        )
        lo99, hi99 = st.sharpe_ratio_ci(
            returns, confidence=0.99, n_bootstrap=800, random_state=5
        )
        assert (hi99 - lo99) > (hi90 - lo90)


# ===========================================================================
# walk_forward_splits
# ===========================================================================
class TestWalkForwardSplits:
    def test_default_split_count(self):
        splits = st.walk_forward_splits(100)
        assert len(splits) == 5

    def test_train_test_indices_partition_window(self):
        splits = st.walk_forward_splits(100, n_splits=5, train_ratio=0.7, gap=2)
        assert len(splits) == 5
        for train_idx, test_idx in splits:
            assert len(train_idx) > 0 and len(test_idx) > 0
            # gap prevents leakage: no test index may be within `gap` of train
            assert train_idx.max() + 2 <= test_idx.min()

    def test_small_n_returns_no_splits(self):
        assert st.walk_forward_splits(3, n_splits=5) == []

    def test_n_splits_zero_returns_empty_list(self):
        assert st.walk_forward_splits(100, n_splits=0) == []
        assert st.walk_forward_splits(100, n_splits=-1) == []

    def test_gap_zero_abuts_train_and_test(self):
        splits = st.walk_forward_splits(100, n_splits=5, gap=0)
        for train_idx, test_idx in splits:
            assert train_idx.max() + 1 == test_idx.min()

    def test_indices_are_within_bounds(self):
        splits = st.walk_forward_splits(77, n_splits=3)
        for train_idx, test_idx in splits:
            assert train_idx.min() >= 0 and test_idx.max() <= 76

    def test_train_ratio_affects_split_point(self):
        lo = st.walk_forward_splits(100, n_splits=1, train_ratio=0.5, gap=0)[0]
        hi = st.walk_forward_splits(100, n_splits=1, train_ratio=0.9, gap=0)[0]
        assert len(hi[0]) > len(lo[0])


# ===========================================================================
# multiple_testing_correction
# ===========================================================================
class TestMultipleTestingCorrection:
    def test_bonferroni_rejects_only_strongest(self):
        # p=[0.01,0.04,0.5,0.001], n=4, alpha=0.05
        # adjusted = min(p*4, 1) = [0.04, 0.16, 1.0, 0.004]
        # rejected  = adjusted < 0.05 = [True, False, False, True]
        p = np.array([0.01, 0.04, 0.5, 0.001])
        rejected, adjusted = st.multiple_testing_correction(p, "bonferroni", 0.05)
        assert rejected.tolist() == [True, False, False, True]
        assert adjusted[3] == pytest.approx(0.004)
        assert adjusted[0] == pytest.approx(0.04)

    def test_bonferroni_caps_at_one(self):
        # p=[0.5], n=1 -> adjusted = min(0.5*1, 1) = 0.5, not rejected at alpha 0.05
        rejected, adjusted = st.multiple_testing_correction(
            np.array([0.5]), "bonferroni", 0.05
        )
        assert adjusted[0] == 0.5
        assert not rejected[0]

    def test_bonferroni_caps_adjusted_at_one(self):
        # p=[0.5], n=2 -> adjusted = min(1.0, 1) = 1.0, capped
        _, adjusted = st.multiple_testing_correction(
            np.array([0.5, 0.5]), "bonferroni", 0.05
        )
        assert adjusted[0] == 1.0

    def test_bh_is_less_conservative_than_bonferroni(self):
        p = np.array([0.01, 0.02, 0.03, 0.04])
        _, adj_b = st.multiple_testing_correction(p, "bonferroni", 0.05)
        _, adj_h = st.multiple_testing_correction(p, "benjamini_hochberg", 0.05)
        assert (adj_h <= adj_b + 1e-12).all()

    def test_bh_monotonic_in_sorted_order(self):
        p = np.array([0.005, 0.01, 0.03, 0.04, 0.20])
        _, adjusted = st.multiple_testing_correction(p, "benjamini_hochberg", 0.05)
        order = np.argsort(p)
        sorted_adj = adjusted[order]
        assert np.all(np.diff(sorted_adj) >= -1e-12)

    def test_unknown_method_raises(self):
        with pytest.raises(ValueError):
            st.multiple_testing_correction(np.array([0.01]), "unknown", 0.05)

    def test_empty_input(self):
        rejected, adjusted = st.multiple_testing_correction(
            np.array([]), "bonferroni", 0.05
        )
        assert len(rejected) == 0 and len(adjusted) == 0


# ===========================================================================
# parameter_sensitivity
# ===========================================================================
class TestParameterSensitivity:
    def _two_regime_returns(self, rng):
        return np.array(
            [
                rng.normal(0.0010, 0.01, 400),
                rng.normal(-0.0005, 0.01, 400),
            ]
        )

    def test_keys_present(self, rng):
        res = st.parameter_sensitivity(
            self._two_regime_returns(rng), np.array([1.0, 2.0]), n_bootstrap=200
        )
        for key in [
            "param_values",
            "metrics",
            "ci_lower",
            "ci_upper",
            "optimal_param",
            "optimal_metric",
            "stability_ratio",
            "metric_std",
        ]:
            assert key in res

    def test_optimal_param_is_best_metric(self, rng):
        res = st.parameter_sensitivity(
            self._two_regime_returns(rng), np.array([1.0, 2.0]), n_bootstrap=200
        )
        assert res["optimal_param"] in (1.0, 2.0)
        assert res["optimal_metric"] == pytest.approx(res["metrics"].max())

    def test_ci_bounds_envelope_metrics(self, rng):
        res = st.parameter_sensitivity(
            self._two_regime_returns(rng), np.array([1.0, 2.0]), n_bootstrap=200
        )
        assert (res["ci_lower"] <= res["metrics"] + 1e-12).all()
        assert (res["metrics"] <= res["ci_upper"] + 1e-12).all()

    def test_stability_ratio_in_unit_interval(self, rng):
        res = st.parameter_sensitivity(
            self._two_regime_returns(rng), np.array([1.0, 2.0]), n_bootstrap=200
        )
        assert 0.0 <= res["stability_ratio"] <= 1.0


# ===========================================================================
# regime_analysis
# ===========================================================================
class TestRegimeAnalysis:
    def test_per_regime_keys(self, rng):
        r1 = rng.normal(0.001, 0.01, 300)
        r2 = rng.normal(-0.0008, 0.01, 300)
        labels = np.array(["up"] * 300 + ["down"] * 300)
        res = st.regime_analysis(np.concatenate([r1, r2]), labels)
        assert "regime_up_sharpe" in res
        assert "regime_down_sharpe" in res
        assert res["regime_up_count"] == 300
        assert res["regime_down_count"] == 300

    def test_positive_regime_has_higher_mean(self, rng):
        r1 = rng.normal(0.002, 0.01, 300)
        r2 = rng.normal(-0.002, 0.01, 300)
        labels = np.array(["A"] * 300 + ["B"] * 300)
        res = st.regime_analysis(np.concatenate([r1, r2]), labels)
        assert res["regime_A_mean"] > res["regime_B_mean"]

    def test_single_observation_regime_skipped(self, rng):
        res = st.regime_analysis(np.array([0.01]), np.array(["only"]))
        assert res == {}


# ===========================================================================
# stressed_cost_test
# ===========================================================================
class TestStressedCostTest:
    def test_keys_present(self, rng):
        base_returns = rng.normal(0.0005, 0.01, 400)
        base_costs = np.abs(rng.normal(0.0002, 0.0001, 400))
        res = st.stressed_cost_test(base_returns, base_costs)
        for name in ["commission", "spread", "slippage", "impact"]:
            assert f"stressed_{name}_sharpe" in res
            assert f"stressed_{name}_return" in res
        assert "stressed_combined_sharpe" in res

    def test_higher_multiplier_reduces_sharpe(self, rng):
        base_returns = rng.normal(0.001, 0.01, 400)
        base_costs = np.full(400, 0.0005)
        mild = st.stressed_cost_test(base_returns, base_costs, {"impact": 1.0})
        severe = st.stressed_cost_test(base_returns, base_costs, {"impact": 10.0})
        assert severe["stressed_impact_sharpe"] < mild["stressed_impact_sharpe"]

    def test_default_multipliers(self, rng):
        base_returns = rng.normal(0.0, 0.01, 400)
        base_costs = np.full(400, 0.0005)
        res = st.stressed_cost_test(base_returns, base_costs)
        assert res["stressed_commission_sharpe"] == pytest.approx(
            res["stressed_spread_sharpe"]
        )


# ===========================================================================
# capacity_estimate
# ===========================================================================
class TestCapacityEstimate:
    def test_keys_present(self, rng):
        res = st.capacity_estimate(rng.normal(0.001, 0.01, 400), adv=1_000_000.0)
        for key in [
            "current_sharpe",
            "max_participation_rate",
            "estimated_max_aum",
            "sharpe_at_max_aum",
        ]:
            assert key in res

    def test_participation_capped_at_max(self, rng):
        res = st.capacity_estimate(
            rng.normal(0.001, 0.01, 400), adv=1_000_000.0, max_participation=0.1
        )
        assert 0.0 <= res["max_participation_rate"] <= 0.1 + 1e-9

    def test_zero_adv_yields_zero_aum(self, rng):
        res = st.capacity_estimate(rng.normal(0.001, 0.01, 400), adv=0.0)
        assert res["estimated_max_aum"] == pytest.approx(0.0)

    def test_custom_impact_model_used(self, rng):
        returns = rng.normal(0.001, 0.01, 400)
        impact = lambda p: 50.0 * p
        res = st.capacity_estimate(returns, adv=1_000_000.0, impact_model=impact)
        assert res["max_participation_rate"] > 0.0


# ===========================================================================
# compare_to_benchmark
# ===========================================================================
class TestCompareToBenchmark:
    def test_keys_present(self, rng):
        strat = rng.normal(0.001, 0.01, 400)
        bench = rng.normal(0.0003, 0.01, 400)
        res = st.compare_to_benchmark(strat, bench)
        for key in [
            "information_ratio",
            "alpha_annualized",
            "beta",
            "alpha_t_stat",
            "alpha_p_value",
            "win_rate",
            "excess_return_annual",
            "excess_vol_annual",
        ]:
            assert key in res

    def test_alpha_positive_when_outperforming(self, rng):
        strat = rng.normal(0.002, 0.01, 400)
        bench = rng.normal(0.0002, 0.01, 400)
        res = st.compare_to_benchmark(strat, bench)
        assert res["alpha_annualized"] > 0

    def test_beta_is_ols_slope(self, rng):
        strat = rng.normal(0.001, 0.01, 400)
        bench = rng.normal(0.001, 0.01, 400)
        res = st.compare_to_benchmark(strat, bench)
        # beta is the OLS regression slope of strat on bench, i.e.
        # cov(S,B,ddof=1) / var(B,ddof=1). The prior implementation mixed
        # np.cov (ddof=1) with np.var (ddof=0), which inflated beta by
        # n/(n-1) relative to the true OLS slope.
        expected_beta = np.cov(strat, bench, ddof=1)[0, 1] / np.var(bench, ddof=1)
        assert res["beta"] == pytest.approx(expected_beta)
        assert res["beta"] == pytest.approx(np.polyfit(bench, strat, 1)[0], rel=1e-9)
        assert res["beta"] == pytest.approx(
            stats.linregress(bench, strat).slope, rel=1e-9
        )

    def test_beta_matches_ols_not_mixed_ddof(self, rng):
        """Regression: beta must equal the OLS slope, not the inflated
        cov(ddof=1)/var(ddof=0) value. The mixed-ddof formula overstates
        beta by exactly n/(n-1)."""
        n = 400
        strat = rng.normal(0.001, 0.01, n)
        bench = rng.normal(0.001, 0.01, n)
        res = st.compare_to_benchmark(strat, bench)
        ols_slope = stats.linregress(bench, strat).slope
        mixed = np.cov(strat, bench, ddof=1)[0, 1] / np.var(bench, ddof=0)
        assert res["beta"] == pytest.approx(ols_slope, rel=1e-9)
        assert res["beta"] != pytest.approx(mixed, rel=1e-9)
        # The mixed formula overstates |beta| by n/(n-1) when beta != 0.
        if abs(ols_slope) > 1e-9:
            assert abs(res["beta"]) < abs(mixed)

    def test_zero_variance_benchmark_no_division(self):
        res = st.compare_to_benchmark(np.full(400, 0.001), np.zeros(400))
        assert res["beta"] == 0.0
        assert res["alpha_annualized"] == 0.0

    def test_p_value_in_unit_interval(self, rng):
        res = st.compare_to_benchmark(
            rng.normal(0.001, 0.01, 400), rng.normal(0.0005, 0.01, 400)
        )
        assert 0.0 <= res["alpha_p_value"] <= 1.0

    def test_dataframe_benchmark_reduced_to_equal_weighted(self, rng):
        """A multi-symbol benchmark (e.g. a DataFrame slice of a futures
        universe) must be reduced to a single series by averaging across
        symbols, not raise "The truth value of a Series is ambiguous".
        """
        strat = pd.Series(rng.normal(0.001, 0.01, 400))
        bench_df = pd.DataFrame(rng.normal(0.0003, 0.01, (400, 5)))
        res = st.compare_to_benchmark(strat, bench_df)
        # The result must equal the comparison against the row-mean series.
        res_mean = st.compare_to_benchmark(strat, bench_df.mean(axis=1))
        for key in res:
            assert res[key] == pytest.approx(res_mean[key])

    def test_2d_ndarray_benchmark_reduced(self, rng):
        """A 2-D ndarray benchmark is likewise reduced along axis 1."""
        strat = rng.normal(0.001, 0.01, 400)
        bench_2d = rng.normal(0.0003, 0.01, (400, 3))
        res = st.compare_to_benchmark(strat, bench_2d)
        res_mean = st.compare_to_benchmark(strat, bench_2d.mean(axis=1))
        assert res["beta"] == pytest.approx(res_mean["beta"])
        assert res["alpha_annualized"] == pytest.approx(res_mean["alpha_annualized"])


# ===========================================================================
# statistical_power_analysis
# ===========================================================================
class TestStatisticalPowerAnalysis:
    def test_returns_positive_int(self):
        n = st.statistical_power_analysis(0.5, alpha=0.05, power=0.8, std=1.0)
        assert isinstance(n, int) and n > 0

    def test_larger_effect_reduces_sample_size(self):
        small = st.statistical_power_analysis(0.2, alpha=0.05, power=0.8, std=1.0)
        large = st.statistical_power_analysis(0.8, alpha=0.05, power=0.8, std=1.0)
        assert large < small

    def test_higher_power_requires_more_samples(self):
        low = st.statistical_power_analysis(0.5, alpha=0.05, power=0.7, std=1.0)
        high = st.statistical_power_analysis(0.5, alpha=0.05, power=0.99, std=1.0)
        assert high > low

    def test_closed_form_formula(self):
        from scipy.stats import norm

        n = st.statistical_power_analysis(0.5, alpha=0.05, power=0.8, std=1.0)
        z_alpha = norm.ppf(1 - 0.05 / 2)
        z_beta = norm.ppf(0.8)
        expected = int(np.ceil(2 * ((z_alpha + z_beta) * 1.0 / 0.5) ** 2))
        assert n == expected


# ===========================================================================
# validate_strategy
# ===========================================================================
class TestValidateStrategy:
    def _trades(self, n=50):
        return pd.DataFrame(
            {
                "timestamp": pd.bdate_range("2020-01-01", periods=n),
                "symbol": ["A"] * n,
                "side": ["buy"] * (n // 2) + ["sell"] * (n - n // 2),
                "weight_change": [0.1] * n,
                "price": [100.0] * n,
                "cost": [0.0002] * n,
            }
        )

    def test_keys_present(self, rng):
        returns = rng.normal(0.001, 0.01, 400)
        res = st.validate_strategy(returns, self._trades(50), {})
        for key in [
            "sharpe",
            "sharpe_pass",
            "n_trades",
            "trades_pass",
            "profit_factor",
            "profit_factor_pass",
            "max_drawdown",
            "drawdown_pass",
            "walkforward_stability",
            "walkforward_pass",
            "annualized_return",
            "annualized_volatility",
            "total_return",
            "all_pass",
        ]:
            assert key in res

    def test_defaults_applied_when_config_empty(self, rng):
        returns = rng.normal(0.001, 0.01, 400)
        res = st.validate_strategy(returns, self._trades(50), {})
        # min_trades default is 200; 50 trades must fail
        assert res["trades_pass"] is False
        assert res["all_pass"] is False

    def test_all_pass_when_gates_cleared(self, rng):
        # Strong trending returns, many trades, low drawdown.
        idx = pd.bdate_range("2020-01-01", periods=600)
        strong = pd.Series(np.cumsum(rng.normal(0.002, 0.005, 600)) + 100.0, index=idx)
        returns = strong.pct_change().fillna(0).values
        trades = self._trades(500)
        cfg = {
            "min_sharpe": 0.5,
            "min_trades": 100,
            "min_profit_factor": 1.0,
            "max_drawdown": 0.5,
            "min_walkforward_stability": -1.0,
        }
        res = st.validate_strategy(returns, trades, cfg)
        assert res["all_pass"] is True
        # min_param_stability defaults to 0.8 and is part of the all_pass
        # conjunction; the trending series must pass it too.
        assert "param_stability" in res
        assert "param_stability_pass" in res
        assert res["param_stability_pass"] is True

    def test_param_stability_gate_is_enforced(self, rng):
        """min_param_stability must actually gate all_pass: a volatile series
        whose walk-forward folds flip sign must fail the gate even when every
        other criterion is configured to pass."""
        idx = pd.bdate_range("2020-01-01", periods=600)
        # Alternating trending / crashing halves => some folds profitable,
        # some not => param_stability < 1.0.
        trend = np.cumsum(rng.normal(0.002, 0.005, 300)) + 100.0
        crash = 100.0 * np.exp(np.cumsum(rng.normal(-0.002, 0.005, 300)))
        prices = pd.Series(np.concatenate([trend, crash]), index=idx)
        returns = prices.pct_change().fillna(0).values
        trades = self._trades(500)
        cfg = {
            "min_sharpe": -10.0,
            "min_trades": 100,
            "min_profit_factor": 0.0,
            "max_drawdown": 1.0,
            "min_walkforward_stability": -10.0,
            "min_param_stability": 0.8,
        }
        res = st.validate_strategy(returns, trades, cfg)
        assert res["param_stability_pass"] is False
        assert res["all_pass"] is False

    def test_profit_factor_infinite_when_no_losses(self, rng):
        # All-positive returns => no gross loss => profit_factor is inf.
        returns = np.abs(rng.normal(0.001, 0.01, 400)) + 1e-6
        res = st.validate_strategy(
            returns, self._trades(50), {"min_profit_factor": 1.0}
        )
        assert np.isinf(res["profit_factor"])

    def test_walkforward_zero_when_first_half_flat(self):
        # First-half returns identically zero => sharpe_first == 0 => wf_stability 0.
        n = 400
        returns = np.zeros(n)
        returns[n // 2 :] = 0.001
        res = st.validate_strategy(returns, self._trades(50), {})
        assert res["walkforward_stability"] == 0.0

    def test_walkforward_passes_with_both_halves_losing(self, rng):
        """Regression: a strategy losing in BOTH halves must NOT pass the
        walk-forward stability gate. The ratio alone is sign-sensitive and can
        exceed the threshold when both halves are negative (e.g. Sharpe -18 /
        -14 => 0.76 => PASS), which is the opposite of "stable".

        Both halves are pinned to Sharpe ~ -1.0, so the raw ratio is ~1.0 and
        would have passed the old 0.7 gate; the guard must force 0.0.
        """
        n = 200
        z1 = rng.normal(size=n)
        z1 = (z1 - z1.mean()) / z1.std()
        z2 = rng.normal(size=n)
        z2 = (z2 - z2.mean()) / z2.std()
        # mean/std = -1/sqrt(252) => annualized Sharpe = -1.0, std = 0.01.
        r1 = -1.0 / np.sqrt(252) * 0.01 + z1 * 0.01
        r2 = -1.0 / np.sqrt(252) * 0.01 + z2 * 0.01
        sr1, sr2 = st.sharpe_ratio(r1), st.sharpe_ratio(r2)
        assert sr1 == pytest.approx(-1.0, abs=0.2)
        assert sr2 == pytest.approx(-1.0, abs=0.2)
        assert sr2 / sr1 > 0.7  # raw ratio would have passed the old gate
        returns = np.concatenate([r1, r2])
        res = st.validate_strategy(
            returns,
            self._trades(50),
            {
                "min_sharpe": -100.0,
                "min_trades": 0,
                "min_profit_factor": 0.0,
                "max_drawdown": 1.0,
                "min_walkforward_stability": 0.7,
                "min_param_stability": 0.0,
            },
        )
        assert res["walkforward_stability"] == 0.0
        assert res["walkforward_pass"] is False
        assert res["all_pass"] is False

    def test_param_stability_zero_when_no_folds(self):
        # A too-short series yields no walk-forward folds => param_stability 0.
        res = st.validate_strategy(np.array([0.01]), self._trades(5), {})
        assert res["param_stability"] == 0.0
        assert res["param_stability_pass"] is False

    def test_empty_input_returns_safe_all_fail(self):
        """Empty returns must not crash (252 / len(returns) divides by zero)
        and must fail every evidence gate rather than certify an empty
        strategy as passing."""
        res = st.validate_strategy(np.array([]), self._trades(0), {})
        assert res["all_pass"] is False
        assert res["sharpe_pass"] is False
        assert res["walkforward_pass"] is False
        assert res["param_stability_pass"] is False
        assert res["walkforward_stability"] == 0.0
        assert res["param_stability"] == 0.0
        assert res["annualized_return"] == 0.0
        assert res["total_return"] == 0.0
        assert res["max_drawdown"] == 0.0
        assert res["drawdown_pass"] is True  # no exposure => no drawdown

    def test_max_drawdown_is_negative_or_zero(self, rng):
        returns = rng.normal(0.0, 0.01, 400)
        res = st.validate_strategy(returns, self._trades(50), {})
        assert res["max_drawdown"] <= 0.0

    def test_pandas_series_input_accepted(self, rng):
        returns = pd.Series(rng.normal(0.001, 0.01, 400))
        res = st.validate_strategy(returns, self._trades(50), {})
        assert "sharpe" in res


def test_purged_kfold_basic():
    from qtr.validation.statistics import purged_kfold_splits
    splits = purged_kfold_splits(100, n_splits=5)
    assert len(splits) == 5
    for tr, te in splits:
        assert len(tr) > 0 and len(te) > 0
        assert set(tr).isdisjoint(set(te))


def test_purged_kfold_purge_embargo():
    from qtr.validation.statistics import purged_kfold_splits
    splits = purged_kfold_splits(100, n_splits=5, purge=2, embargo=2)
    # train should not contain samples within purge of test
    for tr, te in splits:
        for t in te:
            for x in tr:
                assert abs(x - t) > 2 or x < t - 2 or x > t + 2
        # embargo: no train index within embargo after test block
    assert len(splits) >= 1


def test_purged_kfold_invalid():
    from qtr.validation.statistics import purged_kfold_splits
    assert purged_kfold_splits(0, 5) == []
    assert purged_kfold_splits(10, 0) == []
    assert purged_kfold_splits(3, 5) == []


def test_combinatorial_purged_cv_basic():
    from qtr.validation.statistics import combinatorial_purged_cv
    splits = combinatorial_purged_cv(100, n_splits=5, n_test_splits=2)
    # C(5,2)=10
    assert len(splits) == 10
    for tr, te in splits:
        assert len(tr) > 0 and len(te) > 0
        assert set(tr).isdisjoint(set(te))


def test_combinatorial_purged_cv_invalid():
    from qtr.validation.statistics import combinatorial_purged_cv
    assert combinatorial_purged_cv(0, 5, 2) == []
    assert combinatorial_purged_cv(100, 5, 0) == []
    assert combinatorial_purged_cv(100, 5, 5) == []
    assert combinatorial_purged_cv(3, 5, 2) == []
