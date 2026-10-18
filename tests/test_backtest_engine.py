"""
Regression tests for the vectorized backtesting engine
(src/qtr/backtest/engine.py).

Pins down the engine invariants that the H1/H2/H3 experiments depend on:
leverage normalization, position-size caps, short-sale clipping,
trade extraction, metric computation, and the absence of look-ahead
(signals at time t earn returns from t+1 onward).
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
    BacktestResult,
    CostModel,
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


# ============================================================
# Constraint enforcement
# ============================================================
class TestConstraints:
    def test_leverage_normalization(self):
        """Gross leverage must be normalized down to max_leverage."""
        prices = _make_prices(symbols=("A", "B"))
        signals = pd.DataFrame(
            2.0, index=prices.index, columns=prices.columns
        )  # gross = 4
        cfg = _make_config(max_leverage=1.0)
        res = run_backtest(prices=prices, signals=signals, config=cfg)
        gross = res.positions.abs().sum(axis=1)
        assert (gross <= 1.0 + 1e-12).all()

    def test_leverage_not_normalized_when_within_limit(self):
        prices = _make_prices(symbols=("A", "B"))
        signals = pd.DataFrame(
            0.25, index=prices.index, columns=prices.columns
        )  # gross = 0.5
        cfg = _make_config(max_leverage=1.0)
        res = run_backtest(prices=prices, signals=signals, config=cfg)
        gross = res.positions.abs().sum(axis=1)
        assert np.allclose(gross.values, 0.5)

    def test_max_position_size_cap(self):
        prices = _make_prices(symbols=("A",))
        signals = pd.DataFrame(5.0, index=prices.index, columns=prices.columns)
        cfg = _make_config(max_position_size=0.5, max_leverage=2.0)
        res = run_backtest(prices=prices, signals=signals, config=cfg)
        assert (res.positions.abs() <= 0.5 + 1e-12).all().all()

    def test_no_short_clips_negative_positions(self):
        prices = _make_prices(symbols=("A", "B"))
        signals = pd.DataFrame({"A": -1.0, "B": 1.0}, index=prices.index)
        cfg = _make_config(allow_short=False)
        res = run_backtest(prices=prices, signals=signals, config=cfg)
        assert (res.positions >= -1e-12).all().all()

    def test_shorts_allowed_when_configured(self):
        prices = _make_prices(symbols=("A", "B"))
        signals = pd.DataFrame({"A": -0.5, "B": 0.5}, index=prices.index)
        cfg = _make_config(allow_short=True, max_leverage=1.0)
        res = run_backtest(prices=prices, signals=signals, config=cfg)
        assert np.allclose(res.positions["A"].values, -0.5)
        assert np.allclose(res.positions["B"].values, 0.5)


# ============================================================
# Look-ahead safety
# ============================================================
class TestLookAheadSafety:
    def test_signal_earns_from_next_period(self):
        """Position established on day 0 must earn the day-1 return,
        not the day-0 return (engine applies signals.shift(1))."""
        prices = _make_prices(symbols=("A",))
        signals = pd.DataFrame({"A": 0.0}, index=prices.index)
        signals.iloc[0] = 1.0
        cfg = _make_config()  # zero costs
        res = run_backtest(prices=prices, signals=signals, config=cfg)
        asset_ret = prices["A"].pct_change().fillna(0)
        assert res.returns.iloc[0] == pytest.approx(0.0)  # day 0: no exposure yet
        assert res.returns.iloc[1] == pytest.approx(asset_ret.iloc[1])

    def test_flat_signals_give_zero_returns(self):
        prices = _make_prices(symbols=("A", "B"))
        signals = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
        res = run_backtest(prices=prices, signals=signals, config=_make_config())
        assert np.allclose(res.returns.values, 0.0)
        assert np.allclose(res.equity_curve.values, 1_000_000.0)


# ============================================================
# Returns / equity / trades
# ============================================================
class TestReturnsAndTrades:
    def test_buy_and_hold_matches_asset_returns(self):
        prices = _make_prices(symbols=("A",))
        signals = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)
        res = run_backtest(prices=prices, signals=signals, config=_make_config())
        asset_ret = prices["A"].pct_change().fillna(0)
        assert np.allclose(res.returns.values, asset_ret.values, atol=1e-12)

    def test_trade_extraction_counts_position_changes(self):
        prices = _make_prices(symbols=("A",))
        # NaN between target-weight changes: the engine ffill's signals,
        # so the position holds until the next explicit target weight.
        signals = pd.DataFrame({"A": np.nan}, index=prices.index)
        signals.iloc[0] = 1.0
        signals.iloc[50] = 0.0  # exit
        signals.iloc[70] = 0.5  # re-enter half
        res = run_backtest(prices=prices, signals=signals, config=_make_config())
        # nonzero position changes: day 0 (1.0), day 50 (-1.0), day 70 (+0.5)
        assert len(res.trades) == 3
        assert list(res.trades["side"]) == ["buy", "sell", "buy"]
        # position holds at 0.5 after day 70 (ffill)
        assert np.allclose(res.positions["A"].iloc[70:].values, 0.5)

    def test_equity_curve_compounds_net_returns(self):
        prices = _make_prices(symbols=("A",))
        signals = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)
        res = run_backtest(prices=prices, signals=signals, config=_make_config())
        expected = 1_000_000.0 * (1 + res.returns).cumprod()
        assert np.allclose(res.equity_curve.values, expected.values, rtol=1e-10)

    def test_result_contains_all_fields(self):
        prices = _make_prices(symbols=("A",))
        signals = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)
        res = run_backtest(prices=prices, signals=signals, config=_make_config())
        assert isinstance(res, BacktestResult)
        assert isinstance(res.equity_curve, pd.Series)
        assert isinstance(res.returns, pd.Series)
        assert isinstance(res.positions, pd.DataFrame)
        assert isinstance(res.trades, pd.DataFrame)
        assert isinstance(res.metrics, dict)
        assert "sharpe" in res.metrics and "max_drawdown" in res.metrics


# ============================================================
# Metrics
# ============================================================
class TestMetrics:
    def test_sharpe_of_zero_returns_is_zero(self):
        prices = _make_prices(symbols=("A",))
        signals = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
        res = run_backtest(prices=prices, signals=signals, config=_make_config())
        assert res.metrics["sharpe"] == 0.0

    def test_positive_sharpe_for_trending_asset(self):
        rng = np.random.default_rng(3)
        index = pd.bdate_range("2020-01-01", periods=252)
        prices = pd.DataFrame(
            {"A": np.cumsum(rng.normal(0.001, 0.005, 252)) + 100.0}, index=index
        )
        signals = pd.DataFrame(1.0, index=index, columns=["A"])
        res = run_backtest(prices=prices, signals=signals, config=_make_config())
        assert res.metrics["sharpe"] > 0

    def test_max_drawdown_known_series(self):
        # Build prices with a known -20% peak-to-trough path.
        index = pd.bdate_range("2020-01-01", periods=5)
        # prices: 100 -> 120 (peak) -> 96 (-20% from peak)
        prices = pd.DataFrame({"A": [100.0, 110.0, 120.0, 108.0, 96.0]}, index=index)
        signals = pd.DataFrame(1.0, index=index, columns=["A"])
        res = run_backtest(prices=prices, signals=signals, config=_make_config())
        assert res.metrics["max_drawdown"] == pytest.approx(-0.20, abs=1e-9)

    def test_profit_factor_all_gains_is_inf(self):
        rng = np.random.default_rng(5)
        index = pd.bdate_range("2020-01-01", periods=100)
        prices = pd.DataFrame(
            {"A": np.cumsum(rng.normal(0.002, 0.001, 100)) + 100.0}, index=index
        )
        signals = pd.DataFrame(1.0, index=index, columns=["A"])
        res = run_backtest(prices=prices, signals=signals, config=_make_config())
        assert res.metrics["profit_factor"] == np.inf

    def test_sortino_uses_downside_deviation_not_loss_std(self):
        """Regression: the Sortino denominator must be the *downside
        deviation* sqrt(mean(min(0, r - target)^2)), not the standard
        deviation of the negative-returns subset. The two differ whenever
        the series contains zero or positive months, because the loss-subset
        std ignores those observations entirely while the downside
        deviation counts a 0 shortfall for each one (raising the
        denominator and lowering the ratio). The prior implementation used
        `returns[returns < 0].std()`, which understated downside risk and
        inflated the Sortino ratio.
        """
        rng = np.random.default_rng(11)
        n = 252
        # Mix of gains, losses, and zeros so the two denominators differ.
        base = rng.normal(0.0004, 0.01, n)
        base[::5] = 0.0  # every 5th month is flat -> 0 shortfall
        index = pd.bdate_range("2020-01-01", periods=n)
        prices = pd.DataFrame({"A": 100.0 * np.exp(np.cumsum(base))}, index=index)
        signals = pd.DataFrame(1.0, index=index, columns=["A"])
        res = run_backtest(prices=prices, signals=signals, config=_make_config())

        # The engine reports *net* returns (after zero-cost subtraction here),
        # so compute the expected Sortino from the actual returned series.
        returns = res.returns.values
        ann_factor = 252
        target = 0.0  # risk_free = 0.0 in _make_config
        shortfall = np.minimum(0, returns - target)
        downside_dev = np.sqrt(np.mean(shortfall**2))
        loss_std = returns[returns < 0].std()
        expected = returns.mean() / downside_dev * np.sqrt(ann_factor)

        assert downside_dev > 0
        assert downside_dev != pytest.approx(loss_std, rel=1e-6)
        assert res.metrics["sortino"] == pytest.approx(expected, rel=1e-9)

    def test_sortino_zero_when_no_downside(self):
        """All-positive returns => downside deviation 0 => Sortino 0."""
        rng = np.random.default_rng(7)
        index = pd.bdate_range("2020-01-01", periods=100)
        prices = pd.DataFrame(
            {"A": np.cumsum(np.abs(rng.normal(0.002, 0.001, 100))) + 100.0},
            index=index,
        )
        signals = pd.DataFrame(1.0, index=index, columns=["A"])
        res = run_backtest(prices=prices, signals=signals, config=_make_config())
        assert res.metrics["sortino"] == 0.0

    def test_num_trades_metric(self):
        prices = _make_prices(symbols=("A",))
        signals = pd.DataFrame({"A": np.nan}, index=prices.index)
        signals.iloc[0] = 1.0
        signals.iloc[10] = 0.0
        res = run_backtest(prices=prices, signals=signals, config=_make_config())
        assert res.metrics["num_trades"] == 2


# ============================================================
# Futures / crypto cost paths (engine-level smoke tests)
# ============================================================
class TestOtherAssetClasses:
    def test_future_cost_path_runs(self):
        prices = _make_prices(symbols=("ES",))
        signals = pd.DataFrame({"ES": 0.0}, index=prices.index)
        signals.iloc[0] = 1.0
        cfg = _make_config(
            asset_class=AssetClass.FUTURE, max_leverage=5.0, max_position_size=5.0
        )
        cfg.cost_model.future_commission_per_contract = 0.50
        cfg.cost_model.future_contract_multiplier = 50.0  # ES multiplier
        res = run_backtest(prices=prices, signals=signals, config=cfg)
        # day-0 cost = weight_change * capital / (price * multiplier) * contract_cost / capital
        # = 1.0 * 1M / (price * 50) * $9.875 / 1M = contract_cost / (price * 50)
        price_0 = prices["ES"].iloc[0]
        contract_cost = 0.50 + (0.25 + 0.5) * 12.50  # $9.875
        expected_cost = contract_cost / (price_0 * 50)
        assert res.returns.iloc[0] == pytest.approx(-expected_cost, abs=1e-12)

    def test_future_cost_path_scales_with_multiplier(self):
        """Cost should be inversely proportional to contract multiplier."""
        prices = _make_prices(symbols=("ES",))
        signals = pd.DataFrame({"ES": 0.0}, index=prices.index)
        signals.iloc[0] = 1.0

        cfg1 = _make_config(
            asset_class=AssetClass.FUTURE, max_leverage=5.0, max_position_size=5.0
        )
        cfg1.cost_model.future_commission_per_contract = 0.50
        cfg1.cost_model.future_contract_multiplier = 50.0
        res1 = run_backtest(prices=prices, signals=signals, config=cfg1)

        cfg2 = _make_config(
            asset_class=AssetClass.FUTURE, max_leverage=5.0, max_position_size=5.0
        )
        cfg2.cost_model.future_commission_per_contract = 0.50
        cfg2.cost_model.future_contract_multiplier = (
            100.0  # 2x multiplier -> 1/2 contracts
        )
        res2 = run_backtest(prices=prices, signals=signals, config=cfg2)

        # Double multiplier should halve the cost (and thus halve the negative return)
        assert res2.returns.iloc[0] == pytest.approx(
            res1.returns.iloc[0] / 2, abs=1e-12
        )

    def test_future_cost_path_scales_with_weight(self):
        """Cost should scale linearly with position weight change."""
        prices = _make_prices(symbols=("ES",))
        signals = pd.DataFrame({"ES": 0.0}, index=prices.index)
        signals.iloc[0] = 2.0  # 2x weight

        cfg = _make_config(
            asset_class=AssetClass.FUTURE, max_leverage=5.0, max_position_size=5.0
        )
        cfg.cost_model.future_commission_per_contract = 0.50
        cfg.cost_model.future_contract_multiplier = 50.0
        res = run_backtest(prices=prices, signals=signals, config=cfg)

        # Compare to 1.0 weight
        prices1 = _make_prices(symbols=("ES",))
        signals1 = pd.DataFrame({"ES": 0.0}, index=prices1.index)
        signals1.iloc[0] = 1.0
        res1 = run_backtest(prices=prices1, signals=signals1, config=cfg)

        assert res.returns.iloc[0] == pytest.approx(2 * res1.returns.iloc[0], abs=1e-12)

    def test_crypto_cost_path_runs(self):
        prices = _make_prices(symbols=("BTC",))
        signals = pd.DataFrame({"BTC": 0.0}, index=prices.index)
        signals.iloc[0] = 1.0
        cfg = _make_config(
            asset_class=AssetClass.CRYPTO, max_leverage=5.0, max_position_size=5.0
        )
        res = run_backtest(prices=prices, signals=signals, config=cfg)
        # default crypto cost: 5 + 2 + 0 = 7 bps
        assert res.returns.iloc[0] == pytest.approx(-7.0 / 10_000, abs=1e-12)

    def test_future_cost_with_per_symbol_specs(self):
        """Per-symbol futures specs override global defaults."""
        prices = _make_prices(symbols=("ES",))
        signals = pd.DataFrame({"ES": 0.0}, index=prices.index)
        signals.iloc[0] = 1.0
        cfg = _make_config(
            asset_class=AssetClass.FUTURE, max_leverage=5.0, max_position_size=5.0
        )
        cfg.cost_model.futures_specs = {
            "ES": {
                "multiplier": 100.0,
                "tick_value": 25.0,
                "spread_ticks": 0.25,
                "slippage_ticks": 0.5,
                "commission": 1.0,
            }
        }
        res = run_backtest(prices=prices, signals=signals, config=cfg)
        price_es = prices["ES"].iloc[0]
        expected_es = (1.0 + (0.25 + 0.5) * 25.0) / (price_es * 100.0)
        assert res.returns.iloc[0] == pytest.approx(-expected_es, abs=1e-12)


def test_volumes_and_adv_paths():
    """Test when volumes provided and ADV provided in various forms."""
    np.random.seed(123)
    idx = pd.date_range("2020-01-01", periods=50, freq="D")
    prices = pd.DataFrame(
        {"AAPL": np.cumsum(np.random.randn(50) * 0.01) + 100}, index=idx
    )
    signals = pd.DataFrame({"AAPL": 0.0}, index=idx)
    signals.iloc[5] = 0.5
    volumes = pd.DataFrame({"AAPL": 1000000}, index=idx)
    adv = pd.Series({"AAPL": 2000000})
    cfg = _make_config(
        asset_class=AssetClass.EQUITY, max_leverage=2.0, max_position_size=2.0
    )
    res = run_backtest(
        prices=prices, signals=signals, volumes=volumes, adv=adv, config=cfg
    )
    assert res is not None


def test_adv_series_contains_symbol():
    np.random.seed(123)
    idx = pd.date_range("2020-01-01", periods=30, freq="D")
    prices = pd.DataFrame({"A": np.cumsum(np.random.randn(30) * 0.01) + 100}, index=idx)
    signals = pd.DataFrame({"A": 0.0}, index=idx)
    signals.iloc[2] = 1.0
    adv = pd.Series({"A": 1000000})
    cfg = _make_config(asset_class=AssetClass.EQUITY)
    res = run_backtest(prices=prices, signals=signals, adv=adv, config=cfg)
    assert res.returns.iloc[2] <= 0


def test_adv_zero_skips_impact():
    np.random.seed(123)
    idx = pd.date_range("2020-01-01", periods=30, freq="D")
    prices = pd.DataFrame({"A": np.cumsum(np.random.randn(30) * 0.01) + 100}, index=idx)
    signals = pd.DataFrame({"A": 0.0}, index=idx)
    signals.iloc[2] = 1.0
    adv = pd.Series({"A": 0.0})
    cfg = _make_config(asset_class=AssetClass.EQUITY)
    res = run_backtest(prices=prices, signals=signals, adv=adv, config=cfg)
    assert res is not None


def test_crypto_also_uses_weight_changes():
    np.random.seed(123)
    idx = pd.date_range("2020-01-01", periods=40, freq="D")
    prices = pd.DataFrame(
        {"BTC": np.cumsum(np.random.randn(40) * 0.01) + 20000}, index=idx
    )
    signals = pd.DataFrame({"BTC": 0.0}, index=idx)
    signals.iloc[3] = 0.3
    cfg = _make_config(asset_class=AssetClass.CRYPTO)
    res = run_backtest(prices=prices, signals=signals, config=cfg)
    assert res.returns.iloc[3] < 0


def test_unknown_asset_class_zero_costs():
    """The cost-model fallback for an unrecognised asset class must be a
    no-op (zero costs), so a misconfigured asset class degrades to a
    frictionless backtest rather than crashing."""
    prices = _make_prices(symbols=("A",))
    signals = pd.DataFrame({"A": 0.0}, index=prices.index)
    signals.iloc[0] = 1.0
    cfg = _make_config()
    # Bypass the Enum by setting an unrecognised string directly.
    cfg.asset_class = "unknown"  # type: ignore[assignment]
    res = run_backtest(prices=prices, signals=signals, config=cfg)
    # Zero-cost fallback must match the zero-cost equity path exactly.
    cfg_ref = _make_config()  # equity with zero commission/spread/impact
    res_ref = run_backtest(prices=prices, signals=signals, config=cfg_ref)
    assert np.allclose(res.returns.values, res_ref.returns.values, atol=1e-12)
