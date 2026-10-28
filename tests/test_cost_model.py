"""
Regression tests for the transaction cost model (src/qtr/backtest/engine.py).

These tests pin down the **cost-model units fix** applied during the H1/H2
cycle. The original engine multiplied the weight delta by the per-share
price and the bps cost (``weight_delta * price * bps / 1e4``), which
injected the dollar price of the instrument into the cost and inflated
transaction costs by ~price/100 (e.g. ~400x for a $400 stock). The
corrected model treats the weight delta as a fraction of capital:

    cost_fraction_of_capital = weight_delta * cost_bps / 1e4

Costs must therefore be invariant to the price level of the instrument.
These tests must never regress: the PROMPT_V2 evidence gates (Sharpe,
profit factor, drawdown) are only meaningful with correctly scaled costs.
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
    run_backtest,
)


# ============================================================
# CostModel component tests
# ============================================================
class TestCostModelComponents:
    def test_equity_cost_bps_composition(self):
        cm = CostModel(
            equity_commission_bps=1.0,
            equity_spread_bps=1.0,
            equity_impact_bps_per_pct_adv=0.1,
        )
        # 1 bp commission + 1 bp spread + 0.1 bp per 1% ADV * 10% ADV
        assert cm.equity_cost_bps(spread_bps=1.0, adv_pct=10.0) == pytest.approx(3.0)

    def test_equity_cost_bps_default_spread(self):
        cm = CostModel(equity_commission_bps=1.0, equity_spread_bps=2.0)
        assert cm.equity_cost_bps() == pytest.approx(3.0)

    def test_future_cost_per_contract(self):
        cm = CostModel(
            future_commission_per_contract=0.50,
            future_spread_ticks=0.25,
            future_slippage_ticks=0.5,
            future_tick_value=12.50,
        )
        # $0.50 + (0.25 + 0.5) ticks * $12.50/tick = $9.875
        assert cm.future_cost_per_contract() == pytest.approx(9.875)

    def test_crypto_cost_bps(self):
        cm = CostModel(
            crypto_fee_bps=5.0,
            crypto_spread_bps=2.0,
            crypto_slippage_bps_per_pct_daily_vol=1.0,
        )
        # 5 + 2 + 1 * 5 = 12 bps at 5% daily volume participation
        assert cm.crypto_cost_bps(daily_vol_pct=5.0) == pytest.approx(12.0)


# ============================================================
# Units regression: costs are a fraction of capital, price-invariant
# ============================================================
class TestCostUnitsRegression:
    @staticmethod
    def _single_asset_prices(price: float, n: int = 60, seed: int = 7) -> pd.DataFrame:
        rng = np.random.default_rng(seed)
        rets = rng.normal(0.0005, 0.01, n)
        prices = pd.DataFrame(
            {"SYM": price * np.exp(np.cumsum(rets))},
            index=pd.bdate_range("2020-01-01", periods=n),
        )
        return prices

    @staticmethod
    def _step_signals(index: pd.Index, weight: float = 1.0) -> pd.DataFrame:
        sig = pd.DataFrame({"SYM": 0.0}, index=index)
        sig.iloc[0] = weight  # establish position on day 0
        return sig

    def test_cost_independent_of_price_level(self):
        """A $10 stock and a $1000 stock with the same weight delta
        must incur the same capital-fraction cost (regression guard for
        the old `weight_delta * price * bps` bug)."""
        cm = CostModel(
            equity_commission_bps=1.0,
            equity_spread_bps=1.0,
            equity_impact_bps_per_pct_adv=0.0,  # isolate price effect
        )
        results = {}
        for price in (10.0, 100.0, 1000.0):
            prices = self._single_asset_prices(price)
            signals = self._step_signals(prices.index)
            cfg = BacktestConfig(
                initial_capital=1_000_000.0,
                cost_model=cm,
                asset_class=AssetClass.EQUITY,
                max_position_size=1.0,
                max_leverage=1.0,
                allow_short=False,
            )
            res = run_backtest(prices=prices, signals=signals, config=cfg)
            results[price] = res

        # Day-0 net return must be identical (and equal to -cost_bps/1e4
        # for a full-weight entry: -2/1e4 = -0.0002).
        for price, res in results.items():
            assert res.returns.iloc[0] == pytest.approx(-2.0 / 10_000, abs=1e-12), (
                f"day-0 cost depends on price level for price={price} (cost-model units regression)"
            )

    def test_cost_scales_linearly_with_weight_delta(self):
        cm = CostModel(
            equity_commission_bps=1.0,
            equity_spread_bps=1.0,
            equity_impact_bps_per_pct_adv=0.0,
        )
        prices = self._single_asset_prices(100.0)
        cfg = BacktestConfig(
            initial_capital=1_000_000.0,
            cost_model=cm,
            asset_class=AssetClass.EQUITY,
            max_position_size=1.0,
            max_leverage=1.0,
            allow_short=False,
        )
        half = run_backtest(
            prices=prices, signals=self._step_signals(prices.index, 0.5), config=cfg
        )
        full = run_backtest(
            prices=prices, signals=self._step_signals(prices.index, 1.0), config=cfg
        )
        assert half.returns.iloc[0] == pytest.approx(full.returns.iloc[0] / 2.0, abs=1e-12)

    def test_zero_cost_model_gives_zero_cost(self):
        cm = CostModel(
            equity_commission_bps=0.0,
            equity_spread_bps=0.0,
            equity_impact_bps_per_pct_adv=0.0,
        )
        prices = self._single_asset_prices(100.0)
        signals = self._step_signals(prices.index)
        cfg = BacktestConfig(
            initial_capital=1_000_000.0,
            cost_model=cm,
            asset_class=AssetClass.EQUITY,
            max_position_size=1.0,
            max_leverage=1.0,
            allow_short=False,
        )
        res = run_backtest(prices=prices, signals=signals, config=cfg)
        gross = prices.pct_change().fillna(0)
        expected = (signals.shift(1) * gross).sum(axis=1)
        assert np.allclose(res.returns.values, expected.values, atol=1e-12)

    def test_higher_costs_reduce_equity(self):
        prices = self._single_asset_prices(100.0)
        signals = self._step_signals(prices.index)
        base = {
            "initial_capital": 1_000_000.0,
            "asset_class": AssetClass.EQUITY,
            "max_position_size": 1.0,
            "max_leverage": 1.0,
            "allow_short": False,
        }
        cheap = run_backtest(
            prices=prices,
            signals=signals,
            config=BacktestConfig(
                cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
                **base,
            ),
        )
        expensive = run_backtest(
            prices=prices,
            signals=signals,
            config=BacktestConfig(
                cost_model=CostModel(equity_commission_bps=10.0, equity_spread_bps=10.0),
                **base,
            ),
        )
        assert expensive.equity_curve.iloc[-1] < cheap.equity_curve.iloc[-1]


# ============================================================
# Equity ADV impact path
# ============================================================
class TestEquityImpactModel:
    def test_participation_impact_increases_cost(self):
        """With ADV provided, a large weight delta on a thin symbol
        incurs market-impact cost on top of commission + spread."""
        cm = CostModel(
            equity_commission_bps=1.0,
            equity_spread_bps=1.0,
            equity_impact_bps_per_pct_adv=0.1,
        )
        n = 60
        rng = np.random.default_rng(1)
        index = pd.bdate_range("2020-01-01", periods=n)
        # first price is exactly 100.0 so ADV participation is exact
        path = np.concatenate([[0.0], np.cumsum(rng.normal(0, 0.01, n - 1))])
        prices = pd.DataFrame({"THIN": 100.0 * np.exp(path)}, index=index)
        signals = pd.DataFrame({"THIN": 0.0}, index=index)
        signals.iloc[0] = 1.0
        # ADV of 10k shares: 1.0 weight * $1M / $100 = 10k shares = 100% ADV
        adv = pd.Series({"THIN": 10_000.0})
        cfg = BacktestConfig(
            initial_capital=1_000_000.0,
            cost_model=cm,
            asset_class=AssetClass.EQUITY,
            max_position_size=1.0,
            max_leverage=1.0,
            allow_short=False,
        )
        res = run_backtest(prices=prices, signals=signals, adv=adv, config=cfg)
        # commission+spread = 2 bps; impact = 0.1 bps per 1% * 100% = 10 bps => 12 bps
        assert res.returns.iloc[0] == pytest.approx(-12.0 / 10_000, abs=1e-9)

    def test_missing_adv_defaults_to_zero_impact(self):
        cm = CostModel(
            equity_commission_bps=1.0,
            equity_spread_bps=1.0,
            equity_impact_bps_per_pct_adv=0.1,
        )
        n = 60
        rng = np.random.default_rng(1)
        index = pd.bdate_range("2020-01-01", periods=n)
        path = np.concatenate([[0.0], np.cumsum(rng.normal(0, 0.01, n - 1))])
        prices = pd.DataFrame({"SYM": 100.0 * np.exp(path)}, index=index)
        signals = pd.DataFrame({"SYM": np.nan}, index=index)
        signals.iloc[0] = 1.0
        cfg = BacktestConfig(
            initial_capital=1_000_000.0,
            cost_model=cm,
            asset_class=AssetClass.EQUITY,
            max_position_size=1.0,
            max_leverage=1.0,
            allow_short=False,
        )
        res = run_backtest(prices=prices, signals=signals, config=cfg)
        assert res.returns.iloc[0] == pytest.approx(-2.0 / 10_000, abs=1e-12)


class TestCostModelFuturesSpecs:
    def test_future_cost_per_contract_with_symbol_specs(self):
        cm = CostModel(
            futures_specs={
                "ES": {
                    "tick_value": 50.0,
                    "spread_ticks": 1.0,
                    "slippage_ticks": 0.5,
                    "commission": 2.0,
                }
            }
        )
        # (1.0 + 0.5) * 50.0 + 2.0 = 75.0 + 2.0 = 77.0
        assert cm.future_cost_per_contract("ES") == pytest.approx(77.0)

    def test_future_cost_per_contract_with_symbol_missing_keys_uses_defaults(self):
        cm = CostModel(
            future_tick_value=12.50,
            future_spread_ticks=0.25,
            future_slippage_ticks=0.5,
            future_commission_per_contract=0.50,
            futures_specs={"CL": {"multiplier": 1000.0}},  # missing other keys
        )
        # falls back to defaults for missing keys
        assert cm.future_cost_per_contract("CL") == pytest.approx(9.875)

    def test_get_future_contract_multiplier_with_symbol(self):
        cm = CostModel(futures_specs={"ES": {"multiplier": 50.0}})
        assert cm.get_future_contract_multiplier("ES") == 50.0

    def test_get_future_contract_multiplier_with_symbol_missing_key(self):
        cm = CostModel(future_contract_multiplier=100.0, futures_specs={"ES": {}})
        assert cm.get_future_contract_multiplier("ES") == 100.0

    def test_get_future_contract_multiplier_no_symbol(self):
        cm = CostModel(future_contract_multiplier=50.0)
        assert cm.get_future_contract_multiplier() == 50.0
        assert cm.get_future_contract_multiplier(None) == 50.0
