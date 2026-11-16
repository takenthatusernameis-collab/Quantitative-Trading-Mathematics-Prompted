# Next task (set by this session)

## Immediate next action (for the next agent/session)
- **Maintainer (preferred, unblocks CI):** apply and push `patches/0001-gates-workflow-contract-fix.patch` with workflow-scoped credentials, then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on `origin/main`.
- **Agent alternative (only with new evidence):** only pursue a fix if a new concrete, runner-reachable defect exists in `src/qtr`, runners, or corpus metadata. Do **not** edit `.github/workflows/**`, do **not** weaken `tests/test_gates_workflow.py` or frozen contracts, and do **not** invent a free-data H183. If you change `src/qtr`, re-run the full pinned suite `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py`, ruff check/format, and `python scripts/backtest_perf_regression_gate.py` with own evidence.

## Current state (Cycle 162 verification, 2026-11-16)
- **This session verified (own evidence):** `python -m pytest -q --ignore=tests/test_gates_workflow.py` → **4121 passed, 51 skipped** (+1 test for crypto_cost_bps Series non-finite guard). `python -m pytest -q tests/test_gates_workflow.py` → **7 failed** (unchanged, maintainer-gated; expected vs live `.github/workflows/gates.yml`). `git apply --check patches/0001-gates-workflow-contract-fix.patch` → **applies cleanly** (exit 0). `git status --short` clean at start.
- **Baseline carried forward from Cycle 161 evidence (not re-run this session):** full pinned suite excluding workflow-contract tests → **4120 passed, 51 skipped, 0 failed**, `src/qtr` coverage **100.00%**; `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED**; `ruff check`/`ruff format --check` clean over `src tests run_*.py scripts`. Treat as prior-session evidence unless re-verified.
- **Code/test change this session:** Fixed `CostModel.crypto_cost_bps` Series path to fail closed on non-finite vol (nan/inf/-inf), added test `test_crypto_cost_series_non_finite_vol_fails_closed_to_zero`. Coverage remains 100%.
- **Known unresolved (unchanged):** maintainer-only workflow patch for `.github/workflows/gates.yml`; H1–H182 exhausted under free/public PIT data (no honest H183 without new authorized data); reproducibility backlog baseline-frozen at `missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=0`.

## Approaches already tried and why they should not be repeated
- Do not re-audit/close already-pinned defects without new evidence (cache-hit/fresh-fetch index normalization+dedup, config boundaries/degenerate guards, EDGAR non-mapping handling, annualization/`bars_per_year`/`sharpe_ratio` guards, split/CV operand guards, and other closed surfaces recorded in `HANDOFF.md`).
- Do not trust handoff counts without re-running the gate; this session did not re-run the full pinned suite.
- Do not make speculative `src/qtr` changes or "hunt" absent a reproduced, runner-reachable defect.
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or alter coverage/frozen-contract gates or published/frozen artifacts/verdicts/thresholds/frozen numbers.
- Do not invent a free-data H183 or treat parameter/timeframe/universe/close-substitute variations as new mechanism families.
- Do not use `--cov=<dotted.module>` (aborts collection with `ImportError: cannot load module more than once per process`); use `--cov=qtr`.

## One precise next task
**Maintainer (preferred, unblocks CI):** apply and push `patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on `origin/main`.

**Agent alternative (only with new evidence):** if a new concrete, reproduced, runner-reachable defect appears in `src/qtr`, runners, or corpus metadata, implement the smallest reversible fix, add/adjust tests preserving 100% `src/qtr` coverage, and verify with the full pinned suite, ruff check/format, and the perf gate (own evidence required).

**Constraints:** no gate weakening; no modification of published/frozen artifacts, verdicts, thresholds, or frozen numbers except deliberate authorized corpus/baseline updates; no workflow commit from agent.

(End of file - total 40 lines)