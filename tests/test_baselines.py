from __future__ import annotations

import numpy as np
import pandas as pd

from qtr.strategies import baselines


def _make_prices(n_days: int = 100, n_syms: int = 3, start: str = "2020-01-01"):
    idx = pd.date_range(start, periods=n_days, freq="D")
    rng = np.random.default_rng(12345)
    data = rng.normal(0, 0.01, (n_days, n_syms)).cumsum(0)
    prices = pd.DataFrame(data, index=idx, columns=[f"S{i}" for i in range(n_syms)])
    return prices


def test_moving_average_crossover_basic():
    prices = _make_prices()
    sig = baselines.moving_average_crossover_signals(
        prices, fast_window=5, slow_window=10, long_only=True
    )
    assert isinstance(sig, pd.DataFrame)
    assert sig.shape == prices.shape
    assert set(sig.columns) == set(prices.columns)
    assert (sig.values >= 0).all()


def test_moving_average_crossover_short_not_enough():
    prices = _make_prices(n_days=15)
    sig = baselines.moving_average_crossover_signals(
        prices, fast_window=5, slow_window=20, long_only=True
    )
    assert sig.values.sum() == 0


def test_moving_average_crossover_long_short():
    prices = _make_prices()
    sig = baselines.moving_average_crossover_signals(
        prices, fast_window=5, slow_window=10, long_only=False
    )
    assert isinstance(sig, pd.DataFrame)
    vals = sig.values
    assert (vals >= -1).all() and (vals <= 1).all()


def test_buy_and_hold():
    prices = _make_prices()
    sig = baselines.buy_and_hold_signals(prices, weight=0.5)
    assert (sig.values == 0.5).all()
    sig2 = baselines.buy_and_hold_signals(prices)
    assert (sig2.values == 1.0).all()


def test_ewma_crossover():
    prices = _make_prices()
    sig = baselines.ewma_crossover_signals(prices, fast_span=5, slow_span=10, long_only=True)
    assert sig.shape == prices.shape
    sig_ls = baselines.ewma_crossover_signals(prices, fast_span=5, slow_span=10, long_only=False)
    assert (sig_ls.values >= -1).all() and (sig_ls.values <= 1).all()


def test_ewma_short_not_enough():
    prices = _make_prices(n_days=15)
    sig = baselines.ewma_crossover_signals(prices, fast_span=5, slow_span=20, long_only=True)
    assert sig.values.sum() == 0


def test_momentum_basic():
    prices = _make_prices(n_days=300)
    sig = baselines.momentum_signals(prices, lookback=20, skip=5, long_only=True)
    assert sig.shape == prices.shape
    sig_ls = baselines.momentum_signals(prices, lookback=20, skip=5, long_only=False, n_top=1)
    assert sig_ls.shape == prices.shape


def test_momentum_top_n():
    prices = _make_prices(n_days=300, n_syms=5)
    sig = baselines.momentum_signals(prices, lookback=30, skip=5, long_only=True, n_top=2)
    # on any day with signal, sum magnitude relates to weights
    assert sig.shape == prices.shape


def test_momentum_empty_case():
    prices = _make_prices(n_days=50)
    sig = baselines.momentum_signals(prices, lookback=100, skip=10)
    assert sig.values.sum() == 0


def test_mean_reversion_basic():
    prices = _make_prices()
    sig = baselines.mean_reversion_signals(prices, window=20, long_only=True)
    assert sig.shape == prices.shape
    sig_ls = baselines.mean_reversion_signals(prices, window=20, long_only=False)
    assert (sig_ls.values >= -1).all() and (sig_ls.values <= 1).all()


def test_mean_reversion_short():
    prices = _make_prices(n_days=15)
    sig = baselines.mean_reversion_signals(prices, window=20)
    assert sig.values.sum() == 0


class TestZeroVolatilityIsNotASignal:
    """A zero-volatility bar carries no mean-reversion information.

    When the rolling standard deviation is zero the Bollinger bands collapse
    to the rolling mean and *every* bar is simultaneously at, below and above
    them: a constant price series (a flat book, a synthetic fixture, a symbol
    that has not yet moved) has no mean-reversion signal to give. The old
    long/short construction booked every such bar as a SHORT and then held it
    through the forward fill, so a zero-volatility symbol in a long/short book
    carried a full -1.0 short weight. The invariant is that a bar whose
    realized volatility is not positive is flat, for both long-only and
    long/short.
    """

    @staticmethod
    def _flat_prices(length: int = 120) -> pd.DataFrame:
        index = pd.bdate_range("2020-01-01", periods=length)
        return pd.DataFrame({"FLAT": [100.0] * length}, index=index)

    def test_zero_volatility_produces_zero_weight_in_long_short(self):
        prices = self._flat_prices()
        sigma = prices["FLAT"].rolling(20).std()
        assert (sigma.dropna() == 0.0).all(), (
            "the fixture must carry zero realized volatility after the warmup"
        )

        sig = baselines.mean_reversion_signals(prices, window=20, num_std=2.0, long_only=False)
        bad = sig["FLAT"].values
        assert (np.abs(bad) <= 1e-9).all(), (
            f"zero-volatility bars must produce zero mean-reversion weight in "
            f"long/short mode; got {int((np.abs(bad) > 1e-9).sum())} offending rows"
        )
        assert (bad >= -1e-9).all(), "a zero-volatility bar must not be booked as a short"

    def test_zero_volatility_produces_zero_weight_in_long_only(self):
        prices = self._flat_prices()
        sig = baselines.mean_reversion_signals(prices, window=20, num_std=2.0, long_only=True)
        assert (np.abs(sig["FLAT"].values) <= 1e-9).all(), (
            "zero-volatility bars must produce zero mean-reversion weight in long-only mode too"
        )

    def test_a_zero_volatility_symbol_stays_flat_alongside_a_trading_symbol(self):
        """A mixed panel must not let the flat symbol leak a short.

        The forward fill carries the last *valid* signal forward, so the flat
        symbol's column stays at zero even when a neighbouring symbol is
        trading around it. The trading symbol is a high-volatility random
        walk (not a monotone trend: a trend never crosses its own 2-sigma
        band, so it would not trade either).
        """
        length = 200
        idx = pd.bdate_range("2020-01-01", periods=length)
        rng = np.random.default_rng(7)
        data = np.zeros((length, 2))
        data[:, 0] = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.05, length)))
        data[:, 1] = 100.0  # flat: must stay flat
        prices = pd.DataFrame(data, index=idx, columns=["TREND", "FLAT"])

        sig = baselines.mean_reversion_signals(prices, window=20, num_std=2.0, long_only=False)
        assert (np.abs(sig["FLAT"].values) <= 1e-9).all(), (
            "a zero-volatility symbol in a long/short book must stay flat"
        )
        assert (np.abs(sig["TREND"].values) > 1e-9).any(), (
            "the neighbouring trading symbol must still trade"
        )

    def test_the_contract_rejects_the_pre_fix_zero_volatility_is_a_short(self):
        """Behavioural negative control: the pre-fix construction assigns
        ``price >= upper`` to -1 unconditionally, so on a zero-volatility
        panel every bar after the warmup is booked as a SHORT. The corrected
        construction must not be that one.
        """
        prices = self._flat_prices()
        price = prices["FLAT"].dropna()
        rolling_mean = price.rolling(20).mean()
        rolling_std = price.rolling(20).std()
        upper = rolling_mean + 2.0 * rolling_std
        pre_fix = pd.Series(0.0, index=price.index)
        pre_fix[price <= upper] = 1.0
        pre_fix[price >= upper] = -1.0
        pre_fix = pre_fix.ffill().fillna(0)
        # The warmup bars (where the rolling std is NaN) are filled by the
        # forward fill with the first *assigned* value, so they are an
        # artefact of the ffill rather than of the zero-volatility mapping;
        # the invariant is pinned on the bars where the rolling std exists.
        valid = rolling_std.notna()
        assert (pre_fix[valid] == -1.0).all(), (
            "the negative control must reconstruct the pre-fix zero-volatility-is-a-short mapping"
        )

        sig = baselines.mean_reversion_signals(prices, window=20, num_std=2.0, long_only=False)
        assert not (sig["FLAT"].values == pre_fix.values).all(), (
            "the corrected signal must not reproduce the pre-fix zero-volatility-is-a-short mapping"
        )


def test_tsmom_basic():
    prices = _make_prices(n_days=300)
    sig = baselines.time_series_momentum_signals(
        prices,
        lookback=50,
        skip=5,
        long_only=True,
        volatility_scale=True,
        target_vol=0.1,
    )
    assert sig.shape == prices.shape
    sig_no_vol = baselines.time_series_momentum_signals(
        prices, lookback=50, skip=5, long_only=True, volatility_scale=False
    )
    assert sig_no_vol.shape == prices.shape


def test_tsmom_long_short():
    prices = _make_prices(n_days=300)
    sig = baselines.time_series_momentum_signals(
        prices,
        lookback=50,
        skip=5,
        long_only=False,
        volatility_scale=True,
        target_vol=0.1,
    )
    assert (sig.values >= -2).all() and (sig.values <= 2).all()


def test_tsmom_edge_zeros():
    idx = pd.date_range("2020-01-01", periods=100, freq="D")
    prices = pd.DataFrame({"A": [1.0] * 100}, index=idx)
    sig = baselines.time_series_momentum_signals(
        prices, lookback=30, skip=5, long_only=False, volatility_scale=True
    )
    assert sig.shape == prices.shape


def test_tsmom_max_position_size_caps_weights():
    idx = pd.date_range("2020-01-01", periods=300, freq="D")
    # Strong upward trend with tiny oscillation: positive momentum, very low vol
    # so _vol_scale returns the 2x leverage cap and weights reach 2.0 uncapped.
    prices = pd.DataFrame(
        {"A": 100.0 + 0.1 * np.arange(300) + 0.01 * np.sin(np.arange(300))},
        index=idx,
    )
    sig_capped = baselines.time_series_momentum_signals(
        prices,
        lookback=50,
        skip=5,
        long_only=True,
        volatility_scale=True,
        target_vol=0.15,
        max_position_size=1.0,
    )
    assert sig_capped.shape == prices.shape
    # The per-asset cap binds: no weight exceeds 1.0 in absolute value.
    assert (sig_capped["A"].abs() <= 1.0).all()

    sig_uncapped = baselines.time_series_momentum_signals(
        prices,
        lookback=50,
        skip=5,
        long_only=True,
        volatility_scale=True,
        target_vol=0.15,
        max_position_size=2.0,
    )
    # Default cap (2.0) is unchanged: vol scaling can still reach 2.0.
    assert (sig_uncapped["A"].abs() <= 2.0).all()
    assert (sig_uncapped["A"] == 2.0).any(), (
        "volatility scaling should reach the 2x cap so the max_position_size "
        "clipping is actually exercised"
    )


def test_momentum_long_short_n_top_negative():
    # Creates clear positive and negative momentum
    idx = pd.date_range("2020-01-01", periods=60, freq="D")
    data = np.zeros((60, 3))
    for i in range(60):
        data[i, 0] = 0.01 * i  # up
        data[i, 1] = -0.01 * i  # down
        data[i, 2] = 0.0
    prices = pd.DataFrame(data, index=idx, columns=["S0", "S1", "S2"])
    sig = baselines.momentum_signals(prices, lookback=30, skip=5, long_only=False, n_top=1)
    assert isinstance(sig, pd.DataFrame)
    assert sig.shape == prices.shape


def test_vol_scaled_tsmom_constant_prices():
    idx = pd.date_range("2020-01-01", periods=100, freq="D")
    prices = pd.DataFrame({"A": [1.0] * 100}, index=idx)
    sig = baselines.vol_scaled_tsmom_signals(prices, lookback=30, skip=5, long_only=True)
    assert sig.shape == prices.shape
    assert np.allclose(sig.values, 0.0)


def test_vol_scaled_tsmom_long_short_with_momentum():
    idx = pd.date_range("2020-01-01", periods=150, freq="D")
    data = np.zeros((150, 2))
    for i in range(150):
        data[i, 0] = 0.005 * i
        data[i, 1] = -0.005 * i
    prices = pd.DataFrame(data, index=idx, columns=["U", "D"])
    sig = baselines.vol_scaled_tsmom_signals(
        prices, lookback=60, skip=10, long_only=False, vol_window=30
    )
    assert sig.shape == prices.shape
    # Should have some non-zero values
    assert not np.allclose(sig.values, 0.0)


def test_carry_basic():
    idx = pd.date_range("2020-01-01", periods=300, freq="D")
    data = np.zeros((300, 3))
    for i in range(300):
        data[i, 0] = 1.0 + 0.001 * i
        data[i, 1] = 1.0 - 0.001 * i
        data[i, 2] = 1.0
    prices = pd.DataFrame(data, index=idx, columns=["A", "B", "C"])
    sig = baselines.carry_signals(prices, lookback=252, long_only=True)
    assert sig.shape == prices.shape
    sig_ls = baselines.carry_signals(prices, lookback=252, long_only=False)
    assert sig_ls.shape == prices.shape


def test_carry_short_history():
    idx = pd.date_range("2020-01-01", periods=30, freq="D")
    prices = pd.DataFrame({"A": np.arange(30)}, index=idx)
    sig = baselines.carry_signals(prices, lookback=252)
    assert sig.shape == prices.shape


def test_get_strategy_error_and_registry():
    import pytest

    with pytest.raises(ValueError):
        baselines.get_strategy("nonexistent_strategy_xyz")
    assert "ma_crossover" in baselines.STRATEGY_REGISTRY
    assert callable(baselines.get_strategy("ma_crossover"))


def test_run_strategy():
    prices = _make_prices(n_days=100)
    sig = baselines.run_strategy(prices, "buy_and_hold", weight=0.3)
    assert np.allclose(sig.values, 0.3)
    sig2 = baselines.run_strategy(prices, "momentum", lookback=20, skip=5)
    assert sig2.shape == prices.shape


def test_momentum_all_negative_long_short():
    idx = pd.date_range("2020-01-01", periods=60, freq="D")
    data = np.zeros((60, 2))
    for i in range(60):
        data[i, 0] = 10 - 0.1 * i
        data[i, 1] = 10 - 0.2 * i
    prices = pd.DataFrame(data, index=idx, columns=["S0", "S1"])
    sig = baselines.momentum_signals(prices, lookback=30, skip=5, long_only=False, n_top=None)
    assert isinstance(sig, pd.DataFrame)
    # When all negative and long_short, each gets negative weight (-1/2)
    assert np.allclose(sig.iloc[-1].values, -0.5)


class TestMomentumTopNLongShortDisjoint:
    """The long and short n_top sets must be disjoint.

    With ``n_top`` symbols longed and ``n_top`` shorted, when ``2 * n_top``
    exceeds the number of symbols carrying momentum the two selections overlap.
    The old construction assigned the long weight first and then overwrote it
    with the short weight, so a symbol with positive momentum that landed in
    both lists was booked as a SHORT. A symbol is never simultaneously long and
    short: the long side is dropped first, and the short leg is skipped when
    nothing remains.
    """

    @staticmethod
    def _overlap_prices() -> pd.DataFrame:
        """Three symbols, all trending, so momentum never ties.

        S0 rises fastest, S1 rises slower (still positive momentum), S2 falls.
        With ``n_top=2`` the old top set is {S0, S1} and the old bottom set is
        {S2, S1}: S1 is in both and has positive momentum.
        """
        idx = pd.date_range("2020-01-01", periods=40, freq="D")
        data = np.zeros((40, 3))
        for i in range(40):
            data[i, 0] = 100 + 0.1 * i  # S0: up fastest
            data[i, 1] = 100 + 0.05 * i  # S1: up slower (positive momentum)
            data[i, 2] = 100 - 0.2 * i  # S2: down
        return pd.DataFrame(data, index=idx, columns=["S0", "S1", "S2"])

    def test_positive_momentum_symbol_is_not_shorted_on_overlap(self):
        prices = self._overlap_prices()
        sig = baselines.momentum_signals(prices, lookback=20, skip=1, long_only=False, n_top=2)
        last = sig.iloc[-1]
        # S1 has positive momentum and must not carry a short weight.
        assert last["S1"] >= 0.0, (
            f"a positive-momentum symbol must not be shorted on n_top overlap; S1={last['S1']}"
        )
        # S0 is longed, S2 is shorted, and the book nets to zero.
        assert last["S0"] > 0.0, "the top-momentum symbol must be longed"
        assert last["S2"] < 0.0, "the bottom-momentum symbol must be shorted"
        assert abs(last.sum()) <= 1e-9, "a long/short book must net to zero"

    def test_long_only_branch_is_unaffected_by_the_overlap(self):
        prices = self._overlap_prices()
        sig = baselines.momentum_signals(prices, lookback=20, skip=1, long_only=True, n_top=2)
        last = sig.iloc[-1]
        assert last["S0"] > 0.0 and last["S1"] > 0.0, "the two top symbols are longed"
        assert last["S2"] == 0.0, "the bottom symbol is flat in long-only mode"
        assert abs(last.sum() - 1.0) <= 1e-9, "long-only weights sum to one"

    def test_the_contract_rejects_the_pre_fix_overlap_is_a_short(self):
        """Behavioural negative control: the pre-fix construction assigned the
        long weight and then the short weight to the overlapping symbol, so on
        the overlap fixture S1 (positive momentum) ended at -0.25. The
        corrected construction must not reproduce that mapping.
        """
        prices = self._overlap_prices()
        mom = prices.pct_change(20).shift(1)
        date = mom.index[-1]
        mom_vals = mom.loc[date].dropna()
        n_top = 2
        top_symbols = mom_vals.nlargest(n_top).index
        pre_fix = pd.Series(0.0, index=prices.columns)
        pre_fix[list(top_symbols)] = 1.0 / (2 * len(top_symbols))
        pre_fix[list(mom_vals.nsmallest(n_top).index)] = -1.0 / (2 * n_top)
        assert pre_fix["S1"] < 0.0, (
            "the negative control must reconstruct the pre-fix overlap-is-a-short mapping"
        )

        sig = baselines.momentum_signals(prices, lookback=20, skip=1, long_only=False, n_top=2)
        assert sig.loc[date, "S1"] != pre_fix["S1"], (
            "the corrected signal must not book the overlapping positive-momentum symbol as a short"
        )


def test_momentum_degenerate_guard_returns_empty():
    """The degenerate-input guard (lookback <= 0 or skip < 0) returns an
    empty signal frame rather than computing on a nonsensical lookback."""
    prices = _make_prices(n_days=60)
    assert np.allclose(baselines.momentum_signals(prices, lookback=0, skip=5).values, 0.0)
    assert np.allclose(baselines.momentum_signals(prices, lookback=20, skip=-1).values, 0.0)


def test_momentum_n_top_exhausts_symbols_skips_short_leg():
    """When ``n_top`` meets or exceeds the symbol count the long side takes
    every symbol and the short side has nothing left to short, so the short
    leg is skipped (the bottom set is empty)."""
    prices = _make_prices(n_days=60, n_syms=2)
    sig = baselines.momentum_signals(prices, lookback=20, skip=1, long_only=False, n_top=5)
    last = sig.iloc[-1]
    assert (last >= 0.0).all(), "no short leg when n_top exhausts the universe"
    assert (last > 0.0).all(), "the long side takes every symbol"


def test_mean_reversion_degenerate_guard_returns_empty():
    prices = _make_prices(n_days=60)
    assert np.allclose(baselines.mean_reversion_signals(prices, window=0).values, 0.0)
    assert np.allclose(baselines.mean_reversion_signals(prices, num_std=-1.0).values, 0.0)


def test_time_series_momentum_degenerate_guard_returns_empty():
    prices = _make_prices(n_days=60)
    assert np.allclose(baselines.time_series_momentum_signals(prices, lookback=0).values, 0.0)


def test_vol_scaled_tsmom_degenerate_guard_returns_empty():
    prices = _make_prices(n_days=60)
    assert np.allclose(baselines.vol_scaled_tsmom_signals(prices, lookback=0).values, 0.0)


def test_carry_degenerate_guard_returns_empty():
    prices = _make_prices(n_days=60)
    assert np.allclose(baselines.carry_signals(prices, lookback=0).values, 0.0)


def test_momentum_long_short_all_positive_covers_empty_negative_branch():
    """All prices rise, so momentum is always positive: with long_only=False
    and n_top=None the negative set is empty and the short leg is skipped
    (arc ``if len(negative) > 0`` -> next loop iteration)."""
    idx = pd.date_range("2020-01-01", periods=60, freq="D")
    prices = pd.DataFrame(
        {"A": 100 + 0.1 * np.arange(60), "B": 100 + 0.05 * np.arange(60)},
        index=idx,
    )
    sig = baselines.momentum_signals(prices, lookback=20, skip=1, long_only=False, n_top=None)
    assert (sig.values >= 0.0).all()
    assert np.allclose(sig.iloc[-1].values, 0.5)


class TestZeroMomentumIsNotAShort:
    """A zero-momentum bar carries no trend information.

    The rank-based ``n_top`` branch used to select its long and short sets with
    ``nlargest``/``nsmallest`` over the *whole* momentum frame. Those functions
    rank an all-zero series by position rather than by value: on a bar where
    every symbol's momentum is exactly zero they return one symbol (the first)
    and book it as long or short. A price series that returns exactly to its
    starting level over the lookback window (a repeating cycle, a flat book, a
    synthetic fixture) therefore carried a full short weight in long/short mode
    -- the same defect H67 fixed in ``vol_scaled_tsmom_signals`` and H68 in
    ``cs_momentum_vol_scaled``, which use ``np.sign``. Here the construction is
    rank-based, so the equivalent is to rank over the non-zero subset.

    The invariant is that a bar whose momentum is exactly zero receives zero
    weight, for both long-only and long/short, and for both ``n_top`` and
    ``n_top=None`` (the latter already filtered on ``> 0`` / ``< 0`` and is
    pinned so it cannot regress to a rank-based form).
    """

    @staticmethod
    def _repeating_prices(period: int = 3, length: int = 200) -> pd.DataFrame:
        """A price series that returns to the same level every ``period`` bars.

        ``pct_change(period)`` is therefore EXACTLY zero on every bar after the
        first period, while the intra-period moves give a strictly positive
        realised volatility. This is the minimal input that separates "zero
        momentum" from "no volatility".
        """
        index = pd.bdate_range("2020-01-01", periods=length)
        pattern = [100.0, 101.0, 102.0]
        prices = pd.DataFrame(
            {"REP": np.tile(pattern, length // period + 1)[:length]},
            index=index,
        )
        return prices

    def _zero_mom_mask(self, prices, lookback, skip):
        mom = prices.pct_change(lookback).shift(skip)
        return mom["REP"].abs() < 1e-12

    def test_long_short_n_top_zero_momentum_produces_zero_weight(self):
        prices = self._repeating_prices()
        zm = self._zero_mom_mask(prices, lookback=3, skip=1)
        assert zm.sum() > 0, "the fixture must actually produce zero momentum"

        sig = baselines.momentum_signals(prices, lookback=3, skip=1, long_only=False, n_top=1)
        bad = sig.loc[zm, "REP"]
        assert (bad.abs() <= 1e-9).all(), (
            f"zero-momentum bars must produce zero weight in long/short n_top mode; "
            f"got {int((bad.abs() > 1e-9).sum())} offending rows"
        )
        assert (bad >= -1e-9).all(), "a zero-momentum bar must not be booked as a short"

    def test_long_only_n_top_zero_momentum_produces_zero_weight(self):
        prices = self._repeating_prices()
        zm = self._zero_mom_mask(prices, lookback=3, skip=1)
        sig = baselines.momentum_signals(prices, lookback=3, skip=1, long_only=True, n_top=1)
        bad = sig.loc[zm, "REP"]
        assert (bad.abs() <= 1e-9).all(), (
            "zero-momentum bars must produce zero weight in long-only n_top mode too"
        )

    def test_n_top_none_zero_momentum_produces_zero_weight(self):
        """The ``n_top=None`` branch filters on ``> 0`` / ``< 0`` and was already
        correct; pin it so it cannot regress to a rank-based form."""
        prices = self._repeating_prices()
        zm = self._zero_mom_mask(prices, lookback=3, skip=1)
        for long_only in (True, False):
            sig = baselines.momentum_signals(
                prices, lookback=3, skip=1, long_only=long_only, n_top=None
            )
            bad = sig.loc[zm, "REP"]
            assert (bad.abs() <= 1e-9).all(), (
                f"zero-momentum bars must produce zero weight in n_top=None "
                f"mode (long_only={long_only})"
            )

    def test_all_zero_momentum_bar_is_flat_with_no_division(self):
        """A bar where every symbol's momentum is exactly zero must be flat --
        the empty ranked set must not reach the ``1 / len(top_symbols)``
        division (which would be a ZeroDivisionError)."""
        idx = pd.date_range("2020-01-01", periods=60, freq="D")
        prices = pd.DataFrame(
            {"A": [100.0] * 60, "B": [101.0] * 60},
            index=idx,
        )
        # Constant prices => momentum is identically zero for every symbol.
        sig = baselines.momentum_signals(prices, lookback=20, skip=1, long_only=False, n_top=1)
        assert (sig.values == 0.0).all(), (
            "an all-zero-momentum panel must be entirely flat, with no division"
        )

    def test_the_contract_rejects_the_pre_fix_rank_by_position(self):
        """Behavioural negative control: the pre-fix construction ranked the
        whole momentum frame with ``nlargest``/``nsmallest``, so on a bar where
        every symbol's momentum is exactly zero it booked the first symbol as a
        long (and, in long/short mode, a short). The corrected construction must
        not reproduce that mapping."""
        prices = self._repeating_prices()
        mom = prices.pct_change(3).shift(1)
        zm = self._zero_mom_mask(prices, lookback=3, skip=1)
        # Reconstruct the pre-fix selection over the whole frame.
        mom_vals = mom.loc[zm.index[zm], "REP"].dropna()
        pre_fix_top = mom_vals.nlargest(1)
        assert len(pre_fix_top) == 1, (
            "the negative control must reconstruct the pre-fix rank-by-position "
            "mapping on an all-zero momentum frame"
        )

        sig = baselines.momentum_signals(prices, lookback=3, skip=1, long_only=False, n_top=1)
        assert (sig.loc[zm, "REP"].abs() <= 1e-9).all(), (
            "the corrected signal must not book a zero-momentum bar"
        )
