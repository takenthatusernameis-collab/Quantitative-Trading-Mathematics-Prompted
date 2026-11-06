"""Vectorized backtesting engine for QTR.

The engine converts a panel of prices and a panel of position targets into a
net return series, an equity curve, a trade log and a metrics dictionary.

Timing / causality: the engine applies ``signals.shift(1)``, so a position
established at the close of bar ``t`` earns the return from ``t`` to ``t+1``.
Bar 0 therefore earns no return (there is no prior position), which is the
look-ahead safety invariant pinned by ``tests/test_backtest_engine.py``.

Metrics are computed by ``VectorizedBacktester._calculate_metrics`` and are
kept in exact agreement with ``qtr.validation.statistics.validate_strategy``
for every shared metric (total return, annualized return, annualized
volatility, Sharpe, max drawdown, profit factor).  The convention is the
population standard deviation (``ddof=0``) for Sharpe and the sample standard
deviation (``ddof=1``, pandas default) for volatility, matching the committed
record.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd

from qtr.data import non_positive_prices


class AssetClass(Enum):
    EQUITY = "equity"
    FUTURE = "future"
    CRYPTO = "crypto"


@dataclass
class CostModel:
    """Transaction cost parameters.

    Equity costs are quoted in basis points of the notional weight changed:
    ``cost_fraction_of_capital = weight_delta * cost_bps / 1e4``.  This is
    price-invariant (the original ``weight_delta * price * bps`` bug inflated
    costs by roughly the instrument's price).
    Future costs are quoted per contract (commission plus tick spread /
    slippage valued at the contract tick value).  Crypto costs are quoted in
    basis points of the notional weight changed.
    """

    equity_commission_bps: float = 2.0
    equity_spread_bps: float = 0.0
    equity_impact_bps_per_pct_adv: float = 0.0
    future_commission_per_contract: float = 0.0
    future_contract_multiplier: float = 1.0
    future_tick_value: float = 12.50
    future_spread_ticks: float = 0.25
    future_slippage_ticks: float = 0.50
    crypto_fee_bps: float = 5.0
    crypto_spread_bps: float = 2.0
    crypto_slippage_bps_per_pct_daily_vol: float = 0.0
    futures_specs: dict[str, dict[str, float]] = field(default_factory=dict)

    # ----------------------------------------------------------- equity costs
    def equity_cost_bps(
        self, spread_bps: float | None = None, adv_pct: float | None = None
    ) -> float:
        """Equity cost in basis points of the weight changed.

        ``spread_bps`` defaults to the instance spread; ``adv_pct`` defaults to
        zero (no market impact).  Any invalid (non-finite or negative) input
        fails closed to ``0.0``.
        """
        commission = self.equity_commission_bps
        spread = self.equity_spread_bps if spread_bps is None else float(spread_bps)
        adv_pct = 0.0 if adv_pct is None else float(adv_pct)
        impact = self.equity_impact_bps_per_pct_adv * adv_pct
        valid = (
            math.isfinite(commission)
            and math.isfinite(spread)
            and spread >= 0.0
            and math.isfinite(adv_pct)
            and adv_pct >= 0.0
        )
        if not valid:
            return 0.0
        return commission + spread + impact

    # ---------------------------------------------------------- future costs
    def future_cost_per_contract(self, symbol: str | None = None) -> float:
        """Per-contract dollar cost: commission + (spread + slippage) * tick."""
        if symbol is not None and symbol in self.futures_specs:
            specs = self.futures_specs[symbol]
        else:
            specs = {}
        commission = float(specs.get("commission", self.future_commission_per_contract))
        tick_value = float(specs.get("tick_value", self.future_tick_value))
        spread_ticks = float(specs.get("spread_ticks", self.future_spread_ticks))
        slippage_ticks = float(specs.get("slippage_ticks", self.future_slippage_ticks))
        valid = (
            math.isfinite(commission)
            and commission >= 0.0
            and math.isfinite(tick_value)
            and math.isfinite(spread_ticks)
            and math.isfinite(slippage_ticks)
        )
        if not valid:
            return 0.0
        return commission + (spread_ticks + slippage_ticks) * tick_value

    def get_future_contract_multiplier(self, symbol: str | None = None) -> float:
        """Contract multiplier for a symbol, falling back to the default.

        Non-finite or negative multipliers fail closed to ``0.0`` (zero
        contract count, i.e. the symbol cannot be traded).  Zero is a real
        boundary and is returned as-is.
        """
        if (
            symbol is not None
            and symbol in self.futures_specs
            and "multiplier" in self.futures_specs[symbol]
        ):
            raw = float(self.futures_specs[symbol]["multiplier"])
        else:
            raw = float(self.future_contract_multiplier)
        if math.isfinite(raw) and raw >= 0.0:
            return raw
        return 0.0

    # ----------------------------------------------------------- crypto costs
    def crypto_cost_bps(self, daily_vol_pct: float | pd.Series | None = None) -> float | pd.Series:
        """Crypto cost in basis points of the weight changed.

        ``fee + spread + slippage * daily_vol_pct``.  A scalar input that is
        non-finite or negative fails closed to ``0.0``.  A Series input is
        processed element-wise: negative rows zero the slippage term (fee and
        spread still apply); a non-finite fee or spread fails closed to
        ``0.0``.
        """
        fee = self.crypto_fee_bps
        spread = self.crypto_spread_bps
        slippage = self.crypto_slippage_bps_per_pct_daily_vol
        if not (math.isfinite(fee) and math.isfinite(spread)):
            return 0.0
        if daily_vol_pct is None:
            vol = 0.0
        else:
            vol = daily_vol_pct
        if isinstance(vol, pd.Series):
            out = fee + spread + slippage * vol.clip(lower=0.0)
            return out
        vol = float(vol)
        if not math.isfinite(vol) or vol < 0.0:
            return 0.0
        return fee + spread + slippage * vol


@dataclass
class BacktestConfig:
    initial_capital: float = 1_000_000.0
    cost_model: CostModel = field(default_factory=CostModel)
    asset_class: AssetClass = AssetClass.EQUITY
    max_position_size: float = 1.0
    max_leverage: float = 1.0
    allow_short: bool = False


@dataclass
class BacktestResult:
    config: BacktestConfig
    equity_curve: pd.Series
    returns: pd.Series
    positions: pd.DataFrame
    trades: pd.DataFrame
    metrics: dict[str, float]


class VectorizedBacktester:
    def __init__(self, config: BacktestConfig):
        self.config = config

    # ------------------------------------------------------------------ costs
    def _total_costs(self, costs: Any) -> pd.Series:
        """Sum per-symbol costs across symbols; empty input -> zero series."""
        if not hasattr(costs, "columns") or len(getattr(costs, "columns", [])) == 0:
            index = getattr(costs, "index", None)
            if index is None:
                return pd.Series(dtype=float)
            return pd.Series(0.0, index=index)
        return costs.sum(axis=1)

    # --------------------------------------------------------------- drawdown
    def _max_dd_duration(self, dd: pd.Series) -> int:
        """Longest consecutive streak of strictly negative drawdown."""
        if len(dd) == 0:
            return 0
        in_dd = dd < 0
        if not bool(in_dd.any()):
            return 0
        groups = (in_dd != in_dd.shift()).cumsum()
        return int(in_dd.groupby(groups).sum().max())

    # --------------------------------------------------------------- metrics
    def _calculate_metrics(
        self, returns: pd.Series | np.ndarray, equity: pd.Series | np.ndarray, trades: pd.DataFrame
    ) -> dict[str, float]:
        from qtr.validation.statistics import sharpe_ratio

        returns = np.asarray(returns, dtype=float)
        equity = np.asarray(equity, dtype=float)
        n = int(returns.shape[0])

        empty = {
            "total_return": 0.0,
            "annualized_return": 0.0,
            "annualized_volatility": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown": 0.0,
            "max_drawdown_duration": 0,
            "profit_factor": 1.0,
            "num_trades": 0,
            "avg_trade_cost": 0.0,
            "calmar": float("inf"),
        }

        if n == 0:
            return empty

        # Non-finite returns cannot be annualized or compared; fail closed to
        # the same boundary values ``validate_strategy`` reports for this
        # input class, so the cross-module agreement contract holds.
        if not np.all(np.isfinite(returns)):
            return empty

        total_return = float((1.0 + returns).prod() - 1.0)
        gross = 1.0 + total_return
        annualized_return = float(gross ** (252.0 / n) - 1.0) if gross > 0.0 else -1.0
        # Sample standard deviation (ddof=1, pandas convention) matches
        # validate_strategy's annualized volatility exactly.
        if n > 1:
            annualized_volatility = float(np.std(returns, ddof=1) * np.sqrt(252.0))
        else:
            annualized_volatility = 0.0

        sharpe = float(sharpe_ratio(returns))

        shortfall = np.minimum(0.0, returns)
        downside_dev = float(np.sqrt(np.mean(shortfall**2)))
        if np.isfinite(downside_dev) and downside_dev > 1e-15:
            sortino = float(returns.mean() / downside_dev * np.sqrt(252.0))
        else:
            sortino = 0.0

        equity_series = (1.0 + returns).cumprod()
        rolling_max = pd.Series(equity_series).expanding().max().to_numpy()
        safe_max = np.where(rolling_max > 0.0, rolling_max, 1.0)
        drawdown = (equity_series - rolling_max) / safe_max
        max_drawdown = float(drawdown.min()) if drawdown.size > 0 else 0.0
        max_drawdown_duration = self._max_dd_duration(pd.Series(drawdown))

        gross_profit = float(returns[returns > 0].sum())
        gross_loss = float(abs(returns[returns < 0].sum()))
        profit_factor = gross_profit / gross_loss if gross_loss > 0.0 else float("inf")

        n_trades = int(len(trades))
        if n_trades > 0 and "cost" in trades.columns:
            avg_trade_cost = float(trades["cost"].mean())
        else:
            avg_trade_cost = 0.0

        abs_dd = abs(max_drawdown)
        calmar = float(annualized_return / abs_dd) if abs_dd > 1e-15 else float("inf")

        return {
            "total_return": total_return,
            "annualized_return": annualized_return,
            "annualized_volatility": annualized_volatility,
            "sharpe": sharpe,
            "sortino": sortino,
            "max_drawdown": max_drawdown,
            "max_drawdown_duration": float(max_drawdown_duration),
            "profit_factor": profit_factor,
            "num_trades": float(n_trades),
            "avg_trade_cost": avg_trade_cost,
            "calmar": calmar,
        }


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------
def run_backtest(
    prices: pd.DataFrame,
    signals: pd.DataFrame,
    config: BacktestConfig,
    volumes: pd.DataFrame | None = None,
    adv: pd.Series | None = None,
    screen_non_positive_prices: bool = True,
) -> BacktestResult:
    cfg: BacktestConfig = config
    capital = float(cfg.initial_capital)

    if screen_non_positive_prices:
        bad = non_positive_prices(prices)
        if len(bad) > 0:
            first = bad.iloc[0]
            raise ValueError(
                f"non-positive price {first['price']!r} for {first['symbol']} "
                f"on {first['timestamp']}; a percentage return from a "
                "non-positive price base is undefined"
            )

    empty_result = BacktestResult(
        config=cfg,
        equity_curve=pd.Series(dtype=float),
        returns=pd.Series(dtype=float),
        positions=pd.DataFrame(),
        trades=pd.DataFrame(
            columns=["timestamp", "symbol", "side", "weight_change", "price", "cost"]
        ),
        metrics={
            "total_return": 0.0,
            "annualized_return": 0.0,
            "annualized_volatility": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown": 0.0,
            "max_drawdown_duration": 0.0,
            "profit_factor": 1.0,
            "num_trades": 0.0,
            "avg_trade_cost": 0.0,
            "calmar": float("inf"),
        },
    )

    if (
        prices is None
        or len(prices) == 0
        or len(prices.columns) == 0
        or signals is None
        or len(signals) == 0
    ):
        return empty_result

    # Align signals to the price panel (common index / columns), forward-fill
    # targets so a position holds until the next explicit target, then fill any
    # remaining NaN (e.g. a brand-new column) with zero exposure.
    index = prices.index
    columns = list(prices.columns)
    sig = signals.reindex(index=index, columns=columns)
    positions = sig.ffill().fillna(0.0).astype(float)

    # Per-symbol price returns; bar 0 has no prior return and is filled with 0.
    asset_ret = prices[columns].astype(float).pct_change().fillna(0.0)

    # Position-size cap, then short-sale clipping.
    max_pos = float(cfg.max_position_size)
    positions = positions.clip(lower=-max_pos, upper=max_pos)
    if not bool(cfg.allow_short):
        positions = positions.clip(lower=0.0)

    # Futures with a degenerate multiplier cannot be traded: fail closed by
    # removing exposure for that symbol.
    if cfg.asset_class == AssetClass.FUTURE:
        cost_model: CostModel = cfg.cost_model
        for sym in columns:
            multiplier = cost_model.get_future_contract_multiplier(sym)
            if not (math.isfinite(multiplier) and multiplier > 0.0):
                positions[sym] = 0.0

    # Gross-leverage normalization: scale every position down when gross
    # exposure exceeds max_leverage.
    gross = positions.abs().sum(axis=1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        scale = np.where(gross > float(cfg.max_leverage), float(cfg.max_leverage) / gross, 1.0)
    scale = np.where(np.isfinite(scale) & (gross > 0.0), scale, 1.0)
    positions = positions.multiply(scale, axis=0)

    # Position changes drive trades and costs; the initial exposure is a change
    # from a zero prior position.
    prior = positions.shift(1).fillna(0.0)
    position_change = positions - prior

    # Per-symbol cost rate (fraction of notional weight changed).
    cost_model: CostModel = cfg.cost_model
    asset_class = cfg.asset_class
    rates: pd.Series | None = None
    impact_cost: pd.DataFrame | None = None
    if asset_class == AssetClass.EQUITY:
        base_rate = cost_model.equity_cost_bps() / 10_000.0
        rates = pd.Series(base_rate, index=columns)
        impact_cost = pd.DataFrame(0.0, index=index, columns=columns)
        if cost_model.equity_impact_bps_per_pct_adv and adv is not None:
            for sym in columns:
                adv_sym = adv.get(sym) if hasattr(adv, "get") else None
                if adv_sym is None or not math.isfinite(adv_sym) or adv_sym <= 0.0:
                    continue
                price_sym = prices[sym].astype(float)
                participation = (
                    position_change[sym].abs() * capital / (price_sym * float(adv_sym)) * 100.0
                )
                impact_cost[sym] = position_change[sym].abs() * (
                    cost_model.equity_impact_bps_per_pct_adv * participation / 10_000.0
                )
    elif asset_class == AssetClass.CRYPTO:
        rate = cost_model.crypto_cost_bps() / 10_000.0
        rates = pd.Series(rate, index=columns)

    costs = pd.DataFrame(0.0, index=index, columns=columns)
    if rates is not None:
        costs = position_change.abs().multiply(rates, axis=1)
        if impact_cost is not None:
            costs = costs + impact_cost
    elif asset_class == AssetClass.FUTURE:
        for sym in columns:
            multiplier = cost_model.get_future_contract_multiplier(sym)
            if not (math.isfinite(multiplier) and multiplier > 0.0):
                continue
            per_contract = cost_model.future_cost_per_contract(sym)
            price_sym = prices[sym].astype(float)
            contracts = position_change[sym].abs() * capital / (price_sym * multiplier)
            costs[sym] = contracts * per_contract / capital
    # Unknown asset class: zero costs (costs stays zero).

    # Bar t earns the position from bar t-1, minus the cost charged at bar t.
    portfolio_ret = (prior * asset_ret).sum(axis=1) - costs.sum(axis=1)
    portfolio_ret = portfolio_ret.fillna(0.0).astype(float)

    equity_curve = (1.0 + portfolio_ret).cumprod() * capital

    # Trade log: one row per nonzero position change.
    trade_rows = []
    change_mask = position_change.abs() > 0
    for sym in columns:
        sym_change = position_change.loc[change_mask[sym], sym]
        if len(sym_change) == 0:
            continue
        for ts, wc in sym_change.items():
            side = "buy" if wc > 0 else "sell"
            price = float(prices.loc[ts, sym])
            cost = float(costs.loc[ts, sym])
            trade_rows.append(
                {
                    "timestamp": ts,
                    "symbol": sym,
                    "side": side,
                    "weight_change": float(wc),
                    "price": price,
                    "cost": cost,
                }
            )
    trades = pd.DataFrame(
        trade_rows,
        columns=["timestamp", "symbol", "side", "weight_change", "price", "cost"],
    )

    backtester = VectorizedBacktester(cfg)
    metrics = backtester._calculate_metrics(portfolio_ret, equity_curve, trades)

    return BacktestResult(
        config=cfg,
        equity_curve=equity_curve,
        returns=portfolio_ret,
        positions=positions,
        trades=trades,
        metrics=metrics,
    )


__all__ = [
    "AssetClass",
    "BacktestConfig",
    "BacktestResult",
    "CostModel",
    "VectorizedBacktester",
    "run_backtest",
]
