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
    sig_ls = baselines.ewma_crossover_signals(
        prices, fast_span=5, slow_span=10, long_only=False
    )
    assert (sig_ls.values >= -1).all() and (sig_ls.values <= 1).all()


def test_ewma_short_not_enough():
    prices = _make_prices(n_days=15)
    sig = baselines.ewma_crossover_signals(prices, fast_span=5, slow_span=20, long_only=True)
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
        prices, lookback=50, skip=5, long_only=True, volatility_scale=True, target_vol=0.1
    )
    assert sig.shape == prices.shape
    sig_no_vol = baselines.time_series_momentum_signals(
        prices, lookback=50, skip=5, long_only=True, volatility_scale=False
    )
    assert sig_no_vol.shape == prices.shape


def test_tsmom_long_short():
    prices = _make_prices(n_days=300)
    sig = baselines.time_series_momentum_signals(
        prices, lookback=50, skip=5, long_only=False, volatility_scale=True, target_vol=0.1
    )
    assert (sig.values >= -2).all() and (sig.values <= 2).all()


def test_tsmom_edge_zeros():
    idx = pd.date_range("2020-01-01", periods=100, freq="D")
    prices = pd.DataFrame({"A": [1.0] * 100}, index=idx)
    sig = baselines.time_series_momentum_signals(
        prices, lookback=30, skip=5, long_only=False, volatility_scale=True
    )
    assert sig.shape == prices.shape
