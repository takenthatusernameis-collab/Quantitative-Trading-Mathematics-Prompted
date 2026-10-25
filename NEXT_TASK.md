# Next Task

## State

H35–H69 complete. **No hypothesis work is assigned** — every remaining
unresolved item in `FINAL_REPORT.md` (§H53–§H61) is a value that is not a
function of the committed record (missing inputs, disclosed convention
differences, or benchmarks/trade logs/signals never committed). None can be
implemented or verified from this checkout; they stay disclosed, not
quantified, and no gate reads any of them.

## What changed (this session — H69: S&P 500 symbol sanitization relied on a regex default)

- `src/qtr/data/fetcher.py` — `fetch_sp500_constituents` sanitized the
  Wikipedia Symbol column with `df["Symbol"].str.replace(".", "-")`, relying
  on the pandas-2.x default of `regex=True`. Under that default a bare `"."`
  is the "any character" pattern, so every class-share ticker (BRK.B, BF.B,
  GOOGL.A, ...) was turned into a string of dashes. The fix is
  `str.replace(".", "-", regex=False)`, which is correct under both the 2.x
  default (where it changes behaviour) and the 3.x default (where it is a no-op
  but keeps the code honest against the documented contract). No published
  artifact, gate threshold, verdict or certified number depends on this
  output; no runner in the committed record calls
  `fetch_sp500_constituents`.
- `tests/test_data_fetcher.py` — **2 tests added** (40, was 38): a
  `TestSp500SymbolSanitization` class with a dotted-ticker fixture pinning
  that each class-share ticker is preserved as `BRK-B` etc., and a behavioural
  negative control that reconstructs the pre-fix `regex=True` mangling and
  requires the corrected sanitization to differ from it.

- `python -m pytest -q -W error` → **2103 passed, 16 skipped** (was 2101; +2).
- `python -m pytest -q --cov=qtr --cov-branch` → `src/qtr` **1112 statements,
  342 branches, 0 missed, 0 partial, 100.00%** (unchanged).
- `python -m ruff check src tests run_*.py` → *All checks passed!*;
  `python -m ruff format --check src tests run_*.py` → **103 files already
  formatted**.
- Pinned contracts re-run: 609 passed, 1 skipped across
  `test_engine_metric_agreement`, `test_h53_*`, `test_h54_*`, `test_h55_*`,
  `test_h56_*`, `test_h57_*`, `test_h58_*`, `test_h59_*`,
  `test_runner_causality_inventory`, `test_runner_metric_agreement`,
  `test_benchmark_gate_contract`, `test_public_api_contract`,
  `test_ruff_reproducibility`, `test_trade_log_cost_reconciliation`,
  `test_tsmom_signal`, `test_causality_invariant`.

## One precise next task

**None assigned.** The quick-start surface verification from a fresh venv
(`pip install -r requirements.txt` only) is complete and green in prior
sessions. Options if further work is desired:
(a) wait for newly committed artifacts that make any disclosed §H53–§H61
value measurable; or
(b) baseline hygiene — after any change under `src/qtr` or affecting
runners/validation, re-run the pinned contracts
(`test_engine_metric_agreement.py`, `test_h53_published_metrics_disclosure`,
`test_h54_non_metrics_block_disclosure`, `test_h55_nested_metrics_disclosure`,
`test_h56_stats_json_echoes`, `test_h57_total_return_audit`,
`test_h58_price_pathology_contamination`,
`test_h59_containment_gate_blast_radius`, `test_runner_causality_inventory`,
`test_runner_metric_agreement`, `test_benchmark_gate_contract`,
`test_public_api_contract`, `test_ruff_reproducibility`,
`test_trade_log_cost_reconciliation`, `test_tsmom_signal`,
`test_causality_invariant`) and confirm `python -m pytest -q --cov=qtr
--cov-branch` keeps `src/qtr` at 100% with gates green; keep the ruff
lint/format gates clean.

## Constraints carried forward

- No published artifact, gate threshold, verdict or certified number may be
  modified. No grid may be re-run; the H1–H30 hypothesis space remains exhausted.
- `src/qtr` coverage gate must stay at 100% (statement + branch).
- Ruff lint (`python -m ruff check src tests run_*.py`) and format
  (`python -m ruff format --check src tests run_*.py`) gates must stay clean.
- Re-run `tests/test_runner_causality_inventory.py`,
  `tests/test_runner_metric_agreement.py` and `tests/test_benchmark_gate_contract.py`
  after any change in a runner or under `src/qtr/validation`.

(End of file - total 79 lines)