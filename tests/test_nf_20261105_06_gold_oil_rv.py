"""
Regression tests for NF-20261105-06 gold–oil relative-value mean reversion
(run_nf_20261105_06_gold_oil_rv.py, H88).

Pins:
  * Pre-registered gate thresholds and grid integrity
  * Spread construction (log GC - log CL), no non-positive price leakage
  * Signal causality: z-score uses trailing data only; 1-bar position delay
  * Position bounds (dollar-neutral legs), determinism
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_nf_20261105_06_gold_oil_rv as nf06


def _gc_cl(n=300, seed=42):
    dates = pd.date_range("2015-01-01", periods=n, freq="B")
    rng = np.random.default_rng(seed)
    gc = 1500 * np.exp(np.cumsum(rng.normal(0.0001, 0.008, n)))
    cl = 60 * np.exp(np.cumsum(rng.normal(0.0001, 0.015, n)))
    return pd.DataFrame({"GC=F": gc, "CL=F": cl}, index=dates)


class TestPreRegistration:
    def test_gates_pre_registered(self):
        assert nf06.GATES["min_sharpe"] == 1.0
        assert nf06.GATES["min_trades"] == 30
        assert nf06.GATES["min_profit_factor"] == 1.1
        assert nf06.GATES["max_drawdown"] == 0.15
        assert nf06.GATES["min_walkforward_stability"] == 0.7
        assert nf06.GATES["max_p_value"] == 0.05
        assert nf06.GATES["min_information_ratio"] == 0.0
        assert nf06.GATES["min_perturbed_sharpe_ratio"] == 0.5

    def test_grid_integrity(self):
        valid = [
            (l, e, x) for l in nf06.LOOKBACKS for e in nf06.ENTRY_ZS for x in nf06.EXIT_ZS if x < e
        ]
        assert len(valid) >= 12  # 3*3*2 minus exit>=entry filtered cases
        assert nf06.LOOKBACKS == [60, 120, 252]
        assert nf06.ENTRY_ZS == [1.5, 2.0, 2.5]
        assert nf06.EXIT_ZS == [0.5, 0.75]

    def test_splits_pre_registered(self):
        assert nf06.TRAIN_END == "2018-12-31"
        assert nf06.VAL_END == "2022-12-31"
        assert nf06.DATA_START == "2010-01-01"
        assert nf06.DATA_END == "2026-10-31"


class TestSpreadConstruction:
    def test_spread_is_log_ratio(self):
        prices = _gc_cl(n=50)
        s = nf06.spread_series(prices)
        expected = np.log(prices["GC=F"]) - np.log(prices["CL=F"])
        pd.testing.assert_series_equal(s, expected, check_names=False)

    def test_spread_ignores_non_positive(self):
        prices = _gc_cl(n=30)
        prices.loc[prices.index[5], "CL=F"] = 0.0
        prices.loc[prices.index[6], "GC=F"] = -1.0
        s = nf06.spread_series(prices)
        assert not np.isfinite(s.iloc[5])
        assert not np.isfinite(s.iloc[6])
        assert np.isfinite(s.iloc[7])

    def test_zscore_trailing_only(self):
        s = pd.Series(
            np.arange(200, dtype=float), index=pd.date_range("2020-01-01", periods=200, freq="B")
        )
        z = nf06.spread_zscore(s, lookback=60)
        # z at index i must not change when future values change
        z1 = nf06.spread_zscore(s, lookback=60)
        s2 = s.copy()
        s2.iloc[150:] = 9999.0
        z2 = nf06.spread_zscore(s2, lookback=60)
        pd.testing.assert_series_equal(z1.iloc[:150], z2.iloc[:150])


class TestCausalityAndBounds:
    def test_position_delayed_one_bar(self):
        prices = _gc_cl(n=300, seed=7)
        tgt, pos = nf06.build_spread_targets(prices, lookback=60, entry_z=1.5, exit_z=0.5)
        # pos is shifted by 1 in build_spread_targets; first element must be 0
        assert float(tgt["GC=F"].iloc[0]) == 0.0
        assert float(tgt["CL=F"].iloc[0]) == 0.0

    def test_dollar_neutral_legs(self):
        prices = _gc_cl(n=300, seed=11)
        tgt, _ = nf06.build_spread_targets(prices, lookback=60, entry_z=1.5, exit_z=0.5)
        diff = tgt["GC=F"] + tgt["CL=F"]
        assert (diff.abs() < 1e-12).all()

    def test_leg_bounds(self):
        prices = _gc_cl(n=300, seed=13)
        tgt, _ = nf06.build_spread_targets(prices, lookback=60, entry_z=1.5, exit_z=0.5)
        assert (tgt["GC=F"].abs() <= nf06.MAX_LEG + 1e-10).all()
        assert (tgt["CL=F"].abs() <= nf06.MAX_LEG + 1e-10).all()

    def test_future_price_change_does_not_affect_past_targets(self):
        prices = _gc_cl(n=300, seed=17)
        t1, _ = nf06.build_spread_targets(prices, lookback=60, entry_z=2.0, exit_z=0.5)
        perturbed = prices.copy()
        perturbed.iloc[250:, perturbed.columns.get_loc("GC=F")] *= 1.5
        t2, _ = nf06.build_spread_targets(perturbed, lookback=60, entry_z=2.0, exit_z=0.5)
        pd.testing.assert_frame_equal(t1.iloc[:249], t2.iloc[:249])


class TestDeterminismAndMetrics:
    def test_deterministic(self):
        prices = _gc_cl(n=250, seed=23)
        t1, p1 = nf06.build_spread_targets(prices, lookback=120, entry_z=2.0, exit_z=0.75)
        t2, p2 = nf06.build_spread_targets(prices, lookback=120, entry_z=2.0, exit_z=0.75)
        pd.testing.assert_frame_equal(t1, t2)
        pd.testing.assert_series_equal(p1, p2)

    def test_period_metrics_keys(self):
        r = pd.Series(np.random.default_rng(0).normal(0.0002, 0.01, 100))
        m = nf06._period_metrics(r, 10)
        assert set(m) == {
            "sharpe",
            "max_drawdown",
            "profit_factor",
            "trades",
            "gross_profit",
            "gross_loss",
            "n_periods",
        }

    def test_stationarity_diagnostic_shape(self):
        s = nf06.spread_series(_gc_cl(n=200))
        d = nf06._stationarity_diagnostic(s)
        assert "acf1" in d and "ar1_coef" in d and d["n"] > 0
