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
    sig = baselines.ewma_crossover_signals(
        prices, fast_span=5, slow_span=10, long_only=True
    )
    assert sig.shape == prices.shape
    sig_ls = baselines.ewma_crossover_signals(
        prices, fast_span=5, slow_span=10, long_only=False
    )
    assert (sig_ls.values >= -1).all() and (sig_ls.values <= 1).all()


def test_ewma_short_not_enough():
    prices = _make_prices(n_days=15)
    sig = baselines.ewma_crossover_signals(
        prices, fast_span=5, slow_span=20, long_only=True
    )
    assert sig.values.sum() == 0


def test_momentum_basic():
    prices = _make_prices(n_days=300)
    sig = baselines.momentum_signals(prices, lookback=20, skip=5, long_only=True)
    assert sig.shape == prices.shape
    sig_ls = baselines.momentum_signals(
        prices, lookback=20, skip=5, long_only=False, n_top=1
    )
    assert sig_ls.shape == prices.shape


def test_momentum_top_n():
    prices = _make_prices(n_days=300, n_syms=5)
    sig = baselines.momentum_signals(
        prices, lookback=30, skip=5, long_only=True, n_top=2
    )
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
    sig = baselines.momentum_signals(
        prices, lookback=30, skip=5, long_only=False, n_top=1
    )
    assert isinstance(sig, pd.DataFrame)
    assert sig.shape == prices.shape


def test_vol_scaled_tsmom_constant_prices():
    idx = pd.date_range("2020-01-01", periods=100, freq="D")
    prices = pd.DataFrame({"A": [1.0] * 100}, index=idx)
    sig = baselines.vol_scaled_tsmom_signals(
        prices, lookback=30, skip=5, long_only=True
    )
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
    sig = baselines.momentum_signals(
        prices, lookback=30, skip=5, long_only=False, n_top=None
    )
    assert isinstance(sig, pd.DataFrame)
    # When all negative and long_short, each gets negative weight (-1/2)
    assert np.allclose(sig.iloc[-1].values, -0.5)
