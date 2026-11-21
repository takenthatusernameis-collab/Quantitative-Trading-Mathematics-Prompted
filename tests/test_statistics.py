"""Regression tests for src/qtr/validation/statistics.py.

These tests pin the mathematical validation core used by every H1-H25
experiment runner. The module was at ~12% coverage before this suite:
only sharpe_ratio was exercised by the runners. Each function gets
deterministic, seeded assertions plus edge-case guards (empty input,
zero-variance, monotonicity) so a regression in the statistical core
is caught as a hard failure rather than a silent drift in the
certified H10-H14 numbers.
"""

import datetime
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

    @pytest.mark.parametrize("bad", [np.inf, -np.inf, np.nan])
    def test_non_finite_data_fail_closed(self, bad):
        # The H58/H61/H62 input class: an `inf`, a `-inf` or a `nan` reaching
        # a pure function that has no caller to filter for it. The resample
        # draws the bad element into ``bootstrap_stats`` and ``np.percentile``
        # then interpolates across it, raising
        # ``RuntimeWarning: invalid value encountered in scalar subtract`` out
        # of a function every caller treats as returning a tuple of two
        # floats. The result was also internally inconsistent by accident:
        # ``bootstrap([inf, 1, 2])`` returned ``(1.158, nan)`` -- one finite
        # bound and one void -- so a caller reading the interval saw half an
        # answer.
        lo, hi = st.bootstrap_confidence_interval(
            np.array([1.0, 2.0, 3.0, bad]), n_bootstrap=20, random_state=42
        )
        assert np.isnan(lo) and np.isnan(hi), f"bad={bad}"

    def test_the_contract_rejects_the_pre_fix_non_finite_subtract(self):
        """Negative control: reconstruct the pre-fix body and require that it
        emits the warning and the half-finite interval this contract exists to
        prevent. The corrected function returns ``(nan, nan)`` on every
        non-finite input."""

        def pre_fix(data, statistic=np.mean, confidence=0.95, n_bootstrap=1000, random_state=None):
            rng = np.random.default_rng(random_state)
            n = len(data)
            if n == 0:
                return (np.nan, np.nan)
            if n_bootstrap <= 0 or not (0.0 < confidence <= 1.0):
                return (np.nan, np.nan)
            bootstrap_stats = []
            for _ in range(n_bootstrap):
                sample = data[rng.integers(0, n, n)]
                bootstrap_stats.append(statistic(sample))
            alpha = (1 - confidence) / 2
            lower = np.percentile(bootstrap_stats, 100 * alpha)
            upper = np.percentile(bootstrap_stats, 100 * (1 - alpha))
            return (lower, upper)

        data = np.array([1.0, 2.0, 3.0, np.inf])
        # The pre-fix body emits the numpy warning the corrected function
        # swallows.
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            lo, hi = pre_fix(data, n_bootstrap=20, random_state=42)
        assert any(
            issubclass(w.category, RuntimeWarning) and "subtract" in str(w.message) for w in caught
        )
        # And it returns a half-finite interval: one bound finite, one void.
        assert np.isfinite(lo) and np.isnan(hi)

        # The corrected function returns the no-evidence tuple instead.
        lo, hi = st.bootstrap_confidence_interval(data, n_bootstrap=20, random_state=42)
        assert np.isnan(lo) and np.isnan(hi)


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

    def test_walk_forward_splits_fail_closed_on_degenerate_scalars(self):
        """Config-degenerate scalar parameters must not raise.

        ``train_ratio``/``gap``/``n_samples`` are bare scalars a caller
        cannot filter on its own. A non-finite ``train_ratio`` used to
        raise ``ValueError: cannot convert float NaN to integer`` at
        ``int(len * train_ratio)``; a non-finite ``gap`` or ``n_samples``
        raised ``ValueError`` from ``np.arange``/window arithmetic. All
        must fail closed to ``[]`` -- the same no-evidence result as an
        empty or degenerate window.
        """
        import warnings

        for bad_ratio in (float("nan"), float("inf"), float("-inf")):
            with warnings.catch_warnings():
                warnings.simplefilter("error", RuntimeWarning)
                assert st.walk_forward_splits(100, train_ratio=bad_ratio) == []
        for bad_gap in (float("nan"), float("inf"), float("-inf"), -1):
            assert st.walk_forward_splits(100, gap=bad_gap) == []
        for bad_n in (float("nan"), float("inf"), float("-inf"), -5):
            assert st.walk_forward_splits(bad_n) == []
        for bad_splits in (float("nan"), float("inf"), float("-inf")):
            assert st.walk_forward_splits(100, n_splits=bad_splits) == []

    def test_walk_forward_splits_degenerate_contract_rejects_pre_fix(self):
        """Behavioural negative control: the pre-fix arithmetic must raise.

        Reconstructs the pre-fix ``int(len(window_indices) * train_ratio)``
        and ``np.arange(split_point + gap, end)`` paths on a degenerate
        scalar and requires both to be rejected by the fail-closed contract.
        """
        window = np.arange(0, 20)
        with pytest.raises(ValueError):
            _ = int(len(window) * float("nan"))
        with pytest.raises(ValueError):
            _ = np.arange(14 + float("nan"), 20)
        assert st.walk_forward_splits(100, train_ratio=float("nan")) == []
        assert st.walk_forward_splits(100, gap=float("nan")) == []

    def test_walk_forward_splits_rejects_non_integer_operands(self):
        """n_samples, n_splits and gap are bare count scalars; a non-integer
        (float or bool) must fail closed to ``[]`` rather than crash on the
        ``range(n_splits)``/window arithmetic, matching the purged/CV operand
        contract in _purged_cv_operands_valid."""
        for bad_splits in (5.0, 2.5, 0.5, True, False, np.float64(3.0)):
            assert st.walk_forward_splits(100, n_splits=bad_splits) == []
        for bad_n in (10.0, 10.5, True, False, np.float64(50.0)):
            assert st.walk_forward_splits(bad_n, n_splits=5) == []
        for bad_gap in (1.5, 2.0, True, False, np.float64(1.0)):
            assert st.walk_forward_splits(100, n_splits=5, gap=bad_gap) == []

    def test_walk_forward_splits_accepts_integer_and_np_integer(self):
        """Finite integer and np.integer operands are unaffected: the clean
        path is bit-identical to before the guard."""
        assert len(st.walk_forward_splits(100, n_splits=5)) == 5
        assert len(st.walk_forward_splits(100, n_splits=np.int64(5), gap=np.int64(2))) == 5
        a = st.walk_forward_splits(100, n_splits=5, gap=0)
        b = st.walk_forward_splits(100, n_splits=np.int64(5), gap=np.int64(0))
        assert len(a) == len(b)
        for (ta, tb), (ua, ub) in zip(a, b):
            assert np.array_equal(ta, ua)
            assert np.array_equal(tb, ub)

    def test_walk_forward_splits_non_integer_contract_rejects_pre_fix(self):
        """Behavioural negative control: the pre-fix ``range(n_splits)`` must
        raise on a float split count, so the fail-closed contract is required."""
        with pytest.raises(TypeError):
            _ = list(range(float("nan")))
        assert st.walk_forward_splits(100, n_splits=float("nan")) == []


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
# multiple_testing_correction: alpha operand guard
# ===========================================================================
class TestMultipleTestingCorrectionAlphaGuard:
    """Degenerate-operand guard on ``alpha``. The significance level is the
    threshold the adjusted p-values are compared against in BOTH branches
    (``adjusted < alpha``), so a degenerate ``alpha`` does not just corrupt
    one test -- it inverts the decision for the entire set."""

    DEGENERATE_ALPHAS = [
        (np.inf, "positive_infinity"),
        (-np.inf, "negative_infinity"),
        (np.nan, "nan"),
        (0.0, "zero"),
        (1.0, "one"),
        (1.5, "above_one"),
        (-0.1, "negative"),
    ]

    @pytest.mark.parametrize("method", ["bonferroni", "benjamini_hochberg"])
    @pytest.mark.parametrize("alpha, _id", DEGENERATE_ALPHAS, ids=[i for _, i in DEGENERATE_ALPHAS])
    def test_degenerate_alpha_fail_closed(self, method, alpha, _id):
        """A non-finite or out-of-range ``alpha`` is not a significance level,
        and the correction must not manufacture a rejection or acceptance
        out of it.

        Pre-fix behaviour, measured on this input class:
        - ``alpha=inf``: ``adjusted < inf`` is True for every finite adjusted
          p-value, so the correction REJECTS every test (manufactured all-reject).
        - ``alpha=nan``: ``adjusted < nan`` is False (unordered), so the
          correction rejects nothing (manufactured all-accept).
        - ``alpha=-inf``: same as nan, all-accept.
        - ``alpha <= 0``: ``adjusted < 0`` is False for adjusted in [0, 1],
          so the correction rejects nothing (degenerate boundary).
        - ``alpha >= 1``: at ``alpha == 1`` the comparison ``adjusted < 1``
          accepts any test not capped at 1.0 (significance floor drops out);
          for ``alpha > 1`` the comparison is True for all finite adjusted
          values, so the correction rejects everything (vacuous gate).

        The fail-closed result is the no-evidence tuple: every test left
        unadjusted (adjusted p-value 1.0, the maximally non-significant
        value) and nothing rejected.
        """
        p = np.array([0.01, 0.04, 0.5, 0.001])
        rejected, adjusted = st.multiple_testing_correction(p, method, alpha)
        assert rejected.tolist() == [False] * len(p)
        assert adjusted.tolist() == [1.0] * len(p)

    @pytest.mark.parametrize("method", ["bonferroni", "benjamini_hochberg"])
    def test_the_contract_rejects_the_pre_fix_alpha_behaviour(self, method):
        """Negative control: reconstruct the pre-fix comparison on a degenerate
        alpha and require the contract to reject it.

        The pre-fix comparison ``adjusted < alpha`` produced manufactured
        decisions (all-reject or all-accept) on these inputs; the corrected
        function must return the no-evidence tuple instead.
        """
        p = np.array([0.01, 0.04, 0.5, 0.001])
        n = len(p)

        # Pre-fix arithmetic for bonferroni
        adjusted_pre = np.minimum(p * n, 1.0)

        # inf: pre-fix rejects all
        pre_fix_inf = bool(np.all(adjusted_pre < np.inf))
        assert pre_fix_inf is True

        # nan: pre-fix rejects none (unordered)
        pre_fix_nan = bool(np.all(adjusted_pre < np.nan))
        assert pre_fix_nan is False

        # 1.5: pre-fix rejects all
        pre_fix_high = bool(np.all(adjusted_pre < 1.5))
        assert pre_fix_high is True

        # 0.0: pre-fix rejects none
        pre_fix_zero = bool(np.any(adjusted_pre < 0.0))
        assert pre_fix_zero is False

        # The corrected function returns the no-evidence tuple for all.
        for bad_alpha in (np.inf, np.nan, -np.inf, 0.0, 1.0, 1.5, -0.1):
            rejected, adjusted = st.multiple_testing_correction(p, method, bad_alpha)
            assert rejected.tolist() == [False] * len(p)
            assert adjusted.tolist() == [1.0] * len(p)

    @pytest.mark.parametrize("method", ["bonferroni", "benjamini_hochberg"])
    def test_valid_alpha_unchanged(self, method):
        """A finite alpha in (0, 1) computes the standard arithmetic."""
        p = np.array([0.01, 0.04, 0.5, 0.001])
        # 0.05 is the default and a standard significance level
        rejected, adjusted = st.multiple_testing_correction(p, method, 0.05)
        # Just verify it returns a valid result (not the no-evidence tuple)
        assert len(rejected) == len(p)
        assert len(adjusted) == len(p)
        # At least one should be rejected with valid inputs
        if method == "bonferroni":
            assert rejected[3]  # p=0.001 * 4 = 0.004 < 0.05
            assert adjusted[3] == pytest.approx(0.004)


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

    def test_one_dimensional_returns_fail_closed(self):
        """A 1-D ``returns`` violates the "2D: n_params x n_obs" contract.

        A 1-D array's ``shape[0]`` is its length, so a long 1-D series slipped
        past ``shape[0] < n_params`` and the per-row loop then scored a SCALAR:
        ``bootstrap_confidence_interval`` reduced that scalar to a 0-D array and
        ``len()`` of it raised ``TypeError: len() of unsized object`` out of a
        function every caller treats as returning a dict. The fail-closed
        result is the empty-grid tuple.
        """
        res = st.parameter_sensitivity(
            np.random.default_rng(0).normal(size=50), np.array([1.0, 2.0, 3.0]), n_bootstrap=10
        )
        assert res["metrics"].shape == (0,)
        assert res["stability_ratio"] == 0.0
        assert np.isnan(res["optimal_param"])

    def test_scalar_returns_fail_closed(self):
        """A 0-D ``returns`` has no ``shape[0]`` to compare; it fails closed."""
        res = st.parameter_sensitivity(np.float64(1.0), np.array([1.0, 2.0]), n_bootstrap=10)
        assert res["metrics"].shape == (0,)
        assert np.isnan(res["optimal_param"])

    def test_three_dimensional_returns_fail_closed(self):
        """A 3-D ``returns`` would score 2-D slices and emit the wrong shape."""
        res = st.parameter_sensitivity(np.zeros((2, 3, 4)), np.array([1.0, 2.0]), n_bootstrap=10)
        assert res["metrics"].shape == (0,)
        assert np.isnan(res["optimal_param"])

    def test_the_contract_rejects_the_pre_fix_one_dimensional_crash(self):
        # Behavioural negative control: reconstruct the pre-fix per-row scoring
        # of a 1-D ``returns`` and require it to raise the ``TypeError`` the
        # shape guard now prevents, proving the guard is what makes the call
        # safe rather than merely lucky.
        returns = np.random.default_rng(0).normal(size=50)
        with pytest.raises(TypeError):
            _ = len(np.asarray(returns[0], dtype=float))

        res = st.parameter_sensitivity(returns, np.array([1.0, 2.0, 3.0]), n_bootstrap=10)
        assert res["metrics"].shape == (0,)

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

    # ------------------------------------------------------------------
    # Degenerate inputs: fail closed, no warning, no exception.
    # ------------------------------------------------------------------
    @pytest.mark.parametrize("bad", [np.inf, -np.inf, np.nan])
    def test_non_finite_returns_fail_closed(self, bad):
        # The H58/H61/H62 input class: an `inf`, a `-inf` or a `nan` reaching
        # a pure function that has no caller to filter for it. The old
        # function walked into ``regime_returns.mean()`` / ``.std()`` on the
        # non-finite regime and, under ``pytest -W error``, raised
        # ``RuntimeWarning: invalid value encountered in subtract`` out of a
        # function every caller treats as returning a dict. The fail-closed
        # result is the empty dict: no regime, no metric, no evidence.
        res = st.regime_analysis(
            np.array([0.001, bad, 0.001, -0.001]),
            np.array(["up", "up", "down", "down"]),
        )
        assert res == {}

    def test_empty_returns_fail_closed(self):
        # The fetcher's documented "no data" path returns an empty frame per
        # symbol (fetcher.py:196), and a runner that passes every symbol
        # through the engine hands an empty panel straight here. The old
        # function returned an empty dict by construction (no regimes to
        # iterate); the guard keeps that contract explicit rather than
        # incidental.
        assert st.regime_analysis(np.array([]), np.array([])) == {}

    def test_the_contract_rejects_the_pre_fix_non_finite_subtract(self):
        # Behavioural negative control: reconstruct the pre-fix loop (no
        # ``isfinite`` screen) and require it to raise the numpy warning the
        # corrected function swallows, proving the guard is what makes the
        # call safe rather than merely lucky.
        returns = np.array([0.001, np.inf, 0.001, -0.001])
        labels = np.array(["up", "up", "down", "down"])

        def pre_fix(returns, labels, metric_func=st.sharpe_ratio):
            results = {}
            for regime in np.unique(labels):
                regime_returns = returns[labels == regime]
                if len(regime_returns) > 1:
                    results[f"regime_{regime}_sharpe"] = metric_func(regime_returns)
                    results[f"regime_{regime}_count"] = len(regime_returns)
                    results[f"regime_{regime}_mean"] = regime_returns.mean()
                    results[f"regime_{regime}_std"] = regime_returns.std()
            return results

        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            with pytest.raises(RuntimeWarning):
                pre_fix(returns, labels)

        # And the corrected function returns the empty dict on the same input.
        assert st.regime_analysis(returns, labels) == {}

    @pytest.mark.parametrize(
        "returns,labels",
        [
            (np.array([0.001, 0.002, 0.003]), np.array(["up", "down"])),
            (np.array([0.001, 0.002]), np.array(["up", "down", "up", "down"])),
        ],
    )
    def test_length_mismatch_between_returns_and_labels_fails_closed(self, returns, labels):
        # A per-regime statistic pairs every return with the label at the same
        # position, so the two must be the same length. A mismatch used to walk
        # into ``returns[labels == regime]`` and raise ``IndexError: boolean
        # index did not match indexed array`` -- a crash out of a pure function
        # every caller treats as returning a dict, reachable from the public API
        # when a runner drops NaN rows from one side but not the other. The
        # fail-closed result is the empty dict: no regime, no metric.
        assert st.regime_analysis(returns, labels) == {}

    @pytest.mark.parametrize(
        "returns,labels",
        [
            (np.array(0.001), np.array(["up"])),
            (np.array([0.001, 0.002]), np.array("up")),
            (np.ones((2, 3)), np.array(["up", "down"])),
        ],
    )
    def test_non_1d_inputs_fail_closed(self, returns, labels):
        # A per-observation label set is 1-D. A scalar ``returns`` makes the
        # boolean-mask indexing raise (``too many indices``); a scalar
        # ``labels`` compares to a scalar rather than element-wise; a 2-D
        # ``returns`` would select rows rather than observations. All are the
        # same malformed-shape class and fail closed to the empty dict.
        assert st.regime_analysis(returns, labels) == {}

    def test_the_contract_rejects_the_pre_fix_length_mismatch_crash(self):
        # Behavioural negative control: reconstruct the pre-fix masking on a
        # length-mismatched pair and require it to raise the ``IndexError`` the
        # shape guard now prevents, proving the guard is what makes the call
        # safe rather than merely lucky.
        returns = np.array([0.001, 0.002, 0.003])
        labels = np.array(["up", "down"])

        with pytest.raises(IndexError):
            _ = returns[labels == "up"]

        assert st.regime_analysis(returns, labels) == {}


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

    # ------------------------------------------------------------------
    # Degenerate inputs: fail closed, no warning, no exception.
    # ------------------------------------------------------------------
    KEYS = ["commission", "spread", "slippage", "impact", "combined"]

    def _no_evidence(self):
        return {f"stressed_{k}_sharpe": 0.0 for k in self.KEYS} | {
            f"stressed_{k}_return": 0.0 for k in self.KEYS
        }

    @pytest.mark.parametrize("bad", [np.inf, -np.inf, np.nan])
    def test_non_finite_returns_fail_closed(self, bad):
        # The H58/H61/H62 input class: an `inf`, a `-inf` or a `nan` reaching
        # a pure function with no caller to filter for it. The old function
        # carried the non-finite value through every `stressed_*_return`
        # (mean * 252) while `sharpe_ratio` already failed closed to 0.0 on
        # the same series, so the two halves of each entry disagreed.
        res = st.stressed_cost_test(np.array([0.001, bad, 0.001]), np.array([0.0, 0.0, 0.0]))
        assert res == self._no_evidence()

    @pytest.mark.parametrize("bad", [np.inf, -np.inf, np.nan])
    def test_non_finite_costs_fail_closed(self, bad):
        res = st.stressed_cost_test(np.array([0.001, 0.001, 0.001]), np.array([0.0, bad, 0.0]))
        assert res == self._no_evidence()

    def test_empty_arrays_fail_closed(self):
        # Zero bars: the old function raised `RuntimeWarning: Mean of an
        # empty slice` from the first stressor's `mean()` and then crashed on
        # the combined stressor's `sum(...) / len(...)` with ZeroDivisionError.
        res = st.stressed_cost_test(np.array([]), np.array([]))
        assert res == self._no_evidence()

    def test_custom_empty_stress_dict_fails_closed(self):
        # A caller who passes `{}` gets no stressors, so the combined stressor
        # divides by zero; the fail-closed result is the combined entry alone.
        res = st.stressed_cost_test(np.array([0.0] * 5), np.array([0.0] * 5), {})
        assert res == {"stressed_combined_sharpe": 0.0, "stressed_combined_return": 0.0}

    def test_custom_stress_dict_with_non_finite_input(self):
        res = st.stressed_cost_test(
            np.array([0.0, np.inf]), np.array([0.0, 0.0]), {"x": 2.0, "y": 3.0}
        )
        assert res == {
            "stressed_x_sharpe": 0.0,
            "stressed_x_return": 0.0,
            "stressed_y_sharpe": 0.0,
            "stressed_y_return": 0.0,
            "stressed_combined_sharpe": 0.0,
            "stressed_combined_return": 0.0,
        }

    @pytest.mark.parametrize("rb", [np.inf, -np.inf, np.nan])
    @pytest.mark.parametrize("rc", [np.inf, -np.inf, np.nan])
    def test_both_inputs_non_finite_fail_closed(self, rb, rc):
        # Both inputs non-finite: the arithmetic
        # ``base_returns - base_costs * mult`` walks the non-finite value into
        # every stressor's stressed-returns series and numpy raises
        # ``RuntimeWarning: invalid value encountered in subtract`` out of a
        # function every caller treats as returning a dict. The corrected
        # function returns the no-evidence tuple.
        res = st.stressed_cost_test(np.array([0.001, rb, 0.001]), np.array([0.0001, rc, 0.0001]))
        assert res == self._no_evidence()

    @pytest.mark.parametrize("bad", [np.inf, -np.inf, np.nan])
    def test_fail_closed_annualized_mean_helper(self, bad):
        # The ``_fail_closed_annualized_mean`` helper is the return half of
        # every stressor entry. It must fail closed to 0.0 on a non-finite
        # series with no warning and no exception, independently of the
        # ``stressed_cost_test`` guard above (which now short-circuits before
        # the helper is reached, so the helper needs its own direct test to
        # keep the branch covered).
        assert st._fail_closed_annualized_mean(np.array([0.001, bad, 0.001])) == 0.0
        assert st._fail_closed_annualized_mean(np.array([])) == 0.0
        # A finite series is annualised unchanged.
        assert st._fail_closed_annualized_mean(np.array([0.001] * 252)) == pytest.approx(0.252)

    def test_the_contract_rejects_the_pre_fix_both_non_finite_subtract(self):
        """Negative control: reconstruct the pre-fix body and require that it
        emits the numpy warning this contract exists to prevent. The
        corrected function returns the no-evidence tuple on both-non-finite
        input."""

        def pre_fix(base_returns, base_costs, stress_multipliers=None):
            if stress_multipliers is None:
                stress_multipliers = {
                    "commission": 2.0,
                    "spread": 2.0,
                    "slippage": 2.0,
                    "impact": 5.0,
                }
            results = {}
            for name, mult in stress_multipliers.items():
                stressed_costs = base_costs * mult
                stressed_returns = base_returns - stressed_costs
                results[f"stressed_{name}_sharpe"] = st.sharpe_ratio(stressed_returns)
                results[f"stressed_{name}_return"] = stressed_returns.mean() * 252
            total_stress = sum(stress_multipliers.values()) / len(stress_multipliers)
            combined_costs = base_costs * total_stress
            combined_returns = base_returns - combined_costs
            results["stressed_combined_sharpe"] = st.sharpe_ratio(combined_returns)
            results["stressed_combined_return"] = combined_returns.mean() * 252
            return results

        # The pre-fix body emits the numpy warning the corrected function
        # swallows, and its `return` half is non-finite alongside a 0.0 Sharpe.
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            pf = pre_fix(np.array([0.001, np.inf, 0.001]), np.array([0.0001, np.inf, 0.0001]))
        assert any(
            issubclass(w.category, RuntimeWarning) and "subtract" in str(w.message) for w in caught
        )
        assert not np.isfinite(pf["stressed_commission_return"])
        assert pf["stressed_commission_sharpe"] == 0.0

        # The corrected function returns the no-evidence tuple instead.
        assert (
            st.stressed_cost_test(
                np.array([0.001, np.inf, 0.001]), np.array([0.0001, np.inf, 0.0001])
            )
            == self._no_evidence()
        )

    def test_the_contract_rejects_the_pre_fix_behaviour(self):
        """Negative control: reconstruct the pre-fix function body and require
        that it either raises or emits the inconsistent split this contract
        exists to prevent. The corrected function returns the no-evidence
        tuple on every degenerate input."""

        def pre_fix(base_returns, base_costs, stress_multipliers=None):
            if stress_multipliers is None:
                stress_multipliers = {
                    "commission": 2.0,
                    "spread": 2.0,
                    "slippage": 2.0,
                    "impact": 5.0,
                }
            results = {}
            for name, mult in stress_multipliers.items():
                stressed_returns = base_returns - base_costs * mult
                results[f"stressed_{name}_sharpe"] = st.sharpe_ratio(stressed_returns)
                results[f"stressed_{name}_return"] = stressed_returns.mean() * 252
            total_stress = sum(stress_multipliers.values()) / len(stress_multipliers)
            combined_returns = base_returns - base_costs * total_stress
            results["stressed_combined_sharpe"] = st.sharpe_ratio(combined_returns)
            return results

        # Non-finite input: the pre-fix body emits inf returns alongside 0.0
        # Sharpes -- the inconsistent split.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            pf = pre_fix(np.array([0.001, np.inf, 0.001]), np.array([0.0, 0.0, 0.0]))
        assert pf["stressed_commission_return"] != pf["stressed_commission_sharpe"]
        assert not np.isfinite(pf["stressed_commission_return"])
        assert pf["stressed_commission_sharpe"] == 0.0

        # Empty input: the pre-fix body does not fail closed -- with the
        # default stressors it emits a non-finite `return` alongside a `0.0`
        # Sharpe (the inconsistent split this contract exists to prevent).
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            pf = pre_fix(np.array([]), np.array([]))
        assert pf["stressed_commission_sharpe"] == 0.0
        assert not np.isfinite(pf["stressed_commission_return"])

        # Empty stress dict: the pre-fix body raises ZeroDivisionError.
        with pytest.raises(ZeroDivisionError):
            pre_fix(np.array([0.0] * 5), np.array([0.0] * 5), {})

        # The corrected function returns the no-evidence tuple in all three
        # cases instead.
        assert (
            st.stressed_cost_test(np.array([0.001, np.inf, 0.001]), np.array([0.0, 0.0, 0.0]))
            == self._no_evidence()
        )
        assert st.stressed_cost_test(np.array([]), np.array([])) == self._no_evidence()
        assert st.stressed_cost_test(np.array([0.0] * 5), np.array([0.0] * 5), {}) == {
            "stressed_combined_sharpe": 0.0,
            "stressed_combined_return": 0.0,
        }

    # ------------------------------------------------------------------
    # Degenerate stress multipliers: fail closed, no warning, no exception.
    # A stress multiplier scales the cost that is SUBTRACTED from the return,
    # so a negative multiplier is a sign error that ADDS to the return and
    # manufactures P&L -- the same "a cost is a charge" fail-open the module
    # closes on every other cost operand.
    # ------------------------------------------------------------------
    def _zero_for(self, *names):
        return (
            {f"stressed_{k}_sharpe": 0.0 for k in names}
            | {f"stressed_{k}_return": 0.0 for k in names}
            | {"stressed_combined_sharpe": 0.0, "stressed_combined_return": 0.0}
        )

    @pytest.mark.parametrize("bad", [-1.0, -2.0, -0.001, -100.0])
    def test_negative_multiplier_fails_closed(self, bad):
        # A negative multiplier used to inflate the "stressed" return above the
        # honest (positive-multiplier) one; it must fail closed to the
        # no-evidence tuple instead.
        res = st.stressed_cost_test(
            np.array([0.001, 0.002, 0.0015, 0.001]),
            np.array([0.0005, 0.0005, 0.0005, 0.0005]),
            {"commission": bad},
        )
        assert res == self._zero_for("commission")

    @pytest.mark.parametrize("bad", [np.inf, -np.inf, np.nan])
    def test_non_finite_multiplier_fails_closed(self, bad):
        res = st.stressed_cost_test(
            np.array([0.001, 0.002, 0.0015, 0.001]),
            np.array([0.0005, 0.0005, 0.0005, 0.0005]),
            {"impact": bad},
        )
        assert res == self._zero_for("impact")

    @pytest.mark.parametrize("bad", ["2.0", None, [1.0, 2.0], {"x": 1.0}, True, False])
    def test_non_numeric_multiplier_fails_closed(self, bad):
        res = st.stressed_cost_test(
            np.array([0.001, 0.002]), np.array([0.0005, 0.0005]), {"spread": bad}
        )
        assert res == self._zero_for("spread")

    def test_negative_multiplier_never_inflates_return(self):
        base_returns = np.array([0.001] * 10)
        base_costs = np.array([0.0005] * 10)
        honest = st.stressed_cost_test(base_returns, base_costs, {"commission": 1.0})
        negative = st.stressed_cost_test(base_returns, base_costs, {"commission": -1.0})
        # The fail-closed result is 0.0, which can never exceed the honest
        # positive-multiplier stress (nor the zero-cost compound return).
        zero_cost = float(base_returns.mean() * 252)
        assert negative["stressed_commission_return"] == 0.0
        assert negative["stressed_commission_return"] <= honest["stressed_commission_return"]
        assert negative["stressed_commission_return"] <= zero_cost

    @pytest.mark.parametrize("mult", [2.0, 2, np.float64(2.0), np.int64(2), 0.0, 0])
    def test_valid_multiplier_unchanged(self, mult):
        # Every finite, non-negative multiplier is bit-identical to the
        # pre-guard arithmetic.
        base_returns = np.array([0.001, -0.0005, 0.002, 0.0])
        base_costs = np.array([0.0004, 0.0004, 0.0004, 0.0004])
        res = st.stressed_cost_test(base_returns, base_costs, {"impact": mult})
        stressed_returns = base_returns - base_costs * float(mult)
        assert res["stressed_impact_return"] == pytest.approx(float(stressed_returns.mean() * 252))
        assert res["stressed_impact_sharpe"] == pytest.approx(
            float(st.sharpe_ratio(stressed_returns))
        )

    def test_the_contract_rejects_the_pre_fix_negative_multiplier(self):
        """Negative control: the pre-fix body subtracted ``base_costs * mult``,
        so a negative multiplier ADDED to the return and inflated it above the
        honest positive-multiplier stress. The corrected function fails closed
        to the no-evidence tuple instead."""

        def pre_fix(base_returns, base_costs, mult):
            stressed_returns = base_returns - base_costs * mult
            return float(stressed_returns.mean() * 252)

        base_returns = np.array([0.001] * 10)
        base_costs = np.array([0.0005] * 10)
        honest = pre_fix(base_returns, base_costs, 1.0)  # 0.126
        inflated = pre_fix(base_returns, base_costs, -1.0)  # 0.378, manufactured P&L
        assert inflated > honest
        res = st.stressed_cost_test(base_returns, base_costs, {"commission": -1.0})
        assert res == self._zero_for("commission")


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

    @pytest.mark.parametrize(
        "bad", [True, False, "1000000", None, [1_000_000.0], {"adv": 1_000_000.0}]
    )
    def test_non_numeric_or_bool_adv_fail_closed(self, rng, bad):
        # A bool is not a volume (it would be coerced to 0/1 and fabricate
        # capacity) and a non-numeric scalar cannot be a finite volume; both
        # must fail closed to the no-capacity tuple rather than raising or
        # returning a fabricated AUM.
        res = st.capacity_estimate(rng.normal(0.001, 0.01, 400), adv=bad)
        assert res == {
            "current_sharpe": 0.0,
            "max_participation_rate": 0.0,
            "estimated_max_aum": 0.0,
            "sharpe_at_max_aum": 0.0,
        }

    @pytest.mark.parametrize("bad", [np.inf, -np.inf, np.nan, -1.0])
    def test_degenerate_adv_fail_closed(self, rng, bad):
        res = st.capacity_estimate(rng.normal(0.001, 0.01, 400), adv=bad)
        assert res == {
            "current_sharpe": 0.0,
            "max_participation_rate": 0.0,
            "estimated_max_aum": 0.0,
            "sharpe_at_max_aum": 0.0,
        }

    @pytest.mark.parametrize("bad", [True, False, "0.1", None, [0.1], {"max_participation": 0.1}])
    def test_non_numeric_or_bool_max_participation_fail_closed(self, rng, bad):
        res = st.capacity_estimate(
            rng.normal(0.001, 0.01, 400), adv=1_000_000.0, max_participation=bad
        )
        assert res == {
            "current_sharpe": 0.0,
            "max_participation_rate": 0.0,
            "estimated_max_aum": 0.0,
            "sharpe_at_max_aum": 0.0,
        }

    @pytest.mark.parametrize("bad", [np.inf, -np.inf, np.nan, -0.1])
    def test_degenerate_max_participation_fail_closed(self, rng, bad):
        res = st.capacity_estimate(
            rng.normal(0.001, 0.01, 400), adv=1_000_000.0, max_participation=bad
        )
        assert res == {
            "current_sharpe": 0.0,
            "max_participation_rate": 0.0,
            "estimated_max_aum": 0.0,
            "sharpe_at_max_aum": 0.0,
        }

    def test_custom_impact_model_used(self, rng):
        returns = rng.normal(0.001, 0.01, 400)

        def impact(p):
            return 50.0 * p

        res = st.capacity_estimate(returns, adv=1_000_000.0, impact_model=impact)
        assert res["max_participation_rate"] > 0.0

    # ------------------------------------------------------------------
    # Degenerate inputs: fail closed, no warning, no exception.
    # ------------------------------------------------------------------
    def _no_capacity(self):
        return {
            "current_sharpe": 0.0,
            "max_participation_rate": 0.0,
            "estimated_max_aum": 0.0,
            "sharpe_at_max_aum": 0.0,
        }

    def test_empty_returns_fail_closed(self):
        # An empty return series is the fetcher's documented "no data" path
        # (fetcher.py:196 returns an empty frame per symbol on a fetch
        # failure, and a runner that passes every symbol through the engine
        # hands that empty panel straight here). The old function walked
        # into the binary search anyway and reported a **positive capacity
        # claim from no data**: ``max_participation_rate ~= 0.1`` and
        # ``estimated_max_aum ~= adv * 0.1``. The fail-closed result is the
        # no-capacity tuple.
        assert st.capacity_estimate(np.array([]), adv=1_000_000.0) == self._no_capacity()

    @pytest.mark.parametrize("bad", [np.inf, -np.inf, np.nan])
    def test_non_finite_returns_fail_closed(self, bad):
        # The H58/H61/H62 input class: an `inf`, a `-inf` or a `nan` reaching
        # a pure function that has no caller to filter for it. ``sharpe_ratio``
        # already fails closed to 0.0 on it, so the pre-fix binary search did
        # not raise -- it **converged to a positive participation rate** and
        # the function reported a capacity it could not justify. The
        # fail-closed result is the no-capacity tuple.
        res = st.capacity_estimate(np.array([0.001, bad, 0.001]), adv=1_000_000.0)
        assert res == self._no_capacity()

    def test_the_contract_rejects_the_pre_fix_non_finite_capacity_claim(self):
        # Behavioural negative control: reconstruct the pre-fix body (no
        # degenerate-input guard) and require it to report a **positive**
        # participation rate on a non-finite series -- a capacity claim
        # manufactured from an impossible return -- while the corrected
        # function reports zero. ``sharpe_ratio`` fails closed to 0.0 on the
        # non-finite input, so the pre-fix path does not raise; the defect is
        # the fabricated positive answer, not an exception.
        def pre_fix(returns, adv, max_participation=0.1, impact_model=None):
            if impact_model is None:

                def impact_model(p):
                    return 10 * np.sqrt(p / 0.01)

            current_sharpe = st.sharpe_ratio(returns)
            target_sharpe = current_sharpe * 0.5
            low, high = 0.0, max_participation
            for _ in range(20):
                mid = (low + high) / 2
                adj_sharpe = st.sharpe_ratio(returns - impact_model(mid) / 10000)
                if adj_sharpe >= target_sharpe:
                    low = mid
                else:
                    high = mid
            rate = (low + high) / 2
            return {
                "current_sharpe": current_sharpe,
                "max_participation_rate": rate,
                "estimated_max_aum": rate * adv * 100,
                "sharpe_at_max_aum": st.sharpe_ratio(returns - impact_model(rate) / 10000),
            }

        pre = pre_fix(np.array([0.001, np.inf, 0.001]), 1_000_000.0)
        assert pre["max_participation_rate"] > 0.0
        assert pre["estimated_max_aum"] > 0.0

        # And the corrected function returns the no-capacity tuple.
        assert (
            st.capacity_estimate(np.array([0.001, np.inf, 0.001]), adv=1_000_000.0)
            == self._no_capacity()
        )

    def test_the_contract_rejects_the_pre_fix_empty_series_capacity(self):
        # Behavioural negative control: reconstruct the pre-fix body (no
        # degenerate-input guard) and require it to report a positive
        # participation rate on an empty series, proving the corrected
        # function's zero is what makes the call safe rather than merely
        # lucky.
        def pre_fix(returns, adv, max_participation=0.1, impact_model=None):
            if impact_model is None:

                def impact_model(p):
                    return 10 * np.sqrt(p / 0.01)

            current_sharpe = st.sharpe_ratio(returns)
            target_sharpe = current_sharpe * 0.5
            low, high = 0.0, max_participation
            for _ in range(20):
                mid = (low + high) / 2
                adj_sharpe = st.sharpe_ratio(returns - impact_model(mid) / 10000)
                if adj_sharpe >= target_sharpe:
                    low = mid
                else:
                    high = mid
            rate = (low + high) / 2
            return {
                "current_sharpe": current_sharpe,
                "max_participation_rate": rate,
                "estimated_max_aum": rate * adv * 100,
                "sharpe_at_max_aum": st.sharpe_ratio(returns - impact_model(rate) / 10000),
            }

        pre = pre_fix(np.array([]), 1_000_000.0)
        assert pre["max_participation_rate"] > 0.0
        assert pre["estimated_max_aum"] > 0.0

        # And the corrected function returns the no-capacity tuple.
        assert st.capacity_estimate(np.array([]), adv=1_000_000.0) == self._no_capacity()


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

    def test_dataframe_strategy_reduced_to_equal_weighted(self, rng):
        """A multi-symbol strategy panel is reduced to its equal-weighted series.

        Symmetric with the benchmark reduction above: a DataFrame strategy
        (a per-symbol return panel) must be averaged across symbols rather
        than crash. The pre-fix body did not reduce the strategy side, so a 2-D
        ``strategy_returns`` broadcast against the 1-D benchmark and
        ``stats.ttest_1samp`` returned an ARRAY ``t_stat``, making
        ``if t_stat > 0`` raise an opaque ``ValueError: The truth value of an
        array with more than one element is ambiguous``.
        """
        strat_df = pd.DataFrame(rng.normal(0.001, 0.01, (400, 4)))
        bench = rng.normal(0.0003, 0.01, 400)
        res = st.compare_to_benchmark(strat_df, bench)
        res_mean = st.compare_to_benchmark(strat_df.mean(axis=1), bench)
        for key in res:
            assert res[key] == pytest.approx(res_mean[key])

    def test_2d_ndarray_strategy_reduced(self, rng):
        """A 2-D ndarray strategy is likewise reduced along axis 1."""
        strat_2d = rng.normal(0.001, 0.01, (400, 3))
        bench = rng.normal(0.0003, 0.01, 400)
        res = st.compare_to_benchmark(strat_2d, bench)
        res_mean = st.compare_to_benchmark(strat_2d.mean(axis=1), bench)
        for key in res:
            assert res[key] == pytest.approx(res_mean[key])

    def test_1d_strategy_is_unchanged_by_the_reduction(self, rng):
        """A 1-D strategy array is bit-identical to before the strategy guard.

        The reduction only fires for a multi-symbol (ndim > 1) strategy, so the
        clean 1-D path must be unchanged: comparing a 1-D strategy against a
        1-D benchmark equals the same comparison written with an explicit
        ``np.asarray``.
        """
        strat = rng.normal(0.001, 0.01, 400)
        bench = rng.normal(0.0003, 0.01, 400)
        res = st.compare_to_benchmark(strat, bench)
        res_arr = st.compare_to_benchmark(np.asarray(strat, dtype=float), bench)
        assert res == res_arr

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

    def test_annualized_volatility_single_element_is_zero(self):
        """With one observation the sample std (ddof=1) divides by n-1=0 and
        pandas yields NaN, but the engine's convention for this shared metric is
        ``0.0`` (engine.py:243-246: no measurable volatility -> no evidence), so
        validate_strategy mirrors it.  This keeps the cross-module agreement
        contract (tests/test_engine_metric_agreement.py) holding at the n == 1
        boundary too: a NaN here would silently void every gate reading
        ``annualized_volatility`` while ``sharpe_ratio`` reports 0.0 for the
        same input.  The pre-fix behaviour (NaN) is the negative control."""
        res = st.validate_strategy(pd.Series([0.001]), self._trades(1), {})
        assert res["annualized_volatility"] == 0.0

    def test_annualized_volatility_single_element_pref_fix_is_nan(self):
        """Negative control: bare ``Series([x]).std(ddof=1)`` is NaN, which is
        what validate_strategy returned before it mirrored the engine's 0.0."""
        assert np.isnan(pd.Series([0.001]).std())

    # =======================================================================
    # Coverage-gap closure: validate_strategy new degenerate-input guards
    # =======================================================================
    def test_validate_strategy_config_none_fails_closed(self):
        """config=None is a caller type violation; must fail closed, not raise."""
        returns = np.array([0.001] * 100)
        trades = self._trades(50)
        res = st.validate_strategy(returns, trades, None)
        assert res["all_pass"] is False
        assert res["sharpe"] == 0.0
        assert res["n_trades"] == 50

    def test_validate_strategy_trades_none_fails_closed(self):
        """trades=None is a caller type violation; must fail closed, not raise."""
        returns = np.array([0.001] * 100)
        res = st.validate_strategy(returns, None, {})
        assert res["all_pass"] is False
        assert res["sharpe"] == 0.0
        assert res["n_trades"] == 0

    def test_validate_strategy_list_input_accepted(self, rng):
        """list returns must be accepted (normalised via np.asarray)."""
        returns = rng.normal(0.001, 0.01, 200).tolist()
        trades = self._trades(50)
        res = st.validate_strategy(returns, trades, {})
        assert "sharpe" in res
        assert np.isfinite(res["sharpe"])

    def test_validate_strategy_tuple_input_accepted(self, rng):
        """tuple returns must be accepted (normalised via np.asarray)."""
        returns = tuple(rng.normal(0.001, 0.01, 200))
        trades = self._trades(50)
        res = st.validate_strategy(returns, trades, {})
        assert "sharpe" in res
        assert np.isfinite(res["sharpe"])

    def test_validate_strategy_2d_ndarray_fails_closed(self, rng):
        """2-D ndarray returns must fail closed (shape guard)."""
        returns = rng.normal(0.001, 0.01, (2, 100))
        trades = self._trades(50)
        res = st.validate_strategy(returns, trades, {})
        assert res["all_pass"] is False
        assert res["sharpe"] == 0.0

    def test_validate_strategy_dataframe_fails_closed(self, rng):
        """DataFrame returns must fail closed (shape guard)."""
        returns = pd.DataFrame(
            {"a": rng.normal(0.001, 0.01, 100), "b": rng.normal(0.001, 0.01, 100)}
        )
        trades = self._trades(50)
        res = st.validate_strategy(returns, trades, {})
        assert res["all_pass"] is False
        assert res["sharpe"] == 0.0

    def test_validate_strategy_3d_ndarray_fails_closed(self, rng):
        """3-D ndarray returns must fail closed (shape guard)."""
        returns = rng.normal(0.001, 0.01, (2, 3, 10))
        trades = self._trades(50)
        res = st.validate_strategy(returns, trades, {})
        assert res["all_pass"] is False
        assert res["sharpe"] == 0.0


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


# ===========================================================================
# Coverage-gap closure: bars_per_year / annualized_sharpe edge cases
# ===========================================================================
class TestBarsPerYearEdgeCases:
    def test_bars_per_year_single_bar_returns_nan(self):
        # line 186: len(idx) < 2 returns nan.
        idx = pd.DatetimeIndex(["2020-01-01"])
        assert np.isnan(st.bars_per_year(idx))

    def test_bars_per_year_zero_span_returns_nan(self):
        # line 189: span_days <= 0 returns nan.
        idx = pd.DatetimeIndex(["2020-01-01", "2020-01-01"])
        assert np.isnan(st.bars_per_year(idx))


class TestAnnualizedSharpeEdgeCases:
    def test_annualized_sharpe_invalid_bpy_returns_zero(self):
        # line 216: non-finite or <= 0 bars_per_year returns 0.0.
        idx = pd.DatetimeIndex(["2020-01-01"])  # < 2 bars -> bpy is nan
        assert st.annualized_sharpe(np.array([0.001, 0.002]), idx) == 0.0


# ===========================================================================
# Coverage-gap closure: walk_forward_splits empty split
# ===========================================================================
class TestWalkForwardSplitsEmptySplit:
    def test_walk_forward_splits_train_ratio_zero_skips_split(self):
        # branch 274->263: train_idx empty when train_ratio == 0, so the split
        # is not appended.
        splits = st.walk_forward_splits(100, n_splits=5, train_ratio=0.0)
        assert splits == []

    def test_walk_forward_splits_train_ratio_one_skips_split(self):
        # branch 274->263: test_idx empty when train_ratio == 1.0, so the split
        # is not appended.
        splits = st.walk_forward_splits(100, n_splits=5, train_ratio=1.0)
        assert splits == []


# ===========================================================================
# Coverage-gap closure: benchmark_significance_gate invalid threshold
# ===========================================================================
class TestBenchmarkSignificanceGateInvalidThreshold:
    def test_invalid_max_p_value_returns_false(self):
        # lines 876-878: non-finite or out-of-range max_p_value returns False.
        for bad in (np.inf, -np.inf, np.nan, 0.0, 1.5, -0.5):
            assert st.benchmark_significance_gate(0.5, 0.5, max_p_value=bad) is False


# ===========================================================================
# Coverage-gap closure: compare_to_benchmark degenerate inputs
# ===========================================================================
class TestCompareToBenchmarkDegenerate:
    def test_compare_to_benchmark_non_scalar_risk_free_raises(self):
        # line 927: non-scalar risk_free raises TypeError.
        with pytest.raises(TypeError, match="risk_free must be a scalar"):
            st.compare_to_benchmark(
                np.array([0.001, 0.002]),
                np.array([0.0, 0.001]),
                risk_free=np.array([0.05]),
            )

    def test_compare_to_benchmark_empty_arrays_returns_no_evidence(self):
        # line 973: min_len == 0 returns _no_comparison().
        res = st.compare_to_benchmark(np.array([]), np.array([]))
        assert res["information_ratio"] == 0.0
        assert res["alpha_p_value"] == 1.0

    @pytest.mark.parametrize("rf", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_risk_free_returns_no_evidence(self, rf):
        # A non-finite risk-free rate is config-degenerate. The pre-fix body
        # emitted a nan alpha alongside finite beta/IR/p-value (and raised an
        # -W error-fatal RuntimeWarning for an infinite rate); it must fail
        # closed to the no-evidence tuple instead.
        rng = np.random.default_rng(21)
        strat = rng.normal(0.001, 0.01, 252)
        bench = rng.normal(0.0005, 0.01, 252)
        res = st.compare_to_benchmark(strat, bench, risk_free=rf)
        assert res == st._no_comparison()
        assert np.isfinite(res["alpha_annualized"])
        assert res["alpha_p_value"] == 1.0

    def test_the_contract_rejects_the_pre_fix_non_finite_risk_free(self):
        """Negative control: the pre-fix CAPM alpha used ``risk_free / periods``
        directly, so a non-finite rate produced a non-finite alpha.
        """
        strat = np.array([0.01, -0.005, 0.02])
        bench = np.array([0.005, -0.002, 0.01])
        pre_fix_alpha = float(strat.mean() - float("nan") / 252)
        assert not np.isfinite(pre_fix_alpha)
        assert st.compare_to_benchmark(strat, bench, risk_free=float("nan")) == st._no_comparison()


class TestCompareToBenchmarkDegeneratePeriodsPerYear:
    """A non-positive or non-finite ``periods_per_year`` is config-degenerate.

    ``compare_to_benchmark`` divides the risk-free rate by
    ``periods_per_year`` (inside the CAPM alpha), scales the excess
    volatility by ``sqrt(periods_per_year)`` and multiplies the mean excess
    by ``periods_per_year``. A zero count raised ``ZeroDivisionError``; a
    negative count multiplied by the square root of a negative number and
    emitted ``nan`` (plus a ``RuntimeWarning``); a ``nan``/``inf`` count
    likewise poisoned the result. All are inputs a caller has no way to
    filter on its own (the default is a bare int, and all 30+ in-tree
    callers use it), so they must fail closed to ``_no_comparison()`` --
    the same no-evidence tuple the empty-series and the too-few-
    observations paths return -- rather than raising or returning ``nan``.
    """

    @pytest.mark.parametrize(
        "ppy",
        [0, -1, -252, 0.0, -0.5, float("nan"), float("inf"), float("-inf")],
    )
    def test_degenerate_periods_per_year_returns_no_evidence(self, ppy):
        rng = np.random.default_rng(21)
        strat = rng.normal(0.001, 0.01, 252)
        bench = rng.normal(0.0005, 0.01, 252)
        res = st.compare_to_benchmark(strat, bench, risk_free=0.05, periods_per_year=ppy)
        assert res == st._no_comparison()
        assert np.isfinite(res["information_ratio"])
        assert np.isfinite(res["alpha_annualized"])
        assert np.isfinite(res["excess_return_annual"])
        assert res["alpha_p_value"] == 1.0

    def test_zero_period_short_circuits_before_risk_free_division(self):
        # The zero-period path must short-circuit before ``risk_free / 0``.
        res = st.compare_to_benchmark(
            np.array([0.01, -0.005, 0.02]),
            np.array([0.005, -0.002, 0.01]),
            risk_free=0.05,
            periods_per_year=0,
        )
        assert res == st._no_comparison()

    def test_valid_period_is_unchanged(self):
        rng = np.random.default_rng(21)
        strat = rng.normal(0.001, 0.01, 252)
        bench = rng.normal(0.0005, 0.01, 252)
        # A finite positive period count computes the standard arithmetic and
        # matches an equivalent float period exactly.
        assert st.compare_to_benchmark(strat, bench, periods_per_year=252) == (
            st.compare_to_benchmark(strat, bench, periods_per_year=252.0)
        )

    def test_the_contract_rejects_the_pre_fix_zero_period_behaviour(self):
        """Negative control: the pre-fix body raised ``ZeroDivisionError`` for
        ``periods_per_year=0`` and emitted ``nan`` for a negative count. The
        contract "a degenerate period count yields the no-evidence tuple"
        must reject both pre-fix paths.
        """
        strat = np.array([0.01, -0.005, 0.02])
        bench = np.array([0.005, -0.002, 0.01])
        risk_free = 0.05

        # Pre-fix arithmetic, reconstructed exactly: the CAPM alpha used
        # ``risk_free / periods_per_year``.
        with pytest.raises(ZeroDivisionError):
            _ = risk_free / 0

        # Pre-fix arithmetic, reconstructed exactly: the annualized excess
        # volatility was ``excess.std(ddof=0) * sqrt(periods_per_year)``,
        # and ``sqrt`` of a negative number emits ``nan`` (plus a
        # ``RuntimeWarning``).
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            pre_fix_negative = float((strat - bench).std(ddof=0) * np.sqrt(-1))
        assert np.isnan(pre_fix_negative), "the pre-fix negative-period path must emit nan"

        # The corrected implementation returns the no-evidence tuple for both.
        assert (
            st.compare_to_benchmark(strat, bench, risk_free=risk_free, periods_per_year=0)
            == st._no_comparison()
        )
        assert (
            st.compare_to_benchmark(strat, bench, risk_free=risk_free, periods_per_year=-1)
            == st._no_comparison()
        )


# ===========================================================================
# Coverage-gap closure: purged / combinatorial CV empty splits
# ===========================================================================
class TestPurgedKfoldEmptySplit:
    def test_purged_kfold_splits_split_not_appended(self):
        # branch 1459->1446: a fold whose train or test side is empty is not
        # appended. purge=4 masks all train indices when fold_size=1.
        splits = st.purged_kfold_splits(5, n_splits=5, purge=4, embargo=4)
        assert splits == []

    def test_combinatorial_purged_cv_split_not_appended(self):
        # branch 1496->1483: a combination whose train side is fully masked is
        # not appended. n_test_splits == n_splits - 1 leaves only one train
        # index, and purge/embargo can mask it out.
        splits = st.combinatorial_purged_cv(5, n_splits=3, n_test_splits=2, purge=4, embargo=4)
        assert splits == []


# ===========================================================================
# Degenerate-operand guard: purged k-fold / combinatorial CV
# ===========================================================================
class TestPurgedCvDegenerateOperands:
    """A purge/embargo/sample/split width that is not a finite non-negative
    integer is not a positional width. Both schemes share the boundary
    arithmetic (``n_samples // n_splits`` and ``mask[lo:hi]`` slices), so they
    share the guard and the same parametrized coverage."""

    DEGENERATE_PURGE = [
        dict(purge=float("nan")),
        dict(purge=float("inf")),
        dict(purge=float("-inf")),
        dict(purge=1.5),
        dict(purge=-1.0),
        dict(purge=-1.5),
        dict(embargo=float("nan")),
        dict(embargo=float("inf")),
        dict(embargo=float("-inf")),
        dict(embargo=1.5),
        dict(embargo=-1.0),
        dict(embargo=-1.5),
    ]

    @pytest.mark.parametrize("kwargs", DEGENERATE_PURGE)
    def test_purged_kfold_fails_closed(self, kwargs):
        assert st.purged_kfold_splits(100, n_splits=5, **kwargs) == []

    @pytest.mark.parametrize("kwargs", DEGENERATE_PURGE)
    def test_combinatorial_cv_fails_closed(self, kwargs):
        assert st.combinatorial_purged_cv(100, n_splits=5, n_test_splits=2, **kwargs) == []

    @pytest.mark.parametrize(
        "kwargs",
        [
            dict(n_samples=float("nan")),
            dict(n_samples=float("inf")),
            dict(n_samples=float("-inf")),
            dict(n_samples=100.0),
            dict(n_samples=-100),
            dict(n_samples=100, n_splits=float("nan")),
            dict(n_samples=100, n_splits=float("inf")),
            dict(n_samples=100, n_splits=1.5),
            dict(n_samples=100, n_splits=-5),
            dict(n_samples=100, n_splits=True),
        ],
    )
    def test_purged_kfold_bad_sample_or_split_count(self, kwargs):
        assert st.purged_kfold_splits(**kwargs) == []

    @pytest.mark.parametrize(
        "kwargs",
        [
            dict(n_samples=float("nan")),
            dict(n_samples=float("inf")),
            dict(n_samples=100.0),
            dict(n_samples=-100),
            dict(n_splits=float("nan")),
            dict(n_splits=1.5),
            dict(n_splits=-5),
            dict(n_test_splits=float("nan")),
            dict(n_test_splits=float("inf")),
            dict(n_test_splits=1.5),
            dict(n_test_splits=-2),
            dict(n_test_splits=True),
        ],
    )
    def test_combinatorial_cv_bad_sample_split_or_test_count(self, kwargs):
        call_kwargs = {"n_samples": 100, **kwargs}
        call_kwargs.setdefault("n_splits", 5)
        assert st.combinatorial_purged_cv(**call_kwargs) == []

    def test_purged_kfold_negative_purge_inverts_window(self):
        # Negative control: ``purge=-1`` used to yield ``lo = test_start + 1``,
        # masking the *wrong* side and leaking training data across the test
        # fold. The guard now rejects it before any split is built.
        assert st.purged_kfold_splits(100, n_splits=5, purge=-1) == []

    def test_combinatorial_cv_negative_embargo_inverts_window(self):
        # Same class for the combinatorial scheme.
        assert st.combinatorial_purged_cv(100, n_splits=5, n_test_splits=2, embargo=-1) == []

    def test_purged_kfold_valid_domain_unchanged(self):
        # The guard only short-circuits degenerate inputs. A finite,
        # non-negative, integer purge/embargo is bit-identical to before:
        # the existing contracts still hold.
        assert len(st.purged_kfold_splits(100, n_splits=5, purge=2, embargo=2)) == 5
        assert st.purged_kfold_splits(4, n_splits=2, purge=10) == []
        assert len(st.combinatorial_purged_cv(100, n_splits=5, n_test_splits=2)) == 10
        assert st.combinatorial_purged_cv(4, n_splits=2, n_test_splits=1, purge=10) == []
        assert st.combinatorial_purged_cv(100, n_splits=5, n_test_splits=0) == []

    def test_purged_kfold_pre_fix_arange_crash_rejected(self):
        # Behavioural negative control: the pre-fix guard was absent, so the
        # function walked straight into ``np.arange(n_samples)`` with a
        # non-finite count and raised ``ValueError: arange: cannot compute
        # length`` out of a function every caller treats as returning a list.
        # Reconstruct that pre-fix body here and require it to raise; the real
        # function must not.
        def pre_fix(n_samples, n_splits=5, purge=0, embargo=0):
            if n_samples <= 0 or n_splits <= 0:
                return []
            fold_size = n_samples // n_splits
            splits = []
            for i in range(n_splits):
                start = i * fold_size
                end = n_samples if i == n_splits - 1 else (i + 1) * fold_size
                test_idx = np.arange(start, end)
                mask = np.ones(n_samples, dtype=bool)
                mask[start:end] = False
                lo = max(0, start - purge)
                hi = min(n_samples, end + purge)
                mask[lo:hi] = False
                emb_start = end
                emb_end = min(n_samples, end + embargo)
                mask[emb_start:emb_end] = False
                train_idx = np.where(mask)[0]
                if len(train_idx) > 0 and len(test_idx) > 0:
                    splits.append((train_idx, test_idx))
            return splits

        with pytest.raises(ValueError):
            pre_fix(float("nan"), n_splits=5)
        assert st.purged_kfold_splits(float("nan"), n_splits=5) == []

    def test_combinatorial_cv_pre_fix_slice_crash_rejected(self):
        # Behavioural negative control: the pre-fix guard was absent, so a
        # float ``purge`` walked into ``mask[lo:hi]`` and raised
        # ``TypeError: slice indices must be integers or None or have an
        # __index__ method`` out of a function every caller treats as
        # returning a list. Reconstruct that pre-fix body here and require it
        # to raise; the real function must not.
        from itertools import combinations as _combinations

        def pre_fix(n_samples, n_splits=5, n_test_splits=2, purge=0, embargo=0):
            if n_samples <= 0 or n_splits <= 0 or n_test_splits <= 0 or n_test_splits >= n_splits:
                return []
            fold_size = n_samples // n_splits
            groups = []
            for i in range(n_splits):
                s = i * fold_size
                e = n_samples if i == n_splits - 1 else (i + 1) * fold_size
                groups.append((s, e))
            splits = []
            for test_groups in _combinations(range(n_splits), n_test_splits):
                test_idx = np.concatenate(
                    [np.arange(groups[g][0], groups[g][1]) for g in test_groups]
                )
                mask = np.ones(n_samples, dtype=bool)
                for g in test_groups:
                    s, e = groups[g]
                    mask[s:e] = False
                    lo = max(0, s - purge)
                    hi = min(n_samples, e + purge)
                    mask[lo:hi] = False
                    emb_start = e
                    emb_end = min(n_samples, e + embargo)
                    mask[emb_start:emb_end] = False
                train_idx = np.where(mask)[0]
                if len(train_idx) > 0 and len(test_idx) > 0:
                    splits.append((train_idx, test_idx))
            return splits

        with pytest.raises(TypeError):
            pre_fix(100, n_splits=5, n_test_splits=2, purge=1.5)
        assert st.combinatorial_purged_cv(100, n_splits=5, n_test_splits=2, purge=1.5) == []


# ===========================================================================
# Numeric-index annualization guard
# ===========================================================================
class TestBarsPerYearNumericIndex:
    """A positional/numeric index is not a timestamp axis.

    ``pd.DatetimeIndex`` coerces integers as nanoseconds since the epoch, so a
    ``RangeIndex`` (the default index of ``pd.Series(list)`` and of
    ``reset_index(drop=True)``) became a 1970 index spanning a few nanoseconds
    and produced a bars-per-year of ~4.7e16. ``annualized_sharpe`` then scaled
    the Sharpe by ``sqrt(4.7e16)`` ~= 2.2e8 -- a silent nine-orders-of-magnitude
    corruption. The function must refuse a numeric index (NaN, the same
    fail-closed value as a single-bar or zero-span index) rather than coerce it.
    """

    @pytest.mark.parametrize(
        "index",
        [
            pd.RangeIndex(3),
            pd.Index([1, 2, 3]),
            pd.Index([1.0, 2.0, 3.0]),
            pd.Index([1, 2, 3], dtype="int64"),
            np.array([1, 2, 3]),
            [1, 2, 3],
        ],
    )
    def test_numeric_index_returns_nan(self, index):
        assert np.isnan(st.bars_per_year(index))

    def test_numeric_range_index_is_not_coerced_to_1970_nanoseconds(self):
        # The pre-fix ``pd.DatetimeIndex(index)`` coercion is the defect: it
        # turns RangeIndex(3) into a two-nanosecond span, i.e. ~4.7e16 bars/yr.
        coerced = pd.DatetimeIndex(pd.RangeIndex(3))
        span_ns = (coerced[-1] - coerced[0]).total_seconds() * 1e9
        assert span_ns == pytest.approx(2.0)
        pre_fix_bpy = len(coerced) / ((span_ns / 1e9) / 86400.0 / 365.25)
        assert pre_fix_bpy > 1e10
        # The guarded function refuses it instead.
        assert np.isnan(st.bars_per_year(pd.RangeIndex(3)))

    @pytest.mark.parametrize(
        "index",
        [
            ["2020-01-01", "2020-01-02", "2020-01-03"],
            [pd.Timestamp("2020-01-01"), pd.Timestamp("2020-01-02"), pd.Timestamp("2020-01-03")],
            [datetime.date(2020, 1, 1), datetime.date(2020, 1, 2), datetime.date(2020, 1, 3)],
        ],
    )
    def test_datetime_like_non_datetime_index_still_converts(self, index):
        # Only a *numeric* index is refused; a datetime-like list is still a
        # valid timestamp axis and converts as before.
        idx = pd.DatetimeIndex(index)
        span_days = (idx[-1] - idx[0]).total_seconds() / 86400.0
        expected = len(idx) / (span_days / 365.25)
        assert st.bars_per_year(index) == pytest.approx(expected)

    def test_annualized_sharpe_returns_zero_for_positional_index(self):
        rets = np.array([0.01, -0.005, 0.02])
        # A plain Series carries a RangeIndex: the most common way a caller
        # hands a positional axis to the annualizer.
        series = pd.Series(rets)
        assert st.annualized_sharpe(series, series.index) == 0.0
        assert st.annualized_sharpe(rets, pd.RangeIndex(3)) == 0.0

    def test_annualized_sharpe_matches_daily_for_string_index(self):
        rets = np.array([0.01, -0.005, 0.02])
        daily = pd.DatetimeIndex(["2020-01-01", "2020-01-02", "2020-01-03"])
        as_strings = ["2020-01-01", "2020-01-02", "2020-01-03"]
        assert st.annualized_sharpe(rets, as_strings) == pytest.approx(
            st.annualized_sharpe(rets, daily)
        )

    def test_daily_datetime_index_is_unchanged(self):
        idx = pd.bdate_range("2020-01-01", periods=300)
        span_days = (idx[-1] - idx[0]).total_seconds() / 86400.0
        expected = len(idx) / (span_days / 365.25)
        assert st.bars_per_year(idx) == pytest.approx(expected)


class TestBarsPerYearNonTimestampIndex:
    """A non-timestamp axis must fail closed to NaN, not raise.

    ``bars_per_year`` already refuses a numeric/positional axis (a
    ``RangeIndex``, ``pd.Index([1, 2, 3])``) because ``pd.DatetimeIndex``
    would coerce the integers to 1970 nanoseconds and manufacture a
    ~4.7e16 bars-per-year factor.  The docstring's return contract is NaN for
    *any* axis that is "not a timestamp axis", but the implementation only
    screened the numeric case: a categorical/object string index, a
    ``MultiIndex``, a ``PeriodIndex``, a ``TimedeltaIndex`` or an
    ``IntervalIndex`` fell through to ``pd.DatetimeIndex(raw)`` and raised
    ``TypeError`` (or ``DateParseError``, a ``ValueError``) out of a function
    every caller treats as returning a float.  ``annualized_sharpe`` calls
    this helper directly, so the crash propagated there too.

    These axes are all "not a timestamp axis" in exactly the same sense as a
    ``RangeIndex``, so they must return NaN -- the same fail-closed value a
    single-bar or zero-span index returns -- and ``annualized_sharpe`` must
    map that to ``0.0`` rather than crash.  A datetime-like index is
    unchanged (pinned by ``TestBarsPerYearNumericIndex``).
    """

    @pytest.mark.parametrize(
        "index",
        [
            pd.Index(pd.Categorical(["x", "y", "z"])),
            pd.Index(["x", "y", "z"], dtype=object),
            pd.Index([object(), object(), object()], dtype=object),
            pd.MultiIndex.from_tuples([("a", 1), ("b", 2), ("c", 3)]),
            pd.period_range("2020-01", periods=3, freq="M"),
            pd.to_timedelta([1, 2, 3], unit="D"),
            pd.IntervalIndex.from_breaks([0, 1, 2, 3]),
        ],
    )
    def test_non_timestamp_index_returns_nan(self, index):
        assert np.isnan(st.bars_per_year(index))

    def test_annualized_sharpe_returns_zero_for_non_timestamp_index(self):
        rets = np.array([0.01, -0.005, 0.02])
        multi = pd.MultiIndex.from_tuples([("a", 1), ("b", 2), ("c", 3)])
        assert st.annualized_sharpe(rets, multi) == 0.0
        assert st.annualized_sharpe(rets, pd.to_timedelta([1, 2, 3], unit="D")) == 0.0

    def test_datetime_like_index_still_converts(self):
        # The guard only refuses a non-datetime-convertible axis; a valid
        # datetime-like index converts exactly as before.
        idx = pd.DatetimeIndex(["2020-01-01", "2020-01-02", "2020-01-03"])
        span_days = (idx[-1] - idx[0]).total_seconds() / 86400.0
        expected = len(idx) / (span_days / 365.25)
        assert st.bars_per_year(["2020-01-01", "2020-01-02", "2020-01-03"]) == pytest.approx(
            expected
        )


# ===========================================================================
# Sharpe-period annualization guard
# ===========================================================================
class TestSharpeRatioPeriodGuard:
    """A non-positive or non-finite ``periods_per_year`` is config-degenerate.

    ``sharpe_ratio`` divides the risk-free rate by ``periods_per_year`` and
    multiplies the ratio by ``sqrt(periods_per_year)``. A zero period count
    raised ``ZeroDivisionError``; a negative count multiplied by ``sqrt`` of a
    negative number and emitted ``nan``; a ``nan``/``inf`` count poisoned the
    result. All are inputs a caller has no way to filter on its own (the
    default is a bare int), so they must fail closed to the same ``0.0``
    no-evidence result used for an empty or zero-variance series.
    """

    @pytest.mark.parametrize(
        "ppy",
        [0, -1, -252, 0.0, -0.5, float("nan"), float("inf"), float("-inf")],
    )
    def test_degenerate_periods_per_year_returns_zero(self, ppy):
        rng = np.random.default_rng(21)
        rets = rng.normal(0.001, 0.01, 252)
        result = st.sharpe_ratio(rets, periods_per_year=ppy)
        assert result == 0.0
        assert np.isfinite(result)

    def test_empty_series_still_returns_zero_before_period_guard(self):
        # The empty-series guard runs first and is independent of the period.
        assert st.sharpe_ratio(np.array([]), periods_per_year=0) == 0.0

    def test_valid_period_is_unchanged(self):
        rng = np.random.default_rng(21)
        rets = rng.normal(0.001, 0.01, 252)
        # A finite positive period count computes the standard arithmetic and
        # matches an equivalent float period exactly.
        assert st.sharpe_ratio(rets, periods_per_year=252) == pytest.approx(
            st.sharpe_ratio(rets, periods_per_year=252.0)
        )
        assert np.isfinite(st.sharpe_ratio(rets, periods_per_year=252))

    def test_risk_free_term_is_not_divided_by_zero(self):
        # The zero-period path must short-circuit before ``risk_free / 0``.
        rets = np.array([0.01, -0.005, 0.02, 0.015, -0.01])
        assert st.sharpe_ratio(rets, risk_free=0.05, periods_per_year=0) == 0.0

    def test_the_contract_rejects_the_pre_fix_zero_period_behaviour(self):
        """Negative control: the pre-fix body raised ``ZeroDivisionError`` for
        ``periods_per_year=0`` and emitted ``nan`` for a negative count. The
        contract "a degenerate period count yields a finite 0.0" must reject
        both pre-fix paths.
        """
        rets = np.array([0.01, -0.005, 0.02])

        # Pre-fix arithmetic, reconstructed exactly: ``excess = returns -
        # risk_free / periods_per_year`` then ``excess.mean() / std *
        # sqrt(periods_per_year)`` with no period guard.
        risk_free = 0.0
        with pytest.raises(ZeroDivisionError):
            _ = rets - risk_free / 0

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            pre_fix_negative = float(rets.mean() / rets.std() * np.sqrt(-1))
        assert np.isnan(pre_fix_negative), "the pre-fix negative-period path must emit nan"

        # The corrected implementation is finite 0.0 for both.
        assert st.sharpe_ratio(rets, periods_per_year=0) == 0.0
        assert st.sharpe_ratio(rets, periods_per_year=-1) == 0.0


class TestSharpeRatioRiskFreeGuard:
    """A non-finite ``risk_free`` is config-degenerate and fails closed.

    ``risk_free`` is subtracted from the mean return, so an ``inf``/``-inf``/
    ``nan`` rate makes ``excess`` non-finite and the ratio ``nan``/``-inf`` --
    a non-finite result that silently voids every gate reading it. It must
    fail closed to ``0.0`` exactly like the ``periods_per_year`` guard above.
    """

    @pytest.mark.parametrize("rf", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_risk_free_returns_zero(self, rf):
        rng = np.random.default_rng(21)
        rets = rng.normal(0.001, 0.01, 252)
        result = st.sharpe_ratio(rets, risk_free=rf)
        assert result == 0.0
        assert np.isfinite(result)

    def test_finite_risk_free_is_unchanged(self):
        rng = np.random.default_rng(21)
        rets = rng.normal(0.001, 0.01, 252)
        assert st.sharpe_ratio(rets, risk_free=0.05) == pytest.approx(
            st.sharpe_ratio(rets, risk_free=0.0) - 0.05 / (rets.std() * np.sqrt(252))
        )

    def test_annualized_sharpe_inherits_the_guard(self):
        idx = pd.bdate_range("2020-01-01", periods=8)
        rets = np.array([0.01, -0.005, 0.02, 0.015, -0.01, 0.005, 0.0, 0.003])
        assert st.annualized_sharpe(rets, idx, risk_free=float("nan")) == 0.0

    def test_the_contract_rejects_the_pre_fix_non_finite_risk_free(self):
        """Negative control: the pre-fix Sharpe emitted a non-finite value."""
        rets = np.array([0.01, -0.005, 0.02, 0.015, -0.01])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            pre_fix = float((rets - float("inf") / 252).mean() / rets.std() * np.sqrt(252))
        assert not np.isfinite(pre_fix)
        assert st.sharpe_ratio(rets, risk_free=float("inf")) == 0.0
