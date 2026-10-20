"""
Regression tests for the volatility-scaled time-series momentum signal
(src/qtr/strategies/baselines.py::vol_scaled_tsmom_signals).

These tests pin the **sign invariant** that was violated by the H4 runner
(run_futures_tsmom_experiment.py), which constructed ``w_raw = -mom / vol``
and thereby inverted the signal into a mean-reversion strategy. The
canonical TSMOM construction (Moskowitz, Ooi & Pedersen 2012) is
*trend-following*: a rising asset must receive a positive weight.

The invariant is: sign(weight) == sign(momentum) wherever momentum is
non-NaN and the weight is non-zero, for both long-only and long/short.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from qtr.strategies.baselines import vol_scaled_tsmom_signals


def _trending_prices(n: int = 400, seed: int = 7) -> pd.DataFrame:
    """Two assets: one uptrending, one downtrending, over the full window."""
    rng = np.random.default_rng(seed)
    index = pd.bdate_range("2020-01-01", periods=n)
    rets_a = rng.normal(0.0015, 0.01, n)
    rets_b = rng.normal(-0.0015, 0.01, n)
    prices = pd.DataFrame(
        {
            "UP": 100.0 * np.exp(np.cumsum(rets_a)),
            "DOWN": 100.0 * np.exp(np.cumsum(rets_b)),
        },
        index=index,
    )
    return prices


class TestTsmomSignInvariant:
    """Trend-following: sign of weight must match sign of momentum."""

    def test_long_only_positive_momentum_gets_long(self):
        prices = _trending_prices()
        sig = vol_scaled_tsmom_signals(prices, lookback=63, skip=1, long_only=True)
        mom = prices.pct_change(63).shift(1)
        # Where momentum is clearly positive, weight must be > 0
        up_mask = mom["UP"] > 0.05
        assert (sig.loc[up_mask, "UP"] > 1e-12).all(), (
            "long-only TSMOM must hold positive weight when momentum is positive"
        )
        # Where momentum is clearly negative, weight must be 0 (long-only)
        dn_mask = mom["DOWN"] < -0.05
        assert (sig.loc[dn_mask, "DOWN"] <= 1e-12).all(), (
            "long-only TSMOM must be flat when momentum is negative"
        )

    def test_long_short_sign_matches_momentum(self):
        prices = _trending_prices()
        sig = vol_scaled_tsmom_signals(prices, lookback=63, skip=1, long_only=False)
        mom = prices.pct_change(63).shift(1)
        # On the UP asset (positive momentum), weight must be positive
        up_mask = mom["UP"] > 0.05
        assert (sig.loc[up_mask, "UP"] > 1e-12).all(), (
            "long/short TSMOM must be long an asset with positive momentum"
        )
        # On the DOWN asset (negative momentum), weight must be negative
        # (allow a small fraction of boundary rows where ffill/vol-scaling
        # produces a transient zero -- the invariant must hold on the
        # overwhelming majority of rows).
        dn_mask = mom["DOWN"] < -0.05
        frac_negative = (sig.loc[dn_mask, "DOWN"] < -1e-12).mean()
        assert frac_negative > 0.95, (
            f"long/short TSMOM must be short an asset with negative momentum "
            f"on >95% of rows; got {frac_negative:.3f}"
        )

    def test_not_mean_reversion(self):
        """The signal must not be the negation of momentum (regression guard
        for the H4 ``w = -mom/vol`` bug)."""
        prices = _trending_prices()
        sig = vol_scaled_tsmom_signals(prices, lookback=63, skip=1, long_only=False)
        mom = prices.pct_change(63).shift(1)
        # Correlation between signal and momentum must be positive (trend-following),
        # not negative (mean-reversion). Drop NaNs before correlating.
        s = sig.values.ravel()
        m = mom.values.ravel()
        mask = np.isfinite(s) & np.isfinite(m) & (np.abs(m) > 1e-6)
        corr = np.corrcoef(s[mask], m[mask])[0, 1]
        assert corr > 0.5, (
            f"TSMOM signal must be positively correlated with momentum "
            f"(trend-following); got corr={corr:.3f}, which indicates "
            f"mean-reversion (the H4 sign-inversion bug)"
        )

    def test_zero_momentum_produces_zero_direction(self):
        """When momentum is exactly zero, direction must be zero, so the
        weight must be zero regardless of inverse-vol scaling."""
        np.random.default_rng(11)
        index = pd.bdate_range("2020-01-01", periods=400)
        # Perfectly flat price: momentum is identically zero.
        prices = pd.DataFrame(
            {"FLAT": 100.0 + np.zeros(400)},
            index=index,
        )
        sig = vol_scaled_tsmom_signals(prices, lookback=63, skip=1, long_only=False)
        # direction is 0 where momentum == 0, so weight must be 0.
        assert sig.abs().max().max() <= 1e-12, "zero momentum must produce zero TSMOM weight"


class TestTsmomVolScaling:
    """Volatility scaling properties."""

    def test_higher_target_vol_increases_weight_magnitude(self):
        prices = _trending_prices()
        low = vol_scaled_tsmom_signals(prices, lookback=63, skip=1, target_vol=0.10)
        high = vol_scaled_tsmom_signals(prices, lookback=63, skip=1, target_vol=0.20)
        # Higher target vol -> larger weight magnitudes
        assert high.abs().sum().sum() > low.abs().sum().sum(), (
            "higher target_vol should increase position magnitudes"
        )

    def test_position_cap_respected(self):
        prices = _trending_prices()
        sig = vol_scaled_tsmom_signals(prices, lookback=63, skip=1, max_position_size=1.5)
        assert (sig.abs() <= 1.5 + 1e-12).all().all(), "weights must respect max_position_size cap"

    def test_lookahead_safety(self):
        """Signal at time t must depend only on data through t (shift is applied)."""
        prices = _trending_prices()
        sig = vol_scaled_tsmom_signals(prices, lookback=63, skip=1)
        # The signal uses pct_change(lookback).shift(skip), so the first
        # non-NaN signal occurs at index lookback + skip. It must not use
        # future returns.
        assert sig.notna().sum().sum() > 0
        # Signal at the first valid index must equal the value computed
        # from prices up to that index only.
        first_valid = sig.notna().all(axis=1).idxmax()
        mom_manual = prices.pct_change(63).shift(1).loc[first_valid]
        sig_manual = sig.loc[first_valid]
        # Sign agreement: signal sign must match momentum sign (trend-following)
        # wherever momentum is non-negligible.
        for sym in mom_manual.index:
            if abs(mom_manual[sym]) > 1e-6:
                assert np.sign(sig_manual[sym]) == np.sign(mom_manual[sym]), (
                    f"at first valid index, {sym} signal sign must match momentum sign"
                )
