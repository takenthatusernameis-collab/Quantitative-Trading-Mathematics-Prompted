#!/usr/bin/env python3
"""Verify that the maintainer workflow-contract patch still resolves the contract.

``.github/workflows/**`` is maintainer-managed in this repository: automation
cannot stage or push a workflow edit (the repository GitHub App token has no
``workflows`` permission and ``.github/scripts/kilo-controller.sh`` restores the
directory from ``origin/main`` after every session).  The fix therefore lives in
``patches/0001-gates-workflow-contract-fix.patch`` and is applied by a human.

Until it lands, ``tests/test_gates_workflow.py`` is red on ``origin/main`` by
design.  This script makes the pending action self-checking and deterministic:

* it never modifies the working tree -- the patch is applied to a throwaway
  copy of ``.github/workflows/gates.yml``;
* it mirrors every assertion pinned by ``tests/test_gates_workflow.py`` and
  reports the precise violations;
* it treats the already-fixed state as success, so it stays green after the
  maintainer applies the patch and the patch stops applying to a fixed file.

Exit codes: 0 when the live workflow satisfies the contract *or* the pending
patch upgrades it to one that does; 1 when the patch is stale or incomplete;
2 when a required input (``git``, the workflow, the patch) is missing.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_RELPATH = Path(".github") / "workflows" / "gates.yml"
DEFAULT_PATCH = Path("patches") / "0001-gates-workflow-contract-fix.patch"

RUFF_CHECK = "python -m ruff check src tests run_*.py scripts"
RUFF_FORMAT = "python -m ruff format --check src tests run_*.py scripts"
EDITABLE_INSTALL = "python -m pip install -e . --no-deps"
PERF_GATE = "python scripts/backtest_perf_regression_gate.py"


class PatchApplicationError(RuntimeError):
    """Raised when ``git apply`` rejects the patch against the given tree."""


def _triggers(workflow: Any) -> dict:
    """The workflow's ``on:`` mapping; empty for any other shape.

    PyYAML (YAML 1.1) parses the bare ``on:`` key as boolean ``True``, so the
    contract test reads both spellings; this helper does the same.
    """
    if not isinstance(workflow, dict):
        return {}
    triggers = workflow.get("on", workflow.get(True))
    return triggers if isinstance(triggers, dict) else {}


def _run_steps(workflow: Any, job: str) -> list[str]:
    """Every ``run:`` command in ``job``; empty for any malformed shape."""
    if not isinstance(workflow, dict):
        return []
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        return []
    spec = jobs.get(job)
    if not isinstance(spec, dict):
        return []
    steps = spec.get("steps")
    if not isinstance(steps, list):
        return []
    return [step["run"] for step in steps if isinstance(step, dict) and "run" in step]


def contract_violations(workflow: Any) -> list[str]:
    """Every ``tests/test_gates_workflow.py`` assertion the document fails.

    A malformed document (a non-mapping, a missing job, a scalar where a step
    list is expected) is reported as violations rather than raising, so a
    truncated or hand-mangled workflow yields actionable output.
    """
    violations: list[str] = []
    lint_steps = _run_steps(workflow, "lint")
    research_steps = _run_steps(workflow, "research_gates")

    for command in (RUFF_CHECK, RUFF_FORMAT):
        if command not in lint_steps:
            violations.append(f"lint job is missing ruff step: {command!r}")
    for job, steps in (("lint", lint_steps), ("research_gates", research_steps)):
        if EDITABLE_INSTALL not in steps:
            violations.append(f"{job} job is missing step: {EDITABLE_INSTALL!r}")
    if PERF_GATE not in research_steps:
        violations.append(f"research_gates job is missing step: {PERF_GATE!r}")

    triggers = _triggers(workflow)
    for event in ("push", "pull_request"):
        event_cfg = triggers.get(event)
        paths = event_cfg.get("paths") if isinstance(event_cfg, dict) else None
        if not isinstance(paths, list) or "scripts/**" not in paths:
            violations.append(f"{event!r} trigger paths are missing 'scripts/**'")
    return violations


def patched_workflow_text(workflow_path: Path | str, patch_path: Path | str) -> str:
    """Apply ``patch_path`` to a throwaway copy of ``workflow_path`` and return it.

    The repository's real workflow is never touched.  ``git apply`` is used
    (rather than a hand-rolled unified-diff parser) because it is the same tool
    the maintainer runs, so "this function passed" means "``git apply`` accepts
    the patch against the committed file".
    """
    workflow_path = Path(workflow_path)
    patch_path = Path(patch_path)
    original = workflow_path.read_text()

    with tempfile.TemporaryDirectory(prefix="qtr-wf-patch-") as tmp:
        tree = Path(tmp)
        target = tree / WORKFLOW_RELPATH
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(original)

        result = subprocess.run(
            ["git", "apply", "-p1", str(patch_path)],
            cwd=tree,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip() or "no diagnostics"
            raise PatchApplicationError(f"git apply rejected {patch_path.name}: {detail}")
        return target.read_text()


def verify(repo_root: Path | str) -> tuple[int, list[str]]:
    """Return ``(exit_code, report_lines)`` for the tree rooted at ``repo_root``."""
    repo_root = Path(repo_root)
    workflow_path = repo_root / WORKFLOW_RELPATH
    patch_path = repo_root / DEFAULT_PATCH

    if not workflow_path.is_file():
        return 2, [f"MISSING: {workflow_path}"]
    if not patch_path.is_file():
        return 2, [f"MISSING: {patch_path}"]

    live_violations = contract_violations(yaml.safe_load(workflow_path.read_text()))
    if not live_violations:
        return 0, [
            "CONTRACT SATISFIED: the live gates.yml already satisfies "
            "tests/test_gates_workflow.py; the maintainer patch is not required."
        ]

    report = [
        f"live gates.yml fails {len(live_violations)} contract assertion(s):",
        *(f"  - {violation}" for violation in live_violations),
    ]
    try:
        patched_text = patched_workflow_text(workflow_path, patch_path)
    except FileNotFoundError as exc:
        report.append(f"MISSING TOOL: {exc}")
        return 2, report
    except (OSError, PatchApplicationError) as exc:
        report.append(f"PATCH VERIFICATION FAILED: {exc}")
        return 1, report

    patched_violations = contract_violations(yaml.safe_load(patched_text))
    if patched_violations:
        report.append(
            f"PATCH VERIFICATION FAILED: patched gates.yml still fails "
            f"{len(patched_violations)} contract assertion(s):"
        )
        report.extend(f"  - {violation}" for violation in patched_violations)
        return 1, report

    report.append(
        f"PATCH VERIFIED: {patch_path.name} applies to the live gates.yml and "
        f"resolves all {len(live_violations)} violation(s); a maintainer must land "
        "it with workflows-scoped credentials."
    )
    return 0, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=ROOT,
        help=f"repository root holding .github/workflows/gates.yml and patches/ (default: {ROOT})",
    )
    args = parser.parse_args(argv)
    exit_code, report = verify(args.repo_root)
    print("\n".join(report))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
