# Next task (2026-11-17, Cycle 205)

## What changed this session
- **No code changes.** Inspected repository state and verified that Cycle 204's requested follow-up (end-to-end duplicate-column contract for `run_strategy(..., "mean_reversion"/"time_series_momentum") -> run_backtest`) is already present and passing in `tests/test_baselines_extra.py` (`test_mean_reversion_e2e_duplicate_columns_keep_first`, `test_time_series_momentum_e2e_duplicate_columns_keep_first`).
- Prepared this handoff for the next session.

## What was actually verified (own evidence, 2026-11-17)
- `python -m pytest -q tests/test_baselines.py tests/test_baselines_extra.py -W error` → **153 passed**.
- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py` → **4305 passed, 48 skipped, 0 failed**, `src/qtr` coverage **100.00%** (1676 stmts / 634 branches / 0 miss).
- `python -m ruff check src tests run_*.py scripts` → All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` → **336 files already formatted**.
- `python scripts/backtest_perf_regression_gate.py` → PERF GATE PASSED (0.827s < 5s, 10.7MB peak, 13668 trades).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → exit 0 (applies cleanly).
- `python -m pytest -q tests/test_gates_workflow.py` → **NOT rerun this session**; expected **7 failed** on current `origin/main` state until maintainer applies the workflow patch (unchanged, maintainer-gated contract).

## What remains unresolved
- **Maintainer-gated (agent-unreachable):** apply/push `patches/0001-gates-workflow-contract-fix.patch` with `workflows`-scoped credentials, then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
- **Strategy-family discovery exhausted:** H1–H182 executed/rejected (`NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96). H183 is data-blocked (futures roll/contango, crypto funding, or options point-in-time data). Do not invent candidates or treat parameter/timeframe/universe variants as new mechanism families.
- **Reproducibility backlog (frozen, authorization-gated):** missing_files=197, hash_mismatches=11, orphaned_files=528, missing_meta_files=0.
- **Maintainer authorization required:** momentum runners log `param_grid_results` more than once per run (`run_ts_momentum_experiment.py:440/473/708`, `run_regime_gated_momentum_experiment.py:573/613/941`, `run_cs_momentum_experiment.py:294/516`), leaving one recorded hash stale. Frozen/test-covered; do not change without authorization and a full gate run.

## One precise next task
- **Maintainer:** apply and push `patches/0001-gates-workflow-contract-fix.patch`, then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
- **Agent (next session):** perform a bounded, evidence-first maintenance audit only if you can identify a concrete untested/public defect class with a reproducible failure case (not a repeat of prior scalar/degenerate/duplicate-column audits). If a new defect is found, add the smallest regression test + fix in `src/qtr`, then rerun focused tests, `python -m ruff check src tests run_*.py scripts`, `python -m ruff format --check src tests run_*.py scripts`, the full pinned coverage suite (`--ignore=tests/test_gates_workflow.py`), and `python scripts/backtest_perf_regression_gate.py`. Do not broaden into runner/corpus/frozen artifact edits, do not invent strategy families, and do not repeat audits already recorded as exhausted.

## Approaches already tried and why they should not be repeated
- Do not re-audit `src/qtr`/runners for the previously pinned scalar/degenerate-input defect classes without NEW evidence (exhaustively reviewed through Cycle 203).
- Do not repeat the duplicate-price-column builder/E2E audit performed in Cycle 204/205; canonicalization and `run_strategy -> run_backtest` keep-first contracts for mean_reversion/time_series_momentum are now covered.
- Do not edit `.github/workflows/**` or weaken `tests/test_gates_workflow.py` — maintainer-gated contract; fix is the workflow patch.
- Do not edit momentum runners' `param_grid_results` logging without maintainer authorization (frozen; test-covered).
- Do not invent H183 or treat parameter/timeframe/universe variants as new mechanism families.
- Do not trust handoff pass/fail/coverage counts — re-run gates.
