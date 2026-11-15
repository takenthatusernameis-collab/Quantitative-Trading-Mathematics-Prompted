# HANDOFF — current session (2026-11-15, Cycle 136)

## What changed

**Fixed a reproduced `fetch_ccxt` crash on an unknown `exchange_id`; 100% coverage preserved.**

No prior agent assignment existed, so I inspected the repo (clean tree at HEAD `78f756c`,
matches `origin/main`) and selected a bounded, high-value task from the remaining
public `src/qtr` surface. The defect hunts of Cycles 132/135 probed
`qtr.data.insider` and `qtr.strategies.baselines` but not the fetcher's CCXT
exchange initialization, so they missed this one.

- **Reproduced defect (reachable via the public CCXT fetch path):**
  `DataFetcher.fetch_ccxt` did `exchange_class = getattr(ccxt, exchange_id)`
  (fetcher.py:348) **before** the per-symbol `try` block, so an `exchange_id`
  that ccxt does not expose raised a bare
  `AttributeError: module 'ccxt' has no attribute '<exchange_id>'` and aborted the
  whole call instead of failing closed per-symbol like the network, column and
  pagination paths. Reachable from the public API with no caller-side filtering:
  every CCXT runner passes `exchange_id` in, and `run_h23_crypto_futures_tsmom.py:484`
  hard-codes `"coinbase"`, so any other id (or a future ccxt version that drops
  it) hits it. Reproduced in isolation:
  `fetch_ccxt("not_a_real_exchange", ["BTC/USDT"], ...)` -> `AttributeError`.
- **Fix:** `src/qtr/data/fetcher.py` - `getattr(ccxt, exchange_id, None)` then raise
  a named `ValueError` ("unknown CCXT exchange ...") listing `ccxt.exchanges` when
  the real module exposes it and falling back to the plain message for stubs
  that do not. A valid id is a no-op, so the clean path is bit-identical.
- **Tests:** `tests/test_data_fetcher.py` - new `TestUnknownExchangeId` with
  `test_unknown_exchange_id_raises_value_error`,
  `test_unknown_exchange_id_raises_before_any_symbol_fetch` (a `NeverCalled`
  exchange proves the guard short-circuits before the symbol loop),
  `test_known_exchange_id_is_untouched`, and
  `test_the_contract_rejects_the_pre_fix_attribute_error` (behavioural negative
  control reconstructing the pre-fix `AttributeError`). +4 tests.

## What was actually verified (own evidence)

- Before-fix repro (isolated `PYTHONPATH=src`):
  `fetch_ccxt("not_a_real_exchange", ...)` -> `AttributeError: module 'ccxt' has
  no attribute 'not_a_real_exchange'`.
- After-fix: same call raises `ValueError: unknown CCXT exchange
  'not_a_real_exchange'...`; `fetch_ccxt("binance", ...)` still fetches normally.
- **Negative control:** `git stash` of only `fetcher.py` -> the 3 rejecting tests
  fail with the exact pre-fix `AttributeError` (`'kraken'`, `'not_a_real_exchange'`);
  restored via `git stash pop`, 4 passed.
- Full pinned suite `python -m pytest -q -W error --cov=qtr --cov-branch
  --cov-report=term-missing --ignore=tests/test_gates_workflow.py` (434.77s) ->
  **3863 passed, 51 skipped, 0 failed**, `src/qtr` coverage **100.00%** (1504
  stmts / 534 branches / 0 miss; `fetcher.py` 223 stmts / 84 branches).
- `python -m pytest -q tests/test_gates_workflow.py` -> **7 failed** (unchanged,
  maintainer-gated; fix is `patches/0001-gates-workflow-contract-fix.patch`).
- `python scripts/backtest_perf_regression_gate.py` -> **PASSED** (0.481s, limit
  5s, 10.7MB peak, 13668 trades).
- `python -m ruff check src tests run_*.py scripts` -> All checks passed; `ruff
  format --check` -> 335 files already formatted.

## What remains unresolved

1. **Maintainer-only (CI contract):** `.github/workflows/gates.yml` not updated;
   7 `tests/test_gates_workflow.py` tests red until the maintainer applies
   `patches/0001-gates-workflow-contract-fix.patch` with workflow scope. Agent
   cannot land `.github/workflows/**`.
2. **Research queue exhausted under free/public PIT data:** H1-H182
   executed/rejected; no honest free-data H183 is pre-registrable without new
   authorized data.
3. **Reproducibility backlog:** `missing_files=197`, `hash_mismatches=11`,
   `orphaned_files=528`, `missing_meta_files=0` unchanged; baseline-frozen.

## Approaches already failed / must not be repeated

- Do not trust a handoff's pass/coverage claim without running the gate; this
  session ran the full pinned suite + coverage (3863/0/100%).
- Do not make speculative `src/qtr` changes absent a reproduced, reachable defect
  -- the `fetch_ccxt` exchange-id crash is reproduced, reachable from every CCXT
  runner, and was closed here.
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or
  alter coverage/frozen-contract gates.
- Do not invent a free-data H183 or treat parameter/timeframe/universe variations
  as new mechanism families.

## One precise next task

**Maintainer (preferred, unblocks CI):** apply and push
`patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then run
`python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on
`origin/main`.

**Agent alternative (only with new evidence):** continue hunting a *reproduced*,
runner-reachable defect in `src/qtr` -- the productive method is executable
fuzzing/property probes across module boundaries and at the smallest input
boundaries (n = 0/1/2, empty, duplicate labels, non-finite), not re-running the
same suite. If `src/qtr` changes, verify with the full pinned suite
`python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
--ignore=tests/test_gates_workflow.py` and ruff check/format.

**Constraints:** no gate weakening; no modification of published/frozen artifacts,
verdicts, thresholds, or frozen numbers except deliberate authorized
corpus/baseline updates; no workflow commit from agent.