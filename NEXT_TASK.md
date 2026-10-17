# NEXT_TASK.md — Session Follow-up

## What changed (this session)

- Added 5 deterministic tests to `tests/test_experiment_tracker.py`,
  closing the last uncovered lines in `src/qtr/tracking/experiment.py`
  (97% → **100%**): missing-log and no-match paths in `load_experiment`,
  empty-log path in `list_experiments`, and the JSON fallback in
  `record_artifact` for non-standard types.
- Added 15 mocked (no-network) tests to `tests/test_data_fetcher.py`,
  raising `src/qtr/data/fetcher.py` from 58% → **100%**: yahoo/futures/ccxt
  success, cache-hit, empty-result, fetch-exception, missing-column-warning,
  cache-write, and sp500 Wikipedia + fallback paths, plus the
  `get_data_fetcher` singleton.

## What was verified

- `PYTHONPATH=src python -m pytest -q` → **520 passed, 1 failed** (~206 s).
- `python -m ruff check src tests run_*.py` / `ruff format --check` → clean.
- Coverage: `experiment.py` 100%, `fetcher.py` 100%; all `src/qtr` modules
  now ≥99% (`backtest/engine.py` 99% — 1 unreachable else-branch for
  non-standard asset classes).
- The single failure is pre-existing and unrelated: it fails identically on
  a clean `git stash` of this branch.

## Remaining work (bounded)

- Fix `tests/test_h18_overnight_intraday.py::test_weight_bounds` — a
  `fastparquet` bug (`api.py:834` calls `.endswith` on a `numpy.int64` column
  name). Options: pin a newer `fastparquet` in `requirements.txt`, or
  rewrite the test to avoid integer column names. Verify on a clean
  checkout before committing.
- Changes are uncommitted; commit when instructed.

## Next precise task

Commit the pending test additions, then attempt the bounded fastparquet fix
above. If it proves non-trivial, document it in the handoff and stop — the
`src/qtr` coverage goal is complete.

(End of file)