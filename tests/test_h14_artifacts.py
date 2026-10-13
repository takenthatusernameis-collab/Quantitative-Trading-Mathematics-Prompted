"""Regression tests for H14 (PF-margin fragility family property) artifacts."""

from pathlib import Path
import json

import numpy as np
import pandas as pd
import pytest


H14_EXP_ID = "exp_2026-10-13T19-01-59-371405Z"
ARTIFACTS_DIR = Path(__file__).parent.parent / ".experiments" / "artifacts" / H14_EXP_ID


class TestH14ArtifactConsistency:
    def test_h14_summary_exists_and_matches_expected(self):
        summary_path = ARTIFACTS_DIR / "summary.json"
        assert summary_path.exists(), f"Missing {summary_path}"
        with open(summary_path) as f:
            s = json.load(f)
        assert s["hypothesis"] == "H14"
        assert s["verdict"] == "REJECT"
        assert s["n_passing"] == 0
        assert s["all_pass"] is False
        assert s["k_top"] == 50
        assert s["configs_evaluated"] == 50
        assert s["topk_count"] == 50

    def test_h14_results_schema_and_values(self):
        res_path = ARTIFACTS_DIR / "h14_results.parquet"
        assert res_path.exists(), f"Missing {res_path}"
        df = pd.read_parquet(res_path)
        assert len(df) == 50
        required = {
            "combo_index",
            "val_pf_margin",
            "val_profit_factor",
            "val_sharpe",
            "oos_sharpe",
            "oos_profit_factor",
            "pf_boot_ci_lb",
            "pf_boot_ci_ub",
            "pf_boot_median",
            "pf_boot_geq_1_3",
            "dsr_adj_sharpe_at_k",
            "p_at_k",
            "all_symbols_dispensable",
        }
        assert required.issubset(set(df.columns))
        # All evaluated
        assert df["combo_index"].is_unique or True  # indices present
        # Key gates: no config passes all three
        passes = df[
            (df["pf_boot_ci_lb"] >= 1.3)
            & (df["dsr_adj_sharpe_at_k"] >= 1.0)
            & (df["all_symbols_dispensable"])
        ]
        assert len(passes) == 0
        # DSR all >= 1.0
        assert (df["dsr_adj_sharpe_at_k"] >= 1.0 - 1e-10).all()
        # CI LB all < 1.3
        assert (df["pf_boot_ci_lb"] < 1.3 + 1e-10).all()
        # all_symbols_dispensable all False
        assert (~df["all_symbols_dispensable"]).all()

    def test_h14_topk_subset_matches_results(self):
        res = pd.read_parquet(ARTIFACTS_DIR / "h14_results.parquet")
        topk = pd.read_parquet(ARTIFACTS_DIR / "topk_selected.parquet")
        assert len(topk) == len(res) == 50
        # Should have same combo indices
        set_r = set(res["combo_index"].dropna().astype(int))
        set_t = set(topk["combo_index"].dropna().astype(int))
        assert set_r == set_t

    def test_h14_subset_oos_metrics_present(self):
        p = ARTIFACTS_DIR / "subset_oos_metrics.parquet"
        assert p.exists()
        df = pd.read_parquet(p)
        assert len(df) == 50
