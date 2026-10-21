# HANDOFF — H43 complete (session handoff)

## What changed
**H43 is complete.** The record's coverage claim is now a measurement instead of an argument, and
the gate it describes is committed, reproducible and complete.

- `src/qtr/strategies/baselines.py` — the provably unreachable inline `if vol > 0:` guard in
  `time_series_momentum_signals` moved into a module-level `_vol_scale(vol, target_vol)` helper
  (returns `1.0` for a non-positive volatility, `min(target_vol / vol, 2.0)` otherwise).
  **Behavior-identical** — the old code simply skipped the scaling — but the defensive path is now
  reachable and covered. `time_series_momentum_signals` is called by no `run_*.py`, so no published
  artifact can be affected. (+2 statements.)
- `pyproject.toml` — the coverage gate: `[tool.coverage.run] branch = true`,
  `source = ["src/qtr"]`; `[tool.coverage.report] fail_under = 100`, `show_missing = true`.
- `tests/test_coverage_gate_contract.py` — **new**, 18 tests (6 gate pins + 12 branch-closure
  tests).
- `FINAL_REPORT.md` — new §H43 section, updated `Summary statistics` (test-suite tally, coverage
  bullet) and `Next Task`; `NEXT_TASK.md`; the `HANDOFF*` files.

## What was actually verified
- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` → **1230 passed,
  1 skipped**; `src/qtr` = **1016 statements, 316 branches, 0 missed, 0 partial, 100.00%**; the
  committed gate reports *"Required test coverage of 100.0% reached. Total coverage: 100.00%"*.
- `python -m pytest -q -W error` → **1230 passed, 1 skipped** in 271.26 s (the bare-clone path: no
  install step, no coverage plugin, no network).
- `python -m pytest -q -W error tests/test_coverage_gate_contract.py` → **18 passed**.
- Bare-clone path with the coverage tool **absent** (a shim module raising `ModuleNotFoundError`
  on `import coverage`): **17 passed, 1 skipped** — the tool-dependent pin skips cleanly.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **86 files already formatted** (85 + the new
  test module).

## What remains unresolved
- H9's published OOS Sharpe is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict cannot move (REJECT on the profit factor, 55× margin over its 1.0 gate).
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified
  families (H10, H11, H12, H22, H25) are frozen.
- **None of the verification classes.** The coverage gap is closed: `pytest-cov` was already
  declared in `pyproject.toml` (`[project.optional-dependencies] test`) but was never installed in
  the H39–H42 environments, so the figure was re-asserted four times instead of measured. The
  first measurement **confirmed** the recorded number (1014 statements, 0 missed) and then found
  the 11 partial branches that a statement-only figure cannot see. All 11 are closed and the gate
  now fails closed.

## Approaches already tried / failed (and why)
- **Re-asserting the coverage figure from a branch argument was the status quo and is now
  replaced**: H39/H40/H41/H42 each recorded that the coverage tool was not installed and carried
  the claim forward unchanged. H43 installed the tool, measured, and closed what the measurement
  found.
- **Suppressing the unreachable branch instead of resolving it was rejected**: the `vol > 0` guard
  in `time_series_momentum_signals` could be closed with a `pragma: no cover`, but that hides the
  fact rather than fixing it. The guard was moved into a helper whose non-positive arm is
  reachable and testable, which keeps the defensive behavior and makes it observable.
- **Setting `fail_under = 100` without first measuring was rejected**: the gate was declared only
  after the measurement, and the first run with the gate enabled *failed* the suite
  ("Coverage failure: total of 99 is less than fail-under=100"), which is the proof that the gate
  bites. It was then made green by closing the 11 arcs, not by relaxing the threshold.

## Precise next task

**None assigned.** All tasks (H35–H43) are complete. No further work is assigned on any axis:
gate defects (§H35), point-in-time causality (§H36–H37), metric agreement (§H39–H41),
reproducible lint/format (§H42) and a measured, declared, complete coverage gate (§H43).

(End of file - total 65 lines)
