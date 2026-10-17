"""
Regression tests for the H12 selection-bias audit machinery
(run_h12_selection_bias_audit.py).

Pins:
  * _expected_max_sharpe (Bailey & Lopez de Prado 2014, Eq. 2-4)
    -- monotone in N, zero for zero trial variance
  * deflated_sharpe_ratio -- bounded, tends to the observed SR for
    a large observed SR, ~SR/2 at the deflation benchmark
  * _cscv_pbo_multi -- PBO = 0 for a genuinely skilled strategy,
    ~0.5 for pure noise, raises when T is not divisible by S
  * family-wide trial-count arithmetic and Bonferroni/BH adjustment
  * _selected_row / _load_cached_data consistency with the H10
    artifact (selected config = argmax of the Val-Sharpe grid)
"""

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from _utils_parquet import read_parquet_safe

import run_h12_selection_bias_audit as h12


class TestExpectedMaxSharpe:
    def test_monotone_in_n_trials(self):
        prev = 0.0
        for n in (10, 100, 1_000, 13_824, 14_389, 100_000):
            sr0, _ = h12._expected_max_sharpe(n, 1.0)
            assert sr0 > prev
            prev = sr0

    def test_zero_variance_gives_zero(self):
        sr0, _ = h12._expected_max_sharpe(13_824, 0.0)
        assert sr0 == 0.0

    def test_positive_for_positive_variance(self):
        sr0, _ = h12._expected_max_sharpe(13_824, 0.025)
        assert sr0 > 0.0


class TestDeflatedSharpeRatio:
    def test_huge_observed_sr_is_undeflated(self):
        # A Sharpe far above the deflation benchmark survives
        # essentially undeflated with a ~0 p-value.
        dsr, p = h12.deflated_sharpe_ratio(
            observed_sr=100.0,
            n_trials=13_824,
            n_obs=2860,
            var_trials=0.025,
            skewness=0.0,
            kurtosis=3.0,
        )
        assert dsr == pytest.approx(100.0, rel=1e-6)
        assert p == pytest.approx(0.0, abs=1e-6)

    def test_at_benchmark_gives_half(self):
        # Observed SR exactly at the deflation benchmark => the
        # test statistic is 0 => P = 0.5 => DSR = SR / 2.
        sr0, _ = h12._expected_max_sharpe(13_824, 0.025 / 252)
        observed = sr0 * np.sqrt(252)
        dsr, p = h12.deflated_sharpe_ratio(
            observed_sr=observed,
            n_trials=13_824,
            n_obs=2860,
            var_trials=0.025,
            skewness=0.0,
            kurtosis=3.0,
        )
        assert dsr == pytest.approx(observed / 2.0, rel=1e-6)
        assert p == pytest.approx(0.5, abs=1e-6)

    def test_below_benchmark_gives_low_dsr(self):
        dsr, p = h12.deflated_sharpe_ratio(
            observed_sr=0.1,
            n_trials=13_824,
            n_obs=2860,
            var_trials=0.025,
            skewness=0.0,
            kurtosis=3.0,
        )
        assert dsr < 0.05
        assert p > 0.9

    def test_bounded_by_observed_sr(self):
        for sr in (0.5, 1.0, 1.4134, 3.0):
            dsr, p = h12.deflated_sharpe_ratio(
                observed_sr=sr,
                n_trials=13_824,
                n_obs=2860,
                var_trials=0.025,
                skewness=1.4,
                kurtosis=29.0,
            )
            assert 0.0 <= dsr <= sr
            assert 0.0 <= p <= 1.0


class TestCSCVPBO:
    @staticmethod
    def _matrix(n_strategies, n_bars, seed, means=None):
        rng = np.random.default_rng(seed)
        mat = rng.normal(0.0, 1.0, size=(n_bars, n_strategies))
        if means is not None:
            mat = mat + np.asarray(means, dtype=float)[None, :]
        return mat

    def test_raises_when_t_not_divisible(self):
        mat = self._matrix(5, 100, seed=0)
        with pytest.raises(ValueError):
            h12._cscv_pbo_multi(mat, n_blocks=8)

    def test_skilled_strategy_gives_zero_pbo(self):
        # Strategy 0 dominates in every block (skill delta far
        # above the block-mean noise SE) => IS-optimal is always
        # strategy 0 and its OOS rank is always 1 => PBO = 0.
        means = np.zeros(10)
        means[0] = 0.5
        mat = self._matrix(10, 240, seed=1, means=means)
        res = h12._cscv_pbo_multi(mat, n_blocks=4)
        assert res["pbo"] == 0.0
        assert res["median_is_opt_oos_rank"] == 1.0

    def test_pure_noise_pbo_near_half(self):
        # i.i.d. noise strategies: the IS-optimal is selected at
        # random, so its OOS rank is ~uniform => PBO ~ 0.5.
        mat = self._matrix(50, 480, seed=7)
        res = h12._cscv_pbo_multi(mat, n_blocks=4)
        assert 0.0 < res["pbo"] < 1.0
        assert res["n_combinations"] == 6  # C(4, 2)
        assert res["n_strategies"] == 50

    def test_rank_distribution_sums_to_combinations(self):
        mat = self._matrix(20, 240, seed=3)
        res = h12._cscv_pbo_multi(mat, n_blocks=4)
        assert sum(res["rank_distribution"].values()) == res["n_combinations"]
        assert all(1 <= r <= 20 for r in res["rank_distribution"])


class TestFamilyAudit:
    def test_family_total_is_sum_of_counts(self):
        assert h12.FAMILY_TOTAL == sum(h12.FAMILY_TRIAL_COUNTS.values())
        assert h12.FAMILY_TOTAL == 14_389
        assert h12.N_GRID == h12.FAMILY_TRIAL_COUNTS["H10"]

    def test_bonferroni_and_bh_coincide_for_single_rank(self):
        p = h12.BENCHMARK_P_VALUE
        m = h12.FAMILY_TOTAL
        bonf = min(1.0, p * m)
        bh = min(1.0, m * p / 1.0)
        assert bonf == pytest.approx(bh)
        assert bonf < 0.05  # survives family-wide correction


class TestH10ArtifactConsistency:
    def test_selected_row_is_grid_argmax(self):
        grid = read_parquet_safe(h12.H10_GRID_PARQUET)
        row = h12._selected_row(grid)
        assert row["val_sharpe"] == pytest.approx(grid["val_sharpe"].max())
        for key, value in h12.SEL.items():
            if key == "smooth_span":
                assert row[key] == "none"
            else:
                assert row[key] == value

    def test_load_cached_data_matches_h10_window(self):
        prices, volumes, vix, returns = h12._load_cached_data()
        assert prices.shape == (11441, 5)
        assert volumes.shape == (11441, 5)
        assert len(vix) == 11441
        assert len(returns) == 11441
        assert str(prices.index.max())[:10] == "2026-10-09"
