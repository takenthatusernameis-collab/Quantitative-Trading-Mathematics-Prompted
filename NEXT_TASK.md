# NEXT TASK

Status: IN PROGRESS — Session 20 completed a real task the prior handoff wrongly declared done.

## Current state

- HEAD `ddd49c5` on `main`, in sync with `origin/main`.
- **Uncommitted** Session 20 changes (verified, ready to commit):
  - `src/qtr/validation/statistics.py` — `sharpe_ratio` zero-variance guard fix (`== 0` → `<= 1e-15`).
  - `tests/test_statistics.py` — new 59-test regression suite (all 12 public functions).
  - `.gitignore` — added `.coverage`, `coverage.xml`.
- `pytest -q` -> **418 passed** (was 359).
- `ruff check src tests run_*.py` -> All checks passed.
- `ruff format --check src tests run_*.py` -> 62 files formatted.
- Coverage: `statistics.py` 12% -> 100%; repo total 42% -> 60%.

## Precise next task

1. Commit the Session 20 changes above (verified; commit-per-change convention).
2. Add regression tests for remaining sub-60% `src/qtr` modules, in priority order:
   - `src/qtr/utils/config.py` (52%, pure logic — easiest, highest value)
   - `src/qtr/strategies/baselines.py` (22%)
   - `src/qtr/tracking/experiment.py` (34%)
   Skip `src/qtr/data/fetcher.py` (33%, network I/O — not deterministically testable).

## Evidence

The prior "no bounded task remains" claim was falsified by coverage measurement:
`src/qtr/validation/statistics.py` was at 12% with 11 of 12 functions untested,
despite being imported by every H1-H25 runner (`run_baseline.py`,
`run_cs_momentum_experiment.py`, `run_ddcv_experiment.py`, `run_experiment.py`,
`run_futures_tsmom_experiment.py`, `run_h10_intraday_tsmom_pfopt_experiment.py`,
`run_h11_robustness_experiment.py`, `run_h12_selection_bias_audit.py`,
`run_h14_pf_margin_selection_audit.py`, `run_h16_factor_timing_experiment.py`,
...). A hidden bug in `sharpe_ratio` (exact `== 0` std guard) was found only
after writing tests against constant-return inputs.

## Constraints

- Do not accept a handoff's "nothing to do" claim without independent verification.
- `src/` changes minimal and evidence-justified.
- Free-data hypothesis space (H1-H25) exhausted; paid data out of scope.
- Commit-per-experiment; bytecode and caches gitignored.
- Reconcile remote changes; verify persistence before declaring done.

(End of file)