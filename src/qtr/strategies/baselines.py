"""Baseline strategies for quantitative trading research."""

from typing import Optional, Dict, Any
import numpy as np
import pandas as pd
from loguru import logger


def moving_average_crossover_signals(
    prices: pd.DataFrame,
    fast_window: int = 20,
    slow_window: int = 50,
    long_only: bool = True,
) -> pd.DataFrame:
    """
    Generate signals from moving average crossover.

    Args:
        prices: DataFrame of close prices (datetime index, symbols as columns)
        fast_window: Fast MA window
        slow_window: Slow MA window
        long_only: If True, only long positions (0 or 1); if False, allow short (-1 to 1)

    Returns:
        DataFrame of position weights (-1 to 1 or 0 to 1)
    """
    signals = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

    for symbol in prices.columns:
        price = prices[symbol].dropna()
        if len(price) < slow_window:
            continue

        fast_ma = price.rolling(fast_window).mean()
        slow_ma = price.rolling(slow_window).mean()

        # Crossover signal
        signal = (fast_ma > slow_ma).astype(float)

        if not long_only:
            signal = signal * 2 - 1  # Convert to -1/1

        # Align back to full index
        signals.loc[signal.index, symbol] = signal

    return signals.ffill().fillna(0)


def buy_and_hold_signals(
    prices: pd.DataFrame,
    weight: float = 1.0,
) -> pd.DataFrame:
    """
    Generate buy-and-hold signals (benchmark).

    Args:
        prices: DataFrame of close prices
        weight: Position weight per symbol (default: 1.0 = fully invested)

    Returns:
        DataFrame of constant position weights
    """
    return pd.DataFrame(
        weight,
        index=prices.index,
        columns=prices.columns,
    )


def ewma_crossover_signals(
    prices: pd.DataFrame,
    fast_span: int = 20,
    slow_span: int = 50,
    long_only: bool = True,
) -> pd.DataFrame:
    """
    Generate signals from exponential moving average crossover.

    Args:
        prices: DataFrame of close prices
        fast_span: Fast EMA span
        slow_span: Slow EMA span
        long_only: If True, only long positions

    Returns:
        DataFrame of position weights
    """
    signals = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

    for symbol in prices.columns:
        price = prices[symbol].dropna()
        if len(price) < slow_span:
            continue

        fast_ema = price.ewm(span=fast_span, adjust=False).mean()
        slow_ema = price.ewm(span=slow_span, adjust=False).mean()

        signal = (fast_ema > slow_ema).astype(float)

        if not long_only:
            signal = signal * 2 - 1

        signals.loc[signal.index, symbol] = signal

    return signals.ffill().fillna(0)


def momentum_signals(
    prices: pd.DataFrame,
    lookback: int = 252,
    skip: int = 21,
    long_only: bool = True,
    n_top: Optional[int] = None,
) -> pd.DataFrame:
    """
    Generate cross-sectional momentum signals.

    Args:
        prices: DataFrame of close prices
        lookback: Momentum lookback period
        skip: Skip period to avoid microstructure effects
        long_only: If True, only long positions
        n_top: Number of top momentum assets to hold (None = all positive)

    Returns:
        DataFrame of position weights
    """
    signals = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

    # Calculate momentum
    momentum = prices.pct_change(lookback).shift(skip)

    for date in momentum.index:
        mom_vals = momentum.loc[date].dropna()
        if len(mom_vals) == 0:
            continue

        if n_top is not None:
            # Top N momentum
            top_symbols = mom_vals.nlargest(n_top).index
            weight = 1.0 / n_top if long_only else 1.0 / (2 * n_top)
            for sym in top_symbols:
                signals.loc[date, sym] = weight
            if not long_only:
                bottom_symbols = mom_vals.nsmallest(n_top).index
                for sym in bottom_symbols:
                    signals.loc[date, sym] = -weight
        else:
            # All positive momentum
            positive = mom_vals[mom_vals > 0]
            if len(positive) > 0:
                weight = 1.0 / len(positive)
                for sym in positive.index:
                    signals.loc[date, sym] = weight
            if not long_only:
                negative = mom_vals[mom_vals < 0]
                if len(negative) > 0:
                    weight = -1.0 / len(negative)
                    for sym in negative.index:
                        signals.loc[date, sym] = weight

    return signals.ffill().fillna(0)


def mean_reversion_signals(
    prices: pd.DataFrame,
    window: int = 20,
    num_std: float = 2.0,
    long_only: bool = True,
) -> pd.DataFrame:
    """
    Generate mean reversion signals (Bollinger Band style).

    Args:
        prices: DataFrame of close prices
        window: Rolling window for mean/std
        num_std: Number of standard deviations for bands
        long_only: If True, only long positions (buy at lower band)

    Returns:
        DataFrame of position weights
    """
    signals = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

    for symbol in prices.columns:
        price = prices[symbol].dropna()
        if len(price) < window:
            continue

        rolling_mean = price.rolling(window).mean()
        rolling_std = price.rolling(window).std()

        upper = rolling_mean + num_std * rolling_std
        lower = rolling_mean - num_std * rolling_std

        if long_only:
            # Buy when price touches lower band, sell when touches upper
            signal = pd.Series(0.0, index=price.index)
            signal[price <= lower] = 1.0
            signal[price >= upper] = 0.0
            signal = signal.ffill().fillna(0)
        else:
            # Long at lower, short at upper
            signal = pd.Series(0.0, index=price.index)
            signal[price <= lower] = 1.0
            signal[price >= upper] = -1.0
            signal = signal.ffill().fillna(0)

        signals.loc[signal.index, symbol] = signal

    return signals.ffill().fillna(0)


STRATEGY_REGISTRY = {
    "ma_crossover": moving_average_crossover_signals,
    "buy_and_hold": buy_and_hold_signals,
    "ewma_crossover": ewma_crossover_signals,
    "momentum": momentum_signals,
    "mean_reversion": mean_reversion_signals,
}


def get_strategy(name: str):
    """Get strategy function by name."""
    if name not in STRATEGY_REGISTRY:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGY_REGISTRY.keys())}")
    return STRATEGY_REGISTRY[name]


def run_strategy(
    prices: pd.DataFrame,
    strategy_name: str,
    **kwargs,
) -> pd.DataFrame:
    """Run a strategy by name with given parameters."""
    strategy_func = get_strategy(strategy_name)
    return strategy_func(prices, **kwargs)