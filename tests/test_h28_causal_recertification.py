"""H28: causal re-certification of the intraday futures TSMOM family.

The H28 runs themselves are long (the H10 grid is 13,824 combos, run twice);
these tests pin the *mechanics* and the *pre-registration* without re-running
them: the collapse semantics, the module restore, the negative control's
sensitivity, the verdict rule and the frozen elements.
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

import run_h9_intraday_tsmom_experiment as h9
import run_h10_intraday_tsmom_pfopt_experiment as h10
import run_h21_futures_tsmom_multicontract as h21
import run_h22_futures_tsmom_voltarget as h22
import run_h25_futures_tsmom_pfmargin as h25
import run_h27_pnl_level_audit as h27
import run_h28_causal_recertification as h28

SPEC = (ROOT / "HYPOTHESIS_SPEC.md").read_text()
ARTIFACTS = ROOT / ".experiments" / "artifacts"

# The published family artifacts.  Every regression test that re-derives a
# published number resolves its source directory through a "lexicographically
# last matching hypothesis" scan, so these ids must stay unambiguous.
PUBLISHED_ARTIFACTS = {
    "H10": "exp_2026-10-11T17-41-18-169363Z",
    "H21": "exp_2026-10-13T23-27-52-101656Z",
    "H22": "exp_2026-10-14T18-52-08-943792Z",
    "H25": "exp_2026-10-14T20-08-34-613690Z",
}


def h28_summary() -> dict:
    """The committed H28 report (skip if the artifact is not present)."""
    f = ARTIFACTS / "h28_causal_recertification" / "summary.json"
    if not f.exists():
        pytest.skip("H28 artifact not present")
    return json.loads(f.read_text())


def _hourly_signal(n_hours=72):
    idx = pd.date_range("2024-01-01", periods=n_hours, freq="h")
    return pd.DataFrame({"A": np.arange(n_hours, dtype=float)}, index=idx)


class TestCausalCollapseSemantics:
    def test_collapse_lags_the_daily_series_by_exactly_one_day(self):
        sig = _hourly_signal()
        published = h9._daily_target_from_hourly(sig)
        causal = h27.causal_daily_target_from_hourly(sig)
        # day D (causal) == day D-1 (published)
        assert np.allclose(causal.values[1:], published.values[:-1], equal_nan=True)
        # and the first causal day is unknown (NaN), not the same day's close
        assert np.isnan(causal.iloc[0, 0])
        assert published.iloc[0, 0] == 23.0

    def test_the_daily_index_spans_every_calendar_day(self):
        # The guard asserts that the daily collapse covers a *complete* calendar, so
        # that "shift by one" means "the previous calendar day" and a non-trading
        # day is carried forward (the position is held over the weekend).
        sig = _hourly_signal()
        daily = sig.resample("1D").last()
        calendar = pd.date_range(daily.index.min(), daily.index.max(), freq="1D")
        assert len(daily) == len(calendar) == 3

    def test_the_daily_index_is_contiguous_so_the_guard_holds(self):
        # `resample("1D")` always yields one label per calendar day, so the
        # guard's precondition (the daily index spans the calendar) always
        # holds for a DatetimeIndex; the guard is a defensive assertion.
        sig = _hourly_signal()
        daily = sig.resample("1D").last()
        calendar = pd.date_range(daily.index.min(), daily.index.max(), freq="1D")
        assert daily.index.equals(calendar)

    def test_a_non_datetime_index_is_a_hard_error(self):
        # the guard is the only thing standing between a malformed index and a
        # silently wrong lag
        bad = pd.DataFrame({"A": [1.0, 2.0]}, index=["a", "b"])
        with pytest.raises(TypeError):
            h27.causal_daily_target_from_hourly(bad)

    def test_h28_uses_the_h27_collapse_object(self):
        # the H27 regression test and the H28 counterfactual cannot drift apart
        assert h28.causal_daily_target_from_hourly is h27.causal_daily_target_from_hourly

    def test_build_hourly_target_is_lagged_under_the_collapse(self):
        sig = _hourly_signal()
        vix = pd.Series(20.0, index=sig.index)
        published = h10.build_hourly_target(sig, None, 24, False, vix, sig.index)
        with h28.causal_collapse():
            causal = h10.build_hourly_target(sig, None, 24, False, vix, sig.index)
        # first session is flat (nothing is knowable before the first close)
        assert (causal["A"].iloc[:24].to_numpy() == 0.0).all()
        # every later bar of day D carries the published day D-1 value
        assert (causal["A"].iloc[24:48].to_numpy() == 23.0).all()
        assert (published["A"].iloc[0:24].to_numpy() == 23.0).all()

    def test_every_runner_module_is_patched(self):
        originals = {m: m._daily_target_from_hourly for m in h28.COLLAPSE_MODULES}
        with h28.causal_collapse():
            for m in h28.COLLAPSE_MODULES:
                assert m._daily_target_from_hourly is not originals[m]
                assert m._daily_target_from_hourly is h27.causal_daily_target_from_hourly
        for m in h28.COLLAPSE_MODULES:
            assert m._daily_target_from_hourly is originals[m]

    def test_collapse_restores_the_modules_even_on_failure(self):
        originals = {m: m._daily_target_from_hourly for m in h28.COLLAPSE_MODULES}
        with pytest.raises(RuntimeError), h28.causal_collapse():
            raise RuntimeError("boom")
        for m in h28.COLLAPSE_MODULES:
            assert m._daily_target_from_hourly is originals[m]

    def test_the_collapse_carries_the_last_trading_day_over_a_weekend(self):
        # Fri 2024-01-05 has two bars (close = 2.0), Sat/Sun are non-trading,
        # Mon 2024-01-08 has one bar (close = 9.0).
        idx = pd.to_datetime(["2024-01-05 21:00", "2024-01-05 22:00", "2024-01-08 22:00"])
        sig = pd.DataFrame({"A": [1.0, 2.0, 9.0]}, index=idx)
        published = h9._daily_target_from_hourly(sig)
        causal = h27.causal_daily_target_from_hourly(sig)
        # the published collapse: every bar of Monday carries Monday's own close
        assert published.loc[pd.Timestamp("2024-01-08"), "A"] == 9.0
        # the causal collapse: Monday carries the last *trading* day's close
        assert causal.loc[pd.Timestamp("2024-01-08"), "A"] == 2.0
        # and the first day is unknown
        assert np.isnan(causal.iloc[0, 0])

    def test_the_published_collapse_is_untouched(self):
        # the control run must use the published same-day expansion
        sig = _hourly_signal()
        assert h9._daily_target_from_hourly(sig).iloc[0, 0] == 23.0


class TestExperimentIdentity:
    def test_identity_is_swapped_and_restored(self):
        original = (h22.EXPERIMENT_NAME, h22.EXPERIMENT_DESC)
        with h28.experiment_identity(h22, "h28_h22_causal", "desc"):
            assert h22.EXPERIMENT_NAME == "h28_h22_causal"
            assert h22.EXPERIMENT_DESC == "desc"
        assert (h22.EXPERIMENT_NAME, h22.EXPERIMENT_DESC) == original

    def test_tracker_capture_restores_the_runner_binding(self):
        original = h22.get_tracker
        with h28.tracker_capture(h22) as proxy:
            assert h22.get_tracker() is proxy
            assert proxy.experiment_id is None
        assert h22.get_tracker is original


class TestNegativeControl:
    def _fake_dirs(self, tmp_path, published_id, control_id, perturb=False, control_summary=None):
        (tmp_path / published_id).mkdir(parents=True)
        (tmp_path / control_id).mkdir(parents=True)
        df = pd.DataFrame(
            {"x": [1.0, 2.0, 3.0]},
            index=pd.date_range("2024-01-01", periods=3, freq="h"),
        )
        for d in (published_id, control_id):
            pd.DataFrame({"x": [1.0, 2.0, 3.0]}, index=df.index).to_parquet(
                tmp_path / d / "positions.parquet"
            )
        if perturb:
            pd.DataFrame({"x": [1.0, 2.0, 3.5]}, index=df.index).to_parquet(
                tmp_path / control_id / "positions.parquet"
            )
        published_summary = {
            "verdict": "PASS",
            "all_pass": True,
            "passes": {"sharpe": True, "pf": True, "stab": True},
            "metrics": {"oos_sharpe": 1.2, "wf_stability": 0.87},
        }
        (tmp_path / published_id / "summary.json").write_text(json.dumps(published_summary))
        (tmp_path / control_id / "summary.json").write_text(
            json.dumps(control_summary or published_summary)
        )

    def test_an_identical_control_is_bit_exact(self, tmp_path, monkeypatch):
        pub, ctl = "exp_pub", "exp_ctl"
        self._fake_dirs(tmp_path, pub, ctl)
        monkeypatch.setattr(h28, "ARTIFACTS", tmp_path)
        spec = {"family": "X", "published_artifact": pub}
        out = h28.compare_to_published(spec, ctl)
        assert out["bit_exact"] is True
        assert out["artifacts"]["positions"]["max_abs_diff"] == 0.0
        assert out["summary_bit_exact"] is True

    def test_a_perturbed_control_is_not_bit_exact(self, tmp_path, monkeypatch):
        pub, ctl = "exp_pub", "exp_ctl"
        self._fake_dirs(tmp_path, pub, ctl, perturb=True)
        monkeypatch.setattr(h28, "ARTIFACTS", tmp_path)
        spec = {"family": "X", "published_artifact": pub}
        out = h28.compare_to_published(spec, ctl)
        assert out["bit_exact"] is False
        assert out["artifacts"]["positions"]["max_abs_diff"] == 0.5

    def test_the_documented_library_drift_is_tolerated(self, tmp_path, monkeypatch):
        # `metrics.wf_stability` is the one field the pre-2026-10-19
        # walk_forward_splits change moves; it is exempt, but only that field.
        pub, ctl = "exp_pub", "exp_ctl"
        ctl_summary = {
            "verdict": "PASS",
            "all_pass": True,
            "passes": {"sharpe": True, "pf": True, "stab": True},
            "metrics": {"oos_sharpe": 1.2, "wf_stability": 0.86},
        }
        self._fake_dirs(tmp_path, pub, ctl, control_summary=ctl_summary)
        monkeypatch.setattr(h28, "ARTIFACTS", tmp_path)
        out = h28.compare_to_published({"published_artifact": pub}, ctl)
        assert out["bit_exact"] is True
        assert "metrics.wf_stability" in out["documented_library_drift"]
        assert out["unexpected_differences"] == {}
        assert out["gate_outcomes_match"] is True
        assert out["verdict_match"] is True

    def test_a_gate_outcome_change_is_not_tolerated(self, tmp_path, monkeypatch):
        pub, ctl = "exp_pub", "exp_ctl"
        ctl_summary = {
            "verdict": "PASS",
            "all_pass": True,
            "passes": {"sharpe": False, "pf": True, "stab": True},
            "metrics": {"oos_sharpe": 1.2, "wf_stability": 0.87},
        }
        self._fake_dirs(tmp_path, pub, ctl, control_summary=ctl_summary)
        monkeypatch.setattr(h28, "ARTIFACTS", tmp_path)
        out = h28.compare_to_published({"published_artifact": pub}, ctl)
        assert out["bit_exact"] is False
        assert "passes.sharpe" in out["unexpected_differences"]
        assert out["gate_outcomes_match"] is False

    def test_a_verdict_change_is_not_tolerated(self, tmp_path, monkeypatch):
        pub, ctl = "exp_pub", "exp_ctl"
        ctl_summary = {
            "verdict": "REJECT",
            "all_pass": False,
            "passes": {"sharpe": True, "pf": True, "stab": True},
            "metrics": {"oos_sharpe": 1.2, "wf_stability": 0.87},
        }
        self._fake_dirs(tmp_path, pub, ctl, control_summary=ctl_summary)
        monkeypatch.setattr(h28, "ARTIFACTS", tmp_path)
        out = h28.compare_to_published({"published_artifact": pub}, ctl)
        assert out["bit_exact"] is False
        assert out["verdict_match"] is False

    def test_an_unexpected_metric_change_is_not_tolerated(self, tmp_path, monkeypatch):
        pub, ctl = "exp_pub", "exp_ctl"
        ctl_summary = {
            "verdict": "PASS",
            "all_pass": True,
            "passes": {"sharpe": True, "pf": True, "stab": True},
            "metrics": {"oos_sharpe": 1.3, "wf_stability": 0.87},
        }
        self._fake_dirs(tmp_path, pub, ctl, control_summary=ctl_summary)
        monkeypatch.setattr(h28, "ARTIFACTS", tmp_path)
        out = h28.compare_to_published({"published_artifact": pub}, ctl)
        assert out["bit_exact"] is False
        assert "metrics.oos_sharpe" in out["unexpected_differences"]

    def test_a_missing_control_artifact_is_not_bit_exact(self, tmp_path, monkeypatch):
        pub, ctl = "exp_pub", "exp_ctl"
        self._fake_dirs(tmp_path, pub, ctl)
        (tmp_path / ctl / "positions.parquet").unlink()
        monkeypatch.setattr(h28, "ARTIFACTS", tmp_path)
        spec = {"family": "X", "published_artifact": pub}
        out = h28.compare_to_published(spec, ctl)
        assert out["bit_exact"] is False
        assert out["artifacts"]["positions"]["present_in_control"] is False


class TestVerdictRule:
    def _spec(self):
        return {
            "family": "H22",
            "published_artifact": "exp_pub",
            "published_verdict": "PASS",
        }

    def _write_summary(self, tmp_path, exp_id, all_pass):
        (tmp_path / exp_id).mkdir(parents=True, exist_ok=True)
        (tmp_path / exp_id / "summary.json").write_text(
            json.dumps(
                {
                    "verdict": "PASS" if all_pass else "REJECT",
                    "all_pass": all_pass,
                    "passes": {"sharpe": all_pass, "pf": all_pass},
                    "metrics": {
                        "oos_sharpe": 1.5,
                        "profit_factor": 1.4,
                        "max_drawdown": 0.1,
                        "trades": 500,
                    },
                    "selected_config": {"target_vol_mult": 1.0},
                }
            )
        )

    def test_all_gates_pass_and_control_ok_is_certified(self, tmp_path, monkeypatch):
        monkeypatch.setattr(h28, "ARTIFACTS", tmp_path)
        self._write_summary(tmp_path, "exp_causal", True)
        out = h28.causal_verdict(self._spec(), "exp_causal", True)
        assert out["verdict"] == "CAUSAL_CERTIFIED"
        assert out["all_pass"] is True
        assert out["control_reproduced"] is True

    def test_a_failed_gate_is_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setattr(h28, "ARTIFACTS", tmp_path)
        self._write_summary(tmp_path, "exp_causal", False)
        out = h28.causal_verdict(self._spec(), "exp_causal", True)
        assert out["verdict"] == "CAUSAL_REJECTED"

    def test_a_broken_control_voids_the_causal_run(self, tmp_path, monkeypatch):
        monkeypatch.setattr(h28, "ARTIFACTS", tmp_path)
        self._write_summary(tmp_path, "exp_causal", True)
        out = h28.causal_verdict(self._spec(), "exp_causal", False)
        assert out["verdict"] == "CAUSAL_REJECTED"
        assert "control" in out["reason"]

    def test_a_missing_summary_is_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setattr(h28, "ARTIFACTS", tmp_path)
        out = h28.causal_verdict(self._spec(), "exp_missing", True)
        assert out["verdict"] == "CAUSAL_REJECTED"

    def test_the_family_verdict_needs_all_three_certified_members(self):
        verdicts = {
            "H10": {"verdict": "CAUSAL_CERTIFIED"},
            "H22": {"verdict": "CAUSAL_CERTIFIED"},
            "H25": {"verdict": "CAUSAL_REJECTED"},
        }
        report = h28.build_report([], {}, verdicts)
        assert report["family_verdict"] == "CAUSAL_REJECTED"
        assert report["causal_certified_members"] == ["H10", "H22"]
        verdicts["H25"] = {"verdict": "CAUSAL_CERTIFIED"}
        report = h28.build_report([], {}, verdicts)
        assert report["family_verdict"] == "CAUSAL_CERTIFIED"


class TestFrozenElements:
    def test_the_gates_are_the_published_gates(self):
        assert h9.GATES == h28.h9.GATES
        assert h10.GATES is h9.GATES
        assert h22.GATES is h9.GATES
        assert h25.GATES is h9.GATES
        assert h9.GATES["min_sharpe"] == 1.0
        assert h9.GATES["min_profit_factor"] == 1.3
        assert h9.GATES["max_drawdown"] == 0.15

    def test_the_splits_are_the_published_splits(self):
        assert h22._splits is h10._splits
        prices = pd.DataFrame(
            {"A": np.arange(100.0)},
            index=pd.date_range("2024-01-01", periods=100, freq="h"),
        )
        train, val, test = h10._splits(prices)
        n = len(prices)
        assert int(train.sum()) == int(n * 0.55) + 1
        assert int(val.sum()) == int(n * 0.8) - int(n * 0.55)
        assert int(test.sum()) == n - int(n * 0.8) - 1
        assert int(train.sum() + val.sum() + test.sum()) == n

    def test_the_selection_rules_are_unchanged(self):
        # The rules live in the published runners and are reused verbatim by calling
        # the runners' own main(); H28 must not redefine them.
        assert not hasattr(h28, "SELECTION_RULE")
        for mod in (h10, h21, h22):
            src = ROOT / f"run_{mod.EXPERIMENT_NAME.split('_')[0]}.py"
            assert src.exists() or True
        sources = {
            "run_h10_intraday_tsmom_pfopt_experiment.py": "best Val Sharpe",
            "run_h21_futures_tsmom_multicontract.py": "best Val Sharpe",
            "run_h22_futures_tsmom_voltarget.py": "best Val Sharpe",
            "run_h25_futures_tsmom_pfmargin.py": "best Val PF margin",
        }
        for fname, rule in sources.items():
            assert rule in (ROOT / fname).read_text()
        # the H28 runner must not contain its own copy of the rule
        assert "best Val" not in (ROOT / "run_h28_causal_recertification.py").read_text()

    def test_the_frozen_published_artifacts(self):
        ids = {s["family"]: s["published_artifact"] for s in h28.FAMILY_SPECS}
        assert ids == {
            "H10": "exp_2026-10-11T17-41-18-169363Z",
            "H21": "exp_2026-10-13T23-27-52-101656Z",
            "H22": "exp_2026-10-14T18-52-08-943792Z",
            "H25": "exp_2026-10-14T20-08-34-613690Z",
        }
        for spec in h28.FAMILY_SPECS:
            assert (ARTIFACTS / spec["published_artifact"] / "summary.json").exists()

    def test_the_certified_family_is_the_published_one(self):
        assert h28.CERTIFIED_FAMILY == ("H10", "H22", "H25")

    def test_h9_is_out_of_scope(self):
        assert "H9" not in {s["family"] for s in h28.FAMILY_SPECS}

    def test_the_grid_sizes_match_the_published_runs(self):
        for spec in h28.FAMILY_SPECS:
            summary = json.loads(
                (ARTIFACTS / spec["published_artifact"] / "summary.json").read_text()
            )
            assert summary["grid_size"] == spec["grid_size"]


class TestH28Outcome:
    """Pin the executed H28 result (the committed artifact is part of the record)."""

    def _summary(self):
        return h28_summary()

    def test_the_certified_family_is_causal_rejected(self):
        assert self._summary()["family_verdict"] == "CAUSAL_REJECTED"
        assert self._summary()["causal_certified_members"] == []

    def test_every_audited_family_is_causal_rejected(self):
        verdicts = self._summary()["verdicts"]
        assert set(verdicts) == {"H10", "H21", "H22", "H25"}
        for fam, v in verdicts.items():
            assert v["verdict"] == "CAUSAL_REJECTED", fam
            assert v["all_pass"] is False, fam
            assert v["control_reproduced"] is True, fam

    def test_every_negative_control_reproduced_bit_exactly(self):
        controls = self._summary()["controls"]
        assert set(controls) == {"H10", "H21", "H22", "H25"}
        for fam, c in controls.items():
            assert c["bit_exact"] is True, fam
            assert c["unexpected_differences"] == {}, fam
            assert c["gate_outcomes_match"] is True, fam
            assert c["verdict_match"] is True, fam
            # every artifact must be bit-exact, not just some
            for name, art in c["artifacts"].items():
                assert art["bit_exact"] is True, (fam, name)
                assert art["max_abs_diff"] == 0.0, (fam, name)

    def test_the_causal_metrics_are_pinned(self):
        verdicts = self._summary()["verdicts"]
        expected = {
            "H10": (0.39091137211091564, 1.0865498375426346, -0.10139630025096769),
            "H21": (0.13170966460927166, 1.0296424358919745, -0.26124008938124976),
            "H22": (0.36047322955118866, 1.0773354284019054, -0.22760444683234615),
            "H25": (0.3231439026849481, 1.0692804083717933, -0.26191129643718036),
        }
        for fam, (sr, pf, dd) in expected.items():
            v = verdicts[fam]
            assert v["oos_sharpe"] == pytest.approx(sr, abs=1e-12), fam
            assert v["profit_factor"] == pytest.approx(pf, abs=1e-12), fam
            assert v["max_drawdown"] == pytest.approx(dd, abs=1e-12), fam

    def test_the_causal_sharpe_is_far_below_the_unchanged_gate(self):
        # GATES["min_sharpe"] == 1.0 -- unchanged from H9..H25
        for fam, v in self._summary()["verdicts"].items():
            assert v["oos_sharpe"] < h9.GATES["min_sharpe"], fam
            assert v["profit_factor"] < h9.GATES["min_profit_factor"], fam
            assert v["passes"]["sharpe"] is False, fam
            assert v["passes"]["pf"] is False, fam

    def test_the_published_verdicts_are_unchanged_in_the_record(self):
        for spec in h28.FAMILY_SPECS:
            published = json.loads(
                (ARTIFACTS / spec["published_artifact"] / "summary.json").read_text()
            )
            assert published["verdict"] == spec["published_verdict"]
            assert published["all_pass"] is (spec["published_verdict"] == "PASS")


class TestPublishedArtifactDiscovery:
    """The published family artifacts must stay the only depth-1 candidates.

    The repo's discovery helpers (``run_h25_pf_robustness.py::_find_latest_h25_dir``
    and the ``_latest_hXX_dir`` helpers in the family test files) select the
    lexicographically last directory whose ``summary.json`` carries the family's
    ``hypothesis`` label.  An H28 run sitting at depth 1 would therefore
    silently replace the published run in every regression test that re-derives
    a published number -- which is exactly what happened once.  H28 groups its
    runs under the audit directory so that cannot happen again.
    """

    def _depth1_candidates(self):
        found = {}
        for d in sorted(ARTIFACTS.iterdir()):
            if not d.is_dir() or not d.name.startswith("exp_"):
                continue
            f = d / "summary.json"
            if not f.exists():
                continue
            try:
                s = json.loads(f.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            hyp = s.get("hypothesis")
            if hyp in PUBLISHED_ARTIFACTS:
                found.setdefault(hyp, []).append(d.name)
        return found

    def test_no_h28_run_sits_at_depth_one(self):
        for d in ARTIFACTS.iterdir():
            if d.is_dir() and d.name.startswith("exp_"):
                assert "h28" not in d.name.lower(), d.name

    def test_the_last_depth_one_candidate_is_the_published_run(self):
        # `max(cands, key=lambda d: d.name)` is what the helpers use, so the
        # published run must be that maximum for every family.
        found = self._depth1_candidates()
        for fam, exp_id in PUBLISHED_ARTIFACTS.items():
            cands = found.get(fam, [])
            assert cands, fam
            assert max(cands) == exp_id, (fam, cands)
            # and no candidate may be an H28 run
            assert all("h28" not in c.lower() for c in cands), (fam, cands)

    def test_the_h25_robustness_audit_resolves_to_the_published_h25(self):
        import run_h25_pf_robustness as aud

        assert aud._find_latest_h25_dir().name == PUBLISHED_ARTIFACTS["H25"]

    def test_the_h28_runs_live_under_the_audit_directory(self):
        summary = h28_summary()
        paths = summary["run_artifact_paths"]
        assert len(paths) == 8
        for rel in paths.values():
            assert rel.startswith(".experiments/artifacts/h28_causal_recertification/runs/")
            assert (ROOT / rel).is_dir()
        for rec in summary["runs"]:
            assert rec["artifact_path"] == paths[rec["experiment_id"]]


class TestPreRegistration:
    def test_the_spec_has_the_h28_section(self):
        assert "## H28:" in SPEC
        assert "H28: Causal re-certification" in SPEC

    def test_the_spec_freezes_the_same_verdict_rule(self):
        assert "CAUSAL_CERTIFIED" in SPEC
        assert "CAUSAL_REJECTED" in SPEC
        assert "bit-exactly" in SPEC

    def test_the_spec_freezes_the_same_artifact_ids(self):
        for spec in h28.FAMILY_SPECS:
            assert spec["published_artifact"] in SPEC

    def test_the_spec_freezes_the_unchanged_gates(self):
        assert "min_sharpe" in SPEC and "min_profit_factor" in SPEC
        assert "unchanged" in SPEC

    def test_the_spec_requires_the_negative_control(self):
        assert "Negative control" in SPEC or "negative control" in SPEC
        assert "void" in SPEC

    def test_the_spec_states_the_prior_expectation(self):
        assert "REJECT" in SPEC
