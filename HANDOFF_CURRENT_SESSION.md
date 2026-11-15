# HANDOFF — current session (2026-11-15, Cycle 147)

## What changed

1. **`src/qtr/backtest/engine.py` — invalid leverage now fails closed.**
   Cycle 146 reported no remaining defect. This session probed the remaining
   `BacktestConfig` numeric boundaries using correctly aligned signals and found
   new evidence: a negative `max_leverage` inverted a long-only book. With a
   `+1` target and `max_leverage=-1`, the normalization multiplied positions by
   `-1 / gross`; `NaN` and positive infinity bypassed the cap. The intentional
   `max_leverage=0` boundary already produced a flat book, so the fix maps every
   negative or non-finite value to that same zero-leverage path. Every finite
   non-negative value remains unchanged.

2. **Tests:** `tests/test_engine_edge_stress.py::TestInvalidLeverage` adds
   parametrized `-1`, `-inf`, `NaN`, and `+inf` cases plus a behavioural
   negative control reconstructing the pre-fix sign flip (**+5 tests**).

3. **Docs:** `HANDOFF.md`, `NEXT_TASK.md`, and this file record the evidence,
   validation, unresolved capital/position-size boundaries, and the next task.
   No gate, artifact, sidecar, hash, frozen-number, or workflow change.

## What was actually verified (own evidence)

- **Before-fix repro:** aligned prices `[100, 101, 102]`, long-only signals
  `[1, 1, 1]`, and `max_leverage=-1` produced positions `[-1, -1, -1]`, returns
  `[0, -0.01, -0.00990099]`, and a `sell` trade. After the fix the same call
  produces zero positions/returns and no trades.
- `python -m pytest -q tests/test_engine_edge_stress.py tests/test_backtest_engine.py -W error`
  → **98 passed**.
- Full pinned suite `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py`
  (356.90s) → **3929 passed, 48 skipped, 0 failed**, `src/qtr` coverage
  **100.00%** (1534 stmts / 546 branches / 0 miss; `engine.py` 243 stmts /
  86 branches, all covered).
- `python -m pytest -q tests/test_gates_workflow.py` → **7 failed**, unchanged
  and exclusively the documented maintainer-gated workflow contract.
- `python scripts/backtest_perf_regression_gate.py` → **PASSED** (0.326s < 5s,
  10.7MB peak, 13668 trades).
- Full `python -m ruff check src tests run_*.py scripts` → **All checks passed**;
  `python -m ruff format --check src tests run_*.py scripts` → **336 files
  already formatted**.

## What remains unresolved

1. **`BacktestConfig.initial_capital` is the next reproduced boundary.** With a
   valid long-only book, zero capital returns an all-zero equity curve,
   `-1000` returns negative equity, and `NaN`/`inf` return non-finite equity,
   while positions and return-based metrics are still produced. The next agent
   should make non-finite or non-positive capital return the existing
   no-evidence `empty_result` before exposure is computed.
2. **`max_position_size` needs a separate contract decision.** Preliminary
   probes with `-1` and `NaN` left positions unchanged rather than enforcing a
   cap; do not bundle that change with initial-capital validation.
3. **Maintainer-only CI contract:** apply
   `patches/0001-gates-workflow-contract-fix.patch` with workflow scope; the
   agent cannot persist `.github/workflows/**` changes.
4. **Frozen research/reproducibility baselines:** H1–H182 executed/rejected,
   H183 unassigned; reproducibility counts remain `197 / 11 / 528 / 0`.

## Approaches already tried / must not be repeated

- Do not repeat the claim that the `src/qtr` defect hunt is exhausted; this
  session reproduced a new public-API defect after that claim.
- Do not re-probe negative/non-finite `max_leverage`; it is closed and pinned.
  Preserve the existing zero-leverage flat-book behaviour.
- Do not edit workflows, weaken workflow/coverage gates, or change frozen
  artifacts, verdicts, thresholds, or numbers.
- Do not use dotted `--cov` module arguments; use `--cov=qtr`.

## One precise next task

Implement Cycle 148 as one bounded `BacktestConfig.initial_capital` fix:
reproduce the invalid-capital outputs above, return the existing no-evidence
result for non-finite or non-positive capital before exposure is computed, keep
a finite positive-capital control bit-identical, and add positive/invalid/
negative-control tests. Verify with focused tests, the full pinned coverage
suite, Ruff, and the performance gate. Leave `max_position_size` for the next
cycle.