# Next task (2026-11-17, Cycle 204)

## What changed this session
- **Fixed reproduced duplicate-price-column failures in the public baseline signal builders.** A duplicated symbol panel (`columns=["A", "A", "B"]`) made `mean_reversion_signals` raise `KeyError`, `time_series_momentum_signals` raise `ValueError: The truth value of a Series is ambiguous`, and `carry_signals` raise the same `ValueError` on the new nontrivial fixture. The other builders retained ambiguous duplicate output labels.
- Added `src/qtr/strategies/baselines.py::_drop_duplicate_price_columns` and applied it keep-first across all eight public signal builders. Unique-column inputs return the original object unchanged; duplicated columns now match the engine/tracking keep-first convention.
- Added 9 tests in `tests/test_baselines_extra.py`: 8 parametrized public-builder cases and one clean-path/keep-first guard case. No runner, gate, artifact, sidecar, hash, frozen-number, or workflow change.

## What was actually verified (own evidence, 2026-11-17)
- New tests before the source fix: **8 failed, 1 passed**; after the fix: **9 passed**.
- `python -m pytest -q tests/test_baselines.py tests/test_baselines_extra.py -W error` → **151 passed**.
- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py` → **4300 passed, 51 skipped, 0 failed**, `src/qtr` coverage **100.00%** (1676 stmts / 634 branches / 0 miss).
- `python -m ruff check src tests run_*.py scripts` → All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` → **336 files already formatted**.
- `python scripts/backtest_perf_regression_gate.py` → PERF GATE PASSED (0.305s < 5s, 10.7MB peak, 13668 trades).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → exit 0 (applies cleanly).
- `python -m pytest -q tests/test_gates_workflow.py` → **7 failed** (unchanged maintainer-gated contract; fixed by the patch). Not a new defect.

## What remains unresolved
- **Maintainer-gated (agent-unreachable):** apply/push `patches/0001-gates-workflow-contract-fix.patch` with `workflows`-scoped credentials, then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
- **Strategy-family discovery exhausted:** H1–H182 executed/rejected (`NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96). H183 is data-blocked (futures roll/contango, crypto funding, or options point-in-time data). Do not invent candidates or treat parameter/timeframe/universe variants as new mechanism families.
- **Reproducibility backlog (frozen, authorization-gated):** missing_files=197, hash_mismatches=11, orphaned_files=528, missing_meta_files=0.
- **Maintainer authorization required:** momentum runners log `param_grid_results` more than once per run (`run_ts_momentum_experiment.py:440/473/708`, `run_regime_gated_momentum_experiment.py:573/613/941`, `run_cs_momentum_experiment.py:294/516`), leaving one recorded hash stale. Frozen/test-covered; do not change without authorization and a full gate run.

## One precise next task
- **Maintainer:** apply and push `patches/0001-gates-workflow-contract-fix.patch`, then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
- **Agent (next session):** add the missing end-to-end contract for this fix: feed a duplicated-symbol panel through `run_strategy(..., "mean_reversion" or "time_series_momentum")` and then `run_backtest`, asserting keep-first positions and finite returns/equity. Keep it to focused tests in the existing baseline/engine test files; rerun those tests, ruff check/format, the full pinned coverage suite, and the perf gate. Do not broaden into runner/corpus edits or repeat the duplicate-column audit after this contract is green.

## Approaches already tried and why they should not be repeated
- Do not re-audit `src/qtr`/runners for the previously pinned scalar/degenerate-input defect classes without NEW evidence (exhaustively reviewed through Cycle 203).
- Do not repeat the duplicate-price-column builder audit performed in Cycle 204; it is now canonicalized across all eight public builders.
- Do not edit `.github/workflows/**` or weaken `tests/test_gates_workflow.py` — maintainer-gated contract; fix is the workflow patch.
- Do not edit momentum runners' `param_grid_results` logging without maintainer authorization (frozen; test-covered).
- Do not invent H183 or treat parameter/timeframe/universe variants as new mechanism families.
- Do not trust handoff pass/fail/coverage counts — re-run gates.