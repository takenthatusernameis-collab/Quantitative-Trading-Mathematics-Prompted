# HANDOFF_CURRENT — session complete (H46)

## State

- **H46 is COMPLETE** as recorded in `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_NEXT.md` and
  `HANDOFF_CURRENT_SESSION.md`: the runners' import surface is **declared**, **classified** and
  **pinned** by `tests/test_runner_import_contract.py` (65 tests: 32 importability + 32
  classification + 1 inventory). Every `run_*.py` (32 runners) is importable without executing
  `main()`; library imports must resolve to names declared in `qtr.__all__` / the relevant
  subpackage's `__all__`; third-party imports must be declared in `pyproject.toml`; local imports
  are only other `run_*.py` modules.
- **H35, H36, H37, H38, H39, H40, H41, H42, H43, H44 and H45 are COMPLETE**: every gate defect
  class that has surfaced is closed by an executable invariant, the point-in-time invariant
  covers every `run_*.py`, the engine's `total_return` spans every bar, the package's two Sharpe
  implementations agree, the lint/format gate is reproducible, the coverage gate is measured,
  declared and complete, and the package's public API is pinned by `tests/test_public_api_contract.py`.
- No published artifact, gate threshold, verdict or certified number was modified; no grid was
  re-run; no hypothesis was added.

## What changed (this session — H46)

- `tests/test_runner_import_contract.py` — **strengthened**: library imports (`qtr.*`) now
  assert the imported name is in `qtr.__all__` / the subpackage's `__all__` (previously only a
  non-asserting `hasattr` check); third-party imports are validated against `pyproject.toml`
  parsed via `tomllib` (previously a loose regex over the whole file plus a hardcoded
  `common_deps` fallback).
- `NEXT_TASK.md` — H46 marked complete; runner count corrected from 40 to 32; no next task
  assigned.
- `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`, `HANDOFF_NEXT.md` updated.

## What was actually verified

- `python -m pytest -q -W error tests/test_runner_import_contract.py` → **65 passed**.
- `python -m pytest -q -W error` → **1328 passed, 1 skipped**; `src/qtr` =
  **1038 statements, 316 branches, 0 missed, 0 partial, 100.00%**.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **89 files already formatted**.

## What remains unresolved

- The **committed** `src/qtr.egg-info/` manifest is stale. Regenerating it with the local
  setuptools (68.1.2) would *degrade* the committed `PKG-INFO`, so it was left untouched.
  Pre-existing, cosmetic.
- H9's published OOS Sharpe is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict cannot move (REJECT on the profit factor, 55× margin over its 1.0 gate).
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified
  families' numbers and verdicts are frozen.

## Approaches already tried / failed (and why)

- **Regenerating `src/qtr.egg-info/` with the local setuptools** — rejected as a regression to
  the committed metadata; see above.
- **An explicit top-level `__all__` list** — rejected in favour of composing it from the
  subpackages' `__all__`s, so the aggregate cannot drift from what it aggregates.

## Precise next task

None assigned: H45 and H46 are complete, the H1–H30 hypothesis space is exhausted, and all
gate-defect classes are closed by executable invariants.
