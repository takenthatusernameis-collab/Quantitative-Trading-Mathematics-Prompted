# Next Task

## State

H35–H65 complete. **No hypothesis work is assigned** — every remaining unresolved item in
`FINAL_REPORT.md` (§H53–§H61) is a value that is not a function of the committed record (missing
inputs, disclosed convention differences, or benchmarks/trade logs/signals never committed). None
can be implemented or verified from this checkout; they stay disclosed, not quantified, and no gate
reads any of them.

## What changed (this session — H65, the data package's missing public fetch entry point)

The `qtr.data` package re-exported its three fetch methods (`fetch_yahoo`, `fetch_futures`,
`fetch_ccxt`) but exposed **no single dispatch entry point**. A caller who knows which vendor they
want still had to remember which method to call and which keyword arguments it takes, and a
misspelled source was indistinguishable from a symbol that genuinely had no data -- every fetch
method logs and continues on a per-symbol failure, so the miss would be invisible.

- `src/qtr/data/fetcher.py` — new public `fetcher(source, symbols, start, end=None, interval="1d",
  use_cache=True, exchange_id=None)`. Dispatches on `source` to `fetch_yahoo`, `fetch_futures` or
  `fetch_ccxt`, forwarding the rest unchanged. The dispatch is **explicit** (not a `getattr` on
  the fetcher) so a typo in `source` raises `ValueError("unknown data source ...")` instead of
  silently returning an empty dict. `source="ccxt"` requires `exchange_id=` and raises `ValueError`
  when it is omitted, because CCXT has no default exchange.
- `src/qtr/data/__init__.py` — `fetcher` added to `__all__`, so it is reachable through the
  top-level star export as well.
- `tests/test_data_fetcher.py` — **11 tests added**: three dispatch-equality tests (each proving
  `fetcher("yahoo", ...)` == `fetch_yahoo(...)`, likewise for `yahoo_futures` and `ccxt`), the
  CCXT-missing-exchange guard, a parametrised `unknown source` negative control over seven
  spellings (`yahoo_future`, `YAHOO`, `yfinance`, `""`, `ccx`, `binance`), and an export/surface
  assertion that reaches the top-level `from qtr import *` namespace.

No code under `src/qtr` other than the two data files was modified; no published artifact, gate
threshold, verdict or certified number was changed; no grid was re-run; no hypothesis was added.

## What was actually verified (this session)

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

## One precise next task

**None assigned.** The H47–H65 series is complete. If a session wants work, the only honest
options are (a) wait for newly committed artifacts that make any disclosed §H53–§H61 value
measurable, or (b) after any change under `src/qtr`, re-run the pinned contracts and confirm the
gates stay green.

## Constraints carried forward

- No published artifact, gate threshold, verdict or certified number may be modified.
- No grid may be re-run; the H1–H30 hypothesis space remains exhausted.
- The package's public API (§H45) is pinned by `tests/test_public_api_contract.py`; the new
  `fetcher` export is part of that surface and is pinned by the same module's
  `__all__`-vs-public-API invariant.
- The quick-start dependency surface (§H63, §H64) is pinned by running the suite, the coverage
  gate and the two ruff gates from a fresh venv with only `pip install -r requirements.txt`;
  `requirements.txt` must declare every dependency a pinned contract test or a documented gate
  imports (currently `setuptools>=68`, `pyarrow>=14.0.0` and `ruff>=0.6.0`).
- Re-run `tests/test_runner_causality_inventory.py`, `tests/test_runner_metric_agreement.py` and
  `tests/test_benchmark_gate_contract.py` after any change in a runner or under `src/qtr/validation`.
- The coverage gate (`python -m pytest -q --cov=qtr --cov-branch`) must stay at 100% for `src/qtr`;
  the lint gate (`python -m ruff check src tests run_*.py` and
  `python -m ruff format --check src tests run_*.py`) must stay clean.