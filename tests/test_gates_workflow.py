"""Contract tests for ``.github/workflows/gates.yml``.

The lint job must lint ``scripts/`` (otherwise a broken script under
``scripts/`` can pass CI) and the push/pull_request path filters must include
``scripts/**`` so edits there actually trigger the gates. This pins both, plus
the wiring of the backtest performance regression gate into the
``research_gates`` job.

The test only reads the committed workflow YAML; it never runs CI or the gate,
so it is deterministic on any host.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "gates.yml"


@pytest.fixture(scope="module")
def workflow() -> dict:
    """Return the parsed ``gates.yml`` document."""
    return yaml.safe_load(WORKFLOW.read_text())


def _triggers(workflow: dict) -> dict:
    # PyYAML (YAML 1.1) parses the bare ``on:`` key as boolean ``True``.
    return workflow.get("on", workflow.get(True))


def _run_steps(workflow: dict, job: str) -> list[str]:
    return [step["run"] for step in workflow["jobs"][job].get("steps", []) if "run" in step]


@pytest.mark.parametrize(
    "command",
    [
        "python -m ruff check src tests run_*.py scripts",
        "python -m ruff format --check src tests run_*.py scripts",
    ],
)
def test_lint_job_includes_scripts_in_ruff_targets(workflow, command):
    assert command in _run_steps(workflow, "lint")


@pytest.mark.parametrize("event", ["push", "pull_request"])
def test_path_triggers_include_scripts(workflow, event):
    assert "scripts/**" in _triggers(workflow)[event]["paths"]


def test_research_gates_job_runs_performance_regression_gate(workflow):
    assert "python scripts/backtest_perf_regression_gate.py" in _run_steps(
        workflow, "research_gates"
    )


@pytest.mark.parametrize("job", ["lint", "research_gates"])
def test_jobs_install_the_package_editably(workflow, job):
    assert "python -m pip install -e . --no-deps" in _run_steps(workflow, job)
