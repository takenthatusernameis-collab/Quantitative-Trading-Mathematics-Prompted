import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_nf_20261105_09_turn_of_month as nf09
from qtr.backtest.engine import AssetClass


class TestPreRegistration:
    def test_gates(self):
        g = nf09.GATES
        assert g["min_sharpe"] == 1.0
        assert g["min_trades"] == 200
        assert g["min_profit_factor"] == 1.3
        assert g["max_drawdown"] == 0.15
        assert g["min_walkforward_stability"] == 0.7
        assert g["min_worst_regime_sharpe"] == 0.3
        assert g["max_p_value"] == 0.05
        assert g["min_information_ratio"] == 0.0
        assert g["min_perturbed_sharpe_ratio"] == 0.5

    def test_config(self):
        cfg = nf09.make_equity_config()
        assert cfg.asset_class == AssetClass.EQUITY
        assert cfg.allow_short is False
        assert cfg.max_leverage == 1.0
        assert cfg.max_position_size == nf09.MAX_POS

    def test_universe_and_splits(self):
        assert nf09.SPY == "SPY"
        assert nf09.UNIVERSE == ["SPY"]
        assert nf09.DATA_START == "2010-01-01"
        assert nf09.DATA_END == "2026-10-31"
        assert nf09.TRAIN_END == "2019-12-31"
        assert nf09.VAL_END == "2022-12-31"

    def test_grid_and_selection(self):
        assert nf09.HEAD_DAYS == [1, 2, 3, 4, 5]
        assert nf09.TAIL_DAYS == 1
        assert nf09.VOL_TARGETS == [0.10, 0.15]
        assert nf09.WF_FOLDS_SELECTION == 4
        grid = [(h, v) for h in nf09.HEAD_DAYS for v in nf09.VOL_TARGETS]
        assert len(grid) == 10


class TestTurnOfMonthCalendar:
    def test_mask_is_causal_and_covers_month_ends(self):
        # Full calendar months (Jan+Feb 2020) so cumcount/month-max reflect true ranks.
        idx = pd.date_range("2020-01-02", "2020-02-28", freq="B")
        mask = nf09.build_turn_window_mask(idx, head_days=3)
        # Last trading day of January 2020 (Fri 2020-01-31) is in the window.
        assert bool(mask.loc[pd.Timestamp("2020-01-31")]) is True
        # First trading days of February 2020 are head days.
        assert bool(mask.loc[pd.Timestamp("2020-02-03")]) is True
        assert bool(mask.loc[pd.Timestamp("2020-02-04")]) is True
        assert bool(mask.loc[pd.Timestamp("2020-02-05")]) is True
        # Last trading day of February 2020 (Fri 2020-02-28, leap year) is in the window.
        assert bool(mask.loc[pd.Timestamp("2020-02-28")]) is True
        # Mid-month days are neither head days nor the last day.
        assert bool(mask.loc[pd.Timestamp("2020-01-07")]) is False
        assert bool(mask.loc[pd.Timestamp("2020-02-06")]) is False

    def test_head_days_one_is_last_day_plus_first_day(self):
        idx = pd.date_range("2020-01-02", "2020-02-28", freq="B")
        mask = nf09.build_turn_window_mask(idx, head_days=1)
        true_dates = set(idx[mask].tolist())
        # head_days=1: first trading day of each month + last trading day of each month.
        for d in [
            pd.Timestamp("2020-01-02"),
            pd.Timestamp("2020-01-31"),
            pd.Timestamp("2020-02-03"),
            pd.Timestamp("2020-02-28"),
        ]:
            assert d in true_dates
        assert len(true_dates) == 4

    def test_daily_targets_columns_and_bounds(self):
        dates = pd.date_range("2020-01-02", periods=120, freq="B")
        rng = np.random.default_rng(1)
        spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, len(dates))))
        prices = pd.DataFrame({"SPY": spy}, index=dates)
        t = nf09.build_daily_targets(prices, head_days=3, vol_target=0.15)
        assert list(t.columns) == ["SPY"]
        assert (t["SPY"] >= -1e-12).all()
        assert (t["SPY"] <= nf09.MAX_POS + 1e-12).all()
        mask = nf09.build_turn_window_mask(prices.index, head_days=3)
        assert (t.loc[~mask, "SPY"] == 0.0).all()

    def test_deterministic(self):
        dates = pd.date_range("2020-01-02", periods=200, freq="B")
        rng = np.random.default_rng(5)
        spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, len(dates))))
        prices = pd.DataFrame({"SPY": spy}, index=dates)
        t1 = nf09.build_daily_targets(prices, head_days=4, vol_target=0.10)
        t2 = nf09.build_daily_targets(prices, head_days=4, vol_target=0.10)
        pd.testing.assert_frame_equal(t1, t2)
