# HANDOFF_NEXT — H45: the package's public API is declared, complete and pinned

## What changed (this session)

- `src/qtr/utils/__init__.py` — **new**. A regular package with explicit re-exports
  (`get_config`, `load_config`, `save_config`) and an `__all__`.

  This closes a **packaging hole**. `src/qtr/utils/` had **no** `__init__.py`, so it was a PEP 420
  *namespace* directory rather than a package, and `setuptools.find_packages(where="src")`
  returned six packages with **`qtr.utils` missing**:

  ```
  ['qtr', 'qtr.strategies', 'qtr.tracking', 'qtr.backtest', 'qtr.data', 'qtr.validation']
  ```

  The distribution shipped `qtr/utils/config.py` only because setuptools copies the stray file
  as package data, and it was importable only by PEP 420 luck — and because
  `qtr/__init__.py` imports it, the **whole package** was one directory away from failing to
  import.
- `src/qtr/backtest/__init__.py`, `src/qtr/data/__init__.py`, `src/qtr/tracking/__init__.py` —
  were **empty** files; now carry explicit re-exports of each module's public API plus an
  `__all__`, matching the convention already used by `qtr/strategies/__init__.py` and
  `qtr/validation/__init__.py`. Before this, four of the six subpackages exported nothing:
  `qtr.run_backtest`, `qtr.get_data_fetcher`, `qtr.create_experiment` and `qtr.get_config` did
  not exist.
- `src/qtr/__init__.py` — now composes `__all__` **from the subpackages' own `__all__` lists**,
  so the aggregate cannot drift from what it aggregates. The star import exports **46 names**
  plus `__version__` (was: **1**).
- `tests/test_public_api_contract.py` — **new**, 33 tests.
- `FINAL_REPORT.md` — new §H45 section; updated `Summary statistics` (test tally, coverage
  bullet) and the closing `Next task`; the H40-era `Next Task` section is marked superseded;
  `NEXT_TASK.md`; the `HANDOFF*` files.

## The defect this found

H44 added "convenience exports" to the top-level `qtr` package and recorded the verification as

```
PYTHONPATH=src python -c "from qtr import *; print('ok')"   ->   ok
```

That check is **vacuous**: `from qtr import *` succeeds whether it exports zero names or five
hundred, and `print('ok')` prints `ok` either way. It is the same defect class this record has
been hunting since §H35 — **a check that cannot fail is not a check**. Measuring the surface the
check was supposed to certify found three separate defects: the one-name `__all__`, the empty
subpackage `__init__.py` files, and the namespace-package `qtr.utils`.

## The contract

`tests/test_public_api_contract.py` pins the surface in five layers:

1. **Packaging** (3) — every subpackage is a regular package and is discovered by the build
   backend.
2. **Declaration** (22) — every subpackage declares an explicit, non-empty, duplicate-free
   `__all__`; no subpackage uses a star import; and each subpackage's `__all__` is **exactly**
   the public API of the module it re-exports, computed from the AST (so a new public function
   nobody exports fails, and so does an export of a name that does not exist).
3. **Aggregation** (2) — the top-level `__all__` is the union of the subpackages' `__all__`s
   plus `__version__`; every declared name is bound at runtime.
4. **The star import** (3) — `from qtr import *` exports **exactly** the declared API, the
   declared API is not a one-name set, and the star import reaches a representative of every
   subpackage.
5. **Version** (1) — `qtr.__version__` equals the version the distribution ships.

## What was actually verified

- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` → **1263 passed,
  1 skipped**; `src/qtr` = **1038 statements, 316 branches, 0 missed, 0 partial, 100.00%**; the
  committed gate reports *"Required test coverage of 100.0% reached. Total coverage: 100.00%"*.
- **Negative control** — the new module was run against the **pre-H45** sources (`git checkout --
  src/qtr/`, `src/qtr/utils/__init__.py` removed): **15 of the 33 tests fail**, each naming one
  of the defects above. The contract is not vacuous.
- `python -m pytest -q -W error tests/test_public_api_contract.py` → **33 passed**.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **88 files already formatted** (87 + the new
  test module).
- `setuptools.find_packages(where="src")` → **7 packages, `qtr.utils` present** (was 6).
- A wheel was built (`pip wheel --no-deps --no-build-isolation`) and installed into an isolated
  target: the wheel now contains `qtr/utils/__init__.py`, and from the **installed** package
  `from qtr import *` exports the same 46 names, with `qtr.utils` a regular package.

## What remains unresolved (disclosures, not rewrites)

- The **committed** `src/qtr.egg-info/` manifest is stale (it predates eight test modules added
  since H33). Regenerating it with the setuptools available in this session (68.1.2) would
  *degrade* the committed `PKG-INFO` — it emits `Metadata-Version: 2.1` and drops the core
  `Requires-Dist` entries — so the generated metadata was left untouched. It is regenerated on
  every build and does not affect the wheel, which was verified directly.
- H9's published OOS Sharpe is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict cannot move (REJECT on the profit factor, 55× margin over its 1.0 gate).
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified
  families' numbers and verdicts are frozen.

## Approaches already tried / failed (and why)

- **Regenerating `src/qtr.egg-info/` with the local setuptools** — rejected: setuptools 68.1.2
  writes `Metadata-Version: 2.1` and drops the core `Requires-Dist` entries, which is a
  *regression* in the committed metadata. The stale manifest is pre-existing and cosmetic (the
  build regenerates it); it is not worth degrading real metadata over.
- **An explicit top-level `__all__` list** — rejected in favour of composing it from the
  subpackages' `__all__`s, so the aggregate cannot drift from what it aggregates.

## Precise next task

**Extend the executable contract from the package's import surface to the runners' import
surface.** Inventory every `run_*.py`'s imports, classify them (library / stdlib / third-party /
local), and pin each class so that a runner importing an undeclared package, or reaching a
symbol the public API does not declare, fails at **test** time rather than at run time; and
assert that every runner is importable. Full scope and constraints in `NEXT_TASK.md`.

The state a next session inherits:

- The pre-registered free-data hypothesis space (H1–H30) remains **exhausted**; no new
  hypothesis is warranted and no grid may be re-run.
- Every published artifact, threshold, verdict and certified number is frozen.
- The shared library, the engine **and every `run_*.py`** remain pinned as **point-in-time**;
  re-run `tests/test_causality_invariant.py` after any change under `src/qtr`,
  `tests/test_runner_causality_inventory.py` after any change in a runner, and
  `tests/test_public_api_contract.py` after any change under `src/qtr`.
