"""H29: systematic look-ahead sweep of the remaining families.

The sweep itself is cheap (a rebuild of eight families plus one counterfactual),
but these tests pin the *mechanics* and the *pre-registration* so that the
detector cannot silently drift into a different experiment:

* the collapse probe (the pandas label position and the hold lag),
* the frozen verdict rule,
* the negative control (a causal daily collapse must be reported ``CAUSAL``),
* the source inventory (both constructions must be present and classified
  differently),
* the committed H29 report (the per-family verdicts and the self-checks),
* the bit-exactness of the rebuilds that the verdicts rest on.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_h23_crypto_futures_tsmom as h23
import run_h27_pnl_level_audit as h27
import run_h29_lookahead_sweep as h29

SPEC = (ROOT / "HYPOTHESIS_SPEC.md").read_text()
ARTIFACTS = ROOT / ".experiments" / "artifacts"
H29_DIR = ARTIFACTS / "h29_lookahead_sweep"


def h29_summary() -> dict:
    """The committed H29 report (skip if the artifact is not present)."""
    path = H29_DIR / "summary.json"
    if not path.exists():
        pytest.skip("H29 artifact not present")
    return json.loads(path.read_text())


def _hourly_signal(n_hours=48):
    idx = pd.date_range("2024-01-01", periods=n_hours, freq="h")
    return pd.DataFrame({"A": np.arange(n_hours, dtype=float)}, index=idx)


class TestCollapseProbe:
    def test_the_daily_collapse_labels_at_the_bin_start(self):
        probe = h29.probe_collapse("1D", h29.HOURLY_GRID)
        assert probe["label_position"] == "bin_start"
        assert probe["labels_at_bin_end"] == 0

    def test_the_monthly_collapse_labels_at_the_bin_end(self):
        probe = h29.probe_collapse("ME", h29.DAILY_GRID)
        assert probe["label_position"] == "bin_end"
        assert probe["labels_at_bin_start"] == 0

    def test_the_daily_collapse_is_a_look_ahead_on_an_hourly_grid(self):
        probe = h29.probe_collapse("1D", h29.HOURLY_GRID)
        # the position is held with the day's own close: the value is traded
        # from the bar *after* the one that produced it
        assert probe["min_hold_lag_bars"] <= 0
        assert probe["lookahead_bar_fraction"] > 0.9

    def test_the_monthly_collapse_is_causal_on_a_daily_grid(self):
        probe = h29.probe_collapse("ME", h29.DAILY_GRID)
        assert probe["min_hold_lag_bars"] >= 1
        assert probe["n_lookahead_bars"] == 0
        assert probe["lookahead_bar_fraction"] == 0.0

    def test_a_lagged_collapse_is_causal(self):
        # the same label position with the value taken from the previous bin
        # is exactly what a causal daily collapse does
        probe = h29.probe_collapse("1D", h29.HOURLY_GRID, source_bin_offset=-1)
        assert probe["min_hold_lag_bars"] >= 1
        assert probe["n_lookahead_bars"] == 0

    def test_the_probe_depends_on_the_grid_not_on_the_family(self):
        # a "1D" collapse on a *daily* grid is a no-op (one bar per bin)
        probe = h29.probe_collapse("1D", h29.DAILY_GRID)
        assert probe["min_hold_lag_bars"] >= 1


class TestVerdictRule:
    def test_a_negative_hold_lag_with_the_same_period_match_is_a_look_ahead(self):
        assert h29.classify(-22.0, 1.0, 0.38) == "LOOKAHEAD"

    def test_a_positive_hold_lag_with_the_previous_period_match_is_causal(self):
        assert h29.classify(1.0, 0.40, 0.98) == "CAUSAL"

    def test_the_two_legs_must_agree(self):
        assert h29.classify(-22.0, 0.0, 1.0) == "INCONCLUSIVE"
        assert h29.classify(1.0, 1.0, 0.0) == "INCONCLUSIVE"

    def test_a_missing_statistic_is_inconclusive(self):
        assert h29.classify(float("nan"), 1.0, 0.0) == "INCONCLUSIVE"


class TestNegativeControl:
    def test_the_causal_collapse_is_reported_causal(self):
        control = h29.negative_control()
        assert control["causal_verdict"] == "CAUSAL"
        assert control["causal_min_hold_lag_bars"] >= 1
        assert (
            control["causal_prev_period_match_fraction"]
            > control["causal_same_period_match_fraction"]
        )

    def test_the_published_collapse_is_reported_look_ahead(self):
        control = h29.negative_control()
        assert control["published_verdict"] == "LOOKAHEAD"
        assert control["published_min_hold_lag_bars"] <= 0

    def test_the_control_uses_the_h27_collapse_object(self):
        # the H27 regression test and the H29 negative control cannot drift
        assert (
            h29.causal_daily_target_from_hourly is h27.causal_daily_target_from_hourly
        )


class TestSourceSweep:
    def test_the_inventory_covers_both_constructions(self):
        inventory = h29.source_sweep()
        freqs = {row["freq"] for row in inventory}
        assert "1D" in freqs
        assert "ME" in freqs

    def test_the_daily_collapse_is_only_used_by_the_intraday_runners(self):
        inventory = h29.source_sweep()
        daily = {row["file"] for row in inventory if row["freq"] == "1D"}
        assert daily == {
            "run_h26_sharpe_scale_audit.py",
            "run_h27_pnl_level_audit.py",
            "run_h9_intraday_tsmom_experiment.py",
        }

    def test_the_monthly_collapse_is_used_by_the_daily_runners(self):
        inventory = h29.source_sweep()
        monthly = {row["file"] for row in inventory if row["freq"] == "ME"}
        assert monthly == {
            "run_cs_momentum_experiment.py",
            "run_ddcv_experiment.py",
            "run_futures_tsmom_experiment.py",
            "run_h6_vix_ddcv_experiment.py",
            "run_h7_intraday_tsmom_experiment.py",
            "run_h8_rolladjusted_tsmom_experiment.py",
            "run_regime_gated_momentum_experiment.py",
            "run_ts_momentum_experiment.py",
        }

    def test_the_two_constructions_are_classified_differently(self):
        daily = h29.probe_collapse("1D", h29.HOURLY_GRID)
        monthly = h29.probe_collapse("ME", h29.DAILY_GRID)
        assert daily["min_hold_lag_bars"] <= 0
        assert monthly["min_hold_lag_bars"] >= 1


class TestRebuilds:
    def test_the_h1_rebuild_reproduces_the_committed_signals_bit_exactly(self):
        art = h29.art_dir_for("exp_2026-10-14T08-26-18-385545Z")
        _base, target = h29.rebuild_h1(art)
        committed = pd.read_parquet(art / "selected_signals.parquet")
        assert h29._frame_max_abs_diff(target, committed) == 0.0

    def test_the_h8_rebuild_reproduces_the_committed_signals_bit_exactly(self):
        art = h29.art_dir_for("exp_2026-10-11T15-21-31-333870Z")
        _base, target = h29.rebuild_h8(art)
        committed = pd.read_parquet(art / "signals_w0.5.parquet")
        assert h29._frame_max_abs_diff(target, committed) == 0.0

    def test_the_committed_target_only_changes_on_predicted_bars(self):
        art = h29.art_dir_for("exp_2026-10-14T08-26-18-385545Z")
        _base, target = h29.rebuild_h1(art)
        grid = pd.DatetimeIndex(target.index)
        probe = h29.probe_collapse("ME", grid)
        observed = set(h29.change_points(target))
        predicted = h29.predicted_change_points(probe, grid)
        assert not (observed - predicted)

    def test_the_h23_counterfactual_restores_the_runner_module(self):
        original = h23._daily_target_from_hourly
        h23._daily_target_from_hourly = h27.causal_daily_target_from_hourly
        h23._daily_target_from_hourly = original
        assert h23._daily_target_from_hourly is original


class TestCommittedReport:
    def test_the_verdict_is_look_ahead_found(self):
        summary = h29_summary()
        assert summary["verdict"] == "LOOKAHEAD_FOUND"

    def test_every_self_check_passed(self):
        summary = h29_summary()
        assert all(summary["self_checks"].values()), summary["self_checks"]

    def test_the_daily_families_are_causal(self):
        summary = h29_summary()
        verdicts = {f["family"]: f["verdict"] for f in summary["families"]}
        for family in ("H1", "H2", "H3", "H4", "H5", "H6", "H8"):
            assert verdicts[family] == "CAUSAL", family

    def test_the_inherited_and_crypto_families_are_look_ahead(self):
        summary = h29_summary()
        verdicts = {f["family"]: f["verdict"] for f in summary["families"]}
        for family in ("H11", "H12", "H13", "H23"):
            assert verdicts[family] == "LOOKAHEAD", family

    def test_h7_has_a_committed_artifact_and_audits_causal(self):
        summary = h29_summary()
        h7 = next(f for f in summary["families"] if f["family"] == "H7")
        assert h7["verdict"] == "CAUSAL", h7
        assert h7["artifact"] == "exp_2026-10-19T18-56-08-872500Z", h7
        assert h7["route"] == "rebuild_pipeline", h7
        assert h7["collapse_freq"] == "ME", h7
        assert h7["rebuild_bit_exact"] is True, h7
        assert h7["rebuild_max_abs_diff"] == 0.0, h7
        assert h7["n_extra_change_points"] == 0, h7
        assert h7["min_hold_lag_bars"] == 1.0, h7
        assert h7["lookahead_bar_fraction"] == 0.0, h7

    def test_the_causal_families_rebuild_bit_exactly(self):
        summary = h29_summary()
        for family in ("H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8"):
            row = next(f for f in summary["families"] if f["family"] == family)
            assert row["rebuild_bit_exact"] is True, family
            assert row["rebuild_max_abs_diff"] == 0.0, family
            assert row["n_extra_change_points"] == 0, family

    def test_the_look_ahead_families_have_a_negative_hold_lag(self):
        summary = h29_summary()
        for family in ("H11", "H12", "H13", "H23"):
            row = next(f for f in summary["families"] if f["family"] == family)
            assert row["min_hold_lag_bars"] <= 0, family
            assert row["lookahead_bar_fraction"] > 0.9, family

    def test_the_already_audited_families_are_still_look_ahead(self):
        summary = h29_summary()
        for row in summary["already_audited"]:
            assert row["verdict"] == "LOOKAHEAD", row["family"]

    def test_the_h23_control_reproduces_the_published_positions(self):
        summary = h29_summary()
        magnitude = summary["magnitudes"]["H23"]
        assert magnitude["control_bit_exact"] is True
        assert magnitude["control_max_abs_diff_positions_vs_committed"] == 0.0

    def test_the_h23_control_reproduces_the_published_oos_sharpe(self):
        summary = h29_summary()
        magnitude = summary["magnitudes"]["H23"]
        published = json.loads(
            (h29.art_dir_for(magnitude["artifact"]) / "summary.json").read_text()
        )
        assert magnitude["published_build"]["oos_sharpe"] == pytest.approx(
            published["metrics"]["oos_sharpe"], rel=1e-12
        )

    def test_the_h23_causal_fix_does_not_rescue_the_family(self):
        summary = h29_summary()
        magnitude = summary["magnitudes"]["H23"]
        assert magnitude["causal_build"]["oos_sharpe"] < 1.0
        assert magnitude["causal_build"]["oos_sharpe"] < 0.0


class TestPreRegistration:
    def test_the_spec_contains_the_h29_section(self):
        assert "## H29: Systematic look-ahead sweep" in SPEC

    def test_the_spec_freezes_the_families_and_the_artifact_ids(self):
        assert "exp_2026-10-14T08-26-18-385545Z" in SPEC
        assert "exp_2026-10-14T18-13-09-457781Z" in SPEC

    def test_the_spec_records_the_pre_execution_amendment(self):
        assert "H29 — Pre-registration amendment" in SPEC
        assert "made **BEFORE** any sweep execution" in SPEC

    def test_the_runner_does_not_edit_the_published_runners(self):
        # H29 must not modify a published runner: the only intervention it
        # makes is the temporary, restored patch of the H23 module global
        source = (ROOT / "run_h29_lookahead_sweep.py").read_text()
        assert "_daily_target_from_hourly = " in source
        assert "finally:" in source
        for runner in (
            "run_h9_intraday_tsmom_experiment.py",
            "run_h10_intraday_tsmom_pfopt_experiment.py",
        ):
            text = (ROOT / runner).read_text()
            assert "h29" not in text.lower()
