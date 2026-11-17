# Next task (Cycle 176, 2026-11-17)

## What changed this session
The working tree arrived **red on two enforced gates** even though the Cycle-175 handoff claimed green. Both were consequences of the same incomplete `_adv_for_symbol` commit that landed in the squashed import; both are now fixed with the smallest change and verified.

- `tests/test_backtest_engine.py` — added `TestFailClosedCostGuards::test_adv_for_symbol_fails_closed_on_degenerate_adv`. `src/qtr/backtest/engine.py::_adv_for_symbol` (engine.py:376-438) is the sibling fail-closed guard on the market-impact operand (`capital / (price * adv)`). Its degenerate-input branches (adv `None`; a `pd.DataFrame` panel; a non-mapping list/scalar/str; an absent symbol; a raw value `float()` cannot parse) had **no test**, so the enforced 100% coverage gate measured them uncovered (engine.py 97%, total 99.56%, `FAIL Required test coverage of 100.0%`). The new test pins every branch with the exact input that takes it; the non-finite/non-positive branch (engine.py:436) was already covered by `test_adv_zero_skips_impact` and `test_equity_impact_skips_symbol_with_invalid_adv`. Docstring of `TestFailClosedCostGuards` extended to name the helper.
- `src/qtr/backtest/engine.py` — `ruff format` collapsed the redundant 3-line parenthesization of the impact `participation` expression (engine.py:640-642) to one line. This was a **pre-existing** `ruff format --check` violation committed with `_adv_for_symbol` (the Cycle-175 handoff's "336 files already formatted" was stale). The change is AST-preserving (identical expression; only redundant parens removed) — no behaviour change.

## What was actually verified (own evidence, live tree, changes uncommitted)
- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py` (343.25s) -> **4253 passed, 51 skipped, 0 failed**; `src/qtr` coverage **100.00%** (1650 stmts / 622 branches / 0 miss; engine.py 100%). Was **4252 passed, 99.56%** before this session.
- `python -m pytest -q tests/test_backtest_engine.py -W error` -> **70 passed** (was 69; +1 new test).
- `python -m ruff check src tests run_*.py scripts` -> **All checks passed**.
- `python -m ruff format --check src tests run_*.py scripts` -> **336 files already formatted** (was 1 would-reformat).
- `python scripts/backtest_perf_regression_gate.py` -> **PERF GATE PASSED** (0.286s < 5s, 10.7MB, 13668 trades).
- `python -m pytest -q tests/test_gates_workflow.py` -> **7 failed** (unchanged, maintainer-gated; fix is `patches/0001-gates-workflow-contract-fix.patch`).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` -> still **applies cleanly**.

## What remains unresolved
- The 7 `tests/test_gates_workflow.py` failures: fix is `patches/0001-gates-workflow-contract-fix.patch`; the agent cannot land it (repo-scoped token has no `workflows` permission; `.github/scripts/kilo-controller.sh` restores `.github/workflows/**` from `origin/main` after every session). With it applied: **4253 passed, 51 skipped, 0 failed**.
- The changes above (`src/qtr/backtest/engine.py`, `tests/test_backtest_engine.py`) are **uncommitted** in the working tree — no commit unless explicitly requested (prior-session convention).
- The repository git history is a **single squashed import commit** `14de981` (empty message, 3168 files). There is no per-cycle history to diff against; the Cycle-175 handoff's counts (1633 stmts / 612 branches, 100%) do not match the imported tree (1650 stmts / 622 branches, 99.56% before this session) — treat handoff counts as approximate and re-measure.

## One precise next task
**Maintainer (preferred, unblocks CI):** apply and push `patches/0001-gates-workflow-contract-fix.patch` on `origin/main`, then `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed). With it applied the whole pinned suite is **4253 passed, 51 skipped, 0 failed** at 100% coverage.

**Agent:** none — `src/qtr` is now green at 100% coverage, ruff check + format clean, perf gate green, with no evidenced defect remaining. Do **not** make speculative `src/qtr` changes. Act only on a new **reproduced, runner-reachable** defect (smallest reversible fail-closed fix, tests preserving 100% coverage, then the pinned suite + ruff + perf gate verification). If you find a red gate on arrival, re-measure before trusting any handoff's pass/fail counts.

## Approaches already tried and why they should not be repeated
- Do not edit `.github/workflows/**` or weaken `tests/test_gates_workflow.py` — the failures are the maintainer-gated contract block; the fix is the workflow patch.
- Do not re-audit already-pinned defect classes without new evidence (cache normalization/dedup, config boundaries, EDGAR non-mapping, annualization/`bars_per_year`/`periods_per_year` guards, split/CV operand guards, engine cost/metric/position/impact guards, `CostModel` degenerate-input guards, `statistics.multiple_testing_correction(alpha=...)` guard — already implemented at statistics.py:407-438, `_adv_for_symbol` degenerate-input guards — closed this session).
- Do not use `--cov=<dotted.module>` (aborts collection with `ImportError: cannot load module more than once per process`); use `--cov=qtr`.
- Do not trust a handoff's pass/fail/coverage counts — the Cycle-175 handoff claimed 100% / 336-formatted while the imported tree was 99.56% / 335-formatted. Re-run the gates.