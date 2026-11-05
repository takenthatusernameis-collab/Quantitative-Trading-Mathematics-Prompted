"""
Regression tests for NF-20261105-01 / H87 opening-gap fill experiment
(run_nf_20261105_01_opening_gap.py).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_nf_20261105_01_opening_gap as nf05


class TestPreRegistration:
    def test_gates_are_the_pre_registered_set(self):
        assert nf05.GATES == {
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
        assert len(nf05.LOOKBACKS) == 3
        assert len(nf05.ZSCORE_THRESHOLDS) == 3
        assert len(nf05.VOL_TARGETS) == 3
        assert len(nf05.LOOKBACKS) * len(nf05.ZSCORE_THRESHOLDS) * len(nf05.VOL_TARGETS) == 27


class TestSignalCausality:
    def test_gap_computed_from_close_lag_and_open_no_lookahead(self):
        dates = pd.date_range("2020-01-01", periods=50, freq="B")
        rng = np.random.default_rng(7)
        close = pd.Series(
            100 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, len(dates)))), index=dates
        )
        open_ = close * (1 + pd.Series(rng.normal(0, 0.002, len(dates)), index=dates))
        prices = pd.DataFrame({"open": open_, "close": close}, index=dates)

        targets = nf05.build_daily_targets(prices, lookback=5, zscore_thresh=0.0, vol_target=0.15)
        assert (targets.iloc[0] == 0).all()  # no prior close -> no signal
        # positions bounded
        assert (targets.abs() <= 1.0 + 1e-10).all().all()


class TestBounds:
    def test_positions_bounded(self):
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        rng = np.random.default_rng(11)
        close = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, len(dates))))
        open_ = close * (1 + rng.normal(-0.001, 0.003, len(dates)))
        prices = pd.DataFrame({"open": open_, "close": close}, index=dates)
        targets = nf05.build_daily_targets(prices, lookback=21, zscore_thresh=0.5, vol_target=0.20)
        assert (targets.abs() <= 1.0 + 1e-10).all().all()


class TestDeterminism:
    def test_signal_builder_is_deterministic(self):
        dates = pd.date_range("2020-01-01", periods=80, freq="B")
        rng = np.random.default_rng(13)
        close = 100 * np.exp(np.cumsum(rng.normal(0.0001, 0.01, len(dates))))
        open_ = close * (1 + rng.normal(0.0002, 0.0025, len(dates)))
        prices = pd.DataFrame({"open": open_, "close": close}, index=dates)
        t1 = nf05.build_daily_targets(prices, lookback=5, zscore_thresh=0.5, vol_target=0.15)
        t2 = nf05.build_daily_targets(prices, lookback=5, zscore_thresh=0.5, vol_target=0.15)
        pd.testing.assert_frame_equal(t1, t2)
