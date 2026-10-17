"""
Regression tests for the H13 OOS-deflation & PF-margin
fragility audit machinery (run_h13_oos_deflation_pf_audit.py).

Pins:
  * deflated_sharpe_ratio_single_peek -- the N=1 DSR
    (deflation benchmark E[max SR | null, N=1] = 0):
    undeflated for a huge observed SR, 0 at SR=0, always
    >= the N=13,824 deflation, bounded in [0, SR]
  * _profit_factor -- exact on a known series, +inf with
    no losses, NaN on empty input
  * bootstrap_profit_factor_distribution -- seeded
    determinism, point estimate inside the CI
  * _shifted_splits -- partitions the index, OOS bar
    counts match the pre-registered fractions
  * leave-one-out PF -- drop-column and subtraction
    forms coincide; a zero-contribution symbol is
    dispensable by construction
  * _cost_breakeven -- bisection converges on a
    synthetic monotone PF(mult) and rejects a
    non-straddling bracket
  * frozen-pipeline reproduction on the H10/H12 cached
    artifacts: engine returns bit-exact, per-symbol net
    decomposition reconstructs engine returns, shifted
    splits reproduce the H11 E4a profit factors
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_h13_oos_deflation_pf_audit as h13


class TestSinglePeekDSR:
    def test_huge_observed_sr_is_undeflated(self):
        dsr, p = h13.deflated_sharpe_ratio_single_peek(
            observed_sr=100.0,
            n_obs=5148,
            var_trials=0.024,
            skewness=1.0,
            kurtosis=22.0,
        )
        assert dsr == pytest.approx(100.0, rel=1e-6)
        assert p == pytest.approx(0.0, abs=1e-6)

    def test_zero_sr_gives_half(self):
        # SR = 0 => statistic 0 => p = 0.5 => DSR = 0.
        dsr, p = h13.deflated_sharpe_ratio_single_peek(
            observed_sr=0.0,
            n_obs=5148,
            var_trials=0.024,
            skewness=0.0,
            kurtosis=3.0,
        )
        assert dsr == 0.0
        assert p == pytest.approx(0.5, abs=1e-9)

    def test_single_peek_at_least_as_large_as_worst_case(self):
        # N=1 applies no selection deflation, so the
        # single-peek DSR must dominate the worst-case
        # N=13,824 DSR for identical inputs.
        import run_h12_selection_bias_audit as h12

        kwargs = {
            "n_obs": 5148,
            "var_trials": 0.024,
            "skewness": 1.0,
            "kurtosis": 22.0,
        }
        for sr in (0.5, 1.0, 1.275759, 2.0):
            dsr_1, _ = h13.deflated_sharpe_ratio_single_peek(observed_sr=sr, **kwargs)
            dsr_wc, _ = h12.deflated_sharpe_ratio(
                observed_sr=sr, n_trials=13_824, **kwargs
            )
            assert dsr_1 >= dsr_wc - 1e-12

    def test_bounded_by_observed_sr(self):
        for sr in (0.5, 1.0, 1.275759, 3.0):
            for skew, kurt in ((0.0, 3.0), (1.0, 22.0), (-0.8, 15.0)):
                dsr, p = h13.deflated_sharpe_ratio_single_peek(
                    observed_sr=sr,
                    n_obs=5148,
                    var_trials=0.024,
                    skewness=skew,
                    kurtosis=kurt,
                )
                assert 0.0 <= dsr <= sr
                assert 0.0 <= p <= 1.0

    def test_monotone_in_observed_sr(self):
        prev = -1.0
        for sr in np.linspace(0.0, 3.0, 31):
            dsr, _ = h13.deflated_sharpe_ratio_single_peek(
                observed_sr=float(sr),
                n_obs=5148,
                var_trials=0.024,
                skewness=1.0,
                kurtosis=22.0,
            )
            assert dsr >= prev - 1e-12
            prev = dsr


class TestProfitFactor:
    def test_known_series(self):
        r = np.array([0.01, 0.02, -0.01, -0.005, 0.0])
        assert h13._profit_factor(r) == pytest.approx(0.03 / 0.015)

    def test_all_gains_is_inf(self):
        assert h13._profit_factor(np.array([0.01, 0.02])) == float("inf")

    def test_empty_is_nan(self):
        assert np.isnan(h13._profit_factor(np.array([])))

    def test_nonfinite_bars_are_dropped(self):
        r = np.array([0.01, np.nan, -0.01, np.inf])
        assert h13._profit_factor(r) == pytest.approx(1.0)


class TestBootstrapPF:
    def test_seeded_determinism(self):
        rng = np.random.default_rng(0)
        r = rng.normal(0.0002, 0.01, 5000)
        a = h13.bootstrap_profit_factor_distribution(r, seed=42, n_bootstrap=200)
        b = h13.bootstrap_profit_factor_distribution(r, seed=42, n_bootstrap=200)
        assert np.array_equal(a, b)

    def test_point_estimate_within_ci(self):
        rng = np.random.default_rng(1)
        r = rng.normal(0.0003, 0.01, 20000)
        boot = h13.bootstrap_profit_factor_distribution(r, seed=42, n_bootstrap=1000)
        lo, hi = np.percentile(boot, [2.5, 97.5])
        point = h13._profit_factor(r)
        assert lo <= point <= hi

    def test_positive_drift_boots_above_one(self):
        rng = np.random.default_rng(2)
        r = rng.normal(0.001, 0.005, 10000)
        boot = h13.bootstrap_profit_factor_distribution(r, seed=42, n_bootstrap=500)
        assert np.median(boot) > 1.0


class TestShiftedSplits:
    def test_partitions_index(self):
        n = 1000
        idx = pd.date_range("2020-01-01", periods=n, freq="h")
        prices = pd.DataFrame({"a": np.arange(n, dtype=float)}, index=idx)
        for label, tf, vf in h13.SHIFTED_SPLITS:
            tr, va, te = h13._shifted_splits(prices, tf, vf)
            assert not (tr & va).any()
            assert not (tr & te).any()
            assert not (va & te).any()
            assert (tr | va | te).all()

    def test_oos_bar_fractions(self):
        n = 1000
        idx = pd.date_range("2020-01-01", periods=n, freq="h")
        prices = pd.DataFrame({"a": np.arange(n, dtype=float)}, index=idx)
        for label, tf, vf in h13.SHIFTED_SPLITS:
            _, va, te = h13._shifted_splits(prices, tf, vf)
            oos = va | te
            assert oos.sum() == pytest.approx(n * (1 - tf), rel=0.02)

    def test_base_splits_match_h10(self):
        # The H10 split (55/25/20) is the 0.55/0.25 case.
        prices, _, _, _ = h13._load_cached_data()
        tr_h10, va_h10, te_h10 = h13._splits(prices)
        tr, va, te = h13._shifted_splits(prices, 0.55, 0.25)
        assert (tr == tr_h10).all()
        assert (va == va_h10).all()
        assert (te == te_h10).all()


class TestLeaveOneOut:
    @staticmethod
    def _synthetic_contrib(seed=0):
        rng = np.random.default_rng(seed)
        idx = pd.date_range("2020-01-01", periods=3000, freq="h")
        cols = ["a", "b", "c", "d"]
        return pd.DataFrame(
            rng.normal(0.0001, 0.01, size=(3000, 4)), index=idx, columns=cols
        )

    def test_drop_and_subtract_forms_coincide(self):
        contrib = self._synthetic_contrib()
        mask = np.ones(len(contrib), dtype=bool)
        pooled = contrib.sum(axis=1)
        for sym in contrib.columns:
            lou_drop = contrib.drop(columns=[sym]).sum(axis=1)
            lou_sub = pooled - contrib[sym]
            assert np.allclose(lou_drop, lou_sub)
            assert h13._profit_factor(lou_drop[mask]) == pytest.approx(
                h13._profit_factor(lou_sub[mask])
            )

    def test_zero_contribution_symbol_is_dispensable(self):
        contrib = self._synthetic_contrib()
        contrib["zero"] = 0.0
        pooled = contrib.sum(axis=1)
        mask = np.ones(len(contrib), dtype=bool)
        lou = h13._leave_one_out_pf(contrib, mask)
        # Removing an all-zero symbol cannot change the
        # pooled PF.
        assert lou["zero"] == pytest.approx(h13._profit_factor(pooled[mask]))


class TestCostBreakeven:
    def test_bisection_converges(self, monkeypatch):
        # Synthetic monotone PF(mult) = 1.4 - 0.2 * mult,
        # crossing 1.3 at mult = 0.5.
        def fake_pf(positions, prices, volumes, cfg, oos_mask):
            mult = cfg.cost_model.future_commission_per_contract / 0.5
            pf = 1.4 - 0.2 * mult
            return pf, 1.0, 100

        monkeypatch.setattr(h13, "_oos_pf_of_positions", fake_pf)
        breakeven, pf_lo, pf_hi = h13._cost_breakeven(
            None, None, None, None, 0.25, 0.75, tol=1e-3
        )
        assert breakeven == pytest.approx(0.5, abs=1e-3)
        assert pf_lo >= 1.3 >= pf_hi

    def test_rejects_non_straddling_bracket(self, monkeypatch):
        def fake_pf(positions, prices, volumes, cfg, oos_mask):
            return 1.5, 1.0, 100

        monkeypatch.setattr(h13, "_oos_pf_of_positions", fake_pf)
        with pytest.raises(AssertionError):
            h13._cost_breakeven(None, None, None, None, 0.5, 1.5, tol=1e-3)


@pytest.fixture(scope="module")
def frozen_pipeline():
    """Run the frozen H10 pipeline once on the cached
    artifacts (one deterministic backtest)."""
    prices, volumes, vix_hourly, h10_returns = h13._load_cached_data()
    atr, vol_exit = h13._build_exit_inputs(prices)
    positions = h13.build_positions(
        prices, atr, vol_exit, vix_hourly, **h13.FROZEN_CONFIG
    )
    cfg = h13.make_futures_config()
    from qtr.backtest.engine import run_backtest

    res = run_backtest(prices=prices, signals=positions, volumes=volumes, config=cfg)
    contrib = h13.per_symbol_contributions(res, prices, cfg)
    return prices, volumes, vix_hourly, h10_returns, res, contrib


class TestFrozenPipelineReproduction:
    def test_engine_returns_reproduce_h10_artifact(self, frozen_pipeline):
        _prices, _, _, h10_returns, res, _ = frozen_pipeline
        assert (res.returns - h10_returns).abs().max() < 1e-9

    def test_per_symbol_decomposition_reconstructs_returns(self, frozen_pipeline):
        _prices, _, _, _h10_returns, res, contrib = frozen_pipeline
        pooled = contrib.sum(axis=1)
        assert (pooled - res.returns).abs().max() < 1e-9

    def test_pooled_pf_matches_selected_config(self, frozen_pipeline):
        prices, _, _, _, _res, contrib = frozen_pipeline
        _, val_mask, test_mask = h13._splits(prices)
        oos = val_mask | test_mask
        pooled = contrib.sum(axis=1)
        assert h13._profit_factor(pooled[oos]) == pytest.approx(
            1.3041645169434146, rel=1e-9
        )

    def test_shifted_splits_reproduce_h11_e4a(self, frozen_pipeline):
        prices, _, _, _, _res, contrib = frozen_pipeline
        pooled = contrib.sum(axis=1)
        expected = {
            "50/25/25": 1.28064754854388,
            "60/20/20": 1.3297783905647602,
            "45/30/25": 1.291555,
        }
        for label, tf, vf in h13.SHIFTED_SPLITS:
            _, va, te = h13._shifted_splits(prices, tf, vf)
            oos = va | te
            pf = h13._profit_factor(pooled[oos])
            if label in expected:
                assert pf == pytest.approx(expected[label], rel=1e-6)

    def test_leave_one_out_pfs_match_h13_artifact(self, frozen_pipeline):
        prices, _, _, _, _, contrib = frozen_pipeline
        _, val_mask, test_mask = h13._splits(prices)
        oos = val_mask | test_mask
        lou = h13._leave_one_out_pf(contrib, oos)
        expected = {
            "ES=F": 1.3070,
            "NQ=F": 1.3006,
            "CL=F": 1.2494,
            "GC=F": 1.2821,
            "ZB=F": 1.3114,
        }
        for sym in contrib.columns:
            assert lou[sym] == pytest.approx(expected[sym], abs=5e-4)


class TestH13ArtifactConsistency:
    def test_grid_oos_metrics_has_full_grid(self):
        grid = pd.read_parquet(h13.H12_GRID_PARQUET)
        assert len(grid) == h13.N_GRID
        row = h13._selected_row(grid)
        assert row["oos_sharpe"] == pytest.approx(1.2757590680990518, rel=1e-12)
        assert row["oos_profit_factor"] == pytest.approx(1.3041645169434146, rel=1e-12)

    def test_load_cached_data_matches_h10_window(self):
        prices, volumes, vix, returns = h13._load_cached_data()
        assert prices.shape == (11441, 5)
        assert volumes.shape == (11441, 5)
        assert len(vix) == 11441
        assert len(returns) == 11441
        assert str(prices.index.max())[:10] == "2026-10-09"

    def test_h11_original_summary_available(self):
        assert h13.H11_ORIGINAL_SUMMARY.exists()
        orig = json.loads(h13.H11_ORIGINAL_SUMMARY.read_text())
        e4a = {
            row["split"]: float(row["oos_profit_factor"])
            for row in orig["e4_window_robustness"]["shifted_splits"]
        }
        assert e4a["50/25/25"] == pytest.approx(1.28064754854388)
        assert e4a["60/20/20"] == pytest.approx(1.3297783905647602)
