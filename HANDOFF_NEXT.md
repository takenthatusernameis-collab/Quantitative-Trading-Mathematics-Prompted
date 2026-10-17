# Agent Handoff — For the next agent

## State you are inheriting

The repo is at **HEAD `679eee5`** (RUF046: `int(round(x))` -> `round(x)` in 4
scripts). Preceded by `15cf94f` (EXE001 cleanup), `21b0d25` (handoff
housekeeping), `68fdf8d` (F-rule ruff sweep). Baseline: **359/359 tests**,
`ruff check src tests` clean.

## What this session did

Confirmed the assigned RUF046 task was already complete (committed `679eee5`
before this session): all 4 sites now use `round(...)` without the redundant
`int()` wrapper. Verified:

- `ruff check run_*.py` -> 4 errors (2 SIM102 trade guards, 2 PERF102 dict
  iterations), all deliberately left as-is.
- `ruff check src tests` -> All checks passed.
- `pytest -q` -> 359 passed in 204 s.
- `git status` clean.

Updated `HANDOFF.md`, `NEXT_TASK.md`, and this file to record completion
instead of restating the done task.

## Precise next task (your call)

None bounded remains in free-data scope. Confirm the green baseline
(`git status` clean, `ruff check src tests`, `pytest -q`), then either
pursue paid hourly futures data work (out of scope) or declare the free-data
phase complete. Do not re-open SIM102/PERF102 or RUF046.

## Constraints handed down

- Do NOT touch `src/` or `tests/` — clean and must stay clean.
- Do NOT auto-fix SIM102 or PERF102 (unsafe; changes runtime behavior).
- The free-data hypothesis space (H1–H25) is exhausted; no bounded
  free-data experiment remains. Paid hourly futures data required for next
  step (out of free-data scope).
- Commit-per-experiment convention; bytecode is gitignored.
- CI progress telemetry is driven by `.github/scripts/kilo-controller.sh`;
  do not edit the helper's advertised field names without updating the
  controller and the audit guard together.
- Reconcile remote changes instead of blindly overwriting; verify
  persistence before declaring done.

Run `python -m pytest -q` to confirm the green baseline (359 passed) before
starting. `git status` should be clean.
