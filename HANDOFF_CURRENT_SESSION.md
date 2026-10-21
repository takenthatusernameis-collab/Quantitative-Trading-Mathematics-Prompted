# HANDOFF_CURRENT_SESSION — H44: package convenience exports

## What changed

- `src/qtr/__init__.py` — populated with package docstring, `__version__`, and wildcard re-exports from subpackages for convenience.

## What was actually verified

- `PYTHONPATH=src python -c "from qtr import *; print('ok')"` → `ok`
- `python -m ruff check src tests run_*.py` → *All checks passed!*
- `python -m ruff format --check src tests run_*.py` → **86 files already formatted**

## What remains unresolved

None introduced by this change.

## Precise next task

Review if any subpackage `__init__.py` files would benefit from more explicit `__all__` definitions or improved exports. (Low priority; current state is clean.)
