# Current session handoff (2026-11-17, Cycle 204)

## What changed
- **Fixed duplicate-price-column handling across all eight public baseline signal builders.** The new nontrivial duplicate-symbol fixture reproduced `KeyError` in `mean_reversion_signals`, ambiguous-`Series` `ValueError` in `time_series_momentum_signals`, and the same `ValueError` in `carry_signals`; other builders retained ambiguous duplicate labels.
- Added keep-first canonicalization in `src/qtr/strategies/baselines.py` and 9 focused tests in `tests/test_baselines_extra.py`. Unique-column inputs are unchanged.
- No runner, gate, artifact, sidecar, hash, frozen-number, or workflow change.

## What was actually verified (own evidence, 2026-11-17)
- New regression tests before the fix: **8 failed, 1 passed**; after: **9 passed**.
- Focused baseline suite: `python -m pytest -q tests/test_baselines.py tests/test_baselines_extra.py -W error` → **151 passed**.
- Full pinned suite: `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py` → **4300 passed, 51 skipped, 0 failed**, `src/qtr` coverage **100.00%** (1676 stmts / 634 branches / 0 miss).
- `python -m ruff check src tests run_*.py scripts` → All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` → **336 files already formatted**.
- `python scripts/backtest_perf_regression_gate.py` → PERF GATE PASSED (0.305s < 5s, 10.7MB peak, 13668 trades).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → exit 0.
- `python -m pytest -q tests/test_gates_workflow.py` → **7 failed** (unchanged maintainer-gated contract; fixed by the patch).

## What remains unresolved
- **Maintainer-gated (agent-unreachable):** apply/push `patches/0001-gates-workflow-contract-fix.patch` with `workflows`-scoped credentials. After push: `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
- **Strategy-family discovery exhausted:** H1–H182 executed/rejected (`NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96). H183 data-blocked (futures roll/contango, crypto funding, or options PIT data).
- **Reproducibility backlog (frozen, authorization-gated):** missing_files=197, hash_mismatches=11, orphaned_files=528, missing_meta_files=0.
- **Maintainer authorization required:** repeated momentum-runner `param_grid_results` logging leaves one recorded hash stale; frozen and test-covered.

## One precise next task
- **Maintainer:** apply/push `patches/0001-gates-workflow-contract-fix.patch`, then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
- **Agent:** add the missing end-to-end `run_strategy` → `run_backtest` regression for duplicated-symbol `mean_reversion` and `time_series_momentum` panels, asserting keep-first positions and finite outputs. Keep changes confined to existing focused tests; rerun focused tests, ruff check/format, full pinned coverage, and the perf gate.

## Approaches already tried / not to repeat
- Do not repeat the Cycle 204 duplicate-price-column builder audit; all eight public builders are now canonicalized.
- Do not re-audit `src/qtr`/runners for previously pinned scalar/degenerate-input defect classes without NEW evidence.
- Do not edit/weaken `tests/test_gates_workflow.py` or `.github/workflows/**` (maintainer-gated; patch exists).
- Do not edit momentum runners' `param_grid_results` logging without maintainer authorization (frozen; test-covered).
- Do not invent H183 or treat parameter/timeframe/universe variants as new mechanism families.
- Do not trust handoff pass/fail/coverage counts — re-run gates.