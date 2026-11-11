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
