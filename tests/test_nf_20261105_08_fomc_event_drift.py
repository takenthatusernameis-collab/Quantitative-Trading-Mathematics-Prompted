import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_nf_20261105_08_fomc_event_drift as nf08
from qtr.backtest.engine import AssetClass


def _spy_vix(n=80, start="2015-01-20", seed=1):
    dates = pd.date_range(start, periods=n, freq="B")
    rng = np.random.default_rng(seed)
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
    vix = 15 + rng.normal(0, 2, n).cumsum() * 0.1
    vix = np.clip(vix, 10, 40)
    return pd.DataFrame({"SPY": spy, "^VIX": vix}, index=dates)


class TestPreRegistration:
    def test_gates(self):
        g = nf08.GATES
        assert g["min_sharpe"] == 1.0
        assert g["min_trades"] == 200
        assert g["min_profit_factor"] == 1.3
        assert g["max_drawdown"] == 0.15
        assert g["min_walkforward_stability"] == 0.7
        assert g["max_p_value"] == 0.05
        assert g["min_information_ratio"] == 0.0
        assert g["min_perturbed_sharpe_ratio"] == 0.5

    def test_config(self):
        cfg = nf08.make_equity_config()
        assert cfg.asset_class == AssetClass.EQUITY
        assert cfg.allow_short is False
        assert cfg.max_leverage == 1.0

    def test_universe_and_splits(self):
        assert nf08.SPY == "SPY"
        assert nf08.VIX == "^VIX"
        assert nf08.DATA_START == "2015-01-01"
        assert nf08.TRAIN_END == "2019-12-31"
        assert nf08.VAL_END == "2022-12-31"

    def test_fomc_calendar_covers_sample_window(self):
        dates = set(nf08.FOMC_DATES)
        assert "2015-01-28" in dates
        assert "2015-12-16" in dates
        assert "2020-03-15" in dates  # emergency meeting included
        assert "2026-09-16" in dates
        assert len(nf08.FOMC_DATES) >= 90


class TestSignalCausality:
    def test_fomc_day_does_not_create_same_day_exposure(self):
        dates = pd.date_range("2015-01-26", periods=8, freq="B")
        prices = pd.DataFrame({"SPY": [100.0] * 8, "^VIX": [15.0] * 8}, index=dates)
        t = nf08.build_daily_targets(prices, hold_days=1, vix_gate=None, vol_target=0.15)
        assert list(t.columns) == ["SPY"]
        fomc_idx = dates.get_loc(pd.Timestamp("2015-01-28"))
        assert float(t.iloc[fomc_idx, 0]) == 0.0

    def test_hold_window_length(self):
        prices = _spy_vix(n=120, start="2014-11-03", seed=7)
        t = nf08.build_daily_targets(prices, hold_days=2, vix_gate=None, vol_target=0.15)
        fomc_idx = prices.index.get_loc(pd.Timestamp("2015-01-28"))
        assert t.iloc[fomc_idx + 1, 0] > 0
        assert t.iloc[fomc_idx + 2, 0] > 0
        # outside window (before event, with enough warmup context) should be 0
        pre = prices.index.get_loc(pd.Timestamp("2015-01-27"))
        assert float(t.iloc[pre, 0]) == 0.0

    def test_vix_gate_blocks_event(self):
        prices = _spy_vix(n=120, start="2014-11-03", seed=3)
        fomc_idx = prices.index.get_loc(pd.Timestamp("2015-01-28"))
        prices.loc[prices.index[fomc_idx], "^VIX"] = 35.0
        t = nf08.build_daily_targets(prices, hold_days=1, vix_gate=30.0, vol_target=0.15)
        assert float(t.iloc[fomc_idx + 1, 0]) == 0.0

    def test_deterministic(self):
        prices = _spy_vix(n=120)
        t1 = nf08.build_daily_targets(prices, hold_days=2, vix_gate=25.0, vol_target=0.15)
        t2 = nf08.build_daily_targets(prices, hold_days=2, vix_gate=25.0, vol_target=0.15)
        pd.testing.assert_frame_equal(t1, t2)

    def test_positions_bounded(self):
        prices = _spy_vix(n=300, start="2015-01-01")
        t = nf08.build_daily_targets(prices, hold_days=5, vix_gate=None, vol_target=0.50)
        assert (t["SPY"] >= -1e-12).all()
        assert (t["SPY"] <= nf08.MAX_POS + 1e-12).all()
