# HANDOFF_CURRENT_SESSION.md — Cycle 115 (2026-11-14): fixed H182 corpus cache poisoning; corpus repaired

## What changed

- `src/qtr/data/insider.py` — new `load_cached_transactions(path)`: missing, unreadable, or
  zero-row parquet is a cache *miss* (empty `TRANSACTION_COLUMNS` frame), not a valid cache.
- `src/qtr/data/__init__.py` — export `load_cached_transactions`.
- `scripts/fetch_h182_insider_data.py` — skip only non-empty caches; re-fetch empty ones;
  never write an empty parquet; isolate per-issuer errors; added `--force` and a `src`
  `sys.path` bootstrap.
- `tests/test_sec_insider.py` — 2 tests for the helper (all branches).
- `tests/test_fetch_h182_insider_data.py` — new: 5 tests for the corpus cache contract.

## Actually verified (this session, own evidence)

- **Focused:** `pytest tests/test_sec_insider.py tests/test_fetch_h182_insider_data.py -q` — 42 passed.
- **Coverage:** `src/qtr/data/insider.py` — **100%** (234 stmts / 84 branches / 0 miss).
- **Lint:** `python -m ruff check src tests run_*.py scripts` — All checks passed.
- **Format:** `python -m ruff format --check src tests run_*.py scripts` — 333 files already formatted.
- **Real EDGAR re-fetch:** `--symbols AAPL --force` → 325 rows; then
  `--symbols AAPL,MSFT,AMZN,NVDA` → AAPL skipped (325 cached), MSFT 402, AMZN 704, NVDA 1381
  (all previously zero-row). Corpus now populated for AAPL/GOOGL/MSFT/AMZN/NVDA.
- **Full pinned gate:** `pytest -q --cov=qtr --cov-branch --cov-report=term-missing` (427s) —
  **3,788 passed / 51 skipped / 7 failed**. The 7 failures are *exclusively* the
  maintainer-gated `tests/test_gates_workflow.py` contract (unchanged). `src/qtr` coverage **100%**.
- **Patch:** `git apply --check patches/0001-gates-workflow-contract-fix.patch` — **APPLIES_CLEANLY**.
- **Perf gate:** `python scripts/backtest_perf_regression_gate.py` — **PASSED** (0.406s, limit 5s).

## What remains unresolved

1. **Maintainer-only:** apply `patches/0001-gates-workflow-contract-fix.patch` (workflow scope)
   and push to `origin/main` to turn the 7 red `tests/test_gates_workflow.py` tests green.
2. **H182 corpus incomplete:** META, JPM, XOM, JNJ, WMT not yet cached. Fetch with
   `python scripts/fetch_h182_insider_data.py` (now safe: empty results are retried).
3. **H182 runner not built:** no `run_nf_20261110_08_insider_signal.py`. The free PIT data
   blocker is resolved; the directive's selection/authorization step remains.

## Failed approaches / do not repeat

- Do not repeat re-verification-only cycles as "progress" when state is stable and no evidenced defect exists.
- Do not edit `.github/workflows/**` or weaken `tests/test_gates_workflow.py` / coverage / frozen contracts.
- Do not treat a zero-row parquet as a valid cache.

## One precise next task

**Build and run the H182 insider-signal experiment** (`run_nf_20261110_08_insider_signal.py`)
over the cached corpus per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4/§6: PIT
`insider_net_buy_ratio` on `available_at`, engine `shift(1)`, standard fail-closed gates, and a
recorded verdict. First fetch the missing 5 symbols.

**Constraints:** `src/qtr` changes require 100% coverage; no gate weakening; no published/frozen
artifact, verdict, threshold, or frozen number modified; no commit/push of `.github/workflows/**`.