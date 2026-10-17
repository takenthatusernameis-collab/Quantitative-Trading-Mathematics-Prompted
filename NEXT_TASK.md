# NEXT_TASK.md — Session Follow-up

## What changed (this session)
- Added `tests/test_config.py` (15 tests) for `src/qtr/utils/config.py` — covers load/get/save paths, env overrides, caching; config now 100% covered.
- Added `tests/test_baselines.py` (14 tests) and `tests/test_baselines_extra.py` (6 tests) for `src/qtr/strategies/baselines.py` — covers all strategies, registry, get/run; baselines now 97% covered (5 edge lines remain).
- Extended `src/qtr/tracking/experiment.py` with simple `Experiment` class and `create_experiment()` API to match existing test interface; also preserves `ExperimentTracker` etc. Added `tests/test_experiment_tracking.py` (13 tests). Lint/format clean.

## What was verified
- `python -m pytest tests/test_baselines.py tests/test_baselines_extra.py tests/test_config.py tests/test_statistics.py tests/test_experiment_tracking.py -q` → **107 passed**, 1 warning (all deterministic).
- `python -m ruff check src tests run_*.py` → All checks passed.
- `python -m ruff format --check src tests run_*.py` → Clean.

## Remaining work (bounded)
- Improve coverage for remaining low-coverage modules (e.g. `src/qtr/tracking/experiment.py` still has uncovered branches; `src/qtr/data/fetcher.py` 33% network I/O heavy - better to add mocked tests if desired).
- Or continue adding focused regression tests for next sub-60% modules following the same pattern (deterministic, minimal changes).
