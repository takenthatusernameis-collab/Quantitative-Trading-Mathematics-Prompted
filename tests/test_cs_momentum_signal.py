"""
Regression tests for the cross-sectional momentum signal builder
(run_cs_momentum_experiment.py::cs_momentum_vol_scaled).

These tests pin the **sign invariant**: a zero-momentum bar carries no trend
information, so it must receive zero weight in both long-only and long/short
mode. The long/short direction used to be
``(mom > 0).astype(float) * 2.0 - 1.0``, which maps an exact zero to -1: a
price series that returns exactly to its starting level over the lookback
window (a repeating cycle, a flat book, a synthetic fixture) was therefore
booked as a SHORT. The position is then inverse-volatility-scaled, so the
error is not cosmetic -- a zero-momentum bar with positive realised volatility
produced a non-zero short weight. ``np.sign(mom)`` returns 0.0 for an exact
zero, so zero momentum now yields zero direction and zero weight.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from run_cs_momentum_experiment import cs_momentum_vol_scaled


def _repeating_prices(period: int = 3, length: int = 200) -> pd.DataFrame:
    """A price series that returns to the same level every ``period`` bars.

    pct_change(period) is therefore EXACTLY zero on every bar after the first
    period, while the intra-period moves give a strictly positive realised
    volatility. This is the minimal input that separates "zero momentum" from
    "no volatility".
    """
    index = pd.bdate_range("2020-01-01", periods=length)
    pattern = [100.0, 101.0, 102.0]
    prices = pd.DataFrame(
        {"REP": np.tile(pattern, length // period + 1)[:length]},
        index=index,
    )
    return prices


class TestZeroMomentumIsNotAShort:
    """Zero momentum must produce zero weight, in both directions."""

    def test_long_short_zero_momentum_produces_zero_weight(self):
        prices = _repeating_prices()
        sig = cs_momentum_vol_scaled(prices, lookback=3, skip=1, long_only=False)
        mom = prices.pct_change(3).shift(1)
        sigma = prices.pct_change().rolling(3).std() * np.sqrt(252)

        zero_mom = mom["REP"].abs() < 1e-12
        assert zero_mom.sum() > 0, "the fixture must actually produce zero momentum"
        assert (sigma["REP"][zero_mom] > 1e-6).all(), (
            "the fixture must carry positive volatility on its zero-momentum bars"
        )

        bad = sig.loc[zero_mom, "REP"]
        assert (bad.abs() <= 1e-9).all(), (
            f"zero-momentum bars must produce zero weight in long/short mode; "
            f"got {int((bad.abs() > 1e-9).sum())} offending rows"
        )
        assert (bad >= -1e-9).all(), "a zero-momentum bar must not be booked as a short"

    def test_long_only_zero_momentum_still_produces_zero_weight(self):
        prices = _repeating_prices()
        sig = cs_momentum_vol_scaled(prices, lookback=3, skip=1, long_only=True)
        mom = prices.pct_change(3).shift(1)
        zero_mom = mom["REP"].abs() < 1e-12
        bad = sig.loc[zero_mom, "REP"]
        assert (bad.abs() <= 1e-9).all(), (
            "zero-momentum bars must produce zero weight in long-only mode too"
        )

    def test_the_contract_rejects_the_pre_fix_zero_is_short(self):
        """Behavioural negative control: the pre-fix
        ``(mom > 0) * 2 - 1`` construction maps an exact zero to -1, so a
        repeating-cycle price series is booked as a SHORT on every bar. The
        corrected construction must not be that one."""
        prices = _repeating_prices()
        mom = prices.pct_change(3).shift(1)
        pre_fix_direction = (mom > 0).astype(float) * 2.0 - 1.0
        zero_mom = mom["REP"].abs() < 1e-12
        assert (pre_fix_direction.loc[zero_mom, "REP"] == -1.0).all(), (
            "the negative control must reconstruct the pre-fix zero-is-short mapping"
        )

        sig = cs_momentum_vol_scaled(prices, lookback=3, skip=1, long_only=False)
        assert not (sig.loc[zero_mom, "REP"] == pre_fix_direction.loc[zero_mom, "REP"]).all(), (
            "the corrected signal must not reproduce the pre-fix zero-is-short mapping"
        )
