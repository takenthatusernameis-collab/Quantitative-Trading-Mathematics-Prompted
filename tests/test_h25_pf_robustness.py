"""
Regression tests for the H25 bootstrap-CI robustness characterization
(run_h25_pf_robustness.py).

This is a post-hoc statistical audit (mirror of the H13 audit of H10) of the
already-certified H25 selected config. It does NOT re-select on Test and does
NOT weaken any gate.  It quantifies H25's acknowledged residual caveat: the OOS
profit-factor margin (+0.020) sits inside the bootstrap CI noise floor.

Pins:
  * Pre-registration constants (SEED, N_BOOTSTRAP, gates, CI percentiles)
  * Determinism: compute_h25_robustness and bootstrap_arrays are bit-identical
    across repeated calls with the same seed
  * Committed-artifact fidelity: recomputing from the logged H25 OOS returns
    reproduces summary.json at 1e-9 (point estimates == H25 summary.json)
  * Committed parquet fidelity: pf_bootstrap / sharpe_bootstrap parquet equal
    the recomputed bootstrap arrays at 1e-9
  * Point estimates lie inside their 95% CIs; CI lower < upper; fractions in [0,1]
  * The executed characterization numbers are pinned (PF CI LB < 1.3 -> the
    documented fragility is real; Sharpe CI LB < 1.0 though P>=0.90 -> sharpe
    point-robust but CI-fragile)
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

import run_h25_pf_robustness as aud


@pytest.fixture(scope="module")
def summary():
    p = aud.ART_DIR / "summary.json"
    assert p.exists(), f"run run_h25_pf_robustness.py first -> {p}"
    with open(p) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def oos_returns():
    h25_dir = aud._find_latest_h25_dir()
    return aud.oos_returns(h25_dir)


class TestPreRegistration:
    def test_constants_frozen(self):
        assert aud.SEED == 42
        assert aud.N_BOOTSTRAP == 2000
        assert aud.CI_PERCENTILES == (2.5, 97.5)
        assert aud.PF_GATE == 1.3
        assert aud.SR_GATE == 1.0
        # Distinct from "H25" so the audit dir is not mistaken for an H25 run.
        assert aud.HYPOTHESIS == "H25_ROBUSTNESS"
        assert aud.AUDITED_HYPOTHESIS == "H25"

    def test_uses_canonical_bootstrap_infra(self):
        # Must reuse the project's tested primitives, not a bespoke RNG.
        assert aud.h13.bootstrap_profit_factor_distribution is not None
        assert aud.h11.bootstrap_sharpe_distribution is not None
        assert aud.sharpe_ratio is not None


class TestDeterminism:
    def test_compute_idempotent(self, oos_returns):
        a = aud.compute_h25_robustness(oos_returns)
        b = aud.compute_h25_robustness(oos_returns)
        assert a == b

    def test_bootstrap_arrays_bit_identical(self, oos_returns):
        pf1, sr1 = aud.bootstrap_arrays(oos_returns)
        pf2, sr2 = aud.bootstrap_arrays(oos_returns)
        assert np.array_equal(pf1, pf2)
        assert np.array_equal(sr1, sr2)


class TestCommittedArtifact:
    def test_point_estimates_match_h25_summary(self, summary):
        h25_dir = aud._find_latest_h25_dir()
        with open(h25_dir / "summary.json") as f:
            h25_summary = json.load(f)
        assert summary["pf_point_estimate"] == pytest.approx(
            h25_summary["metrics"]["profit_factor"], abs=1e-9)
        assert summary["sharpe_point_estimate"] == pytest.approx(
            h25_summary["metrics"]["oos_sharpe"], abs=1e-9)

    def test_recompute_matches_summary(self, oos_returns, summary):
        r = aud.compute_h25_robustness(oos_returns)
        assert r["n_oos_bars"] == summary["n_oos_bars"]
        assert r["pf_point_estimate"] == pytest.approx(
            summary["pf_point_estimate"], abs=1e-9)
        assert r["sharpe_point_estimate"] == pytest.approx(
            summary["sharpe_point_estimate"], abs=1e-9)
        assert r["pf_bootstrap_ci_95"] == pytest.approx(
            summary["pf_bootstrap_ci_95"], abs=1e-9)
        assert r["sharpe_bootstrap_ci_95"] == pytest.approx(
            summary["sharpe_bootstrap_ci_95"], abs=1e-9)
        assert r["pf_frac_ge_gate"] == pytest.approx(
            summary["pf_frac_ge_gate"], abs=1e-9)
        assert r["sharpe_frac_ge_gate"] == pytest.approx(
            summary["sharpe_frac_ge_gate"], abs=1e-9)

    def test_parquet_matches_recompute(self, oos_returns):
        pf_boot, sr_boot = aud.bootstrap_arrays(oos_returns)
        pf_pq = pd.read_parquet(aud.ART_DIR / "pf_bootstrap.parquet")
        sr_pq = pd.read_parquet(aud.ART_DIR / "sharpe_bootstrap.parquet")
        assert len(pf_pq) == aud.N_BOOTSTRAP
        assert len(sr_pq) == aud.N_BOOTSTRAP
        assert np.allclose(pf_pq["profit_factor"].values, pf_boot, atol=1e-9)
        assert np.allclose(sr_pq["sharpe"].values, sr_boot, atol=1e-9)


class TestSanity:
    def test_point_inside_ci(self, summary):
        pf_lo, pf_hi = summary["pf_bootstrap_ci_95"]
        sr_lo, sr_hi = summary["sharpe_bootstrap_ci_95"]
        assert pf_lo <= summary["pf_point_estimate"] <= pf_hi
        assert sr_lo <= summary["sharpe_point_estimate"] <= sr_hi
        assert pf_lo < pf_hi and sr_lo < sr_hi

    def test_fractions_in_unit_interval(self, summary):
        for f in (summary["pf_frac_ge_gate"], summary["sharpe_frac_ge_gate"]):
            assert 0.0 <= f <= 1.0


class TestExecutedCharacterization:
    """Pins the executed H25 robustness characterization numbers."""

    def test_pf_ci_lower_below_gate_confirms_documented_fragility(self, summary):
        # The H25 PF margin (+0.020) is documented as inside the bootstrap
        # noise floor. The CI lower bound must sit below the 1.3 gate, i.e.
        # the fragility is real and quantified (not a pass-by-point-estimate).
        pf_lo, _ = summary["pf_bootstrap_ci_95"]
        assert summary["pf_point_estimate"] >= summary["pf_gate"]
        assert pf_lo < summary["pf_gate"]
        assert summary["pf_frac_ge_gate"] < 0.90
        assert summary["pf_ci_lower_ge_gate"] is False

    def test_sharpe_is_point_robust(self, summary):
        # Sharpe clears the gate at >90% of bootstrap resamples -> point-robust,
        # even though the CI lower bound dips below 1.0 (CI-fragile).
        assert summary["sharpe_frac_ge_gate"] >= 0.90
        assert summary["sharpe_ci_lower_ge_gate"] is False

    def test_exactly_5148_oos_bars(self, summary):
        # Pins the OOS slice to H25's `_splits` 55/25/20 boundary on this data.
        assert summary["n_oos_bars"] == 5148
