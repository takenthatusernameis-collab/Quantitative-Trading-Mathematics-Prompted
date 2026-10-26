# Next task — run full verification gates after H73

## Status

H73 (hunt H67-H72 defect class in `src/qtr/tracking/experiment.py` and
`src/qtr/utils/config.py`) is COMPLETE with a conclusive negative result:
both files already guard degenerate inputs / have no numeric surface, so no
defect was reproduced and no code change was made. The H67-H72 defect class
(sharpe_ratio, compare_to_benchmark, _vol_scale, momentum_signals, engine
drawdown, fetcher tz) is fully hunted and guarded.

Verified this session:
- `python -m pytest -q -W error tests/test_config.py tests/test_experiment_tracker.py` → 35 passed.
- `python -m ruff check ...` and `ruff format --check ...` on those four files → clean.
- `git status` → clean working tree (HEAD 8e3ce2a). Nothing committed.

## What to do

Run the full verification gates to confirm the package is green and
`src/qtr` stays at 100% branch coverage:

    python -m pytest -q -W error
    python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing
    python -m ruff check src tests run_*.py
    python -m ruff format --check src tests run_*.py

(The full suite previously exceeded a 120s sandbox timeout; allow a longer window.)

## Constraints

- qtr is left **uninstalled** (bare clone) — do not `pip install -e .` unless a test requires it; restore that state if you do.
- Do not modify frozen published numbers/gates under `src/qtr` without re-running pinned contracts (causality / metric agreement / benchmark gate).
- Do not commit unless explicitly asked.
