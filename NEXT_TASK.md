# Next task (set by this session, Cycle 163, 2026-11-16)

## Immediate next action (for the next agent/session)
- **Maintainer (preferred, unblocks CI):** apply and push
  `patches/0001-gates-workflow-contract-fix.patch` with workflow-scoped credentials,
  then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on
  `origin/main`.
- **Agent alternative (only with new evidence):** only pursue a fix if a new concrete,
  runner-reachable defect exists in `src/qtr`, runners, or corpus metadata. Do **not**
  edit `.github/workflows/**`, do **not** weaken `tests/test_gates_workflow.py` or
  frozen contracts, and do **not** invent a free-data H183. If you change `src/qtr`,
  re-run the full pinned suite
  `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py`,
  ruff check/format, and `python scripts/backtest_perf_regression_gate.py` with own evidence.

## Current state (Cycle 163 verification, 2026-11-16)
- **This session verified (own evidence):**
  `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py`
  -> **4188 passed, 51 skipped**, `src/qtr` coverage **100.00%** (1614 stmts, 598 branches, 0 missing).
  `python -m pytest -q tests/test_gates_workflow.py` -> **7 failed** (unchanged,
  maintainer-gated). `git apply --check patches/0001-gates-workflow-contract-fix.patch`
  -> applies cleanly. `ruff check`/`ruff format --check` clean over `src tests run_*.py scripts`.
  `python scripts/backtest_perf_regression_gate.py` -> **PERF GATE PASSED** (0.422s, limit 5s).
- **Code/test change this session:** Added fail-closed guards for degenerate numeric
  parameters to the baseline signal functions (`src/qtr/strategies/baselines.py`):
  `_is_int` (window/span/lookback/skip must be a real integer) and
  `_is_finite_non_negative` (per-asset cap must be finite and >= 0), applied to
  `moving_average_crossover_signals`, `ewma_crossover_signals`, `momentum_signals`,
  `mean_reversion_signals`, `time_series_momentum_signals`, `vol_scaled_tsmom_signals`,
  `carry_signals`; +67 tests in `tests/test_baselines_extra.py`. Coverage remains 100%.
  (Previously these raised opaque pandas errors on nan/inf/float/bool windows and
  silently failed to cap on negative/non-finite `max_position_size`.)
- **Known unresolved (unchanged):** maintainer-only workflow patch for
  `.github/workflows/gates.yml`; H1-H182 exhausted under free/public PIT data (no honest
  H183 without new authorized data); reproducibility backlog baseline-frozen at
  `missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=0`.

## Approaches already tried and why they should not be repeated
- Do not re-audit/close already-pinned defects without new evidence (cache-hit/fresh-fetch
  index normalization+dedup, config boundaries/degenerate guards, EDGAR non-mapping
  handling, annualization/`bars_per_year`/`sharpe_ratio` guards, split/CV operand guards,
  engine cost/metric guards, and other closed surfaces recorded in `HANDOFF.md`).
- Do not trust handoff counts without re-running the gate.
- Do not make speculative `src/qtr` changes or "hunt" absent a reproduced, runner-reachable defect.
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or alter
  coverage/frozen-contract gates or published/frozen artifacts/verdicts/thresholds/frozen numbers.
- Do not invent a free-data H183 or treat parameter/timeframe/universe/close-substitute
  variations as new mechanism families.
- Do not use `--cov=<dotted.module>` (aborts collection with `ImportError`); use `--cov=qtr`.

## One precise next task
**Maintainer (preferred, unblocks CI):** apply and push
`patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then
`python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on `origin/main`.

**Agent alternative (only with new evidence):** if a new concrete, reproduced,
runner-reachable defect appears in `src/qtr`, runners, or corpus metadata, implement the
smallest reversible fix, add/adjust tests preserving 100% `src/qtr` coverage, and verify
with the full pinned suite, ruff check/format, and the perf gate (own evidence required).

**Constraints:** no gate weakening; no modification of published/frozen artifacts, verdicts,
thresholds, or frozen numbers except deliberate authorized corpus/baseline updates; no
workflow commit from agent.

**Working-tree note:** `src/qtr/strategies/baselines.py` and
`tests/test_baselines_extra.py` are modified but NOT committed (no explicit commit
request). Commit them if this session's work is to be persisted before the next session.

(End of file - total 44 lines)