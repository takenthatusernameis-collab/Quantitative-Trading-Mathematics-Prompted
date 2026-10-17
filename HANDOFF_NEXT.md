# Agent Handoff — For the next agent

## State you are inheriting

The repo is at **HEAD `57b9a4f`** (SIM102/PERF102 cleanup — the last 4
`run_*.py` ruff errors). Preceded by `679eee5` (RUF046), `3cba159`
(handoff housekeeping). Baseline: **359/359 tests**, `ruff check src tests
run_*.py` all clean, `ruff format --check run_*.py` all clean.

Working tree has **26 modified `run_*.py` files (uncommitted)** from
`ruff format` applied this session. `git status` is NOT clean — these
changes need to be committed before progress is durable. Branch is ahead of
`origin/main` by 2 commits (`57b9a4f`, `ebbc8c3`), not yet pushed.

## What this session did

Applied `ruff format` to all 26 `run_*.py` experiment scripts, resolving
formatting debt across the experiment harness. 26 files reformatted, 2
already formatted. No `src/` or `tests/` files were touched (constraint
still in force).

Verified:
- `ruff format --check run_*.py` -> All 28 files formatted (was 26
  unformatted + 2 already formatted).
- `ruff check run_*.py` -> All checks passed.
- `ruff check src tests` -> All checks passed.
- `pytest -q` -> 359 passed in 207.83 s (count unchanged -> semantics
  preserved).
- `bash -n` + `test_kilo_progress.sh` on all CI scripts -> OK
  (carried from Session 16).

Updated `HANDOFF.md`, `NEXT_TASK.md`, and this file.

## Precise next task (your call)

None bounded remains under current constraints. Confirm the green baseline
(`ruff check src tests run_*.py`, `ruff format --check run_*.py`, `pytest -q`),
then either (a) commit the 26 formatted `run_*.py` files and push to
`origin/main` (making progress durable), (b) lift the `src/`/`tests/`
hands-off constraint and apply `ruff format` there too, (c) pursue paid
hourly futures data work (out of scope), or (d) declare the free-data phase
complete. Do not re-open any ruff lint rule — the sweep is finished.

## Constraints handed down

- Do NOT touch `src/` or `tests/` — clean and must stay clean (ruff lint is
  clean; ruff format has 8 `src/` and 53 `tests/` files unformatted but the
  hands-off constraint blocks formatting them).
- The free-data hypothesis space (H1–H25) is exhausted; no bounded
  free-data experiment remains. Paid hourly futures data required for next
  step (out of free-data scope).
- Commit-per-experiment convention; bytecode is gitignored.
- CI progress telemetry is driven by `.github/scripts/kilo-controller.sh`;
  do not edit the helper's advertised field names without updating the
  controller and the audit guard together.
- Reconcile remote changes instead of blindly overwriting; verify
  persistence before declaring done.

Run `python -m pytest -q` to confirm the green baseline (359 passed)
before starting. `git status` should show the 26 formatted `run_*.py`
files as uncommitted changes.

(End of file - total 47 lines)