# Next task (set by this session, Cycle 169, 2026-11-16)

## Immediate next action (for the next agent/session)
- **Maintainer (preferred, unblocks CI):** apply and push
  `patches/0001-gates-workflow-contract-fix.patch` with workflow-scoped
  credentials, then run `python -m pytest -q tests/test_gates_workflow.py`
  (expect 7 passed) on `origin/main`.
- **Agent alternative (only with new evidence):** audit the remaining public
  scalar operands in `src/qtr/validation/statistics.py` for the same
  non-finite fail-open class closed this session for `risk_free`. Concrete
  lead: `multiple_testing_correction`'s `alpha` is unvalidated (a non-finite
  `alpha` produces a manufactured all-reject or all-accept result). Reproduce
  first; if real, apply the smallest fail-closed guard + tests preserving 100%
  `src/qtr` coverage. Do **not** edit `.github/workflows/**`, do **not** weaken
  `tests/test_gates_workflow.py` or frozen contracts, and do **not** invent a
  free-data H183.

## Current state (Cycle 169 verification, 2026-11-16)
- **Changed this session:** `src/qtr/validation/statistics.py` — fail-closed
  non-finite `risk_free` guards in `sharpe_ratio` and `compare_to_benchmark`
  (previously `nan`/`-inf` output, and an `-W error`-fatal `RuntimeWarning` in
  `compare_to_benchmark`). `tests/test_statistics.py` — +10 tests.
- **Verified this session (own evidence):**
  - `python -m ruff check src tests run_*.py scripts` -> All checks passed.
  - `python -m ruff format --check src tests run_*.py scripts` -> 336 files already formatted.
  - `python scripts/backtest_perf_regression_gate.py` -> PERF GATE PASSED
    (0.431s < 5s, 10.7MB, 13668 trades).
  - Full pinned suite
    `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py`
    (452.88s) -> **4220 passed, 51 skipped, 0 failed**, `src/qtr` coverage
    **100.00%** (1620 stmts / 604 branches / 0 miss).
  - `python -m pytest -q tests/test_gates_workflow.py` -> **7 failed**
    (unchanged, maintainer-gated; fix `patches/0001-gates-workflow-contract-fix.patch`).
- **Known unresolved (unchanged):** maintainer-only workflow patch for
  `.github/workflows/gates.yml`; H1–H182 exhausted under free/public PIT data
  (no honest H183 without new authorized data); reproducibility backlog
  baseline-frozen at Recoverable 0 / Excluded 172 / Unrecoverable 25.

## Approaches already tried and why they should not be repeated
- Do not re-audit/close already-pinned defects without new evidence
  (cache-hit/fresh-fetch index normalization+dedup, config boundaries/degenerate
  guards, EDGAR non-mapping handling, annualization/`bars_per_year` guards,
  split/CV operand guards, engine cost/metric guards, baselines target_vol guard,
  sidecar schema backfill, H182 runner, and now non-finite `risk_free`).
- Do not trust handoff counts without re-running the gate.
- Do not make speculative `src/qtr` changes or "hunt" absent a reproduced,
  runner-reachable defect.
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or
  alter coverage/frozen-contract gates or published/frozen artifacts/verdicts/
  thresholds/frozen numbers.
- Do not invent a free-data H183 or treat parameter/timeframe/universe/close-
  substitute variations as new mechanism families.
- Do not use `--cov=<dotted.module>` (aborts collection); use `--cov=qtr`.

## One precise next task
**Maintainer (preferred, unblocks CI):** apply and push
`patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then
`python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on
`origin/main`.

**Agent alternative (only with new evidence):** reproduce and, if real, fix the
unvalidated `alpha` operand in `multiple_testing_correction` (and any sibling
public scalar operand found), with the smallest reversible fail-closed change,
tests preserving 100% `src/qtr` coverage, and verification via:
- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py`
- `python -m ruff check src tests run_*.py scripts`
- `python -m ruff format --check src tests run_*.py scripts`
- `python scripts/backtest_perf_regression_gate.py`

**Constraints:** no gate weakening; no modification of published/frozen
artifacts, verdicts, thresholds, or frozen numbers except deliberate authorized
corpus/baseline updates; no workflow commit from agent.

(End of file - total 44 lines)