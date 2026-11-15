# HANDOFF — current session (2026-11-15, Cycle 144)

## What changed (substantive, not annotation-only)

1. **`src/qtr/data/fetcher.py` — corrected and completed the cache-hit index standardization.**
   The prior session's HEAD commit `73b38c3` had added `_standardize_cached_index`
   but left it **buggy, incomplete, and untested**:
   - It returned `None` for a non-datetime index, and `_fetch_yahoo_panel` then
     did `cached.empty` on that `None` -> **`AttributeError: 'NoneType' object has
     no attribute 'empty'`** on a cache hit (a crash the pre-index code did not
     have). It also had **no tests**, so the new lines broke the 100% coverage gate.
   - The **ccxt cache-hit path was not standardized at all**: it normalized only
     columns, so a stale integer index or a duplicated timestamp passed through
     (`fetch_ccxt`'s fresh path dedups+sorts).
   This session:
   - `_standardize_cached_index` now returns a **`pd.DataFrame` (never `None`)**:
     a non-datetime index is **refused** -> `df.iloc[:0]` (empty, columns intact),
     not coerced (coercing a stale integer index manufactures 1970 timestamps);
     a duplicated index keeps `keep="first"` and is sorted, matching the ccxt
     fresh path.
   - `_fetch_yahoo_panel`'s cache-hit path always calls `_standardize_columns`
     after `_standardize_cached_index` (the `if cached.empty` on a possibly-`None`
     value is gone).
   - `fetch_ccxt`'s cache-hit path now also calls `_standardize_cached_index`
     before `_standardize_columns`, so its cache hit matches its fresh path.
   - No other source, gate, artifact, sidecar, hash, frozen-number, or workflow change.

2. **Tests:** `tests/test_data_fetcher.py` `TestCacheHitIndexStandardization` (7):
   yahoo integer-index cache hit is refused (empty, `close` column intact); it warns
   (`non-datetime index`); yahoo duplicated index is deduped+sorted; yahoo clean
   index is unchanged; ccxt integer-index cache hit is refused; ccxt duplicated
   index is deduped+sorted; and a behavioural negative control reconstructs the
   pre-fix cache hit (only columns normalized, stale integer index survives).
   **+7 tests.**

3. **Docs:** `HANDOFF.md` banner, `NEXT_TASK.md` Cycle 144 section, this file.

## What was actually verified (own evidence, this session)

- **Reproduced before fixing** (`/tmp/repro_cache_index.py`, seeded cache entries
  written by `DataCache.set` with a stale index):
  - yahoo cache hit, integer index -> **`AttributeError: 'NoneType' object has no
    attribute 'empty'`** (the HEAD crash);
  - ccxt cache hit, integer index -> returned with index `[0, 1]` (not standardized);
  - ccxt cache hit, duplicated timestamp -> returned **2 duplicate rows**.
  After the fix the same four cases give: yahoo integer -> empty; yahoo dup -> 1 row;
  ccxt integer -> empty; ccxt dup -> 1 row.
- **Negative control:** `git stash push -- src/qtr/data/fetcher.py` (reverts to the
  buggy HEAD) -> `TestCacheHitIndexStandardization` **5 failed, 2 passed** (the two
  yahoo dedup/clean cases pass even on HEAD); `git stash pop`, **78 passed** on
  `tests/test_data_fetcher.py` (was 71; +7).
- **Committed-cache audit:** all **82** committed `.cache/data/*.parquet` files ->
  **0** capitalized-column, **0** non-datetime-index, **0** duplicated-index,
  **0** empty. The new normalization is a **no-op on the committed store** (no
  regression); the defect is a stale/foreign-writer hazard, as the column fix was.
- Full pinned suite `python -m pytest -q -W error --cov=qtr --cov-branch
  --cov-report=term-missing --ignore=tests/test_gates_workflow.py` (345.66s, and a
  second deterministic run at 343.74s) -> **3922 passed, 48 skipped, 0 failed**,
  `src/qtr` coverage **100.00%** (1529 stmts / 542 branches / 0 miss;
  `fetcher.py` 229 stmts / 82 branches, all 100%).
  - Count reconciliation vs the Cycle 143 baseline (3912 passed / 51 skipped):
    **+10 passed / -3 skipped** = +7 (these tests) + 3 conditional-skip tests that
    now run and pass. Verified separately: `test_reproducibility_audit`,
    `test_trade_log_cost_reconciliation`, `test_generated_manifest_contract`,
    `test_h29_lookahead_sweep`, `test_h28_causal_recertification`,
    `test_coverage_gate_contract`, `test_public_api_contract` -> **189 passed, 0
    skipped**. The 48 skips are deterministic artifact-content skips
    (`test_causality_invariant` 1, `test_h51_benchmark_container_invariance` 47).
- `python -m pytest -q tests/test_gates_workflow.py` -> **7 failed** (unchanged,
  exclusively the maintainer-gated block; fix is
  `patches/0001-gates-workflow-contract-fix.patch`).
- `python scripts/backtest_perf_regression_gate.py` -> **PASSED** (0.305s < 5s,
  10.7MB peak, 13668 trades).
- `python -m ruff check src tests run_*.py scripts` -> **All checks passed.**
  `python -m ruff format --check src tests run_*.py scripts` -> **336 files
  already formatted.**

## What remains unresolved

1. **Maintainer-only (CI contract):** `.github/workflows/gates.yml` not updated;
   7 `tests/test_gates_workflow.py` tests red until the maintainer applies
   `patches/0001-gates-workflow-contract-fix.patch` with workflow scope. Agent
   cannot land `.github/workflows/**`.
2. **Research queue exhausted under free/public PIT data:** H1–H182
   executed/rejected; H183 unassigned. Cycle 140 (FRED) confirmed the corrected
   data does not yield a new family.
3. **Reproducibility backlog:** `missing_files=197`, `hash_mismatches=11`,
   `orphaned_files=528`, `missing_meta_files=0` unchanged; baseline-frozen.
4. **Deliberate asymmetry (not a bug):** a cache hit with a duplicated index is
   now deduped+sorted, while the *fresh yahoo* path does not dedup (only the
   fresh ccxt path does). Dedup is strictly safer and matches ccxt; the difference
   only appears for a pathological duplicated vendor frame. A non-datetime cached
   index is refused, not coerced (coercion would fabricate 1970 timestamps).

## Approaches already tried / must not be repeated

- **Do not return `None` from `_standardize_cached_index` and then call `.empty`
  on it** — that is exactly the HEAD `73b38c3` bug and it crashes `fetch_yahoo`.
- **Do not coerce a non-datetime cached index with `pd.to_datetime`** — it
  manufactures 1970 timestamps; refuse (empty) instead.
- Do not make `_set_nested` write flat keys or otherwise change the config loader
  (closed Cycle 142).
- Do not re-audit the duplicate index/column engine guards (Cycles 125/130), the
  statistics shape guards (Cycle 124), or the malformed-JSONL skip (Cycle 127).
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or
  alter coverage/frozen-contract gates.
- Do not use `--cov=<dotted.module>` (aborts collection with `ImportError:
  cannot load module more than once per process`); use `--cov=qtr`.
- Do not make speculative `src/qtr` changes absent a reproduced, reachable defect;
  the defect hunt is **not** exhausted (this cycle corrected a defect the prior
  commit introduced).

## One precise next task

**Maintainer (preferred, unblocks CI):** apply and push
`patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then
`python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on
`origin/main`.

**Agent path:** the cache-hit schema (columns + index dtype + dedup) is now
consistent for **both** yahoo and ccxt, and is a no-op on all 82 committed cache
files. The next bounded, verifiable work is one more reproduced-defect cycle on a
surface not yet probed at its boundary — e.g. probe the *other* consumer of
`DataCache.get` (the CCXT `cache_symbol` key path and the `DataCache` round-trip
under a tz-aware/duplicated stored index) for any remaining fresh-vs-cache
divergence. Any `src/qtr` change must preserve 100% coverage and pass
`ruff`/the pinned suite; do not edit `.github/workflows/**` or the gates.