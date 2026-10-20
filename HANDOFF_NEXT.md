# HANDOFF_NEXT — all runners covered (remaining-runner extension complete)

## What changed (this session)

1. **`tests/test_runner_causality_inventory.py`** — extended the point-in-time
   invariant to the last nine runners:
   `run_experiment.py`, `run_baseline.py`, `run_param_sweep.py`,
   `run_alternatives.py`, `run_h13_oos_deflation_pf_audit.py`,
   `run_h14_pf_margin_selection_audit.py`, `run_h25_pf_robustness.py`,
   `run_h26_sharpe_scale_audit.py`, `run_h28_causal_recertification.py`.
   All 48 of their module-level functions are classified `static` with a
   written argument (they compose imported frozen pipelines or audit committed
   artifacts; none builds a position series inline). `run_h26`'s single
   `resample("1D")` collapse site is pinned in `RESAMPLE_SITES`. No probe
   cases, `KNOWN_LOOKAHEAD_CASES` or `INHERITED_LOOKAHEAD` entries were
   added or changed. Every `run_*.py` in the repository (32 files) is now in
   scope.

2. **`src/qtr/backtest/engine.py:317`** — the annualized return now guards a
   non-positive equity base (returns -1.0 instead of raising
   `RuntimeWarning: invalid value encountered in scalar power` under `-W
   error` when the dense sweep drives equity to zero or below). One line +
   guard; engine.py stays at 100% coverage and the branch is exercised by the
   existing dense-sweep tests.

3. **`tests/test_data_fetcher.py`** — new test
   `test_fetch_sp500_constituents_rejects_date` covering the `ValueError`
   branch of `fetch_sp500_constituents(date=...)` (the footgun from the
   earlier record is already closed in code: a historical date raises loudly).
   `src/qtr` coverage is now **100%** (1014/1014 statements).

## What was actually verified

- `python -m pytest -q -W error` → **1102 passed, 1 skipped**.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `src/qtr` coverage **100%** (`--cov=qtr --cov-report=term-missing`).
- No published artifact, gate threshold, verdict, certified number or
  published row modified; no grid re-run; no hypothesis added.

## Predictor-timing audit

Every H29-CAUSAL family predictor is probed clean; the nine runners added this
session call only pinned constructors. **No same-bar-close predictor** (the
H37/P3 class) was found in any remaining runner; all disclosures remain
bounded against the committed artifacts as P3 is.

## What remains unresolved

- `qtr/backtest/engine.py`: `metrics["total_return"]` excludes the first bar's
  return while `annualized_return` counts it (~a few bps; disclosure only --
  values are in published artifacts; the carried-forward constraints forbid
  rewriting them).

## Approaches already tried / failed (this session)

- None: the runner inventory, the static sweep, the `-W error` blocker (fixed
  at the root cause in the engine) and the coverage gap all resolved on the
  first attempt.

## Precise next task (one task)

**None for the invariant:** all 32 `run_*.py` files are covered, every
module-level function is classified and pinned, and the suite is green under
`-W error`. If a future session wants one bounded item, it is the engine's
`metrics["total_return"]` inconsistency disclosed above (a few bps; values in
published artifacts -- only addressable if the record is rewritten, which the
constraints currently forbid).
