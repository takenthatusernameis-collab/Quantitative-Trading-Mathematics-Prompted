# Next Task

## State

H35–H66 complete. **No hypothesis work is assigned** — every remaining unresolved item in
`FINAL_REPORT.md` (§H53–§H61) is a value that is not a function of the committed record (missing
inputs, disclosed convention differences, or benchmarks/trade logs/signals never committed). None
can be implemented or verified from this checkout; they stay disclosed, not quantified, and no gate
reads any of them.

## What changed (this session — H66, the fetcher() CCXT branch forwarded the wrong default)

The `fetcher()` dispatch entry point added in §H65 documented `fetcher("ccxt", ...)` as the same
call as `DataFetcher().fetch_ccxt(...)`. It was not: the CCXT branch forwarded the dispatcher's
`interval` parameter (default `"1d"`) into `fetch_ccxt`'s `timeframe` slot, whose own default is
`"1h"`. A caller using defaults got hourly bars requested as daily ones.

- `src/qtr/data/fetcher.py` — `fetcher` now carries its own `timeframe: str = "1h"` parameter and
  forwards *that* into the CCXT branch; `interval` is documented as applying to the yahoo branches
  only. The yahoo and futures branches forwarded `interval` unchanged and are bit-identical to
  before; only the CCXT default call moved.
- `tests/test_data_fetcher.py` — **3 tests added** (38, was 35): the CCXT dispatch-equality test
  now passes an explicit `timeframe` on both sides so it pins the *forwarding* rather than leaving
  it at the dispatcher's default; a recording CCXT stub proves the default call forwards `"1h"`;
  and a behavioural negative control reconstructs the pre-fix forwarding (passing
  `timeframe="1d"`) and requires it to differ from the corrected default.

The defect was invisible to the inherited dispatch-equality test because the fake exchange's
`fetch_ohlcv` ignored `timeframe` entirely, so both sides returned the same frame and the "same
call" claim was untested for the argument that actually differed.

No code under `src/qtr` other than the one data file was modified; no published artifact, gate
threshold, verdict or certified number was changed; no grid was re-run; no hypothesis was added.

## What was actually verified (this session)

- The two new tests **fail on the pre-fix code** (reverted dispatcher:
  `TypeError: fetcher() got an unexpected keyword argument 'timeframe'`), then pass with the fix
  restored.
- `python -m pytest -q -W error` → **2 089 passed, 16 skipped** (full suite; +2 are the new tests;
  the 16 skips are unchanged and all intentional/self-declaring).
- `python -m pytest -q --cov=qtr --cov-branch` → `src/qtr` **1 102 statements, 338 branches,
  0 missed, 0 partial, 100.00%** (unchanged: the new parameter adds no statement and no branch).
- `python -m ruff check src tests run_*.py` → *All checks passed!*; `python -m ruff format --check
  src tests run_*.py` → **103 files already formatted**.
- `tests/test_data_fetcher.py` → **38 passed** (was 35); `tests/test_public_api_contract.py` →
  **33 passed**; `tests/test_ruff_reproducibility.py` → **2 passed**.

## One precise next task

**None assigned.** The H47–H66 series is complete. If a session wants work, the only honest
options are (a) wait for newly committed artifacts that make any disclosed §H53–§H61 value
measurable, or (b) after any change under `src/qtr`, re-run the pinned contracts and confirm the
gates stay green.

## Constraints carried forward

- No published artifact, gate threshold, verdict or certified number may be modified.
- No grid may be re-run; the H1–H30 hypothesis space remains exhausted.
- The package's public API (§H45) is pinned by `tests/test_public_api_contract.py`; the `fetcher`
  export is part of that surface and is pinned by the same module's `__all__`-vs-public-API
  invariant. A change to `fetcher`'s signature is invisible to that invariant (it only compares
  declared names), which is why the forwarding behaviour needed its own behavioural contract.
- The quick-start dependency surface (§H63, §H64) is pinned by running the suite, the coverage
  gate and the two ruff gates from a fresh venv with only `pip install -r requirements.txt`;
  `requirements.txt` must declare every dependency a pinned contract test or a documented gate
  imports (currently `setuptools>=68`, `pyarrow>=14.0.0` and `ruff>=0.6.0`).
- Re-run `tests/test_runner_causality_inventory.py`, `tests/test_runner_metric_agreement.py` and
  `tests/test_benchmark_gate_contract.py` after any change in a runner or under `src/qtr/validation`.
- The coverage gate (`python -m pytest -q --cov=qtr --cov-branch`) must stay at 100% for `src/qtr`;
  the lint gate (`python -m ruff check src tests run_*.py` and
  `python -m ruff format --check src tests run_*.py`) must stay clean.