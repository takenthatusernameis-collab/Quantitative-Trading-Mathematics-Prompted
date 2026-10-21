# HANDOFF_NEXT — H46: the runners' import surface is declared, classified and pinned

## What changed (this session)

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
- `FINAL_REPORT.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md` updated.

## The defect this closed

Before H46, `tests/test_runner_import_contract.py` existed but was vacuous in the same way the
pre-H45 `from qtr import *; print('ok')` check was:

- `from qtr import X` checked `hasattr(qtr, X)` with `pass` — no assertion that `X` is in
  `qtr.__all__`, so a runner could import a name the public API does not declare and the test
  would still pass.
- `from qtr.subpackage import X` only checked the submodule is importable, not that `X` is in
  the subpackage's `__all__`.
- Third-party imports used a loose regex over ALL quoted strings in `pyproject.toml` (matching
  build-system, tool config, etc.) plus a hardcoded `common_deps` fallback that let undeclared
  packages pass.

## The contract

`tests/test_runner_import_contract.py` pins the runners' import surface in four layers:

1. **Importability** (32) — every `run_*.py` is importable via `spec_from_file_location`
   without executing `main()`, so a broken runner is caught at test time.
2. **Library imports** — `from qtr import X` requires `X in qtr.__all__`; `from qtr.subpackage
   import X` requires `X in qtr.subpackage.__all__`; bare `import qtr` / `import qtr.subpackage`
   requires the module to resolve.
3. **Third-party imports** — must be declared in `pyproject.toml` `[project.dependencies]` or an
   optional extra, parsed via `tomllib` (not a loose regex).
4. **Local imports** — must be another `run_*.py` module in the repository.

## What was actually verified

- `python -m pytest -q -W error tests/test_runner_import_contract.py` → **65 passed**.
- `python -m pytest -q -W error` → **1328 passed, 1 skipped**; `src/qtr` =
  **1038 statements, 316 branches, 0 missed, 0 partial, 100.00%**.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **89 files already formatted**.

## What remains unresolved (disclosures, not rewrites)

- The **committed** `src/qtr.egg-info/` manifest is stale. Regenerating it with setuptools 68.1.2
  would *degrade* the committed `PKG-INFO`; left untouched (pre-existing, cosmetic).
- H9's published OOS Sharpe is on the sample convention (gap 1.026e-04); disclosed and pinned.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified
  families' numbers and verdicts are frozen.

## Approaches already tried / failed (and why)

- **Regenerating `src/qtr.egg-info/` with the local setuptools** — rejected as a regression to
  the committed metadata; the stale manifest is cosmetic (the build regenerates it).

## Precise next task

None assigned: H45 (public API contract) and H46 (runners' import contract) are complete,
the H1–H30 hypothesis space is exhausted, and all gate-defect classes are closed by executable
invariants.

## State a next session inherits

- The pre-registered free-data hypothesis space (H1–H30) remains **exhausted**; no new
  hypothesis is warranted and no grid may be re-run.
- Every published artifact, threshold, verdict and certified number is frozen.
- The shared library, the engine **and every `run_*.py`** remain pinned as **point-in-time**;
  re-run `tests/test_causality_invariant.py` after any change under `src/qtr`,
  `tests/test_runner_causality_inventory.py` after any change in a runner,
  `tests/test_public_api_contract.py` after any change under `src/qtr`, and
  `tests/test_runner_import_contract.py` after any change in a runner or under `src/qtr`.
