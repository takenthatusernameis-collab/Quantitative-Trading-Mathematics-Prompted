# HANDOFF — Session 2/3

## What changed this session

H18 prose-grid drift fix + regression pins for H16/H21 (same defect class).

### `run_h18_overnight_intraday_experiment.py`
- Added module-level constants `EXPERIMENT_NAME = "h18_overnight_intraday"`,
  `EXPERIMENT_DESC` (now carries "6-combo grid (predictor x hold_convention),
  Val-selected, Test-protected, gates per H18 pre-registration"), and
  `PREDICTORS` / `HOLD_CONVENTIONS` lists.
- `main()` now reads `PREDICTORS`/`HOLD_CONVENTIONS` from the module constants
  (single source of truth) and computes `grid_size` as
  `len(PREDICTORS) * len(HOLD_CONVENTIONS)` instead of the hardcoded `6`.
- Logged description in `.experiments/experiments.jsonl` now carries the
  combo count (verified: 3 stale bare records existed before).

### `tests/test_h18_overnight_intraday.py`
- Added `test_experiment_description_matches_pre_registered_grid` to
  `TestPreRegistration` (mirrors the H17/H19/H20/H22/H23/H25 pins).

### `tests/test_h16_factor_timing.py`
- Added `test_experiment_description_matches_pre_registered_grid` to
  `TestPreRegistration` (H16 prose already carried "54-combo" but nothing
  pinned it to the computed grid size).

### `tests/test_h21_futures_tsmom_multicontract.py`
- Added `test_experiment_description_matches_pre_registered_grid` to
  `TestPreRegistration` (H21 prose already carried "16-combo" but nothing
  pinned it to the computed grid size).

## What was actually verified

- `python -m pytest -q` → **541 passed** (was 538; +3 new tests).
- `python -m pytest -W error -q` → 541 passed, no warnings.
- `python -m pytest --cov=qtr --cov-report=term-missing` → 99% coverage
  (only `src/qtr/validation/statistics.py:114` uncovered, pre-existing).
- `python -m ruff check src tests run_*.py` → All checks passed.
- `python -m ruff format --check src tests run_*.py` → 69 files already
  formatted (applied the 3-file diff first).
- `bash -n .github/scripts/*.sh` OK; `bash .github/scripts/test_kilo_progress.sh` OK.
- **Negative test (regression guard):** reverted `run_h18_overnight_intraday_experiment.py`
  to the stale bare prose and confirmed
  `test_experiment_description_matches_pre_registered_grid` FAILS with
  `EXPERIMENT_DESC missing '6-combo'`; restored the fix and it PASSES.
- Same negative test performed for H16 (removing "54-combo") and H21
  (removing "16-combo") — both FAIL as expected, both PASS after restore.

## What remains unresolved

- **H10 prose-grid drift (next task).** `run_h10_intraday_tsmom_pfopt_experiment.py:64`
  `EXPERIMENT_DESC` carries no combo count despite a 13,824-combo grid
  (8-dim: SMOOTH_SPANS × VOL_WINDOWS_LONG × REGIME_SCALING_FLAGS ×
  MIN_TRADE_INTERVALS × TRAILING_MULTS × MAX_HOLD_BARS × VOL_LIMIT_MULTS ×
  VOL_FLOOR_FRACTIONS). `HYPOTHESIS_SPEC.md:881` documents "Full 13,824-combo
  grid". Same defect class, same fix pattern. H10 is a certified PASS edge
  (8/8 gates) so the prose is the first thing an auditor reads.
- `src/qtr/validation/statistics.py:114` is the only uncovered line (pre-existing,
  not introduced this session).

## Which approaches have already failed and why

- No failed approaches this session. The single fix was a text + constant
  refactor with no behavioral change; the runner's numerical output is
  bit-identical because the grid contents are unchanged.