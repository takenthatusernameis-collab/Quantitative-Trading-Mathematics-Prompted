"""H56 -- the `stats.json` text echoes and the 14 benchmark `avg_trade_cost` entries.

Both halves are *disclosure* tasks, not verification tasks: neither can move
a published number, and both are bounded by the frozen record. Nothing under
`src/qtr` changes, no grid is re-run, nothing is written.

1. The `stats.json` text echoes --- 40 files
   --------------------------------
   The committed record holds 40 `stats.json` files, one per strategy variant
   of the six H18 overnight/intraday runs (2026-10-13). Each one publishes
   two text fields:

   - `returns` -- a pandas repr of the strategy's daily return series, rounded
     to display precision and truncated: five head rows, a `...` truncation
     line, five tail rows, then `Length: N, dtype: float64`.
   - `trades` -- the head of a trade log as text.

   §H55 already measured that `returns` re-derives from the `equity.parquet`
   committed beside it, provided the H18 family's initial capital of 100 000
   is used rather than the 1 000 000 every other producer uses
   (`equity[0] / capital - 1` for the first bar, then bar-over-bar returns).
   This contract pins the exact display convention: the published string must
   equal

       series.to_string(max_rows=10) + "\nLength: {n}, dtype: {dtype}"

   computed from the committed equity curve, byte for byte, for all 40 files.
   It also pins that the `trades` text is *not* recoverable: every one of the
   40 directories holds exactly `{equity.parquet, stats.json}` -- no trade log
   was ever committed -- and all 40 publish the same constant dummy head, so
   the text is disclosed as unrecoverable rather than reconstructed.

2. The 14 benchmark `avg_trade_cost` entries
   ------------------------------------------
   The tracker log (`.experiments/experiments.jsonl`) holds 23
   `benchmark_avg_trade_cost_step0` entries. §H52 verified 9 of them against
   the committed record (6 x 20.0x against the committed benchmark trade log
   of 20 ETFs entering on one bar; 3 x 5x against the committed
   `signals_buy_and_hold.parquet` of the ma_crossover buy-and-hold benchmark,
   all five symbols entering on one bar). The other 14 -- futures_tsmom,
   ddcv_futures_tsmom and h6_vix_ddcv_futures_tsmom runs, all publishing
   `0.00010629059079463798` -- commit only `benchmark_equity.parquet` for the
   benchmark: no `benchmark_trades.parquet` and no benchmark signals file was
   ever committed. The benchmark's weight changes over time are not a function
   of the record, so the benchmark cannot be rebuilt (the §H55 route-2 style
   re-derivation is unavailable) and its over-count factor is not measurable.
   It is disclosed as remaining on the pre-fix basis, exactly as §H52 states.

   This contract enumerates all 23 entries, pins the 9 measurable ones and the
   14 not-measurable ones, and verifies that none of the 14 has a committed
   equity curve *and* a committed signal that would let the benchmark be
   rebuilt.
"""

from __future__ import annotations

import json
import pathlib
import sys

import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(ROOT / "tests"))
from _utils_parquet import read_parquet_safe  # noqa: E402

STATS_ROOT = ROOT / ".experiments" / "artifacts"
TRACKER = ROOT / ".experiments" / "experiments.jsonl"

#: The H18 family starts every book from 100 000, not the 1 000 000 every
#: other producer uses (§H55 measured this; this contract pins it).
CAPITAL = 100_000.0

#: The value all 14 non-measurable benchmark entries publish.
BENCHMARK_COST_UNMEASURABLE = 0.00010629059079463798

#: The six measurable entries verified against the committed benchmark trade
#: log (20 ETFs on one bar: a 20.0x repetition factor per §H52).
BENCHMARK_MEASURABLE_VIA_TRADE_LOG = {
    "exp_2026-10-10T20-56-30-507309Z",
    "exp_2026-10-10T20-57-26-136503Z",
    "exp_2026-10-10T21-08-54-188263Z",
    "exp_2026-10-10T21-27-13-928282Z",
    "exp_2026-10-10T21-28-20-920399Z",
    "exp_2026-10-14T08-26-18-385545Z",
}

#: The three measurable entries verified against the committed buy-and-hold
#: benchmark signals (5 symbols on one bar: a 5x repetition factor per §H52).
BENCHMARK_MEASURABLE_VIA_SIGNALS = {
    "exp_2026-10-10T17-02-22-080026Z",
    "exp_2026-10-10T17-03-39-610858Z",
    "exp_2026-10-10T17-04-21-400695Z",
}

#: The 14 entries whose benchmark trade log and signals were never committed.
BENCHMARK_NOT_MEASURABLE = {
    "exp_2026-10-10T21-58-07-833835Z",
    "exp_2026-10-10T21-58-28-353634Z",
    "exp_2026-10-10T21-59-16-546117Z",
    "exp_2026-10-10T22-59-01-182037Z",
    "exp_2026-10-11T00-25-56-751422Z",
    "exp_2026-10-11T00-26-08-362690Z",
    "exp_2026-10-11T00-26-18-281925Z",
    "exp_2026-10-11T00-26-35-750834Z",
    "exp_2026-10-11T00-34-05-381535Z",
    "exp_2026-10-11T02-44-40-301520Z",
    "exp_2026-10-11T02-46-37-311994Z",
    "exp_2026-10-11T07-18-39-160945Z",
    "exp_2026-10-11T08-02-22-999214Z",
    "exp_2026-10-14T08-27-02-650342Z",
}


def _stats_files() -> list[pathlib.Path]:
    files = sorted(STATS_ROOT.glob("*/*/stats.json"))
    assert files, f"no stats.json found under {STATS_ROOT}"
    return files


STATS_FILES = _stats_files()


def _load_stats(path: pathlib.Path) -> dict:
    return json.loads(path.read_text())


def _derived_returns_text(equity: pd.Series, capital: float) -> str:
    """The engine's return convention: first bar vs capital, then bar over bar.

    The division is positional so a DatetimeIndex never misaligns the two
    sides (§H51's container-independence lesson, applied to the record).
    """
    returns = equity / capital - 1.0
    returns.iloc[1:] = equity.iloc[1:].to_numpy() / equity.iloc[:-1].to_numpy() - 1.0
    return returns.to_string(max_rows=10) + f"\nLength: {len(returns)}, dtype: {returns.dtype}"


class TestStatsEchoEnumeration:
    """The record's shape is pinned: it must not move underfoot."""

    def test_there_are_forty_stats_json_files(self):
        assert len(STATS_FILES) == 40

    def test_they_live_in_six_h18_experiment_directories(self):
        experiments = {p.parent.parent.name for p in STATS_FILES}
        assert experiments == {
            "exp_2026-10-13T22-12-11-288084Z",
            "exp_2026-10-13T22-13-11-327754Z",
            "exp_2026-10-13T22-13-37-475937Z",
            "exp_2026-10-13T22-14-03-861826Z",
            "exp_2026-10-13T22-14-26-107907Z",
            "exp_2026-10-13T22-14-50-729923Z",
        }

    def test_each_directory_holds_only_equity_and_stats(self):
        for path in STATS_FILES:
            names = {child.name for child in path.parent.iterdir()}
            assert names == {"equity.parquet", "stats.json"}

    def test_every_equity_curve_has_forty_four_hundred_sixty_eight_rows(self):
        for path in STATS_FILES:
            equity = read_parquet_safe(path.parent / "equity.parquet")
            assert len(equity) == 4468


class TestStatsEchoReturns:
    """The `returns` text re-derives from the committed equity curve, exactly."""

    @pytest.mark.parametrize("path", STATS_FILES, ids=lambda p: str(p.relative_to(ROOT)))
    def test_returns_re_derives_byte_for_byte(self, path):
        stats = _load_stats(path)
        equity = read_parquet_safe(path.parent / "equity.parquet").iloc[:, 0]
        assert _derived_returns_text(equity, CAPITAL) == stats["returns"]

    @pytest.mark.parametrize("path", STATS_FILES, ids=lambda p: str(p.relative_to(ROOT)))
    def test_the_capital_is_one_hundred_thousand_not_one_million(self, path):
        """Behavioural negative control: the convention every other producer
        uses (1 000 000) does *not* reproduce the published text -- the first
        bar becomes -0.900020 instead of -0.000200 -- so the 100 000 anchor is
        load-bearing, not incidental."""
        stats = _load_stats(path)
        equity = read_parquet_safe(path.parent / "equity.parquet").iloc[:, 0]
        assert _derived_returns_text(equity, 1_000_000.0) != stats["returns"]

    @pytest.mark.parametrize("path", STATS_FILES, ids=lambda p: str(p.relative_to(ROOT)))
    def test_the_truncation_convention_is_load_bearing(self, path):
        """The untruncated repr (all 4468 rows) is not what was published:
        the `max_rows=10` truncation is part of the convention."""
        stats = _load_stats(path)
        equity = read_parquet_safe(path.parent / "equity.parquet").iloc[:, 0]
        returns = equity / CAPITAL - 1.0
        returns.iloc[1:] = equity.iloc[1:].to_numpy() / equity.iloc[:-1].to_numpy() - 1.0
        assert returns.to_string() != stats["returns"]

    @pytest.mark.parametrize("path", STATS_FILES, ids=lambda p: str(p.relative_to(ROOT)))
    def test_a_nudged_first_value_fails_exact_match(self, path):
        stats = _load_stats(path)
        equity = read_parquet_safe(path.parent / "equity.parquet").iloc[:, 0]
        derived = _derived_returns_text(equity, CAPITAL)
        nudged = derived.replace("-0.000200", "-0.000201", 1)
        assert nudged != stats["returns"]
        assert derived == stats["returns"]

    def test_the_published_display_convention(self):
        """Five head rows, a 16-space `...   ` truncation line, five tail
        rows, then `Length: {n}, dtype: float64` -- pinned on one file and
        re-derived byte for byte on all forty by the tests above."""
        path = STATS_FILES[0]
        lines = _load_stats(path)["returns"].splitlines()
        assert lines[0] == "Date"
        assert len(lines) == 13
        assert lines[6] == "                ...   "
        assert lines[-1] == "Length: 4468, dtype: float64"
        import re

        row = re.compile(r"^\d{4}-\d{2}-\d{2}\s+-?\d+\.\d{6}$")
        assert all(row.match(line) for line in lines[1:6])
        assert all(row.match(line) for line in lines[7:12])


class TestStatsEchoTrades:
    """The `trades` text is not recoverable from the record."""

    def test_all_forty_publish_the_identical_trades_head(self):
        texts = {_load_stats(p)["trades"] for p in STATS_FILES}
        assert len(texts) == 1

    def test_the_trades_text_is_the_dummy_first_row(self):
        (text,) = {_load_stats(p)["trades"] for p in STATS_FILES}
        assert text == (
            "   timestamp symbol side  weight_change  price    cost\n"
            "0 2009-01-02    SPY  buy            1.0    1.0  0.0002"
        )

    def test_no_trade_log_was_ever_committed_beside_stats_json(self):
        for path in STATS_FILES:
            names = {child.name for child in path.parent.iterdir()}
            assert "trades.parquet" not in names
            assert not any(name.startswith("trades_") for name in names)
        # consequently the `trades` text cannot be reconstructed from the
        # record: equity curves carry no trade counts or costs. Disclosed.


class TestBenchmarkEntries:
    """The 23 tracker entries publishing `benchmark_avg_trade_cost_step0`."""

    def _tracker_entries(self) -> list[dict]:
        entries = []
        for line in TRACKER.read_text().strip().splitlines():
            record = json.loads(line)
            metrics = record.get("metrics", {})
            if "benchmark_avg_trade_cost_step0" in metrics:
                entries.append(
                    {
                        "experiment_id": record["metadata"]["experiment_id"],
                        "name": record["metadata"]["name"],
                        "value": metrics["benchmark_avg_trade_cost_step0"],
                    }
                )
        assert entries, "no benchmark_avg_trade_cost_step0 entries in tracker"
        return entries

    def test_there_are_twenty_three_tracker_entries(self):
        entries = self._tracker_entries()
        assert len(entries) == 23

    def test_the_entries_split_nine_measurable_and_fourteen_not(self):
        entries = self._tracker_entries()
        measurable_value_entries = [e for e in entries if e["value"] != BENCHMARK_COST_UNMEASURABLE]
        assert len(measurable_value_entries) == 9
        unmeasurable = [e for e in entries if e["value"] == BENCHMARK_COST_UNMEASURABLE]
        assert len(unmeasurable) == 14
        assert {e["experiment_id"] for e in unmeasurable} == BENCHMARK_NOT_MEASURABLE

    def test_the_six_measurable_via_trade_log_commit_benchmark_trades(self):
        for experiment_id in BENCHMARK_MEASURABLE_VIA_TRADE_LOG:
            directory = STATS_ROOT / experiment_id
            names = {child.name for child in directory.iterdir()}
            assert "benchmark_trades.parquet" in names
            # twenty trades on one bar: the 20.0x repetition factor §H52 measured.
            trades = read_parquet_safe(directory / "benchmark_trades.parquet")
            assert len(trades) == 20
            assert trades["timestamp"].nunique() == 1

    def test_the_three_measurable_via_signals_commit_buy_and_hold_signals(self):
        for experiment_id in BENCHMARK_MEASURABLE_VIA_SIGNALS:
            directory = STATS_ROOT / experiment_id
            names = {child.name for child in directory.iterdir()}
            assert "signals_buy_and_hold.parquet" in names
            assert "benchmark_trades.parquet" not in names

    @pytest.mark.parametrize(
        "experiment_id",
        sorted(BENCHMARK_NOT_MEASURABLE),
        ids=lambda eid: eid,
    )
    def test_not_measurable_entries_commit_only_benchmark_equity(self, experiment_id):
        """The benchmark's trade log and signals were never committed: only
        `benchmark_equity.parquet` exists for the benchmark, so the benchmark
        cannot be rebuilt and its over-count factor is not measurable."""
        directory = STATS_ROOT / experiment_id
        names = {child.name for child in directory.iterdir()}
        assert "benchmark_equity.parquet" in names
        assert "benchmark_trades.parquet" not in names
        assert not any(name.startswith("signals_") for name in names)
        assert not any(
            name.startswith("benchmark_") and name.endswith("trades.parquet") for name in names
        )

    def test_all_fourteen_publish_the_same_unmeasurable_value(self):
        entries = self._tracker_entries()
        values = {e["value"] for e in entries if e["experiment_id"] in BENCHMARK_NOT_MEASURABLE}
        assert values == {BENCHMARK_COST_UNMEASURABLE}
