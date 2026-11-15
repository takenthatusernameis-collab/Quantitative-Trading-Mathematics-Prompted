# HANDOFF — current session (2026-11-15, Cycle 143)

## What changed (substantive, not annotation-only)

1. **`src/qtr/data/fetcher.py` — new `DataFetcher._standardize_columns(df, symbol)`.**
   `DataCache` is a **persistent, cross-version file store** (committed under
   `.cache/data`, keyed by `source:symbol:start:end:interval`). `DataCache.get`
   returned the stored columns **verbatim** — it only strips a tz-aware index —
   while the fresh-fetch path lowercased vendor columns, reordered
   `present required + extras`, and warned on a missing required column. So a
   cache file written by an older/foreign writer carrying capitalized vendor
   columns (`Close`, `Volume`) was returned as-is on a cache hit, and every
   downstream runner that does `df["close"]` (30+ call sites across `run_*.py`)
   raised `KeyError: 'close'`, while the same frame fetched fresh was normalized
   and worked. This is the same "stale cache file from an older writer" premise
   `DataCache.get`'s tz handling already defends against, extended to the column
   axis.
   - `_standardize_columns` lowercases/normalizes column names, degrades over the
     required columns that are present (warn on each missing one), and returns
     `present + extras`.
   - The fresh path of `_fetch_yahoo_panel`, the fresh path of `fetch_ccxt`, and
     **both cache-hit paths** now call it. A frame already carrying canonical
     lowercase columns is returned bit-identically, so a clean cache hit is
     unchanged.
2. **Tests:** `tests/test_data_fetcher.py` `TestCacheHitColumnNormalization` (5):
   capitalized cache hit is normalized; capitalized cache hit equals a fresh
   fetch; a cache hit warns on a missing required column; a behavioural negative
   control reconstructs the pre-fix verbatim return; the ccxt cache-hit path
   normalizes. **+5 tests.**
3. **Docs:** `HANDOFF.md` banner, `NEXT_TASK.md` Cycle 143 section, this file.

**No gate, artifact, sidecar, hash, frozen-number, or workflow change.**

## What was actually verified (own evidence, this session)

- **Reproduced before fixing:** seeded a cache entry with
  `Open/High/Low/Close/Volume`; `fetch_yahoo(..., use_cache=True)` returned
  capitalized columns and `df["close"]` raised `KeyError`; the fresh path over
  the same vendor frame returned `['open','high','low','close','volume']` and
  `df["close"]` worked. Same for `fetch_ccxt` cache hits (its default
  `timeframe="1h"` matters for the cache key).
- **Negative control:** `git stash push -- src/qtr/data/fetcher.py` -> exactly
  the 4 positive cases fail on capitalized `Close`/`Volume` (`4 failed, 1
  passed`); the negative control passes by construction. `git stash pop`, **71
  passed** on `tests/test_data_fetcher.py` (was 66).
- Full pinned suite `python -m pytest -q -W error --cov=qtr --cov-branch
  --cov-report=term-missing --ignore=tests/test_gates_workflow.py` (343.30s) ->
  **3912 passed, 51 skipped, 0 failed**, `src/qtr` coverage **100.00%**
  (1521 stmts / 540 branches / 0 miss; `fetcher.py` 221 stmts / 80 branches, all
  100%). 3912 = 3907 (Cycle 142) + 5 (this session).
- `python -m pytest -q tests/test_gates_workflow.py` -> **7 failed** (unchanged,
  exclusively the maintainer-gated block; fix is
  `patches/0001-gates-workflow-contract-fix.patch`).
- `python scripts/backtest_perf_regression_gate.py` -> **PASSED** (0.307s < 5s,
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
4. **Deliberately not changed (needs a decision, not a bug fix):** the cache-hit
   path still does **not** coerce a non-datetime index to datetime the way the
   fresh path does (`pd.to_datetime(df.index)`). Coercing a stale integer index
   would manufacture 1970 timestamps, which is arguably worse than leaving it;
   the column-axis defect was the demonstrated one. Also unchanged: a cache frame
   missing `close` is still returned without `close` on both paths (fail-soft;
   both layers behave identically and `run_baseline.py:126` drops it).

## Approaches already tried / must not be repeated

- Do not make `_set_nested` write flat keys or otherwise change the config loader
  (closed in Cycle 142).
- Do not re-audit the duplicate index/column engine guards (Cycles 125/130), the
  statistics shape guards (Cycle 124), or the malformed-JSONL skip (Cycle 127) —
  all closed and pinned.
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or
  alter coverage/frozen-contract gates.
- Do not use `--cov=<dotted.module>` (aborts collection with `ImportError:
  cannot load module more than once per process`); use `--cov=qtr`.
- Do not make speculative `src/qtr` changes absent a reproduced, reachable
  defect; the defect hunt is **not** exhausted (this cycle landed after the prior
  handoff called the cached-read path "not a proven defect").

## One precise next task

**Maintainer (preferred, unblocks CI):** apply and push
`patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then
`python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on
`origin/main`.

**Agent path:** run one more reproduced-defect cycle on a surface not yet probed
at its boundary. One measured, undecided inconsistency remains (verify before
acting): the cache-hit path does not coerce a **non-datetime index** to datetime
the way the fresh path does, and does not dedup a duplicated index the way
`fetch_ccxt`'s fresh path does. Decide whether a stale integer/duplicated index
in a cached frame is a real defect (it would reach `prices.reindex(...)` /
`pd.concat` in the runners) before changing it; do not "fix" it speculatively.
Any `src/qtr` change must preserve 100% coverage and pass `ruff`/the pinned
suite.