# HANDOFF_NEXT — H42: the lint/format gate is reproducible

## What changed (this session)

- `tests/test_runner_causality_inventory.py` — reformatted by `python -m ruff format`
  (`1 file reformatted`, 61 insertions / 22 deletions across 8 hunks). Pure whitespace; the file
  was introduced in H38 (commit 944cdc3) and was not touched by H39/H40/H41, so the drift
  predates the sessions that quoted the clean result.
- `FINAL_REPORT.md` — new §H42 section, updated `Summary statistics` (test-suite tally) and
  `Next Task`; `NEXT_TASK.md`; the `HANDOFF*` files.

## What was actually verified

- `python -m ruff check src tests run_*.py` → *All checks passed!* (unchanged).
- `python -m ruff format --check src tests run_*.py` → **85 files already formatted** (was
  `1 file would be reformatted, 84 files already formatted`; the deviation is gone).
- `python -m pytest -q -W error tests/test_runner_causality_inventory.py` → **321 passed**
  (the module that owns the formatted file; unchanged — formatting cannot change semantics).
- `python -m pytest -q -W error` → **1212 passed, 1 skipped** in 275.34 s (identical to the H41
  baseline of 1212 passed, 1 skipped in 276.17 s; the change is whitespace-only).
- `src/qtr` coverage is unchanged at 100%: the change is confined to a test file, so no branch is
  added or removed. (The coverage tool, `pytest-cov`, is still not installed in this
  environment — `python -m pytest --cov=qtr` → "unrecognized arguments"; the H39/H40/H41 branch
  argument applies unchanged.)

## What remains unresolved (disclosures, not rewrites)

- H9's published OOS Sharpe is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict cannot move (REJECT on the profit factor, 55× margin over its 1.0 gate).
- The premise in `HANDOFF.md` that ruff was undeclared was partly stale: `pyproject.toml`
  (introduced in H38, commit 944cdc3) already declares `[project.optional-dependencies] lint`
  and a `[tool.ruff]` block with `target-version`, `line-length`, a lint `select`/`ignore` set and
  a format `quote-style`/`indent-style`. The residual gap was one format deviation, now closed.

## Precise next task

None. All assigned tasks (H35–H42) are complete. All metric-agreement sites — library-side
(§H39), runner-local helpers (§H40) and runner-inline sites (§H41) — are classified and pinned;
every gate defect class that has surfaced (§H35) is closed by an executable invariant; the
point-in-time contract covers every `run_*.py` (§H36–H37); the engine's `total_return` spans
every bar (§H38); the package's two Sharpe implementations agree (§H39); and the lint/format
gate is reproducible (§H42). No further work is assigned.

(End of file - total 41 lines)