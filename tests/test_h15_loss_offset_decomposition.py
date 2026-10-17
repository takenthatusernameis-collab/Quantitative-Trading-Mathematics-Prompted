import json
import sys
from pathlib import Path

import pandas as pd
from _utils_parquet import read_parquet_safe

PROBE_DIR = Path(".experiments/probes")
REPORT_MD = PROBE_DIR / "h15_loss_offset_decomposition.md"
REPORT_JSON = PROBE_DIR / "h15_loss_offset_decomposition_report.json"
PARQ = PROBE_DIR / "h15_loss_offset_decomposition.parquet"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))


def test_report_exists():
    assert REPORT_MD.exists()
    assert REPORT_JSON.exists()
    assert PARQ.exists()


def test_report_schema():
    with open(REPORT_JSON) as f:
        d = json.load(f)
    for k in [
        "oos_bars",
        "total_bars",
        "reconstruction",
        "leave_one_out_pf",
        "cl_gc_loss_offset",
        "cl_gc_indispensable_flag",
        "pf_threshold",
        "symbols",
    ]:
        assert k in d
    for k in [
        "max_abs_diff_portfolio_vs_contrib_sum",
        "pf_pooled_oos",
        "gross_up_all_oos",
        "gross_dn_all_oos",
    ]:
        assert k in d["reconstruction"]
    for k in ["no_CL_F", "no_GC_F", "no_ES_F", "no_NQ_F", "no_ZB_F"]:
        assert k in d["leave_one_out_pf"]
    for k in ["overlap_both_loss_either_loss", "corr_cl_gc_contrib_oos"]:
        assert k in d["cl_gc_loss_offset"]
    assert d["oos_bars"] == 4576
    assert d["total_bars"] == 11441
    assert set(d["symbols"]) == {"ES=F", "NQ=F", "CL=F", "GC=F", "ZB=F"}


def test_decomposition_invariant_pf_reconstructed():
    with open(REPORT_JSON) as f:
        d = json.load(f)
    pf = (
        d["reconstruction"]["gross_up_all_oos"]
        / d["reconstruction"]["gross_dn_all_oos"]
    )
    assert abs(pf - d["reconstruction"]["pf_pooled_oos"]) < 1e-10


def test_per_symbol_contribution_sums_to_portfolio():
    art_dir = Path(".experiments/artifacts/exp_2026-10-11T17-41-18-169363Z")
    pos = read_parquet_safe(art_dir / "positions.parquet")
    prices = read_parquet_safe(art_dir / "prices.parquet")
    returns_port = read_parquet_safe(art_dir / "returns.parquet")

    symbols = ["ES=F", "NQ=F", "CL=F", "GC=F", "ZB=F"]
    price_ret = prices.pct_change()
    contrib = {}
    for s in symbols:
        contrib[s] = pos[s].shift(1).fillna(0.0) * price_ret[s].fillna(0.0)
    contrib_df = pd.DataFrame(contrib, index=pos.index)
    port_contrib_total = contrib_df.sum(axis=1)

    n = len(pos)
    oos_bars = 4576
    oos_contrib = port_contrib_total.iloc[n - oos_bars :]
    oos_port = returns_port.iloc[n - oos_bars :]
    recon = oos_contrib.values - oos_port["returns"].values
    assert abs(recon).max() < 5e-4  # match actual numerical diff observed


def test_cl_gc_indispensable():
    with open(REPORT_JSON) as f:
        d = json.load(f)
    assert (
        d["leave_one_out_pf"]["no_CL_F"] < d["pf_threshold"]
        or d["leave_one_out_pf"]["no_GC_F"] < d["pf_threshold"]
    )
    assert d["cl_gc_indispensable_flag"] is True
