# Next task (set by this session, Cycle 173, 2026-11-16)

## What changed this session
- **Fixed a reproduced runner-reachable defect:** `walk_forward_splits` in
  `src/qtr/validation/statistics.py` guarded finiteness of `n_samples`,
  `n_splits`, `train_ratio`, `gap` but not **integrality**. A non-integer
  `n_splits` (e.g. `5.0`, `2.5`) or `gap`/`n_samples` reached
  `range(n_splits)`/`np.arange` and crashed with
  `TypeError: 'float' object cannot be interpreted as an integer` instead of
  failing closed to `[]`. Its siblings `purged_kfold_splits` and
  `combinatorial_purged_cv` already reject non-integer operands via
  `_purged_cv_operands_valid`; `walk_forward_splits` was the inconsistent
  site. Fix: added an `isinstance(v, (int, np.integer)) and not isinstance(v,
  bool)` guard for `(n_samples, n_splits, gap)` (fail closed to `[]`),
  leaving `train_ratio` (a fraction) untouched. Clean/int/np.integer paths are
  bit-identical.
- **Tests:** `tests/test_statistics.py::TestWalkForwardSplits` —
  `test_walk_forward_splits_rejects_non_integer_operands` (parametrized
  floats/bools/np.float64 for `n_samples`, `n_splits`, `gap` all `[]`),
  `test_walk_forward_splits_accepts_integer_and_np_integer` (int/np.integer
  clean path unchanged, bit-identical), and
  `test_walk_forward_splits_non_integer_contract_rejects_pre_fix` (negative
  control: pre-fix `range(float("nan"))` raises `TypeError`; the fixed
  function returns `[]`). +3 tests.

## What was actually verified (own evidence, live tree @ HEAD 229f491)
- Repro before fix: `walk_forward_splits(10, n_splits=5.0)` → `TypeError` at
  `statistics.py:331`; after fix → `[]`. Bool/np.float64 variants also `[]`;
  `walk_forward_splits(100, n_splits=5)` → 5 splits unchanged.
- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py` (334.98s) → **4241 passed, 51 skipped, 0 failed**, `src/qtr` coverage **100.00%** (1624 stmts / 608 branches / 0 miss).
- `python -m pytest -q tests/test_statistics.py -W error` → **320 passed**.
- `python -m ruff check src tests run_*.py scripts` → **All checks passed**.
- `python -m ruff format --check src tests run_*.py scripts` → **336 files already formatted**.
- `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.322s < 5s, 10.7MB, 13668 trades).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → still **PATCH_APPLIES_CLEANLY** (unchanged, maintainer-gated).
- `python -m pytest -q tests/test_gates_workflow.py` → **7 failed** (unchanged; maintainer-gated, fix is the workflow patch — no agent workflow commit).

## Known unresolved (unchanged)
- Maintainer-only workflow patch for `.github/workflows/gates.yml`;
  `tests/test_gates_workflow.py` red by design until the maintainer applies
  `patches/0001-gates-workflow-contract-fix.patch`.
- H1–H182 exhausted under free/public PIT data (no honest H183 without new
  authorized data); reproducibility backlog baseline-frozen at Recoverable 0 /
  Excluded 172 / Unrecoverable 25.

## Approaches already tried and why they should not be repeated
- Do not re-audit/close already-pinned defects without new evidence
  (cache-hit/fresh-fetch normalization+dedup, config boundaries/degenerate
  guards, EDGAR non-mapping handling, annualization/`bars_per_year`/
  `periods_per_year`/`risk_free` guards, split/CV operand guards, engine
  cost/metric/position guards, baselines target_vol guard, sidecar schema
  backfill, H182 runner, `statistics.py` operand guards incl. MTC `alpha`,
  and now `walk_forward_splits` integrality).
- Do not make speculative `src/qtr` changes absent a reproduced,
  runner-reachable defect.
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`,
  or alter coverage/frozen-contract gates or published/frozen artifacts/
  verdicts/thresholds/frozen numbers.
- Do not invent a free-data H183 or treat parameter/timeframe/universe/
  close-substitute variations as new mechanism families.
- Do not use `--cov=<dotted.module>` (aborts collection); use `--cov=qtr`.

## One precise next task
**Maintainer (preferred, unblocks CI):** apply and push
`patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then
`python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on
`origin/main`.

**Agent alternative (only with new evidence):** reproduce a concrete,
runner-reachable defect in `src/qtr` (not already pinned/closed above) and,
if real, fix it with the smallest reversible fail-closed change, tests
preserving 100% `src/qtr` coverage, and verification via:
- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py`
- `python -m ruff check src tests run_*.py scripts`
- `python -m ruff format --check src tests run_*.py scripts`
- `python scripts/backtest_perf_regression_gate.py`

**Constraints:** no gate weakening; no modification of published/frozen
artifacts, verdicts, thresholds, or frozen numbers except deliberate
authorized corpus/baseline updates; no workflow commit from agent.
