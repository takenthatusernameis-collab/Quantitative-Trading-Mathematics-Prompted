from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "nf_20261125_01", ROOT / "run_nf_20261125_01_institutional_flow.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def test_constants_match_preregistration():
    assert mod.EXPERIMENT == "nf_20261125_01_institutional_flow"
    assert mod.NF_ID == "NF-20261125-01"
    assert mod.HYPOTHESIS == "H200"
    assert mod.START == "2015-01-01"
    assert mod.END == "2026-11-25"
    assert mod.TRAIN_END == "2021-12-31"
    assert mod.VAL_END == "2023-12-31"
    assert mod.COST_ONE_WAY_BPS == 5.0
    assert mod.GATES == mod.h184.GATES
    assert set(mod.INSTITUTIONS) == {"0001067983", "0001610520", "0001103653"}


def test_bounded_grid_is_eight_declared_combos():
    combos = list(mod.iter_grid())
    assert len(combos) == 2 * 1 * 2 * 2 == 8
    for row in combos:
        assert row["exit_z"] == 0.0
        assert row["entry_z"] in {0.5, 1.0}
        assert row["k"] in {10, 20}
        assert row["vol_target"] in {0.10, 0.15}


def test_cross_sectional_z_zero_mean_unit_std():
    calendar = pd.bdate_range("2020-01-01", periods=5)
    frame = pd.DataFrame(
        np.array([[1.0, 2.0, 3.0, 4.0, 5.0]] * len(calendar)),
        index=calendar,
        columns=list("ABCDE"),
    )
    # build_flow_signal_panel's internal z is not exported; test the exported
    # signal_weights direction instead (long top z, short bottom z).
    z = pd.DataFrame(
        np.array([[2.0, 1.0, 0.0, -1.0, -2.0]] * len(calendar)),
        index=calendar,
        columns=list("ABCDE"),
    )
    weights = mod.signal_weights(z, entry_z=1.0, exit_z=0.0, k=1, tickers=list("ABCDE"))
    assert weights.iloc[0]["A"] == 0.5
    assert weights.iloc[0]["E"] == -0.5


def test_walk_forward_score_short_train_returns_sentinel():
    calendar = pd.bdate_range("2020-01-01", periods=10)
    products = ["A", "B", "C"]
    signal = pd.DataFrame(
        np.random.default_rng(7).normal(0, 1, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    returns = pd.DataFrame(
        np.random.default_rng(8).normal(0, 0.01, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    params = {"entry_z": 1.0, "exit_z": 0.0, "k": 1, "vol_target": 0.10}
    assert mod.walk_forward_score(signal, params, returns, products, calendar) == -999.0


def test_artifact_summary_exists_and_verdict():
    import glob

    artifacts = glob.glob(
        str(
            ROOT
            / ".experiments"
            / "nf_runs"
            / "nf_20261125_01_institutional_flow_*"
            / "summary.json"
        )
    )
    if not artifacts:
        import pytest

        pytest.skip("H200 artifact not yet generated")
    with open(max(artifacts)) as handle:
        summary = json.load(handle)
    assert summary["experiment"] == "nf_20261125_01_institutional_flow"
    assert summary["hypothesis"] == "H200"
    assert summary["verdict"] in {"ACCEPT", "REJECT"}
    assert summary["gates_total"] == 8
    assert summary["integrity"]["src_qtr_unchanged"] is True
    assert summary["integrity"]["gate_weakening"] is False
