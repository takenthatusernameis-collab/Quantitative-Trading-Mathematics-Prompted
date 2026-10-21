# HANDOFF — H45 complete (session handoff)

## What changed

**H45:** the package's public API is declared, complete and non-vacuously pinned.

- `src/qtr/utils/__init__.py` — **new**. A regular package with explicit re-exports
  (`get_config`, `load_config`, `save_config`) and an `__all__`. This closes the packaging
  hole: `qtr.utils` was a *namespace* package that `setuptools.find_packages(where="src")` did
  not discover.
- `src/qtr/backtest/__init__.py`, `src/qtr/data/__init__.py`, `src/qtr/tracking/__init__.py` —
  were **empty**; now carry explicit re-exports of each module's public API plus an `__all__`,
  matching the convention already used by `qtr/strategies/__init__.py` and
  `qtr/validation/__init__.py`.
- `src/qtr/__init__.py` — now composes `__all__` from the subpackages' own `__all__` lists.
  The star import exports **46 names** plus `__version__` (was: 1).
- `tests/test_public_api_contract.py` — **new**, 33 tests.
- `FINAL_REPORT.md` — new §H45 section, updated `Summary statistics` and `Next task`; the
  H40-era `Next Task` section is marked superseded; `NEXT_TASK.md`; the `HANDOFF*` files.

## What was actually verified

- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` → **1263 passed,
  1 skipped**; `src/qtr` = **1038 statements, 316 branches, 0 missed, 0 partial, 100.00%**; the
  committed gate reports *"Required test coverage of 100.0% reached. Total coverage: 100.00%"*.
- **Negative control**: the new module run against the **pre-H45** sources
  (`git checkout -- src/qtr/`, `src/qtr/utils/__init__.py` removed) → **15 of 33 tests fail**,
  each naming one defect. The contract is not vacuous.
- `python -m pytest -q -W error tests/test_public_api_contract.py` → **33 passed**.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **88 files already formatted**.
- `setuptools.find_packages(where="src")` → now includes `qtr.utils` (7 packages, was 6).
- A wheel was built and installed into an isolated target: it contains `qtr/utils/__init__.py`,
  and from the **installed** package `from qtr import *` exports the same 46 names.

## What remains unresolved

- The **committed** `src/qtr.egg-info/` manifest is stale (it predates eight test modules added
  since H33). Regenerating it with the setuptools available here (68.1.2) would *degrade* the
  committed `PKG-INFO` (it emits `Metadata-Version: 2.1` and drops the `Requires-Dist`
  entries), so the generated metadata was left untouched. It is regenerated on every build and
  does not affect the wheel, which was verified directly.
- H9's published OOS Sharpe is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict cannot move (REJECT on the profit factor, 55× margin over its 1.0 gate).
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified
  families' numbers and verdicts are frozen.

## Approaches already tried / failed (and why)

- **Regenerating `src/qtr.egg-info/` with the local setuptools** — rejected: setuptools 68.1.2
  writes `Metadata-Version: 2.1` and drops the core `Requires-Dist` entries, which is a
  *regression* in the committed metadata. The stale manifest is a pre-existing cosmetic issue,
  not a packaging defect (the build regenerates it), and it is not worth degrading real
  metadata over.
- **Using the top-level `__all__` as an explicit list** — rejected in favour of composing it
  from the subpackages' `__all__`s, so the aggregate cannot drift from what it aggregates.

## Precise next task

**Extend the executable contract from the package's import surface to the runners' import
surface** — inventory every `run_*.py`'s imports, classify them (library / stdlib /
third-party / local), and pin each class so that a runner importing an undeclared package, or
reaching a symbol the public API does not declare, fails at **test** time rather than at run
time. Full scope and constraints in `NEXT_TASK.md`.
