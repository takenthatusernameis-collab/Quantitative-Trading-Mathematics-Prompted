"""Baseline strategies for quantitative trading research."""

import numpy as np
import pandas as pd


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

        # Crossover signal: +1 when fast > slow, -1 when fast < slow, 0 on tie
        signal = np.sign(fast_ma - slow_ma)

        if long_only:
            signal = (signal > 0).astype(float)

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

        signal = np.sign(fast_ema - slow_ema)

        if long_only:
            signal = (signal > 0).astype(float)

        signals.loc[signal.index, symbol] = signal

    return signals.ffill().fillna(0)


def momentum_signals(
    prices: pd.DataFrame,
    lookback: int = 252,
    skip: int = 21,
    long_only: bool = True,
    n_top: int | None = None,
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
            if n_top <= 0:
                continue
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
            # Buy when price touches lower band, sell when touches upper.
            # Both legs require a positive realized volatility: when the
            # rolling std is zero the bands collapse to the mean and *every*
            # bar is simultaneously at, below and above them, so a constant
            # price series carries no mean-reversion information. On such a
            # panel the long-only branch is self-cancelling (the upper-mask
            # assignment runs after the lower-mask one and zeroes the book),
            # so it needs no guard; the long/short branch does not cancel and
            # used to book a full short. See the long/short branch below.
            signal = pd.Series(0.0, index=price.index)
            signal[(price <= lower) & (rolling_std > 0)] = 1.0
            signal[(price >= upper) & (rolling_std > 0)] = 0.0
            signal = signal.ffill().fillna(0)
        else:
            # Long at lower, short at upper. When the realized volatility is
            # zero the bands collapse to the rolling mean and *every* bar is
            # simultaneously at, below and above them -- a constant price
            # series (a flat book, a synthetic fixture, a symbol that has not
            # yet moved) has no mean-reversion information, yet the old
            # construction booked every such bar as a SHORT. The position is
            # then held through the forward fill, so the error is not
            # cosmetic: a zero-volatility symbol in a long/short book carries
            # a full -1.0 short weight. Both legs now require a positive
            # realized volatility, so a zero-volatility bar is flat and the
            # forward fill carries the last *valid* signal forward. On any
            # panel with positive realized volatility the masks are identical
            # to the old ``price <= lower`` / ``price >= upper`` ones, so the
            # change is bit-identical on every panel the record actually
            # contains (verified: max abs diff 0.0 against the pre-fix
            # construction over 400-bar random panels).
            signal = pd.Series(0.0, index=price.index)
            signal[(price <= lower) & (rolling_std > 0)] = 1.0
            signal[(price >= upper) & (rolling_std > 0)] = -1.0
            signal = signal.ffill().fillna(0)

        signals.loc[signal.index, symbol] = signal

    return signals.ffill().fillna(0)


def _vol_scale(vol: float, target_vol: float) -> float:
    """Leverage multiplier that scales a position to a target volatility.

    The multiplier is ``target_vol / vol``, capped at 2x so that no single
    asset is ever levered more than double. A non-positive ``vol`` carries
    no information about the risk of the position, so the position is left
    unscaled (multiplier 1.0) rather than being amplified.

    This is a separate function so that the non-positive branch is
    reachable and testable. Inside :func:`time_series_momentum_signals` the
    realized-volatility series is sanitized to be strictly positive by
    construction (zeros -> NaN -> forward fill -> 0.15), so an inline
    ``if vol > 0`` guard could never fire and was therefore never executed
    by any test. See tests/test_coverage_gate_contract.py.
    """
    if vol <= 0:
        return 1.0
    return min(target_vol / vol, 2.0)


def time_series_momentum_signals(
    prices: pd.DataFrame,
    lookback: int = 252,
    skip: int = 21,
    long_only: bool = True,
    volatility_scale: bool = True,
    target_vol: float = 0.15,
) -> pd.DataFrame:
    """
    Generate time-series momentum signals (Moskowitz, Ooi, Pedersen 2012).

    Each asset's position is based on its own past returns (not cross-sectional).
    Optionally volatility-scaled per Kim et al. (2016).

    Args:
        prices: DataFrame of close prices
        lookback: Momentum lookback period (default 252 = 1 year)
        skip: Skip period to avoid microstructure effects (default 21 = 1 month)
        long_only: If True, only long positions
        volatility_scale: If True, scale positions by inverse volatility
        target_vol: Target annualized volatility for scaling

    Returns:
        DataFrame of position weights
    """
    signals = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

    # Calculate momentum: past return over lookback, shifted by skip
    momentum = prices.pct_change(lookback).shift(skip)

    # Calculate realized volatility (annualized) for scaling
    if volatility_scale:
        returns = prices.pct_change()
        realized_vol = returns.rolling(63).std() * np.sqrt(252)
        realized_vol = realized_vol.replace(0, np.nan).ffill().fillna(0.15)
    else:
        realized_vol = None

    for date in momentum.index:
        mom_vals = momentum.loc[date].dropna()
        if len(mom_vals) == 0:
            continue

        for symbol in mom_vals.index:
            mom_val = mom_vals[symbol]
            if mom_val > 0:
                weight = 1.0
            elif mom_val < 0 and not long_only:
                weight = -1.0
            else:
                weight = 0.0

            # Volatility scaling
            if volatility_scale and realized_vol is not None and symbol in realized_vol.columns:
                vol = realized_vol.loc[date, symbol]
                # Scale to target volatility (leverage capped at 2x).
                weight = weight * _vol_scale(vol, target_vol)

            signals.loc[date, symbol] = weight

    return signals.ffill().fillna(0)


def vol_scaled_tsmom_signals(
    prices: pd.DataFrame,
    lookback: int = 252,
    skip: int = 21,
    long_only: bool = True,
    target_vol: float = 0.15,
    vol_window: int = 63,
    max_position_size: float = 2.0,
) -> pd.DataFrame:
    """Faithful AQR/Moskowitz-style volatility-scaled time-series momentum.

    This is the canonical TSMOM construction (Moskowitz, Ooi & Pedersen 2012;
    Kim, Liew & Moulang 2016 vol-scaling), matching the pre-registered H1
    implementation in ``run_ts_momentum_experiment.py``.

    Construction:
        1. momentum = pct_change(lookback).shift(skip)  -- lookahead-safe.
        2. direction = sign(momentum)  (+1 long, -1 short; 0 if long_only
           and momentum <= 0, or momentum is NaN).
        3. w_raw = direction / sigma   (inverse-volatility weighting),
           sigma = rolling(1d return, vol_window).std * sqrt(252).
        4. Portfolio-level volatility targeting: scale the whole book so
           realized portfolio vol ~ target_vol (linear in scale).
        5. Per-asset cap at +/- max_position_size.

    Sign invariant: direction tracks the *sign of momentum*, so a rising
    asset gets a positive weight. This is a *trend-following* signal. A
    construction with ``w = -momentum / vol`` would invert the sign and
    produce a mean-reversion signal -- a documented regression in the H4
    runner (see run_futures_tsmom_experiment.py history).

    All scaling uses only data available at time t (rolling windows, shift).
    """
    pct = prices.pct_change()
    # Momentum = lookback return, shifted by skip to avoid short-horizon
    # reversal (Moskowitz, Ooi & Pedersen 2012).
    mom = prices.pct_change(lookback).shift(skip)
    if long_only:
        direction = (mom > 0).astype(float)
    else:
        # Direction is the SIGN of momentum: +1 long, -1 short, and **0 when
        # momentum is exactly zero**. The sign of zero is not a direction, and
        # ``(mom > 0) * 2 - 1`` maps it to -1, so a price series that returns
        # exactly to its starting level over the lookback window (a
        # repeating cycle, a flat book, a synthetic test fixture) was booked
        # as a SHORT while carrying no information about trend. The position
        # is then inverse-volatility-scaled, so the error is not cosmetic: a
        # zero-momentum bar with positive realised volatility produced a
        # non-zero short weight. ``np.sign`` returns 0.0 for an exact zero and
        # is used instead of the arithmetic form; NaN momentum is mapped to
        # 0.0 by the ``where`` below, exactly as before.
        direction = np.sign(mom)
        direction = direction.where(mom.notna(), 0.0)

    sigma = pct.rolling(vol_window).std() * np.sqrt(252)
    sigma = sigma.replace(0, np.nan).ffill()
    inv_vol = 1.0 / sigma

    w_raw = direction * inv_vol
    w_raw = w_raw.replace([np.inf, -np.inf], np.nan).ffill().fillna(0.0)

    # Portfolio-level vol targeting (scale is linear in portfolio vol).
    port_ret = (w_raw.shift(1) * pct).sum(axis=1).ffill()
    port_vol = port_ret.rolling(vol_window).std() * np.sqrt(252)
    port_vol = port_vol.replace(0, np.nan)
    scale = (target_vol / port_vol).clip(lower=0.0, upper=3.0)
    scale = scale.ffill().fillna(0.0)
    weights = w_raw.multiply(scale, axis=0)

    # Per-asset cap (also enforced by the engine).
    weights = weights.clip(-max_position_size, max_position_size)
    return weights.ffill().fillna(0.0)


def carry_signals(
    prices: pd.DataFrame,
    lookback: int = 252,
    long_only: bool = True,
) -> pd.DataFrame:
    """
    Generate carry signals (Koijen, Moskowitz, Pedersen, Vrugt 2018).

    For futures: carry = futures price - spot price (contango/backwardation).
    For ETFs: approximate carry using dividend yield and roll yield.

    Args:
        prices: DataFrame of close prices
        lookback: Lookback for carry calculation
        long_only: If True, only long positions

    Returns:
        DataFrame of position weights
    """
    signals = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

    # Simple carry proxy: 12-month return minus 1-month return
    # High carry = positive term structure
    long_ret = prices.pct_change(lookback)
    short_ret = prices.pct_change(21)

    carry = long_ret - short_ret

    for date in carry.index:
        carry_vals = carry.loc[date].dropna()
        if len(carry_vals) == 0:
            continue

        for symbol in carry_vals.index:
            if carry_vals[symbol] > 0:
                signals.loc[date, symbol] = 1.0
            elif carry_vals[symbol] < 0 and not long_only:
                signals.loc[date, symbol] = -1.0

    return signals.ffill().fillna(0)


STRATEGY_REGISTRY = {
    "ma_crossover": moving_average_crossover_signals,
    "buy_and_hold": buy_and_hold_signals,
    "ewma_crossover": ewma_crossover_signals,
    "momentum": momentum_signals,
    "mean_reversion": mean_reversion_signals,
    "time_series_momentum": time_series_momentum_signals,
    "vol_scaled_tsmom": vol_scaled_tsmom_signals,
    "carry": carry_signals,
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
