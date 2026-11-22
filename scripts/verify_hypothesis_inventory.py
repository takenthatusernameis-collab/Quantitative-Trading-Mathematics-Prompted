#!/usr/bin/env python3
"""Reconcile the recorded hypothesis high-water mark against the documented record.

The research notes in this repository (``AGENTS.md``, ``NEXT_TASK.md``,
``NEW_FAMILY_RESEARCH_REGISTER.md``) carry prose "exhausted/rejected" high-water
marks and "never executed" claims.  Those prose claims have repeatedly drifted from
the committed record and cost whole cycles to detect and correct:

* Cycle 251 asserted NF-01 (VIX term structure) and NF-02 (cross-asset lead-lag) were
  "proposed, never executed"; both are in fact executed and rejected (H86, H85).  The
  error was only caught in Cycle 252.
* ``AGENTS.md`` stated the executed record was "H1-H196 exhausted/rejected" while
  H197 was already executed and committed (Cycle 253).

This script encodes the single high-value, machine-checkable invariant that catches
that class of drift:

    the executed high-water mark recorded in ``AGENTS.md`` -- an HTML comment of the
    form ``<!-- inventory-high-water-mark: H<N> -->`` -- must equal the highest
    ``H<ID>`` documented as a section heading (``## H<ID>``) in ``HYPOTHESIS_SPEC.md``.

The marker is the authoritative, unambiguous claim; the spec headings are the
ground-truth executed record.  When a new hypothesis is executed, the author bumps the
marker and the spec together; if either is forgotten this script (and
``tests/test_verify_hypothesis_inventory.py``) fails, forcing reconciliation instead of
letting a stale "exhausted" claim propagate into the next cycle's planning.

The script is read-only, standard-library only, and offline.  It never writes to the
working tree and never touches ``src/qtr``, experiment artifacts, gates, thresholds, or
frozen numbers.

Exit codes:
    0  the recorded high-water mark equals the documented maximum;
    1  the mark is missing, malformed, or disagrees with the documented maximum;
    2  a required input file (``AGENTS.md`` / ``HYPOTHESIS_SPEC.md``) is missing.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS_RELPATH = Path("AGENTS.md")
SPEC_RELPATH = Path("HYPOTHESIS_SPEC.md")

# ``## H12: ...`` / ``## H197 (NF-...) ...`` -- the heading number is the documented ID.
_SPEC_HEADING = re.compile(r"^##\s+H(\d+)\b", re.MULTILINE)
# The authoritative recorded marker: ``<!-- inventory-high-water-mark: H197 -->``.
_MARKER = re.compile(r"<!--\s*inventory-high-water-mark:\s*H(\d+)\s*-->")


@dataclass(frozen=True)
class Reconciliation:
    """The outcome of comparing the recorded marker to the documented record."""

    documented_count: int
    max_documented: int | None
    recorded: int | None

    @property
    def match(self) -> bool:
        return self.recorded is not None and self.recorded == self.max_documented


def documented_h_ids(spec_text: str) -> set[int]:
    """Every ``H<ID>`` that has a ``## H<ID>`` section heading in the spec."""
    return {int(match) for match in _SPEC_HEADING.findall(spec_text)}


def max_documented_h_id(spec_text: str) -> int | None:
    """The highest documented ``H<ID>``, or ``None`` when the spec has no headings."""
    ids = documented_h_ids(spec_text)
    return max(ids) if ids else None


def recorded_high_water_mark(agents_text: str) -> int | None:
    """The ``H<ID>`` recorded in the AGENTS.md marker, or ``None`` if absent.

    If the marker is accidentally duplicated, the highest value is returned so a
    stray copy cannot silently lower the recorded mark.
    """
    values = [int(match) for match in _MARKER.findall(agents_text)]
    return max(values) if values else None


def reconcile(spec_text: str, agents_text: str) -> Reconciliation:
    """Compare the documented maximum against the recorded AGENTS.md marker."""
    ids = documented_h_ids(spec_text)
    return Reconciliation(
        documented_count=len(ids),
        max_documented=max(ids) if ids else None,
        recorded=recorded_high_water_mark(agents_text),
    )


def format_report(result: Reconciliation) -> list[str]:
    """Human-readable report lines for ``result``."""
    lines = [
        f"documented H-IDs: {result.documented_count}",
        f"max documented H-ID (HYPOTHESIS_SPEC.md): {result.max_documented}",
        f"recorded high-water mark (AGENTS.md): {result.recorded}",
    ]
    if result.recorded is None:
        lines.append(
            "OUT OF SYNC: AGENTS.md has no '<!-- inventory-high-water-mark: H<N> -->' marker."
        )
    elif result.max_documented is None:
        lines.append("OUT OF SYNC: HYPOTHESIS_SPEC.md has no '## H<N>' section headings.")
    elif result.match:
        lines.append(
            f"IN SYNC: recorded high-water mark H{result.recorded} equals the documented maximum."
        )
    else:
        lines.append(
            f"OUT OF SYNC: recorded H{result.recorded} != documented maximum H{result.max_documented}."
        )
    return lines


def verify(repo_root: Path | str) -> tuple[int, list[str]]:
    """Return ``(exit_code, report_lines)`` for the tree rooted at ``repo_root``."""
    repo_root = Path(repo_root).resolve()
    agents_path = repo_root / AGENTS_RELPATH
    spec_path = repo_root / SPEC_RELPATH

    missing = [str(path) for path in (agents_path, spec_path) if not path.is_file()]
    if missing:
        return 2, [f"MISSING: {path}" for path in missing]

    result = reconcile(spec_path.read_text(), agents_path.read_text())
    return (0 if result.match else 1), format_report(result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=ROOT,
        help=f"repository root holding AGENTS.md and HYPOTHESIS_SPEC.md (default: {ROOT})",
    )
    args = parser.parse_args(argv)
    exit_code, report = verify(args.repo_root)
    print("\n".join(report))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
