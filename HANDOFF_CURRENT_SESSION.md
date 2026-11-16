# HANDOFF — current session (2026-11-16, Cycle 157)

## What changed (substantive, not annotation-only)

1. **`src/qtr/validation/statistics.py` — `sharpe_ratio` now fails closed on a
   degenerate `periods_per_year` instead of raising or emitting `nan`.**
   The body computed `excess = returns - risk_free / periods_per_year` and
   returned `excess.mean() / std * np.sqrt(periods_per_year)` with no guard on
   the period count. A **zero** period count raised `ZeroDivisionError`; a
   **negative** count multiplied by `sqrt(negative)` and emitted `nan` (plus a
   `RuntimeWarning: invalid value encountered in sqrt`); a `nan`/`inf` count
   poisoned the result (`nan`/`±inf`). `periods_per_year` is a bare `int`
   parameter no caller can filter on its own, and the default (`252`) is the
   only value any in-tree runner passes (`engine.py:290`, `run_baseline.py`, the
   CS-momentum runners, `annualized_sharpe` — which already validates `bpy`
   finite-positive — and `sharpe_ratio_ci`). This is the scalar-operand class the
   Cycle 156 handoff flagged as the next lead.
   - **Fix:** `sharpe_ratio` returns `0.0` (the module's no-evidence result,
     already used for an empty or zero-variance series) when
     `periods_per_year` is not finite or is `<= 0`, before the
     `risk_free / periods_per_year` division. The empty-series guard still runs
     first. For every finite positive period count the arithmetic is
     bit-identical to before.

2. **Tests:** `tests/test_statistics.py::TestSharpeRatioPeriodGuard` (+12) —
   parametrized degenerate period counts (`0`, `-1`, `-252`, `0.0`, `-0.5`,
   `nan`, `inf`, `-inf`) all return finite `0.0`; the empty-series path still
   returns `0.0`; a valid period (`252` vs `252.0`) is unchanged and finite; a
   non-zero `risk_free` with `periods_per_year=0` short-circuits before the
   division; a behavioural negative control reconstructs the pre-fix
   `risk_free / 0` `ZeroDivisionError` and the pre-fix `sqrt(-1)` `nan` and
   requires both to be rejected by the contract.

## What was actually verified (own evidence, this session)

- **Repro before fix** (`/tmp/probe_ppo.py`): `sharpe_ratio([0.01,-0.005,0.02],
  periods_per_year=0)` raised `ZeroDivisionError`; `periods_per_year=-1` returned
  `nan` with a `RuntimeWarning`; `periods_per_year=np.inf` returned `-inf`. After
  the fix all three return `0.0`.
- **Negative control:** `git stash push -- src/qtr/validation/statistics.py`
  -> `TestSharpeRatioPeriodGuard` **10 failed / 2 passed**; `git stash pop` ->
  **12 passed** on the new class.
- **Focused files:** `tests/test_statistics.py tests/test_engine_metric_agreement.py`
  -> **298 passed**.
- **Full pinned suite** `python -m pytest -q -W error --cov=qtr --cov-branch
  --cov-report=term-missing --ignore=tests/test_gates_workflow.py` (450.96s) ->
  **4033 passed, 51 skipped, 0 failed**, `src/qtr` coverage **100.00%**
  (1584 stmts / 578 branches / 0 miss; `statistics.py` 344/130).
- `python -m pytest -q tests/test_gates_workflow.py` -> **7 failed** (unchanged,
  exclusively the maintainer-gated block; fix is
  `patches/0001-gates-workflow-contract-fix.patch`).
- `python scripts/backtest_perf_regression_gate.py` -> **PERF GATE PASSED**
  (0.435s < 5s, 10.7MB peak, 13668 trades).
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
4. **Sibling scalar-operand crashes NOT fixed this cycle** (leave for a future
   evidenced cycle): `compare_to_benchmark(..., periods_per_year=0)` raises
   `ZeroDivisionError` (same `risk_free / periods_per_year` term, plus
   `alpha * periods_per_year`); `walk_forward_splits(n_samples, ...,
   train_ratio=nan|inf)` / `gap=nan` / `n_samples=nan` raise
   `ValueError`/`OverflowError` out of `np.arange`/`int()`. These are
   scalar-operand/config-degenerate, not the silent-corruption class; fix the
   smallest one next, not all at once.

## Approaches already tried / must not be repeated

- Do not re-audit the pinned families without new evidence: cache-hit and
  fresh-fetch index/column normalization+dedup (Cycles 144/153),
  `max_leverage`/`initial_capital`/`max_position_size` boundaries (Cycles
  147/148/152), duplicate index/column handling in engine/fetcher/tracker paths,
  `Experiment.record_artifact` DataFrame dedupe, `Experiment.load_metadata`
  non-dict-file handling (Cycle 150), artifact/log path traversal, the
  `load_config`/`_set_nested` non-mapping-document handling (Cycle 154), the
  EDGAR `_recent_filings`/`filing_documents` non-mapping-document handling
  (Cycle 155), the `bars_per_year` numeric-index refusal (Cycle 156), and now
  the `sharpe_ratio` degenerate-period refusal (Cycle 157).
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
own reproduction is the sibling scalar-operand class listed under "remains
unresolved" item 4 (`compare_to_benchmark` with `periods_per_year=0`, and
`walk_forward_splits` with non-finite `train_ratio`/`gap`/`n_samples`) -- fix
the smallest one with a fail-closed guard and a behavioural negative control,
not all at once. If `src/qtr` changes, re-run the full pinned suite (excluding
the maintainer-gated workflow file), `ruff check`/`ruff format --check`, and
`python scripts/backtest_perf_regression_gate.py`, with own evidence. Do **not**
re-audit the pinned families above, and do **not** invent a free-data H183 or
treat parameter/timeframe/universe variations as new families.