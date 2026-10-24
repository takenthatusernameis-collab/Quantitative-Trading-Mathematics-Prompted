# Next Task

## State

H35–H66 complete. **No hypothesis work is assigned** — every remaining
unresolved item in `FINAL_REPORT.md` (§H53–§H61) is a value that is not a
function of the committed record (missing inputs, disclosed convention
differences, or benchmarks/trade logs/signals never committed). None can be
implemented or verified from this checkout; they stay disclosed, not
quantified, and no gate reads any of them.

## What changed (this session — duplicate CCXT recording test removed)

Removed the duplicate test
`test_fetcher_ccxt_rejects_the_pre_fix_interval_forwarding` from
`tests/test_data_fetcher.py` (51 deletions). Its body was identical to
`test_fetcher_ccxt_default_timeframe_matches_fetch_ccxt`: both clear the
fetcher's CCXT exchange cache, install a recording CCXT stub, call
`fetcher("ccxt", ...)` with defaults and with `timeframe="1d"`, and assert
`"1h"` vs `"1d"`. The removed test's "negative control" docstring was
misleading — it tested the exact same corrected behavior, adding zero unique
coverage. Kept the better-documented, earlier test.

- `python -m pytest -q -W error` → **2 089 passed, 16 skipped** (was 2 090;
  −1 is the removed test).
- `python -m pytest -q --cov=qtr --cov-branch` → `src/qtr` **1 104 statements,
  338 branches, 0 missed, 0 partial, 100.00%** (unchanged).
- `python -m ruff check src tests run_*.py` → *All checks passed!*;
  `python -m ruff format --check src tests run_*.py` → **103 files already
  formatted**.

## One precise next task

**None assigned.** Options if work is desired:
(a) wait for newly committed artifacts that make any disclosed §H53–§H61 value
measurable; or
(b) baseline hygiene — after any change under `src/qtr` or affecting
runners/validation, re-run the pinned contracts
(`test_engine_metric_agreement.py`, `test_h53_published_metrics_disclosure`,
`test_h54_non_metrics_block_disclosure`, `test_h55_nested_metrics_disclosure`,
`test_h56_stats_json_echoes`, `test_h57_total_return_audit`,
`test_h58_price_pathology_contamination`, `test_h59_contamination_gate_blast_radius`)
and confirm `python -m pytest -q --cov=qtr --cov-branch` keeps `src/qtr` at
100% with gates green; keep the ruff lint/format gates clean. Verify the
quick-start surface from a fresh venv with only `pip install -r
requirements.txt` (`setuptools>=68`, `pyarrow>=14.0.0`, `ruff>=0.6.0`).

## Constraints carried forward

- No published artifact, gate threshold, verdict or certified number may be
  modified. No grid may be re-run; the H1–H30 hypothesis space remains
  exhausted.
- `src/qtr` coverage gate must stay at 100% (statement + branch).
- Ruff lint (`python -m ruff check src tests run_*.py`) and format
  (`python -m ruff format --check src tests run_*.py`) gates must stay clean.
- Re-run `tests/test_runner_causality_inventory.py`,
  `tests/test_runner_metric_agreement.py` and
  `tests/test_benchmark_gate_contract.py` after any change in a runner or
  under `src/qtr/validation`.
