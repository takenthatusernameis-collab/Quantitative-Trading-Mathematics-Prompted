"""The engine's trade log must reconcile with the transaction costs it charges.

**The defect (fixed in ``src/qtr/backtest/engine.py``).** ``_extract_trades``
recorded the *portfolio* cost of a bar on **every** trade of that bar: the
``cost`` column of the trade log was the bar's aggregate charge, repeated
once per simultaneous trade. A bar with ``k`` trades therefore reported ``k``
times the cost that was actually deducted from the returns, and the trade log
no longer reconciled with the P&L it was supposed to audit.

The engine's *charge* was never wrong -- only the attribution inside the log.
The repository's own H27 audit proves this: its ``L3`` check recomputes the
per-bar cost **from the trade log** (each trade's own cost, summed per bar)
and matches the engine's per-bar cost to ~1e-19 for all five audited families
(H9, H10, H21, H22, H25). The engine therefore already computed the correct
per-trade cost; the trade log simply did not carry it.

**The evidence (frozen artifacts).** The certified H10 artifact
(``exp_2026-10-11T17-41-18-169363Z``) holds 3,701 trades over 2,975 bars with
up to 5 simultaneous trades per bar:

* every trade in a bar records the **same** value (the bar total) -- 0 of
  2,975 bars disagree;
* the bar totals sum to the engine's charge, **0.034907**;
* the ``cost`` column sums to **0.062352** -- an over-count of **1.786x**.

**The correction.** The engine now keeps the *per-symbol* cost breakdown
(``_calculate_costs_by_symbol``) and attributes each trade its own share of it
(``_extract_trades``). The per-bar charge is the sum of that breakdown, exactly
as before, so the net returns, the equity curve, the positions and every
metric except ``avg_trade_cost`` are **bit-identical** to the pre-fix engine.

**What is deliberately not changed.** The frozen artifacts are *history*: the
``cost`` column of the committed trade logs (H10, H11, H16, H21, H22, H25) and
the ``avg_trade_cost`` of the three exploratory 2026-10-10 MA-crossover
summaries still carry the pre-fix aggregate attribution. They are left
untouched and pinned below. No gate, threshold, verdict or certified number
uses the trade-log cost column, and no certified number changes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))

from _utils_parquet import read_parquet_safe  # noqa: E402

from qtr.backtest.engine import (  # noqa: E402
    AssetClass,
    BacktestConfig,
    CostModel,
    VectorizedBacktester,
)

ARTIFACTS = ROOT / ".experiments" / "artifacts"
H10_DIR = ARTIFACTS / "exp_2026-10-11T17-41-18-169363Z"
H27_DIR = ARTIFACTS / "h27_pnl_level"

INITIAL_CAPITAL = 1_000_000.0


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _prices(n: int = 40, symbols: tuple[str, ...] = ("A", "B"), seed: int = 11) -> pd.DataFrame:
    """A deterministic multi-symbol price frame."""
    rng = np.random.default_rng(seed)
    index = pd.bdate_range("2020-01-01", periods=n)
    return pd.DataFrame(
        {sym: 100.0 * np.exp(np.cumsum(rng.normal(0.0004, 0.01, n))) for sym in symbols},
        index=index,
    )


def _simultaneous_signals(prices: pd.DataFrame) -> pd.DataFrame:
    """Both symbols enter and leave on the SAME bars (so the trades overlap)."""
    signals = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    signals.iloc[5:15, :] = 1.0
    signals.iloc[20:28, :] = 0.5
    return signals


def _config(asset_class: AssetClass = AssetClass.EQUITY) -> BacktestConfig:
    return BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        cost_model=CostModel(),
        asset_class=asset_class,
        max_position_size=1.0,
        max_leverage=1.0,
        allow_short=True,
    )


class _ChargeSpy(VectorizedBacktester):
    """A backtester that records the per-bar cost the engine charged.

    Both hooks are overridden so the spy observes the charge under either
    engine version: the fixed engine assembles it in ``_total_costs``, the
    pre-fix one in ``_calculate_costs``. That keeps the negative control
    behavioural -- the pre-fix engine must fail the *reconciliation*, not
    merely lack a method.
    """

    def __init__(self, config: BacktestConfig):
        super().__init__(config)
        self.charged: pd.Series | None = None

    def _total_costs(self, symbol_costs: pd.DataFrame) -> pd.Series:
        out = super()._total_costs(symbol_costs)
        self.charged = out
        return out

    def _calculate_costs(
        self,
        position_changes: pd.DataFrame,
        prices: pd.DataFrame,
        volumes: pd.DataFrame,
        adv: pd.Series | None,
    ) -> pd.Series:
        out = super()._calculate_costs(position_changes, prices, volumes, adv)
        self.charged = out
        return out


def _run_with_charge(
    prices: pd.DataFrame,
    signals: pd.DataFrame,
    asset_class: AssetClass = AssetClass.EQUITY,
):
    """Run a backtest and return (result, the per-bar cost the engine charged)."""
    spy = _ChargeSpy(_config(asset_class))
    result = spy.run(prices, signals)
    assert spy.charged is not None
    return result, spy.charged


def _reconciles(trades: pd.DataFrame, charged: pd.Series) -> bool:
    """Does the trade log's cost column add up to the cost the engine charged?

    This is the invariant: the per-trade costs must sum to the charge, bar by
    bar and in total.
    """
    per_bar = trades.groupby("timestamp")["cost"].sum()
    aligned = per_bar.reindex(charged.index).fillna(0.0)
    if not np.allclose(aligned.to_numpy(), charged.to_numpy(), rtol=1e-12, atol=1e-18):
        return False
    return bool(
        np.isclose(trades["cost"].sum(), charged.sum(), rtol=1e-12, atol=1e-18),
    )


# --------------------------------------------------------------------------- #
# the contract
# --------------------------------------------------------------------------- #
class TestTradeLogReconcilesWithTheCharge:
    def test_the_trade_log_reconciles_with_the_charge(self):
        """The per-trade costs sum to the cost the engine deducted."""
        prices = _prices()
        signals = _simultaneous_signals(prices)
        result, charged = _run_with_charge(prices, signals)

        assert len(result.trades) > 0
        assert _reconciles(result.trades, charged), (
            "the trade log does not reconcile with the charged cost: "
            f"log={result.trades['cost'].sum()!r} charged={charged.sum()!r}"
        )

    def test_the_trade_log_reconciles_for_every_asset_class(self):
        """The reconciliation is not specific to the equity cost path."""
        prices = _prices()
        signals = _simultaneous_signals(prices)
        for asset_class in (AssetClass.EQUITY, AssetClass.FUTURE, AssetClass.CRYPTO):
            result, charged = _run_with_charge(prices, signals, asset_class)
            assert _reconciles(result.trades, charged), asset_class

    def test_every_trade_in_a_bar_records_only_its_own_share(self):
        """A trade in a multi-trade bar records a *strict fraction* of the bar.

        Under the pre-fix attribution every trade of a bar recorded the bar's
        full cost, so the share of a bar that a trade accounts for was 1.0 no
        matter how many trades the bar held. It is now 1/k.
        """
        prices = _prices()
        signals = _simultaneous_signals(prices)
        result, charged = _run_with_charge(prices, signals)

        per_bar = result.trades.groupby("timestamp")["cost"]
        sizes = per_bar.size()
        assert (sizes > 1).any(), "the case must contain simultaneous trades"

        multi = sizes[sizes > 1].index
        bar_total = charged.reindex(multi)
        per_trade = per_bar.mean().reindex(multi)
        assert (per_trade < bar_total).all(), (
            "a trade in a multi-trade bar records the whole bar cost: the bar "
            "total is still being attributed to every trade"
        )
        # Each trade accounts for exactly 1/k of its bar.
        np.testing.assert_allclose(
            per_trade.to_numpy(),
            (bar_total / sizes.reindex(multi)).to_numpy(),
            rtol=1e-12,
            atol=1e-18,
        )

    def test_the_equity_cost_of_a_trade_is_its_own_weight_change_times_the_bps(self):
        """The per-trade cost is reproduced by an independent formula.

        The formula uses only the trade log and the cost model -- not the
        engine's internals -- so it is a real check of the attribution.
        """
        prices = _prices()
        signals = _simultaneous_signals(prices)
        cm = CostModel()
        result, charged = _run_with_charge(prices, signals)

        cost_bps = cm.equity_commission_bps + cm.equity_spread_bps
        expected = result.trades["weight_change"].abs() * (cost_bps / 10_000)
        np.testing.assert_allclose(
            result.trades["cost"].to_numpy(), expected.to_numpy(), rtol=1e-12, atol=1e-18
        )

    def test_the_futures_cost_of_a_trade_is_its_own_contracts_times_the_contract_cost(self):
        """The futures path attributes the per-contract cost to the trade."""
        prices = _prices(symbols=("ES=F", "ZN=F"))
        signals = _simultaneous_signals(prices)
        cm = CostModel()
        result, charged = _run_with_charge(prices, signals, AssetClass.FUTURE)

        for _, row in result.trades.iterrows():
            contract_cost = cm.future_cost_per_contract(row["symbol"])
            multiplier = cm.get_future_contract_multiplier(row["symbol"])
            expected = (
                abs(row["weight_change"])
                * INITIAL_CAPITAL
                / (row["price"] * multiplier)
                * contract_cost
                / INITIAL_CAPITAL
            )
            assert row["cost"] == pytest.approx(expected, rel=1e-12, abs=1e-18)
        assert _reconciles(result.trades, charged)

    def test_avg_trade_cost_is_the_charge_divided_by_the_number_of_trades(self):
        """`avg_trade_cost` is an average *per trade*, not per trade-bar."""
        prices = _prices()
        signals = _simultaneous_signals(prices)
        result, charged = _run_with_charge(prices, signals)

        assert result.metrics["avg_trade_cost"] == pytest.approx(
            charged.sum() / len(result.trades), rel=1e-12, abs=1e-18
        )

    def test_a_symbol_that_never_trades_costs_nothing(self):
        """A symbol with no position change contributes no cost and no trade."""
        prices = _prices(symbols=("A", "B"))
        signals = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
        signals["A"] = 1.0
        result, charged = _run_with_charge(prices, signals)

        assert set(result.trades["symbol"]) == {"A"}
        assert "B" not in set(result.trades["symbol"])
        assert _reconciles(result.trades, charged)

    def test_the_charge_itself_is_unchanged_by_the_attribution(self):
        """The per-bar charge is the sum of the per-symbol costs.

        The attribution moved the *log*, not the charge: the engine still
        deducts exactly the same series from the returns. The changes are
        taken from the *final* positions, because the engine normalises the
        leverage before it prices the trades.
        """
        prices = _prices()
        signals = _simultaneous_signals(prices)
        config = _config()
        backtester = VectorizedBacktester(config)
        result = backtester.run(prices, signals)

        changes = result.positions.diff().fillna(result.positions.iloc[0])
        charged = backtester._calculate_costs(changes, prices, None, None)

        # The charge is a per-bar series of non-negative fractions of capital.
        assert (charged >= 0).all()
        assert charged.sum() > 0
        # The engine's net returns are the gross returns minus that charge.
        gross = (result.positions.shift(1) * prices.pct_change().fillna(0.0)).sum(axis=1)
        np.testing.assert_allclose(
            result.returns.to_numpy(),
            (gross - charged).to_numpy(),
            rtol=1e-12,
            atol=1e-15,
        )


# --------------------------------------------------------------------------- #
# the negative control: the pre-fix attribution must fail the invariant
# --------------------------------------------------------------------------- #
class TestNegativeControl:
    def test_the_aggregate_attribution_fails_the_reconciliation(self):
        """The invariant is discriminating, not vacuous.

        The pre-fix attribution -- the bar total repeated on every trade of
        the bar -- is reconstructed here from the fixed log and shown to
        violate the invariant the tests above assert.
        """
        prices = _prices()
        signals = _simultaneous_signals(prices)
        result, charged = _run_with_charge(prices, signals)

        # Rebuild the pre-fix log: every trade of a bar carries the bar total.
        bar_total = result.trades.groupby("timestamp")["cost"].transform("sum")
        pre_fix = result.trades.copy()
        pre_fix["cost"] = bar_total

        assert not _reconciles(pre_fix, charged), (
            "the aggregate attribution satisfies the reconciliation, so the "
            "invariant cannot distinguish it from the per-trade attribution"
        )
        assert pre_fix["cost"].sum() > charged.sum()

    def test_the_single_symbol_case_cannot_reveal_the_defect(self):
        """With one symbol the two attributions coincide.

        This is why the defect survived: a single-symbol backtest records the
        same number under either attribution, so only a multi-symbol case
        can see it.
        """
        prices = _prices(symbols=("A",))
        signals = _simultaneous_signals(prices)
        result, charged = _run_with_charge(prices, signals)

        bar_total = result.trades.groupby("timestamp")["cost"].transform("sum")
        pre_fix = result.trades.copy()
        pre_fix["cost"] = bar_total

        assert _reconciles(pre_fix, charged)
        np.testing.assert_array_equal(pre_fix["cost"].to_numpy(), result.trades["cost"].to_numpy())


# --------------------------------------------------------------------------- #
# the frozen record: a disclosure, not a rewrite
# --------------------------------------------------------------------------- #
class TestFrozenArtifactDisclosure:
    """The committed artifacts still carry the pre-fix attribution.

    They are frozen and are not load-bearing for any gate, threshold, verdict
    or certified number, so they are left untouched and pinned here.
    """

    def _h10_trades(self) -> pd.DataFrame:
        df = read_parquet_safe(H10_DIR / "trades.parquet")
        trades = pd.DataFrame(df)
        trades["timestamp"] = pd.to_datetime(trades["timestamp"])
        return trades

    def test_the_h10_trade_log_stored_the_bar_total_on_every_trade(self):
        trades = self._h10_trades()
        per_bar = trades.groupby("timestamp")["cost"]
        assert len(trades) == 3701
        assert (per_bar.nunique() == 1).all(), (
            "the frozen H10 trade log no longer shows the pre-fix aggregate attribution"
        )

    def test_the_h10_trade_log_over_counted_the_charged_cost(self):
        """The published column over-states the charge by 1.786x."""
        trades = self._h10_trades()
        bar_total = trades.groupby("timestamp")["cost"].first()
        assert trades["cost"].sum() == pytest.approx(0.0623522855991627, rel=1e-12)
        assert bar_total.sum() == pytest.approx(0.03490706683778448, rel=1e-12)
        assert trades["cost"].sum() / bar_total.sum() == pytest.approx(
            1.7862367493928384, rel=1e-12
        )

    def test_the_h27_audit_already_established_the_per_bar_charge(self):
        """The H27 `L3` check is the proof that the bar total is the charge.

        H27 recomputes the per-bar cost from the trade log (each trade's own
        cost, summed) and matches the engine's per-bar cost to ~1e-19 for
        every audited family. That is the same reconciliation the engine now
        performs internally, and it confirms the *charge* was never wrong.
        """
        with open(H27_DIR / "summary.json") as f:
            summary = json.load(f)

        families = {entry["family"]: entry for entry in summary["audited"]}
        assert set(families) == {"H9", "H10", "H21", "H22", "H25"}
        for family, entry in families.items():
            l3 = entry["level_checks"]["L3"]
            assert l3["passes"] is True, family
            assert l3["cost_from_trades_matches_engine_max_abs_diff"] < 1e-15, family

        # H10 is the family whose trade log this module pins.
        assert families["H10"]["level_checks"]["L3"]["n_trades"] == 3701
