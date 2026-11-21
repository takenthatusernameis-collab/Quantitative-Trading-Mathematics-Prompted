"""Schema guard for experiment artifacts under ``.experiments/nf_runs/``.

Forward-looking guard implementing the immediate recommendation in
``EXPERIMENT_ARTIFACT_AUDIT.md`` ("Add a schema validation test to CI to
prevent future inconsistency"):

* every committed ``summary.json`` must be parseable JSON decoding to an
  object (catches corruption / truncated writes);
* the ``verdict`` key is the corpus's dominant shared key and must remain
  near-universal (>= 90%), so new runners that omit it are caught.

Historical pre-contract artifacts are documented rather than failed so the
guard does not regress the suite: 8 directories have no ``summary.json`` at
all (incomplete runs), and a handful of summaries lack a canonical
``verdict`` value (see ``EXPERIMENT_ARTIFACT_AUDIT.md``). These are locked
in by ``test_incomplete_runs_match_audit_inventory``.

Read-only: does not modify ``src/qtr``, frozen-contract tests, or artifacts.
"""

import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
NF_RUNS = ROOT / ".experiments" / "nf_runs"


def _summary_paths():
    return sorted(p for p in NF_RUNS.glob("*/summary.json") if p.is_file())


SUMMARY_PATHS = _summary_paths()

# Inventory of directories with no summary.json, per
# EXPERIMENT_ARTIFACT_AUDIT.md (incomplete / early-terminated runs).
EXPECTED_INCOMPLETE = frozenset(
    {
        "nf_20261109_15_tax_loss_harvesting_20261110_025201",
        "nf_20261109_24_equity_risk_premium_20261109_223319",
        "nf_20261109_24_equity_risk_premium_20261109_223333",
        "nf_20261109_24_equity_risk_premium_20261109_223703",
        "nf_20261109_24_equity_risk_premium_20261109_223731",
        "nf_20261109_26_etf_nav_arbitrage_20261109_234200",
        "nf_20261110_01_treasury_auction_20261110_045905",
        "nf_20261110_01_treasury_auction_20261110_045929",
    }
)


@pytest.mark.parametrize("path", SUMMARY_PATHS, ids=[p.parent.name for p in SUMMARY_PATHS])
def test_summary_json_is_valid_json_object(path):
    """Every summary.json must be parseable JSON and decode to an object."""
    with open(path) as f:
        data = json.load(f)
    assert isinstance(data, dict), f"{path.parent.name}: summary.json is not a JSON object"


def test_verdict_key_is_near_universal():
    """``verdict`` is the corpus's dominant shared key.

    Requires >= 90% coverage: new runners that omit ``verdict`` are caught
    without failing on the pre-contract historical summaries that lack it.
    """
    total = len(SUMMARY_PATHS)
    assert total > 0, "no summary.json files found under .experiments/nf_runs"
    with_verdict = 0
    for path in SUMMARY_PATHS:
        with open(path) as f:
            data = json.load(f)
        if "verdict" in data:
            with_verdict += 1
    assert with_verdict / total >= 0.90, (
        f"verdict key in {with_verdict}/{total} ({100 * with_verdict / total:.1f}%) < 90%"
    )


def test_incomplete_runs_match_audit_inventory():
    """The set of directories without summary.json matches the audit inventory.

    Locks in the EXPERIMENT_ARTIFACT_AUDIT.md finding so any new incomplete
    run (or recovery of one of these) is surfaced as a deliberate test
    change rather than a silent regression.
    """
    actual = frozenset(
        d.name for d in NF_RUNS.iterdir() if d.is_dir() and not (d / "summary.json").is_file()
    )
    assert actual == EXPECTED_INCOMPLETE, (
        f"incomplete-run set changed: {sorted(actual)} vs expected {sorted(EXPECTED_INCOMPLETE)}"
    )


# Summary statistics pinned from EXPERIMENT_ARTIFACT_AUDIT.md (re-verified
# 2026-11-18 by recomputing from the corpus). The audit doc previously stated
# 87 distinct keys / 6 keys >=50% / 1 key >=80% / 19 cache-only directories;
# the corpus actually has 131 / 9 / 3 / 11 as of Cycle 115. These pins make
# the summary recomputable so a future audit cannot silently drift from the
# artifacts. The Cycle 115 H182 run (5 new summaries) added
# `information_ratio_vs_equal_weight` (1 distinct key) and pushed
# `oos_val_test` over the 50% threshold while `selected_params` fell below it.
# Cycle 213 added one summary (+1 directory): the full-window H183 crypto
# funding-carry re-run `nf_20261114_02_crypto_funding_carry_20261118_194621`
# (the earlier truncated `…_20261118_163437` artifact is preserved). Key
# statistics are unchanged: 134 distinct keys, the same >=50% / >=80% sets.
# Cycle 215 added one summary (+1 directory): the H184 commodity
# term-structure-carry run
# `nf_20261114_01_commodity_termstructure_carry_20261119_cycle215`. It adds
# five keys (+5 distinct): `benchmark_comparison`,
# `benchmark_passive_front_month_long_oos`, `benchmark_pvalue_two_sided`,
# `full_sample` and `information_ratio_vs_passive_front_month`. Each appears
# in one of 104 summaries, so the >=50% / >=80% sets are unchanged.
# Cycle 219 added one summary (+1 directory): the H186 commodity commercial
# hedging-pressure run
# `nf_20261119_02_commodity_hedging_pressure_20261119_093333`. It adds three
# top-level keys (distinct keys 143 -> 146):
# `benchmark_passive_equal_weight_long_oos`,
# `information_ratio_vs_passive_book` and
# `train_input_collinearity_hp_vs_change`. Each appears in one of 105
# summaries, so the >=50% / >=80% sets are unchanged.
# Cycle 230 added one summary (+1 directory): the H187 equity accounting
# accruals run
# `nf_20261120_01_equity_accruals_20261120_062010`. It adds one top-level
# key (distinct keys 146 -> 147): `train_input_collinearity_accruals_vs_asset_growth`
# (the other keys `benchmark_passive_equal_weight_long_oos` and
# `information_ratio_vs_passive_book` were already introduced by H186).
# Each appears in one of 106 summaries, so the >=50% / >=80% sets are unchanged.
# Cycle 232 added one summary (+1 directory): the H188 equity net share
# issuance run
# `nf_20261120_02_net_share_issuance_20261120_075812`. It adds two top-level
# keys (distinct keys 147 -> 149): `train_input_collinearity_net_issuance_vs_buyback`
# and `train_input_collinearity_vs_h187`. Each appears in one of 107 summaries,
# so the >=50% / >=80% sets are unchanged.
# Cycle 235 added one summary (+1 directory): the H190 crypto perpetual funding/basis
# cross-section run `nf_20261120_04_crypto_funding_carry_20261120_101548`. It adds one
# top-level key (distinct keys 149 -> 150): `train_input_collinearity`, a nested dict
# holding the three pairwise feature-collinearity diagnostics
# `funding_annualized_vs_basis_annualized`,
# `funding_annualized_vs_carry_combined` and
# `basis_annualized_vs_carry_combined` (nested, so they do not add to the top-level
# distinct-key count). Each appears in one of 108 summaries, so the >=50% / >=80% sets
# are unchanged. (H-ID note: this runner is H190, not H189 — H189 is reserved by the
# data-blocked gross-profitability candidate NF-20261120-03.)
# Cycle 245 added one summary (+1 directory): the H191 equity value /
# book-to-price & cash-flow-yield cross-section run
# `nf_20261121_01_equity_value_20261121_144056`. It adds one top-level key
# (distinct keys 150 -> 151): `train_input_collinearity_bp_vs_cfy`, the
# book-to-price vs cash-flow-yield Spearman diagnostic (the sibling H187/H188
# runners use distinct collinearity-key names, so each adds its own key). The key
# appears in one of 109 summaries, so the >=50% / >=80% sets are unchanged.
# Cycle 246 added one summary (+1 directory): the H192 innovation-intensity
# (R&D / revenue, R&D / assets) cross-section run
# `nf_20261121_02_innovation_intensity_20261121_174135`. It adds one top-level
# key (distinct keys 151 -> 152): `train_input_collinearity_rd_intensity_vs_rd_to_assets`,
# the R&D/revenue vs R&D/assets Spearman diagnostic (a sibling-collinearity key
# name distinct from H187/H188/H190/H191, so it adds its own key). The key
# appears in one of 110 summaries, so the >=50% / >=80% sets are unchanged.
# Cycle 247 added one summary (+1 directory): the H193 betting-against-beta
# cross-section run `nf_20261121_03_bab_beta_20261121_184109`. It adds one
# top-level key (distinct keys 152 -> 153):
# `train_input_collinearity_beta126_vs_beta252`, the 6-month vs 12-month beta
# Spearman diagnostic (a sibling-collinearity key name distinct from
# H187/H188/H190/H191/H192, so it adds its own key). The key appears in one of
# 111 summaries, so the >=50% / >=80% sets are unchanged.
EXPECTED_TOTAL_DIRS = 119
EXPECTED_SUMMARY_COUNT = 111
EXPECTED_CACHE_ONLY_DIRS = 11
EXPECTED_DISTINCT_KEYS = 153
EXPECTED_KEYS_GE_50_PCT = frozenset(
    {
        "ablations",
        "data",
        "experiment",
        "gates",
        "gates_passed",
        "hypothesis",
        "nf_id",
        "oos_val_test",
        "verdict",
    }
)
EXPECTED_KEYS_GE_80_PCT = frozenset({"data", "gates", "verdict"})


def _key_counts():
    """Return (per-key frequency, number of summaries) over the corpus."""
    counts: dict[str, int] = {}
    total = 0
    for path in SUMMARY_PATHS:
        total += 1
        with open(path) as f:
            data = json.load(f)
        for key in data:
            counts[key] = counts.get(key, 0) + 1
    return counts, total


def test_summary_statistics_match_audit_inventory():
    """Distinct-key and frequency statistics match the pinned audit summary."""
    counts, total = _key_counts()
    assert total == EXPECTED_SUMMARY_COUNT
    assert len(counts) == EXPECTED_DISTINCT_KEYS, (
        f"distinct keys changed: {len(counts)} vs expected {EXPECTED_DISTINCT_KEYS}"
    )
    ge_50 = frozenset(key for key, count in counts.items() if count >= 0.5 * total)
    ge_80 = frozenset(key for key, count in counts.items() if count >= 0.8 * total)
    assert ge_50 == EXPECTED_KEYS_GE_50_PCT, (
        f"keys >=50% changed: {sorted(ge_50)} vs expected {sorted(EXPECTED_KEYS_GE_50_PCT)}"
    )
    assert ge_80 == EXPECTED_KEYS_GE_80_PCT, (
        f"keys >=80% changed: {sorted(ge_80)} vs expected {sorted(EXPECTED_KEYS_GE_80_PCT)}"
    )


def test_cache_only_directory_inventory_matches_audit():
    """The number of cache-only subdirectories matches the audit inventory."""
    cache_dirs = [
        os.path.join(root, name)
        for root, dirnames, _ in os.walk(NF_RUNS)
        for name in dirnames
        if "cache" in name.lower()
    ]
    assert len(cache_dirs) == EXPECTED_CACHE_ONLY_DIRS, (
        f"cache-only directory count changed: {len(cache_dirs)} vs "
        f"expected {EXPECTED_CACHE_ONLY_DIRS}"
    )


def test_total_directory_inventory_matches_audit():
    """The number of top-level artifact directories matches the audit inventory."""
    total_dirs = sum(1 for d in NF_RUNS.iterdir() if d.is_dir())
    assert total_dirs == EXPECTED_TOTAL_DIRS, (
        f"total artifact directories changed: {total_dirs} vs expected {EXPECTED_TOTAL_DIRS}"
    )
