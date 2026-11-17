from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from qtr.backtest.engine import BacktestConfig, CostModel, run_backtest
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


_BAD_TARGET_VOL = [-0.15, float("nan"), float("inf"), float("-inf"), True, "0.15"]


@pytest.mark.parametrize("bad", _BAD_TARGET_VOL)
def test_vol_scale_bad_target_vol_fails_closed(bad):
    """A non-finite or negative ``target_vol`` is not a risk target.

    ``_vol_scale`` divides by ``vol`` with ``target_vol`` as the numerator,
    so a negative ``target_vol`` makes the multiplier negative and
    **inverts the sign of every position** (``_vol_scale(0.15, -0.15) ==
    -1.0``), turning a trend-following book into a mean-reversion book;
    a non-finite one makes the multiplier ``inf`` (the ``min(inf, 2.0)``
    cap does not fire). Both fail closed to ``1.0`` -- the no-scaling
    boundary -- so a bad target can only leave a position at its raw
    direction weight, never invert or blow it up.
    """
    assert baselines._vol_scale(0.15, bad) == 1.0


def test_vol_scale_zero_target_vol_returns_zero():
    """``target_vol == 0.0`` is a real, measured boundary.

    A zero target means no risk to take, so every position scales to
    zero -- the no-exposure answer, consistent with the way
    ``max_position_size == 0.0`` and ``adv == 0.0`` are handled elsewhere
    in this module. It is finite and non-negative, so it passes the guard
    and is answered as ``0.0`` rather than ``1.0``.
    """
    assert baselines._vol_scale(0.15, 0.0) == 0.0
    assert baselines._vol_scale(2.0, 0.0) == 0.0


@pytest.mark.parametrize("bad", _BAD_TARGET_VOL)
def test_time_series_momentum_bad_target_vol_fails_closed(bad):
    prices = _make_prices(n_days=60)
    sig = baselines.time_series_momentum_signals(prices, lookback=20, skip=1, target_vol=bad)
    assert (sig.values == 0).all()


@pytest.mark.parametrize("bad", _BAD_TARGET_VOL)
def test_vol_scaled_tsmom_bad_target_vol_fails_closed(bad):
    prices = _make_prices(n_days=60)
    sig = baselines.vol_scaled_tsmom_signals(prices, lookback=20, skip=1, target_vol=bad)
    assert (sig.values == 0).all()


def test_time_series_momentum_negative_target_vol_does_not_invert_signal():
    """The defect this guard closes: a negative ``target_vol`` used to
    produce the exact negation of the intended trend-following book
    (measured correlation -1.0 between the ``+0.15`` and ``-0.15`` books
    over a 300-bar panel). With the guard it returns the all-zero frame,
    so a sign error can only ever *remove* exposure, never manufacture a
    mean-reversion book out of a misconfiguration.
    """
    prices = _make_prices(n_days=300)
    sig_ok = baselines.time_series_momentum_signals(prices, target_vol=0.15, long_only=False)
    sig_neg = baselines.time_series_momentum_signals(prices, target_vol=-0.15, long_only=False)
    assert (sig_neg.values == 0).all()
    assert not (sig_ok.values == 0).all()


def test_time_series_momentum_valid_target_vol_unchanged():
    """For every finite, non-negative ``target_vol`` the arithmetic is
    bit-identical to before: the guard only short-circuits the degenerate
    cases. Both TSMOM variants are deterministic on the same panel."""
    prices = _make_prices(n_days=300)
    a = baselines.time_series_momentum_signals(prices, target_vol=0.15, long_only=False)
    b = baselines.time_series_momentum_signals(prices, target_vol=0.15, long_only=False)
    assert np.allclose(a.values, b.values)
    c = baselines.vol_scaled_tsmom_signals(prices, target_vol=0.15, long_only=False)
    d = baselines.vol_scaled_tsmom_signals(prices, target_vol=0.15, long_only=False)
    assert np.allclose(c.values, d.values)


def test_vol_scaled_tsmom_valid_numpy_float_target_vol_still_runs():
    prices = _make_prices(n_days=60)
    sig = baselines.vol_scaled_tsmom_signals(
        prices, lookback=20, skip=1, target_vol=np.float64(0.15)
    )
    assert sig.shape == prices.shape


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


_DUPLICATE_COLUMN_CASES = [
    ("buy_and_hold_signals", {}),
    ("moving_average_crossover_signals", {"fast_window": 5, "slow_window": 10}),
    ("ewma_crossover_signals", {"fast_span": 5, "slow_span": 10}),
    ("momentum_signals", {"lookback": 60, "skip": 5, "n_top": 1}),
    ("mean_reversion_signals", {"window": 20}),
    ("time_series_momentum_signals", {"lookback": 60, "skip": 5}),
    ("vol_scaled_tsmom_signals", {"lookback": 60, "skip": 5, "vol_window": 30}),
    ("carry_signals", {"lookback": 60}),
]


def _duplicate_price_panel() -> pd.DataFrame:
    index = pd.date_range("2020-01-01", periods=300, freq="D")
    rng = np.random.default_rng(20261117)
    first_a = 100.0 + np.cumsum(rng.normal(0.0, 0.02, len(index)))
    second_a = 200.0 - first_a
    other = 100.0 + np.cumsum(rng.normal(0.0, 0.02, len(index)))
    return pd.DataFrame(
        np.column_stack([first_a, second_a, other]),
        index=index,
        columns=["A", "A", "B"],
    )


@pytest.mark.parametrize(("name", "kwargs"), _DUPLICATE_COLUMN_CASES)
def test_duplicate_price_columns_are_canonized_keep_first(name, kwargs):
    prices = _duplicate_price_panel()
    deduplicated = prices.iloc[:, [0, 2]].copy()
    strategy = getattr(baselines, name)

    signals = strategy(prices, **kwargs)
    expected = strategy(deduplicated, **kwargs)

    assert signals.columns.tolist() == ["A", "B"]
    pd.testing.assert_frame_equal(signals, expected)


def test_unique_price_columns_remain_unchanged_by_duplicate_guard():
    prices = _make_prices(n_days=300, n_syms=3)
    duplicated = _duplicate_price_panel()

    assert baselines._drop_duplicate_price_columns(prices) is prices
    canonical = baselines._drop_duplicate_price_columns(duplicated)
    pd.testing.assert_frame_equal(canonical, duplicated.iloc[:, [0, 2]].copy())


# ============================================================
# End-to-end duplicate-column contract: run_strategy -> run_backtest
# ============================================================
def _make_backtest_config() -> BacktestConfig:
    """Zero-cost, long-only config for deterministic E2E tests."""
    return BacktestConfig(
        initial_capital=1_000_000.0,
        cost_model=CostModel(
            equity_commission_bps=0.0,
            equity_spread_bps=0.0,
            equity_impact_bps_per_pct_adv=0.0,
        ),
        max_position_size=1.0,
        max_leverage=1.0,
        allow_short=False,
    )


def _duplicate_price_panel() -> pd.DataFrame:
    index = pd.date_range("2020-01-01", periods=300, freq="D")
    rng = np.random.default_rng(20261117)
    first_a = 100.0 + np.cumsum(rng.normal(0.0, 0.02, len(index)))
    second_a = 200.0 - first_a  # Anti-correlated duplicate
    other = 100.0 + np.cumsum(rng.normal(0.0, 0.02, len(index)))
    return pd.DataFrame(
        np.column_stack([first_a, second_a, other]),
        index=index,
        columns=["A", "A", "B"],
    )


def _deduplicated_price_panel() -> pd.DataFrame:
    """Same as _duplicate_price_panel but with keep-first canonical columns."""
    index = pd.date_range("2020-01-01", periods=300, freq="D")
    rng = np.random.default_rng(20261117)
    first_a = 100.0 + np.cumsum(rng.normal(0.0, 0.02, len(index)))
    other = 100.0 + np.cumsum(rng.normal(0.0, 0.02, len(index)))
    return pd.DataFrame(
        np.column_stack([first_a, other]),
        index=index,
        columns=["A", "B"],
    )


def test_mean_reversion_e2e_duplicate_columns_keep_first():
    """E2E: mean_reversion strategy + backtest on duplicated panel matches deduplicated."""
    prices_dup = _duplicate_price_panel()
    prices_dedup = _deduplicated_price_panel()
    cfg = _make_backtest_config()

    # Run strategy on both panels
    sig_dup = baselines.run_strategy(prices_dup, "mean_reversion", window=20, num_std=2.0, long_only=True)
    sig_dedup = baselines.run_strategy(prices_dedup, "mean_reversion", window=20, num_std=2.0, long_only=True)

    # Signals should have canonical columns and match
    assert sig_dup.columns.tolist() == ["A", "B"]
    pd.testing.assert_frame_equal(sig_dup, sig_dedup)

    # Run backtest on both signal panels
    res_dup = run_backtest(prices=prices_dup, signals=sig_dup, config=cfg)
    res_dedup = run_backtest(prices=prices_dedup, signals=sig_dedup, config=cfg)

    # Results must be identical (keep-first behavior)
    pd.testing.assert_frame_equal(res_dup.positions, res_dedup.positions)
    pd.testing.assert_series_equal(res_dup.returns, res_dedup.returns)
    pd.testing.assert_series_equal(res_dup.equity_curve, res_dedup.equity_curve)

    # All outputs must be finite
    assert np.all(np.isfinite(res_dup.returns))
    assert np.all(np.isfinite(res_dup.equity_curve))
    assert np.all(np.isfinite(res_dup.positions.values))
    assert np.all(np.isfinite(res_dedup.returns))
    assert np.all(np.isfinite(res_dedup.equity_curve))
    assert np.all(np.isfinite(res_dedup.positions.values))

    # Metrics must be identical and finite
    for k in res_dup.metrics:
        assert res_dup.metrics[k] == res_dedup.metrics[k]
        assert np.isfinite(res_dup.metrics[k]) or np.isinf(res_dup.metrics[k])


def test_time_series_momentum_e2e_duplicate_columns_keep_first():
    """E2E: time_series_momentum strategy + backtest on duplicated panel matches deduplicated."""
    prices_dup = _duplicate_price_panel()
    prices_dedup = _deduplicated_price_panel()
    cfg = _make_backtest_config()

    # Run strategy on both panels
    sig_dup = baselines.run_strategy(
        prices_dup,
        "time_series_momentum",
        lookback=60,
        skip=5,
        long_only=True,
        volatility_scale=True,
        target_vol=0.15,
        max_position_size=1.0,
    )
    sig_dedup = baselines.run_strategy(
        prices_dedup,
        "time_series_momentum",
        lookback=60,
        skip=5,
        long_only=True,
        volatility_scale=True,
        target_vol=0.15,
        max_position_size=1.0,
    )

    # Signals should have canonical columns and match
    assert sig_dup.columns.tolist() == ["A", "B"]
    pd.testing.assert_frame_equal(sig_dup, sig_dedup)

    # Run backtest on both signal panels
    res_dup = run_backtest(prices=prices_dup, signals=sig_dup, config=cfg)
    res_dedup = run_backtest(prices=prices_dedup, signals=sig_dedup, config=cfg)

    # Results must be identical (keep-first behavior)
    pd.testing.assert_frame_equal(res_dup.positions, res_dedup.positions)
    pd.testing.assert_series_equal(res_dup.returns, res_dedup.returns)
    pd.testing.assert_series_equal(res_dup.equity_curve, res_dedup.equity_curve)

    # All outputs must be finite
    assert np.all(np.isfinite(res_dup.returns))
    assert np.all(np.isfinite(res_dup.equity_curve))
    assert np.all(np.isfinite(res_dup.positions.values))
    assert np.all(np.isfinite(res_dedup.returns))
    assert np.all(np.isfinite(res_dedup.equity_curve))
    assert np.all(np.isfinite(res_dedup.positions.values))

    # Metrics must be identical and finite
    for k in res_dup.metrics:
        assert res_dup.metrics[k] == res_dedup.metrics[k]
        assert np.isfinite(res_dup.metrics[k]) or np.isinf(res_dup.metrics[k])
