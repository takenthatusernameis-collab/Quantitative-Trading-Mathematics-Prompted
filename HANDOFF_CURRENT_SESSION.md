# Handoff — Current Session: fail-closed non-finite `risk_free` guard (Cycle 169, 2026-11-16)

## What changed
- `src/qtr/validation/statistics.py`:
  - `sharpe_ratio`: added a fail-closed guard so a non-finite `risk_free`
    (`nan`/`inf`/`-inf`) returns `0.0` instead of `nan`/`-inf`.
  - `compare_to_benchmark`: added the same guard so a non-finite `risk_free`
    returns `_no_comparison()` instead of a `nan` `alpha_annualized` alongside
    finite `beta`/IR/p-value (and instead of an `-W error`-fatal
    `RuntimeWarning: invalid value encountered in scalar subtract`).
  - Both docstrings updated to state the new invariant.
- `tests/test_statistics.py`: +10 tests
  (`TestSharpeRatioRiskFreeGuard`, plus two `compare_to_benchmark` cases),
  covering both outcomes of each new branch and a pre-fix negative control.

## Why this was a real defect (own reproduction, before the fix)
- `sharpe_ratio(rets, risk_free=nan)` -> `nan`; `risk_free=inf` -> `-inf`.
- `compare_to_benchmark(strat, bench, risk_free=inf)` raised
  `RuntimeWarning: invalid value encountered in scalar subtract` under
  `python -W error` (fatal in the pinned suite), and with `nan` returned
  `alpha_annualized=nan` while `information_ratio`/`alpha_p_value` stayed finite
  — the same internally-inconsistent, fail-open class the module already guards
  for `periods_per_year`, `max_p_value`, `adv`, `max_participation`, etc.
- No in-tree runner passes a non-default `risk_free` (all use `0.0`), so no
  published/frozen number changes; the full suite confirms this.

## Actually verified (this session, own evidence)
- `python -m ruff check src tests run_*.py scripts` -> All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` -> 336 files already formatted.
- `python scripts/backtest_perf_regression_gate.py` -> PERF GATE PASSED
  (0.431s < 5s, 10.7MB peak, 13668 trades).
- Full pinned suite
  `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py`
  (452.88s) -> **4220 passed, 51 skipped, 0 failed**, `src/qtr` coverage
  **100.00%** (1620 stmts / 604 branches / 0 miss).
- `python -m pytest -q tests/test_gates_workflow.py` -> **7 failed** (unchanged,
  maintainer-gated; fix is `patches/0001-gates-workflow-contract-fix.patch`).

## Approaches already tried / do not repeat
- Do not re-audit the already-pinned statistics guards without new evidence
  (empty/non-finite data, `periods_per_year`, split/CV operands, `max_p_value`,
  `adv`/`max_participation`, `power`/`alpha`/`effect_size`, etc. are closed).
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or
  alter coverage/frozen-contract gates or published/frozen artifacts/verdicts/
  thresholds/numbers.
- Do not invent a free-data H183 or treat parameter/timeframe/universe/close-
  substitute variations as new mechanism families.
- Do not use `--cov=<dotted.module>` (aborts collection); use `--cov=qtr`.

## Unresolved / pre-existing (unchanged)
- Maintainer-only workflow patch for `.github/workflows/gates.yml` required to
  make `tests/test_gates_workflow.py` green on `origin/main`
  (`patches/0001-gates-workflow-contract-fix.patch`); the agent token has no
  `workflows` permission and the controller restores `.github/workflows/**`.
- H1–H182 exhausted/rejected under free/public PIT data; no honest H183 without
  new authorized data (see `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 140/116).
- Reproducibility backlog baseline-frozen: Recoverable 0 / Excluded 172 /
  Unrecoverable 25.

## One precise next task
**Maintainer (preferred, unblocks CI):** apply and push
`patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then
`python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on
`origin/main`.

**Agent alternative (only with new evidence):** audit the remaining public
scalar operands for the same non-finite fail-open class. Concrete lead:
`multiple_testing_correction(p_values, alpha=...)` does not validate `alpha`; a
non-finite `alpha` (e.g. `inf`) makes `rejected = adjusted < alpha` reject every
hypothesis (a manufactured rejection), and `alpha=nan` rejects none. Reproduce
first, then apply the smallest fail-closed guard + tests, preserving 100%
`src/qtr` coverage, and verify with the full pinned suite, ruff, and the perf
gate.

## Evidence / constraints
- Changes are in the working tree (not committed; no commit was requested).
- `git diff --stat`: `src/qtr/validation/statistics.py` (+27/-1),
  `tests/test_statistics.py` (+63).
- Do not modify published/frozen artifacts, verdicts, thresholds, or frozen
  numbers; do not weaken gates; no workflow commit from the agent.