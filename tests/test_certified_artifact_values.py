"""Value-pinning regression tests for the certified H10-H14 artifact chain.

The structural/count tests in test_h10_pfopt / test_h11_robustness /
test_h12_selection_bias / test_h13_oos_deflation_pf / test_h14_artifacts
verify schema, counts and boolean relationships, but NONE of them assert the
published (report-quoted) gate numbers themselves. These tests close that gap:
they read the committed frozen artifact files (summary.json + parquet) and
pin the headline certification numbers so that any drift in the published
results is caught as a hard failure.

These tests are read-only against the frozen artifacts (no pipeline
re-execution, no network) and run in <1s. They are a drift guard for the
*committed* certification, not a re-derivation of it.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / ".experiments" / "artifacts"

H10_DIR = ARTIFACTS / "exp_2026-10-11T17-41-18-169363Z"
H11_DIR = ARTIFACTS / "exp_2026-10-11T18-40-37-427062Z"
H12_DIR = ARTIFACTS / "exp_2026-10-13T12-51-06-515939Z"
H13_DIR = ARTIFACTS / "exp_2026-10-13T14-35-58-316759Z"
H14_DIR = ARTIFACTS / "exp_2026-10-13T19-01-59-371405Z"


def _summary(d: Path) -> dict:
    with open(d / "summary.json") as f:
        return json.load(f)


# Exact published certification numbers (frozen artifacts are static bytes).
PF = 1.3041645169434146
SR = 1.2757590680990518


class TestH10Certification:
    """H10 (intraday TSMOM, PF-optimized) is the first config to clear all gates."""

    def test_summary_pins(self):
        s = _summary(H10_DIR)
        assert s["hypothesis"] == "H10"
        assert s["verdict"] == "PASS"
        assert s["all_pass"] is True

    def test_selected_config(self):
        s = _summary(H10_DIR)
        cfg = s["selected_config"]
        assert cfg["vol_window_long"] == 1008
        assert cfg["smooth_span"] == "none"
        assert cfg["regime_scaling"] is False
        assert cfg["min_trade_interval"] == 0
        assert cfg["trailing_mult"] == 2.0
        assert cfg["max_hold_bars"] == 60
        assert cfg["vol_limit_mult"] == 1.5
        assert cfg["vol_floor_fraction"] == 0.25

    def test_oos_gate_values(self):
        m = _summary(H10_DIR)["metrics"]
        assert m["train_sharpe"] == pytest.approx(0.9588934313666013, abs=1e-12)
        assert m["test_sharpe"] == pytest.approx(1.0930742500890243, abs=1e-12)
        assert m["oos_sharpe"] == pytest.approx(SR, rel=1e-12, abs=1e-15)
        assert m["profit_factor"] == pytest.approx(PF, rel=1e-12, abs=1e-15)
        assert m["max_drawdown"] == pytest.approx(-0.05842847204487622, abs=1e-12)
        assert m["trades"] == 2416
        assert m["wf_stability"] == pytest.approx(0.7805709265313979, abs=1e-12)
        assert m["worst_regime_sharpe"] == pytest.approx(1.045717651017743, abs=1e-12)
        assert m["benchmark_p_value"] == pytest.approx(4.790305556723297e-10, rel=1e-9)
        assert m["information_ratio"] == pytest.approx(0.9247889169803807, abs=1e-12)

    def test_regime_sharpes(self):
        rs = _summary(H10_DIR)["metrics"]["regime_sharpes"]
        assert rs["bull"] == pytest.approx(1.045717651017743, abs=1e-12)
        assert rs["sideways"] == pytest.approx(1.1697883985727624, abs=1e-12)
        assert rs["bear"] == pytest.approx(1.7530420313316548, abs=1e-12)

    def test_gates_all_pass(self):
        gates = _summary(H10_DIR)["passes"]
        assert gates == {
            "sharpe": True,
            "trades": True,
            "pf": True,
            "dd": True,
            "stab": True,
            "worst": True,
            "p": True,
            "ir": True,
        }

    def test_regime_scaling_ablation_lowers_pf(self):
        """Pre-registered ablation: regime_scaling=True lowers OOS PF (the
        frozen grid result that motivates the data-wall handoff)."""
        abl = _summary(H10_DIR)["metrics"]["ablations"]["regime_scaling_only"]
        assert abl["oos_sharpe"] == pytest.approx(1.0212242716355602, abs=1e-12)
        assert abl["oos_profit_factor"] == pytest.approx(1.2485589178667436, abs=1e-12)
        assert abl["oos_profit_factor"] < PF


class TestH11Certification:
    """H11 robustness certification: bit-exact reproduction + perturbation."""

    def test_summary_pins(self):
        s = _summary(H11_DIR)
        assert s["hypothesis"] == "H11"
        assert s["verdict"] == "PASS"
        assert s["all_pass"] is True
        assert s["h10_artifact_id"] == "exp_2026-10-11T17-41-18-169363Z"

    def test_e1_determinism(self):
        e1 = _summary(H11_DIR)["e1_seed_robustness"]
        assert e1["determinism_holds"] is True
        assert {x["seed"] for x in e1["seeds"]} == {42, 7, 123, 2026}
        for seed in e1["seeds"]:
            assert seed["max_equity_abs_diff_vs_seed42"] == 0.0
            assert seed["oos_profit_factor"] == pytest.approx(PF, rel=1e-12)
            assert seed["oos_sharpe"] == pytest.approx(SR, rel=1e-12)

    def test_e1_bootstrap(self):
        e1 = _summary(H11_DIR)["e1_seed_robustness"]
        assert e1["bootstrap"][0]["seed"] == 42
        assert e1["bootstrap"][0]["n_bootstrap"] == 2000
        assert e1["bootstrap"][0]["frac_sharpe_ge_1"] == pytest.approx(0.8885, abs=1e-4)

    def test_e2_perturbation(self):
        e2 = _summary(H11_DIR)["e2_perturbation"]
        assert e2["frozen_oos_sharpe"] == pytest.approx(SR, rel=1e-12)
        assert e2["min_perturbed_sharpe"] == pytest.approx(1.026673203093223, abs=1e-12)
        assert e2["perturbation_ratio"] == pytest.approx(0.8047547760119159, abs=1e-9)
        assert e2["perturbation_ratio"] >= e2["gate_threshold"]
        assert e2["passes"] is True

    def test_e3_cost_stress(self):
        m = _summary(H11_DIR)
        e3 = m["e3_cost_stress"]
        assert e3["pf_at_1_0x"] == pytest.approx(PF, rel=1e-12)
        assert e3["pf_at_1_5x"] == pytest.approx(1.3003210899035884, abs=1e-12)
        assert e3["pf_at_2_0x"] == pytest.approx(1.2964769492672368, abs=1e-12)
        assert e3["breakeven_cost_multiplier_for_pf_1_3"] == pytest.approx(
            1.5418109506746565, abs=1e-6
        )
        assert e3["passes"] is True

    def test_e4_window_robustness(self):
        e4 = _summary(H11_DIR)["e4_window_robustness"]["shifted_splits"]
        by = {r["split"]: r for r in e4}
        assert by["60/20/20"]["oos_profit_factor"] == pytest.approx(
            1.3297783905647602, abs=1e-12
        )
        assert by["50/25/25"]["oos_profit_factor"] == pytest.approx(
            1.28064754854388, abs=1e-12
        )
        assert by["45/30/25"]["oos_profit_factor"] == pytest.approx(
            1.2915554339489663, abs=1e-12
        )
        rw = _summary(H11_DIR)["e4_window_robustness"]["rolling_window_summary"]
        assert rw["n_windows"] == 16
        assert rw["min_sharpe"] == pytest.approx(0.709065213698279, abs=1e-12)
        assert rw["max_sharpe"] == pytest.approx(1.4364684093648858, abs=1e-12)
        assert rw["frac_windows_sharpe_ge_1"] == pytest.approx(0.9375, abs=1e-4)

    def test_e5_per_symbol_concentration(self):
        e5 = _summary(H11_DIR)["e5_per_symbol"]
        assert e5["concentration_flag"] is False
        assert e5["hhi_abs_pnl_shares"] == pytest.approx(0.21370569410792872, abs=1e-9)
        assert e5["max_gross_profit_share"] < 0.25
        by = {x["symbol"]: x for x in e5["per_symbol"]}
        assert len(by) == 5
        assert by["CL=F"]["oos_profit_factor"] == pytest.approx(
            1.3578645592334793, abs=1e-12
        )

    def test_reproduction_vs_h10(self):
        """H11 must reproduce H10's frozen metrics bit-for-bit."""
        rep = _summary(H11_DIR)["f1"]["reproduced_vs_h10_artifact"]
        for key in [
            "oos_sharpe",
            "profit_factor",
            "max_drawdown",
            "trades",
            "wf_stability",
            "worst_regime_sharpe",
            "benchmark_p_value",
            "information_ratio",
        ]:
            assert rep[key]["reproduced"] is True
            assert rep[key]["abs_diff"] == 0.0


class TestH12Certification:
    """H12 selection-bias audit: DSR, PBO, family-wide multiple testing."""

    def test_summary_pins(self):
        s = _summary(H12_DIR)
        assert s["hypothesis"] == "H12"
        assert s["verdict"] == "PASS"
        assert s["all_pass"] is True

    def test_dsr(self):
        dsr = _summary(H12_DIR)["dsr"]
        assert dsr["n_trials_h10"] == 13824
        assert dsr["n_trials_family"] == 14389
        assert dsr["expected_max_sharpe_h10"] == pytest.approx(
            0.6213985379019645, abs=1e-12
        )
        assert dsr["dsr_adjusted_sharpe_h10"] == pytest.approx(
            1.409362160369927, abs=1e-9
        )
        assert dsr["p_value_h10"] == pytest.approx(0.0028335844626995454, rel=1e-6)
        assert dsr["dsr_adjusted_sharpe_family"] == pytest.approx(
            1.4092966525685025, abs=1e-9
        )

    def test_pbo(self):
        pbo = _summary(H12_DIR)["pbo"]
        assert pbo["pbo"] == pytest.approx(0.05519480519480519, abs=1e-12)
        assert pbo["n_combinations"] == 924
        assert pbo["n_strategies"] == 13824

    def test_family_correction(self):
        fw = _summary(H12_DIR)["family_wide"]
        assert fw["pooled_trials"] == 14389
        assert fw["bonferroni_p"] == pytest.approx(6.892770665569151e-06, rel=1e-6)
        assert fw["bh_fdr_p"] == pytest.approx(6.892770665569151e-06, rel=1e-6)
        assert fw["benchmark_p_value"] == pytest.approx(4.790305556723297e-10, rel=1e-6)
        assert fw["bonferroni_p"] < 0.05
        # Family-corrected DSR p-value (Bonferroni-style significance on the
        # family-wide selection, distinct from the H10-only p_value_h10 above).
        assert _summary(H12_DIR)["dsr"]["p_value_family"] == pytest.approx(
            0.0028799332163222946, rel=1e-6
        )

    def test_pf_margin(self):
        pm = _summary(H12_DIR)["pf_margin"]
        assert pm["frac_oos_pf_pass"] == pytest.approx(0.00318287037037037, abs=1e-9)
        assert pm["frac_val_pf_pass"] == pytest.approx(0.07262731481481481, abs=1e-9)
        assert pm["selected_val_profit_factor"] == pytest.approx(
            1.3527016462448131, abs=1e-9
        )


class TestH13Certification:
    """H13: Sharpe deflation PASSES, PF-margin/fragility REJECTED."""

    def test_summary_pins(self):
        s = _summary(H13_DIR)
        assert s["hypothesis"] == "H13"
        assert s["verdict"] == "REJECT"
        assert s["all_pass"] is False

    def test_deflation_gate_passes(self):
        d = _summary(H13_DIR)["oos_deflation"]
        assert d["n_trials_worst_case"] == 13824
        assert d["dsr_adjusted_sharpe_worst_case"] == pytest.approx(
            1.2744528901196646, abs=1e-9
        )
        assert d["p_value_worst_case"] == pytest.approx(0.0010238437743056439, rel=1e-6)
        assert d["dsr_adjusted_sharpe_worst_case"] >= 1.0

    def test_pf_bootstrap_gate_fails(self):
        b = _summary(H13_DIR)["pf_bootstrap"]
        assert b["n_bootstrap"] == 2000
        assert b["seed"] == 42
        assert b["ci_95_lower"] == pytest.approx(1.1900177977043005, abs=1e-12)
        assert b["ci_95_upper"] == pytest.approx(1.42483816902447, abs=1e-12)
        assert b["median"] == pytest.approx(1.3022402697761128, abs=1e-12)
        assert b["point_estimate"] == pytest.approx(PF, rel=1e-12)
        assert b["frac_ge_1_3"] == pytest.approx(0.517, abs=1e-4)
        assert b["ci_95_lower"] < 1.3  # gate FAILS

    def test_per_symbol_dispensability(self):
        ps = _summary(H13_DIR)["per_symbol_net_oos"]
        # CL=F and GC=F indispensable (leave-one-out pooled PF < 1.3)
        assert ps["CL=F"]["leave_one_out_pooled_pf"] == pytest.approx(
            1.249383030332208, abs=1e-9
        )
        assert ps["GC=F"]["leave_one_out_pooled_pf"] == pytest.approx(
            1.2821295085444708, abs=1e-9
        )
        assert ps["CL=F"]["leave_one_out_pooled_pf"] < 1.3
        assert ps["GC=F"]["leave_one_out_pooled_pf"] < 1.3
        # ES/ZB dispensable
        assert ps["ES=F"]["leave_one_out_pooled_pf"] >= 1.3
        assert ps["ZB=F"]["leave_one_out_pooled_pf"] >= 1.3
        assert ps["CL=F"]["net_profit_factor"] == pytest.approx(
            1.3578645592334793, abs=1e-12
        )

    def test_gates(self):
        g = _summary(H13_DIR)["gates"]
        assert g["worst_case_dsr_adjusted_oos_sharpe_ge_1.0"] is True
        assert g["pf_bootstrap_ci_lower_ge_1.3"] is False
        assert g["all_symbols_dispensable_lou_pf_ge_1.3"] is False

    def test_cost_break_even(self):
        cb = _summary(H13_DIR)["cost_breakeven"]
        assert cb["breakeven_multiplier"] == pytest.approx(1.5419921875, abs=1e-6)
        assert cb["h11_interpolated"] == pytest.approx(1.5418109506746565, abs=1e-6)
        # 1.542x: costs would need to more than double to break even -> costs immaterial
        assert cb["breakeven_multiplier"] > 1.5

    def test_reproduction_invariants(self):
        r = _summary(H13_DIR)["reproduction_checks"]
        assert r["returns_max_abs_diff_vs_h10"] == 0.0
        assert r["per_symbol_reconstruction_max_abs_diff"] == pytest.approx(
            6.938893903907228e-18, abs=1e-20
        )

    def test_shifted_split_pf_shortfalls(self):
        """Pre-registered: 50/25/25 and 45/30/25 splits drop PF below 1.3
        (driven by CL=F on the bull regime)."""
        rows = {r["split"]: r for r in _summary(H13_DIR)["shifted_splits"]["results"]}
        assert rows["50/25/25"]["oos_profit_factor"] == pytest.approx(
            1.28064754854388, abs=1e-12
        )
        assert rows["45/30/25"]["oos_profit_factor"] == pytest.approx(
            1.2915554339489663, abs=1e-12
        )
        assert rows["50/25/25"]["oos_profit_factor"] < 1.3
        assert rows["45/30/25"]["oos_profit_factor"] < 1.3


class TestH14Certification:
    """H14: PF-margin fragility is a FAMILY property (0/50 clear all gates)."""

    def test_summary_pins(self):
        s = _summary(H14_DIR)
        assert s["hypothesis"] == "H14"
        assert s["verdict"] == "REJECT"
        assert s["k_top"] == 50
        assert s["configs_evaluated"] == 50
        assert s["topk_count"] == 50
        assert s["n_passing"] == 0
        assert s["all_pass"] is False
        assert s["min_pf_gate"] == 1.3
        assert s["min_sr_gate"] == 1.0

    def test_results_gate_landscape(self):
        df = pd.read_parquet(H14_DIR / "h14_results.parquet")
        assert len(df) == 50
        # No config clears all three gates
        passes = df[
            (df["pf_boot_ci_lb"] >= 1.3)
            & (df["dsr_adj_sharpe_at_k"] >= 1.0)
            & (df["all_symbols_dispensable"])
        ]
        assert len(passes) == 0
        # All have DSR >= 1.0
        assert (df["dsr_adj_sharpe_at_k"] >= 1.0).all()
        # All fail the PF bootstrap CI lower-bound gate
        assert (df["pf_boot_ci_lb"] < 1.3).all()
        assert df["pf_boot_ci_lb"].max() == pytest.approx(1.1993148493610435, abs=1e-12)
        # All carry the CL/GC dispensability dependency
        assert (~df["all_symbols_dispensable"]).all()

    def test_topk_subset_consistency(self):
        res = pd.read_parquet(H14_DIR / "h14_results.parquet")
        topk = pd.read_parquet(H14_DIR / "topk_selected.parquet")
        assert len(topk) == len(res) == 50
        assert set(res["combo_index"].astype(int)) == set(
            topk["combo_index"].astype(int)
        )

    def test_subset_oos_metrics(self):
        df = pd.read_parquet(H14_DIR / "subset_oos_metrics.parquet")
        assert len(df) == 50


class TestCrossArtifactIdentity:
    """The H10/H11/H13 OOS numbers are the SAME frozen quantity, reproduced
    bit-for-bit across the certification chain."""

    def test_oos_pf_identical_across_chain(self):
        h10_pf = _summary(H10_DIR)["metrics"]["profit_factor"]
        h11_pf = _summary(H11_DIR)["f1"]["oos_metrics"]["profit_factor"]
        h13_pf = _summary(H13_DIR)["oos_window"]["selected_oos_profit_factor"]
        assert h10_pf == pytest.approx(PF, rel=1e-12)
        assert h11_pf == PF
        assert h13_pf == PF

    def test_oos_sharpe_identical_across_chain(self):
        h10_sr = _summary(H10_DIR)["metrics"]["oos_sharpe"]
        h11_sr = _summary(H11_DIR)["f1"]["oos_metrics"]["sharpe"]
        h13_sr = _summary(H13_DIR)["oos_window"]["selected_oos_sharpe"]
        assert h10_sr == pytest.approx(SR, rel=1e-12)
        assert h11_sr == SR
        assert h13_sr == SR

    def test_oos_n_periods_and_trades_consistent(self):
        assert _summary(H11_DIR)["f1"]["oos_metrics"]["n_periods"] == 5148
        assert _summary(H11_DIR)["f1"]["oos_metrics"]["trades"] == 2416
        assert _summary(H13_DIR)["oos_window"]["n_bars"] == 5148
