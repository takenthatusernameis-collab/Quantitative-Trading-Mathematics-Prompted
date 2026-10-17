# Handoff Summary

## Current state
- All tests pass: 521 passed, 1 warning (unrelated scipy numerical warning).
- Changes this session:
  - src/qtr/tracking/experiment.py — replaced deprecated `pkg_resources` with stdlib
    `importlib.metadata` in `_get_dependencies` (verified equivalent output, 127 entries).
  - tests/test_experiment_tracker.py — updated failure-simulation test to block
    `importlib.metadata` instead of `pkg_resources`.
- Lint clean, format clean, coverage on experiment.py = 100%.
- Prior parquet-helper task (tests/_utils_parquet.py) confirmed complete: used by all
  15 test files reading parquet artifacts; no direct pd.read_parquet calls remain.

## Next agent actions
No pending task. If assigned a new task, verify with `python -m pytest -q`,
`python -m ruff check src tests run_*.py`, and `python -m ruff format --check`.
Note: `qtr` must be importable — run `pip install -e .` from the repo root if
`ModuleNotFoundError: No module named 'qtr'` appears at collection time.