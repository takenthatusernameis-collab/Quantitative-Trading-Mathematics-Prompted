# NEXT_TASK.md — Session Follow-up

## What changed (this session)
- Added coverage tests for `src/qtr/backtest/engine.py` covering volumes/ADV paths, ADV edge cases (zero, symbol present), and crypto cost path; backtest engine coverage now ~99% (remaining: 1 line in else branch for non-standard asset classes; hard to trigger meaningfully without expanding enum).
- Formatted tests to satisfy ruff.

## What was verified
- `PYTHONPATH=src PATH=$PATH:/home/runner/work/_temp/kilo-home/.local/bin python -m pytest tests/test_backtest_engine.py tests/test_baselines.py tests/test_config.py tests/test_statistics.py tests/test_experiment_tracker.py tests/test_baselines_extra.py -q` → 143 passed.
- `python -m ruff check src tests run_*.py` / `ruff format --check` → clean.

## Remaining work (bounded)
- Consider small coverage improvements in `src/qtr/tracking/experiment.py` (3-5 lines, mostly exception/load paths already exercised; remaining around 267, 273, 335-337 appear hard to hit without contrived conditions but we added comprehensive tests).
- Fetcher (`src/qtr/data/fetcher.py`) has network I/O; mock tests optional and time-boxed.
- No other untested high-value pure-logic modules obvious from prior inspection.

## Next precise task
Option 1: Add targeted mocked tests for `src/qtr/data/fetcher.py` where safe (avoid real network). Focus on error handling and parsing logic that can be unit-tested. Time-box to small scope.
Option 2: If fetcher mocking is complex, prepare final handoff documenting completed coverage work. Given session goals prioritize durable verified progress.
