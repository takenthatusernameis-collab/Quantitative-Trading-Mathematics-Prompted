# Next task (set by this session)

## Immediate next action (for the next agent/session)
- **Maintainer (preferred, unblocks CI):** apply and push `patches/0001-gates-workflow-contract-fix.patch` with workflow-scoped credentials, then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on `origin/main`.
- **Agent alternative (only with new evidence):** only pursue a fix if a new concrete, runner-reachable defect exists in `src/qtr`, runners, or corpus metadata. Do **not** edit `.github/workflows/**`, do **not** weaken `tests/test_gates_workflow.py` or frozen contracts, and do **not** invent a free-data H183. If you change `src/qtr`, re-run the full pinned suite `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py`, ruff check/format, and `python scripts/backtest_perf_regression_gate.py` with own evidence.

## Current state (Cycle 160 complete, 2026-11-16)
- **Baseline independently re-verified (own evidence):** full pinned suite `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py` (460.29s) → **4120 passed, 51 skipped, 0 failed**, `src/qtr` coverage **100.00%** (1604 stmts / 592 branches / 0 miss). `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.437s < 5s, 10.7MB, 13668 trades). `python -m ruff check src tests run_*.py scripts` → clean; `python -m ruff format --check src tests run_*.py scripts` → **336 files already formatted**. `python -m pytest -q tests/test_gates_workflow.py` → **7 failed** (unchanged, maintainer-gated; fix is `patches/0001-gates-workflow-contract-fix.patch`). `git apply --check patches/0001-gates-workflow-contract-fix.patch` → **applies cleanly**.
- **Code/test change this session:** None. Working tree is clean (`git status` shows nothing to commit). The sec_insider test fix from Cycle 159 is already on `origin/main` (HEAD `3e55565`).
- **Known unresolved (unchanged):** maintainer-only workflow patch for `.github/workflows/gates.yml`; H1–H182 exhausted under free/public PIT data (no honest H183 without new authorized data); reproducibility backlog baseline-frozen at `missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=0`.

## Recent session (Cycle 160, 2026-11-16)
- **No code changes.** Verified full pinned suite (4120 passed, 51 skipped, 0 failed, 100% coverage), ruff check/format clean, perf gate passed. Only 7 maintainer-gated workflow contract tests fail; patch applies cleanly but cannot be landed by agent.

## Approaches already tried and why they should not be repeated
- Do not re-audit/close already-pinned defects without new evidence: cache-hit and fresh-fetch index/column normalization+dedup (Cycles 144/153), `max_leverage`/`initial_capital`/`max_position_size` boundaries (Cycles 147/148/152), duplicate index/column handling in engine/fetcher/tracker paths, `Experiment.record_artifact` DataFrame dedupe, `Experiment.load_metadata` non-dict-file handling (Cycle 150), artifact/log path traversal, `load_config`/`_set_nested` non-mapping-document handling (Cycle 154), EDGAR `_recent_filings`/`filing_documents` non-mapping-document handling (Cycle 155), `bars_per_year` numeric-index refusal (Cycle 156), `sharpe_ratio` degenerate-period refusal (Cycle 157), `purged_kfold_splits`/`combinatorial_purged_cv` operand guards (Cycle 158), and the insider scalar-form-cell `fetch_filings` end-to-end expectation (Cycle 159).
- Do not trust handoff counts without re-running the gate; this session ran the full pinned suite with own evidence.
- Do not make speculative `src/qtr` changes absent a reproduced, runner-reachable defect.
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or alter coverage/frozen-contract gates or published/frozen artifacts/verdicts/thresholds/frozen numbers.
- Do not invent a free-data H183 or treat parameter/timeframe/universe/close-substitute variations as new mechanism families.
- Do not use `--cov=<dotted.module>` (aborts collection with `ImportError: cannot load module more than once per process`); use `--cov=qtr`.

## One precise next task
**Maintainer (preferred, unblocks CI):** apply and push `patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on `origin/main`.

**Agent alternative (only with new evidence):** the `src/qtr` config-degenerate/fail-closed defect surface and pinned-suite red state (other than maintainer-gated workflow contract) are clear in this session's evidence. Do **not** hunt for another defect without a fresh reproduction. Only pursue a new fix if a concrete, reproduced, runner-reachable defect appears in `src/qtr`, runners, or corpus metadata; verify with the full pinned suite, ruff check/format, and the perf gate.

**Constraints:** no gate weakening; no modification of published/frozen artifacts, verdicts, thresholds, or frozen numbers except deliberate authorized corpus/baseline updates; no workflow commit from agent.