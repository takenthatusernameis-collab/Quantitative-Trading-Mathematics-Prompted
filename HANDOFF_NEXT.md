# Agent Handoff — For the next agent

## State you are inheriting

The repo is at HEAD `8cead58` (branch up to date with `origin/main`).
Baseline: **359/359 tests**, `ruff check src tests run_*.py` all clean,
`ruff format --check src tests run_*.py` all clean (61 files formatted).

Working tree has **27 modified files uncommitted** from `ruff format`
applied this session (8 in `src/`, 19 in `tests/`). `git status` is NOT
clean — these changes need to be committed and pushed before progress is
durable.

## What this session did

Lifted the `src/`/`tests/` hands-off constraint and applied `ruff format`
to those directories, resolving the last ruff format debt. 27 files
reformatted, 34 already formatted. No `src/`/`tests/` semantics altered.

Verified:
- `ruff format --check src tests run_*.py` -> All 61 files formatted.
- `ruff check src tests run_*.py` -> All checks passed.
- `pytest -q` -> 359 passed in 206.35 s (count unchanged -> semantics
  preserved).

Updated `HANDOFF.md`, `NEXT_TASK.md`, and this file.

## Precise next task

1. `git add src tests` and commit the 27 formatted files (one commit).
2. Push to `origin/main`.
3. Verify persistence: `git status` clean, remote in sync.
4. Declare the free-data phase complete. No bounded task remains under
   current constraints; paid hourly futures data work is out of scope.

## Constraints handed down

- Do NOT re-open any ruff lint rule — the sweep is finished.
- Do NOT touch `src/`/`tests/` semantics — formatting only is permitted.
- The free-data hypothesis space (H1–H25) is exhausted; no bounded
  free-data experiment remains. Paid hourly futures data required for next
  step (out of free-data scope).
- Commit-per-experiment convention; bytecode is gitignored.
- Reconcile remote changes instead of blindly overwriting; verify
  persistence before declaring done.

(End of file)
