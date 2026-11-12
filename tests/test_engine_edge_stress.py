"""Stress tests for the backtest engine at the boundary conditions the
STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md fallback path lists:

* extreme leverage (max_leverage == 0 zeros all exposure; a very large
  max_leverage normalizes nothing),
* zero-volume / degenerate futures contracts (multiplier == 0 removes a
  symbol's exposure while the rest of the book still trades),
* look-ahead boundary (bar 0 earns nothing even when a position is established
  there; bar t earns the position from bar t-1).

These are behavioural pins over ``src/qtr/backtest/engine.py``; the engine is
not modified here. Every case fails closed (no crash, boundary metrics, no
look-ahead) rather than manufacturing a return.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from qtr.backtest.engine import (
    AssetClass,
    BacktestConfig,
    CostModel,
    VectorizedBacktester,
    run_backtest,
)


def _make_prices(n: int = 100, seed: int = 42, symbols=("A", "B")) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    index = pd.bdate_range("2020-01-01", periods=n)
    data = {}
    for sym in symbols:
        rets = rng.normal(0.0004, 0.01, n)
        data[sym] = 100.0 * np.exp(np.cumsum(rets))
    return pd.DataFrame(data, index=index)


def _make_config(**overrides) -> BacktestConfig:
    defaults = {
        "initial_capital": 1_000_000.0,
        "cost_model": CostModel(
            equity_commission_bps=0.0,
            equity_spread_bps=0.0,
            equity_impact_bps_per_pct_adv=0.0,
        ),
        "asset_class": AssetClass.EQUITY,
        "max_position_size": 1.0,
        "max_leverage": 1.0,
        "allow_short": False,
    }
    defaults.update(overrides)
    return BacktestConfig(**defaults)


# --------------------------------------------------------------------------- #
# Extreme leverage
# --------------------------------------------------------------------------- #
class TestExtremeLeverage:
    def test_zero_leverage_zeros_all_exposure_without_crashing(self):
        """max_leverage == 0 scales every position to zero: the book is flat,
        no trades are recorded, and the metrics degrade to the boundary
        values instead of dividing by zero or manufacturing a return."""
        prices = _make_prices(symbols=("A", "B"))
        signals = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)  # gross = 2
        cfg = _make_config(max_leverage=0.0)
        res = run_backtest(prices=prices, signals=signals, config=cfg)

        assert (res.positions == 0.0).all().all()
        assert len(res.trades) == 0
        assert (res.returns == 0.0).all()
        m = res.metrics
        assert m["total_return"] == 0.0
        assert m["annualized_return"] == 0.0
        assert m["annualized_volatility"] == 0.0
        assert m["sharpe"] == 0.0
        assert m["max_drawdown"] == 0.0
        assert m["profit_factor"] == float("inf")
        assert m["num_trades"] == 0
        assert m["calmar"] == float("inf")

    def test_zero_leverage_signal_change_still_earns_nothing(self):
        """With zero leverage a position change at bar 0 is a trade in the log
        only if it were non-zero, but since every position is zeroed there is
        no change and no cost; bar 0 earns nothing regardless."""
        prices = _make_prices(symbols=("A",))
        signals = pd.DataFrame({"A": np.nan}, index=prices.index)
        signals.iloc[0] = 1.0
        cfg = _make_config(max_leverage=0.0, allow_short=False)
        res = run_backtest(prices=prices, signals=signals, config=cfg)
        assert (res.positions["A"] == 0.0).all()
        assert res.returns.iloc[0] == 0.0
        assert len(res.trades) == 0

    def test_enormous_leverage_normalizes_nothing(self):
        """A max_leverage far above any plausible gross exposure leaves every
        position exactly as the signal specified it."""
        prices = _make_prices(symbols=("A", "B"))
        signals = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)  # gross = 2
        cfg = _make_config(max_leverage=1_000_000.0)
        res = run_backtest(prices=prices, signals=signals, config=cfg)
        assert np.allclose(res.positions.values, 1.0)
        gross = res.positions.abs().sum(axis=1)
        assert np.allclose(gross.values, 2.0)


# --------------------------------------------------------------------------- #
# Zero-volume / degenerate futures contract
# --------------------------------------------------------------------------- #
class TestDegenerateFuturesContract:
    def test_zero_multiplier_removes_exposure_for_that_symbol_only(self):
        """A futures symbol whose contract multiplier is 0.0 cannot be traded:
        the engine removes its exposure while the other symbol still trades
        normally (fail closed per symbol, not per panel)."""
        prices = _make_prices(symbols=("ES", "NQ"))
        signals = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)
        cfg = _make_config(
            asset_class=AssetClass.FUTURE,
            max_leverage=5.0,
            max_position_size=5.0,
        )
        # NQ has a normal multiplier; ES is degenerate (multiplier == 0).
        cfg.cost_model.future_contract_multiplier = 50.0
        cfg.cost_model.futures_specs = {"ES": {"multiplier": 0.0}}
        res = run_backtest(prices=prices, signals=signals, config=cfg)

        assert (res.positions["ES"] == 0.0).all()
        assert np.allclose(res.positions["NQ"].values, 1.0)
        # ES never trades; NQ is fully invested.
        es_trades = res.trades[res.trades["symbol"] == "ES"]
        assert len(es_trades) == 0

    def test_non_zero_multiplier_trades_normally(self):
        """Control: with a valid multiplier the futures symbol is fully
        exposed and costs flow through."""
        prices = _make_prices(symbols=("ES",))
        signals = pd.DataFrame({"ES": 0.0}, index=prices.index)
        signals.iloc[0] = 1.0
        cfg = _make_config(asset_class=AssetClass.FUTURE, max_leverage=5.0, max_position_size=5.0)
        cfg.cost_model.future_commission_per_contract = 0.50
        cfg.cost_model.future_contract_multiplier = 50.0
        res = run_backtest(prices=prices, signals=signals, config=cfg)
        assert np.allclose(res.positions["ES"].iloc[0], 1.0)
        assert res.returns.iloc[0] < 0.0  # day-0 entry cost


# --------------------------------------------------------------------------- #
# Look-ahead boundary
# --------------------------------------------------------------------------- #
class TestLookAheadBoundary:
    def test_bar_zero_earns_nothing_even_with_a_position_established_there(self):
        """The engine applies signals.shift(1), so a position established at
        the close of bar 0 earns the bar-1 return, not the bar-0 return. With
        zero costs bar 0 earns exactly 0.0 and bar 1 earns the full asset
        return of the bar-0 position."""
        prices = _make_prices(symbols=("A",))
        signals = pd.DataFrame({"A": np.nan}, index=prices.index)
        signals.iloc[0] = 1.0  # long at close of bar 0
        signals.iloc[1] = 0.0  # flat at close of bar 1
        cfg = _make_config()  # zero costs
        res = run_backtest(prices=prices, signals=signals, config=cfg)

        asset_ret = prices["A"].pct_change().fillna(0.0)
        assert res.returns.iloc[0] == pytest.approx(0.0, abs=1e-12)
        assert res.returns.iloc[1] == pytest.approx(asset_ret.iloc[1], abs=1e-12)
        assert res.trades["side"].iloc[0] == "buy"
        assert res.trades["side"].iloc[1] == "sell"

    def test_signal_at_bar_zero_never_contemporaneous(self):
        """No signal at any bar can earn that same bar's return: re-enter at
        bar 50 and bar 50 still earns nothing, bar 51 earns the bar-50
        position."""
        prices = _make_prices(symbols=("A",))
        signals = pd.DataFrame({"A": 0.0}, index=prices.index)
        signals.iloc[50] = 1.0
        cfg = _make_config()
        res = run_backtest(prices=prices, signals=signals, config=cfg)

        asset_ret = prices["A"].pct_change().fillna(0.0)
        assert res.returns.iloc[50] == pytest.approx(0.0, abs=1e-12)
        assert res.returns.iloc[51] == pytest.approx(asset_ret.iloc[51], abs=1e-12)

    def test_extreme_position_at_bar_zero_still_earns_nothing(self):
        """A very large position at bar 0 is capped by max_position_size, but
        even the capped position earns nothing at bar 0 (shift(1) applies
        before any return is attributed)."""
        prices = _make_prices(symbols=("A",))
        signals = pd.DataFrame({"A": np.nan}, index=prices.index)
        signals.iloc[0] = 1e6
        cfg = _make_config(max_position_size=1.0, max_leverage=1.0)
        res = run_backtest(prices=prices, signals=signals, config=cfg)
        assert np.allclose(res.positions["A"].iloc[0], 1.0)
        assert res.returns.iloc[0] == pytest.approx(0.0, abs=1e-12)
