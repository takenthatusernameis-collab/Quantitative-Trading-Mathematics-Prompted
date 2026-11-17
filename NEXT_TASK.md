# Next task (Cycle 177, 2026-11-17)

## What changed this session
No source changes. The prior session (Cycle 176) already landed and committed:
- `tests/test_backtest_engine.py` — added `TestFailClosedCostGuards::test_adv_for_symbol_fails_closed_on_degenerate_adv` (69 → 70 passed in that file).
- `src/qtr/backtest/engine.py` — ruff format fix at engine.py:641 (removed redundant parenthesization of the `participation` expression; AST-preserving, no behaviour change).
This session's work was purely re-verification: re-measured every enforced gate against the live tree because handoff counts cannot be trusted (the Cycle-175 handoff claimed green while the imported tree was 99.56% / 335-formatted).

## What was actually verified (own evidence, live tree, working tree clean at 404268c)
- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py` (331.65s) -> **4253 passed, 51 skipped, 0 failed**; `src/qtr` coverage **100.00%** (1650 stmts / 622 branches / 0 miss; engine.py 100%).
- `python -m pytest -q tests/test_backtest_engine.py -W error` -> **70 passed**.
- `python -m ruff check src tests run_*.py scripts` -> **All checks passed**.
- `python -m ruff format --check src tests run_*.py scripts` -> **336 files already formatted**.
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` -> **applies cleanly**.
- `python -m pytest -q tests/test_gates_workflow.py` -> **7 failed** (unchanged, maintainer-gated; all assertions on `.github/workflows/gates.yml` content). With the patch applied: **4253 passed, 51 skipped, 0 failed**.

## What remains unresolved
- The 7 `tests/test_gates_workflow.py` failures: fix is `patches/0001-gates-workflow-contract-fix.patch`. The agent **cannot** land it — repo-scoped token has no `workflows` permission, and `.github/scripts/kilo-controller.sh` restores `.github/workflows/**` from `origin/main` after every session. This is a maintainer action: apply + push the patch on `origin/main`, then `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
- No code defect remains in `src/qtr`; do not make speculative changes.

## One precise next task
**Maintainer:** apply and push `patches/0001-gates-workflow-contract-fix.patch` on `origin/main`, then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed). With it applied the whole pinned suite is **4253 passed, 51 skipped, 0 failed** at 100% coverage.
**Agent:** none — `src/qtr` is green at 100% coverage, ruff check + format clean, with no evidenced defect remaining. Act only on a new **reproduced, runner-reachable** defect (smallest reversible fail-closed fix, tests preserving 100% coverage, then pinned suite + ruff + perf gate verification). If you find a red gate on arrival, re-measure before trusting any handoff's pass/fail/coverage counts.

## Approaches already tried and why they should not be repeated
- Do not edit `.github/workflows/**` or weaken `tests/test_gates_workflow.py` — the failures are the maintainer-gated contract block; the fix is the workflow patch.
- Do not re-audit already-pinned defect classes without new evidence (cache normalization/dedup, config boundaries, EDGAR non-mapping, annualization/`bars_per_year`/`periods_per_year` guards, split/CV operand guards, engine cost/metric/position/impact guards, `CostModel` degenerate-input guards, `statistics.multiple_testing_correction(alpha=...)` guard, `_adv_for_symbol` degenerate-input guards — closed Cycle 176).
- Do not use `--cov=<dotted.module>` (aborts collection with `ImportError`); use `--cov=qtr`.
- Do not trust a handoff's pass/fail/coverage counts — re-run the gates (done this session: confirmed green).
