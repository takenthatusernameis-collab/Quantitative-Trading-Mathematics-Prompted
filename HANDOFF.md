# HANDOFF — H42 complete (session handoff)

## What changed
**H42 is complete.** The last open reproducibility gap is closed: the lint/format gate that the
record quoted throughout is now reproducible from a bare clone.

- `tests/test_runner_causality_inventory.py` — reformatted by `python -m ruff format`
  (`1 file reformatted`, 61 insertions / 22 deletions across 8 hunks). Pure whitespace; the file
  was introduced in H38 (commit 944cdc3) and was not touched by H39/H40/H41, so the drift
  predates the sessions that quoted the clean result.
- `FINAL_REPORT.md` — new §H42 section, updated `Summary statistics` (test-suite tally) and
  `Next Task`; `NEXT_TASK.md`; the `HANDOFF*` files.

## What was actually verified
- `python -m ruff check src tests run_*.py` → **All checks passed!** (unchanged).
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

## What remains unresolved
- **None of the reproducibility classes.** The `ruff` gap described in `HANDOFF.md` is closed:
  ruff is declared in `pyproject.toml` (`[project.optional-dependencies] lint`), the ruff
  configuration that makes the quoted commands meaningful is committed, and both commands are
  clean on `src tests run_*.py` from a bare clone with `pip install -e ".[lint]"`. The premise
  that ruff was undeclared was partly stale — `pyproject.toml` (introduced in H38, commit
  944cdc3) already carried the declaration and config; the residual gap was one format deviation,
  now closed.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified
  families (H10, H11, H12, H22, H25) are frozen.

## Approaches already tried / failed (and why)
- **Quoting `ruff format --check` as clean while a deviation remained was disclosed, not
  silently re-quoted**: H39/H40/H41 each recorded in their own handoff that the only deviation
  was on pre-existing lines of `tests/test_runner_causality_inventory.py`. H42 closed it rather
  than carrying the disclosure forward a fourth time.
- **Reformatting by hand instead of via `ruff format` was not attempted**: the tool is installed
  and the config is committed, so the canonical command reproduces the result exactly.

## Precise next task

**None assigned.** All tasks (H35–H42) are complete. No further work is assigned on any axis:
gate defects (§H35), point-in-time causality (§H36–H37), metric agreement (§H39–H41) and
reproducible lint/format (§H42).

(End of file - total 63 lines)