# HANDOFF_CURRENT_SESSION — H45: the package's public API is declared and pinned

## What changed

- `src/qtr/utils/__init__.py` — **new**; a regular package with explicit re-exports and an
  `__all__` (closes the `setuptools.find_packages` discovery hole).
- `src/qtr/backtest/__init__.py`, `src/qtr/data/__init__.py`, `src/qtr/tracking/__init__.py` —
  were empty; now carry explicit re-exports plus an `__all__`.
- `src/qtr/__init__.py` — now composes `__all__` from the subpackages' `__all__` lists; the star
  import exports 46 names plus `__version__` (was 1).
- `tests/test_public_api_contract.py` — **new**, 33 tests.
- `FINAL_REPORT.md` §H45 + updated summary/next-task; `NEXT_TASK.md`; the `HANDOFF*` files.

## What was actually verified

- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` → **1263 passed,
  1 skipped**; `src/qtr` = **1038 statements, 316 branches, 0 missed, 0 partial, 100.00%**.
- **Negative control** against the pre-H45 sources → **15 of 33 tests fail**.
- `python -m pytest -q -W error tests/test_public_api_contract.py` → **33 passed**.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **88 files already formatted**.
- Wheel built and installed into an isolated target → contains `qtr/utils/__init__.py`; the
  installed package's star import exports the same 46 names.

## What remains unresolved

- The committed `src/qtr.egg-info/` manifest is stale; regenerating it with the local
  setuptools 68.1.2 would degrade its `PKG-INFO`, so it was left untouched (pre-existing,
  cosmetic — the build regenerates it).
- H9's sample-convention Sharpe disclosure, and the exhausted H1–H30 hypothesis space, stand.

## Precise next task

Pin the **runners'** import surface with an executable contract (inventory, classify, pin), so
an import-level break in a `run_*.py` fails at test time rather than at run time. Full scope in
`NEXT_TASK.md`.
