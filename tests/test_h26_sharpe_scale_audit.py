"""H26 regression tests: the Sharpe annualization-scale audit.

H26 (pre-registered in ``HYPOTHESIS_SPEC.md`` §H26) characterizes a
cross-cutting defect in the published record: every "OOS Sharpe" in this
project is ``sharpe_ratio(returns)`` with the default
``periods_per_year=252``, i.e. the **per-bar** mean/vol ratio times
``sqrt(252)``.  For the daily families the bar is a trading day, so
``sqrt(252)`` *is* the calendar annualization; for the intraday (1h)
families the bar is one hour and the same multiplier annualizes neither
the trading year nor the calendar year.

These tests pin:

* the audit's reproduction of every audited artifact's published Sharpe,
* the scale factors and the corrected (annualized) Sharpe values,
* the linear rescaling of the bootstrap CI and the *recomputed* gate
  fraction at each scale,
* the daily control (the daily family was already correctly annualized),
* the H9 exclusion and its two diagnosed causes,
* the library helpers ``bars_per_year`` / ``annualized_sharpe``.

They are read-only against the frozen artifacts (no pipeline re-execution,
no network) and run in well under a second.
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

from qtr.validation.statistics import (
    annualized_sharpe,
    bars_per_year,
    sharpe_ratio,
)

SUMMARY_PATH = ROOT / ".experiments" / "artifacts" / "h26_sharpe_scale" / "summary.json"
TABLE_PATH = ROOT / ".experiments" / "artifacts" / "h26_sharpe_scale" / "scale_table.parquet"

# The committed H25 robustness audit -- the published source of the
# "Sharpe CI-fragile" caveat that H26 re-characterizes.
PF_ROBUSTNESS = ROOT / ".experiments" / "artifacts" / "pf_robustness" / "summary.json"


def _summary() -> dict:
    with open(SUMMARY_PATH) as f:
        return json.load(f)


def _audited() -> dict:
    return {a["family"]: a for a in _summary()["audited"]}


def _excluded() -> dict:
    return {a["family"]: a for a in _summary()["excluded"]}


class TestAuditSummary:
    """The audit artifact itself."""

    def test_summary_pins(self):
        s = _summary()
        assert s["hypothesis"] == "H26"
        assert s["kind"] == "audit"
        assert s["seed"] == 42
        assert s["n_bootstrap"] == 2000
        assert s["sharpe_gate"] == 1.0
        assert s["as_published_factor"] == pytest.approx(np.sqrt(252), rel=1e-12)
        assert s["repo_vol_factor"] == pytest.approx(np.sqrt(252 * 6.5), rel=1e-12)

    def test_verdict(self):
        v = _summary()["verdict"]
        assert v["scale_confirmed"] is True
        assert v["control_ok"] is True

    def test_audited_families(self):
        assert set(_audited()) == {"H10", "H21", "H22", "H23", "H25"}
        assert set(_excluded()) == {"H9"}

    def test_scale_table_artifact(self):
        df = pd.read_parquet(TABLE_PATH)
        assert set(df["family"]) == {"H10", "H21", "H22", "H23", "H25"}
        assert set(df["scale"]) == {
            "as_published",
            "repo_vol_convention",
            "empirical_calendar",
            "daily_aggregated_sqrt252",
        }


class TestReproductionAnchor:
    """Every audited artifact is reproduced bit-close from its frozen returns."""

    @pytest.mark.parametrize("family", ["H10", "H21", "H22", "H23", "H25"])
    def test_reproduced(self, family):
        a = _audited()[family]
        assert a["reproduced"] is True
        assert a["reproduction_abs_diff"] <= 1e-9
        assert a["recomputed_oos_sharpe"] == pytest.approx(
            a["published_oos_sharpe"], rel=1e-12, abs=1e-15
        )

    @pytest.mark.parametrize("family", ["H10", "H21", "H22", "H23", "H25"])
    def test_published_sharpe_is_the_sqrt252_per_bar_metric(self, family):
        """The published metric is exactly per-bar Sharpe x sqrt(252).

        This is the defect itself, pinned: if the published number were an
        annualized Sharpe it would have to equal the empirical-calendar
        value instead.
        """
        a = _audited()[family]
        as_published = a["scales"]["as_published"]
        assert as_published["sharpe"] == pytest.approx(
            a["published_oos_sharpe"], rel=1e-12, abs=1e-15
        )
        assert a["scales"]["empirical_calendar"]["sharpe"] != pytest.approx(
            a["published_oos_sharpe"], rel=1e-3
        )

    def test_published_convention_is_population_std(self):
        for a in _audited().values():
            assert a["sharpe_convention_check"]["published_convention"] == ("population_ddof0")


class TestScaleFactors:
    """The annualization factors and the corrected Sharpe values."""

    def test_repo_vol_convention_factor(self):
        expected = np.sqrt(252 * 6.5) / np.sqrt(252)
        assert expected == pytest.approx(2.549509756796992, rel=1e-12)
        for a in _audited().values():
            assert a["scale_ratio_repo_vol_over_published"] == pytest.approx(expected, rel=1e-12)

    def test_empirical_calendar_ratio(self):
        a = _audited()["H25"]
        assert a["bars_per_day"] == pytest.approx(15.6098, abs=1e-3)
        assert a["scale_ratio_empirical_over_published"] == pytest.approx(4.7566, rel=1e-4)

    @pytest.mark.parametrize(
        "family,published,repo_vol,empirical",
        [
            ("H10", 1.2757590680990518, 3.2525601914400055, 6.0682),
            ("H22", 1.3724750832147166, 3.4991, 6.5283),
            ("H25", 1.3236288879255962, 3.3746, 6.2959),
        ],
    )
    def test_corrected_sharpe_values(self, family, published, repo_vol, empirical):
        a = _audited()[family]
        assert a["published_oos_sharpe"] == pytest.approx(published, rel=1e-12)
        assert a["scales"]["repo_vol_convention"]["sharpe"] == pytest.approx(repo_vol, rel=1e-4)
        assert a["scales"]["empirical_calendar"]["sharpe"] == pytest.approx(empirical, rel=1e-4)

    def test_corrected_sharpe_magnitude_is_larger_than_published(self):
        """The mis-scaling is conservative: it understates the edge.

        (For a negative-Sharpe family the rescaled value is more negative,
        so the comparison is on magnitudes.)
        """
        for a in _audited().values():
            assert abs(a["scales"]["repo_vol_convention"]["sharpe"]) > abs(
                a["published_oos_sharpe"]
            )


class TestBootstrapRescaling:
    """The CI scales linearly with the annualization factor; the gate
    fraction is recomputed, never rescaled."""

    @pytest.mark.parametrize("family", ["H10", "H21", "H22", "H23", "H25"])
    def test_ci_scales_linearly(self, family):
        a = _audited()[family]
        base = a["scales"]["as_published"]
        for name in ("repo_vol_convention", "empirical_calendar"):
            s = a["scales"][name]
            ratio = s["factor"] / base["factor"]
            assert s["ci_95"][0] == pytest.approx(base["ci_95"][0] * ratio, rel=1e-12)
            assert s["ci_95"][1] == pytest.approx(base["ci_95"][1] * ratio, rel=1e-12)

    def test_h25_as_published_ci_matches_published_robustness_audit(self):
        """The as-published CI is exactly the one quoted in the record."""
        with open(PF_ROBUSTNESS) as f:
            rob = json.load(f)
        a = _audited()["H25"]
        assert a["scales"]["as_published"]["ci_95"] == pytest.approx(
            rob["sharpe_bootstrap_ci_95"], rel=1e-12
        )
        assert a["scales"]["as_published"]["frac_ge_gate"] == pytest.approx(
            rob["sharpe_frac_ge_gate"], rel=1e-12
        )

    def test_sharpe_ci_fragility_is_a_scale_artifact(self):
        """As published the CI lower bound dips below 1.0; under the repo's
        own annualization convention it does not. The 'Sharpe CI-fragile'
        caveat is therefore a property of the metric scale, not of the edge."""
        for family in ("H10", "H22", "H25"):
            a = _audited()[family]
            assert a["scales"]["as_published"]["ci_lower_ge_gate"] is False
            assert a["scales"]["repo_vol_convention"]["ci_lower_ge_gate"] is True
            assert a["scales"]["repo_vol_convention"]["frac_ge_gate"] == 1.0

    def test_gate_fraction_is_recomputed_not_rescaled(self):
        a = _audited()["H25"]
        base = a["scales"]["as_published"]
        scaled = a["scales"]["repo_vol_convention"]
        # A linear rescale of the fraction would leave it at 0.9275.
        assert scaled["frac_ge_gate"] == 1.0
        assert base["frac_ge_gate"] == pytest.approx(0.9275, abs=1e-4)


class TestDailyControl:
    """The daily family was already correctly annualized (unaffected)."""

    def test_control_factor_is_one(self):
        c = _summary()["daily_control"]
        assert c["family"] == "H16"
        assert c["bars_per_year_empirical"] == pytest.approx(251.75, abs=0.05)
        assert c["scale_ratio_empirical_over_published"] == pytest.approx(1.0, abs=0.01)
        assert c["is_correctly_annualized"] is True


class TestH9Exclusion:
    """H9 is excluded by the pre-registered reproduction rule; the two
    causes of the mismatch are diagnosed and neither changes its verdict."""

    def test_excluded_with_reason(self):
        h9 = _excluded()["H9"]
        assert h9["reproduced"] is False
        assert "reproduction failed" in h9["excluded_reason"]

    def test_sharpe_convention_drift(self):
        """H9 was published with the sample-std (ddof=1) Sharpe estimator."""
        h9 = _excluded()["H9"]
        check = h9["sharpe_convention_check"]
        assert check["published_convention"] == "sample_ddof1"
        assert check["abs_diff_ddof1"] <= 1e-9
        assert check["abs_diff_ddof0"] > 1e-9

    def test_pf_gate_window_defect(self):
        """H9's published profit factor is the FULL-SAMPLE (train+val+test)
        profit factor, so the PF gate saw the training window."""
        h9 = _excluded()["H9"]
        pf = h9["pf_window_check"]
        assert pf["published_pf_window"] == "full_sample"
        assert pf["abs_diff_full_sample"] <= 1e-9
        assert pf["abs_diff_oos_window"] > 1e-9
        # The correct OOS-window PF is *higher* than the published one, and
        # both are below the 1.3 gate -> H9 stays REJECTED either way.
        assert pf["oos_window_profit_factor"] > pf["published_profit_factor"]
        assert pf["oos_window_profit_factor"] < 1.3
        assert pf["published_profit_factor"] < 1.3

    def test_audited_families_pf_window_is_oos(self):
        for family, a in _audited().items():
            if family == "H23":
                # 134 OOS bars out of 300: the train window is flat, so the
                # two windows coincide and the check is ambiguous by design.
                assert a["pf_window_check"]["published_pf_window"] in (
                    "oos_window",
                    "ambiguous_both_match",
                )
            else:
                assert a["pf_window_check"]["published_pf_window"] == "oos_window"


class TestDependence:
    """Square-root scaling is only meaningful if the returns are close to
    serially independent; the audit records the diagnostics.

    The four futures families (5,148 OOS bars each) are effectively
    independent, so the sqrt-scaling is sound there.  H23's crypto slice is
    only 134 bars and is strongly positively autocorrelated, so its
    rescaled value is *not* a reliable annualized Sharpe -- which is
    immaterial because H23 is REJECTED, but is recorded rather than hidden.
    """

    FUTURES = ("H10", "H21", "H22", "H25")

    def test_weak_autocorrelation(self):
        for family in self.FUTURES:
            a = _audited()[family]
            assert a["dependence"]["max_abs_autocorrelation_lag1_24"] < 0.15

    def test_newey_west_lrv_close_to_iid_variance(self):
        for family in self.FUTURES:
            a = _audited()[family]
            for ratio in a["dependence"]["lrv_ratio_vs_iid"].values():
                assert 0.5 < ratio < 2.0

    def test_h23_scaling_is_not_reliable(self):
        """H23's short crypto slice is autocorrelated -> the sqrt-scaling
        overstates its annualized value; documented, not hidden."""
        a = _audited()["H23"]
        assert a["n_oos_bars"] < 200
        assert a["dependence"]["autocorrelation"]["lag_1"] > 0.3
        assert a["dependence"]["lrv_ratio_vs_iid"]["lag_24"] > 1.5


class TestLibraryHelpers:
    """``bars_per_year`` / ``annualized_sharpe`` (added for this audit)."""

    def test_daily_index_implies_252_bars_per_year(self):
        """A real trading-day index implies ~252 bars per calendar year."""
        idx = pd.read_parquet(
            ROOT
            / ".experiments"
            / "artifacts"
            / "exp_2026-10-13T21-22-02-751156Z"
            / "prices.parquet"
        ).index
        assert bars_per_year(idx) == pytest.approx(251.75, abs=0.05)
        # A generic business-day index is slightly denser (~261/yr) than a
        # market trading-day index (holidays), so the factor is near 252.
        generic = pd.date_range("2020-01-01", periods=504, freq="B")
        assert bars_per_year(generic) == pytest.approx(252.0, rel=0.05)

    def test_hourly_index_implies_more_bars_per_year(self):
        idx = pd.date_range("2020-01-01", periods=24 * 365, freq="h")
        assert bars_per_year(idx) == pytest.approx(8760.0, rel=0.01)

    def test_annualized_sharpe_uses_the_index_frequency(self):
        idx = pd.date_range("2020-01-01", periods=24 * 200, freq="h")
        r = np.random.default_rng(0).normal(1e-4, 1e-3, size=len(idx))
        bpy = bars_per_year(idx)
        assert annualized_sharpe(r, idx) == pytest.approx(
            sharpe_ratio(r, periods_per_year=bpy), rel=1e-12
        )
        # A daily-annualized Sharpe is materially smaller for hourly bars.
        assert annualized_sharpe(r, idx) > sharpe_ratio(r) * 1.5

    def test_degenerate_index(self):
        assert np.isnan(bars_per_year(pd.DatetimeIndex(["2020-01-01"])))
        assert np.isnan(bars_per_year(pd.DatetimeIndex([])))
        # Two bars with no elapsed time -> no measurable frequency.
        assert np.isnan(bars_per_year(pd.DatetimeIndex(["2020-01-01", "2020-01-01"])))
        assert annualized_sharpe(np.zeros(1), pd.DatetimeIndex(["2020-01-01"])) == 0.0


class TestNegativeGuards:
    """Negative tests: each fails if the corresponding correction is undone.

    * If the scale correction were removed (i.e. the published metric were
      treated as an annualized Sharpe), the per-family ratio guards fail.
    * If ``bars_per_year`` always returned the daily constant 252, the
      hourly factor guard fails.
    * If the H9 diagnosis were wrong, the convention/window guards fail.
    """

    def test_detects_unlabelled_scale_drift(self):
        a = _audited()["H25"]
        published = a["published_oos_sharpe"]
        annualized = a["scales"]["empirical_calendar"]["sharpe"]
        # The published metric is NOT an annualized Sharpe.
        assert annualized != pytest.approx(published, rel=1e-2)
        assert annualized / published == pytest.approx(4.7566, rel=1e-4)

    def test_detects_hardcoded_daily_annualization(self):
        """A helper that always returns 252 would break the hourly factor."""
        hourly = bars_per_year(pd.date_range("2020-01-01", periods=24 * 365, freq="h"))
        assert hourly > 1000
        assert hourly != pytest.approx(252.0, rel=0.1)

    def test_detects_wrong_pf_gate_window(self):
        """If the H9 PF had been computed on the OOS window, the published
        value would match the OOS PF -- the defect guard would fail."""
        h9 = _excluded()["H9"]
        pf = h9["pf_window_check"]
        assert pf["published_profit_factor"] != pytest.approx(
            pf["oos_window_profit_factor"], rel=1e-6
        )
        assert pf["published_profit_factor"] == pytest.approx(
            pf["full_sample_profit_factor"], rel=1e-12
        )
