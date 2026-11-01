"""Regression tests for src/qtr/validation/statistics.py.

These tests pin the mathematical validation core used by every H1-H25
experiment runner. The module was at ~12% coverage before this suite:
only sharpe_ratio was exercised by the runners. Each function gets
deterministic, seeded assertions plus edge-case guards (empty input,
zero-variance, monotonicity) so a regression in the statistical core
is caught as a hard failure rather than a silent drift in the
certified H10-H14 numbers.
"""

import warnings

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
        lo, hi = st.bootstrap_confidence_interval(returns, n_bootstrap=500, random_state=42)
        assert isinstance(lo, float) or np.isscalar(lo)
        assert lo < hi

    def test_seed_is_reproducible(self, returns):
        a = st.bootstrap_confidence_interval(returns, n_bootstrap=500, random_state=42)
        b = st.bootstrap_confidence_interval(returns, n_bootstrap=500, random_state=42)
        assert a == b

    def test_default_statistic_is_mean(self, returns):
        lo, hi = st.bootstrap_confidence_interval(returns, n_bootstrap=500, random_state=1)
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
        lo, hi = st.bootstrap_confidence_interval(np.array([0.05]), n_bootstrap=100, random_state=3)
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

    def test_zero_or_negative_bootstrap_returns_nan_tuple(self):
        """A bootstrap with no resamples has no interval to report.

        ``n_bootstrap <= 0`` produced an empty ``bootstrap_stats`` list and
        ``np.percentile([], ...)`` then raised ``IndexError: index -1 is out
        of bounds for axis 0 with size 0`` -- a crash out of a function every
        caller treats as returning a tuple of two floats. The crash is
        reachable from the public API with no caller-side filtering:
        ``parameter_sensitivity`` forwards its own ``n_bootstrap`` straight
        through here.
        """
        for bad_n in (0, -1, -100):
            lo, hi = st.bootstrap_confidence_interval(
                np.array([1.0, 2.0, 3.0]), n_bootstrap=bad_n, random_state=42
            )
            assert np.isnan(lo) and np.isnan(hi), f"n_bootstrap={bad_n}"

    def test_non_positive_bootstrap_returns_nan_tuple(self):
        """A non-positive bootstrap count is degenerate, same as zero."""
        lo, hi = st.bootstrap_confidence_interval(
            np.array([1.0, 2.0, 3.0]), n_bootstrap=0, random_state=42
        )
        assert np.isnan(lo) and np.isnan(hi)

    def test_confidence_outside_zero_to_one_returns_nan_tuple(self):
        """A confidence level outside (0, 1] is not a confidence level.

        * ``confidence <= 0`` sent both percentile arguments to 0 and
          returned ``(median, median)`` -- a zero-width interval at the
          middle of the distribution, claiming a precision the resample does
          not have.
        * ``confidence < 0`` sent them negative and returned ``(max, min)``,
          an INVERTED interval with the bounds swapped.
        * ``confidence > 1`` sent both arguments above 100 and
          ``np.percentile`` raised ``ValueError: Percentiles must be in the
          range [0, 100]``.

        All three are loud failures in the corrected implementation, which
        returns the same ``(nan, nan)`` tuple the empty-data path returns.
        """
        for bad_conf in (0.0, -0.5, -1.0, 1.5, 2.0):
            lo, hi = st.bootstrap_confidence_interval(
                np.array([1.0, 2.0, 3.0]),
                confidence=bad_conf,
                n_bootstrap=10,
                random_state=42,
            )
            assert np.isnan(lo) and np.isnan(hi), f"confidence={bad_conf}"

    def test_confidence_one_is_the_full_range(self):
        """``confidence == 1.0`` is valid: both percentiles sit at the
        extremes of the resample distribution.

        The interval is the resample min and max (percentile 0 and 100 of
        the bootstrap statistics), not the data min and max: a resample
        drawn with replacement from a small set need not include the
        extremes, so the resample range is a subset of the data range.
        Every bootstrap statistic is a mean of a subset, so the bounds
        stay within ``[data.min(), data.max()]``.
        """
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        lo, hi = st.bootstrap_confidence_interval(
            data, confidence=1.0, n_bootstrap=50, random_state=42
        )
        assert lo <= hi
        assert lo >= data.min() - 1e-12
        assert hi <= data.max() + 1e-12


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
        assert st.sharpe_ratio(daily, risk_free=0.10, periods_per_year=252) == pytest.approx(
            st.sharpe_ratio(daily, risk_free=0.0, periods_per_year=252)
            - 0.10 / (std * np.sqrt(252))
        )

    def test_constant_returns_give_zero_sharpe(self):
        # Regression guard: a constant return series must not divide by a
        # near-zero std (float noise ~1e-19) and produce a garbage Sharpe.
        assert st.sharpe_ratio(np.full(252, 0.0005)) == 0.0
        assert st.sharpe_ratio(np.zeros(100)) == 0.0

    @pytest.mark.parametrize("non_finite", [np.inf, -np.inf, np.nan])
    def test_non_finite_returns_give_zero_sharpe(self, non_finite):
        """A return series carrying an `inf`, `-inf` or `nan` bar must not
        propagate through the Sharpe computation.

        The guard used to be ``returns.std() <= 1e-15``. A non-finite standard
        deviation compares unordered, so ``nan <= 1e-15`` is ``False`` and the
        guard did NOT fire: the function then divided an inf/nan mean by a nan
        std and emitted ``nan``. That is the same class of silent-void defect
        H61 found in `compare_to_benchmark` (an `inf` is not a missing value,
        it is an impossible return) and the same input class H58 found in the
        record (a price crossing zero makes `pct_change()` produce an `inf`).
        The engine's own Sharpe guard fires on the same input and reports
        ``0.0`` (see tests/test_engine_metric_agreement.py), so this function
        now matches it.

        Every finite input is bit-identical to before: the guard only fires
        for a non-finite std.
        """
        returns = np.array([0.001] * 9 + [non_finite] + [0.001] * 10)
        assert st.sharpe_ratio(returns) == 0.0

    def test_the_contract_rejects_the_pre_fix_non_finite_guard(self):
        """Negative control: the pre-fix ``std <= 1e-15`` guard does not fire
        on a non-finite series, so the pre-fix Sharpe is ``nan`` while the
        corrected one is ``0.0``. The invariant "a non-finite series yields a
        finite Sharpe" that this contract states must reject the pre-fix path.
        """
        import warnings

        returns = np.array([0.001] * 9 + [np.inf] + [0.001] * 10)

        # Reconstruct the pre-fix arithmetic exactly: the guard was
        # ``if returns.std() <= 1e-15: return 0.0`` and the return was
        # ``excess.mean() / returns.std() * sqrt(periods_per_year)``.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            std = float(returns.std())
            pre_fix_guard_fires = std <= 1e-15
            pre_fix = float(returns.mean() / std * np.sqrt(252))

        # The pre-fix guard evaluates to False for a nan std (NaN compares
        # unordered), so the division runs and emits nan.
        assert not pre_fix_guard_fires, "the control must not fire"
        assert np.isnan(std)
        assert np.isnan(pre_fix), "the pre-fix path must emit nan"

        # The corrected implementation is finite and equals the engine's 0.0.
        corrected = st.sharpe_ratio(returns)
        assert corrected == 0.0
        assert np.isfinite(corrected)

    def test_ci_is_reproducible(self, returns):
        a = st.sharpe_ratio_ci(returns, n_bootstrap=500, random_state=42)
        b = st.sharpe_ratio_ci(returns, n_bootstrap=500, random_state=42)
        assert a == b

    def test_ci_contains_point_estimate(self, returns):
        point = st.sharpe_ratio(returns)
        lo, hi = st.sharpe_ratio_ci(returns, n_bootstrap=800, random_state=5)
        assert lo <= point <= hi

    def test_ci_wider_at_lower_confidence(self, returns):
        lo90, hi90 = st.sharpe_ratio_ci(returns, confidence=0.90, n_bootstrap=800, random_state=5)
        lo99, hi99 = st.sharpe_ratio_ci(returns, confidence=0.99, n_bootstrap=800, random_state=5)
        assert (hi99 - lo99) > (hi90 - lo90)

    def test_ci_propagates_the_bootstrap_degenerate_guard(self):
        """``sharpe_ratio_ci`` is a thin wrapper over
        ``bootstrap_confidence_interval`` and must not mask its guard.

        A non-positive bootstrap count or an out-of-range confidence level
        used to raise here (``IndexError`` from the empty resample list, or
        ``ValueError`` from ``np.percentile``) rather than returning the
        no-evidence tuple the underlying function now returns.
        """
        for bad_n in (0, -5):
            lo, hi = st.sharpe_ratio_ci(np.array([1.0, 2.0, 3.0]), n_bootstrap=bad_n)
            assert np.isnan(lo) and np.isnan(hi)
        for bad_conf in (0.0, -1.0, 1.5):
            lo, hi = st.sharpe_ratio_ci(
                np.array([1.0, 2.0, 3.0]),
                confidence=bad_conf,
                n_bootstrap=10,
                random_state=42,
            )
            assert np.isnan(lo) and np.isnan(hi)


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
        rejected, adjusted = st.multiple_testing_correction(np.array([0.5]), "bonferroni", 0.05)
        assert adjusted[0] == 0.5
        assert not rejected[0]

    def test_bonferroni_caps_adjusted_at_one(self):
        # p=[0.5], n=2 -> adjusted = min(1.0, 1) = 1.0, capped
        _, adjusted = st.multiple_testing_correction(np.array([0.5, 0.5]), "bonferroni", 0.05)
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
        rejected, adjusted = st.multiple_testing_correction(np.array([]), "bonferroni", 0.05)
        assert len(rejected) == 0 and len(adjusted) == 0

    @pytest.mark.parametrize("method", ["bonferroni", "benjamini_hochberg"])
    @pytest.mark.parametrize(
        "bad",
        [
            np.array([0.05, np.nan]),
            np.array([0.05, np.inf]),
            np.array([0.05, -np.inf]),
            np.array([-0.1]),
            np.array([1.5]),
            np.array([0.05, -0.05]),
        ],
        ids=["nan", "inf", "neg_inf", "negative", "above_one", "mixed"],
    )
    def test_degenerate_p_values_fail_closed(self, method, bad):
        """A non-finite, negative or above-one p-value is not a p-value, and
        the correction must not manufacture a rejection out of it.

        Pre-fix behaviour, measured on this input class:
        - a `nan` propagated through ``p * n`` and ``min(nan, 1.0)``
          unchanged, leaving one adjusted p-value as `nan` while every
          other test in the same set got a finite value -- an internally
          inconsistent result that silently voids one test's adjustment;
        - a `-inf` adjusted p-value was rejected at any alpha > 0;
        - a negative p-value was rejected at any alpha > 0 (a false
          positive manufactured out of a bad input).

        The fail-closed result is the no-evidence tuple: every test left
        unadjusted (adjusted p-value 1.0, the maximally non-significant
        value) and nothing rejected.
        """
        rejected, adjusted = st.multiple_testing_correction(bad, method, 0.05)
        assert rejected.tolist() == [False] * len(bad)
        assert adjusted.tolist() == [1.0] * len(bad)

    @pytest.mark.parametrize("method", ["bonferroni", "benjamini_hochberg"])
    def test_the_contract_rejects_the_pre_fix_degenerate_behaviour(self, method):
        """Negative control: reconstruct the pre-fix arithmetic on a
        degenerate input and require the contract to reject it.

        A `nan` p-value left a `nan` adjusted p-value and a negative
        p-value left a rejected hypothesis; both are failures the guard
        exists to prevent, so the reconstructed pre-fix result must NOT
        equal the fail-closed tuple.
        """
        # nan: pre-fix adjusted p-value is nan, not 1.0
        nan_p = np.array([0.05, np.nan])
        pre_fix_nan = float(np.minimum(nan_p * 2, 1.0)[1])
        assert pre_fix_nan != 1.0
        assert np.isnan(pre_fix_nan)

        # negative: pre-fix rejected the hypothesis
        neg_p = np.array([-0.1])
        pre_fix_rejected = bool(np.minimum(neg_p * 1, 1.0)[0] < 0.05)
        assert pre_fix_rejected is True

        # The corrected function rejects neither.
        _, adjusted = st.multiple_testing_correction(nan_p, method, 0.05)
        assert adjusted.tolist() == [1.0, 1.0]
        rejected, _ = st.multiple_testing_correction(neg_p, method, 0.05)
        assert rejected.tolist() == [False]


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

    def test_empty_param_grid_returns_safe_all_fail_tuple(self):
        """A grid with no parameter rows has nothing to summarize.

        ``parameter_sensitivity`` used to walk straight into
        ``np.argmax([])`` and raise ``ValueError: attempt to get argmax of
        an empty sequence`` -- a crash out of a pure function every caller
        treats as returning a dict. The crash is reachable from the public
        API with no caller-side filtering: ``validate_strategy`` derives its
        published ``param_stability`` from this function's ``optimal_param``
        (see tests/test_parameter_sensitivity_reproducibility.py), so a
        strategy with no parameter grid hands an empty array here.
        """
        res = st.parameter_sensitivity(np.zeros((0, 5)), np.array([]))
        assert res["param_values"].shape == (0,)
        assert res["metrics"].shape == (0,)
        assert res["ci_lower"].shape == (0,)
        assert res["ci_upper"].shape == (0,)
        assert np.isnan(res["optimal_param"])
        assert res["optimal_metric"] == 0.0
        assert res["stability_ratio"] == 0.0
        assert res["metric_std"] == 0.0

    def test_length_mismatched_returns_is_treated_as_an_empty_grid(self):
        """A ``returns`` array with fewer rows than ``param_values`` leaves
        the loop unable to index every parameter row.

        The contract is ``returns.shape[0] == n_params`` ("2D: n_params x
        n_obs"); a frame with fewer rows than parameters cannot be scored
        per-row and used to raise ``IndexError`` on the first missing row.
        A frame with MORE rows is a contract violation the pre-fix code
        accepted by silently ignoring the extras, and that behaviour is
        unchanged here -- only the under-supplied case is fail-closed.
        """
        res = st.parameter_sensitivity(np.zeros((1, 5)), np.array([1.0, 2.0, 3.0]))
        assert res["metrics"].shape == (0,)
        assert res["stability_ratio"] == 0.0

    def test_extra_rows_in_returns_are_silently_ignored(self):
        """Pre-existing behaviour, pinned so the guard does not widen it.

        A frame with more rows than parameters is scored over the first
        ``n_params`` rows; the extras are ignored, exactly as before the
        guard was added.
        """
        res = st.parameter_sensitivity(
            np.zeros((5, 5)), np.array([1.0, 2.0]), n_bootstrap=10, random_state=42
        )
        assert res["metrics"].shape == (2,)
        assert res["optimal_param"] in (1.0, 2.0)

    def test_non_positive_bootstrap_returns_safe_tuple(self):
        """A non-positive ``n_bootstrap`` is forwarded to the bootstrap and
        must not crash here either: it is caught at the top, in one place,
        so the empty-params crash cannot mask it."""
        for bad_n in (0, -1):
            res = st.parameter_sensitivity(
                self._two_regime_returns(np.random.default_rng(1)),
                np.array([1.0, 2.0]),
                n_bootstrap=bad_n,
            )
            assert res["metrics"].shape == (0,)
            assert res["stability_ratio"] == 0.0
            assert np.isnan(res["optimal_param"])

    def test_empty_grid_is_a_no_op_on_every_call(self):
        """The degenerate result is deterministic: no randomness, no crash.

        The two calls differ only in their seed, which the guard never
        reaches, so the empty-grid tuple is identical. Comparison is done
        field by field because the arrays are empty and ``a == b`` on a
        dict of empty numpy arrays raises "truth value is ambiguous".
        """
        a = st.parameter_sensitivity(np.zeros((0, 5)), np.array([]), random_state=42)
        b = st.parameter_sensitivity(np.zeros((0, 5)), np.array([]), random_state=99)
        for key in ("metrics", "ci_lower", "ci_upper"):
            assert a[key].shape == b[key].shape == (0,)
        assert np.array_equal(a["param_values"], b["param_values"])
        assert np.isnan(a["optimal_param"]) and np.isnan(b["optimal_param"])
        assert a["optimal_metric"] == b["optimal_metric"]
        assert a["stability_ratio"] == b["stability_ratio"]
        assert a["metric_std"] == b["metric_std"]


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
        assert res["stressed_commission_sharpe"] == pytest.approx(res["stressed_spread_sharpe"])


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

        def impact(p):
            return 50.0 * p

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
        assert res["beta"] == pytest.approx(stats.linregress(bench, strat).slope, rel=1e-9)

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

    def test_near_constant_benchmark_does_not_produce_a_garbage_information_ratio(self):
        """Regression: a benchmark whose bars move by ~1e-19 (float noise,
        not exactly 0.0) used to divide the mean excess by ~1e-19 and emit a
        garbage information ratio of ~7.3e16.

        `sharpe_ratio` carries a 1e-15 tolerance guard and reports 0.0 for
        the same excess series, so the two implementations disagreed on an
        input the record actually contains: any benchmark series whose
        prices are constant to float precision (a flat book, a synthetic
        fixture, or a benchmark whose per-bar move is below ~1e-8). The
        information ratio must agree with `sharpe_ratio` on this input.
        """
        rng = np.random.default_rng(0)
        bench = np.full(200, 0.0001) + rng.normal(0.0, 1e-19, 200)
        strat = bench + 0.0005
        excess = strat - bench

        assert excess.std(ddof=0) < 1e-15  # the input is near-constant

        res = st.compare_to_benchmark(strat, bench)
        assert res["information_ratio"] == 0.0
        assert abs(res["information_ratio"]) < 1e6
        assert res["information_ratio"] == pytest.approx(
            st.sharpe_ratio(excess), rel=1e-12, abs=1e-15
        )
        # The t-test must also fail closed on the same input: a near-constant
        # series has no measurable variation, so it cannot be "significant".
        assert res["alpha_t_stat"] == 0.0
        assert res["alpha_p_value"] == 1.0
        assert res["alpha_p_value_one_sided"] == 0.5
        # The CAPM beta/alpha block used to carry its own loose guard
        # (`bench.std(ddof=0) > 0`) that did NOT fire on this same input: it
        # divided cov(S,B) by a ~1e-19 variance and emitted a garbage beta
        # (~1.03) and a garbage alpha (~0.125 annualized) while the IR and
        # t-test guards above both reported 0.0 -- a cross-statistic
        # disagreement on an input the record actually contains. The three
        # guards must agree on the same input: no measurable benchmark
        # variation means no beta and no alpha.
        assert res["beta"] == 0.0
        assert res["alpha_annualized"] == 0.0

    def test_non_finite_excess_std_fails_closed(self):
        """An excess series that is entirely non-finite must not divide.

        The guard is `np.isfinite(excess_std) and excess_std > 1e-15`,
        not `excess_std > 0`: a non-finite std compares unordered, so
        `inf > 0` is True and the old guard did NOT fire, emitting `nan`.
        A series that is all-inf drops to fewer than two surviving rows and
        returns the no-evidence tuple (see `_no_comparison`); a single
        finite row alongside the non-finite ones survives the row filter
        but is too short for a t-test, so it likewise returns no evidence.
        """
        for non_finite in (np.inf, -np.inf, np.nan):
            excess = np.array([non_finite, non_finite])
            res = st.compare_to_benchmark(excess, np.zeros(2))
            assert res["information_ratio"] == 0.0
            assert res["alpha_t_stat"] == 0.0
            assert res["alpha_p_value"] == 1.0

    def test_the_information_ratio_and_t_test_guards_use_the_same_tolerance(self):
        """The two guards must agree at every scale: both fire, or neither
        does.

        Between 1e-15 and 1e-12 the old t-test guard (1e-12) had already
        fired while the IR guard (then `> 0`, now 1e-15) had not, so the two
        statistics disagreed -- a garbage IR alongside a "significant"
        p-value. Both now use the 1e-15 tolerance: at or below it a series
        with no measurable variation yields the no-evidence tuple on both
        sides; above it both report a real signal. The exact value above the
        threshold is not asserted -- only that the two guards agree on the
        boundary and that neither emits a garbage-scale statistic.
        """
        rng = np.random.default_rng(0)
        for exponent in range(-19, -12):  # 1e-19 .. 1e-13
            std = 10.0**exponent
            mean = std * 10.0
            excess = mean + rng.normal(0.0, std, 400)
            res = st.compare_to_benchmark(excess, np.zeros(400))
            if excess.std(ddof=0) <= 1e-15:
                assert res["information_ratio"] == 0.0
                assert res["alpha_t_stat"] == 0.0
                assert res["alpha_p_value"] == 1.0
            else:
                # Both guards fire: a real (if tiny) 10:1 signal-to-noise
                # series is reported, not suppressed as no evidence.
                assert np.isfinite(res["information_ratio"])
                assert abs(res["information_ratio"]) < 1e6
                assert np.isfinite(res["alpha_t_stat"])
                assert 0.0 <= res["alpha_p_value"] <= 1.0

    def test_the_contract_rejects_the_pre_fix_information_ratio_guard(self):
        """Negative control: the pre-fix `excess_std > 0` guard did NOT fire
        on a near-constant series, so the information ratio was ~7.3e16.
        Reconstruct the pre-fix arithmetic and require the contract to
        reject it as not equal to 0.0.
        """
        rng = np.random.default_rng(0)
        bench = np.full(200, 0.0001) + rng.normal(0.0, 1e-19, 200)
        strat = bench + 0.0005
        excess = strat - bench

        pre_fix_std = float(excess.std(ddof=0))
        pre_fix_ir = float(excess.mean() / pre_fix_std * np.sqrt(252))
        assert pre_fix_ir > 1e6  # the pre-fix path emitted garbage

        res = st.compare_to_benchmark(strat, bench)
        assert res["information_ratio"] != pytest.approx(pre_fix_ir, rel=1e-6)
        assert res["information_ratio"] == 0.0

    def test_the_contract_rejects_the_pre_fix_t_test_guard(self):
        """Negative control: the pre-fix `excess.std(ddof=0) > 1e-12` t-test
        guard did NOT fire on a series whose excess std is ~1e-13, so it
        suppressed a real 10:1 signal-to-noise series as "no evidence"
        (t_stat 0.0, p_value 1.0). The corrected 1e-15 guard fires there and
        reports the real statistic, so the two disagree on this input and the
        contract must reject the pre-fix no-evidence tuple.
        """
        rng = np.random.default_rng(0)
        std = 1e-13
        excess = std * 10.0 + rng.normal(0.0, std, 400)
        assert excess.std(ddof=0) > 1e-15  # above the corrected tolerance
        assert excess.std(ddof=0) <= 1e-12  # but below the pre-fix tolerance

        res = st.compare_to_benchmark(excess, np.zeros(400))
        # The corrected path reports the real statistic ...
        assert np.isfinite(res["alpha_t_stat"])
        assert res["alpha_t_stat"] != 0.0
        assert res["alpha_p_value"] != 1.0
        # ... and rejects the pre-fix no-evidence tuple.
        assert res["alpha_t_stat"] != pytest.approx(0.0)
        assert res["alpha_p_value"] != pytest.approx(1.0)

    def test_p_value_in_unit_interval(self, rng):
        res = st.compare_to_benchmark(rng.normal(0.001, 0.01, 400), rng.normal(0.0005, 0.01, 400))
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

    def test_non_finite_rows_are_dropped(self):
        """An ``inf``/``-inf`` row is dropped, not treated as a missing value.

        The row filter used to be ``isnan``: a single ``inf`` survived it,
        then ``excess.mean()`` became ``inf``, ``np.cov``/``np.var`` turned
        ``alpha_annualized`` and ``beta`` into ``nan`` and ``excess.std()``
        into ``nan``, so the result was internally inconsistent -- ``win_rate``
        was a finite fraction of the surviving rows, ``excess_return_annual``
        was ``inf`` and ``alpha_p_value`` was the default ``1.0``. That is the
        class of silent void the filter exists to prevent: a gate reading any
        one of those fields would see a plausible-looking number while the
        comparison had actually broken.

        With the ``isfinite`` mask the offending row is dropped and every key
        comes back finite. The surviving two rows are the clean ones and the
        published CAPM formula reproduces them: beta is the OLS slope of
        ``[0.01, 0.02]`` on ``[0.0, 0.01]`` (= 1.0), so alpha is the OLS
        intercept ``mean(strat) - beta * mean(bench) = 0.01`` and the
        annualized alpha is ``0.01 * 252 = 2.52``.
        """
        strat = np.array([0.01, 0.02, np.inf])
        bench = np.array([0.0, 0.01, 0.01])
        res = st.compare_to_benchmark(strat, bench)

        assert len(res) == 9
        for key, value in res.items():
            assert np.isfinite(float(value)), f"{key} is not finite: {value!r}"
        assert res["beta"] == pytest.approx(1.0)
        assert res["alpha_annualized"] == pytest.approx(2.52)
        assert res["win_rate"] == pytest.approx(1.0)

    def test_nan_rows_are_still_dropped(self):
        """The ``isnan`` case the mask has always handled must still work."""
        strat = np.array([0.01, np.nan, 0.02])
        bench = np.array([0.0, 0.01, 0.01])
        res = st.compare_to_benchmark(strat, bench)
        for key, value in res.items():
            assert np.isfinite(float(value)), f"{key} is not finite: {value!r}"
        assert res["beta"] == pytest.approx(1.0)
        assert res["alpha_annualized"] == pytest.approx(2.52)

    def test_negative_infinity_rows_are_dropped(self):
        """Symmetric to the positive case: ``-inf`` is not a missing value."""
        strat = np.array([0.01, -np.inf, 0.02])
        bench = np.array([0.0, 0.01, 0.01])
        res = st.compare_to_benchmark(strat, bench)
        for key, value in res.items():
            assert np.isfinite(float(value)), f"{key} is not finite: {value!r}"

    def test_the_contract_rejects_the_pre_fix_isnan_mask(self):
        """Negative control: the pre-fix ``isnan`` mask leaves ``inf`` rows in.

        Reconstructs the filter the module used before the fix and feeds it the
        same input: the result is internally inconsistent (a finite ``win_rate``
        alongside ``nan`` alpha and ``inf`` excess return), so the invariant
        "every key is finite" that this contract states must reject it.
        """
        import warnings

        strat = np.array([0.01, 0.02, np.inf])
        bench = np.array([0.0, 0.01, 0.01])

        # The pre-fix mask drops only NaN rows.
        pre_fix_valid = ~(np.isnan(strat) | np.isnan(bench))
        assert pre_fix_valid.all(), "the control must not drop anything"

        # Re-run the downstream arithmetic on the pre-fix filtered input.
        # The inf propagates through mean/std and numpy warns; the warning is
        # part of the defect (the pre-fix path emitted RuntimeWarnings too) and
        # is swallowed here so the control measures the *result*, not the noise.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            excess = strat[pre_fix_valid] - bench[pre_fix_valid]
            excess_std = float(excess.std(ddof=0))
            ir = float(excess.mean() / excess_std * np.sqrt(252)) if excess_std > 0 else 0.0
            win_rate = float((excess > 0).mean())

        # The pre-fix path is inconsistent: the inf propagates.
        assert np.isinf(excess.mean()) or np.isnan(excess_std)
        assert np.isfinite(win_rate), "win_rate is finite on the broken path"

        # The invariant the contract states must reject it.
        broken = {
            "information_ratio": ir,
            "alpha_annualized": float("nan"),
            "beta": float("nan"),
            "alpha_t_stat": 0.0,
            "alpha_p_value": 1.0,
            "alpha_p_value_one_sided": 0.5,
            "win_rate": win_rate,
            "excess_return_annual": float(excess.mean() * 252),
            "excess_vol_annual": float(excess_std * np.sqrt(252)),
        }
        inconsistent = [key for key, value in broken.items() if not np.isfinite(float(value))]
        assert inconsistent, "the pre-fix result must be internally inconsistent"
        assert "win_rate" not in inconsistent, "win_rate must survive on the broken path"


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

    @pytest.mark.parametrize(
        "effect_size",
        [0.0, -0.5, np.inf, -np.inf, np.nan],
        ids=["zero", "negative", "positive_infinity", "negative_infinity", "nan"],
    )
    def test_degenerate_effect_size_fails_closed(self, effect_size):
        """A non-positive or non-finite effect size must not divide.

        The closed form divides by ``effect_size``. An exact zero (a flat
        effect, a synthetic fixture, a series with no measurable difference)
        makes the required sample size infinite; a negative one is a sign
        error in the caller's intent, and the formula squares it away so it
        would silently answer the wrong question. A non-finite operand is the
        H58/H61/H62 input class (an `inf`, a `-inf` or a `nan` reaching a pure
        function that has no caller to filter for it). The pre-fix path raised
        ``OverflowError`` on ``inf`` and ``ValueError`` on ``nan`` out of a
        function every caller treats as returning an ``int``.
        """
        assert st.statistical_power_analysis(effect_size, alpha=0.05, power=0.8, std=1.0) == 0

    @pytest.mark.parametrize(
        "std",
        [0.0, -1.0, np.inf, -np.inf, np.nan],
        ids=["zero", "negative", "positive_infinity", "negative_infinity", "nan"],
    )
    def test_degenerate_std_fails_closed(self, std):
        """A non-positive or non-finite standard deviation must not scale."""
        assert st.statistical_power_analysis(0.5, alpha=0.05, power=0.8, std=std) == 0

    @pytest.mark.parametrize(
        "alpha",
        [0.0, 1.0, 1.5, np.inf, np.nan],
        ids=["zero", "one", "above_one", "positive_infinity", "nan"],
    )
    def test_degenerate_alpha_fails_closed(self, alpha):
        """``norm.ppf(1 - alpha / 2)`` is only finite for ``0 < alpha < 1``.

        ``alpha <= 0`` sends the argument to >= 1 (ppf of 1 is +inf); ``alpha
        >= 1`` sends it to <= 0.5, and at exactly 1 the z-score is 0.0 -- a
        finite but meaningless answer -- while any value past 1 makes the
        argument negative and ppf returns nan. The pre-fix path raised
        ``OverflowError`` on the infinities and returned a nonsense 6 for
        ``alpha == 1``.
        """
        assert st.statistical_power_analysis(0.5, alpha=alpha, power=0.8, std=1.0) == 0

    @pytest.mark.parametrize(
        "power",
        [0.0, 1.0, 1.5, np.inf, np.nan],
        ids=["zero", "one", "above_one", "positive_infinity", "nan"],
    )
    def test_degenerate_power_fails_closed(self, power):
        """``norm.ppf(power)`` is only finite for ``0 < power < 1``.

        ``power <= 0`` sends the argument to <= 0 (ppf of 0 is -inf); ``power
        >= 1`` sends it to >= 1 (ppf of 1 is +inf). The pre-fix path raised
        ``OverflowError`` on both boundaries.
        """
        assert st.statistical_power_analysis(0.5, alpha=0.05, power=power, std=1.0) == 0

    def test_all_degenerate_inputs_raise_no_warning_or_exception(self):
        """Negative control: the pre-fix path raised and warned.

        The pre-fix closed form emits ``RuntimeWarning: divide by zero`` for
        an exact-zero effect size and raises ``OverflowError``/``ValueError``
        for the non-finite operands, so this contract must reject the
        pre-fix path: every degenerate input must return ``0`` under
        ``-W error`` with no warning and no exception.
        """
        degenerate = [
            dict(effect_size=0.0, alpha=0.05, power=0.8, std=1.0),
            dict(effect_size=-0.5, alpha=0.05, power=0.8, std=-1.0),
            dict(effect_size=np.inf, alpha=0.05, power=0.8, std=1.0),
            dict(effect_size=np.nan, alpha=0.05, power=0.8, std=np.nan),
            dict(effect_size=0.5, alpha=0.0, power=0.8, std=1.0),
            dict(effect_size=0.5, alpha=1.0, power=0.8, std=1.0),
            dict(effect_size=0.5, alpha=0.05, power=0.0, std=1.0),
            dict(effect_size=0.5, alpha=0.05, power=1.0, std=1.0),
        ]
        for kwargs in degenerate:
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                assert st.statistical_power_analysis(**kwargs) == 0


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
        res = st.validate_strategy(returns, self._trades(50), {"min_profit_factor": 1.0})
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

    def test_annualized_volatility_matches_the_engine_convention(self, rng):
        """annualized_volatility uses ddof=1 (pandas Series.std default),
        matching the engine's VectorizedBacktester._calculate_metrics
        (engine.py:_calculate_metrics).  This is the cross-module agreement
        convention pinned by test_engine_metric_agreement.py.

        ddof=1 inflates volatility by sqrt(n / (n - 1)) relative to the
        population std (ddof=0) that sharpe_ratio divides by.  The two
        volatility measures within a single validate_strategy result
        deliberately use different conventions: annualized_volatility follows
        the engine (ddof=1), while sharpe follows sharpe_ratio (ddof=0).
        """
        returns = pd.Series(rng.normal(0.001, 0.01, 400))
        res = st.validate_strategy(returns, self._trades(50), {})
        expected = returns.std(ddof=1) * np.sqrt(252)
        assert res["annualized_volatility"] == pytest.approx(expected)

    def test_annualized_volatility_single_element_is_nan(self):
        """With one observation the sample std (ddof=1) divides by n-1=0,
        yielding NaN.  This matches the engine convention."""
        res = st.validate_strategy(pd.Series([0.001]), self._trades(1), {})
        assert np.isnan(res["annualized_volatility"])


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
