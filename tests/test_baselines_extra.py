from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from qtr.strategies import baselines


def _make_prices(n_days: int = 400, n_syms: int = 3, start: str = "2020-01-01", seed=42):
    idx = pd.date_range(start, periods=n_days, freq="D")
    rng = np.random.default_rng(seed)
    data = rng.normal(0, 0.01, (n_days, n_syms)).cumsum(0)
    return pd.DataFrame(data, index=idx, columns=[f"S{i}" for i in range(n_syms)])


def test_vol_scaled_tsmom_basic():
    prices = _make_prices(n_days=500)
    sig = baselines.vol_scaled_tsmom_signals(
        prices,
        lookback=50,
        skip=5,
        long_only=True,
        target_vol=0.1,
        vol_window=30,
        max_position_size=2.0,
    )
    assert sig.shape == prices.shape
    assert ((sig.values >= -2.0) & (sig.values <= 2.0)).all()


def test_vol_scaled_tsmom_long_short():
    prices = _make_prices(n_days=500)
    sig = baselines.vol_scaled_tsmom_signals(
        prices,
        lookback=50,
        skip=5,
        long_only=False,
        target_vol=0.1,
        vol_window=30,
        max_position_size=1.5,
    )
    assert ((sig.values >= -1.5) & (sig.values <= 1.5)).all()


def test_carry_signals_basic():
    prices = _make_prices(n_days=300)
    sig = baselines.carry_signals(prices, lookback=60, long_only=True)
    assert sig.shape == prices.shape
    sig_ls = baselines.carry_signals(prices, lookback=60, long_only=False)
    assert ((sig_ls.values >= -1) & (sig_ls.values <= 1)).all()


def test_carry_empty():
    prices = _make_prices(n_days=50)
    sig = baselines.carry_signals(prices, lookback=100)
    assert sig.values.sum() == 0


def test_registry_and_get_run():
    prices = _make_prices(n_days=100)
    for name in [
        "ma_crossover",
        "buy_and_hold",
        "ewma_crossover",
        "momentum",
        "mean_reversion",
        "time_series_momentum",
        "vol_scaled_tsmom",
        "carry",
    ]:
        fn = baselines.get_strategy(name)
        sig = fn(prices)
        assert sig.shape == prices.shape
    sig = baselines.run_strategy(prices, "buy_and_hold", weight=0.3)
    assert (sig.values == 0.3).all()


def test_get_strategy_invalid():
    with pytest.raises(ValueError):
        baselines.get_strategy("nope")


def test_momentum_signals_n_top_nonpositive_skips():
    prices = _make_prices(n_days=300)
    sig = baselines.momentum_signals(prices, lookback=20, skip=1, n_top=0)
    assert (sig.values == 0).all()


def test_momentum_signals_n_top_negative_skips():
    """A negative ``n_top`` is also nonpositive and must skip every date,
    leaving an all-zero signal frame (the ``n_top <= 0`` guard, H70)."""
    prices = _make_prices(n_days=300)
    sig = baselines.momentum_signals(prices, lookback=20, skip=1, n_top=-1)
    assert (sig.values == 0).all()


def test_vol_scale_nonpositive_vol_returns_one():
    assert baselines._vol_scale(0.0, 0.15) == 1.0
    assert baselines._vol_scale(-1.0, 0.15) == 1.0


def test_ma_crossover_invalid_window():
    prices = _make_prices(n_days=50)
    sig = baselines.moving_average_crossover_signals(prices, fast_window=0, slow_window=10)
    assert (sig.values == 0).all()
    sig2 = baselines.moving_average_crossover_signals(prices, fast_window=5, slow_window=-1)
    assert (sig2.values == 0).all()


def test_ewma_crossover_invalid_span():
    prices = _make_prices(n_days=50)
    sig = baselines.ewma_crossover_signals(prices, fast_span=0, slow_span=10)
    assert (sig.values == 0).all()
    sig2 = baselines.ewma_crossover_signals(prices, fast_span=5, slow_span=-1)
    assert (sig2.values == 0).all()


# ---------------------------------------------------------------------------
# Degenerate numeric-parameter guards.
#
# A window/span/lookback/skip count is used as an ``int`` by pandas; a bool,
# a non-integral float or a nan/inf slipped past the ``<= 0`` guards and raised
# an opaque ``ValueError``/``TypeError``/``OverflowError`` from deep inside
# pandas. A per-asset cap that is negative or non-finite silently disabled
# ``clip`` (the engine closes the same fail-open at its own layer). Both classes
# now fail closed to the all-zero "no exposure" frame the surrounding
# degenerate guards already return, and are bit-identical on every valid input.
# ---------------------------------------------------------------------------

_BAD_INT_PARAMS = [float("nan"), float("inf"), float("-inf"), 20.5, True, "20"]


def test_is_int_distinguishes_real_integers():
    assert baselines._is_int(5)
    assert baselines._is_int(np.int64(5))
    assert not baselines._is_int(True)
    assert not baselines._is_int(np.bool_(True))
    assert not baselines._is_int(20.5)
    assert not baselines._is_int(float("nan"))
    assert not baselines._is_int("20")


def test_is_finite_non_negative_distinguishes_valid_caps():
    assert baselines._is_finite_non_negative(2)
    assert baselines._is_finite_non_negative(2.0)
    assert baselines._is_finite_non_negative(np.float64(1.5))
    assert baselines._is_finite_non_negative(0.0)
    assert not baselines._is_finite_non_negative(-1.0)
    assert not baselines._is_finite_non_negative(float("nan"))
    assert not baselines._is_finite_non_negative(float("inf"))
    assert not baselines._is_finite_non_negative(True)
    assert not baselines._is_finite_non_negative("2")


@pytest.mark.parametrize("bad", _BAD_INT_PARAMS)
def test_ma_crossover_non_integer_window_fails_closed(bad):
    prices = _make_prices(n_days=60)
    sig = baselines.moving_average_crossover_signals(prices, fast_window=bad, slow_window=10)
    assert (sig.values == 0).all()
    sig2 = baselines.moving_average_crossover_signals(prices, fast_window=5, slow_window=bad)
    assert (sig2.values == 0).all()


@pytest.mark.parametrize("bad", _BAD_INT_PARAMS)
def test_ewma_crossover_non_integer_span_fails_closed(bad):
    prices = _make_prices(n_days=60)
    sig = baselines.ewma_crossover_signals(prices, fast_span=bad, slow_span=10)
    assert (sig.values == 0).all()
    sig2 = baselines.ewma_crossover_signals(prices, fast_span=5, slow_span=bad)
    assert (sig2.values == 0).all()


@pytest.mark.parametrize("bad", _BAD_INT_PARAMS)
def test_momentum_non_integer_lookback_or_skip_fails_closed(bad):
    prices = _make_prices(n_days=60)
    sig = baselines.momentum_signals(prices, lookback=bad, skip=1)
    assert (sig.values == 0).all()
    sig2 = baselines.momentum_signals(prices, lookback=20, skip=bad)
    assert (sig2.values == 0).all()


@pytest.mark.parametrize("bad", _BAD_INT_PARAMS)
def test_momentum_non_integer_n_top_fails_closed(bad):
    prices = _make_prices(n_days=60)
    sig = baselines.momentum_signals(prices, lookback=20, skip=1, n_top=bad)
    assert (sig.values == 0).all()


def test_momentum_valid_numpy_integer_n_top_still_runs():
    prices = _make_prices(n_days=60, n_syms=4)
    sig = baselines.momentum_signals(prices, lookback=20, skip=1, n_top=np.int64(2))
    assert sig.shape == prices.shape


@pytest.mark.parametrize("bad", _BAD_INT_PARAMS)
def test_mean_reversion_non_integer_window_fails_closed(bad):
    prices = _make_prices(n_days=60)
    sig = baselines.mean_reversion_signals(prices, window=bad, num_std=2.0)
    assert (sig.values == 0).all()


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1.0, True, "2"])
def test_mean_reversion_non_finite_num_std_fails_closed(bad):
    prices = _make_prices(n_days=60)
    sig = baselines.mean_reversion_signals(prices, window=10, num_std=bad)
    assert (sig.values == 0).all()


@pytest.mark.parametrize("bad", _BAD_INT_PARAMS)
def test_time_series_momentum_non_integer_lookback_or_skip_fails_closed(bad):
    prices = _make_prices(n_days=60)
    sig = baselines.time_series_momentum_signals(prices, lookback=bad, skip=1)
    assert (sig.values == 0).all()
    sig2 = baselines.time_series_momentum_signals(prices, lookback=20, skip=bad)
    assert (sig2.values == 0).all()


@pytest.mark.parametrize("bad", [-1.0, float("nan"), float("inf"), True, "2"])
def test_time_series_momentum_bad_max_position_size_fails_closed(bad):
    prices = _make_prices(n_days=60)
    sig = baselines.time_series_momentum_signals(prices, lookback=20, skip=1, max_position_size=bad)
    assert (sig.values == 0).all()


@pytest.mark.parametrize("bad", _BAD_INT_PARAMS)
def test_vol_scaled_tsmom_non_integer_window_fails_closed(bad):
    prices = _make_prices(n_days=60)
    sig = baselines.vol_scaled_tsmom_signals(prices, lookback=bad, skip=1)
    assert (sig.values == 0).all()
    sig2 = baselines.vol_scaled_tsmom_signals(prices, lookback=20, skip=bad)
    assert (sig2.values == 0).all()
    sig3 = baselines.vol_scaled_tsmom_signals(prices, lookback=20, skip=1, vol_window=bad)
    assert (sig3.values == 0).all()


@pytest.mark.parametrize("bad", [-1.0, float("nan"), float("inf"), True, "2"])
def test_vol_scaled_tsmom_bad_max_position_size_fails_closed(bad):
    prices = _make_prices(n_days=60)
    sig = baselines.vol_scaled_tsmom_signals(prices, lookback=20, skip=1, max_position_size=bad)
    assert (sig.values == 0).all()


def test_vol_scaled_tsmom_valid_numpy_float_cap_still_runs():
    prices = _make_prices(n_days=60)
    sig = baselines.vol_scaled_tsmom_signals(
        prices, lookback=20, skip=1, max_position_size=np.float64(1.5)
    )
    assert sig.shape == prices.shape
    assert sig.to_numpy().max() <= 1.5 + 1e-12


@pytest.mark.parametrize("bad", _BAD_INT_PARAMS)
def test_carry_non_integer_lookback_fails_closed(bad):
    prices = _make_prices(n_days=60)
    sig = baselines.carry_signals(prices, lookback=bad)
    assert (sig.values == 0).all()
