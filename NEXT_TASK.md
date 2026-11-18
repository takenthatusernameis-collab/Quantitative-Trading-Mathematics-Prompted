# Next task (2026-11-18, Cycle 209)

## What changed this session
- **No source change.** Executed the agent's bounded, evidence-first search for a NEW reproduced, runner-reachable defect in `src/qtr` or runners/corpus metadata (excluding the already-pinned scalar/degenerate, duplicate-price-column, duplicate-index, long-only-sign, and direction-formula-at-zero classes).
  - Re-read all seven `src/qtr` modules end-to-end (`utils/config.py`, `validation/statistics.py`, `strategies/baselines.py`, `backtest/engine.py`, `data/fetcher.py`, `data/insider.py`, `tracking/experiment.py`) — every public function carries fail-closed guards; no reachable defect found.
  - Spot-checked runners for lookahead (`shift(-N)`: 0 matches across `run_*.py`) and sign/direction usage (`run_h7`, `run_h9`, `run_h20`, `run_h21`, `run_h22`, `run_h25`, `run_h27`, `run_cs_momentum`, `run_ts_momentum`): long-only branches use `(mom > 0).astype(float)`, long/short branches use `np.sign(mom)` with NaN mapping — consistent with the H67 "sign of zero is not a direction" invariant. No new defect reproduced.
- No `src/qtr`, runner, test, gate, artifact, sidecar, hash, frozen-number, or workflow change.

## What was actually verified (own evidence, 2026-11-18)
- Full pinned suite `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py` → **4335 passed, 51 skipped, 0 failed** (648.99s), `src/qtr` coverage **100.00%** (1692 stmts / 642 branches / 0 miss). `Required test coverage of 100.0% reached.`
- `python -m ruff check src tests run_*.py scripts` → All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` → **337 files already formatted**.
- `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.798s < 5s, 10.7MB peak, 13668 trades).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → exit 0.
- `python -m pytest -q tests/test_gates_workflow.py` → **7 failed** (unchanged maintainer-gated contract; expected until the patch is applied).

## What remains unresolved
- **Maintainer-gated (agent-unreachable):** apply/push `patches/0001-gates-workflow-contract-fix.patch` with `workflows`-scoped credentials, then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
- **Strategy-family discovery exhausted:** H1–H182 executed/rejected (`NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96). H183 data-blocked (futures roll/contango, crypto funding, or options PIT data).
- **Reproducibility backlog (frozen, authorization-gated):** missing_files=197, hash_mismatches=11, orphaned_files=528, missing_meta_files=0.

## One precise next task
- **Maintainer:** (1) apply and push `patches/0001-gates-workflow-contract-fix.patch`, then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
- **Agent:** perform a bounded, evidence-first search for a NEW reproduced, runner-reachable defect in `src/qtr` or runners/corpus metadata (not previously pinned scalar/degenerate/duplicate-column/duplicate-index/long-only-sign/direction-formula-at-zero classes). If found, implement the smallest fix + focused regression, then rerun focused tests, `python -m ruff check src tests run_*.py scripts`, `python -m ruff format --check src tests run_*.py scripts`, full pinned coverage (`--ignore=tests/test_gates_workflow.py`), and `python scripts/backtest_perf_regression_gate.py`. If none found after concrete repro attempts, make no source change and re-verify the baseline with own evidence.

## Approaches already tried and why they should not be repeated
- Do not re-audit `src/qtr`/runners for the pinned defect classes without NEW evidence (exhaustively reviewed through Cycle 195+, plus this session's full re-read of all seven modules and runner spot-checks).
- Do not edit `.github/workflows/**` or weaken `tests/test_gates_workflow.py` (maintainer-gated; patch exists).
- Do not edit momentum runners' `param_grid_results` logging without maintainer authorization (frozen/test-covered).
- Do not invent H183 or treat parameter/timeframe/universe variants as new mechanism families.
- Do not trust handoff pass/fail/coverage counts — re-run the gates.

## HEAD
- `657923a` (adds all-NaN column drop to `run_backtest` + test; working tree clean, up to date with `origin/main`). Commit `7373188` beneath it reverted the `run_h7`/`run_h9` zero-momentum direction change.
