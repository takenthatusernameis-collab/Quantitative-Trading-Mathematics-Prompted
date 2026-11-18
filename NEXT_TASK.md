# Next task (2026-11-17, Cycle 206)

## What changed this session
- **Fixed reproduced duplicate-index (duplicated bar label) defect in all public baseline signal builders** (`src/qtr/strategies/baselines.py`): `ma_crossover/ewma_crossover/mean_reversion` raised `ValueError: cannot reindex on an axis with duplicate labels` on duplicate-index panels. Added keep-first sorted duplicate-index canonicalization (defensive, symmetric with `run_backtest`) via `_canonicalize_price_panel`; unique panels unchanged. Added 8 parametrized regression tests in `tests/test_baselines_extra.py` covering all 8 public builders. No runner/gate/artifact/sidecar/hash/frozen-number/workflow change.

## What was actually verified (own evidence, 2026-11-17)
- Pre-fix repro (inline): `ma_crossover`, `ewma_crossover`, `mean_reversion` raised on duplicate-index panel.
- `python -m pytest -q tests/test_baselines_extra.py -k duplicate_index -W error` → **8 passed**.
- `python -m pytest -q tests/test_baselines.py tests/test_baselines_extra.py -W error` → **161 passed**.
- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py` → **4313 passed, 48 skipped, 0 failed**, `src/qtr` coverage **100.00%** (1682 stmts / 638 branches / 0 miss).
- `python -m ruff check src tests run_*.py scripts` → All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` → **336 files already formatted**.
- `python scripts/backtest_perf_regression_gate.py` → PERF GATE PASSED (0.778s < 5s, 10.7MB peak, 13668 trades).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → exit 0.
- `python -m pytest -q tests/test_gates_workflow.py` → **NOT rerun** (unchanged maintainer-gated contract; expected 7 failed until patch applied).

## What remains unresolved
- **Maintainer-gated (agent-unreachable):** apply/push `patches/0001-gates-workflow-contract-fix.patch` with `workflows`-scoped credentials, then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
- **Strategy-family discovery exhausted:** H1–H182 executed/rejected (`NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96). H183 data-blocked (futures roll/contango, crypto funding, or options PIT data).
- **Reproducibility backlog (frozen, authorization-gated):** missing_files=197, hash_mismatches=11, orphaned_files=528, missing_meta_files=0.
- **Maintainer authorization required:** repeated momentum-runner `param_grid_results` logging leaves one recorded hash stale; frozen/test-covered.

## One precise next task
- **Maintainer:** apply and push `patches/0001-gates-workflow-contract-fix.patch`, then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
- **Agent:** perform a bounded, evidence-first search for a NEW reproduced, runner-reachable defect in `src/qtr` or runners/corpus metadata (not previously pinned scalar/degenerate/duplicate-column/duplicate-index audits). If found, implement the smallest fix + focused regression, then rerun focused tests, `python -m ruff check src tests run_*.py scripts`, `python -m ruff format --check src tests run_*.py scripts`, full pinned coverage (`--ignore=tests/test_gates_workflow.py`), and `python scripts/backtest_perf_regression_gate.py`. If none found after concrete repro attempts, make no source change and re-verify baseline with own evidence.

## Approaches already tried and why they should not be repeated
- Do not re-audit `src/qtr`/runners for previously pinned scalar/degenerate-input, duplicate-price-column builder/E2E, or duplicate-index builder classes without NEW evidence (Cycles 203–206).
- Do not edit `.github/workflows/**` or weaken `tests/test_gates_workflow.py` — maintainer-gated; fix is the workflow patch.
- Do not edit momentum runners' `param_grid_results` logging without maintainer authorization (frozen; test-covered).
- Do not invent H183 or treat parameter/timeframe/universe variants as new mechanism families.
- Do not trust handoff pass/fail/coverage counts — re-run gates.
