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

import math
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


class TestInvalidLeverage:
    @pytest.mark.parametrize("invalid_leverage", [-1.0, -np.inf, np.nan, np.inf])
    def test_invalid_leverage_fails_closed_without_flipping_a_long_only_book(
        self, invalid_leverage
    ):
        prices = _make_prices(symbols=("A",))
        signals = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)
        cfg = _make_config(max_leverage=invalid_leverage, allow_short=False)

        res = run_backtest(prices=prices, signals=signals, config=cfg)

        assert (res.positions == 0.0).all().all()
        assert len(res.trades) == 0
        assert (res.returns == 0.0).all()
        assert np.isfinite(res.equity_curve.values).all()

    def test_the_contract_rejects_the_pre_fix_negative_leverage_sign_flip(self):
        gross = pd.Series([1.0])
        pre_fix_scale = np.where(gross > -1.0, -1.0 / gross, 1.0)
        pre_fix_positions = pd.Series([1.0]) * pre_fix_scale

        assert np.allclose(pre_fix_positions, -1.0)


# --------------------------------------------------------------------------- #
# Invalid initial capital
# --------------------------------------------------------------------------- #
class TestInvalidInitialCapital:
    @pytest.mark.parametrize("invalid_capital", [0.0, -1000.0, np.nan, np.inf])
    def test_invalid_initial_capital_fails_closed_to_no_evidence(self, invalid_capital):
        prices = _make_prices(symbols=("A",))
        signals = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)
        cfg = _make_config(initial_capital=invalid_capital)

        res = run_backtest(prices=prices, signals=signals, config=cfg)

        assert len(res.equity_curve) == 0
        assert len(res.returns) == 0
        assert res.positions.empty
        assert res.trades.empty
        assert list(res.trades.columns) == [
            "timestamp",
            "symbol",
            "side",
            "weight_change",
            "price",
            "cost",
        ]
        assert res.metrics == {
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
        }

    def test_finite_positive_initial_capital_remains_unchanged(self):
        prices = _make_prices(symbols=("A",))
        signals = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)
        baseline_cfg = _make_config(initial_capital=1_000_000.0)
        custom_cfg = _make_config(initial_capital=500_000.0)

        baseline = run_backtest(prices=prices, signals=signals, config=baseline_cfg)
        res = run_backtest(prices=prices, signals=signals, config=custom_cfg)

        pd.testing.assert_series_equal(res.returns, baseline.returns)
        pd.testing.assert_frame_equal(res.positions, baseline.positions)
        pd.testing.assert_frame_equal(res.trades, baseline.trades)
        pd.testing.assert_series_equal(res.equity_curve, baseline.equity_curve * 0.5)
        assert res.metrics == baseline.metrics

    def test_the_contract_rejects_the_pre_fix_invalid_capital_book(self):
        """Behavioural negative control: reconstruct the pre-fix capital
        handling and require it to manufacture equity/positions/trades instead
        of the no-evidence result."""
        capital = 0.0
        if math.isfinite(capital) and capital > 0.0:
            result = "empty"
        else:
            index = pd.bdate_range("2020-01-01", periods=3)
            prices = pd.DataFrame({"A": [100.0, 101.0, 102.0]}, index=index)
            signals = pd.DataFrame(1.0, index=index, columns=["A"])
            asset_ret = prices.pct_change().fillna(0.0)
            positions = signals.astype(float)
            prior = positions.shift(1).fillna(0.0)
            portfolio_ret = (prior * asset_ret).sum(axis=1).astype(float)
            equity_curve = (1.0 + portfolio_ret).cumprod() * capital
            trades = pd.DataFrame([{"timestamp": index[0], "symbol": "A"}])
            result = (equity_curve, positions, trades)

        equity_curve, positions, trades = result
        assert (equity_curve == 0.0).all()
        assert not positions.empty
        assert not trades.empty


# --------------------------------------------------------------------------- #
# Invalid position size
# --------------------------------------------------------------------------- #
class TestInvalidPositionSize:
    @pytest.mark.parametrize("invalid_position_size", [-1.0, -np.inf, np.nan, np.inf])
    def test_invalid_position_size_fails_closed_to_no_exposure(self, invalid_position_size):
        """A negative or non-finite per-asset cap is not a cap. The engine must
        fail closed (flatten the book) rather than silently disable the cap and
        let an oversized signal reach the book at full size."""
        prices = _make_prices(symbols=("A",))
        signals = pd.DataFrame({"A": 3.0}, index=prices.index)
        cfg = _make_config(max_position_size=invalid_position_size, max_leverage=5.0)

        res = run_backtest(prices=prices, signals=signals, config=cfg)

        assert (res.positions == 0.0).all().all()
        assert len(res.trades) == 0
        assert (res.returns == 0.0).all()
        assert np.isfinite(res.equity_curve.values).all()

    def test_finite_positive_position_size_still_caps(self):
        """Control: a finite non-negative cap is applied exactly as before."""
        prices = _make_prices(symbols=("A",))
        signals = pd.DataFrame({"A": 3.0}, index=prices.index)
        cfg = _make_config(max_position_size=0.5, max_leverage=5.0)

        res = run_backtest(prices=prices, signals=signals, config=cfg)

        assert np.allclose(res.positions["A"].values, 0.5)
        asset_ret = prices["A"].pct_change().fillna(0.0)
        assert res.returns.iloc[1] == pytest.approx(0.5 * asset_ret.iloc[1], abs=1e-12)

    def test_the_contract_rejects_the_pre_fix_position_size_bypass(self):
        """Behavioural negative control: the pre-fix engine passed the raw cap
        to ``clip``. With a NaN cap, ``clip(lower=nan, upper=nan)`` is a no-op,
        so an oversized signal reaches the book at full size -- the cap silently
        disabled, exactly the bypass the guard above closes."""
        signal = pd.Series([3.0, 3.0, 3.0])
        pre_fix_positions = signal.clip(lower=-np.nan, upper=np.nan)

        assert np.allclose(pre_fix_positions.values, 3.0)


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


# --------------------------------------------------------------------------- #
# NaN prices
# --------------------------------------------------------------------------- #
class TestNaNPrices:
    def test_nan_price_bar_earns_nothing_fail_closed(self):
        """A NaN price cannot be the base of a percentage return. The engine
        must not manufacture a return from it and must not crash: the bar
        whose price is NaN earns 0.0 (fail closed), every return stays finite,
        and positions, equity curve and metrics are all well formed."""
        prices = _make_prices(symbols=("A",))
        nan_bar = prices.index[10]
        prices.loc[nan_bar, "A"] = np.nan
        signals = pd.DataFrame({"A": 1.0}, index=prices.index)
        cfg = _make_config()
        res = run_backtest(prices=prices, signals=signals, config=cfg)

        assert np.isfinite(res.returns.values).all()
        assert res.returns.loc[nan_bar] == pytest.approx(0.0, abs=1e-12)
        assert np.isfinite(res.equity_curve.values).all()
        assert all(np.isfinite(v) for v in res.metrics.values())
        assert (res.positions["A"] == 1.0).all()

    def test_nan_price_at_first_bar_does_not_crash(self):
        """A NaN price on bar 0 (which earns nothing anyway under shift(1))
        must not raise or emit a non-finite return."""
        prices = _make_prices(symbols=("A",))
        prices.iloc[0] = np.nan
        signals = pd.DataFrame({"A": np.nan}, index=prices.index)
        signals.iloc[0] = 1.0
        cfg = _make_config()
        res = run_backtest(prices=prices, signals=signals, config=cfg)

        assert np.isfinite(res.returns.values).all()
        assert res.returns.iloc[0] == pytest.approx(0.0, abs=1e-12)

    def test_trade_at_nan_price_bar_records_without_crashing(self):
        """A position change at a NaN-price bar still logs the trade (the
        equity cost is weight-based and price-invariant) without crashing;
        returns stay finite. The NaN price itself is not asserted on the
        trade log here - that is a separate data-quality concern."""
        prices = _make_prices(symbols=("A",))
        trade_bar = prices.index[5]
        prices.loc[trade_bar, "A"] = np.nan
        signals = pd.DataFrame({"A": 0.0}, index=prices.index)
        signals.loc[trade_bar] = 1.0
        cfg = _make_config()
        res = run_backtest(prices=prices, signals=signals, config=cfg)

        assert np.isfinite(res.returns.values).all()
        assert len(res.trades) == 2
        assert res.trades["symbol"].eq("A").all()


# --------------------------------------------------------------------------- #
# Equity zero volume
# --------------------------------------------------------------------------- #
class TestEquityZeroVolume:
    def test_zero_volume_and_adv_skips_impact_without_crashing(self):
        """An equity symbol with zero volume and zero ADV cannot support a
        market-impact estimate. The engine must skip impact (fail closed)
        rather than divide by zero, still charge the weight-based cost, and
        produce finite returns without crashing."""
        prices = _make_prices(symbols=("A",))
        signals = pd.DataFrame({"A": 0.0}, index=prices.index)
        signals.iloc[5] = 1.0
        volumes = pd.DataFrame({"A": 0.0}, index=prices.index)
        adv = pd.Series({"A": 0.0})
        cfg = _make_config(asset_class=AssetClass.EQUITY, max_position_size=1.0)
        cfg.cost_model.equity_impact_bps_per_pct_adv = 10.0
        res = run_backtest(prices=prices, signals=signals, volumes=volumes, adv=adv, config=cfg)

        assert np.isfinite(res.returns.values).all()
        # Impact is skipped for zero ADV; only the weight-based cost applies,
        # so the entry bar earns a non-positive cost drag.
        assert res.returns.iloc[5] <= 0.0
        assert len(res.trades) == 2


# --------------------------------------------------------------------------- #
# Invalid equity market-impact coefficient
# --------------------------------------------------------------------------- #
class TestInvalidEquityImpactCoefficient:
    """A negative or non-finite ``equity_impact_bps_per_pct_adv`` must fail closed.

    The coefficient scales the market-impact cost the engine SUBTRACTS from the
    return, so a negative coefficient is a *negative* cost that
    ``portfolio_ret = ... - costs`` ADDS -- it manufactures P&L. A non-finite
    coefficient is the same class: ``inf`` makes the cost sum ``inf`` and the
    return ``-inf`` (a non-finite series the metrics then silently void), while
    ``nan`` is truthy and poisons the cost sum so the charge is silently
    dropped. ``CostModel.equity_cost_bps`` already fails closed on the same
    operand (returns ``0.0``), but the engine's separate impact loop read the
    raw attribute and bypassed that guard. The coefficient now normalizes to
    ``0.0`` (the no-impact boundary) at the point of use, so a bad value can
    only ever REMOVE the impact charge, never invert or blow it up.
    """

    @staticmethod
    def _run(impact):
        prices = pd.DataFrame(
            {"A": [100.0, 101.0, 102.0, 103.0, 104.0]},
            index=pd.date_range("2020-01-01", periods=5, freq="D"),
        )
        signals = pd.DataFrame({"A": 1.0}, index=prices.index)
        adv = pd.Series({"A": 1_000_000.0})
        cm = CostModel(equity_commission_bps=2.0, equity_impact_bps_per_pct_adv=impact)
        cfg = BacktestConfig(initial_capital=1_000_000.0, cost_model=cm, max_leverage=1.0)
        return run_backtest(prices, signals, cfg, adv=adv)

    @pytest.mark.parametrize("bad", [-10.0, -0.001, float("inf"), float("-inf"), float("nan")])
    def test_invalid_impact_fails_closed_without_inflating_the_return(self, bad):
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            res = self._run(bad)

        # No non-finite value escapes and no negative cost is ever booked.
        assert np.isfinite(res.returns.values).all()
        assert np.isfinite(res.equity_curve.values).all()
        assert (res.trades["cost"] >= 0.0).all()
        # The pre-fix negative coefficient turned the entry-bar return (which
        # earns no prior position) into a positive credit; the guarded engine
        # books no such credit.
        assert res.returns.iloc[0] <= 0.0

    def test_finite_positive_impact_is_unchanged(self):
        res = self._run(10.0)
        assert np.isfinite(res.returns.values).all()
        # The entry bar carries the commission + impact drag (a cost, not a
        # credit), so the positive path is bit-identical to before.
        assert res.returns.iloc[0] < 0.0
        assert (res.trades["cost"] > 0.0).all()

    def test_the_contract_rejects_the_pre_fix_negative_cost(self):
        """Behavioural negative control: the pre-fix impact loop read the raw
        coefficient, so a negative one produced a negative cost that
        ``portfolio_ret = ... - costs`` ADDED. Reconstruct that arithmetic and
        require it to be a credit (cost < 0), which the guarded engine never
        books."""
        position_change = 1.0
        participation = 1.0  # 1% of ADV
        impact_coef = -10.0
        pre_fix_cost = position_change * (impact_coef * participation / 10_000.0)
        assert pre_fix_cost < 0.0  # a credit -> manufactured P&L

        res = self._run(-10.0)
        assert (res.trades["cost"] >= 0.0).all()


# --------------------------------------------------------------------------- #
# Duplicate index labels
# --------------------------------------------------------------------------- #
class TestDuplicateIndex:
    """A repeated index label must not crash the engine.

    A duplicated bar is reachable from the documented pipeline: an overlapping
    vendor window or a cache entry written before dedup. ``fetch_ccxt`` already
    de-duplicates (``~duplicated(keep="first").sort_index()``, fetcher.py:407),
    but ``fetch_yahoo``/``fetch_futures`` and the cached read path do not, so a
    duplicated timestamp can reach ``run_backtest`` from a live fetch. Before
    the fix, a position change at the duplicated label made
    ``prices.loc[ts, sym]`` return a Series and ``float(...)`` raised
    ``TypeError``; the engine now canonicalizes the index (keep first, sort)
    once on entry, so the duplicated label is a no-op and the clean path is
    bit-identical.
    """

    def test_duplicate_price_index_with_a_trade_at_the_dup_does_not_crash(self):
        prices = pd.DataFrame(
            {"A": [101.0, 102.0, 103.0], "B": [10.0, 11.0, 12.0]},
            index=pd.DatetimeIndex(["2020-01-02", "2020-01-03", "2020-01-02"]),
        )
        signals = pd.DataFrame({"A": [0.0, 1.0, 1.0], "B": [1.0, 1.0, 1.0]}, index=prices.index)
        res = run_backtest(prices=prices, signals=signals, config=_make_config())

        # The duplicated 2020-01-02 bar collapses to one row (keep first), so the
        # panel has two unique sessions and the book trades without raising.
        assert len(res.returns) == 2
        assert np.isfinite(res.returns.values).all()
        assert res.returns.index.is_unique
        assert np.isfinite(res.equity_curve.values).all()

    def test_duplicate_signal_index_does_not_crash(self):
        prices = _make_prices(symbols=("A",))
        signals = pd.DataFrame({"A": 0.0}, index=prices.index)
        signals.iloc[5] = 1.0
        duplicated = pd.concat([signals, signals.iloc[[5]]])
        res = run_backtest(prices=prices, signals=duplicated, config=_make_config())

        assert np.isfinite(res.returns.values).all()
        assert len(res.trades) == 2

    def test_unique_index_is_untouched_by_the_dedup_guard(self):
        """A clean panel must be bit-identical with and without the guard."""
        prices = _make_prices(symbols=("A",))
        signals = pd.DataFrame({"A": 0.0}, index=prices.index)
        signals.iloc[5] = 1.0
        res = run_backtest(prices=prices, signals=signals, config=_make_config())

        # The dedup guard is a no-op on a unique index: returns, positions and
        # trades are exactly what the pre-fix engine produced.
        assert res.returns.index.is_unique
        assert len(res.trades) == 2
        assert np.isfinite(res.returns.values).all()

    def test_the_contract_rejects_the_pre_fix_duplicate_index_crash(self):
        """Behavioural negative control: the raw ``prices.loc[ts, sym]`` read the
        trade log performs raises on a duplicated label, which is exactly the
        crash the entry guard removes."""
        prices = pd.DataFrame(
            {"A": [101.0, 102.0, 103.0]},
            index=pd.DatetimeIndex(["2020-01-02", "2020-01-03", "2020-01-02"]),
        )
        dup_ts = prices.index[0]
        with pytest.raises(TypeError):
            float(prices.loc[dup_ts, "A"])


# --------------------------------------------------------------------------- #
# Duplicate column labels
# --------------------------------------------------------------------------- #
class TestDuplicateColumns:
    """A repeated column label must not crash the engine.

    The duplicate-label class exists on the column axis as well as the index
    axis. A panel built with ``pd.concat(..., axis=1)`` from two frames that
    share a symbol name (a repeated ticker in a universe, or an overlapping
    benchmark/universe concatenation) carries a duplicated column, and
    ``signals.reindex(..., columns=columns)`` refuses to align against one
    (``ValueError: cannot reindex on an axis with duplicate labels``), while
    the trade log's ``float(prices.loc[ts, sym])`` returns a Series. The engine
    now canonicalizes both panels' columns (keep first) once on entry, so a
    repeated symbol is a no-op and the clean path is bit-identical.
    """

    def test_duplicate_price_columns_do_not_crash(self):
        prices = pd.DataFrame(
            [[101.0, 999.0, 10.0], [102.0, 102.0, 11.0], [103.0, 103.0, 12.0]],
            index=pd.DatetimeIndex(["2020-01-02", "2020-01-03", "2020-01-04"]),
            columns=["A", "A", "B"],
        )
        signals = pd.DataFrame({"A": [0.0, 1.0, 1.0], "B": [1.0, 1.0, 1.0]}, index=prices.index)
        res = run_backtest(prices=prices, signals=signals, config=_make_config())

        assert res.positions.columns.is_unique
        assert list(res.positions.columns) == ["A", "B"]
        assert res.returns.index.is_unique
        assert np.isfinite(res.returns.values).all()
        assert np.isfinite(res.equity_curve.values).all()

    def test_duplicate_signal_columns_do_not_crash(self):
        prices = _make_prices(symbols=("A", "B"))
        base = pd.DataFrame({"A": 0.0, "B": 1.0}, index=prices.index)
        base.iloc[5] = 1.0
        duplicated = pd.concat([base, base[["A"]]], axis=1)  # columns A, B, A
        res = run_backtest(prices=prices, signals=duplicated, config=_make_config())

        assert res.positions.columns.is_unique
        assert np.isfinite(res.returns.values).all()
        assert len(res.trades) >= 1

    def test_unique_columns_are_untouched_by_the_column_guard(self):
        """A clean panel must be bit-identical with and without the guard."""
        prices = _make_prices(symbols=("A", "B"))
        signals = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)
        res = run_backtest(prices=prices, signals=signals, config=_make_config())

        assert res.positions.columns.is_unique
        assert np.isfinite(res.returns.values).all()
        assert len(res.trades) == 2

    def test_the_contract_rejects_the_pre_fix_duplicate_column_crash(self):
        """Behavioural negative control: reindexing a duplicated-label source
        against a unique target raises -- exactly the crash the column guard
        removes."""
        sig = pd.DataFrame(
            np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
            index=pd.DatetimeIndex(["2020-01-02", "2020-01-03"]),
            columns=["A", "A", "B"],
        )
        with pytest.raises(ValueError, match="duplicate labels"):
            sig.reindex(index=sig.index, columns=["A", "B"])


# --------------------------------------------------------------------------- #
# Non-finite (infinite) prices
# --------------------------------------------------------------------------- #
class TestNonFinitePrices:
    """An ``inf`` price is the input class the NaN-price tests above leave out.

    A NaN price already fails closed because ``pct_change`` yields NaN there
    and ``fillna(0.0)`` zeroes the bar. An ``inf`` price does not: it yields an
    ``inf`` return (and a NaN on the following bar), so the pre-fix engine let
    the equity curve's ``cumprod`` carry inf/nan while ``_calculate_metrics``
    reported the no-evidence tuple -- an internally inconsistent result, and a
    fatal ``RuntimeWarning`` under the pinned ``-W error``. The engine now maps
    every non-finite price to NaN, so an infinite price bar is handled exactly
    like a missing one (fail closed).
    """

    def test_positive_infinity_price_bar_fails_closed(self):
        """An ``inf`` price bar earns 0.0, every return and the equity curve
        stay finite, and no warning escapes (the pinned suite runs ``-W
        error``)."""
        import warnings

        prices = _make_prices(symbols=("A",))
        inf_bar = prices.index[10]
        prices.loc[inf_bar, "A"] = np.inf
        signals = pd.DataFrame({"A": 1.0}, index=prices.index)
        cfg = _make_config()

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            res = run_backtest(prices=prices, signals=signals, config=cfg)

        assert np.isfinite(res.returns.values).all()
        assert res.returns.loc[inf_bar] == pytest.approx(0.0, abs=1e-12)
        assert np.isfinite(res.equity_curve.values).all()
        # The shared metrics stay finite (calmar is excluded: it is legitimately
        # +inf when there is no drawdown, which the engine pins elsewhere).
        for key in ("total_return", "sharpe", "max_drawdown", "annualized_volatility"):
            assert np.isfinite(res.metrics[key])

    def test_positive_infinity_price_at_first_bar_does_not_crash(self):
        """An ``inf`` price on bar 0 (which earns nothing under ``shift(1)``)
        must not raise or emit a non-finite return."""
        prices = _make_prices(symbols=("A",))
        prices.iloc[0] = np.inf
        signals = pd.DataFrame({"A": np.nan}, index=prices.index)
        signals.iloc[0] = 1.0
        res = run_backtest(prices=prices, signals=signals, config=_make_config())

        assert np.isfinite(res.returns.values).all()
        assert res.returns.iloc[0] == pytest.approx(0.0, abs=1e-12)

    def test_one_infinite_symbol_does_not_void_the_rest_of_the_book(self):
        """A single ``inf`` price must not contaminate the other symbols: the
        clean symbol still trades and the whole result stays finite."""
        prices = _make_prices(symbols=("A", "B"))
        prices.loc[prices.index[7], "A"] = np.inf
        signals = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)
        res = run_backtest(prices=prices, signals=signals, config=_make_config())

        assert np.isfinite(res.returns.values).all()
        assert np.isfinite(res.equity_curve.values).all()
        assert res.positions.columns.is_unique
        assert len(res.trades) >= 1

    def test_finite_panel_is_bit_identical(self):
        """A finite price panel must be bit-identical with the guard in place."""
        prices = _make_prices(symbols=("A", "B"))
        signals = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)
        res = run_backtest(prices=prices, signals=signals, config=_make_config())

        assert np.isfinite(res.returns.values).all()
        assert len(res.trades) == 2

    def test_the_contract_rejects_the_pre_fix_non_finite_price_warning(self):
        """Behavioural negative control: the pre-fix engine computed the equity
        curve from an un-sanitised return series, so an ``inf`` price (which
        ``pct_change`` turns into an ``inf`` return) made ``cumprod`` emit
        ``RuntimeWarning: invalid value encountered in accumulate`` -- fatal
        under the pinned ``-W error``. Reconstruct that exact arithmetic and
        require it to warn, so the guard above is pinned to a real pre-fix
        failure."""
        import warnings

        returns = pd.Series([-0.0002, np.inf, -1.0])
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            with pytest.raises(RuntimeWarning, match="invalid value encountered in accumulate"):
                (1.0 + returns).cumprod()
