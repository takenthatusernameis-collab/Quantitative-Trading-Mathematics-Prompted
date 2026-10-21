# HANDOFF — H46 complete (session handoff)

## What changed

**H46:** the runners' import surface is declared, classified and non-vacuously pinned.

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
- `NEXT_TASK.md` — H46 marked complete; runner count corrected (32, not 40); no next task
  assigned.
- `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`, `HANDOFF_NEXT.md` updated.

## What was actually verified

- `python -m pytest -q -W error tests/test_runner_import_contract.py` → **65 passed**
  (32 importability + 32 classification + 1 inventory).
- `python -m pytest -q -W error` → **1328 passed, 1 skipped**; `src/qtr` =
  **1038 statements, 316 branches, 0 missed, 0 partial, 100.00%**; the committed gate reports
  *"Required test coverage of 100.0% reached. Total coverage: 100.00%"*.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **89 files already formatted**.

## What remains unresolved

- The **committed** `src/qtr.egg-info/` manifest is stale (it predates eight test modules added
  since H33). Regenerating it with the setuptools available here (68.1.2) would *degrade* the
  committed `PKG-INFO` (`Metadata-Version: 2.1`, core `Requires-Dist` entries dropped), so it
  was left untouched. Pre-existing, cosmetic: the build regenerates it.
- H9's published OOS Sharpe is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict cannot move (REJECT on the profit factor, 55× margin over its 1.0 gate).
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified
  families' numbers and verdicts are frozen.

## Approaches already tried / failed (and why)

- **Regenerating `src/qtr.egg-info/` with the local setuptools** — rejected: setuptools 68.1.2
  writes `Metadata-Version: 2.1` and drops the core `Requires-Dist` entries, which is a
  *regression* in the committed metadata. The stale manifest is pre-existing and cosmetic; the
  build regenerates it.

## Precise next task

None assigned: H45 (public API contract) and H46 (runners' import contract) are complete,
the H1–H30 hypothesis space is exhausted, and all gate-defect classes are closed by executable
invariants.
