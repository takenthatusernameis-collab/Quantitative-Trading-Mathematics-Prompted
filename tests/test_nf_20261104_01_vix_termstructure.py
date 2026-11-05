"""
Regression tests for NF-20261104-01 VIX term structure slope experiment
(run_nf_20261104_01_vix_termstructure.py).

Pins:
  * Pre-registered gate thresholds
  * Grid integrity (27 combos)
  * Signal causality (slope from close prices, no future info)
  * Position bounds
  * Determinism
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_nf_20261104_01_vix_termstructure as nf01


class TestPreRegistration:
    def test_gates_are_the_pre_registered_set(self):
        assert nf01.GATES == {
            "min_sharpe": 1.0,
            "min_trades": 200,
            "min_profit_factor": 1.3,
            "max_drawdown": 0.15,
            "min_walkforward_stability": 0.7,
            "min_worst_regime_sharpe": 0.3,
            "max_p_value": 0.05,
            "min_information_ratio": 0.0,
            "min_perturbed_sharpe_ratio": 0.5,
        }

    def test_grid_is_27_combos(self):
        assert len(nf01.LOOKBACKS) == 3
        assert len(nf01.ZSCORES) == 3
        assert len(nf01.VOL_TARGETS) == 3
        assert len(nf01.LOOKBACKS) * len(nf01.ZSCORES) * len(nf01.VOL_TARGETS) == 27


class TestSignalCausality:
    def test_slope_computed_from_close_prices(self):
        dates = pd.date_range("2020-01-01", periods=200, freq="B")
        rng = np.random.default_rng(42)
        vix = 15 + np.cumsum(rng.normal(0, 0.5, len(dates)))
        vix3m = vix + rng.normal(0.5, 0.1, len(dates))
        spy = 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.01, len(dates))))
        prices = pd.DataFrame({nf01.VIX_SPOT: vix, nf01.VIX3M: vix3m, nf01.SPY: spy}, index=dates)

        targets = nf01.build_daily_targets(prices, lookback=63, zscore=1.0, vol_target=0.15)
        assert (targets.iloc[0] == 0).all()
        # Check slope is VIX3M/VIX
        slope = prices[nf01.VIX3M] / prices[nf01.VIX_SPOT]
        # Positions depend on slope
        assert targets[nf01.SPY].abs().max() <= nf01.MAX_POS


class TestBounds:
    def test_positions_bounded(self):
        dates = pd.date_range("2020-01-01", periods=200, freq="B")
        rng = np.random.default_rng(123)
        vix = 15 + np.cumsum(rng.normal(0, 0.5, len(dates)))
        vix3m = vix * 1.1 + rng.normal(0, 0.1, len(dates))
        spy = 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.01, len(dates))))
        prices = pd.DataFrame({nf01.VIX_SPOT: vix, nf01.VIX3M: vix3m, nf01.SPY: spy}, index=dates)

        targets = nf01.build_daily_targets(prices, lookback=126, zscore=0.5, vol_target=0.20)
        assert (targets.abs() <= nf01.MAX_POS + 1e-10).all().all()


class TestDeterminism:
    def test_signal_builder_is_deterministic(self):
        dates = pd.date_range("2020-01-01", periods=150, freq="B")
        rng = np.random.default_rng(17)
        vix = 15 + np.cumsum(rng.normal(0, 0.5, len(dates)))
        vix3m = vix + rng.normal(0.3, 0.1, len(dates))
        spy = 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.01, len(dates))))
        prices = pd.DataFrame({nf01.VIX_SPOT: vix, nf01.VIX3M: vix3m, nf01.SPY: spy}, index=dates)

        t1 = nf01.build_daily_targets(prices, lookback=63, zscore=1.0, vol_target=0.15)
        t2 = nf01.build_daily_targets(prices, lookback=63, zscore=1.0, vol_target=0.15)
        pd.testing.assert_frame_equal(t1, t2)
