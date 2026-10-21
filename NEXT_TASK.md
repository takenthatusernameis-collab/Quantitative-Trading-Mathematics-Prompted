# Next Task

## State

H35–H44 complete (the coverage gate is measured, declared and complete at 100% statement +
branch). **H45 is complete**: the package's public API is declared, complete, and pinned by a
non-vacuous executable contract.

## Precise next task

**Extend the executable contract from the package's import surface to the runners' import
surface.**

The `run_*.py` scripts are the repository's other public entry points — they are what the
record calls "the runners" — but no test pins *which* modules they import, whether those
imports are the canonical ones, or whether a runner can still be imported at all. A runner
broken by an import-level change (a renamed symbol, a moved module, a subpackage that no
longer re-exports what a runner expects) currently fails at **run** time, not at **test** time.

### Scope

1. Inventory the import statements of every `run_*.py` in the repository (there are 40).
2. Classify each import as one of:
   - a **library** import (`qtr.*`) — must resolve to a name the package actually exports
     (`qtr.__all__` / the relevant subpackage's `__all__`), so a runner cannot reach a symbol
     through a path the public API does not declare;
   - a **stdlib** import;
   - a **third-party** import — must be a declared dependency in `pyproject.toml` (or an
     optional extra), so a runner cannot depend on an undeclared package;
   - a **local** import — an import of another `run_*.py` in the repository.
3. Pin each class with an executable test (a new `tests/test_runner_import_contract.py`), so a
   runner that imports an undeclared package, or reaches a symbol the public API does not
   declare, fails at test time.
4. Verify every runner is **importable** (module-level code only — no `main()` execution, no
   network, no grid re-run). A runner that cannot be imported at all is currently invisible
   to the test suite.

### Constraints

- No published artifact, gate threshold, verdict or certified number may be modified.
- No grid may be re-run; the H1–H30 hypothesis space remains exhausted.
- No runner's *behaviour* may change. This is an inspection + pinning task, not a refactor.
- Do **not** re-run the runners' `main()`: import them, do not execute them.
- Re-run `tests/test_runner_causality_inventory.py` and `tests/test_runner_metric_agreement.py`
  after any change in a runner.

## Constraints carried forward

- The certified families (H10, H22, H25) are unchanged and frozen.
- Every recomputed number in `FINAL_REPORT.md` is a **disclosure**, not a rewrite.
- The package's public API (§H45) is now pinned by `tests/test_public_api_contract.py`; re-run
  it after any change under `src/qtr`.
- The coverage gate (`python -m pytest -q --cov=qtr --cov-branch`) must stay at 100% for
  `src/qtr`; the lint gate (`python -m ruff check src tests run_*.py` and
  `python -m ruff format --check src tests run_*.py`) must stay clean.
