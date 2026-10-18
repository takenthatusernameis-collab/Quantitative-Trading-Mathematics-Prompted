"""
Vectorized backtesting engine with realistic cost modeling.

Cost Model (from PROMPT_V2.md):
- Equities: 1 bp commission + 0.5-5 bp spread + 0.1 bp market impact per 1% ADV
- Futures: $0.50/contract commission + 0.25 tick spread + 0.5 tick slippage
- Crypto: 5 bp taker fee + 2 bp spread + 1 bp slippage per 0.1% daily volume
"""

from dataclasses import dataclass, field
from enum import Enum

import numpy as np
import pandas as pd


class AssetClass(Enum):
    EQUITY = "equity"
    FUTURE = "future"
    CRYPTO = "crypto"


@dataclass
class CostModel:
    """Transaction cost model parameters."""

    # Equity costs (basis points)
    equity_commission_bps: float = 1.0
    equity_spread_bps: float = 1.0  # average, can be overridden per symbol
    equity_impact_bps_per_pct_adv: float = 0.1

    # Futures costs (per contract) - defaults for ES
    future_commission_per_contract: float = 0.50
    future_spread_ticks: float = 0.25
    future_slippage_ticks: float = 0.5
    future_tick_value: float = 12.50  # ES = $12.50 per tick
    future_contract_multiplier: float = 50.0  # ES = $50 per point

    # Per-symbol futures contract specifications (overrides defaults)
    # Dict[symbol] -> dict with keys: multiplier, tick_value, tick_size, commission, spread_ticks, slippage_ticks
    futures_specs: dict[str, dict[str, float]] = field(default_factory=dict)

    # Crypto costs (basis points)
    crypto_fee_bps: float = 5.0
    crypto_spread_bps: float = 2.0
    crypto_slippage_bps_per_pct_daily_vol: float = 1.0

    def equity_cost_bps(
        self, spread_bps: float | None = None, adv_pct: float = 0.0
    ) -> float:
        """Total equity cost in basis points."""
        spread = spread_bps if spread_bps is not None else self.equity_spread_bps
        impact = self.equity_impact_bps_per_pct_adv * adv_pct
        return self.equity_commission_bps + spread + impact

    def future_cost_per_contract(self, symbol: str | None = None) -> float:
        """Total futures cost per contract in dollars for a given symbol."""
        if symbol and symbol in self.futures_specs:
            spec = self.futures_specs[symbol]
            tick_value = spec.get("tick_value", self.future_tick_value)
            spread_ticks = spec.get("spread_ticks", self.future_spread_ticks)
            slippage_ticks = spec.get("slippage_ticks", self.future_slippage_ticks)
            commission = spec.get("commission", self.future_commission_per_contract)
        else:
            tick_value = self.future_tick_value
            spread_ticks = self.future_spread_ticks
            slippage_ticks = self.future_slippage_ticks
            commission = self.future_commission_per_contract
        tick_cost = (spread_ticks + slippage_ticks) * tick_value
        return commission + tick_cost

    def get_future_contract_multiplier(self, symbol: str | None = None) -> float:
        """Contract multiplier for a given symbol."""
        if symbol and symbol in self.futures_specs:
            return self.futures_specs[symbol].get(
                "multiplier", self.future_contract_multiplier
            )
        return self.future_contract_multiplier

    def crypto_cost_bps(self, daily_vol_pct: float = 0.0) -> float:
        """Total crypto cost in basis points."""
        slippage = self.crypto_slippage_bps_per_pct_daily_vol * daily_vol_pct
        return self.crypto_fee_bps + self.crypto_spread_bps + slippage


@dataclass
class BacktestConfig:
    """Backtest configuration."""

    initial_capital: float = 1_000_000.0
    cost_model: CostModel = field(default_factory=CostModel)
    asset_class: AssetClass = AssetClass.EQUITY
    max_position_size: float = 1.0  # fraction of capital
    max_leverage: float = 1.0
    allow_short: bool = False
    benchmark_symbol: str | None = None


@dataclass
class BacktestResult:
    """Backtest results container."""

    equity_curve: pd.Series
    returns: pd.Series
    positions: pd.DataFrame
    trades: pd.DataFrame
    metrics: dict[str, float]
    config: BacktestConfig


class VectorizedBacktester:
    """
    Vectorized backtesting engine.

    Computes portfolio equity curve, trades, and performance metrics
    from signal DataFrames (position weights or target weights over time).
    """

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.cost_model = config.cost_model

    def run(
        self,
        prices: pd.DataFrame,
        signals: pd.DataFrame,
        volumes: pd.DataFrame | None = None,
        adv: pd.Series | None = None,
    ) -> BacktestResult:
        """
        Run backtest.

        Args:
            prices: DataFrame of close prices (datetime index, symbols as columns)
            signals: DataFrame of target position weights (-1 to 1, same index/columns as prices)
            volumes: Optional volume DataFrame for market impact estimation
            adv: Optional average daily volume (shares) per symbol for impact model

        Returns:
            BacktestResult with equity curve, trades, and metrics
        """
        # Align data
        common_index = prices.index.intersection(signals.index)
        prices = prices.loc[common_index]
        signals = signals.loc[common_index]

        if volumes is not None:
            volumes = volumes.loc[common_index]
        else:
            volumes = pd.DataFrame(
                index=prices.index, columns=prices.columns, dtype=float
            )

        # Forward fill signals (hold position until change)
        signals = signals.ffill().fillna(0)

        # Enforce leverage constraint: normalize so sum of absolute weights <= max_leverage
        gross_leverage = signals.abs().sum(axis=1)
        over_leverage = gross_leverage > self.config.max_leverage
        if over_leverage.any():
            signals.loc[over_leverage] = (
                signals.loc[over_leverage].div(gross_leverage[over_leverage], axis=0)
                * self.config.max_leverage
            )

        # Enforce max position size per symbol
        signals = signals.clip(
            -self.config.max_position_size, self.config.max_position_size
        )

        # If short not allowed, clip negative positions
        if not self.config.allow_short:
            signals = signals.clip(lower=0)

        # Calculate position changes (trades)
        position_changes = signals.diff().fillna(signals.iloc[0])

        # Calculate returns
        price_returns = prices.pct_change().fillna(0)

        # Portfolio returns before costs
        portfolio_returns = (signals.shift(1) * price_returns).sum(axis=1)

        # Calculate transaction costs
        costs = self._calculate_costs(position_changes, prices, volumes, adv)

        # Net returns
        net_returns = portfolio_returns - costs

        # Equity curve
        equity = (1 + net_returns).cumprod() * self.config.initial_capital

        # Extract trades
        trades = self._extract_trades(position_changes, prices, costs)

        # Calculate metrics
        metrics = self._calculate_metrics(net_returns, equity, trades)

        return BacktestResult(
            equity_curve=equity,
            returns=net_returns,
            positions=signals,
            trades=trades,
            metrics=metrics,
            config=self.config,
        )

    def _calculate_costs(
        self,
        position_changes: pd.DataFrame,
        prices: pd.DataFrame,
        volumes: pd.DataFrame,
        adv: pd.Series | None,
    ) -> pd.Series:
        """Calculate transaction costs for each time step."""
        costs = pd.Series(0.0, index=position_changes.index)

        for symbol in position_changes.columns:
            changes = position_changes[symbol].abs()
            if changes.sum() == 0:
                continue

            price = prices[symbol]

            if self.config.asset_class == AssetClass.EQUITY:
                # Estimate ADV participation using initial capital (approximate).
                # changes is a weight delta (fraction of capital); shares_traded
                # converts it to a share count for volume-participation impact.
                if adv is not None and symbol in adv.index and adv[symbol] > 0:
                    # Position change in shares = weight_change * initial_capital / price
                    shares_traded = changes * self.config.initial_capital / price
                    adv_pct = (shares_traded / adv[symbol]).clip(
                        0, 1
                    ) * 100  # as percentage
                else:
                    adv_pct = 0.0

                # Spread estimate (could be enhanced with real spread data)
                spread_bps = self.cost_model.equity_spread_bps

                cost_bps = self.cost_model.equity_cost_bps(spread_bps, adv_pct)
                # Cost as a FRACTION of portfolio value: weight_delta * cost_bps.
                # (Previously multiplied by `price`, which injected the per-share
                # dollar price and inflated costs ~400x. See cost-model audit.)
                symbol_costs = changes * (cost_bps / 10000)

            elif self.config.asset_class == AssetClass.FUTURE:
                # Per contract cost - use per-symbol specs if available
                contract_cost = self.cost_model.future_cost_per_contract(symbol)
                multiplier = self.cost_model.get_future_contract_multiplier(symbol)
                # Position in contracts = weight * portfolio_value / (price * contract_multiplier)
                # contracts_traded = weight_change * portfolio_value / (price * multiplier)
                # Using initial_capital as portfolio_value approximation (consistent with equity path)
                contracts_traded = (
                    changes * self.config.initial_capital / (price * multiplier)
                )
                symbol_costs = (
                    contracts_traded.abs() * contract_cost / self.config.initial_capital
                )

            elif self.config.asset_class == AssetClass.CRYPTO:
                daily_vol_pct = 0.0  # Would need 24h volume data
                cost_bps = self.cost_model.crypto_cost_bps(daily_vol_pct)
                # Cost as a fraction of portfolio value (weight_delta * cost_bps).
                symbol_costs = changes * (cost_bps / 10000)

            else:
                symbol_costs = pd.Series(0.0, index=position_changes.index)

            costs += symbol_costs.fillna(0)

        return costs

    def _extract_trades(
        self,
        position_changes: pd.DataFrame,
        prices: pd.DataFrame,
        costs: pd.Series,
    ) -> pd.DataFrame:
        """Extract individual trades from position changes."""
        trades_list = []

        for symbol in position_changes.columns:
            changes = position_changes[symbol]
            trade_idx = changes[changes != 0].index

            for idx in trade_idx:
                change = changes[idx]
                price = prices.loc[idx, symbol]

                trades_list.append(
                    {
                        "timestamp": idx,
                        "symbol": symbol,
                        "side": "buy" if change > 0 else "sell",
                        "weight_change": change,
                        "price": price,
                        "cost": costs[idx] if idx in costs.index else 0,
                    }
                )

        if not trades_list:
            return pd.DataFrame(
                columns=[
                    "timestamp",
                    "symbol",
                    "side",
                    "weight_change",
                    "price",
                    "cost",
                ]
            )

        return pd.DataFrame(trades_list)

    def _calculate_metrics(
        self,
        returns: pd.Series,
        equity: pd.Series,
        trades: pd.DataFrame,
    ) -> dict[str, float]:
        """Calculate performance metrics."""
        metrics = {}

        # Basic returns
        total_return = equity.iloc[-1] / equity.iloc[0] - 1
        n_periods = len(returns)
        ann_factor = 252  # daily data assumption

        # Annualized metrics
        ann_return = (1 + total_return) ** (ann_factor / n_periods) - 1
        ann_vol = returns.std() * np.sqrt(ann_factor)

        metrics["total_return"] = total_return
        metrics["annualized_return"] = ann_return
        metrics["annualized_volatility"] = ann_vol

        # Sharpe & Sortino
        risk_free = 0.0  # Assume 0 for simplicity
        excess_returns = returns - risk_free / ann_factor

        if returns.std() > 0:
            metrics["sharpe"] = (
                excess_returns.mean() / returns.std() * np.sqrt(ann_factor)
            )
        else:
            metrics["sharpe"] = 0.0

        # TEMP REGRESSION CHECK: buggy denominator
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0 and downside_returns.std() > 0:
            metrics["sortino"] = (
                excess_returns.mean() / downside_returns.std() * np.sqrt(ann_factor)
            )
        else:
            metrics["sortino"] = 0.0

        # Drawdown
        rolling_max = equity.expanding().max()
        drawdown = (equity - rolling_max) / rolling_max
        metrics["max_drawdown"] = drawdown.min()
        metrics["max_drawdown_duration"] = self._max_dd_duration(drawdown)

        # Profit factor
        gross_profit = returns[returns > 0].sum()
        gross_loss = abs(returns[returns < 0].sum())
        metrics["profit_factor"] = (
            gross_profit / gross_loss if gross_loss > 0 else np.inf
        )

        # Trade stats
        if len(trades) > 0:
            metrics["num_trades"] = len(trades)
            metrics["avg_trade_cost"] = trades["cost"].mean()
        else:
            metrics["num_trades"] = 0
            metrics["avg_trade_cost"] = 0

        # Calmar
        if abs(metrics["max_drawdown"]) > 0:
            metrics["calmar"] = ann_return / abs(metrics["max_drawdown"])
        else:
            metrics["calmar"] = np.inf

        return metrics

    def _max_dd_duration(self, drawdown: pd.Series) -> int:
        """Calculate maximum drawdown duration in periods."""
        in_dd = drawdown < 0
        if not in_dd.any():
            return 0

        # Group consecutive drawdown periods
        dd_groups = (in_dd != in_dd.shift()).cumsum()
        dd_durations = in_dd.groupby(dd_groups).sum()
        return int(dd_durations.max()) if len(dd_durations) > 0 else 0


def run_backtest(
    prices: pd.DataFrame,
    signals: pd.DataFrame,
    config: BacktestConfig | None = None,
    **kwargs,
) -> BacktestResult:
    """Convenience function to run a backtest."""
    config = config or BacktestConfig()
    backtester = VectorizedBacktester(config)
    return backtester.run(prices, signals, **kwargs)
