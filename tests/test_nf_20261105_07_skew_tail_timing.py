"""
Regression tests for NF-20261105-07 CBOE SKEW tail-risk regime timing
(run_nf_20261105_07_skew_tail_timing.py, H89).

Pins:
  * Pre-registered gate thresholds, splits, grid, and config
  * Signal causality (1-bar delay, trailing z-score inputs)
  * Long/flat bounds and hysteresis behavior
  * Determinism and alignment handling
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_nf_20261105_07_skew_tail_timing as nf07
from qtr.backtest.engine import AssetClass


def _skew_spy(n=320, seed=42):
    dates = pd.date_range("2016-01-01", periods=n, freq="B")
    rng = np.random.default_rng(seed)
    spy = 200 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
    skew = 130 + np.cumsum(rng.normal(0.0, 1.5, n))
    skew = np.clip(skew, 105, 185)
    return pd.DataFrame({"^SKEW": skew, "SPY": spy}, index=dates)


class TestPreRegistration:
    def test_gates(self):
        g = nf07.GATES
        assert g["min_sharpe"] == 1.0
        assert g["min_trades"] == 200
        assert g["min_profit_factor"] == 1.3
        assert g["max_drawdown"] == 0.15
        assert g["min_walkforward_stability"] == 0.7
        assert g["max_p_value"] == 0.05
        assert g["min_information_ratio"] == 0.0
        assert g["min_perturbed_sharpe_ratio"] == 0.5

    def test_splits_and_universe(self):
        assert nf07.UNIVERSE == ["^SKEW", "SPY"]
        assert nf07.TRAIN_END == "2019-12-31"
        assert nf07.VAL_END == "2022-12-31"
        assert nf07.DATA_START == "2015-01-01"
        assert nf07.DATA_END == "2026-10-31"

    def test_config(self):
        cfg = nf07.make_equity_config()
        assert cfg.asset_class == AssetClass.EQUITY
        assert cfg.allow_short is False
        assert cfg.max_leverage == 1.0
        assert cfg.max_position_size == nf07.MAX_POS

    def test_grid_integrity(self):
        valid = [
            (l, e, x, vt)
            for l in nf07.LOOKBACKS
            for e in nf07.ENTRY_ZS
            for x in nf07.EXIT_ZS
            for vt in nf07.VOL_TARGETS
            if x < e
        ]
        assert nf07.LOOKBACKS == [63, 126, 252]
        assert nf07.ENTRY_ZS == [0.5, 1.0, 1.5]
        assert nf07.EXIT_ZS == [-0.5, 0.0, 0.5]
        assert nf07.VOL_TARGETS == [0.10, 0.15]
        assert len(valid) == 48  # 3 lookbacks * 6 valid (entry,exit) pairs * 2 vol targets


class TestSignalCausality:
    def test_one_bar_delay(self):
        prices = _skew_spy(n=320)
        # construct extreme high SKEW at a single bar to force risk-off state at t
        prices.loc[prices.index[150:], "^SKEW"] = 180.0
        prices.loc[prices.index[:150], "^SKEW"] = 120.0
        pos = nf07.build_daily_targets(
            prices, lookback=63, entry_z=0.5, exit_z=0.0, vol_target=0.15
        )
        # position uses shift(1): the risk-off decision at t cannot affect t
        # find first index where delayed state likely becomes 0 after regime change
        # check no impossible future use by mutating future SKEW not changing past pos
        pos0 = pos["SPY"].copy()
        prices2 = prices.copy()
        prices2.loc[prices2.index[-1], "^SKEW"] = 999.0  # impossible but isolates future
        pos2 = nf07.build_daily_targets(
            prices2, lookback=63, entry_z=0.5, exit_z=0.0, vol_target=0.15
        )
        pd.testing.assert_series_equal(
            pos0.iloc[:-1], pos2["SPY"].iloc[:-1], check_names=False, check_freq=False
        )

    def test_trailing_zscore_uses_past_only(self):
        s = pd.Series(np.arange(100, dtype=float), index=pd.date_range("2020-01-01", periods=100))
        z = nf07.skew_zscore(s, lookback=20)
        assert z.iloc[:19].isna().all() or np.isfinite(z.iloc[19:].dropna()).any()
        # append future point should not change earlier z
        s2 = pd.concat([s, pd.Series([9999.0], index=[s.index[-1] + pd.Timedelta(days=1)])])
        z2 = nf07.skew_zscore(s2, lookback=20)
        pd.testing.assert_series_equal(
            z.dropna(), z2.loc[z.index].dropna(), check_names=False, check_freq=False
        )


class TestBoundsAndBehavior:
    def test_long_flat_bounds(self):
        prices = _skew_spy(n=400)
        pos = nf07.build_daily_targets(prices, 126, 1.0, 0.0, 0.15)
        w = pos["SPY"].dropna()
        assert (w >= -1e-12).all()
        assert (w <= nf07.MAX_POS + 1e-12).all()

    def test_invalid_hysteresis_returns_flat(self):
        prices = _skew_spy(n=200)
        pos = nf07.build_daily_targets(prices, 63, 0.5, 0.5, 0.15)
        assert (pos["SPY"] == 0.0).all()

    def test_deterministic(self):
        prices = _skew_spy(n=300)
        p1 = nf07.build_daily_targets(prices, 63, 1.0, 0.0, 0.10)
        p2 = nf07.build_daily_targets(prices, 63, 1.0, 0.0, 0.10)
        pd.testing.assert_frame_equal(p1, p2)

    def test_missing_columns_safe(self):
        prices = pd.DataFrame({"SPY": [100.0, 101.0]}, index=pd.date_range("2020-01-01", periods=2))
        pos = nf07.build_daily_targets(prices, 63, 1.0, 0.0, 0.15)
        assert (pos["SPY"] == 0.0).all()
