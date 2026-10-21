# HANDOFF_NEXT — H41: the runners' inline metric sites are pinned

## What changed (this session)

**`tests/test_runner_metric_agreement.py`** (+9 tests, now 42 total) — the executable
cross-runner metric-agreement contract extended to the runners' inline metric sites:

1. `TestInlineDrawdownConforming` — inline drawdowns using the library's convention
   (`cum / cummax - 1` at H11 :548,:648; `equity / expanding().max() - 1` at H18 :527,:641)
   agree with `validate_strategy["max_drawdown"]` within 1e-15 (4 parametrized tests).
2. `TestInlineDrawdownRawVariant` — inline drawdowns using the raw formula
   `(equity - expanding().max()).min()` (DDCV :386,:443; futures :467) — a dollar drawdown,
   not the library's ratio — are pinned as `differs_convention` (3 parametrized tests).
3. `TestH18TotalReturn` — H18's runner-local `total_return` copies (:526,:637) agree with the
   library's `total_return` exactly (2 tests).

No `run_*.py` was touched; no published artifact, gate threshold, verdict, certified number or
published row was modified; no grid was re-run; no hypothesis was added.

## What was actually verified

- `python -m pytest -q -W error` → **1212 passed, 1 skipped** (baseline before: 1203 passed,
  1 skipped after H40).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → all format-clean; the only deviation
  across the repo is on pre-existing lines of `tests/test_runner_causality_inventory.py`.
- `tests/test_engine_metric_agreement.py`, `tests/test_runner_causality_inventory.py` and
  `tests/test_causality_invariant.py` all pass alongside the updated module.
- The coverage tool (`pytest-cov` / `coverage`) is **not installed in this environment**, so
  the `src/qtr` 100% figure could not be re-measured here; H41 adds no branch to `src/qtr`
  (all changes are in the test module).

## What remains unresolved (disclosures, not rewrites)

- H9's published OOS Sharpe is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict cannot move (REJECT on the profit factor, 55× margin over its 1.0 gate).

## Precise next task

None. All assigned tasks (H35–H41) are complete. All metric-agreement sites — library-side
(§H39), runner-local helpers (§H40) and runner-inline sites (§H41) — are classified and pinned.
