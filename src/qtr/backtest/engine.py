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

    def equity_cost_bps(self, spread_bps: float | None = None, adv_pct: float = 0.0) -> float:
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
            return self.futures_specs[symbol].get("multiplier", self.future_contract_multiplier)
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

        # Degenerate-input guard: an empty panel (no bars after alignment) has no
        # position changes to extract and no returns to annualize, and every
        # downstream step that indexes ``.iloc[0]`` or ``.iloc[-1]`` raises
        # ``IndexError`` on it. The fetcher's documented "no data" path returns
        # an empty DataFrame per symbol (fetcher.py:196), and a runner that
        # passes every symbol through the engine (run_ts_momentum_experiment.py)
        # hands that empty panel straight here, so the crash is reachable from
        # a live data failure, not just from a synthetic test fixture.
        #
        # The boundary is the same one ``validate_strategy`` returns for an
        # empty return series (statistics.py:759): every shared metric is a
        # boundary value, so the two implementations still agree on this input
        # and the cross-module contract in test_engine_metric_agreement.py
        # holds. The engine-only metrics follow the same boundary convention
        # (zero volatility, zero Sortino, zero Calmar, zero trade cost).
        if len(common_index) == 0:
            empty_returns = pd.Series([], dtype=float)
            empty_equity = pd.Series([], dtype=float)
            empty_trades = pd.DataFrame(
                columns=["timestamp", "symbol", "side", "weight_change", "price", "cost"]
            )
            empty_positions = pd.DataFrame(index=common_index, columns=prices.columns)
            return BacktestResult(
                equity_curve=empty_equity,
                returns=empty_returns,
                positions=empty_positions,
                trades=empty_trades,
                metrics=self._calculate_metrics(empty_returns, empty_equity, empty_trades),
                config=self.config,
            )

        if volumes is not None:
            volumes = volumes.loc[common_index]
        else:
            volumes = pd.DataFrame(index=prices.index, columns=prices.columns, dtype=float)

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
        signals = signals.clip(-self.config.max_position_size, self.config.max_position_size)

        # If short not allowed, clip negative positions
        if not self.config.allow_short:
            signals = signals.clip(lower=0)

        # Calculate position changes (trades)
        position_changes = signals.diff().fillna(signals.iloc[0])

        # Calculate returns
        price_returns = prices.pct_change().fillna(0)

        # Portfolio returns before costs
        portfolio_returns = (signals.shift(1) * price_returns).sum(axis=1)

        # Calculate transaction costs. The per-symbol breakdown is kept so the
        # trade log can attribute each trade the cost IT incurred.
        symbol_costs = self._calculate_costs_by_symbol(position_changes, prices, volumes, adv)
        costs = self._total_costs(symbol_costs)

        # Net returns
        net_returns = portfolio_returns - costs

        # Equity curve
        equity = (1 + net_returns).cumprod() * self.config.initial_capital

        # Extract trades
        trades = self._extract_trades(position_changes, prices, symbol_costs)

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
        return self._total_costs(
            self._calculate_costs_by_symbol(position_changes, prices, volumes, adv)
        )

    def _total_costs(self, symbol_costs: pd.DataFrame) -> pd.Series:
        """The portfolio cost per bar: the sum of the per-symbol costs.

        The accumulation runs over the symbols in column order and is the
        *same* series the engine has always charged, so the net returns, the
        equity curve and every published metric are unchanged by the
        attribution fix in ``_extract_trades``.
        """
        if symbol_costs is None or symbol_costs.empty or symbol_costs.shape[1] == 0:
            index = getattr(symbol_costs, "index", None)
            if index is None:
                return pd.Series(dtype=float)
            return pd.Series(0.0, index=index)
        return symbol_costs.sum(axis=1)

    def _calculate_costs_by_symbol(
        self,
        position_changes: pd.DataFrame,
        prices: pd.DataFrame,
        volumes: pd.DataFrame,
        adv: pd.Series | None,
    ) -> pd.DataFrame:
        """Calculate the transaction cost of each symbol for each time step.

        Every column of the result is that symbol's own cost, expressed as a
        fraction of capital; the portfolio cost of a bar is their sum (see
        ``_total_costs``). Keeping the breakdown is what allows the trade log
        to record the cost each trade actually incurred: the log used to store
        the *bar total* on every trade of that bar, so a bar with k
        simultaneous trades reported k times the cost that was charged, and
        the trade log no longer reconciled with the P&L. See
        tests/test_trade_log_cost_reconciliation.py.
        """
        per_symbol: dict[str, pd.Series] = {}

        for symbol in position_changes.columns:
            changes = position_changes[symbol].abs()
            if changes.sum() == 0:
                # The symbol never trades: it contributes no cost.
                per_symbol[symbol] = pd.Series(0.0, index=position_changes.index)
                continue

            price = prices[symbol]

            if self.config.asset_class == AssetClass.EQUITY:
                # Estimate ADV participation using initial capital (approximate).
                # changes is a weight delta (fraction of capital); shares_traded
                # converts it to a share count for volume-participation impact.
                if adv is not None and symbol in adv.index and adv[symbol] > 0:
                    # Position change in shares = weight_change * initial_capital / price
                    shares_traded = changes * self.config.initial_capital / price
                    adv_pct = (shares_traded / adv[symbol]).clip(0, 1) * 100  # as percentage
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
                contracts_traded = changes * self.config.initial_capital / (price * multiplier)
                symbol_costs = contracts_traded.abs() * contract_cost / self.config.initial_capital

            elif self.config.asset_class == AssetClass.CRYPTO:
                daily_vol_pct = 0.0  # Would need 24h volume data
                cost_bps = self.cost_model.crypto_cost_bps(daily_vol_pct)
                # Cost as a fraction of portfolio value (weight_delta * cost_bps).
                symbol_costs = changes * (cost_bps / 10000)

            else:
                symbol_costs = pd.Series(0.0, index=position_changes.index)

            per_symbol[symbol] = symbol_costs.fillna(0)

        return pd.DataFrame(per_symbol, index=position_changes.index)

    def _extract_trades(
        self,
        position_changes: pd.DataFrame,
        prices: pd.DataFrame,
        symbol_costs: pd.DataFrame,
    ) -> pd.DataFrame:
        """Extract individual trades from position changes.

        Each trade records the cost *it* incurred -- its own symbol's share of
        the transaction cost charged in that bar -- so the trade log reconciles
        with the engine's charge: the per-trade costs sum to the total cost
        the backtest deducted from the returns. The log used to record the
        *bar total* on every trade of that bar, which over-counted the charged
        cost by the number of simultaneous trades (1.79x on the frozen H10
        artifact). See tests/test_trade_log_cost_reconciliation.py.
        """
        trades_list = []

        for symbol in position_changes.columns:
            changes = position_changes[symbol]
            symbol_cost_series = symbol_costs[symbol]
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
                        "cost": symbol_cost_series.at[idx],
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

        # Degenerate-input guard: an empty return series cannot be annualized
        # (252 / len(returns) divides by zero) and yields no trades, so it
        # must return the same boundary values ``validate_strategy`` returns
        # for the same input (statistics.py:759) rather than crashing on
        # ``equity.iloc[-1]``. The engine-only metrics follow the flat-series
        # convention (zero Sortino, zero drawdown duration, zero trade cost,
        # infinite Calmar from a zero drawdown), matching what this function
        # already returns for a 40-bar zero series.
        if len(returns) == 0:
            return {
                "total_return": 0.0,
                "annualized_return": 0.0,
                "annualized_volatility": 0.0,
                "sharpe": 0.0,
                "sortino": 0.0,
                "max_drawdown": 0.0,
                "max_drawdown_duration": 0,
                "profit_factor": 1.0,
                "num_trades": len(trades),
                "avg_trade_cost": 0.0,
                "calmar": np.inf,
            }

        # Basic returns
        # The total return is measured from the INITIAL capital to the final
        # equity, so it spans every bar of the return series (n_periods
        # compounding periods). Measuring it from equity.iloc[0] instead would
        # silently drop the first bar -- the only bar on which the initial
        # entry cost is charged -- and would disagree with
        # qtr.validation.statistics.validate_strategy, which measures the same
        # statistic as ``(1 + returns).cumprod().iloc[-1] - 1``: bit-identical
        # to this for finite series, and matching even on a NaN-tail input
        # where the engine's gross <= 0 guard fires. See
        # tests/test_engine_total_return_consistency.py and
        # tests/test_engine_metric_agreement.py.
        total_return = equity.iloc[-1] / self.config.initial_capital - 1.0
        n_periods = len(returns)
        ann_factor = 252  # daily data assumption

        # Annualized metrics
        # The volatility keeps the SAMPLE standard deviation (pandas
        # `Series.std()`, ddof=1) because that is the convention
        # qtr.validation.statistics.validate_strategy uses for
        # `annualized_volatility` and the one every published artifact
        # records. The Sharpe below uses the POPULATION standard deviation,
        # exactly as the record does -- the two conventions differ, and
        # mirroring the record is what makes the two implementations agree.
        gross = 1.0 + total_return
        ann_return = (gross ** (ann_factor / n_periods) - 1) if gross > 0.0 else -1.0
        ann_vol = returns.std() * np.sqrt(ann_factor)

        metrics["total_return"] = total_return
        metrics["annualized_return"] = ann_return
        metrics["annualized_volatility"] = ann_vol

        # Sharpe & Sortino
        # The Sharpe denominator is the POPULATION standard deviation
        # (ddof=0), matching qtr.validation.statistics.sharpe_ratio (which
        # divides by `numpy.ndarray.std()`, ddof=0) and therefore
        # validate_strategy. The engine used to divide by the SAMPLE standard
        # deviation (pandas `Series.std()`, ddof=1), so every published
        # artifact carried TWO Sharpes for one run -- the engine's under
        # `strategy_metrics` and validate_strategy's under `validation` --
        # differing by exactly sqrt(n / (n - 1)) (0.02% at n = 2515).
        # The record's convention is ddof=0: the certified H10-H14 numbers
        # come from `sharpe_ratio` calls, so the engine is the side that had
        # to move. The change is a uniform rescaling of every Sharpe
        # computed from the same number of bars, so it cannot reorder two
        # strategies compared on the same series, and no certified number,
        # gate threshold or published verdict depends on it.
        # See tests/test_engine_metric_agreement.py.
        risk_free = 0.0  # Assume 0 for simplicity
        excess_returns = returns - risk_free / ann_factor

        # The degenerate-series guard carries the same tolerance as
        # `sharpe_ratio` (1e-15) instead of testing for an exact zero: a
        # constant return series has a standard deviation of ~1e-19 from
        # float noise, not exactly 0.0, so an exact `> 0` test lets it
        # through and divides by ~1e-19, producing a garbage Sharpe of ~1e16
        # where validate_strategy reports 0.0.
        if returns.std(ddof=0) > 1e-15:
            metrics["sharpe"] = excess_returns.mean() / returns.std(ddof=0) * np.sqrt(ann_factor)
        else:
            metrics["sharpe"] = 0.0

        # Sortino ratio uses the *downside deviation* — the square root of the
        # mean squared shortfall below the target — NOT the standard deviation
        # of the negative-returns subset. The two differ whenever the series
        # contains zero or positive months: the loss-subset std ignores those
        # observations entirely, while the downside deviation counts a 0
        # shortfall for each one (raising the denominator and lowering the
        # ratio). The loss-subset std understates downside risk and inflates
        # the Sortino ratio.
        shortfall = np.minimum(0, returns - risk_free / ann_factor)
        downside_dev = np.sqrt(np.mean(shortfall**2))
        # The guard is `np.isfinite(downside_dev) and downside_dev > 0`, not
        # `downside_dev > 0`: a non-finite downside deviation (the series
        # carries an `inf`, a `-inf` or a `nan` -- the H58/H61/H62 input
        # class, reachable whenever a runner builds a return series from
        # `prices.pct_change()` and a price crosses zero or a roll gap is
        # unbounded) compares unordered, so `inf > 0` is True and the old
        # guard did NOT fire: the function then divided `excess_returns.mean()`
        # (inf or nan) by an inf downside deviation and emitted `nan`, while
        # the engine's own Sharpe guard (``engine.py:414``) fired on the same
        # input and reported ``0.0`` -- the same silent-void failure H62 found
        # in `sharpe_ratio`, one guard over in the same metric block. Both now
        # report 0.0 for every non-finite input. For every finite input the
        # arithmetic is bit-identical to before.
        if np.isfinite(downside_dev) and downside_dev > 0:
            metrics["sortino"] = excess_returns.mean() / downside_dev * np.sqrt(ann_factor)
        else:
            metrics["sortino"] = 0.0

        # Drawdown. The denominator is guarded the same way the matching
        # guard in ``validate_strategy`` was given in §H71
        # (statistics.py:825): ``rolling_max.where(rolling_max > 0, 1.0)``.
        # Without it the first bar of a strategy that loses its entire
        # capital on day one -- ``equity[0] == 0``, so ``rolling_max[0]``
        # is exactly 0 -- divides by zero and reports ``max_drawdown = nan``,
        # while ``validate_strategy`` reports ``0.0`` for the same input: the
        # two implementations disagreed on a series the record actually
        # contains (any runner that feeds a first-bar total loss, e.g. a
        # contract that is in default on day one). The guard is a no-op on
        # every curve that starts at positive capital: ``rolling_max`` is
        # then positive from the first bar and the substitution never fires,
        # so the published drawdowns are bit-identical (measured: identical
        # to all five committed equity curves). See
        # tests/test_engine_metric_agreement.py.
        rolling_max = equity.expanding().max()
        drawdown = (equity - rolling_max) / rolling_max.where(rolling_max > 0, 1.0)
        metrics["max_drawdown"] = drawdown.min()
        metrics["max_drawdown_duration"] = self._max_dd_duration(drawdown)

        # Profit factor
        gross_profit = returns[returns > 0].sum()
        gross_loss = abs(returns[returns < 0].sum())
        metrics["profit_factor"] = gross_profit / gross_loss if gross_loss > 0 else np.inf

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
