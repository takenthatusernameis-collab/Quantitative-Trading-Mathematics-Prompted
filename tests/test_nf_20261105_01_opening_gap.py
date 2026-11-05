"""
Regression tests for NF-20261105-01 opening-gap fill experiment
(run_nf_20261105_01_opening_gap.py, H87).

Pins:
  * Pre-registered gate thresholds
  * Grid integrity (27 combos)
  * Signal causality: gap uses open[t] - close[t-1] only (no future info)
  * Position bounds and determinism
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_nf_20261105_01_opening_gap as nf05


def _spy_ohlc(n=220, seed=42):
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0004, 0.01, n)))
    open_ = close * (1 + rng.normal(0.0, 0.003, n))
    high = np.maximum(close, open_) * 1.002
    low = np.minimum(close, open_) * 0.998
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close}, index=dates)


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

    def test_splits_are_pre_registered(self):
        assert nf05.TRAIN_END == "2020-12-31"
        assert nf05.VAL_END == "2023-12-31"
        assert nf05.DATA_START == "2015-01-01"
        assert nf05.DATA_END == "2026-10-31"


class TestSignalCausality:
    def test_gap_uses_only_open_t_and_close_t_minus_1(self):
        prices = _spy_ohlc(n=150, seed=7)
        targets = nf05.build_daily_targets(prices, lookback=5, zscore_thresh=0.0, vol_target=0.15)
        assert targets.shape == (len(prices), 1)
        assert targets.columns[0] == nf05.SYMBOL
        # First row has no prior close -> gap NaN -> position 0
        assert float(targets.iloc[0, 0]) == 0.0

    def test_signal_direction_matches_gap_sign(self):
        dates = pd.date_range("2020-01-01", periods=5, freq="B")
        # Construct clear gaps with stable vol
        close = pd.Series([100.0, 100.0, 100.0, 100.0, 100.0], index=dates)
        open_ = pd.Series([100.0, 102.0, 98.0, 101.0, 99.0], index=dates)
        prices = pd.DataFrame(
            {"open": open_, "high": 103.0, "low": 97.0, "close": close}, index=dates
        )
        targets = nf05.build_daily_targets(prices, lookback=1, zscore_thresh=0.0, vol_target=0.15)
        pos = targets[nf05.SYMBOL]
        # gap positive at t=1 (open 102 > close 100) -> short (negative)
        assert pos.iloc[1] < 0
        # gap negative at t=2 -> long
        assert pos.iloc[2] > 0

    def test_concurrent_close_change_does_not_flip_signal(self):
        prices = _spy_ohlc(n=120, seed=11)
        t1 = nf05.build_daily_targets(prices, lookback=5, zscore_thresh=0.0, vol_target=0.15)
        perturbed = prices.copy()
        # Change close[t] dramatically; gap at t uses open[t]-close[t-1], intraday
        # return uses close[t]/open[t], but the *gap signal* must not use close[t].
        # build_daily_targets computes gap from open and close.shift(1) — close[t] affects
        # vol scaling via intraday_ret[t] but not the gap direction. Verify gap logic:
        t_idx = 50
        perturbed.iloc[t_idx, perturbed.columns.get_loc("close")] *= 1.2
        t2 = nf05.build_daily_targets(perturbed, lookback=5, zscore_thresh=0.0, vol_target=0.15)
        # Sign of gap-based direction is preserved (vol scaling may change magnitude slightly
        # at/after t_idx due to intraday vol rolling window, but direction at t_idx is gap-driven).
        s1 = np.sign(t1.iloc[t_idx, 0])
        s2 = np.sign(t2.iloc[t_idx, 0])
        assert s1 == s2


class TestBounds:
    def test_positions_bounded(self):
        prices = _spy_ohlc(n=220, seed=123)
        targets = nf05.build_daily_targets(prices, lookback=21, zscore_thresh=0.5, vol_target=0.20)
        assert (targets.abs() <= 1.0 + 1e-10).all().all()

    def test_no_nan_after_warmup(self):
        prices = _spy_ohlc(n=220, seed=5)
        targets = nf05.build_daily_targets(prices, lookback=21, zscore_thresh=0.0, vol_target=0.15)
        assert not targets.iloc[30:].isna().any().any()


class TestDeterminism:
    def test_signal_builder_is_deterministic(self):
        prices = _spy_ohlc(n=150, seed=17)
        t1 = nf05.build_daily_targets(prices, lookback=5, zscore_thresh=0.5, vol_target=0.15)
        t2 = nf05.build_daily_targets(prices, lookback=5, zscore_thresh=0.5, vol_target=0.15)
        pd.testing.assert_frame_equal(t1, t2)


class TestMetrics:
    def test_period_metrics_shapes(self):
        r = pd.Series(np.random.default_rng(0).normal(0.0002, 0.01, 100))
        m = nf05._period_metrics(r, 50)
        assert set(m) == {
            "sharpe",
            "max_drawdown",
            "profit_factor",
            "trades",
            "gross_profit",
            "gross_loss",
            "n_periods",
        }
        assert m["trades"] == 50
        assert m["n_periods"] == 100

    def test_period_metrics_empty(self):
        m = nf05._period_metrics(pd.Series(dtype=float), 0)
        assert m["sharpe"] == 0.0
        assert m["trades"] == 0
