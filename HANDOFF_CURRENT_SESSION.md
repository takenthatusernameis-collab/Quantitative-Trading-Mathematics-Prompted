# Current session handoff (Cycle 163, 2026-11-16)

## What changed
- **Hardened the baseline signal layer against degenerate numeric parameters**
  (`src/qtr/strategies/baselines.py`). This is a NEW, reproduced, runner-reachable
  defect class (not previously closed): the signal functions only guarded
  `<= 0` / `< 0`, so a `bool`, a non-integral `float` (`20.5`) or a `nan`/`inf`
  window/span/lookback/skip slipped past and made the pandas call raise an opaque
  `ValueError`/`TypeError`/`OverflowError` from deep inside pandas (reproduced:
  `moving_average_crossover_signals(fast_window=nan)`, `momentum_signals(lookback=inf)`,
  `carry_signals(lookback=20.5)`, etc.). Separately, a negative or non-finite
  `max_position_size` silently inverted/disabled `Series.clip`, so an
  out-of-range signal reached the book uncapped -- the same fail-open the engine
  closes for its own `max_position_size`/`max_leverage` (`engine.py`).
- Added two module-private helpers:
  - `_is_int(value)` -- a real integer window/span/lookback/skip (rejects bool,
    float, str, nan/inf).
  - `_is_finite_non_negative(value)` -- a finite, non-negative cap/scale.
- Applied fail-closed guards (return the same all-zero "no exposure" frame the
  surrounding degenerate guards return) to: `moving_average_crossover_signals`,
  `ewma_crossover_signals`, `momentum_signals` (incl. `n_top`), `mean_reversion_signals`
  (window + `num_std`), `time_series_momentum_signals` (+ cap),
  `vol_scaled_tsmom_signals` (lookback/vol_window/skip + cap), `carry_signals`.
  Every valid input is bit-identical to before.
- Added 67 parametrized tests in `tests/test_baselines_extra.py` covering every
  new guard branch and both helpers.

## What was actually verified (own evidence, this session)
- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py`
  -> **4188 passed, 51 skipped**, `src/qtr` coverage **100.00%**
  (1614 stmts, 598 branches, 0 missing; baselines.py 180 stmts / 94 branches, 0 missing).
- `python -m pytest tests/test_baselines.py tests/test_baselines_extra.py -q` -> **120 passed** (was 53).
- `python -m ruff check src tests run_*.py scripts` -> **All checks passed**.
- `python -m ruff format --check src tests run_*.py scripts` -> **336 files already formatted**.
- `python scripts/backtest_perf_regression_gate.py` -> **PERF GATE PASSED** (0.422s, limit 5s).
- `python -m pytest -q tests/test_gates_workflow.py` -> **7 failed** (unchanged,
  maintainer-gated; expected vs live `.github/workflows/gates.yml`).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` -> applies cleanly.

## What remains unresolved
- **Maintainer-only (unchanged):** `.github/workflows/gates.yml` must be patched/pushed
  with workflow-scoped credentials per `patches/0001-gates-workflow-contract-fix.patch`
  to satisfy `tests/test_gates_workflow.py` (7 tests). The agent cannot land this.
- **Research boundary (unchanged):** H1-H182 exhausted under free/public PIT data;
  no honest H183 without new authorized data.
- **Reproducibility backlog (baseline-frozen, unchanged):** `missing_files=197`,
  `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=0`.

## Approaches already failed / not to repeat
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or alter
  frozen contracts/gates/artifacts/verdicts/thresholds/numbers from the agent.
- Do not re-audit already-pinned defect surfaces (cache index/column normalization,
  config boundaries, EDGAR non-mapping handling, annualization/`sharpe_ratio` guards,
  split/CV operand guards, engine cost/metric guards) without NEW evidence.
- Do not hunt/speculate for new `src/qtr` defects without a fresh, concrete,
  runner-reachable reproduction.
- Do not invent a free-data H183 or treat parameter/timeframe/universe/close-substitute
  variations as new mechanism families.

## One precise next task
- **Maintainer (preferred, unblocks CI):** apply and push
  `patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then run
  `python -m pytest -q tests/test_gates_workflow.py` on `origin/main` (expect 7 passed).
- **Agent alternative (only with new evidence):** if a new concrete, reproduced,
  runner-reachable defect appears in `src/qtr`, runners, or corpus metadata, implement
  the smallest reversible fix, add/adjust tests preserving 100% `src/qtr` coverage, and
  verify with `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
  --ignore=tests/test_gates_workflow.py`, `python -m ruff check src tests run_*.py scripts`,
  `python -m ruff format --check src tests run_*.py scripts`, and
  `python scripts/backtest_perf_regression_gate.py` (own evidence required).

**Working-tree note:** these changes are staged in the working tree but NOT committed
(no explicit commit request). Files changed: `src/qtr/strategies/baselines.py`,
`tests/test_baselines_extra.py`.

**Constraints:** no gate weakening; no modification of published/frozen artifacts,
verdicts, thresholds, or frozen numbers except deliberate authorized corpus/baseline
updates; no workflow commit from agent.

(End of file - total 60 lines)