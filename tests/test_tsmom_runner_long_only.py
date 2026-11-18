"""Regression tests for the runner-local ``vol_scaled_tsmom_signals``
long-only branch (run_ts_momentum_experiment.py and
run_regime_gated_momentum_experiment.py).

Both runners carry a *copy* of the volatility-scaled TSMOM construction
rather than importing ``qtr.strategies.baselines.vol_scaled_tsmom_signals``.
The canonical library pins the long-only contract that a negative-momentum
asset is held **flat** (weight 0), never booked short (see
tests/test_tsmom_signal.py::TestTsmomSignInvariant::
test_long_only_positive_momentum_gets_long).

A prior change rewrote the runner long-only branch to ``np.sign(mom)``, which
returns ``-1`` for negative momentum. That both

* books a phantom -1 (and, after inverse-vol scaling and the +/-MAX_POSITION_SIZE
  cap, up to a -2.0) short in a *long-only* book, and
* corrupts the portfolio-level volatility-targeting scale, because the phantom
  short enters ``port_ret = (w_raw.shift(1) * pct).sum(axis=1)`` and therefore
  shrinks every *long* position that does execute.

These tests pin the runners' long-only branch to the canonical library
behaviour: no negative weights, and bit-identical to
``qtr.strategies.baselines.vol_scaled_tsmom_signals(long_only=True)`` on a
clean panel. A behavioural negative control reconstructs the pre-fix
``np.sign(mom)`` construction and asserts the current code no longer matches
it, so a future regression back to ``np.sign`` fails loudly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import run_regime_gated_momentum_experiment as run_rg  # noqa: E402
import run_ts_momentum_experiment as run_ts  # noqa: E402
from qtr.strategies.baselines import (  # noqa: E402
    vol_scaled_tsmom_signals as lib_vol_scaled_tsmom_signals,
)


def _trending_prices(n: int = 400, seed: int = 7) -> pd.DataFrame:
    """Two assets: one uptrending, one downtrending, over the full window."""
    rng = np.random.default_rng(seed)
    index = pd.bdate_range("2020-01-01", periods=n)
    rets_a = rng.normal(0.0015, 0.01, n)
    rets_b = rng.normal(-0.0015, 0.01, n)
    return pd.DataFrame(
        {
            "UP": 100.0 * np.exp(np.cumsum(rets_a)),
            "DOWN": 100.0 * np.exp(np.cumsum(rets_b)),
        },
        index=index,
    )


_RUNNERS = [run_ts, run_rg]


@pytest.mark.parametrize("runner", _RUNNERS, ids=lambda m: m.__name__)
class TestRunnerLongOnlyIsFlatOnNegativeMomentum:
    LOOKBACK = 63
    SKIP = 1

    def test_long_only_has_no_negative_weights(self, runner):
        """A long-only runner book must never hold a negative (short) weight."""
        prices = _trending_prices()
        sig = runner.vol_scaled_tsmom_signals(
            prices, lookback=self.LOOKBACK, skip=self.SKIP, long_only=True
        )
        # The book is long-only, so every weight is >= 0. The pre-fix
        # ``np.sign(mom)`` construction emitted up to -2.0 here.
        assert (sig.to_numpy() >= -1e-12).all(), (
            f"{runner.__name__} long-only produced a negative weight "
            f"(min={sig.to_numpy().min():.6f}); a long-only book must be flat "
            "on negative-momentum assets"
        )

    def test_long_only_flat_where_momentum_negative(self, runner):
        """Where momentum is clearly negative the long-only weight is 0."""
        prices = _trending_prices()
        sig = runner.vol_scaled_tsmom_signals(
            prices, lookback=self.LOOKBACK, skip=self.SKIP, long_only=True
        )
        mom = prices.pct_change(self.LOOKBACK).shift(self.SKIP)
        down = mom["DOWN"] < -0.05
        assert int(down.sum()) > 0, "fixture must produce negative-momentum rows"
        assert (sig.loc[down, "DOWN"].to_numpy() <= 1e-12).all(), (
            f"{runner.__name__} long-only booked a non-flat weight on a negative-momentum asset"
        )

    def test_long_only_matches_canonical_library(self, runner):
        """On a clean panel the runner long-only signal equals the library's.

        Both use MAX_POSITION_SIZE = 2.0 (== the library default), identical
        lookback/skip/target_vol/vol_window defaults and the identical
        construction, so the two must be bit-identical.
        """
        prices = _trending_prices()
        sig = runner.vol_scaled_tsmom_signals(
            prices, lookback=self.LOOKBACK, skip=self.SKIP, long_only=True
        )
        expected = lib_vol_scaled_tsmom_signals(
            prices, lookback=self.LOOKBACK, skip=self.SKIP, long_only=True
        )
        assert np.allclose(sig.to_numpy(), expected.to_numpy(), atol=1e-12), (
            f"{runner.__name__} long-only diverges from the canonical "
            "qtr.strategies.baselines.vol_scaled_tsmom_signals"
        )

    def test_long_short_branch_still_shorts(self, runner):
        """Regression guard: the long/short branch still shorts negative momentum.

        This pins the H67 zero-momentum-is-not-a-short fix (sign(mom), not the
        old ``(mom > 0) * 2 - 1``) and confirms the long-only fix above did not
        accidentally flatten the long/short leg.
        """
        prices = _trending_prices()
        sig = runner.vol_scaled_tsmom_signals(
            prices, lookback=self.LOOKBACK, skip=self.SKIP, long_only=False
        )
        mom = prices.pct_change(self.LOOKBACK).shift(self.SKIP)
        down = mom["DOWN"] < -0.05
        frac_negative = (sig.loc[down, "DOWN"] < -1e-12).mean()
        assert frac_negative > 0.95, (
            f"{runner.__name__} long/short must short a negative-momentum "
            f"asset on >95% of rows; got {frac_negative:.3f}"
        )

    def test_long_only_not_the_pre_fix_sign_construction(self, runner):
        """Behavioural negative control: the pre-fix ``np.sign(mom)`` long-only
        branch booked negative-momentum assets short; the current code must not
        reproduce it."""
        prices = _trending_prices()
        mom = prices.pct_change(self.LOOKBACK).shift(self.SKIP)
        pre_fix_direction = np.sign(mom)
        # The pre-fix long-only direction was -1 on the DOWN asset's
        # negative-momentum rows.
        down = mom["DOWN"] < -0.05
        assert (pre_fix_direction.loc[down, "DOWN"] == -1.0).all(), (
            "the negative control must reconstruct the pre-fix long-only mapping"
        )
        sig = runner.vol_scaled_tsmom_signals(
            prices, lookback=self.LOOKBACK, skip=self.SKIP, long_only=True
        )
        # The corrected long-only signal must be flat (0) there, not the -1
        # pre-fix direction scaled up.
        assert (sig.loc[down, "DOWN"].to_numpy() <= 1e-12).all(), (
            f"{runner.__name__} still reproduces the pre-fix long-only "
            "short-on-negative-momentum mapping"
        )
