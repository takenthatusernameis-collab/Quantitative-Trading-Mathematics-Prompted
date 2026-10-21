# HANDOFF_CURRENT_SESSION — H46: the runners' import surface is declared, classified and pinned

## What changed

- `tests/test_runner_import_contract.py` — **strengthened**. The runner import contract now
  enforces every class strictly:
  - every `run_*.py` (32 runners) is importable without executing `main()`;
  - library imports (`qtr.*`) must resolve to names declared in `qtr.__all__` / the relevant
    subpackage's `__all__` — a runner cannot reach a symbol through an undeclared path;
  - third-party imports must be declared in `pyproject.toml` (`[project.dependencies]` or an
    optional extra under `[project.optional-dependencies]`), parsed via `tomllib`;
  - local imports are only other `run_*.py` modules in the repository.
  - Removed the loose regex-based dependency extraction and the hardcoded `common_deps`
    fallback that previously let undeclared packages pass.
- `NEXT_TASK.md` — H46 marked complete, runner count corrected (32, not 40), no further task
  assigned.

## What was actually verified

- `python -m pytest -q -W error tests/test_runner_import_contract.py` → **65 passed**
  (32 importability + 32 classification + 1 inventory).
- `python -m pytest -q -W error` → **1328 passed, 1 skipped**; `src/qtr` =
  **1038 statements, 316 branches, 0 missed, 0 partial, 100.00%**.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **89 files already formatted**.

## What remains unresolved

- The committed `src/qtr.egg-info/` manifest is stale; regenerating it would degrade its
  `PKG-INFO`, so it was left untouched (pre-existing, cosmetic).
- H9's sample-convention Sharpe disclosure, and the exhausted H1–H30 hypothesis space, stand.
- No next task is assigned.

## Precise next task

None assigned: H45 (public API contract) and H46 (runners' import contract) are complete,
the H1–H30 hypothesis space is exhausted, and all gate-defect classes are closed by
executable invariants.
