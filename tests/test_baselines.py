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
