# Next task (set by this session, Cycle 174, 2026-11-17)

## What changed this session
- **Fixed a reproduced runner-reachable fail-open:** `run_backtest` in
  `src/qtr/backtest/engine.py` charges market impact in a *separate* loop from
  `CostModel.equity_cost_bps`:
  `impact_cost[sym] = position_change[sym].abs() * (equity_impact_bps_per_pct_adv
  * participation / 1e4)`. `CostModel.equity_cost_bps` already fails closed
  (returns `0.0`) on a negative or non-finite `equity_impact_bps_per_pct_adv`
  (a cost is a *charge*), but this loop read the raw attribute and bypassed it:
  a **negative** coefficient produced a *negative* cost that
  `portfolio_ret = ... - costs` **adds** (manufactured P&L; measured: entry-bar
  return `-0.0012` → `+0.0010`, trade cost `-0.001`); **`±inf`** made the
  return `±inf` while the metrics silently degraded; **`nan`** (truthy) poisoned
  the cost sum and the charge was silently dropped. Fix: normalize the
  coefficient to `0.0` (no-impact boundary) when non-finite or negative, before
  the loop. Finite non-negative values are bit-identical.
- **Tests:** `tests/test_engine_edge_stress.py::TestInvalidEquityImpactCoefficient`
  (+7) — parametrized `-10.0 / -0.001 / ±inf / nan` (finite, no negative cost,
  non-positive entry-bar return), a finite-positive `10.0` control (unchanged),
  and a behavioural negative control reconstructing the pre-fix negative-cost
  arithmetic.

## What was actually verified (own evidence, live tree @ HEAD e585cbc + this change)
- Repro before fix: `-10` coefficient → entry-bar return `+0.0010`, trade cost
  `-0.001`; `inf`/`-inf` → `returns[0] == ±inf`; `nan` → cost `NaN`. After fix
  all finite, no negative cost, entry-bar return `<= 0`.
- Negative control (`git stash push -- src/qtr/backtest/engine.py`) → **6 failed
  / 1 passed** on the new class; restored → **7 passed**.
- `python -m pytest -q tests/test_engine_edge_stress.py tests/test_cost_model.py tests/test_backtest_engine.py -W error` → **149 passed**.
- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py` (335.50s) → **4248 passed, 51 skipped, 0 failed**, `src/qtr` coverage **100.00%** (1627 stmts / 610 branches / 0 miss).
- `python -m ruff check src tests run_*.py scripts` → **All checks passed**.
- `python -m ruff format --check src tests run_*.py scripts` → **336 files already formatted**.
- `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.280s < 5s, 10.7MB, 13668 trades).
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
  cost/metric/position guards **including the new `equity_impact_bps_per_pct_adv`
  normalization**, baselines target_vol guard, sidecar schema backfill, H182
  runner, `statistics.py` operand guards incl. MTC `alpha` and
  `walk_forward_splits` integrality).
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