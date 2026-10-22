"""H57 -- the equity record is on a **price-return** basis.

The gap
-------
Every runner builds its price series from the vendor's **raw close**. The
vendor's total-return column (``adj_close``) is committed into the same
cache file (``src/qtr/data/fetcher.py``, ``auto_adjust=False``) and is
never read by a producer. Two consequences follow, and neither was stated
anywhere in the record before H57:

1. **Every equity return series in the record is a price return.** The
   dividends and distributions the record omits are not negligible: the
   committed cache measures an annualised gap of **1.81 %/yr** for SPY over
   2009-2026 and **8.00 %/yr** for PDBC over 2015-2024.
2. **A distribution ex-date is booked as a loss.** On the ex-date the raw
   close drops by the distribution while the total-return series does not
   move, so a position held through the ex-date books a realised loss that
   never happened. The committed PDBC series holds **three** such *level
   bars**.

Why it is decision-relevant
---------------------------
The published **benchmark-significance gate** (``p < 0.05``) is evaluated
against a dividend-excluded benchmark. H57 asks whether the *magnitude* of
the excess return -- and therefore the p-value -- survives the total-return
convention.

What H57 measures
-----------------
============  ==================================================  =========
measured      quantity                                            value
============  ==================================================  =========
families      audited                                               **6**
gate blocks   published (H1, H3)                                   **2**
gate blocks   that move under the counterfactual                   **0**
counterfact.  informative (a family whose universe carries no      **5**
              adjustment cannot be measured at all -- H17)
files         committed cache files                                **82**
files         indexed by the audit                                 **59**
files         not indexed (the CCXT crypto files, no ex-date)      **23**
symbols       distribution profiles measured                       **37**
bars          the correction could not reach                       **0**
============  ==================================================  =========

What this module pins
---------------------
1. The audit **re-derives**: ``run_h57_total_return_audit.build_report()``
   rebuilds the committed ``summary.json`` leaf for leaf, from the
   committed cache and the committed artifacts alone.
2. The **control** reproduces each family's published comparison, so the
   counterfactual is measured against the published record and not against a
   reconstruction of it.
3. The **convention** is what the audit claims it is: no producer runner
   reads ``adj_close``, and the fetcher commits the raw close.
4. The **counterfactual** is complete (no bar is silently dropped) and it
   bites (the correction is not a no-op on the informative families).
5. The **verdict impact**: no published gate boolean moves, and the three
   families carrying a published ``p`` PASS stay below 0.05.
6. The **disclosure** itself: the measured gap, the three PDBC level bars
   and the symbols the record carries no adjustment for.
7. The **independence** of the audit from the engine: with the backtest
   engine disabled, the audit still rebuilds the committed summary leaf for
   leaf, so the engine's ``total_return`` metric (§H38) cannot be
   load-bearing for anything the audit publishes.

Every number is a read of the frozen artifacts. Nothing is written, no grid
is re-run, no gate, threshold, verdict or certified number is touched, and
the audit is **disclosed, not repaired**: the record stays on the price-return
basis.
"""

from __future__ import annotations

import ast
import json
import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
for _path in (str(ROOT), str(ROOT / "src"), str(ROOT / "tests")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from _utils_parquet import read_parquet_safe  # noqa: E402

import run_h57_total_return_audit as h57  # noqa: E402
from qtr.validation.statistics import compare_to_benchmark  # noqa: E402

ARTIFACTS = ROOT / ".experiments" / "artifacts"
H57_DIR = ARTIFACTS / "h57_total_return"
SUMMARY_PATH = H57_DIR / "summary.json"
CACHE_DIR = ROOT / ".cache" / "data"

#: The audit's own tolerance: the published values are float64 round-trips of
#: the same computation, so they agree to ~1e-12 relative.
TOLERANCE = 1e-9

#: Two families (H1 and H3) publish the comparison rounded to four decimals;
#: the control reproduces them to that step, not to the last bit.
PUBLISHED_ROUNDING_STEP = 1e-4

#: The families under audit, as the runner declares them.
FAMILIES = h57.FAMILIES
FAMILY_BY_ID = {spec["hypothesis"]: spec for spec in FAMILIES}

#: The audit's runner. It is the only file in the repository that reads the
#: vendor's total-return column, and it reads it to *measure* the gap.
AUDIT_RUNNER = "run_h57_total_return_audit.py"


# ---------------------------------------------------------------------------
# The committed artifact
# ---------------------------------------------------------------------------
def _committed_summary() -> dict:
    assert SUMMARY_PATH.exists(), f"the H57 artifact is missing: {SUMMARY_PATH}"
    return json.loads(SUMMARY_PATH.read_text())


COMMITTED = _committed_summary()


def _family(hypothesis: str) -> dict:
    for family in COMMITTED["families"]:
        if family["hypothesis"] == hypothesis:
            return family
    raise AssertionError(f"{hypothesis} is not in the committed H57 summary")


_REBUILT: dict | None = None


def _rebuilt() -> dict:
    """The audit, rebuilt from the committed record.

    The rebuild is done once: the audit reads the whole committed cache and
    every audited artifact, and the result is a pure function of them.
    """
    global _REBUILT
    if _REBUILT is None:
        _REBUILT = h57.build_report()
    return _REBUILT


def _leaves(value, path: str = ""):
    """Every published leaf, as ``(path, value)`` pairs."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _leaves(child, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _leaves(child, f"{path}[{index}]")
    else:
        yield path, value


# ---------------------------------------------------------------------------
# 1. The record's shape
# ---------------------------------------------------------------------------
class TestTheRecord:
    """The record H57 audits must not move underfoot."""

    def test_six_families_are_audited(self):
        assert len(COMMITTED["families"]) == 6
        assert [f["hypothesis"] for f in COMMITTED["families"]] == [
            "H1",
            "H3",
            "H16",
            "H17",
            "H19",
            "H20",
        ]

    def test_every_family_was_audited(self):
        for family in COMMITTED["families"]:
            assert family["status"] == "audited", family["hypothesis"]

    def test_the_cache_coverage_is_disclosed(self):
        coverage = COMMITTED["cache_coverage"]
        assert coverage["n_cache_files_on_disk"] == 82
        assert coverage["n_cache_files_indexed"] == 59
        assert coverage["n_cache_files_not_indexed"] == 23
        # the 23 unindexed files are the CCXT crypto ones: their cache key
        # carries an ``exchange_id:`` prefix, and a crypto spot series has
        # no ex-date, so they are outside the question.
        assert len(list(CACHE_DIR.glob("*.parquet"))) == 82

    def test_thirty_seven_symbol_profiles_are_measured(self):
        assert len(COMMITTED["symbol_profiles"]) == 37
        assert "SPY" in COMMITTED["symbol_profiles"]
        assert "^VIX3M" in COMMITTED["symbol_profiles"]

    def test_the_audit_is_declared_as_an_audit(self):
        assert COMMITTED["hypothesis"] == "H57"
        assert COMMITTED["kind"] == "audit_of_the_published_record"
        assert COMMITTED["preregistered_in"] == "HYPOTHESIS_SPEC.md §H57"


# ---------------------------------------------------------------------------
# 2. The audit re-derives
# ---------------------------------------------------------------------------
class TestTheAuditReDerives:
    """``build_report()`` rebuilds the committed summary from the record."""

    def test_the_rebuild_reproduces_every_published_leaf(self):
        committed = {k: v for k, v in _leaves(COMMITTED) if k != "elapsed_sec"}
        rebuilt = {k: v for k, v in _leaves(_rebuilt()) if k != "elapsed_sec"}
        assert set(committed) == set(rebuilt)
        mismatches = [
            (path, committed[path], rebuilt[path])
            for path in committed
            if not _agrees(committed[path], rebuilt[path])
        ]
        assert mismatches == [], mismatches[:5]

    def test_the_rebuild_is_deterministic(self):
        """The audit must not depend on the order the cache is read in.

        Several cache windows cover a family's index equally well, and the
        vendor's adjustment factors differ slightly between fetches; an
        arbitrary pick would make the audit's numbers depend on the
        process's hash seed.
        """
        first = dict(_rebuilt())
        second = h57.build_report()
        for report in (first, second):
            report.pop("elapsed_sec", None)
        assert json.dumps(first, sort_keys=True, default=str) == json.dumps(
            second, sort_keys=True, default=str
        )

    def test_the_elapsed_time_is_the_only_unreproducible_leaf(self):
        """``elapsed_sec`` is a runtime measurement, not a fact about the
        record; it is the one leaf the audit cannot re-derive."""
        committed_paths = {path for path, _ in _leaves(COMMITTED)}
        assert "elapsed_sec" in committed_paths
        rebuilt = _rebuilt()
        assert isinstance(rebuilt["elapsed_sec"], float)
        assert rebuilt["elapsed_sec"] >= 0.0

    def test_a_nudged_leaf_breaks_the_re_derivation(self):
        """Behavioural negative control: the re-derivation is not vacuous."""
        committed = dict(_leaves(COMMITTED))
        committed["families[2].counterfactual_total_return.alpha_p_value"] = 0.5
        rebuilt = dict(_leaves(_rebuilt()))
        path = "families[2].counterfactual_total_return.alpha_p_value"
        assert not _agrees(committed[path], rebuilt[path])


def _agrees(published, rederived) -> bool:
    """Do a published leaf and its reconstruction agree?"""
    if isinstance(published, bool) or isinstance(rederived, bool):
        return bool(published) == bool(rederived)
    if isinstance(published, (int, float)) and isinstance(rederived, (int, float)):
        return abs(published - rederived) <= TOLERANCE * max(1.0, abs(published))
    return published == rederived


# ---------------------------------------------------------------------------
# 3. The audit is independent of the engine
# ---------------------------------------------------------------------------
class TestTheEngineIndependence:
    """The audit must not be a function of the engine's metric.

    The engine's ``total_return`` was the subject of §H38: it used to span
    the wrong horizon. If the audit -- or any other runner -- selected on
    it, a change to the metric would move a published number. The audit
    reads the committed record and the committed cache, so it must never
    reach the engine at all; the check below proves that behaviourally
    rather than by reading the source.
    """

    def test_the_audit_reproduces_itself_with_the_engine_disabled(self, monkeypatch):
        """With the engine disabled, the audit still rebuilds the committed
        summary leaf for leaf: the engine's metric cannot be load-bearing
        for anything the audit publishes."""
        import qtr.backtest.engine as engine

        def _explode(*args, **kwargs):
            raise AssertionError("the audit must not run the backtest engine")

        monkeypatch.setattr(engine, "run_backtest", _explode)
        monkeypatch.setattr(engine, "BacktestConfig", _explode)

        rebuilt = h57.build_report()
        committed = {k: v for k, v in _leaves(COMMITTED) if k != "elapsed_sec"}
        rebuilt_leaves = {k: v for k, v in _leaves(rebuilt) if k != "elapsed_sec"}
        assert set(committed) == set(rebuilt_leaves)
        mismatches = [
            (path, committed[path], rebuilt_leaves[path])
            for path in committed
            if not _agrees(committed[path], rebuilt_leaves[path])
        ]
        assert mismatches == [], mismatches[:5]

    def test_the_sabotage_is_live(self, monkeypatch):
        """Negative control: the sabotage above really disables the engine,
        so the check is not vacuous."""
        import qtr.backtest.engine as engine

        def _explode(*args, **kwargs):
            raise AssertionError("the engine is disabled")

        monkeypatch.setattr(engine, "run_backtest", _explode)
        with pytest.raises(AssertionError):
            engine.run_backtest(prices=None, signals=None, config=None)


# ---------------------------------------------------------------------------
# 3. The control reproduces the published comparison
# ---------------------------------------------------------------------------
class TestTheControl:
    """The audit's control must reproduce what the family published."""

    @pytest.mark.parametrize("hypothesis", sorted(FAMILY_BY_ID), ids=lambda h: h)
    def test_the_control_reproduces_the_published_information_ratio(self, hypothesis):
        family = _family(hypothesis)
        published = family["published"]["information_ratio"]
        control = family["control"]["information_ratio"]
        assert abs(control - published) <= PUBLISHED_ROUNDING_STEP

    @pytest.mark.parametrize("hypothesis", sorted(FAMILY_BY_ID), ids=lambda h: h)
    def test_the_control_reproduces_the_published_p_value(self, hypothesis):
        family = _family(hypothesis)
        published = family["published"]["alpha_p_value"]
        control = family["control"]["alpha_p_value"]
        assert abs(control - published) <= PUBLISHED_ROUNDING_STEP

    @pytest.mark.parametrize("hypothesis", ["H16", "H17", "H19", "H20"], ids=lambda h: h)
    def test_the_full_precision_families_reproduce_their_published_value_exactly(self, hypothesis):
        """Four families publish the comparison at full float precision; the
        control reproduces them to the last bit, not merely to the published
        rounding step."""
        family = _family(hypothesis)
        assert (
            abs(family["control"]["alpha_p_value"] - family["published"]["alpha_p_value"])
            <= TOLERANCE
        )

    @pytest.mark.parametrize("hypothesis", sorted(FAMILY_BY_ID), ids=lambda h: h)
    def test_the_positions_reproduce_the_published_equity_curve(self, hypothesis):
        """The engine's own convention -- the position of the previous bar
        earns the bar's return -- must reconstruct the published return
        series up to the costs the engine charges."""
        family = _family(hypothesis)
        residual = family["control"]["strategy_return_from_positions_max_abs_diff"]
        assert residual is not None
        assert residual < 5e-3

    def test_the_control_reproduces_the_published_comparison_independently(self):
        """A second, independent reconstruction of H3's control.

        The positions are rebuilt here from the engine's own rules rather
        than from the runner's helper, so the control binds the record and
        not the runner.
        """
        spec = FAMILY_BY_ID["H3"]
        art = ARTIFACTS / spec["artifact"]
        prices = read_parquet_safe(art / "prices.parquet").apply(pd.to_numeric, errors="coerce")
        equity = read_parquet_safe(art / "selected_equity.parquet").iloc[:, 0].astype(float)
        benchmark = read_parquet_safe(art / "benchmark_equity.parquet").iloc[:, 0].astype(float)
        signals = (
            read_parquet_safe(art / "selected_signals.parquet")
            .apply(pd.to_numeric, errors="coerce")
            .reindex(columns=prices.columns)
        )

        positions = signals.ffill().fillna(0.0)
        gross = positions.abs().sum(axis=1)
        over = gross > 5.0
        positions.loc[over] = positions.loc[over].div(gross[over], axis=0) * 5.0
        positions = positions.clip(-2.0, 2.0)

        returns = equity.pct_change()
        bench_returns = benchmark.pct_change()
        window = equity.index[equity.index >= pd.Timestamp(spec["oos_start"])]
        strat = returns.reindex(window)
        bench = bench_returns.reindex(window).ffill()
        mask = ~(strat.isna() | bench.isna())

        rebuilt = compare_to_benchmark(strat[mask].to_numpy(), bench[mask].to_numpy())
        family = _family("H3")
        assert (
            abs(rebuilt["information_ratio"] - family["control"]["information_ratio"]) <= TOLERANCE
        )
        assert abs(rebuilt["alpha_p_value"] - family["control"]["alpha_p_value"]) <= TOLERANCE
        assert abs(rebuilt["alpha_t_stat"] - family["control"]["alpha_t_stat"]) <= TOLERANCE


# ---------------------------------------------------------------------------
# 4. The convention the audit claims
# ---------------------------------------------------------------------------
def _references_adj_close(source: str) -> bool:
    """Does the source read the vendor's total-return column?"""
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Constant) and node.value == "adj_close":
            return True
        if isinstance(node, ast.Attribute) and node.attr == "adj_close":
            return True
    return False


class TestTheConvention:
    """The audit's premise: the record is on the raw close."""

    def test_no_producer_runner_reads_the_total_return_column(self):
        runners = [path for path in sorted(ROOT.glob("run_*.py")) if path.name != AUDIT_RUNNER]
        assert runners
        offenders = [path.name for path in runners if _references_adj_close(path.read_text())]
        assert offenders == []

    def test_the_audit_runner_does_read_it(self):
        """Negative control for the check above: it is not vacuous."""
        assert _references_adj_close((ROOT / AUDIT_RUNNER).read_text())

    def test_the_check_fires_on_a_runner_that_reads_the_column(self):
        """Behavioural negative control: a synthetic runner that reads
        ``adj_close`` is detected."""
        source = 'prices = pd.DataFrame({s: df["adj_close"] for s in UNIVERSE})\n'
        assert _references_adj_close(source)

    def test_the_fetcher_commits_the_raw_close_and_the_total_return_column(self):
        """The premise of the gap: the cache holds the vendor's *raw* close
        (the fetcher asks for ``auto_adjust=False``) next to the total-return
        column, so the record *could* have been built on total returns and
        was not."""
        fetcher = (ROOT / "src" / "qtr" / "data" / "fetcher.py").read_text()
        assert "auto_adjust=False" in fetcher
        assert "adj_close" in fetcher

    def test_the_audit_says_so_in_its_own_words(self):
        convention = COMMITTED["convention"]
        assert "price return" in convention
        assert "adj_close" in convention


# ---------------------------------------------------------------------------
# 5. The counterfactual is complete, and it bites
# ---------------------------------------------------------------------------
class TestTheCounterfactual:
    """The correction must reach every bar and must not be a no-op."""

    @pytest.mark.parametrize("hypothesis", sorted(FAMILY_BY_ID), ids=lambda h: h)
    def test_no_bar_is_silently_dropped(self, hypothesis):
        """A bar on which a price is known but its distribution is not is a
        bar the correction cannot reach. It must be counted, not dropped:
        a silent zero would understate the correction without saying so."""
        assert _family(hypothesis)["correction_unreachable_bars"] == 0

    @pytest.mark.parametrize("hypothesis", ["H1", "H3", "H16", "H19", "H20"], ids=lambda h: h)
    def test_the_correction_bites(self, hypothesis):
        family = _family(hypothesis)
        counterfactual = family["counterfactual_total_return"]
        assert counterfactual["mean_strategy_distribution_per_bar"] != 0.0
        assert counterfactual["mean_benchmark_distribution_per_bar"] != 0.0
        assert family["control"]["alpha_p_value"] != counterfactual["alpha_p_value"]

    def test_h17_cannot_be_measured_and_says_so(self):
        """SVXY is the H17 family's only symbol *and* its benchmark, and the
        committed cache carries no adjustment for it: the counterfactual is
        the control by construction. That is a null result, not a finding."""
        family = _family("H17")
        assert family["symbols_without_adjustment"] == ["SVXY"]
        assert family["counterfactual_informative"] is False
        control = family["control"]["alpha_p_value"]
        counterfactual = family["counterfactual_total_return"]["alpha_p_value"]
        assert abs(control - counterfactual) <= TOLERANCE

    def test_the_five_other_families_are_informative(self):
        for hypothesis in ("H1", "H3", "H16", "H19", "H20"):
            assert _family(hypothesis)["counterfactual_informative"] is True

    def test_the_counterfactual_is_rebuilt_independently(self):
        """A second, independent reconstruction of H3's counterfactual.

        The total-return series is taken from the very cache file the audit
        names, the positions are rebuilt from the engine's rules, and the
        comparison is recomputed with the library's own function.
        """
        spec = FAMILY_BY_ID["H3"]
        family = _family("H3")
        art = ARTIFACTS / spec["artifact"]
        prices = read_parquet_safe(art / "prices.parquet").apply(pd.to_numeric, errors="coerce")
        equity = read_parquet_safe(art / "selected_equity.parquet").iloc[:, 0].astype(float)
        benchmark = read_parquet_safe(art / "benchmark_equity.parquet").iloc[:, 0].astype(float)
        signals = (
            read_parquet_safe(art / "selected_signals.parquet")
            .apply(pd.to_numeric, errors="coerce")
            .reindex(columns=prices.columns)
        )

        positions = signals.ffill().fillna(0.0)
        gross = positions.abs().sum(axis=1)
        over = gross > 5.0
        positions.loc[over] = positions.loc[over].div(gross[over], axis=0) * 5.0
        positions = positions.clip(-2.0, 2.0)

        price_returns = prices.pct_change()
        total_returns = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
        for symbol in prices.columns:
            frame = read_parquet_safe(CACHE_DIR / family["cache_file_used"][symbol])
            adj = frame["adj_close"].astype(float).reindex(prices.index)
            total_returns[symbol] = adj.pct_change()
        distribution = total_returns - price_returns

        strategy = equity.pct_change() + (positions.shift(1) * distribution).sum(axis=1)
        bench = benchmark.pct_change() + distribution.mean(axis=1)

        window = equity.index[equity.index >= pd.Timestamp(spec["oos_start"])]
        strat = strategy.reindex(window)
        bench_oos = bench.reindex(window)
        mask = ~(strat.isna() | bench_oos.isna())

        rebuilt = compare_to_benchmark(strat[mask].to_numpy(), bench_oos[mask].to_numpy())
        counterfactual = family["counterfactual_total_return"]
        assert abs(rebuilt["information_ratio"] - counterfactual["information_ratio"]) <= TOLERANCE
        assert abs(rebuilt["alpha_p_value"] - counterfactual["alpha_p_value"]) <= TOLERANCE
        assert abs(rebuilt["alpha_t_stat"] - counterfactual["alpha_t_stat"]) <= TOLERANCE


# ---------------------------------------------------------------------------
# 6. The verdict impact
# ---------------------------------------------------------------------------
class TestTheVerdictImpact:
    """No published gate boolean may move."""

    def test_no_published_gate_boolean_moves(self):
        tally = COMMITTED["verdict_tally"]
        assert tally["n_gate_booleans_published"] == 2
        assert tally["n_gate_booleans_moved"] == 0
        for family in COMMITTED["families"]:
            assert family["verdict_impact"]["gate_boolean_moves"] is False

    def test_the_two_published_gate_blocks_keep_their_boolean(self):
        h1 = _family("H1")["verdict_impact"]
        h3 = _family("H3")["verdict_impact"]
        assert h1["published_pass"] is False and h1["counterfactual_pass"] is False
        assert h3["published_pass"] is True and h3["counterfactual_pass"] is True

    def test_the_three_published_p_passes_stay_below_the_threshold(self):
        """H3, H19 and H20 publish a p-value below 0.05. The counterfactual
        moves each of them further from the boundary, not across it."""
        for hypothesis in ("H3", "H19", "H20"):
            family = _family(hypothesis)
            impact = family["verdict_impact"]
            assert impact["published_value"] < impact["threshold"]
            assert impact["counterfactual_value"] < impact["threshold"]
        # H3 is the family closest to the boundary: its published p-value sits
        # 0.0036 below 0.05 and the counterfactual moves it further down.
        h3 = _family("H3")["verdict_impact"]
        assert h3["published_value"] == pytest.approx(0.0464, abs=PUBLISHED_ROUNDING_STEP)
        assert h3["counterfactual_value"] < h3["published_value"]

    def test_the_direction_aware_rule_fails_for_every_family(self):
        """H33/H34 disclosed that the published gate is direction-blind and
        that all three ``p`` PASS families have a *negative* alpha. The
        direction-aware rule the library applies now fails before and after
        the correction."""
        for family in COMMITTED["families"]:
            impact = family["verdict_impact"]
            assert impact["counterfactual_pass_direction_aware"] is False

    def test_the_detector_fires_when_a_gate_would_move(self):
        """Behavioural negative control: the impact detector is not vacuous."""
        published = {"gate_block_published": True, "value": 0.0464, "threshold": 0.05, "pass": True}
        assert h57.verdict_impact(published, 0.0261, -0.99)["gate_boolean_moves"] is False
        assert h57.verdict_impact(published, 0.0600, -0.99)["gate_boolean_moves"] is True

    def test_no_family_keeps_a_moved_verdict_quietly(self):
        """A family that published no gate block cannot hide a move: the
        counterfactual's own boolean is reported for every family."""
        for family in COMMITTED["families"]:
            impact = family["verdict_impact"]
            assert isinstance(impact["counterfactual_pass"], bool)
            assert impact["threshold"] == 0.05


# ---------------------------------------------------------------------------
# 7. The disclosure
# ---------------------------------------------------------------------------
class TestTheDisclosure:
    """What the audit measured, pinned."""

    def test_the_spy_gap_is_measured(self):
        """The record omits SPY's distributions: 1.81 %/yr over 2009-2026."""
        profile = COMMITTED["symbol_profiles"]["SPY"]
        assert profile["annualised_total_return_excess"] == pytest.approx(0.01806568828638544)
        assert profile["first"] == "2009-01-02"
        assert profile["last"] == "2026-10-07"

    def test_the_high_yield_bond_gap_is_measured(self):
        """HYG pays 5.40 %/yr, the largest gap in the H1-H3 universe."""
        profile = COMMITTED["symbol_profiles"]["HYG"]
        assert profile["annualised_total_return_excess"] == pytest.approx(0.053955077144621555)

    def test_the_three_pdbc_level_bars_are_measured(self):
        """The ex-dates the record books as losses, with the distributions
        they carry."""
        profile = COMMITTED["symbol_profiles"]["PDBC"]
        assert profile["n_level_bars"] == 3
        levels = [bar for bar in profile["corporate_action_bars"] if bar["level_bar"]]
        assert [bar["date"] for bar in levels] == ["2021-12-03", "2021-12-20", "2022-12-19"]
        assert [bar["price_return"] for bar in levels] == pytest.approx(
            [-0.2656481544499222, -0.12206265814684392, -0.11909149324899315]
        )
        assert [bar["implied_distribution_per_share"] for bar in levels] == pytest.approx(
            [5.389999914719134, 1.757001342467607, 1.9279997901536152]
        )

    def test_the_symbols_the_record_carries_no_adjustment_for_are_named(self):
        """Five of the twenty symbols of the H1-H3 universe carry an
        ``adj_close`` equal to their ``close``: the record holds no
        distribution for them at all, so the correction is a lower bound for
        that universe."""
        assert _family("H1")["symbols_without_adjustment"] == ["GLD", "USO", "GSG", "FXY"]
        assert _family("H3")["symbols_without_adjustment"] == ["GLD", "USO", "GSG", "FXY", "VXX"]
        assert _family("H17")["symbols_without_adjustment"] == ["SVXY"]

    def test_every_audited_symbol_carries_a_total_return_column(self):
        for hypothesis in FAMILY_BY_ID:
            assert _family(hypothesis)["symbols_without_total_return"] == []

    def test_the_counterfactual_p_values_are_pinned(self):
        expected = {
            "H1": 0.8802270541049035,
            "H3": 0.026128937180404453,
            "H16": 0.17264796358158924,
            "H17": 0.5338912916185102,
            "H19": 0.0018937816707710808,
            "H20": 0.0067395554253963635,
        }
        for hypothesis, value in expected.items():
            assert _family(hypothesis)["counterfactual_total_return"][
                "alpha_p_value"
            ] == pytest.approx(value, rel=1e-12)

    def test_the_audit_wrote_nothing_but_its_own_summary(self):
        """The audit's artifact directory holds exactly one file."""
        assert sorted(child.name for child in H57_DIR.iterdir()) == ["summary.json"]
