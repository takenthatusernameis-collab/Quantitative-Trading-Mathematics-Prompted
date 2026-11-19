"""Guard: no experiment record carries duplicate JSON keys / artifact names.

The 2026-10-10 momentum runs originally recorded ``param_grid_results`` twice in
one ``artifacts`` object: once with the hash of the file on disk and once with a
stale hash from an earlier grid run. That duplicate *key* pattern is gone from
the current corpus, but the reproducibility audit still counts 11
``hash_mismatches``: those are stale hash suffixes on records whose artifact file
was rewritten in place (8 momentum ``param_grid_results`` parquet rows and 3
``summary.json`` rows), not duplicate keys. See ``REPRODUCIBILITY_AUDIT_REPORT.md``.

Why the parse below is raw: ``json.loads`` keeps the last value for a repeated
key and silently drops the duplicate, so a guard built on the parsed dict can
never see the pattern it claims to protect. We therefore parse each line with an
``object_pairs_hook`` that records repeated keys at every nesting level.
``test_duplicate_key_detection_is_not_vacuous`` proves the detector fires on a
crafted record while ``json.loads`` collapses it.

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


def _duplicate_keys(raw: str) -> list[str]:
    """Return every JSON key repeated within one object of ``raw``.

    ``json.loads`` collapses duplicate keys, so the duplicate is only visible
    while the object pairs are still being decoded.
    """
    duplicates: list[str] = []

    def hook(pairs):
        counts = Counter(key for key, _ in pairs)
        duplicates.extend(key for key, count in counts.items() if count > 1)
        return dict(pairs)

    json.loads(raw, object_pairs_hook=hook)
    return duplicates


def test_no_duplicate_keys_within_an_experiment_record():
    """No experiment record may repeat a JSON key (artifact names included)."""
    offenders = []
    with open(EXPERIMENTS_JSONL) as f:
        for lineno, line in enumerate(f, start=1):
            if not line.strip():
                continue
            duplicates = _duplicate_keys(line)
            if duplicates:
                offenders.append({"line": lineno, "duplicate_keys": duplicates})

    assert not offenders, (
        f"found {len(offenders)} experiment record(s) with duplicate JSON keys:\n"
        + "\n".join(f"  line {o['line']}: {o['duplicate_keys']}" for o in offenders)
    )


def test_duplicate_key_detection_is_not_vacuous():
    """The detector must catch a duplicate that ``json.loads`` would hide."""
    raw = (
        '{"metadata": {"experiment_id": "x"}, '
        '"artifacts": {"param_grid_results_deadbeef": "p1", '
        '"param_grid_results_deadbeef": "p2"}}'
    )

    assert _duplicate_keys(raw) == ["param_grid_results_deadbeef"]
    assert list(json.loads(raw)["artifacts"]) == ["param_grid_results_deadbeef"]
    assert list(json.loads(raw)["artifacts"].values()) == ["p2"]


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
            f"  {o['artifact_name']} -> {o['path']} from {o['experiments']}" for o in offenders
        )
    )


@pytest.mark.parametrize("line_ending", ["\n", ""])
def test_detector_handles_trailing_newline(line_ending):
    """The detector is newline-agnostic so it can read raw lines from disk."""
    raw = '{"a": 1, "a": 2}' + line_ending
    assert _duplicate_keys(raw) == ["a"]
