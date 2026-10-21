# HANDOFF_CURRENT — session complete (H41)

## State

- **H41 is COMPLETE** as recorded in `NEXT_TASK.md`, `HANDOFF_NEXT.md`, `HANDOFF_CURRENT.md` and
  `HANDOFF_CURRENT_SESSION.md`: the metric-agreement contract has been extended from the library
  to the runners' inline metric sites — the inline drawdowns using the library's convention
  (H11 :548,:648; H18 :527,:641) are pinned as agreeing within 1e-15, the raw drawdown variants
  (DDCV :386,:443; futures :467) are pinned as `differs_convention`, and H18's runner-local
  `total_return` copies (:526,:637) are pinned as agreeing exactly.
- **H35, H36, H37, the remaining-runner extension, H38, H39 and H40 are COMPLETE** as recorded
  in `NEXT_TASK.md`, `HANDOFF_NEXT.md` and `HANDOFF_CURRENT_SESSION.md`: every gate defect class
  that has surfaced is closed by an executable invariant, the point-in-time invariant covers
  every `run_*.py` in the repository, the engine's `total_return` spans every bar, and the
  package's two Sharpe implementations agree.
- No published artifact, gate threshold, verdict, certified number or published row was
  modified; no grid was re-run; no hypothesis was added.

## What changed (this session — H41)

- `tests/test_runner_metric_agreement.py` (+9 tests, now 42 total) — added:
  - `TestInlineDrawdownConforming` — inline drawdowns using the library's convention
    (`cum / cummax - 1` or `equity / expanding().max() - 1`) agree with
    `validate_strategy["max_drawdown"]` within 1e-15 (4 parametrized tests).
  - `TestInlineDrawdownRawVariant` — inline drawdowns using the raw formula
    `(equity - expanding().max()).min()` (a dollar drawdown, not the library's ratio) are
    pinned as `differs_convention` (3 parametrized tests).
  - `TestH18TotalReturn` — H18's runner-local `total_return` copies agree with the library's
    `total_return` exactly (2 tests).
- `NEXT_TASK.md`, `HANDOFF_NEXT.md`, `HANDOFF_CURRENT_SESSION.md`, this file.
- No `run_*.py` was touched; no published artifact, gate threshold, verdict, certified number
  or published row was modified; no grid was re-run; no hypothesis was added.

## What was actually verified

- Baseline (before this session, after H40): `python -m pytest -q -W error` → **1203 passed,
  1 skipped**.
- After: `python -m pytest -q -W error` → **1212 passed, 1 skipped** (1203 + the 9 new H41
  tests; the skip is the pre-existing `buy_and_hold` skip in H36's module).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → all format-clean; the only deviation
  across the repo is on pre-existing lines of `tests/test_runner_causality_inventory.py`
  (ruff 0.17.1 style drift, not touched this session).
- `tests/test_engine_metric_agreement.py`, `tests/test_runner_causality_inventory.py` and
  `tests/test_causality_invariant.py` all pass alongside the updated module.

## What remains unresolved

- H9's published OOS Sharpe is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict cannot move.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified
  families' numbers and verdicts are frozen.
- **No further task is assigned.** All metric-agreement sites (library and runners, helpers and
  inline) are classified and pinned.

## Approaches already tried / failed (and why)

- **Rewriting the runners' local metric helpers in place was rejected**: the artifacts are
  frozen, so a rewritten helper would stop reproducing them. The copies are classified and
  pinned, not replaced.
- **Re-running a grid to quantify the impact was not attempted and is forbidden.** Every number
  is read out of the committed artifacts and the committed H26 audit.

## Precise next task

None. All assigned tasks (H35–H41) are complete.
