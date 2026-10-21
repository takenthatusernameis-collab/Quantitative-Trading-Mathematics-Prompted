# HANDOFF — H44 complete (session handoff)

## What changed
**H44:** Added convenience exports to top-level `qtr` package.

- `src/qtr/__init__.py` — added `__version__`, package docstring, and wildcard re-exports from subpackages.

## What was actually verified
- `PYTHONPATH=src python -c "from qtr import *; print('ok')"` → `ok`
- `python -m ruff check src tests run_*.py` → *All checks passed!*
- `python -m ruff format --check src tests run_*.py` → **86 files already formatted**

## What remains unresolved
- None introduced. Previous H43 items (coverage gate at 100%) remain resolved.

## Precise next task
No assigned task. Optionally expand top-level exports with explicit symbols if API ergonomics matter; not critical.
