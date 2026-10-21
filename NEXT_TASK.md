# Next Task

## State

H35–H44 complete (the coverage gate is measured, declared and complete at 100% statement +
branch). **H45 is complete**: the package's public API is declared, complete, and pinned by a
non-vacuous executable contract. **H46 is complete**: the runners' import surface is declared,
classified and pinned by `tests/test_runner_import_contract.py`.

## What changed (H46)

- `tests/test_runner_import_contract.py` — strengthened to enforce the full contract:
  - every `run_*.py` (32 runners) is importable without executing `main()`;
  - library imports (`qtr.*`) must resolve to names declared in `qtr.__all__` / the relevant
    subpackage's `__all__` — a runner cannot reach a symbol through an undeclared path;
  - third-party imports must be declared in `pyproject.toml` (`[project.dependencies]` or an
    optional extra under `[project.optional-dependencies]`), parsed via `tomllib`;
  - local imports are only other `run_*.py` modules in the repository.
- Removed the loose regex-based dependency extraction and the hardcoded `common_deps`
  fallback that previously let undeclared packages pass.

## What was actually verified

- `python -m pytest -q -W error tests/test_runner_import_contract.py` → **65 passed**
  (32 importability + 32 classification + 1 inventory).
- `python -m pytest -q -W error` → **1328 passed, 1 skipped** (full suite).
- `python -m ruff check src tests run_*.py` → **All checks passed!**.
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
- No next task is assigned: the H1–H30 hypothesis space is exhausted, all gate-defect classes
  are closed by executable invariants, and the import contract covers both the package surface
  (H45) and the runners' surface (H46).

## Approaches already tried / failed (and why)

- **Regenerating `src/qtr.egg-info/` with the local setuptools** — rejected as a regression to
  the committed metadata (see above).
- **An explicit top-level `__all__` list** — rejected in favour of composing it from the
  subpackages' `__all__`s, so the aggregate cannot drift from what it aggregates.

## Constraints carried forward

- No published artifact, gate threshold, verdict or certified number may be modified.
- No grid may be re-run; the H1–H30 hypothesis space remains exhausted.
- The package's public API (§H45) is pinned by `tests/test_public_api_contract.py`; re-run it
  after any change under `src/qtr`.
- The runners' import surface (§H46) is pinned by `tests/test_runner_import_contract.py`; re-run
  it after any change in a runner or under `src/qtr`.
- Re-run `tests/test_runner_causality_inventory.py` and `tests/test_runner_metric_agreement.py`
  after any change in a runner.
- The coverage gate (`python -m pytest -q --cov=qtr --cov-branch`) must stay at 100% for
  `src/qtr`; the lint gate (`python -m ruff check src tests run_*.py` and
  `python -m ruff format --check src tests run_*.py`) must stay clean.
