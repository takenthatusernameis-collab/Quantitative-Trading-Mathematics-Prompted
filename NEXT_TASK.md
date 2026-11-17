# Next task (Cycle 175, 2026-11-17)

## What changed this session
Completed the incomplete HEAD commit (`ae394d6`) on `CostModel` non-mapping `futures_specs` entries — a reproduced runner-reachable defect class (same non-mapping class as Cycles 154 config / 155 EDGAR), reachable through the engine futures path (`engine.py:593` divides by `get_future_contract_multiplier` and charges `future_cost_per_contract`):

- `src/qtr/backtest/engine.py::CostModel.future_cost_per_contract` — a non-mapping `futures_specs[symbol]` entry (list/scalar/str/float) now returns `0.0` (fail-closed: no charge) instead of falling back to the non-zero-cost defaults, which manufactured a silent per-contract cost (measured `9.375` with the class defaults). Dict entries and absent symbols are bit-identical. `get_future_contract_multiplier` already fell back to the instance default via `_as_spec_mapping`; engine.py:513-514 zeroes exposure when the multiplier is not finite-positive, so the end-to-end path stays finite.
- `tests/test_cost_model.py::TestCostModelDegenerateInput` — fixed three slips in the tests committed at `ae394d6`: (1) `cm_bad` now passes `future_contract_multiplier=50.0` (it asserted `50.0` with a default of `1.0`, inconsistent with its own docstring and with the sibling negative control, which expects the instance default `1.0`); (2) removed the `"multiplier" in bad_entry` negative-control block (`in` on `list`/`str` is valid and does not raise; `bad_entry.get("commission")` already raises `AttributeError` for all four non-mapping inputs); (3) the engine-path test's `base` now uses `future_contract_multiplier=50.0` so the valid-spec comparison is bit-identical as its docstring requires.

## What was actually verified (own evidence, live tree, changes uncommitted)
- `python -m pytest -q tests/test_cost_model.py -W error` → **35 passed**
- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py` (337.68s) → **4252 passed, 51 skipped, 0 failed** (was 4 failed before this session), `src/qtr` coverage **100.00%** (1633 stmts / 612 branches / 0 miss)
- `python -m ruff check src tests run_*.py scripts` → **All checks passed**
- `python -m ruff format --check src tests run_*.py scripts` → **336 files already formatted**
- `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.305s < 5s, 10.7MB, 13668 trades)
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → still **applies cleanly** (unchanged)
- `python -m pytest -q tests/test_gates_workflow.py` → **7 failed** (unchanged, maintainer-gated)

## What remains unresolved
- The 7 `tests/test_gates_workflow.py` failures: fix is `patches/0001-gates-workflow-contract-fix.patch`; the agent cannot land it (repo-scoped token has no `workflows` permission; `.github/scripts/kilo-controller.sh` restores `.github/workflows/**` from `origin/main` after every session).
- The changes above (`src/qtr/backtest/engine.py`, `tests/test_cost_model.py`) are **uncommitted** in the working tree — no commit unless explicitly requested.

## One precise next task
**Maintainer (unblocks CI):** apply and push `patches/0001-gates-workflow-contract-fix.patch` on `origin/main`, then `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed). With it applied: **4252 passed, 51 skipped, 0 failed**.
**Agent:** none — `src/qtr` is green at 100% coverage with no evidenced defect remaining; do not make speculative `src/qtr` changes. Act only on a new reproduced, runner-reachable defect (smallest reversible fail-closed fix, tests preserving 100% coverage, then the pinned suite + ruff + perf gate verification).

## Approaches already tried and why they should not be repeated
- Do not edit `.github/workflows/**` or weaken `tests/test_gates_workflow.py` — the failures are the maintainer-gated contract block; the fix is the workflow patch.
- Do not re-audit already-pinned defect classes without new evidence (cache normalization/dedup, config boundaries, EDGAR non-mapping, annualization/`bars_per_year`/`periods_per_year` guards, split/CV operand guards, engine cost/metric/position/impact guards, `CostModel` degenerate-input guards just closed this session).
- Do not use `--cov=<dotted.module>` (aborts collection); use `--cov=qtr`.
