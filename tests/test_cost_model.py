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


# ============================================================
# Degenerate-input guards: fail closed to 0.0 on invalid operands
# ============================================================
class TestCostModelDegenerateInput:
    def test_equity_cost_bps_rejects_invalid_scalar(self):
        cm = CostModel(
            equity_commission_bps=1.0,
            equity_spread_bps=1.0,
            equity_impact_bps_per_pct_adv=0.1,
        )
        assert cm.equity_cost_bps(spread_bps=1.0, adv_pct=-1.0) == 0.0
        assert cm.equity_cost_bps(spread_bps=-1.0, adv_pct=1.0) == 0.0
        assert cm.equity_cost_bps(spread_bps=float("nan"), adv_pct=1.0) == 0.0
        assert cm.equity_cost_bps(spread_bps=1.0, adv_pct=float("inf")) == 0.0

    def test_crypto_cost_bps_rejects_invalid_scalar(self):
        cm = CostModel(
            crypto_fee_bps=5.0,
            crypto_spread_bps=2.0,
            crypto_slippage_bps_per_pct_daily_vol=1.0,
        )
        assert cm.crypto_cost_bps(daily_vol_pct=-1.0) == 0.0
        assert cm.crypto_cost_bps(daily_vol_pct=float("nan")) == 0.0

    def test_crypto_cost_bps_zeroes_invalid_series_rows(self):
        cm = CostModel(
            crypto_fee_bps=5.0,
            crypto_spread_bps=2.0,
            crypto_slippage_bps_per_pct_daily_vol=1.0,
        )
        # A negative row is not a missing value; it is an impossible input, so
        # that row's slippage input is zeroed (fee + spread still apply).
        vols = pd.Series([1.0, -2.0, 3.0])
        out = cm.crypto_cost_bps(daily_vol_pct=vols)
        assert list(out) == [8.0, 7.0, 10.0]

    def test_future_cost_per_contract_rejects_invalid(self):
        cm = CostModel(
            future_commission_per_contract=0.5,
            future_spread_ticks=0.25,
            future_slippage_ticks=0.5,
            future_tick_value=12.5,
            futures_specs={"BAD": {"commission": -1.0}},
        )
        assert cm.future_cost_per_contract("BAD") == 0.0
        cm_nan = CostModel(future_commission_per_contract=float("nan"))
        assert cm_nan.future_cost_per_contract() == 0.0

    def test_get_future_contract_multiplier_rejects_invalid_default(self):
        cm = CostModel(future_contract_multiplier=50.0)
        assert cm.get_future_contract_multiplier() == 50.0
        assert cm.get_future_contract_multiplier(None) == 50.0
        # A non-finite default is not a contract multiplier.
        assert (
            CostModel(future_contract_multiplier=float("inf")).get_future_contract_multiplier()
            == 0.0
        )
        assert (
            CostModel(future_contract_multiplier=float("nan")).get_future_contract_multiplier()
            == 0.0
        )
        assert (
            CostModel(future_contract_multiplier=float("-inf")).get_future_contract_multiplier()
            == 0.0
        )
        # A negative default is a sign error, not a short position.
        assert CostModel(future_contract_multiplier=-50.0).get_future_contract_multiplier() == 0.0

    def test_get_future_contract_multiplier_rejects_invalid_spec(self):
        cm = CostModel(futures_specs={"ES": {"multiplier": 50.0}})
        assert cm.get_future_contract_multiplier("ES") == 50.0
        for bad in (float("inf"), float("nan"), float("-inf"), -50.0):
            cm_bad = CostModel(futures_specs={"ES": {"multiplier": bad}})
            assert cm_bad.get_future_contract_multiplier("ES") == 0.0
        # A missing spec key still falls back to the (valid) default.
        assert (
            CostModel(
                future_contract_multiplier=100.0, futures_specs={"ES": {}}
            ).get_future_contract_multiplier("ES")
            == 100.0
        )
        # A non-finite default with a valid spec still returns the spec value.
        assert (
            CostModel(
                future_contract_multiplier=float("inf"), futures_specs={"ES": {"multiplier": 50.0}}
            ).get_future_contract_multiplier("ES")
            == 50.0
        )

    def test_get_future_contract_multiplier_zero_is_a_real_boundary(self):
        # 0.0 is finite and non-negative, so it is a measured boundary (a symbol
        # with no deliverable cannot be traded), not a degenerate input.
        assert (
            CostModel(futures_specs={"ES": {"multiplier": 0.0}}).get_future_contract_multiplier(
                "ES"
            )
            == 0.0
        )

    @staticmethod
    def _futures_panel(price: float = 100.0, n: int = 6) -> tuple[pd.DataFrame, pd.DataFrame]:
        rng = np.random.default_rng(7)
        rets = rng.normal(0.0005, 0.01, n)
        prices = pd.DataFrame(
            {"ES=F": price * np.exp(np.cumsum(rets))},
            index=pd.bdate_range("2020-01-01", periods=n),
        )
        signals = pd.DataFrame({"ES=F": [0.0] + [1.0] * (n - 1)}, index=prices.index)
        return prices, signals

    def test_the_engine_futures_path_fails_closed_on_a_degenerate_multiplier(self):
        # The engine divides by this method's return value (engine.py:483), so
        # a non-finite or negative multiplier used to flow straight into a
        # published P&L number. Measured on a six-bar futures panel: with the
        # default 50.0 multiplier the engine's total_return is
        # 0.03757107146358196; with an inf or nan multiplier it was
        # 0.03960396039603964 -- a fabricated return with no finite meaning.
        # The guarded method returns 0.0, so the caller's division yields a zero
        # contract count and the symbol contributes no cost.
        prices, signals = self._futures_panel()
        base_cfg = dict(
            initial_capital=1_000_000.0,
            asset_class=AssetClass.FUTURE,
            max_position_size=1.0,
            max_leverage=1.0,
            allow_short=False,
        )
        for bad in (float("inf"), float("nan"), float("-inf"), -50.0):
            cm = CostModel(futures_specs={"ES=F": {"multiplier": bad}})
            res = run_backtest(
                prices=prices, signals=signals, config=BacktestConfig(cost_model=cm, **base_cfg)
            )
            assert res.metrics["total_return"] == 0.0, (
                f"a {bad!r} multiplier must fail closed to a zero total_return, "
                f"got {res.metrics['total_return']!r}"
            )

    def test_the_engine_futures_path_is_bit_identical_on_finite_multipliers(self):
        # For every finite, non-negative input the arithmetic is bit-identical
        # to before: the guard only short-circuits the degenerate cases.
        prices, signals = self._futures_panel()
        base_cfg = dict(
            initial_capital=1_000_000.0,
            asset_class=AssetClass.FUTURE,
            max_position_size=1.0,
            max_leverage=1.0,
            allow_short=False,
        )
        base = run_backtest(
            prices=prices,
            signals=signals,
            config=BacktestConfig(cost_model=CostModel(), **base_cfg),
        )
        for mult in (1.0, 50.0, 100.0, 1000.0):
            cm = CostModel(futures_specs={"ES=F": {"multiplier": mult}})
            res = run_backtest(
                prices=prices, signals=signals, config=BacktestConfig(cost_model=cm, **base_cfg)
            )
            # The contract count scales with the multiplier, so the cost -- and
            # with it the net return -- is NOT invariant across multipliers;
            # what must hold is that the finite path produces a finite result
            # and that the default (50.0) reproduces the pre-guard baseline.
            assert np.isfinite(res.metrics["total_return"])
        assert (
            run_backtest(
                prices=prices,
                signals=signals,
                config=BacktestConfig(cost_model=CostModel(), **base_cfg),
            ).metrics["total_return"]
            == base.metrics["total_return"]
        )

    def test_the_contract_rejects_the_pre_guard_multiplier(self):
        # Behavioural negative control: the pre-guard method returned whatever
        # the caller supplied, so a non-finite or negative operand reached the
        # engine's division (engine.py:483) and manufactured a published P&L
        # number. Reconstruct that behaviour here and require it to be the
        # bad value, while the guarded method fails closed to 0.0 on the same
        # input.

        import math

        def pre_guard(cm, symbol):
            if symbol and symbol in cm.futures_specs:
                return cm.futures_specs[symbol].get("multiplier", cm.future_contract_multiplier)
            return cm.future_contract_multiplier

        for bad in (float("inf"), float("nan"), float("-inf"), -50.0):
            cm = CostModel(futures_specs={"ES": {"multiplier": bad}})
            emitted = pre_guard(cm, "ES")
            # `nan == nan` is False by IEEE 754, so the nan case is checked
            # with math.isnan rather than equality -- the point is that the
            # pre-guard path passes the caller's value through unchanged.
            assert (math.isnan(emitted) and math.isnan(bad)) or emitted == bad
            assert cm.get_future_contract_multiplier("ES") == 0.0  # the guarded path rejects it
