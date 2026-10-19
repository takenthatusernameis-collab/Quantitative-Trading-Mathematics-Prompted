"""Value-pinning regression tests for the certified H22 and H25 artifact chain.

Pins the headline certification numbers (OOS Sharpe, profit factor, max
drawdown, trades, walk-forward stability, worst-regime Sharpe, benchmark
p-value, information ratio) as literals against the committed frozen artifact
summary.json files.

Mirrors tests/test_certified_artifact_values.py, which does the same for
H10-H14 but left H22/H25 unpinned. Those two are the strongest certified
edges (FINAL_REPORT.md: H22 strongest Sharpe 1.372, H25 strongest PF-margin
repair 1.320), so their published numbers deserve the same hard drift guard:
any re-run that drifts the certified numbers fails here rather than silently
corroding the certification.

These tests are read-only against the frozen artifacts (no pipeline
re-execution, no network) and run in <1s. They are a drift guard for the
*committed* certification, not a re-derivation of it.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))

ARTIFACTS = ROOT / ".experiments" / "artifacts"

H22_DIR = ARTIFACTS / "exp_2026-10-14T18-52-08-943792Z"
H25_DIR = ARTIFACTS / "exp_2026-10-14T20-08-34-613690Z"


def _summary(d: Path) -> dict:
    with open(d / "summary.json") as f:
        return json.load(f)


# Exact published certification numbers (frozen artifacts are static bytes).
H22_SR = 1.3724750832147166
H22_PF = 1.334150203648997

H25_SR = 1.3236288879255962
H25_PF = 1.3201316886422707


class TestH22Certification:
    """H22 (multi-contract intraday futures TSMOM, vol-targeting gap closed) is
    certified PASS: strongest Sharpe of the certified family (9/9 gates)."""

    def test_summary_pins(self):
        s = _summary(H22_DIR)
        assert s["hypothesis"] == "H22"
        assert s["verdict"] == "PASS"
        assert s["all_pass"] is True

    def test_selected_config(self):
        s = _summary(H22_DIR)
        cfg = s["selected_config"]
        assert cfg["target_vol_mult"] == 1.0
        assert cfg["max_pos"] == 0.5
        assert cfg["scale_rule"] == "equal"
        assert cfg["n_assets"] == 5
        base = cfg["h10_base_config"]
        assert base["vol_window_long"] == 1008
        assert base["smooth_span"] is None
        assert base["regime_scaling"] is False
        assert base["min_trade_interval"] == 0
        assert base["trailing_mult"] == 2.0
        assert base["max_hold_bars"] == 60
        assert base["vol_limit_mult"] == 1.5
        assert base["vol_floor_fraction"] == 0.25

    def test_oos_gate_values(self):
        m = _summary(H22_DIR)["metrics"]
        assert m["train_sharpe"] == pytest.approx(1.1287879743988896, abs=1e-12)
        assert m["val_sharpe"] == pytest.approx(1.4744477045430648, abs=1e-12)
        assert m["test_sharpe"] == pytest.approx(1.2338683717453456, abs=1e-12)
        assert m["oos_sharpe"] == pytest.approx(H22_SR, rel=1e-12, abs=1e-15)
        assert m["profit_factor"] == pytest.approx(H22_PF, rel=1e-12, abs=1e-15)
        assert m["max_drawdown"] == pytest.approx(-0.11914252854616503, abs=1e-12)
        assert m["trades"] == 3045
        assert m["wf_stability"] == pytest.approx(0.7591247935618846, abs=1e-12)
        assert m["worst_regime_sharpe"] == pytest.approx(1.1292798467863572, abs=1e-12)
        assert m["benchmark_p_value"] == pytest.approx(1.3340812548651885e-19, rel=1e-9)
        assert m["information_ratio"] == pytest.approx(1.3466905696542812, abs=1e-12)

    def test_regime_sharpes(self):
        rs = _summary(H22_DIR)["metrics"]["regime_sharpes"]
        assert rs["bull"] == pytest.approx(1.245038554656642, abs=1e-12)
        assert rs["sideways"] == pytest.approx(1.1292798467863572, abs=1e-12)
        assert rs["bear"] == pytest.approx(2.004105338021563, abs=1e-12)

    def test_gates_all_pass(self):
        gates = _summary(H22_DIR)["passes"]
        assert gates == {
            "sharpe": True,
            "trades": True,
            "pf": True,
            "dd": True,
            "stab": True,
            "worst": True,
            "p": True,
            "ir": True,
            "perturbation": True,
        }

    def test_computation_budget_respected(self):
        s = _summary(H22_DIR)
        assert s["compute_cpu_hours"] <= 2.0


class TestH25Certification:
    """H25 (futures TSMOM basket, PF-margin repair by vol-targeting expansion,
    pruned 4-contract basket dropping CL=F) is certified PASS: strongest
    profit-factor margin of the certified family (9/9 gates, qualified by a
    CI-fragile PF audit)."""

    def test_summary_pins(self):
        s = _summary(H25_DIR)
        assert s["hypothesis"] == "H25"
        assert s["verdict"] == "PASS"
        assert s["all_pass"] is True

    def test_selected_config(self):
        s = _summary(H25_DIR)
        cfg = s["selected_config"]
        assert cfg["target_vol_mult"] == 1.75
        assert cfg["max_pos"] == 0.5
        assert cfg["scale_rule"] == "equal"
        assert cfg["n_assets"] == 4
        base = cfg["h10_base_config"]
        assert base["vol_window_long"] == 1008
        assert base["smooth_span"] is None
        assert base["regime_scaling"] is False
        assert base["min_trade_interval"] == 0
        assert base["trailing_mult"] == 2.0
        assert base["max_hold_bars"] == 60
        assert base["vol_limit_mult"] == 1.5
        assert base["vol_floor_fraction"] == 0.25

    def test_oos_gate_values(self):
        m = _summary(H25_DIR)["metrics"]
        assert m["train_sharpe"] == pytest.approx(1.1709790993030502, abs=1e-12)
        assert m["val_sharpe"] == pytest.approx(1.4356822087995853, abs=1e-12)
        assert m["test_sharpe"] == pytest.approx(1.170237299474902, abs=1e-12)
        assert m["oos_sharpe"] == pytest.approx(H25_SR, rel=1e-12, abs=1e-15)
        assert m["profit_factor"] == pytest.approx(H25_PF, rel=1e-12, abs=1e-15)
        assert m["max_drawdown"] == pytest.approx(-0.11914252854616447, abs=1e-12)
        assert m["trades"] == 1712
        assert m["wf_stability"] == pytest.approx(0.8726919975457872, abs=1e-12)
        assert m["worst_regime_sharpe"] == pytest.approx(1.1880923542184698, abs=1e-12)
        assert m["benchmark_p_value"] == pytest.approx(1.4028853805082562e-19, rel=1e-9)
        assert m["information_ratio"] == pytest.approx(1.3458716250016904, abs=1e-12)

    def test_regime_sharpes(self):
        rs = _summary(H25_DIR)["metrics"]["regime_sharpes"]
        assert rs["bull"] == pytest.approx(1.2324310438027033, abs=1e-12)
        assert rs["sideways"] == pytest.approx(1.1880923542184698, abs=1e-12)
        assert rs["bear"] == pytest.approx(2.143794177313109, abs=1e-12)

    def test_gates_all_pass(self):
        gates = _summary(H25_DIR)["passes"]
        assert gates == {
            "sharpe": True,
            "trades": True,
            "pf": True,
            "dd": True,
            "stab": True,
            "worst": True,
            "p": True,
            "ir": True,
            "perturbation": True,
        }

    def test_computation_budget_respected(self):
        s = _summary(H25_DIR)
        assert s["compute_cpu_hours"] <= 2.0
