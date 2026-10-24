# HANDOFF_CURRENT — session complete (H65: the data package had no public fetch entry point)

## State

- **H35–H64 are COMPLETE** per prior handoffs; H1–H30 exhausted; certified families frozen. No
  hypothesis work is assigned.
- **One new bounded task was found and completed (H65):** the `qtr.data` package re-exported its
  three fetch methods (`fetch_yahoo`, `fetch_futures`, `fetch_ccxt`) but exposed **no single
  dispatch entry point**. A caller who knows which vendor they want still had to remember which
  method to call and which keyword arguments it takes, and a misspelled source was indistinguishable
  from a symbol that genuinely had no data (every fetch method logs and continues on a per-symbol
  failure). Added a public `fetcher(source, ...)` dispatcher with an explicit, named
  `ValueError` on an unknown source, exported it in `qtr.data.__all__` (and therefore through the
  top-level star export), and pinned the dispatch with 11 tests.
- **No published artifact, gate threshold, verdict or certified number was changed; no grid was
  re-run; no hypothesis was added.** The change is purely additive on the public API surface.

## What changed (this session)

- `src/qtr/data/fetcher.py` — new public `fetcher(source, symbols, start, end=None, interval="1d",
  use_cache=True, exchange_id=None)`. Dispatches on `source` to `fetch_yahoo`,
  `fetch_futures` or `fetch_ccxt`, forwarding the rest unchanged. The dispatch is explicit (not a
  `getattr` on the fetcher) so a typo in `source` raises `ValueError("unknown data source ...")`
  instead of silently returning an empty dict. `source="ccxt"` requires `exchange_id=` and raises
  `ValueError` when it is omitted, because CCXT has no default exchange.
- `src/qtr/data/__init__.py` — `fetcher` added to `__all__`.
- `tests/test_data_fetcher.py` — **11 tests added** (3 dispatch-equality tests against the three
  methods, the CCXT-missing-exchange guard, a parametrised `unknown source` negative control over
  7 spellings, and an export/surface assertion that reaches the top-level star import).

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

## What remains unresolved

- All remaining items in `FINAL_REPORT.md` §H53–§H61 are **disclosed, not quantified** — each
  depends on an input the record does not hold (missing inputs, disclosed convention differences,
  or benchmarks/trade logs/signals never committed). None can be resolved without new committed
  inputs; none affect gates.
- No published artifact, gate threshold, verdict or certified number may be modified.
- No grid may be re-run; the H1–H30 hypothesis space remains exhausted.

## Precise next task

**None assigned.** The H47–H65 series is complete. If a session wants work, the only honest
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