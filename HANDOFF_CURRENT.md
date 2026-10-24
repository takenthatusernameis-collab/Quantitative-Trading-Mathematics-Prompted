# HANDOFF_CURRENT — session complete (H66: the fetcher() CCXT branch forwarded the wrong default)

## State

- **H35–H65 are COMPLETE** per prior handoffs; H1–H30 exhausted; certified families frozen. No
  hypothesis work is assigned.
- **One new bounded task was found and completed (H66):** the `fetcher()` dispatch entry point
  added in §H65 documented `fetcher("ccxt", ...)` as the same call as `fetch_ccxt(...)`, but its
  CCXT branch forwarded the dispatcher's `interval` parameter (default `"1d"`) into
  `fetch_ccxt`'s `timeframe` slot, whose own default is `"1h"`. A caller using defaults got hourly
  bars requested as daily ones. Added a `timeframe: str = "1h"` parameter to `fetcher` and forwarded
  that instead; pinned the forwarding with 3 tests, including a recording-stub positive control
  that the inherited dispatch-equality test could not see (the fake exchange ignored `timeframe`).
- **No published artifact, gate threshold, verdict or certified number was changed; no grid was
  re-run; no hypothesis was added.** The change is a one-parameter addition to a function with no
  callers in the committed record.

## What changed (this session)

- `src/qtr/data/fetcher.py` — `fetcher` now carries `timeframe: str = "1h"` and forwards it into
  the CCXT branch; `interval` is documented as applying to the yahoo branches only.
- `tests/test_data_fetcher.py` — **3 tests added** (38, was 35): the CCXT dispatch-equality test
  passes an explicit `timeframe` on both sides; a recording CCXT stub proves the default call
  forwards `"1h"`; a behavioural negative control reconstructs the pre-fix forwarding and
  requires it to differ from the corrected default.

## What was actually verified (this session)

- `python -m pytest -q -W error` → **2 089 passed, 16 skipped** (was 2 087; the 16 skips are
  unchanged and all intentional/self-declaring).
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` → `src/qtr` =
  **1 102 statements, 338 branches, 0 missed, 0 partial, 100.00%** (unchanged).
- `python -m ruff check src tests run_*.py` → *All checks passed!*; `python -m ruff format --check
  src tests run_*.py` → **103 files already formatted**.
- `tests/test_data_fetcher.py` → **38 passed**; `tests/test_public_api_contract.py` → **33 passed**;
  `tests/test_ruff_reproducibility.py` → **2 passed**.
- The two new tests **fail on the pre-fix code** (reverted dispatcher:
  `TypeError: fetcher() got an unexpected keyword argument 'timeframe'`), then pass with the fix.

## What remains unresolved

- All remaining items in `FINAL_REPORT.md` §H53–§H61 are **disclosed, not quantified** — each
  depends on an input the record does not hold (missing inputs, disclosed convention differences,
  or benchmarks/trade logs/signals never committed). None can be resolved without new committed
  inputs; none affect gates.
- No published artifact, gate threshold, verdict or certified number may be modified.
- No grid may be re-run; the H1–H30 hypothesis space remains exhausted.

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