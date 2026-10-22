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
``cost`` column of **every** committed trade log (**82** of them) and the
``avg_trade_cost`` of the five summaries that publish it still carry the
pre-fix aggregate attribution. They are left untouched and pinned below -- for
the whole record, not for one artifact. No gate, threshold, verdict or
certified number uses the trade-log cost column, and no certified number
changes.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
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


def _unequal_signals(prices: pd.DataFrame) -> pd.DataFrame:
    """The symbols trade on the same bars, but with different sizes.

    Their costs therefore differ, so the per-trade attribution writes
    different numbers on the two trades of a bar -- which is what makes the
    classifier able to tell the two attributions apart.
    """
    signals = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    signals.iloc[5:15, :] = 1.0
    signals.iloc[20:28, :] = 0.5
    if signals.shape[1] > 1:
        signals.iloc[20:28, 1] = 0.25
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


# --------------------------------------------------------------------------- #
# the frozen record, in full: every committed trade log (H52)
# --------------------------------------------------------------------------- #
#: A trade-log read of the ``cost`` column: ``["cost"]`` or ``.cost``.
COST_COLUMN_ACCESS = re.compile(r"""\[\s*['"]cost['"]\s*\]|\.\s*cost\b""")

#: The commit that carries the engine's per-trade attribution fix. Every
#: committed trade log was produced by a run stamped *before* it, so every one
#: of them was written by the pre-fix engine.
ATTRIBUTION_FIX_COMMIT = "3fbef17"

#: The UTC time that commit was made. This clone's history was squashed and
#: no longer contains ``3fbef17``, so the timestamp is pinned here rather
#: than read from ``git``. The value is the one recorded in ``FINAL_REPORT.md``
#: and it is cross-checked against ``git`` whenever the commit *is* present,
#: so the pin cannot silently drift away from the upstream history.
ATTRIBUTION_FIX_TIMESTAMP = datetime(2026, 10, 21, 11, 33, 35, tzinfo=timezone.utc)

#: Every trade log the repository tracks, with the numbers that classify its
#: cost attribution: ``(trades, bars, bars holding more than one trade)``.
TRADE_LOG_RECORD: dict[str, tuple[int, int, int]] = {
    ".experiments/artifacts/exp_2026-10-10T17-02-22-080026Z/trades.parquet": (257, 231, 21),
    ".experiments/artifacts/exp_2026-10-10T17-03-39-610858Z/trades.parquet": (257, 231, 21),
    ".experiments/artifacts/exp_2026-10-10T17-04-21-400695Z/trades.parquet": (778, 231, 198),
    ".experiments/artifacts/exp_2026-10-10T17-05-58-697503Z/trades.parquet": (1, 1, 0),
    ".experiments/artifacts/exp_2026-10-10T17-07-48-008615Z/best_trades.parquet": (9, 9, 0),
    ".experiments/artifacts/exp_2026-10-10T17-09-34-333145Z/best_trades.parquet": (1, 1, 0),
    ".experiments/artifacts/exp_2026-10-10T20-56-30-507309Z/benchmark_trades.parquet": (20, 1, 1),
    ".experiments/artifacts/exp_2026-10-10T20-56-30-507309Z/selected_trades.parquet": (
        1471,
        113,
        111,
    ),
    ".experiments/artifacts/exp_2026-10-10T20-57-26-136503Z/benchmark_trades.parquet": (20, 1, 1),
    ".experiments/artifacts/exp_2026-10-10T20-57-26-136503Z/selected_trades.parquet": (
        1471,
        113,
        111,
    ),
    ".experiments/artifacts/exp_2026-10-10T20-59-28-306148Z/selected_trades.parquet": (
        714,
        100,
        91,
    ),
    ".experiments/artifacts/exp_2026-10-10T21-08-54-188263Z/benchmark_trades.parquet": (20, 1, 1),
    ".experiments/artifacts/exp_2026-10-10T21-08-54-188263Z/selected_trades.parquet": (
        1471,
        113,
        111,
    ),
    ".experiments/artifacts/exp_2026-10-10T21-09-06-830199Z/selected_trades.parquet": (
        714,
        100,
        91,
    ),
    ".experiments/artifacts/exp_2026-10-10T21-27-13-928282Z/benchmark_trades.parquet": (20, 1, 1),
    ".experiments/artifacts/exp_2026-10-10T21-27-13-928282Z/selected_trades.parquet": (
        2379,
        115,
        115,
    ),
    ".experiments/artifacts/exp_2026-10-10T21-28-20-920399Z/benchmark_trades.parquet": (20, 1, 1),
    ".experiments/artifacts/exp_2026-10-10T21-28-20-920399Z/selected_trades.parquet": (
        2379,
        115,
        115,
    ),
    ".experiments/artifacts/exp_2026-10-10T21-58-28-353634Z/ensemble_trades.parquet": (270, 82, 79),
    ".experiments/artifacts/exp_2026-10-10T21-59-16-546117Z/ensemble_trades.parquet": (270, 82, 79),
    ".experiments/artifacts/exp_2026-10-10T22-59-01-182037Z/ensemble_trades.parquet": (356, 82, 80),
    ".experiments/artifacts/exp_2026-10-11T00-26-35-750834Z/best_ddcv_trades.parquet": (
        353,
        104,
        97,
    ),
    ".experiments/artifacts/exp_2026-10-11T00-34-05-381535Z/best_ddcv_trades.parquet": (
        353,
        104,
        97,
    ),
    ".experiments/artifacts/exp_2026-10-11T02-44-40-301520Z/best_trades.parquet": (335, 99, 92),
    ".experiments/artifacts/exp_2026-10-11T02-44-40-301520Z/vix_only_trades.parquet": (285, 82, 77),
    ".experiments/artifacts/exp_2026-10-11T02-46-37-311994Z/best_trades.parquet": (335, 99, 92),
    ".experiments/artifacts/exp_2026-10-11T02-46-37-311994Z/vix_only_trades.parquet": (285, 82, 77),
    ".experiments/artifacts/exp_2026-10-11T07-18-39-160945Z/best_trades.parquet": (335, 99, 92),
    ".experiments/artifacts/exp_2026-10-11T07-18-39-160945Z/vix_only_trades.parquet": (285, 82, 77),
    ".experiments/artifacts/exp_2026-10-11T08-02-22-999214Z/best_trades.parquet": (335, 99, 92),
    ".experiments/artifacts/exp_2026-10-11T08-02-22-999214Z/vix_only_trades.parquet": (285, 82, 77),
    ".experiments/artifacts/exp_2026-10-11T14-52-29-891596Z/trades.parquet": (441, 176, 100),
    ".experiments/artifacts/exp_2026-10-11T14-53-13-076438Z/trades.parquet": (441, 176, 100),
    ".experiments/artifacts/exp_2026-10-11T15-21-31-333870Z/benchmark_trades.parquet": (5, 1, 1),
    ".experiments/artifacts/exp_2026-10-11T15-21-31-333870Z/best_trades_w0.5.parquet": (
        374,
        106,
        100,
    ),
    ".experiments/artifacts/exp_2026-10-11T15-53-31-819888Z/trades.parquet": (31519, 11029, 9216),
    ".experiments/artifacts/exp_2026-10-11T15-54-17-212022Z/trades.parquet": (31519, 11029, 9216),
    ".experiments/artifacts/exp_2026-10-11T16-44-06-168529Z/trades.parquet": (2690, 2176, 368),
    ".experiments/artifacts/exp_2026-10-11T16-46-06-466282Z/trades.parquet": (2690, 2176, 368),
    ".experiments/artifacts/exp_2026-10-11T16-52-38-694559Z/trades.parquet": (2690, 2176, 368),
    ".experiments/artifacts/exp_2026-10-11T17-24-14-385352Z/trades.parquet": (2869, 2320, 391),
    ".experiments/artifacts/exp_2026-10-11T17-41-18-169363Z/trades.parquet": (3701, 2975, 513),
    ".experiments/artifacts/exp_2026-10-11T18-40-37-427062Z/frozen_trades.parquet": (
        3701,
        2975,
        513,
    ),
    ".experiments/artifacts/exp_2026-10-11T20-25-36-443045Z/baseline_trades.parquet": (
        3701,
        2975,
        513,
    ),
    ".experiments/artifacts/exp_2026-10-13T21-11-45-843908Z/best_trades.parquet": (413, 129, 129),
    ".experiments/artifacts/exp_2026-10-13T21-13-09-580962Z/best_trades.parquet": (413, 129, 129),
    ".experiments/artifacts/exp_2026-10-13T21-18-23-178134Z/best_trades.parquet": (338, 129, 129),
    ".experiments/artifacts/exp_2026-10-13T21-22-02-751156Z/best_trades.parquet": (338, 129, 129),
    ".experiments/artifacts/exp_2026-10-13T21-51-45-034237Z/best_trades.parquet": (1467, 1467, 0),
    ".experiments/artifacts/exp_2026-10-13T22-40-41-870350Z/best_trades.parquet": (1424, 1424, 0),
    ".experiments/artifacts/exp_2026-10-13T23-06-33-191710Z/best_trades.parquet": (4404, 4404, 0),
    ".experiments/artifacts/exp_2026-10-13T23-27-52-101656Z/trades.parquet": (12624, 6335, 2897),
    ".experiments/artifacts/exp_2026-10-14T07-12-35-292010Z/trades.parquet": (4980, 2695, 830),
    ".experiments/artifacts/exp_2026-10-14T07-12-59-473353Z/trades.parquet": (4980, 2695, 830),
    ".experiments/artifacts/exp_2026-10-14T07-15-23-322705Z/trades.parquet": (4980, 2695, 830),
    ".experiments/artifacts/exp_2026-10-14T07-32-43-425839Z/trades.parquet": (4980, 2695, 830),
    ".experiments/artifacts/exp_2026-10-14T08-20-16-720432Z/trades.parquet": (441, 176, 100),
    ".experiments/artifacts/exp_2026-10-14T08-20-39-255883Z/trades.parquet": (2715, 2180, 394),
    ".experiments/artifacts/exp_2026-10-14T08-26-02-537359Z/trades.parquet": (1, 1, 0),
    ".experiments/artifacts/exp_2026-10-14T08-26-18-385545Z/benchmark_trades.parquet": (20, 1, 1),
    ".experiments/artifacts/exp_2026-10-14T08-26-18-385545Z/selected_trades.parquet": (
        1471,
        113,
        111,
    ),
    ".experiments/artifacts/exp_2026-10-14T08-27-02-650342Z/ensemble_trades.parquet": (356, 82, 80),
    ".experiments/artifacts/exp_2026-10-14T08-48-49-412372Z/trades.parquet": (0, 0, 0),
    ".experiments/artifacts/exp_2026-10-14T09-28-59-592390Z/trades.parquet": (0, 0, 0),
    ".experiments/artifacts/exp_2026-10-14T09-32-25-959733Z/trades.parquet": (0, 0, 0),
    ".experiments/artifacts/exp_2026-10-14T09-39-07-412533Z/trades.parquet": (0, 0, 0),
    ".experiments/artifacts/exp_2026-10-14T10-04-52-936640Z/trades.parquet": (0, 0, 0),
    ".experiments/artifacts/exp_2026-10-14T11-53-37-996139Z/trades.parquet": (107, 60, 42),
    ".experiments/artifacts/exp_2026-10-14T18-13-09-457781Z/trades.parquet": (107, 60, 42),
    ".experiments/artifacts/exp_2026-10-14T18-52-08-943792Z/trades.parquet": (4980, 2695, 830),
    ".experiments/artifacts/exp_2026-10-14T20-02-45-189859Z/trades.parquet": (3056, 1424, 570),
    ".experiments/artifacts/exp_2026-10-14T20-08-34-613690Z/trades.parquet": (3056, 1424, 570),
    ".experiments/artifacts/exp_2026-10-19T18-56-08-872500Z/trades.parquet": (441, 176, 100),
    ".experiments/artifacts/exp_2026-10-19T18-56-58-553612Z/trades.parquet": (441, 176, 100),
    ".experiments/artifacts/h28_causal_recertification/runs/exp_2026-10-19T15-46-16-261803Z/trades.parquet": (
        3701,
        2975,
        513,
    ),
    ".experiments/artifacts/h28_causal_recertification/runs/exp_2026-10-19T16-41-44-683912Z/trades.parquet": (
        3820,
        3090,
        539,
    ),
    ".experiments/artifacts/h28_causal_recertification/runs/exp_2026-10-19T17-38-03-570526Z/trades.parquet": (
        12624,
        6335,
        2897,
    ),
    ".experiments/artifacts/h28_causal_recertification/runs/exp_2026-10-19T17-38-21-389139Z/trades.parquet": (
        12669,
        6443,
        2846,
    ),
    ".experiments/artifacts/h28_causal_recertification/runs/exp_2026-10-19T17-38-39-157337Z/trades.parquet": (
        4980,
        2695,
        830,
    ),
    ".experiments/artifacts/h28_causal_recertification/runs/exp_2026-10-19T17-38-50-887609Z/trades.parquet": (
        5262,
        2754,
        903,
    ),
    ".experiments/artifacts/h28_causal_recertification/runs/exp_2026-10-19T17-39-02-719690Z/trades.parquet": (
        3056,
        1424,
        570,
    ),
    ".experiments/artifacts/h28_causal_recertification/runs/exp_2026-10-19T17-39-12-729639Z/trades.parquet": (
        3160,
        1465,
        593,
    ),
}

#: The logs whose recorded attribution differs from the per-trade attribution:
#: they hold at least one bar with more than one trade, so the bar's value was
#: written on every trade of that bar and the recorded column repeats it.
ATTRIBUTION_CHANGES_A_NUMBER: frozenset[str] = frozenset(
    {
        ".experiments/artifacts/exp_2026-10-10T17-02-22-080026Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-10T17-03-39-610858Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-10T17-04-21-400695Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-10T20-56-30-507309Z/benchmark_trades.parquet",
        ".experiments/artifacts/exp_2026-10-10T20-56-30-507309Z/selected_trades.parquet",
        ".experiments/artifacts/exp_2026-10-10T20-57-26-136503Z/benchmark_trades.parquet",
        ".experiments/artifacts/exp_2026-10-10T20-57-26-136503Z/selected_trades.parquet",
        ".experiments/artifacts/exp_2026-10-10T20-59-28-306148Z/selected_trades.parquet",
        ".experiments/artifacts/exp_2026-10-10T21-08-54-188263Z/benchmark_trades.parquet",
        ".experiments/artifacts/exp_2026-10-10T21-08-54-188263Z/selected_trades.parquet",
        ".experiments/artifacts/exp_2026-10-10T21-09-06-830199Z/selected_trades.parquet",
        ".experiments/artifacts/exp_2026-10-10T21-27-13-928282Z/benchmark_trades.parquet",
        ".experiments/artifacts/exp_2026-10-10T21-27-13-928282Z/selected_trades.parquet",
        ".experiments/artifacts/exp_2026-10-10T21-28-20-920399Z/benchmark_trades.parquet",
        ".experiments/artifacts/exp_2026-10-10T21-28-20-920399Z/selected_trades.parquet",
        ".experiments/artifacts/exp_2026-10-10T21-58-28-353634Z/ensemble_trades.parquet",
        ".experiments/artifacts/exp_2026-10-10T21-59-16-546117Z/ensemble_trades.parquet",
        ".experiments/artifacts/exp_2026-10-10T22-59-01-182037Z/ensemble_trades.parquet",
        ".experiments/artifacts/exp_2026-10-11T00-26-35-750834Z/best_ddcv_trades.parquet",
        ".experiments/artifacts/exp_2026-10-11T00-34-05-381535Z/best_ddcv_trades.parquet",
        ".experiments/artifacts/exp_2026-10-11T02-44-40-301520Z/best_trades.parquet",
        ".experiments/artifacts/exp_2026-10-11T02-44-40-301520Z/vix_only_trades.parquet",
        ".experiments/artifacts/exp_2026-10-11T02-46-37-311994Z/best_trades.parquet",
        ".experiments/artifacts/exp_2026-10-11T02-46-37-311994Z/vix_only_trades.parquet",
        ".experiments/artifacts/exp_2026-10-11T07-18-39-160945Z/best_trades.parquet",
        ".experiments/artifacts/exp_2026-10-11T07-18-39-160945Z/vix_only_trades.parquet",
        ".experiments/artifacts/exp_2026-10-11T08-02-22-999214Z/best_trades.parquet",
        ".experiments/artifacts/exp_2026-10-11T08-02-22-999214Z/vix_only_trades.parquet",
        ".experiments/artifacts/exp_2026-10-11T14-52-29-891596Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-11T14-53-13-076438Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-11T15-21-31-333870Z/benchmark_trades.parquet",
        ".experiments/artifacts/exp_2026-10-11T15-21-31-333870Z/best_trades_w0.5.parquet",
        ".experiments/artifacts/exp_2026-10-11T15-53-31-819888Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-11T15-54-17-212022Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-11T16-44-06-168529Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-11T16-46-06-466282Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-11T16-52-38-694559Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-11T17-24-14-385352Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-11T17-41-18-169363Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-11T18-40-37-427062Z/frozen_trades.parquet",
        ".experiments/artifacts/exp_2026-10-11T20-25-36-443045Z/baseline_trades.parquet",
        ".experiments/artifacts/exp_2026-10-13T21-11-45-843908Z/best_trades.parquet",
        ".experiments/artifacts/exp_2026-10-13T21-13-09-580962Z/best_trades.parquet",
        ".experiments/artifacts/exp_2026-10-13T21-18-23-178134Z/best_trades.parquet",
        ".experiments/artifacts/exp_2026-10-13T21-22-02-751156Z/best_trades.parquet",
        ".experiments/artifacts/exp_2026-10-13T23-27-52-101656Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-14T07-12-35-292010Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-14T07-12-59-473353Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-14T07-15-23-322705Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-14T07-32-43-425839Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-14T08-20-16-720432Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-14T08-20-39-255883Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-14T08-26-18-385545Z/benchmark_trades.parquet",
        ".experiments/artifacts/exp_2026-10-14T08-26-18-385545Z/selected_trades.parquet",
        ".experiments/artifacts/exp_2026-10-14T08-27-02-650342Z/ensemble_trades.parquet",
        ".experiments/artifacts/exp_2026-10-14T11-53-37-996139Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-14T18-13-09-457781Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-14T18-52-08-943792Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-14T20-02-45-189859Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-14T20-08-34-613690Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-19T18-56-08-872500Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-19T18-56-58-553612Z/trades.parquet",
        ".experiments/artifacts/h28_causal_recertification/runs/exp_2026-10-19T15-46-16-261803Z/trades.parquet",
        ".experiments/artifacts/h28_causal_recertification/runs/exp_2026-10-19T16-41-44-683912Z/trades.parquet",
        ".experiments/artifacts/h28_causal_recertification/runs/exp_2026-10-19T17-38-03-570526Z/trades.parquet",
        ".experiments/artifacts/h28_causal_recertification/runs/exp_2026-10-19T17-38-21-389139Z/trades.parquet",
        ".experiments/artifacts/h28_causal_recertification/runs/exp_2026-10-19T17-38-39-157337Z/trades.parquet",
        ".experiments/artifacts/h28_causal_recertification/runs/exp_2026-10-19T17-38-50-887609Z/trades.parquet",
        ".experiments/artifacts/h28_causal_recertification/runs/exp_2026-10-19T17-39-02-719690Z/trades.parquet",
        ".experiments/artifacts/h28_causal_recertification/runs/exp_2026-10-19T17-39-12-729639Z/trades.parquet",
    }
)

#: The logs whose recorded attribution coincides with the per-trade one by
#: construction: every bar holds exactly one trade, so the bar's value *is* that
#: trade's own cost. The attribution changes no number in them.
ATTRIBUTION_COINCIDES: frozenset[str] = frozenset(
    {
        ".experiments/artifacts/exp_2026-10-10T17-05-58-697503Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-10T17-07-48-008615Z/best_trades.parquet",
        ".experiments/artifacts/exp_2026-10-10T17-09-34-333145Z/best_trades.parquet",
        ".experiments/artifacts/exp_2026-10-13T21-51-45-034237Z/best_trades.parquet",
        ".experiments/artifacts/exp_2026-10-13T22-40-41-870350Z/best_trades.parquet",
        ".experiments/artifacts/exp_2026-10-13T23-06-33-191710Z/best_trades.parquet",
        ".experiments/artifacts/exp_2026-10-14T08-26-02-537359Z/trades.parquet",
    }
)

#: The logs that hold no trade at all: they attribute nothing.
NO_TRADES: frozenset[str] = frozenset(
    {
        ".experiments/artifacts/exp_2026-10-14T08-48-49-412372Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-14T09-28-59-592390Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-14T09-32-25-959733Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-14T09-39-07-412533Z/trades.parquet",
        ".experiments/artifacts/exp_2026-10-14T10-04-52-936640Z/trades.parquet",
    }
)

#: The published numbers that read the trade log's ``cost`` column, with the
#: factor by which the recorded column repeats the bar's value:
#: ``(published value, repetition factor)``.
PUBLISHED_COST_NUMBERS: dict[str, tuple[float, float]] = {
    ".experiments/artifacts/exp_2026-10-10T17-02-22-080026Z/summary.json": (
        0.046661483375726044,
        1.2299534267300314,
    ),
    ".experiments/artifacts/exp_2026-10-10T17-03-39-610858Z/summary.json": (
        0.04106853533924311,
        1.2471085910700175,
    ),
    ".experiments/artifacts/exp_2026-10-10T17-04-21-400695Z/summary.json": (
        0.021484183909932723,
        2.8689482110802778,
    ),
    ".experiments/artifacts/exp_2026-10-10T17-05-58-697503Z/summary.json": (
        0.041105949376283715,
        1.0,
    ),
    ".experiments/artifacts/exp_2026-10-14T08-26-02-537359Z/summary.json": (
        0.00020009711746988646,
        1.0,
    ),
}

#: The tracker-metadata entries that publish the *benchmark's* ``avg_trade_cost``:
#: ``experiment id -> (published value, benchmark trade count)``.
BENCHMARK_COST_METADATA: dict[str, tuple[float, int]] = {
    "exp_2026-10-10T17-02-22-080026Z": (0.021074414724414924, 5),
    "exp_2026-10-10T17-03-39-610858Z": (0.021074301216455565, 5),
    "exp_2026-10-10T17-04-21-400695Z": (0.021074301216455565, 5),
    "exp_2026-10-10T20-56-30-507309Z": (0.0002018306804270815, 20),
    "exp_2026-10-10T20-57-26-136503Z": (0.0002018306804270815, 20),
    "exp_2026-10-10T21-08-54-188263Z": (0.0002018306804270815, 20),
    "exp_2026-10-10T21-27-13-928282Z": (0.0002018306804270815, 20),
    "exp_2026-10-10T21-28-20-920399Z": (0.0002018306804270815, 20),
    "exp_2026-10-10T21-58-07-833835Z": (0.00010629059079463798, 5),
    "exp_2026-10-10T21-58-28-353634Z": (0.00010629059079463798, 5),
    "exp_2026-10-10T21-59-16-546117Z": (0.00010629059079463798, 5),
    "exp_2026-10-10T22-59-01-182037Z": (0.00010629059079463798, 5),
    "exp_2026-10-11T00-25-56-751422Z": (0.00010629059079463798, 5),
    "exp_2026-10-11T00-26-08-362690Z": (0.00010629059079463798, 5),
    "exp_2026-10-11T00-26-18-281925Z": (0.00010629059079463798, 5),
    "exp_2026-10-11T00-26-35-750834Z": (0.00010629059079463798, 5),
    "exp_2026-10-11T00-34-05-381535Z": (0.00010629059079463798, 5),
    "exp_2026-10-11T02-44-40-301520Z": (0.00010629059079463798, 5),
    "exp_2026-10-11T02-46-37-311994Z": (0.00010629059079463798, 5),
    "exp_2026-10-11T07-18-39-160945Z": (0.00010629059079463798, 5),
    "exp_2026-10-11T08-02-22-999214Z": (0.00010629059079463798, 5),
    "exp_2026-10-14T08-26-18-385545Z": (0.0002018306804270815, 20),
    "exp_2026-10-14T08-27-02-650342Z": (0.00010629059079463798, 5),
}

#: The benchmark entries whose benchmark trade log was committed: the published
#: value repeats the bar's value once per benchmark trade (20, for the
#: 20-symbol benchmark).
BENCHMARK_COST_OVER_COUNT_VERIFIED: dict[str, float] = {
    "exp_2026-10-10T20-56-30-507309Z": 20.0,
    "exp_2026-10-10T20-57-26-136503Z": 20.0,
    "exp_2026-10-10T21-08-54-188263Z": 20.0,
    "exp_2026-10-10T21-27-13-928282Z": 20.0,
    "exp_2026-10-10T21-28-20-920399Z": 20.0,
    "exp_2026-10-14T08-26-18-385545Z": 20.0,
}

#: The benchmark entries whose benchmark signals were committed: the benchmark
#: holds every symbol from the same bar, so its trades share that bar and the
#: published value repeats the bar's value once per symbol.
BENCHMARK_COST_ENTRY_BARS_VERIFIED: dict[str, float] = {
    "exp_2026-10-10T17-02-22-080026Z": 5.0,
    "exp_2026-10-10T17-03-39-610858Z": 5.0,
    "exp_2026-10-10T17-04-21-400695Z": 5.0,
}

#: The families whose trade logs are in the record. §H47 named six of them;
#: the record holds eleven.
H47_FAMILIES: frozenset[str] = frozenset({"H10", "H11", "H16", "H21", "H22", "H25"})

#: The ``stats.json`` files that echo the head of a trade log, cost column
#: included.
STATS_FILES_ECHOING_A_TRADE_LOG = 40


def _committed_trade_logs() -> list[str] | None:
    """The trade-log parquet files the repository tracks.

    ``None`` when this checkout has no git, in which case the committed record
    cannot be enumerated and the scope contract cannot be evaluated at all.
    """
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z", "--", ".experiments/artifacts/*trades*.parquet"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if completed.returncode != 0:
        return None
    return sorted(path for path in completed.stdout.split("\0") if path)


def _load_trade_log(relative: str) -> pd.DataFrame:
    """Read one committed trade log."""
    df = pd.DataFrame(read_parquet_safe(ROOT / relative))
    if len(df) == 0:
        return df
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def _attribution(trades: pd.DataFrame) -> str:
    """Which cost attribution does this log record?

    ``"empty"``     the log holds no trade, so it attributes nothing.
    ``"aggregate"`` every trade of a bar records the bar's whole value: the
                    pre-fix attribution.
    ``"per-trade"`` the trades of a bar record different numbers: the
                    per-trade attribution the engine writes today.
    """
    if len(trades) == 0:
        return "empty"
    per_bar = trades.groupby("timestamp")["cost"]
    return "aggregate" if bool((per_bar.nunique() == 1).all()) else "per-trade"


def _repetition_factor(trades: pd.DataFrame) -> float:
    """How many times the log repeats each bar's value.

    An aggregate log writes a bar's value on every one of its trades, so the
    log repeats it. Under the pre-fix attribution that value *is* the bar's
    charge, so the factor is also the factor by which the recorded column
    over-counts the charge. It is 1 exactly when no bar repeats its value.
    """
    if len(trades) == 0:
        return 1.0
    per_bar = trades.groupby("timestamp")["cost"]
    total = float(per_bar.first().sum())
    if total == 0.0:
        return 1.0
    return float(trades["cost"].sum()) / total


def _run_timestamp(relative: str) -> datetime:
    """The UTC time the run that produced this log started.

    The tracker stamps the artifact id with the start of the run
    (``exp_<UTC timestamp>``), so the id carries the run's own clock.
    """
    artifact_id = Path(relative).parent.name
    stamp = artifact_id.removeprefix("exp_")
    return datetime.strptime(stamp, "%Y-%m-%dT%H-%M-%S-%fZ").replace(tzinfo=timezone.utc)


def _commit_timestamp(commit: str) -> datetime:
    """The UTC time a commit was made.

    The attribution fix's commit is not in this squashed clone, so the
    timestamp is pinned in :data:`ATTRIBUTION_FIX_TIMESTAMP`. When the commit
    *is* present the pinned value is cross-checked against it, so the pin
    cannot silently drift away from the upstream history.
    """
    completed = subprocess.run(
        ["git", "show", "-s", "--format=%cI", commit],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return ATTRIBUTION_FIX_TIMESTAMP
    measured = datetime.fromisoformat(completed.stdout.strip())
    if measured != ATTRIBUTION_FIX_TIMESTAMP:
        raise AssertionError(
            f"the pinned attribution-fix timestamp "
            f"{ATTRIBUTION_FIX_TIMESTAMP.isoformat()} does not match {commit}'s "
            f"{measured.isoformat()}"
        )
    return measured


class TestFrozenRecordScope:
    """H52: the disclosure covers every committed trade log, not one artifact.

    §H47 named the families "H10, H11, H16, H21, H22, H25" and pinned the
    disclosure for **one** artifact. The record is wider on both counts:
    **82** trade logs are committed (the §H47-era scan used a
    ``trades.parquet``-only glob and so saw 41 of them), they span **eleven**
    families plus the exploratory artifacts, and the attribution is pinned here
    for every one.
    """

    def test_the_committed_trade_logs_are_exactly_the_pinned_record(self):
        """A committed trade log that is not named here fails the contract."""
        committed = _committed_trade_logs()
        if committed is None:
            pytest.skip("no git checkout: the committed record cannot be enumerated")
        assert committed == sorted(TRADE_LOG_RECORD)

    def test_every_committed_trade_log_records_the_aggregate_attribution(self):
        """None of the 82 logs records a per-trade attribution."""
        committed = _committed_trade_logs()
        if committed is None:
            pytest.skip("no git checkout: the committed record cannot be enumerated")
        per_trade = [p for p in committed if _attribution(_load_trade_log(p)) == "per-trade"]
        assert per_trade == [], "a committed trade log no longer carries the pre-fix attribution"

    def test_every_committed_trade_log_precedes_the_attribution_fix(self):
        """The decisive leg: no committed log was written by the fixed engine.

        The engine's per-trade attribution fix is committed in
        ``ATTRIBUTION_FIX_COMMIT``; the tracker stamps each artifact id with
        the UTC start of the run that produced it. Every committed log's stamp
        precedes that commit, so every one of them was written by the pre-fix
        engine -- and the pre-fix engine wrote the bar's whole cost on every
        trade of the bar.
        """
        fix = _commit_timestamp(ATTRIBUTION_FIX_COMMIT)
        for relative in TRADE_LOG_RECORD:
            assert _run_timestamp(relative) < fix, relative

    def test_the_logs_whose_attribution_changes_a_number_are_pinned(self):
        measured = {
            path
            for path in TRADE_LOG_RECORD
            if _attribution(_load_trade_log(path)) == "aggregate"
            and _repetition_factor(_load_trade_log(path)) > 1.0
        }
        assert measured == ATTRIBUTION_CHANGES_A_NUMBER

    def test_the_logs_where_the_attribution_cannot_change_a_number_are_pinned(self):
        measured = {
            path
            for path in TRADE_LOG_RECORD
            if _attribution(_load_trade_log(path)) == "aggregate"
            and _repetition_factor(_load_trade_log(path)) == 1.0
        }
        assert measured == ATTRIBUTION_COINCIDES

    def test_the_logs_without_trades_are_pinned(self):
        measured = {
            path for path in TRADE_LOG_RECORD if _attribution(_load_trade_log(path)) == "empty"
        }
        assert measured == NO_TRADES

    def test_the_three_pinned_sets_partition_the_record(self):
        """The split is complete: no committed log is left unclassified."""
        assert ATTRIBUTION_CHANGES_A_NUMBER | ATTRIBUTION_COINCIDES | NO_TRADES == set(
            TRADE_LOG_RECORD
        )
        assert not ATTRIBUTION_CHANGES_A_NUMBER & ATTRIBUTION_COINCIDES
        assert not ATTRIBUTION_CHANGES_A_NUMBER & NO_TRADES
        assert not ATTRIBUTION_COINCIDES & NO_TRADES

    def test_the_measured_structure_of_every_log_is_pinned(self):
        for relative, (n_trades, n_bars, n_multi) in TRADE_LOG_RECORD.items():
            trades = _load_trade_log(relative)
            assert len(trades) == n_trades, relative
            if n_trades == 0:
                assert n_bars == 0 and n_multi == 0, relative
                continue
            assert trades["timestamp"].nunique() == n_bars, relative
            sizes = trades.groupby("timestamp").size()
            assert int((sizes > 1).sum()) == n_multi, relative

    def test_both_kinds_of_log_are_present_in_the_record(self):
        """The split must discriminate: neither side may be empty."""
        assert ATTRIBUTION_CHANGES_A_NUMBER
        assert ATTRIBUTION_COINCIDES
        assert NO_TRADES

    def test_the_repetition_factor_is_never_below_one(self):
        """A log can repeat a bar's value; it can never fall below it."""
        for relative in TRADE_LOG_RECORD:
            assert _repetition_factor(_load_trade_log(relative)) >= 1.0, relative

    def test_the_families_named_by_h47_are_a_strict_subset_of_the_record(self):
        """§H47's list was narrower than the truth; the record is the truth."""
        families: set[str] = set()
        for relative in TRADE_LOG_RECORD:
            summary = ROOT / Path(relative).parent / "summary.json"
            if not summary.exists():
                continue
            with open(summary) as f:
                hypothesis = json.load(f).get("hypothesis")
            if hypothesis:
                families.add(str(hypothesis))
        assert H47_FAMILIES < families, (
            "the families §H47 named are no longer a strict subset of the record"
        )


class TestPublishedCostColumnNumbers:
    """The published numbers that read the trade log's ``cost`` column."""

    def test_the_engine_metric_is_the_only_reader_of_the_cost_column(self):
        """``avg_trade_cost`` is the only number the record derives from it."""
        readers: list[tuple[str, str]] = []
        sources = sorted((ROOT / "src" / "qtr").rglob("*.py")) + sorted(ROOT.glob("run_*.py"))
        for path in sources:
            for line in path.read_text().splitlines():
                if COST_COLUMN_ACCESS.search(line):
                    readers.append((str(path.relative_to(ROOT)), line))
        assert [name for name, _ in readers] == ["src/qtr/backtest/engine.py"]
        assert all("avg_trade_cost" in line for _, line in readers)

    def test_the_published_avg_trade_cost_values_are_pinned(self):
        for relative, (published, factor) in PUBLISHED_COST_NUMBERS.items():
            with open(ROOT / relative) as f:
                summary = json.load(f)
            assert summary["strategy_metrics"]["avg_trade_cost"] == pytest.approx(
                published, rel=1e-12
            ), relative
            log = str(Path(relative).parent / "trades.parquet")
            assert _repetition_factor(_load_trade_log(log)) == pytest.approx(factor, rel=1e-12), (
                relative
            )

    def test_the_published_avg_trade_cost_is_the_recorded_column_mean(self):
        """The published value is the recorded column's mean: the pre-fix basis."""
        for relative, (published, _) in PUBLISHED_COST_NUMBERS.items():
            log = str(Path(relative).parent / "trades.parquet")
            trades = _load_trade_log(log)
            assert float(trades["cost"].mean()) == pytest.approx(published, rel=1e-12), relative

    def test_the_pre_fix_attribution_changes_three_of_the_five_published_values(self):
        changed = {p for p, (_, factor) in PUBLISHED_COST_NUMBERS.items() if factor > 1.0}
        assert len(PUBLISHED_COST_NUMBERS) == 5
        assert len(changed) == 3
        assert changed == {
            ".experiments/artifacts/exp_2026-10-10T17-02-22-080026Z/summary.json",
            ".experiments/artifacts/exp_2026-10-10T17-03-39-610858Z/summary.json",
            ".experiments/artifacts/exp_2026-10-10T17-04-21-400695Z/summary.json",
        }

    def test_the_per_trade_attribution_would_scale_the_published_values(self):
        """The over-statement is exactly the repetition factor."""
        for relative, (published, factor) in PUBLISHED_COST_NUMBERS.items():
            log = str(Path(relative).parent / "trades.parquet")
            trades = _load_trade_log(log)
            bar_total = float(trades.groupby("timestamp")["cost"].first().sum())
            per_trade = bar_total / len(trades)
            assert per_trade == pytest.approx(published / factor, rel=1e-12), relative

    def test_the_benchmark_cost_is_published_on_the_same_basis(self):
        """The tracker metadata publishes the benchmark's cost too."""
        entries = []
        with open(ROOT / ".experiments" / "experiments.jsonl") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                metrics = record.get("metrics", {})
                if "benchmark_avg_trade_cost_step0" in metrics:
                    entries.append(
                        (
                            record["metadata"]["experiment_id"],
                            float(metrics["benchmark_avg_trade_cost_step0"]),
                            int(metrics["benchmark_num_trades_step0"]),
                        )
                    )
        assert {eid: (value, n) for eid, value, n in entries} == BENCHMARK_COST_METADATA

    def test_the_verified_benchmark_over_counts_are_pinned(self):
        """Six benchmarks have a committed trade log: their factor is measured."""
        for experiment_id, factor in BENCHMARK_COST_OVER_COUNT_VERIFIED.items():
            log = f".experiments/artifacts/{experiment_id}/benchmark_trades.parquet"
            trades = _load_trade_log(log)
            assert _repetition_factor(trades) == pytest.approx(factor, rel=1e-12), experiment_id
            published, n_trades = BENCHMARK_COST_METADATA[experiment_id]
            assert n_trades == len(trades)
            assert float(trades["cost"].mean()) == pytest.approx(published, rel=1e-12)

    def test_the_verified_benchmark_entry_bars_are_pinned(self):
        """Three benchmarks have committed signals: they enter on one bar."""
        for experiment_id, factor in BENCHMARK_COST_ENTRY_BARS_VERIFIED.items():
            signals = pd.DataFrame(
                read_parquet_safe(
                    ROOT
                    / ".experiments"
                    / "artifacts"
                    / experiment_id
                    / "signals_buy_and_hold.parquet"
                )
            )
            active = signals.ne(0)
            assert bool(active.any().all()), experiment_id
            first = active.idxmax()
            assert first.nunique() == 1, experiment_id
            assert len(first) == int(factor), experiment_id

    def test_the_stats_files_echo_the_cost_column(self):
        """Forty ``stats.json`` files echo the head of a trade log."""
        echoes = 0
        for path in sorted((ROOT / ".experiments" / "artifacts").rglob("stats.json")):
            with open(path) as f:
                stats = json.load(f)
            if "cost" in stats.get("trades", ""):
                echoes += 1
        assert echoes == STATS_FILES_ECHOING_A_TRADE_LOG


class TestScopeNegativeControl:
    """The scope contract must be able to fail."""

    def test_a_log_whose_trades_differ_is_not_classified_as_aggregate(self):
        """The classifier is discriminating, not vacuous."""
        prices = _prices()
        signals = _unequal_signals(prices)
        result, _ = _run_with_charge(prices, signals)
        assert _attribution(result.trades) == "per-trade"

    def test_the_reconstructed_pre_fix_log_is_classified_as_aggregate(self):
        prices = _prices()
        signals = _unequal_signals(prices)
        result, _ = _run_with_charge(prices, signals)
        pre_fix = result.trades.copy()
        pre_fix["cost"] = result.trades.groupby("timestamp")["cost"].transform("sum")
        assert _attribution(pre_fix) == "aggregate"

    def test_the_repetition_factor_counts_the_repeats(self):
        """The reconstructed pre-fix log repeats the bar's value once per trade."""
        prices = _prices()
        signals = _unequal_signals(prices)
        result, _ = _run_with_charge(prices, signals)
        pre_fix = result.trades.copy()
        pre_fix["cost"] = result.trades.groupby("timestamp")["cost"].transform("sum")
        sizes = result.trades.groupby("timestamp").size()
        assert sizes.max() == 2
        assert _repetition_factor(pre_fix) == pytest.approx(2.0, rel=1e-12)

    def test_a_single_symbol_log_repeats_nothing(self):
        """With one symbol the two attributions coincide, by construction."""
        prices = _prices(symbols=("A",))
        signals = _simultaneous_signals(prices)
        result, _ = _run_with_charge(prices, signals)
        assert _attribution(result.trades) == "aggregate"
        assert _repetition_factor(result.trades) == pytest.approx(1.0, rel=1e-12)
