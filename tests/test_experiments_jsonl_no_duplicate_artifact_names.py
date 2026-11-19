"""Guard: no experiment records two ``artifacts`` entries with the same name.

The 2026-10-10 momentum runs (ts_momentum_20etf_v1, cs_momentum_10etf_v1,
regime_gated_momentum_20etf_v1) each record ``param_grid_results`` twice: once
with the hash of the file actually on disk and once with a stale hash from an
earlier grid run.  The duplicate entry is what the reproducibility audit's
``hash_mismatches`` backlog counts (11 rows, all ``param_grid_results`` /
``summary``), so the baseline cannot be lowered without first removing the
phantom rows from ``.experiments/experiments.jsonl``.

Read-only: does not modify ``src/qtr``, frozen-contract tests, or artifacts.
"""

import json
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EXPERIMENTS_JSONL = ROOT / ".experiments" / "experiments.jsonl"


def _load_experiments() -> list[dict]:
    experiments = []
    with open(EXPERIMENTS_JSONL) as f:
        for line in f:
            line = line.strip()
            if line:
                experiments.append(json.loads(line))
    return experiments


def test_no_duplicate_artifact_names_within_an_experiment():
    """No single experiment may publish two artifacts under the same name."""
    experiments = _load_experiments()
    offenders = []
    for exp in experiments:
        names = list(exp.get("artifacts", {}).keys())
        dupes = [name for name, count in Counter(names).items() if count > 1]
        if dupes:
            offenders.append(
                {
                    "experiment_id": exp["metadata"]["experiment_id"],
                    "name": exp["metadata"]["name"],
                    "duplicate_names": dupes,
                }
            )

    assert not offenders, (
        f"found {len(offenders)} experiment(s) with duplicate artifact names:\n"
        + "\n".join(
            f"  {o['experiment_id']} ({o['name']}): {o['duplicate_names']}"
            for o in offenders
        )
    )


def test_no_duplicate_artifact_names_across_same_run_family():
    """A run family must not publish the same artifact name to two paths.

    The 2026-10-10 momentum runs each record ``param_grid_results`` twice at
    the *same* path with different recorded hashes; the on-disk file matches
    only one of them.  This guard catches that pattern without depending on
    the specific hash values.
    """
    experiments = _load_experiments()
    by_name: dict[str, list[tuple[str, str, str]]] = {}
    for exp in experiments:
        eid = exp["metadata"]["experiment_id"]
        for name, path in exp.get("artifacts", {}).items():
            by_name.setdefault(name, []).append((eid, exp["metadata"]["name"], path))

    offenders = []
    for name, entries in by_name.items():
        paths = {p for _, _, p in entries}
        if len(entries) > 1 and len(paths) == 1:
            offenders.append(
                {
                    "artifact_name": name,
                    "path": next(iter(paths)),
                    "experiments": [e[0] for e in entries],
                }
            )

    assert not offenders, (
        f"found {len(offenders)} artifact name(s) published to one path by "
        f"multiple experiments:\n"
        + "\n".join(
            f"  {o['artifact_name']} -> {o['path']} from {o['experiments']}"
            for o in offenders
        )
    )