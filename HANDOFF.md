# HANDOFF — H66 complete (the `fetcher()` CCXT branch forwarded the wrong default)

## What changed (H66)

No hypothesis task was assigned and the H1–H30 space is exhausted, so the session inspected the
most recent change (§H65's `fetcher()` dispatch entry point) for a defect of the same class as the
ones that produced it — a pinned contract that passes while the thing it makes reachable does not.
It found one in the CCXT branch.

- `src/qtr/data/fetcher.py` — `fetcher` now carries its own `timeframe: str = "1h"` parameter and
  forwards *that* into the CCXT branch. Before the fix the CCXT branch forwarded the dispatcher's
  `interval` parameter (default `"1d"`) into `fetch_ccxt`'s `timeframe` slot, whose own default is
  `"1h"`, so `fetcher("ccxt", ...)` with defaults was **not** the same call as `fetch_ccxt(...)`
  — hourly bars requested as daily ones. The yahoo and futures branches forwarded `interval`
  unchanged and are bit-identical to before; only the CCXT default call moved.
- `tests/test_data_fetcher.py` — **3 tests added** (38, was 35): the CCXT dispatch-equality test
  now passes an explicit `timeframe` on both sides so it pins the *forwarding* rather than leaving
  it at the dispatcher's default; a recording CCXT stub proves the default call forwards `"1h"`;
  and a behavioural negative control reconstructs the pre-fix forwarding and requires it to
  differ from the corrected default.

The defect was invisible to the inherited dispatch-equality test because the fake exchange's
`fetch_ohlcv` ignored `timeframe` entirely, so both sides returned the same frame.

No published artifact, gate threshold, verdict or certified number was changed; no grid was
re-run; no hypothesis was added.

## What was actually verified

- The two new tests **fail on the pre-fix code** (reverted dispatcher:
  `TypeError: fetcher() got an unexpected keyword argument 'timeframe'`), then pass with the fix.
- `python -m pytest -q -W error` → **2 089 passed, 16 skipped** (was 2 087; the 16 skips are
  unchanged and all intentional/self-declaring).
- `python -m pytest -q --cov=qtr --cov-branch` → `src/qtr` = **1 102 statements, 338 branches,
  0 missed, 0 partial, 100.00%** (unchanged).
- `python -m ruff check src tests run_*.py` → *All checks passed!*; `python -m ruff format --check
  src tests run_*.py` → **103 files already formatted**.
- `tests/test_data_fetcher.py` → **38 passed**; `tests/test_public_api_contract.py` → **33 passed**;
  `tests/test_ruff_reproducibility.py` → **2 passed**.

## What remains unresolved

All remaining items in `FINAL_REPORT.md` §H53–§H61 are **disclosed, not quantified** — each
depends on an input the record does not hold, and none can be resolved without new committed
inputs. The thirteen H58/H59 gate booleans stay as published (all in REJECT families; no certified
verdict moves). H1–H30 exhausted; certified families frozen.

## Precise next task

**None assigned.** The H47–H66 series is complete. If a session wants work, the only honest
options are (a) wait for newly committed artifacts that make a disclosed value measurable, or
(b) after any change under `src/qtr`, re-run the pinned contracts -- including
`test_engine_metric_agreement.py`, `test_h53_published_metrics_disclosure`,
`test_h54_non_metrics_block_disclosure`, `test_h55_nested_metrics_disclosure`,
`test_h56_stats_json_echoes`, `test_h57_total_return_audit`, `test_h58_price_pathology_contamination`
and `test_h59_contamination_gate_blast_radius` -- and confirm the gates stay green. In addition,
verify the quick-start surface by running the suite from a fresh venv with only
`pip install -r requirements.txt`, since `requirements.txt` is now the contract that must declare
every dependency a pinned contract test or a documented gate imports (currently
`setuptools>=68`, `pyarrow>=14.0.0` and `ruff>=0.6.0`).

---

## What changed (H65)

## What changed (H64)

The carried-forward task from `HANDOFF_CURRENT.md` / `NEXT_TASK.md` was run end-to-end: verify the
quick-start surface from a fresh venv with only `pip install -r requirements.txt`. It reproduced
the prior session's claim (2072 passed, 16 skipped) and **found a third dependency of the same
class** as the pyarrow and setuptools fixes before it.

- `requirements.txt` — added `ruff>=0.6.0` after `pytest-cov>=4.1.0`, under a comment that names
  the two documented gates it unblocks.

`AGENTS.md:16-17` documents the lint/format gates as the canonical commands to run:

```
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
```

`ruff` is declared in `pyproject.toml:25` only as the optional `lint` extra
(`lint = ["ruff>=0.6.0"]`), and `pip install -r requirements.txt` does **not** install optional
extras. So a fresh environment following the documented quick start could not run the documented
lint/format gates at all — `python: No module named ruff`. The committed configuration
(`[tool.ruff]`, `[tool.ruff.lint]`, `[tool.ruff.format]`) and the declaration itself were already
pinned by `tests/test_ruff_reproducibility.py:31` (`test_ruff_is_declared_as_a_lint_dependency`),
but the pinned *gate* was unreachable from the quick start: the declaration test could pass while
the gates it exists to make reproducible could not be executed. Same defect class as the two prior
instances — `requirements.txt` is the documented quick start and must pull in everything the
pinned contract surface needs to run, not just what `src/qtr` imports at runtime.

No code under `src/qtr` or tests was modified; no published artifact, gate threshold, verdict or
certified number was changed; no grid was re-run; no hypothesis was added.

## What was actually verified

- Fresh venv, `pip install -r requirements.txt` only: `ruff-0.17.2` installs (alongside the
  previously fixed `setuptools-84.2.1` and `pyarrow-26.0.0`).
- From that same clean venv, the documented gates now run and pass:
  - `python -m ruff check src tests run_*.py` → *All checks passed!*
  - `python -m ruff format --check src tests run_*.py` → **103 files already formatted**
  - (Verified with the literal `run_*.py` argument from `AGENTS.md`; a bare `run_*.py` is a shell
    glob, not a ruff argument — `ruff check run_*.py` errors with E902 "No such file or
    directory", so the gates are run as the shell expands them.)
- `python -m pytest -q --cov=qtr --cov-branch` from the clean venv → `src/qtr` **1 091 statements,
  330 branches, 0 missed, 0 partial, 100.00%** (unchanged).
- `python -m pytest -q -W error` from the clean venv → **2 072 passed, 16 skipped** (full suite; the
  16 skips are all intentional and self-declaring, unchanged).
- System environment re-check after the edit: `ruff check` → *All checks passed!*;
  `ruff format --check` → **103 files already formatted**; `tests/test_ruff_reproducibility.py`
  and `tests/test_public_api_contract.py` → **35 passed**.

## What remains unresolved

All remaining items in `FINAL_REPORT.md` §H53–§H61 are **disclosed, not quantified** — each
depends on an input the record does not hold, and none can be resolved without new committed
inputs. The thirteen H58/H59 gate booleans stay as published (all in REJECT families; no certified
verdict moves). H1–H30 exhausted; certified families frozen.

## Precise next task

**None assigned.** The H47–H64 series is complete. If a session wants work, the only honest
options are (a) wait for newly committed artifacts that make a disclosed value measurable, or
(b) after any change under `src/qtr`, re-run the pinned contracts -- including
`test_engine_metric_agreement.py`, `test_h53_published_metrics_disclosure`,
`test_h54_non_metrics_block_disclosure`, `test_h55_nested_metrics_disclosure`,
`test_h56_stats_json_echoes`, `test_h57_total_return_audit`, `test_h58_price_pathology_contamination`
and `test_h59_contamination_gate_blast_radius` -- and confirm the gates stay green. In addition,
verify the quick-start surface by running the suite from a fresh venv with only
`pip install -r requirements.txt`, since `requirements.txt` is now the contract that must declare
every dependency a pinned contract test or a documented gate imports (currently
`setuptools>=68`, `pyarrow>=14.0.0` and `ruff>=0.6.0`).

---

## What changed (H63)

The one precise task carried forward from `HANDOFF_NEXT.md` was run end-to-end: a fresh venv with
only `pip install -r requirements.txt` (no pre-installed pyarrow or setuptools). It confirmed the
pyarrow fix and found a second dependency of the same class.

- `requirements.txt` — added `setuptools>=68` ahead of `numpy>=1.24.0`, mirroring
  `pyproject.toml`'s `[build-system] requires`. `pyproject.toml:2` declares it as the build backend
  and `tests/test_public_api_contract.py:147`/`:157` exercise `setuptools.find_packages`, but both
  use `pytest.importorskip("setuptools")`, so a clean environment following the documented quick start
  skipped those two pinned contract tests instead of running them. The system runner had setuptools
  68.1.2 apt-installed, which is why the inherited baseline showed only 16 skipped.

No code under `src/qtr` or tests was modified; no published artifact, gate threshold, verdict or
certified number was changed; no grid was re-run; no hypothesis was added.

## What was actually verified

- Fresh venv, `pip install -r requirements.txt` only: `setuptools-84.2.1` and `pyarrow-26.0.0` both
  install.
- `python -m pytest -q -W error tests/test_public_api_contract.py` → **33 passed, 0 skipped**
  (was 31 passed, 2 skipped before the fix).
- `python -m pytest -q -W error` → **2 072 passed, 16 skipped** (full suite). The remaining 16 skips
  are all intentional and self-declaring.
- `python -m pytest -q --cov=qtr --cov-branch` → `src/qtr` **1 091 statements, 330 branches,
  0 missed, 0 partial, 100.00%** (unchanged: no source or test code moved).
- `python -m ruff check src tests run_*.py` → *All checks passed!*; `ruff format --check` →
  **103 files already formatted**.
- The two previously-erroring modules from the pyarrow fix still collect and pass:
  `tests/test_h53_published_metrics_disclosure.py` and `tests/test_h55_nested_metrics_disclosure.py`
  → 45 passed.

## What remains unresolved

All remaining items are **disclosed, not quantified** -- each depends on an input the record does
not hold (the H9 VIX series, pre-fix fold/beta conventions, the H16 train+val `val_sharpe`,
the 22 sample-convention information ratios, the 14 benchmark `avg_trade_cost` entries, the 40
`stats.json` echoes, the SVXY split) and none can be resolved without new committed inputs. The
thirteen H58/H59 gate booleans stay as published (all in REJECT families; no certified verdict
moves). H1–H30 exhausted; certified families frozen.

## Precise next task

**None assigned.** The H47–H63 series is complete. If a session wants work, the only honest
options are (a) wait for newly committed artifacts that make a disclosed value measurable, or
(b) after any change under `src/qtr`, re-run the pinned contracts -- including
`test_engine_metric_agreement.py`, `test_h53_published_metrics_disclosure`,
`test_h54_non_metrics_block_disclosure`, `test_h55_nested_metrics_disclosure`,
`test_h56_stats_json_echoes`, `test_h57_total_return_audit`, `test_h58_price_pathology_contamination`
and `test_h59_contamination_gate_blast_radius` -- and confirm the gates stay green. In addition,
verify the quick-start surface by running the suite from a fresh venv with only
`pip install -r requirements.txt`, since `requirements.txt` is now the contract that must declare
every dependency a pinned contract test imports.

---

## What changed (this session — dependency fix)

`requirements.txt` — added the missing core dependency `pyarrow>=14.0.0`.

`pyproject.toml` declares `pyarrow>=14.0.0` as a core dependency and `src/qtr` uses it
(`data/fetcher.py:92`/`111`, `tracking/experiment.py:166`/`336`), but `requirements.txt` — the
documented quick start (`pip install -r requirements.txt` per AGENTS.md) — omitted it. A fresh
environment following the quick start could not read/write parquet, so
`tests/test_h53_published_metrics_disclosure.py` and `tests/test_h55_nested_metrics_disclosure.py`
errored at collection (`ImportError: Unable to find a usable engine`). Added `pyarrow>=14.0.0` after
`loguru>=0.7.0`, mirroring `pyproject.toml`'s core-dependency block.

No code under `src/qtr` or tests was modified; no published artifact, gate threshold, verdict or
certified number was changed; no grid was re-run; no hypothesis was added.

## What was actually verified (this session)

- `python -m pytest -q -W error` → **2 057 passed, 16 skipped** (full suite; both previously
  erroring modules collect and pass).
- `python -m pytest -q --cov=qtr --cov-branch` → `src/qtr` = **1 086 statements, 330 branches,
  0 missed, 0 partial, 100.00%**.
- `python -m ruff check src tests run_*.py` → *All checks passed!*; `ruff format --check` →
  **103 files already formatted**.

## What remains unresolved

- Clean-environment verification of the requirements.txt fix (fresh venv, install only
  requirements.txt, full suite green) remains; see NEXT_TASK.md.
- All remaining items in FINAL_REPORT.md §H53–§H61 are disclosed, not quantified, and depend on
  inputs the record does not hold.

---

# HANDOFF — H63 complete (the NaN-tail total-return disagreement)

## What changed (H63)

The carried-forward task from `HANDOFF_CURRENT.md` / `NEXT_TASK.md` was to find and fix the
next defect of the H38/H62 class. The existing non-finite tests all passed, so the probe had to
reach an input class they did not cover. A matrix of adversarial return series (mid-series
`inf`/`-inf`/`nan`, first, last, all, all-NaN, loss below -100%, huge) fed to
`VectorizedBacktester._calculate_metrics` and `validate_strategy` found a residual disagreement
the contract did not catch.

- `src/qtr/validation/statistics.py:804` — `validate_strategy` now measures the total return as
  `(1 + returns).cumprod().iloc[-1] - 1`, the same statistic the engine measures, instead of
  `(1 + returns).prod() - 1`. For every finite input the arithmetic is **bit-identical**
  (measured: relative difference 0.0 over 200 series of length 2..11441, including returns as large
  as +/-50%), so no published number moves. The change only matters on the boundary the engine's
  guard exists for: a series whose tail carries a non-finite bar.
- `tests/test_engine_metric_agreement.py` — **4 tests added** (2 positive, 2 negative controls),
  suite 70 → 74.

## The defect

`pandas.Series.prod()` reduces with `skipna=True` by default, so it silently drops a trailing NaN
and reports the compound of the bars before it. `pandas.Series.cumprod()` propagates NaN, so its
last row is NaN and the engine's `equity.iloc[-1]` is NaN too. On a NaN-tail input the engine
reported `total_return = NaN` and `annualized_return = -1.0` (its `gross <= 0` guard fires),
while `validate_strategy` reported `0.0` and `0.0` — the two implementations disagreed on an input
the record actually contains: every runner that builds a return series from `prices.pct_change()`
can produce one, and `run_experiment.py:218` and `run_baseline.py:193` both pass
`result.returns.values` to `validate_strategy`. This is the same class of defect as H38 (the
total-return range) and H62 (the non-finite Sharpe/Sortino guards), which is why the engine is the
side that had to move here.

## What was actually verified (this session)

- `python -m pytest -q -W error` → **2 076 passed, 16 skipped** (was 2072; 4 added).
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` → `src/qtr` =
  **1 091 statements, 330 branches, 0 missed, 0 partial, 100.00%**; both changed modules
  (`engine.py`, `statistics.py`) individually at 100%.
- `python -m ruff check src tests run_*.py` → *All checks passed!*; `ruff format --check` →
  **103 files already formatted**.
- Regression check: the five published `validation.total_return` values re-derive from their own
  equity curves under the new formula. The only two that differ do so by 9e-16 and 5e-15 — float
  noise at the 15th significant digit, far inside the contract's 1e-12 tolerance.

## What remains unresolved

Nothing. The H1–H30 hypothesis space is exhausted, H31–H63 are all closed, and the suite is green
at 100% coverage on `src/qtr`.

## Approaches that failed and why

- Running the existing non-finite tests first: they passed, because the mid-series
  `inf`/`-inf`/`nan` bar does not reach the total return (the std guard short-circuits the Sharpe
  before the compound is consulted). The defect only surfaces on a **non-finite tail**, which no
  test covered. The probe matrix (mid-series, first, last, all, all-NaN, loss, huge) found it.
- Reconstructing the published `validation.total_return` from the equity curve without the
  initial-capital term first reported all five as changed; that was a reconstruction error in the
  probe, not a real change — re-running with the correct first-bar return confirmed only
  float-noise differences.

## Next task

None. The repository is in a verified, fully-covered, green state. If a new task is assigned,
start from the baseline above (2076 passed, 16 skipped, 100% coverage on `src/qtr`).

---

# HANDOFF — H65 complete (the data package had no public fetch entry point)

## What changed (H65)

No hypothesis task was assigned and the H1–H30 space is exhausted, so the session inspected the
repository for a bounded, high-value, verifiable gap instead of waiting passively. It found one in
the same "declaration is the surface" class as §H64: `src/qtr/data/fetcher.py` defined three
public fetch methods (`fetch_yahoo`, `fetch_futures`, `fetch_ccxt`) and the package re-exported
`DataCache`, `DataFetcher`, `get_data_fetcher`, `non_positive_prices` and `PRICE_COLUMNS`, but
exposed **no single dispatch entry point**. A caller who knew which vendor they wanted still had
to remember which method to call and which keyword arguments it takes, and a misspelled source was
indistinguishable from a symbol that genuinely had no data (every fetch method logs and continues
on a per-symbol failure). The package's own public-API invariant
(`tests/test_public_api_contract.py:192`) could not catch it, because that invariant only fires on a
name that is *declared* and not defined, or *defined* and not declared -- a public function that
exists in the module and is simply not re-exported is invisible to it.

- `src/qtr/data/fetcher.py` — new public `fetcher(source, symbols, start, end=None, interval="1d",
  use_cache=True, exchange_id=None)`. Dispatches on `source` to `fetch_yahoo`, `fetch_futures` or
  `fetch_ccxt`, forwarding the rest unchanged. The dispatch is explicit (not a `getattr` on the
  fetcher) so a typo in `source` raises `ValueError("unknown data source ...")` instead of
  silently returning an empty dict. `source="ccxt"` requires `exchange_id=` and raises `ValueError`
  when it is omitted, because CCXT has no default exchange.
- `src/qtr/data/__init__.py` — `fetcher` added to `__all__`, so it is reachable through the
  top-level star export as well.
- `tests/test_data_fetcher.py` — **11 tests added** (36, was 25): three dispatch-equality tests
  against the three methods, the CCXT-missing-exchange guard, a parametrised `unknown source`
  negative control over seven spellings, and an export/surface assertion reaching
  `from qtr import *`.

No published artifact, gate threshold, verdict or certified number was changed; no grid was
re-run; no hypothesis was added. The change is purely additive on the public API surface.

## What was actually verified (H65)

- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` → `src/qtr` =
  **1 102 statements, 338 branches, 0 missed, 0 partial, 100.00%** (was 1 091 / 330; the +11
  statements and +8 branches are the new function).
- `python -m pytest -q -W error` → **2 087 passed, 16 skipped** (was 2 072; +11 are the new tests;
  the 16 skips are unchanged and all intentional/self-declaring).
- `python -m ruff check src tests run_*.py` → *All checks passed!*; `python -m ruff format --check
  src tests run_*.py` → **103 files already formatted**.
- `tests/test_public_api_contract.py` → **33 passed** (the new export is caught by
  `test_each_subpackage_all_is_exactly_the_public_api_of_its_module` and by
  `test_the_star_import_exports_exactly_the_declared_api`).
- `tests/test_data_fetcher.py` → **36 passed** (was 25).

## Approaches that failed and why

- Inspecting only the pinned contract tests first would have reported everything green and missed
  the gap: the public-API invariant is bidirectional on *declared* names, so a function that exists
  in the module and is simply not re-exported is outside its scope. The gap was found by reading
  `src/qtr/data/__init__.py` and `fetcher.py` side by side against the package's stated purpose
  ("Unified data fetcher with caching and standardization"), not by running tests.
- A `getattr(fetcher, source)` dispatcher was rejected: the three methods have different keyword
  contracts and every fetch method treats a per-symbol failure as non-fatal, so a misspelled
  source would have returned an empty dict indistinguishable from a genuinely empty symbol. The
  explicit three-branch dispatch with a named `ValueError` is the only form that fails loud.

## Next task

None assigned. The H47–H65 series is complete. If a new task is assigned, start from the baseline
above (2087 passed, 16 skipped, 100% coverage on `src/qtr` at 1 102 statements / 338 branches).
