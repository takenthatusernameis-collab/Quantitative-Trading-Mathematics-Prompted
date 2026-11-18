"""Tests for ``scripts/verify_gates_workflow_patch.py``.

The script is the executable ratchet for the maintainer-gated workflow fix: it
must (a) flag exactly the assertions ``tests/test_gates_workflow.py`` pins,
(b) apply the pending patch to a throwaway copy without touching the working
tree, (c) fail closed on a stale or incomplete patch, and (d) accept the
already-fixed state so it stays green after the maintainer lands the change.

The synthetic fixtures below exercise the state machine; the final test runs
the script against this repository so either "the live workflow is fixed" or
"the committed patch resolves it" is continuously proven.
"""

from __future__ import annotations

import difflib
import importlib.util
import shutil
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_gates_workflow_patch.py"
PATCH_RELPATH = Path("patches") / "0001-gates-workflow-contract-fix.patch"
WORKFLOW_RELPATH = Path(".github") / "workflows" / "gates.yml"

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None, reason="git apply is required to verify the patch"
)

PRE_FIX_YAML = """\
on:
  push:
    branches: [main]
    paths:
      - 'src/**'
      - 'tests/**'
      - 'run_*.py'
  pull_request:
    branches: [main]
    paths:
      - 'src/**'
      - 'tests/**'
      - 'run_*.py'
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - name: Install deps
        run: pip install -r requirements.txt
      - name: Ruff check
        run: python -m ruff check src tests run_*.py
      - name: Ruff format check
        run: python -m ruff format --check src tests run_*.py
  research_gates:
    runs-on: ubuntu-latest
    steps:
      - name: Install deps
        run: pip install -r requirements.txt
      - name: Run gates
        run: python -m pytest -q -W error --cov=qtr
"""

FIXED_YAML = """\
on:
  push:
    branches: [main]
    paths:
      - 'src/**'
      - 'tests/**'
      - 'run_*.py'
      - 'scripts/**'
  pull_request:
    branches: [main]
    paths:
      - 'src/**'
      - 'tests/**'
      - 'run_*.py'
      - 'scripts/**'
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - name: Install deps
        run: pip install -r requirements.txt
      - name: Install package editably
        run: python -m pip install -e . --no-deps
      - name: Ruff check
        run: python -m ruff check src tests run_*.py scripts
      - name: Ruff format check
        run: python -m ruff format --check src tests run_*.py scripts
  research_gates:
    runs-on: ubuntu-latest
    steps:
      - name: Install deps
        run: pip install -r requirements.txt
      - name: Install package editably
        run: python -m pip install -e . --no-deps
      - name: Backtest performance regression gate
        run: python scripts/backtest_perf_regression_gate.py
      - name: Run gates
        run: python -m pytest -q -W error --cov=qtr
"""

UNRELATED_YAML = """\
name: other
on:
  workflow_dispatch:
jobs:
  only_job:
    runs-on: ubuntu-latest
    steps:
      - run: echo hi
"""


def _load_script():
    spec = importlib.util.spec_from_file_location("verify_gates_workflow_patch", SCRIPT)
    assert spec is not None and spec.loader is not None, f"cannot load {SCRIPT}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _unified_patch(old: str, new: str) -> str:
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile="a/.github/workflows/gates.yml",
            tofile="b/.github/workflows/gates.yml",
        )
    )


def _write_repo(tmp_path: Path, workflow_text: str, patch_text: str) -> Path:
    workflow = tmp_path / WORKFLOW_RELPATH
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text(workflow_text)
    patch = tmp_path / PATCH_RELPATH
    patch.parent.mkdir(parents=True)
    patch.write_text(patch_text)
    return tmp_path


def test_pre_fix_workflow_fails_all_seven_assertions():
    module = _load_script()
    violations = module.contract_violations(yaml.safe_load(PRE_FIX_YAML))

    assert len(violations) == 7
    assert any("ruff check" in violation for violation in violations)
    assert any("ruff format" in violation for violation in violations)
    assert any("pip install -e . --no-deps" in violation for violation in violations)
    assert any("backtest_perf_regression_gate.py" in violation for violation in violations)
    assert sum("scripts/**" in violation for violation in violations) == 2


def test_fixed_workflow_has_no_violations():
    module = _load_script()
    assert module.contract_violations(yaml.safe_load(FIXED_YAML)) == []


@pytest.mark.parametrize("document", [None, "gates", {}, {"jobs": []}, {"on": None, "jobs": {}}])
def test_malformed_documents_are_reported_not_raised(document):
    module = _load_script()
    violations = module.contract_violations(document)
    assert len(violations) == 7


def test_patched_workflow_text_applies_diff_to_throwaway_copy(tmp_path):
    module = _load_script()
    _write_repo(tmp_path, PRE_FIX_YAML, _unified_patch(PRE_FIX_YAML, FIXED_YAML))
    workflow = tmp_path / WORKFLOW_RELPATH

    patched = module.patched_workflow_text(workflow, tmp_path / PATCH_RELPATH)

    assert yaml.safe_load(patched) == yaml.safe_load(FIXED_YAML)
    assert workflow.read_text() == PRE_FIX_YAML


def test_patched_workflow_text_rejects_stale_patch(tmp_path):
    module = _load_script()
    _write_repo(tmp_path, PRE_FIX_YAML, _unified_patch(UNRELATED_YAML, FIXED_YAML))

    with pytest.raises(module.PatchApplicationError):
        module.patched_workflow_text(tmp_path / WORKFLOW_RELPATH, tmp_path / PATCH_RELPATH)


def test_main_reports_contract_satisfied_for_fixed_live_workflow(tmp_path, capsys):
    module = _load_script()
    _write_repo(tmp_path, FIXED_YAML, "placeholder\n")

    assert module.main(["--repo-root", str(tmp_path)]) == 0
    assert "CONTRACT SATISFIED" in capsys.readouterr().out


def test_main_verifies_pending_patch(tmp_path, capsys):
    module = _load_script()
    _write_repo(tmp_path, PRE_FIX_YAML, _unified_patch(PRE_FIX_YAML, FIXED_YAML))

    assert module.main(["--repo-root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "PATCH VERIFIED" in out
    assert "resolves all 7 violation(s)" in out


def test_main_fails_on_stale_patch(tmp_path, capsys):
    module = _load_script()
    _write_repo(tmp_path, PRE_FIX_YAML, _unified_patch(UNRELATED_YAML, FIXED_YAML))

    assert module.main(["--repo-root", str(tmp_path)]) == 1
    assert "PATCH VERIFICATION FAILED" in capsys.readouterr().out


def test_main_fails_on_incomplete_patch(tmp_path, capsys):
    module = _load_script()
    partial = PRE_FIX_YAML.replace(
        "      - 'run_*.py'\n", "      - 'run_*.py'\n      - 'scripts/**'\n"
    )
    _write_repo(tmp_path, PRE_FIX_YAML, _unified_patch(PRE_FIX_YAML, partial))

    assert module.main(["--repo-root", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "still fails 5 contract assertion(s)" in out


def test_main_reports_missing_inputs(tmp_path, capsys):
    module = _load_script()
    assert module.main(["--repo-root", str(tmp_path)]) == 2
    assert "MISSING:" in capsys.readouterr().out


def test_live_repository_is_fixed_or_patch_resolves_it(capsys):
    module = _load_script()

    assert module.main(["--repo-root", str(ROOT)]) == 0
    out = capsys.readouterr().out
    assert "CONTRACT SATISFIED" in out or "PATCH VERIFIED" in out
