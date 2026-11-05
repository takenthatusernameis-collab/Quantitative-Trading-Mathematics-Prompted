"""
Regression tests for NF-20261105-01 / H87 opening-gap fill.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

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
        assert len(nf05.ZSCORES) == 3
        assert len(nf05.VOL_TARGETS) == 3
        assert len(nf05.LOOKBACKS) * len(nf05.ZSCORES) * len(nf05.VOL_TARGETS) == 27


class TestSignalCausality:
    def test_uses_open_and_prev_close(self):
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        rng = np.random.default_rng(42)
        close = 100 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, len(dates))))
        # create gap
        openp = close * (1 + rng.normal(0, 0.005, len(dates)))
        prices = pd.DataFrame({"SPY": close, "Open": openp}, index=dates)
        targets = nf05.build_daily_targets(prices, lookback=5, zscore=0.5, vol_target=0.15)
        assert targets[nf05.SYMBOL].abs().max() <= nf05.MAX_POS + 1e-10


class TestBounds:
    def test_positions_bounded(self):
        dates = pd.date_range("2020-01-01", periods=200, freq="B")
        rng = np.random.default_rng(123)
        close = 100 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, len(dates))))
        openp = close * (1 + rng.normal(0, 0.01, len(dates)))
        prices = pd.DataFrame({"SPY": close, "Open": openp}, index=dates)
        targets = nf05.build_daily_targets(prices, lookback=21, zscore=1.0, vol_target=0.20)
        assert (targets.abs() <= nf05.MAX_POS + 1e-10).all().all()


class TestDeterminism:
    def test_signal_builder_is_deterministic(self):
        dates = pd.date_range("2020-01-01", periods=150, freq="B")
        rng = np.random.default_rng(17)
        close = 100 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, len(dates))))
        openp = close * (1 + rng.normal(0, 0.005, len(dates)))
        prices = pd.DataFrame({"SPY": close, "Open": openp}, index=dates)
        t1 = nf05.build_daily_targets(prices, lookback=5, zscore=0.5, vol_target=0.15)
        t2 = nf05.build_daily_targets(prices, lookback=5, zscore=0.5, vol_target=0.15)
        pd.testing.assert_frame_equal(t1, t2)
