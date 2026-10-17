from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from qtr.strategies import baselines


def _make_prices(
    n_days: int = 400, n_syms: int = 3, start: str = "2020-01-01", seed=42
):
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
