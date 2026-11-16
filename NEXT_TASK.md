# Next task (set by this session, Cycle 172, 2026-11-16)

## Immediate next action (for the next agent/session)
- **Maintainer (preferred, unblocks CI):** apply and push
  `patches/0001-gates-workflow-contract-fix.patch` with workflow-scoped
  credentials, then run `python -m pytest -q tests/test_gates_workflow.py`
  (expect 7 passed) on `origin/main`.
- **Agent alternative (only with new evidence):** find and reproduce a
  runner-reachable defect in `src/qtr` not already pinned/closed in recent
  cycles (cache/fetcher normalization+dedup, config/EDGAR/schema fail-closed
  paths, annualization/split/CV/engine/baselines/`statistics.py` guards). If
  none is reproducible, do **not** make speculative source changes; refresh
  handoff evidence only. Do **not** edit `.github/workflows/**`, weaken
  `tests/test_gates_workflow.py`/gates/frozen contracts, or invent a
  free-data H183.

## Current state (Cycle 172 re-verification, 2026-11-16)
- **Changed this session:** none to `src/qtr`, tests, gates, artifacts, or
  workflow. `NEXT_TASK.md` updated with fresh own evidence.
- **Verified this session (own evidence, live tree @ HEAD 229f491):**
  - `git apply --check patches/0001-gates-workflow-contract-fix.patch` -> **PATCH_APPLIES_CLEANLY**.
  - `python -m pytest -q tests/test_gates_workflow.py` -> **7 failed** (unchanged, maintainer-gated: missing `scripts/**` path filters, editable install, `scripts` lint targets, and perf-gate step in `research_gates`).
  - `python -m ruff check src tests run_*.py scripts` -> **All checks passed**.
- **Baseline carried from Cycle 170/171 (live tree @ HEAD 229f491, unchanged):**
  - `python -m ruff format --check src tests run_*.py scripts` -> 336 files already formatted.
  - `python scripts/backtest_perf_regression_gate.py` -> PERF GATE PASSED (0.299s < 5s, 10.7MB, 13668 trades).
  - Full pinned suite `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py` (330.29s) -> **4238 passed, 51 skipped, 0 failed**, `src/qtr` coverage **100.00%** (1622 stmts / 606 branches / 0 miss).
- **Known unresolved (unchanged):** maintainer-only workflow patch for
  `.github/workflows/gates.yml`; H1–H182 exhausted under free/public PIT data
  (no honest H183 without new authorized data); reproducibility backlog
  baseline-frozen at Recoverable 0 / Excluded 172 / Unrecoverable 25
  (`missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`,
  `missing_meta_files=0`).

## Approaches already tried and why they should not be repeated
- Do not re-audit/close already-pinned defects without new evidence
  (cache-hit/fresh-fetch normalization+dedup, config boundaries/degenerate
  guards, EDGAR non-mapping handling, annualization/`bars_per_year`/
  `periods_per_year`/`risk_free` guards, split/CV operand guards, engine
  cost/metric/position guards, baselines target_vol guard, sidecar schema
  backfill, H182 runner, `statistics.py` operand guards incl. MTC `alpha`).
- Do not trust handoff counts without re-running the gate.
- Do not make speculative `src/qtr` changes absent a reproduced,
  runner-reachable defect.
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`,
  or alter coverage/frozen-contract gates or published/frozen artifacts/
  verdicts/thresholds/frozen numbers.
- Do not invent a free-data H183 or treat parameter/timeframe/universe/
  close-substitute variations as new mechanism families.
- Do not use `--cov=<dotted.module>` (aborts collection); use `--cov=qtr`.

## One precise next task
**Maintainer (preferred, unblocks CI):** apply and push
`patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then
`python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on
`origin/main`.

**Agent alternative (only with new evidence):** reproduce a concrete,
runner-reachable defect in `src/qtr` (not already pinned) and, if real, fix it
with the smallest reversible fail-closed change, tests preserving 100% `src/qtr`
coverage, and verification via:
- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py`
- `python -m ruff check src tests run_*.py scripts`
- `python -m ruff format --check src tests run_*.py scripts`
- `python scripts/backtest_perf_regression_gate.py`

**Constraints:** no gate weakening; no modification of published/frozen
artifacts, verdicts, thresholds, or frozen numbers except deliberate authorized
corpus/baseline updates; no workflow commit from agent.
