# HANDOFF — current session (2026-11-16, Cycle 156)

## What changed (substantive, not annotation-only)

1. **`src/qtr/validation/statistics.py` — `bars_per_year` now refuses a numeric
   (positional) index instead of coercing it to 1970 nanosecond timestamps.**
   The body did `idx = pd.DatetimeIndex(index)` unconditionally. A numeric
   index is not a timestamp axis, but `pd.DatetimeIndex` coerces integers as
   nanoseconds since the Unix epoch, so a `RangeIndex(3)` became
   `1970-01-01T00:00:00.000000001 .. .000000003` — a two-nanosecond span and a
   bars-per-year of ~4.7e16. `annualized_sharpe` then scales the Sharpe by
   `sqrt(bpy)` ~= 2.2e8. Measured: three returns `[0.01, -0.005, 0.02]` give a
   daily-annualized Sharpe of **18.99** but a RangeIndex-annualized Sharpe of
   **1.76e8** — a silent nine-orders-of-magnitude corruption, not an error. A
   `RangeIndex` is the *default* index of `pd.Series(list)` and of
   `frame.reset_index(drop=True)`, so this is reachable from the public API
   with no caller-side filtering. This is the same class as the Cycle 153
   `DataFetcher._standardize_cached_index` policy ("refuse a non-datetime index
   rather than manufacture 1970 timestamps", fetcher.py:237) and Cycle 154's
   non-mapping config refusal.
   - **Fix:** `bars_per_year` returns `float("nan")` for a numeric index
     (`pd.api.types.is_numeric_dtype(pd.Index(index))`), the same fail-closed
     value already returned for a <2-bar or zero-span index. A
     `pd.DatetimeIndex` is used as-is; a datetime-like non-DatetimeIndex (a
     list of date strings, `datetime`/`date` objects, or `pd.Timestamp`s)
     still converts exactly as before. `annualized_sharpe` already maps a
     non-finite `bpy` to `0.0` (the no-evidence result), so a positional index
     now yields `0.0` rather than a fabricated 1e8 Sharpe.

2. **Tests:** `tests/test_statistics.py::TestBarsPerYearNumericIndex` (+14) —
   parametrized numeric indexes (`RangeIndex`, `Index[int]`, `Index[float]`,
   `np.array`, plain `list`) all return NaN; a behavioural negative control
   reconstructs the pre-fix `pd.DatetimeIndex(pd.RangeIndex(3))` coercion and
   asserts the ~4.7e16 bars/year it produced; parametrized datetime-like
   non-DatetimeIndex inputs still convert; `annualized_sharpe` returns `0.0`
   for a `RangeIndex`/Series-index; a string date index matches the daily
   `DatetimeIndex`; a daily `DatetimeIndex` is unchanged.

## What was actually verified (own evidence, this session)

- **Repro before fix** (`/tmp/probe2.py`): `bars_per_year(pd.RangeIndex(3))`
  returned `4.733639999999999e+16`; `annualized_sharpe([0.01,-0.005,0.02],
  pd.RangeIndex(3))` returned `176472004.6382786` vs the daily `18.985...`.
  After the fix both return `nan` / `0.0`.
- **Negative control:** `git stash push -- src/qtr/validation/statistics.py`
  -> `TestBarsPerYearNumericIndex` **8 failed / 5 passed**; `git stash pop` ->
  **14 passed** on the new class.
- **Focused files:** `tests/test_statistics.py tests/test_h26_sharpe_scale_audit.py
  tests/test_h27_pnl_level_audit.py tests/test_engine_metric_agreement.py` ->
  **366 passed**.
- **Full pinned suite** `python -m pytest -q -W error --cov=qtr --cov-branch
  --cov-report=term-missing --ignore=tests/test_gates_workflow.py` (449.95s) ->
  **4021 passed, 51 skipped, 0 failed**, `src/qtr` coverage **100.00%**
  (1582 stmts / 576 branches / 0 miss; `statistics.py` 342/128).
- `python -m pytest -q tests/test_gates_workflow.py` -> **7 failed** (unchanged,
  exclusively the maintainer-gated block; fix is
  `patches/0001-gates-workflow-contract-fix.patch`).
- `python scripts/backtest_perf_regression_gate.py` -> **PERF GATE PASSED**
  (0.425s < 5s, 10.7MB peak, 13668 trades).
- `python -m ruff check src tests run_*.py scripts` -> **All checks passed.**
  `python -m ruff format --check src tests run_*.py scripts` -> **336 files
  already formatted.**

## What remains unresolved

1. **Maintainer-only (CI contract):** `.github/workflows/gates.yml` not updated;
   7 `tests/test_gates_workflow.py` tests red until the maintainer applies
   `patches/0001-gates-workflow-contract-fix.patch` with workflow scope. Agent
   cannot land `.github/workflows/**`.
2. **Research queue exhausted under free/public PIT data:** H1–H182
   executed/rejected; no honest H183 without new authorized data.
3. **Reproducibility backlog:** `missing_files=197`, `hash_mismatches=11`,
   `orphaned_files=528`, `missing_meta_files=0` unchanged; baseline-frozen.
4. **Other degenerate-operand crashes observed but NOT fixed this cycle** (leave
   for a future evidenced cycle): `sharpe_ratio(returns, periods_per_year=0)`
   and `compare_to_benchmark(..., periods_per_year=0)` raise
   `ZeroDivisionError`; `walk_forward_splits(n_samples, ..., train_ratio=nan)`
   / `gap=nan` / `n_samples=nan` raise `ValueError`/`OverflowError` out of
   `np.arange`/`int()`. These are scalar-operand/config-degenerate, not the
   silent-corruption class fixed here.

## Approaches already tried / must not be repeated

- Do not re-audit the pinned families without new evidence: cache-hit and
  fresh-fetch index/column normalization+dedup (Cycles 144/153),
  `max_leverage`/`initial_capital`/`max_position_size` boundaries (Cycles
  147/148/152), duplicate index/column handling in engine/fetcher/tracker paths,
  `Experiment.record_artifact` DataFrame dedupe, `Experiment.load_metadata`
  non-dict-file handling (Cycle 150), artifact/log path traversal, the
  `load_config`/`_set_nested` non-mapping-document handling (Cycle 154), the
  EDGAR `_recent_filings`/`filing_documents` non-mapping-document handling
  (Cycle 155), and now the `bars_per_year` numeric-index refusal (Cycle 156).
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or
  alter coverage/frozen-contract gates.
- Do not make speculative `src/qtr` changes absent a reproduced, reachable
  defect.
- Do not use `--cov=<dotted.module>` (aborts collection with
  `ImportError: cannot load module more than once per process`); use
  `--cov=qtr`.

## One precise next task

**Maintainer (preferred, unblocks CI):** apply and push
`patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then
`python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on
`origin/main`.

**Agent path (new evidence only):** hunt a *reproduced, runner-reachable*
`src/qtr` defect on a public path **not yet closed** -- fuzz/boundary probes at
smallest inputs (n=0/1/2, empty, duplicate labels, non-finite, corrupt/partial
state, untrusted names/paths, type-mismatched operands). A concrete lead with
own reproduction is the scalar-operand class listed under "remains unresolved"
item 4 (`sharpe_ratio`/`compare_to_benchmark` with `periods_per_year=0`, and
`walk_forward_splits` with non-finite `train_ratio`/`gap`/`n_samples`) -- fix
the smallest one with a fail-closed guard and a behavioural negative control,
not all at once. If `src/qtr` changes, re-run the full pinned suite (excluding
the maintainer-gated workflow file), `ruff check`/`ruff format --check`, and
`python scripts/backtest_perf_regression_gate.py`, with own evidence. Do **not**
re-audit the pinned families above, and do **not** invent a free-data H183 or
treat parameter/timeframe/universe variations as new families.