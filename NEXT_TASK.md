# NEXT_TASK.md — Session Follow-up

## What changed (this session)
- Added `tests/test_experiment_tracker.py` (11 tests) for `ExperimentTracker` in `src/qtr/tracking/experiment.py` — covers start/finish, metric logging, artifact logging, dataframe, load/list, singleton; coverage 52%->70%.

## What was verified
- `PYTHONPATH=src python -m pytest tests/test_experiment_tracker.py -q` → 11 passed.
- `python -m ruff check` / `ruff format --check` clean.

## Remaining work (bounded)
- Backtest engine (`src/qtr/backtest/engine.py`) coverage unmeasured; add deterministic tests.
- Fetcher (`src/qtr/data/fetcher.py`) 33% network I/O; add mocked tests if desired.
- ExperimentTracker uncovered branches (62-68, 81-117 etc.) remaining.
