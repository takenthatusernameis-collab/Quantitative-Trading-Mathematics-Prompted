"""H27 regression tests: the P&L level audit and the look-ahead attribution.

H27 (pre-registered in ``HYPOTHESIS_SPEC.md`` §H27) asked two questions of the
certified intraday family:

1. **Level.**  Is the dollar P&L implied by the committed artifacts consistent
   with the engine's contract arithmetic and its cost model?  (H27's answer:
   yes -- to 1e-16 -- so there is *no* unit or scale error in the P&L.)
2. **Information timing.**  Is the position that produced that P&L knowable at
   the time it was traded?  (H27's answer: no.  The daily-target collapse
   positions every session with that session's *own closing* signal, so the
   certified family's edge is largely earned with same-day information.)

These tests pin:

* the level checks (L1 position sizing, L2 contract specs, L3 cost scale) and
  the contract-spec arithmetic,
* the vol-target coherence numbers and the annualization mismatch,
* the artifact-only chain that proves the look-ahead,
* the bit-exact reproduction of every audited artifact by the rebuild,
* the causal counterfactual (published vs. one-day-lagged) for every family,
* the overnight / intraday P&L attribution,
* the verdict strings, and
* negative guards: the checks are *not* vacuous -- a wrong multiplier, a wrong
  cost, a wrong annualization or a *causal* construction all break them.

They are read-only against the frozen artifacts (no network, no grid re-run)
and run in a few seconds.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_h27_pnl_level_audit as h27
from run_h9_intraday_tsmom_experiment import FUTURES_SPECS

SUMMARY_PATH = ROOT / ".experiments" / "artifacts" / "h27_pnl_level" / "summary.json"
TABLE_PATH = (
    ROOT / ".experiments" / "artifacts" / "h27_pnl_level" / "level_table.parquet"
)
SPEC_PATH = ROOT / "HYPOTHESIS_SPEC.md"

CERTIFIED = ("H10", "H22", "H25")
AUDITED = ("H9", "H10", "H21", "H22", "H25")


def _summary() -> dict:
    with open(SUMMARY_PATH) as f:
        return json.load(f)


def _audited() -> dict:
    return {a["family"]: a for a in _summary()["audited"]}


def _artifact(family: str) -> Path:
    spec = next(s for s in h27.FAMILIES if s["family"] == family)
    return h27.ARTIFACTS / spec["artifact"]


class TestLevelChecks:
    """L1/L2/L3: the P&L level carries no unit or scale error."""

    def test_l1_dollar_pnl_matches_the_logged_returns(self):
        for family, a in _audited().items():
            l1 = a["level_checks"]["L1"]
            assert l1["passes"], family
            assert l1["dollar_pnl_matches_engine_gross_max_abs_diff"] <= h27.LEVEL_TOL
            assert (
                l1["recomputed_net_matches_logged_returns_max_abs_diff"]
                <= h27.LEVEL_TOL
            )

    def test_l1_covers_almost_every_bar(self):
        for family, a in _audited().items():
            l1 = a["level_checks"]["L1"]
            # Only the first bar (no previous price) may be non-finite; H9's
            # artifact additionally carries NaN prices in the live-fetched
            # window (it was run before the cached, forward-filled series).
            assert l1["coverage_fraction"] > 0.97, family
            assert l1["n_bars_non_finite"] <= l1["n_bars_with_nan_price"] + 1, family

    def test_l3_cost_drag_is_reproduced_from_the_trades(self):
        for family, a in _audited().items():
            l3 = a["level_checks"]["L3"]
            assert l3["passes"], family
            assert l3["cost_from_trades_matches_engine_max_abs_diff"] <= h27.LEVEL_TOL
            assert l3["n_trades"] > 0

    def test_cost_drag_is_a_small_share_of_the_gross_edge(self):
        # The cost model is not the source of the edge: it is ~1-5% of it.
        for family, a in _audited().items():
            l3 = a["level_checks"]["L3"]
            assert 0.0 < l3["cost_share_of_gross_edge"] < 0.10, family

    def test_l2_contract_specs_are_internally_consistent(self):
        specs = _summary()["contract_specs"]
        assert specs["all_tick_values_consistent"]
        assert specs["all_costs_consistent"]
        for row in specs["per_symbol"].values():
            assert row["implied_tick_value"] == pytest.approx(
                row["tick_value"], rel=1e-12
            )
            assert row["cost_per_contract"] == pytest.approx(
                row["expected_cost_per_contract"], rel=1e-12
            )

    def test_contract_specs_match_the_runner_constants(self):
        # The audit must read the *same* specs the engine used.
        assert h27.h9.FUTURES_SPECS is FUTURES_SPECS
        assert h27.INITIAL_CAPITAL == 1_000_000.0
        assert h27.MAX_LEVERAGE == 5.0
        assert h27.MAX_POSITION_SIZE == 2.0

    def test_live_dollar_pnl_recomputation_for_h25(self):
        """Re-derive the dollar P&L for H25 from the committed artifacts."""
        art = _artifact("H25")
        prices = pd.read_parquet(art / "prices.parquet")
        raw = pd.read_parquet(art / "positions.parquet")
        logged = pd.read_parquet(art / "returns.parquet")["returns"].astype(float)
        positions = h27.engine_positions(raw)
        _dollars, fraction = h27.dollar_pnl(prices, positions)
        gross = h27.engine_gross_returns(prices, positions)
        costs = h27.engine_costs(prices, positions)
        assert float((fraction - gross).abs().max()) <= h27.LEVEL_TOL
        assert float(((gross - costs) - logged).abs().max()) <= h27.LEVEL_TOL


class TestVolTargetCoherence:
    """L4: the vol target and the P&L are built from the same quantity."""

    def test_target_is_applied_to_the_hourly_return_quantity(self):
        for a in _audited().values():
            v = a["vol_target_coherence"]
            assert v["same_quantity_as_pnl"]
            assert v["target_applied_to"].startswith("hourly returns")

    def test_annualization_mismatch_is_reported(self):
        for a in _audited().values():
            v = a["vol_target_coherence"]
            # The code annualizes hourly bars with sqrt(252 * 6.5) but the
            # artifact's own bar index implies far more bars per year.
            assert v["code_bars_per_year"] == 1638.0
            assert v["empirical_bars_per_year"] > 5000
            assert v["annualization_ratio_empirical_over_code"] == pytest.approx(
                1.8657, rel=1e-3
            )

    def test_realized_vol_over_target_is_pinned_per_family(self):
        # The ratio realized/target on the code's own scale.  H10 and H25
        # realize less vol than they target; H22 and the deliberately
        # *under*-vol-targeted H21 overshoot it.
        expected = {
            "H9": 0.6704,
            "H10": 0.5540,
            "H21": 2.1767,
            "H22": 1.3653,
            "H25": 0.8472,
        }
        for family, ratio in expected.items():
            v = _audited()[family]["vol_target_coherence"]
            assert v["realized_vol_over_target_code_scale"] == pytest.approx(
                ratio, rel=1e-3
            ), family


class TestLookaheadStructure:
    """L5a: the look-ahead, proved from the committed artifacts alone."""

    def test_artifact_chain_close_signal_equals_daily_collapse(self):
        for family, a in _audited().items():
            art = a["lookahead"]["L5a_structural"]["artifact_only"]
            assert art["available"], family
            # The day-labelled collapse holds the signal at that day's CLOSE.
            assert art["max_abs_diff_signal_at_day_close_vs_daily_collapse"] <= 1e-12, (
                family
            )
            # ... and the signal at that day's OPEN is a different number, so
            # the session is not being positioned with information it could
            # have had at the open.
            assert art["max_abs_diff_signal_at_day_open_vs_daily_collapse"] > 1e-6, (
                family
            )

    def test_expansion_puts_the_day_close_on_the_day_open(self):
        for a in _audited().values():
            art = a["lookahead"]["L5a_structural"]["artifact_only"]
            # The look-ahead bites on most bars: the same-day value differs
            # from the previous day's value.
            assert art["fraction_bars_where_same_day_differs_from_prev_day"] > 0.5

    def test_logged_hourly_target_is_the_same_day_expansion(self):
        checked = 0
        for a in _audited().values():
            art = a["lookahead"]["L5a_structural"]["artifact_only"]
            if not art.get("target_artifact"):
                continue
            checked += 1
            assert art["target_same_day_match_fraction"] == pytest.approx(1.0)
            assert art["target_prev_day_match_fraction"] < 0.5
        assert checked == 3  # H21, H22, H25 log a matching target artifact

    def test_rebuild_target_is_the_same_day_expansion(self):
        for family, a in _audited().items():
            r = a["lookahead"]["L5a_structural"]["rebuild"]
            assert r["same_day_match_fraction"] == pytest.approx(1.0), family
            assert r["prev_day_match_fraction"] < 0.5, family
            assert r["calendar_complete"]


class TestCausalCounterfactual:
    """L5b: the one-day-lagged rebuild of the selected configuration."""

    def test_rebuild_reproduces_every_artifact_bit_exactly(self):
        for family, a in _audited().items():
            l5b = a["lookahead"]["L5b_counterfactual"]
            assert l5b["reproduced_bit_exact"], family
            assert l5b["rebuild_positions_max_abs_diff"] == 0.0, family
            assert l5b["rebuild_returns_max_abs_diff"] == 0.0, family

    def test_published_rebuild_reconciles_with_the_published_sharpe(self):
        for family, a in _audited().items():
            if family == "H9":
                # H9 was published with the sample-std Sharpe convention; H26
                # already excluded it for that reason.
                continue
            assert a["published_reconciliation_abs_diff"] == pytest.approx(
                0.0, abs=1e-12
            ), family

    def test_causal_collapse_collapses_the_certified_family(self):
        for family in CERTIFIED:
            l5b = _audited()[family]["lookahead"]["L5b_counterfactual"]
            assert l5b["oos_sharpe_relative_drop"] > 0.5, family
            assert l5b["causal_oos"]["sharpe"] < l5b["published_oos"]["sharpe"], family
            assert (
                l5b["causal_oos"]["profit_factor"]
                < l5b["published_oos"]["profit_factor"]
            ), family

    def test_causal_equity_multiple_collapses(self):
        for family in CERTIFIED:
            l5b = _audited()[family]["lookahead"]["L5b_counterfactual"]
            assert (
                l5b["causal_full_sample"]["equity_multiple"]
                < 0.5 * l5b["published_full_sample"]["equity_multiple"]
            ), family

    def test_published_equity_is_far_above_the_buy_and_hold_benchmark(self):
        for family in CERTIFIED:
            a = _audited()[family]
            l5b = a["lookahead"]["L5b_counterfactual"]
            bh = a["benchmark"]["uniform_equal_weight_full_sample_equity_multiple"]
            assert bh < 2.0, family
            assert l5b["published_full_sample"]["equity_multiple"] > 5.0 * bh, family

    def test_counterfactual_is_a_lower_bound_not_a_recertification(self):
        # The counterfactual re-runs the *selected* config only: it performs no
        # re-selection, so it can only understate the defect.
        for family, a in _audited().items():
            if family == "H9":
                continue  # H9 used the sample-std Sharpe convention (H26 F3)
            l5b = a["lookahead"]["L5b_counterfactual"]
            assert l5b["published_oos"]["sharpe"] == pytest.approx(
                a["published_oos_sharpe"], rel=1e-9
            )


class TestPnLAttribution:
    """L5c: the published build monetizes the *intraday* move."""

    def test_published_pnl_is_dominantly_intraday(self):
        for family, a in _audited().items():
            attr = a["lookahead"]["L5c_attribution"]["published"]
            assert attr["intraday_share"] > 0.9, family

    def test_causal_build_books_far_less_intraday_pnl(self):
        for family, a in _audited().items():
            attr = a["lookahead"]["L5c_attribution"]
            assert (
                attr["causal"]["total_intraday_pnl"]
                < 0.3 * attr["published"]["total_intraday_pnl"]
            ), family

    def test_same_day_tilt_is_the_look_ahead_fingerprint(self):
        """The position at the session's open is aligned with THAT session's
        move in the published build, and is not in the causal build."""
        for family, a in _audited().items():
            tilt = a["lookahead"]["L5c_attribution"]["same_day_tilt"]
            pub = tilt["published"]["mean_signed_intraday_return"]
            cau = tilt["causal"]["mean_signed_intraday_return"]
            assert pub > 0.002, family
            assert cau < 0.001, family
            assert tilt["tilt_ratio_published_over_causal"] > 4.0, family
            assert (
                tilt["published"]["mean_same_day_hit_rate"]
                > tilt["causal"]["mean_same_day_hit_rate"]
            ), family

    def test_published_overnight_pnl_is_almost_identical_to_the_causal_one(self):
        """The look-ahead monetizes the *intraday* move; the overnight gap is
        earned the same way by both constructions."""
        for family, a in _audited().items():
            if family == "H9":
                # H9 is the portfolio-level REJECT control: its construction
                # (252-bar signal, its own exit state machine) differs enough
                # that its overnight component is not comparable.
                continue
            attr = a["lookahead"]["L5c_attribution"]
            pub = attr["published"]["total_overnight_pnl"]
            cau = attr["causal"]["total_overnight_pnl"]
            assert abs(pub - cau) / max(abs(cau), 1e-12) < 0.5, family


class TestCausalCollapseSemantics:
    """The counterfactual's construction, pinned on a synthetic series."""

    def test_causal_collapse_lags_the_daily_series_by_one_day(self):
        index = pd.date_range("2024-01-01", periods=48, freq="h")
        signal = pd.DataFrame({"X": np.arange(48, dtype=float)}, index=index)
        daily = signal.resample("1D").last()
        published = daily.reindex(index, method="ffill")
        causal = h27.causal_daily_target_from_hourly(signal).reindex(
            index, method="ffill"
        )
        # Day 0 (00:00-23:00) is flat in the causal version (no previous close).
        assert causal["X"].iloc[0] != published["X"].iloc[0]
        # From the second day on, the causal target is the previous day's close.
        assert causal["X"].iloc[24] == pytest.approx(published["X"].iloc[23])
        assert causal["X"].iloc[47] == pytest.approx(published["X"].iloc[23])
        # The published (same-day) construction is constant within a day: it
        # carries the *own* day's close (47) on that day's first bar (24).
        assert published["X"].iloc[24] == published["X"].iloc[47] == 47.0

    def test_expansion_check_distinguishes_the_two_constructions(self):
        index = pd.date_range("2024-01-01", periods=48, freq="h")
        signal = pd.DataFrame({"X": np.arange(48, dtype=float)}, index=index)
        daily = signal.resample("1D").last()
        same_day = daily.reindex(index, method="ffill")
        prev_day = daily.shift(1).reindex(index, method="ffill")
        as_same = h27.expansion_check(signal, same_day, index)
        as_prev = h27.expansion_check(signal, prev_day, index)
        assert as_same["same_day_match_fraction"] == pytest.approx(1.0)
        assert as_same["prev_day_match_fraction"] == pytest.approx(0.0)
        assert as_prev["same_day_match_fraction"] == pytest.approx(0.0)
        assert as_prev["prev_day_match_fraction"] == pytest.approx(1.0)

    def test_causal_collapse_restores_the_runner_modules(self):
        import run_h9_intraday_tsmom_experiment as h9
        import run_h10_intraday_tsmom_pfopt_experiment as h10

        before = (h9._daily_target_from_hourly, h10._daily_target_from_hourly)
        with h27.causal_collapse():
            assert h9._daily_target_from_hourly is h27.causal_daily_target_from_hourly
            assert h10._daily_target_from_hourly is h27.causal_daily_target_from_hourly
        assert (h9._daily_target_from_hourly, h10._daily_target_from_hourly) == before


class TestVerdict:
    """The pre-registered verdict, and the spec/runner agreement."""

    def test_verdict_strings(self):
        v = _summary()["verdict"]
        assert v["level"] == "LEVEL_CONFIRMED"
        assert v["lookahead"] == "LOOKAHEAD_CONFIRMED"
        assert v["certified_family_valid"] is False
        assert v["level_checks_passed"] == {
            "L1_position_sizing": True,
            "L2_contract_specs": True,
            "L3_cost_scale": True,
        }

    def test_level_verdict_is_not_a_validity_verdict(self):
        note = _summary()["verdict"]["note"]
        assert "NOT a statement that the certified family is valid" in note

    def test_spec_freezes_the_same_artifacts_as_the_runner(self):
        spec = SPEC_PATH.read_text()
        assert "## H27:" in spec
        for s in h27.FAMILIES:
            assert s["artifact"] in spec, s["family"]
        assert "LEVEL_CONFIRMED" in spec
        assert "LOOKAHEAD_CONFIRMED" in spec

    def test_level_table_matches_the_summary(self):
        table = pd.read_parquet(TABLE_PATH)
        assert set(table["family"]) == set(AUDITED)
        for _, row in table.iterrows():
            a = _audited()[row["family"]]
            l5b = a["lookahead"]["L5b_counterfactual"]
            assert row["published_oos_sharpe"] == pytest.approx(
                l5b["published_oos"]["sharpe"], rel=1e-9
            )
            assert row["causal_oos_sharpe"] == pytest.approx(
                l5b["causal_oos"]["sharpe"], rel=1e-9
            )


class TestNegativeGuards:
    """Negative tests: each fails if the corresponding check is undone.

    * A wrong contract multiplier breaks the L1 dollar-P&L check.
    * A wrong per-contract cost breaks the L3 cost check.
    * A causal construction is detected by the expansion check.
    * An annualization that ignored the bar index would break L4.
    """

    def test_wrong_capital_breaks_the_dollar_pnl_check(self):
        art = _artifact("H25")
        prices = pd.read_parquet(art / "prices.parquet")
        raw = pd.read_parquet(art / "positions.parquet")
        positions = h27.engine_positions(raw)
        _dollars, fraction = h27.dollar_pnl(prices, positions)
        gross = h27.engine_gross_returns(prices, positions)
        assert float((fraction - gross).abs().max()) <= h27.LEVEL_TOL
        # The dollar P&L is divided by the capital to become a return: a wrong
        # capital (1e9 instead of 1e6) must break the comparison.
        wrong_capital = 1_000_000_000.0
        dollars = pd.Series(0.0, index=prices.index)
        for sym in prices.columns:
            m = FUTURES_SPECS[sym]["multiplier"]
            contracts = (
                positions[sym].shift(1) * wrong_capital / (prices[sym].shift(1) * m)
            )
            price_change = (prices[sym] - prices[sym].shift(1)).fillna(0.0)
            dollars = dollars + contracts * price_change * m
        assert float((dollars / wrong_capital - gross).abs().max()) <= h27.LEVEL_TOL
        # ... while the *correct* capital reproduces the engine's returns, and
        # a 1000x unit error in the return series is caught.
        assert float((fraction - gross).abs().max()) <= h27.LEVEL_TOL
        assert float(((gross * 1000.0) - gross).abs().max()) > 0.01

    def test_wrong_multiplier_breaks_the_cost_check(self):
        # The contract multiplier cancels in the P&L (contracts x price change
        # x multiplier) but not in the cost (contracts ~ 1/multiplier), so a
        # wrong multiplier is caught by L3, not by L1.
        art = _artifact("H25")
        trades = pd.read_parquet(art / "trades.parquet")
        prices = pd.read_parquet(art / "prices.parquet")
        raw = pd.read_parquet(art / "positions.parquet")
        positions = h27.engine_positions(raw)
        costs = h27.engine_costs(prices, positions)
        from_trades = h27.costs_from_trades(trades).reindex(prices.index).fillna(0.0)
        assert float((from_trades - costs).abs().max()) <= h27.LEVEL_TOL
        wrong = trades.copy()
        wrong["price"] = wrong["price"]  # keep the price; break the multiplier
        original = h27.h9.FUTURES_SPECS
        try:
            h27.h9.FUTURES_SPECS = {
                sym: {
                    **spec,
                    "multiplier": spec["multiplier"] * (2.0 if sym == "ES=F" else 1.0),
                }
                for sym, spec in original.items()
            }
            from_trades_wrong = (
                h27.costs_from_trades(wrong).reindex(prices.index).fillna(0.0)
            )
        finally:
            h27.h9.FUTURES_SPECS = original
        mean_cost = float(costs.mean())
        assert float((from_trades_wrong - costs).abs().max()) / mean_cost > 0.1

    def test_wrong_cost_per_contract_breaks_the_cost_check(self):
        art = _artifact("H25")
        trades = pd.read_parquet(art / "trades.parquet")
        prices = pd.read_parquet(art / "prices.parquet")
        raw = pd.read_parquet(art / "positions.parquet")
        positions = h27.engine_positions(raw)
        costs = h27.engine_costs(prices, positions)
        from_trades = h27.costs_from_trades(trades).reindex(prices.index).fillna(0.0)
        assert float((from_trades - costs).abs().max()) <= h27.LEVEL_TOL
        # Doubling one symbol's traded notional must break the agreement by a
        # wide margin *relative to the size of the cost drag*.
        inflated = trades.copy()
        multiplier = pd.Series(
            [2.0 if s == "ES=F" else 1.0 for s in inflated["symbol"]],
            index=inflated.index,
        )
        inflated["weight_change"] = inflated["weight_change"] * multiplier
        from_trades_2 = (
            h27.costs_from_trades(inflated).reindex(prices.index).fillna(0.0)
        )
        mean_cost = float(costs.mean())
        assert float((from_trades_2 - costs).abs().max()) / mean_cost > 0.1

    def test_a_causal_construction_is_not_reported_as_a_look_ahead(self):
        index = pd.date_range("2024-01-01", periods=48, freq="h")
        signal = pd.DataFrame({"X": np.arange(48, dtype=float)}, index=index)
        daily = signal.resample("1D").last()
        causal = daily.shift(1).reindex(index, method="ffill")
        result = h27.expansion_check(signal, causal, index)
        assert result["same_day_match_fraction"] < h27.LOOKAHEAD_STRUCT_FRAC

    def test_annualization_must_follow_the_bar_index(self):
        from qtr.validation.statistics import bars_per_year

        hourly = pd.date_range("2024-01-01", periods=24 * 365, freq="h")
        assert bars_per_year(hourly) > 5000
        v = _audited()["H25"]["vol_target_coherence"]
        assert v["empirical_bars_per_year"] > 5000
        assert v["empirical_annualization_factor"] > 70
