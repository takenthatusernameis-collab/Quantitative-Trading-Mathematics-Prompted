# HANDOFF — current session (2026-11-16, Cycle 153)

## Reconciliation note (read first)

The checkout this session started from (`dce28d4`) was **8 commits behind
`origin/main`**. The real prior handoff is **Cycle 152** on `origin/main`
(`HANDOFF_CURRENT_SESSION.md` / `HANDOFF.md` / `NEXT_TASK.md` there), not the
Cycle 144 doc that was present at `dce28d4`. This session **fast-forwarded to
`origin/main` (`f97b6a8`, Cycle 152)** and re-applied + re-verified the change on
that base. Every number below is from the `origin/main` base.

## What changed (substantive, not annotation-only)

1. **`src/qtr/data/fetcher.py` — the fresh yahoo/futures path now canonicalizes its
   index (keep-first dedup + sort), matching the ccxt fresh path and every cache
   hit.** The fresh path did ``_standardize_columns`` + ``pd.to_datetime(...).tz_localize(None)``
   and returned the vendor index verbatim. yfinance returns the frame verbatim, so
   an overlapping request window can repeat a bar and some intervals return an
   unsorted index. The **cache-hit path already dedups+sorts**
   (`_standardize_cached_index`, Cycle 144) and the **ccxt fresh path already
   dedups+sorts** (`fetch_ccxt`), so the fresh yahoo path was the only path that
   did not. This is a **fresh-vs-cache divergence with a material effect**: the
   engine only sorts a panel when ``prices.index.has_duplicates``
   (`engine.py:402`), so a **unique-but-unsorted** fresh panel is left in storage
   order and ``pct_change`` compounds returns in the wrong order.
   - **Reproduced before fix** (3 bars, all-1 signal, `close=[110,100,121]`
     unsorted vs `[100,110,121]` sorted): sorted → `total_return=0.2098` (correct
     `1.1*1.1-1`); unsorted → `total_return=0.0998` (wrong). The same vendor frame
     fetched twice also diverged: fresh returned `[2020-01-03, 2020-01-02,
     2020-01-04]`, the cache hit returned the sorted index.
   - **Fix:** one line after the tz normalization:
     ``df = df[~df.index.duplicated(keep="first")].sort_index()``. A clean
     (sorted, unique) frame is a no-op, so the clean path is bit-identical; this
     matches the ccxt fresh path (`fetch_ccxt`) exactly.

2. **`src/qtr/backtest/engine.py` — corrected the now-stale comment** at the
   duplicate-index guard (`engine.py:393-401`). It claimed
   ``fetch_yahoo``/``fetch_futures`` and the cached read path "do not" dedup; as of
   Cycle 144 (cache path) and this change (fresh yahoo/futures) **every fetch path
   does**, so the guard is now pure defense in depth. Comment-only; no behavior
   change.

3. **Tests:** `tests/test_data_fetcher.py::TestFreshYahooIndexCanonicalization`
   (+5): fresh yahoo unsorted index is sorted; fresh yahoo duplicated index is
   deduplicated (keep first); fresh yahoo == cache hit for an unsorted frame (the
   indistinguishable invariant); fresh futures unsorted index is sorted; and a
   behavioural negative control that reconstructs the pre-fix fresh path and shows
   the unsorted index survives.

## What was actually verified (own evidence, this session)

- **Repro before fix** (`/tmp/probe_cache.py`, `/tmp/fuzz_cache.py`; fake
  `yfinance`/`ccxt`): fresh yahoo unsorted index returned
  `[2020-01-03, 2020-01-02, 2020-01-04]` while the cache hit returned the sorted
  index; fresh duplicated index returned 3 rows while the cache hit returned 2.
  After the fix all fresh-vs-cache cases (clean / unsorted / duplicated /
  capitalized) are `equal=True`, and every foreign-writer cache case
  (integer index refused; duplicated/unsorted deduped+sorted; tz-aware dup
  tz-stripped; capitalized columns normalized) is canonical.
- **Engine impact:** unsorted unique 3-bar panel → `total_return=0.0998`; sorted →
  `0.2098`. (The fetcher now sorts, so the fetched panel is the sorted one.)
- **Negative control:** `git stash push -- src/qtr/data/fetcher.py` →
  `TestFreshYahooIndexCanonicalization` **4 failed, 1 passed** (the 5th is the
  intentional pre-fix reconstruction); `git stash pop` → **87 passed** on
  `tests/test_data_fetcher.py` (was 82 on `origin/main`; +5).
- **Focused:** `python -m pytest -q tests/test_data_fetcher.py
  tests/test_backtest_engine.py tests/test_engine_edge_stress.py
  tests/test_h58_price_pathology_contamination.py
  tests/test_h59_contamination_gate_blast_radius.py` → **284 passed**.
- **Full pinned suite** `python -m pytest -q -W error --cov=qtr --cov-branch
  --cov-report=term-missing --ignore=tests/test_gates_workflow.py` (451.73s) →
  **3962 passed, 51 skipped, 0 failed**, `src/qtr` coverage **100.00%**
  (1563 stmts / 564 branches / 0 miss; `fetcher.py` 238 stmts / 88 branches, all
  100%).
  - Count reconciliation vs the Cycle 152 baseline (3960 passed / 48 skipped):
    this environment does not have `qtr` installed as a distribution and has no
    generated manifest, so the 3 `test_generated_manifest_contract` tests **skip**
    here instead of passing → 3960 − 3 + 5 (new tests) = **3962 passed**, and
    48 + 3 = **51 skipped**. No other delta.
- `python -m pytest -q tests/test_gates_workflow.py` → **7 failed** (unchanged,
  exclusively the maintainer-gated block; fix is
  `patches/0001-gates-workflow-contract-fix.patch`).
- `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED**
  (0.424s < 5s, 10.7MB peak, 13668 trades).
- `python -m ruff check src tests run_*.py scripts` → **All checks passed.**
  `python -m ruff format --check src tests run_*.py scripts` → **336 files
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
4. **Residual (out of scope this cycle):** the engine still only sorts a panel
   when `prices.index.has_duplicates` (`engine.py:402`); a caller that assembles a
   **unique-but-unsorted** panel *outside* the fetcher and calls `run_backtest`
   directly still gets storage-order returns. Cycle 152 explicitly lists
   "duplicate index/column handling in engine/fetcher/tracker paths" as a pinned
   defect not to re-audit, so this was left untouched; the fetcher-side fix
   removes the reachable path (all three fetch methods now sort+dedup).

## Approaches already tried / must not be repeated

- **Do not return `None` from `_standardize_cached_index` and then call `.empty`
  on it** — that is the historical `73b38c3` bug and crashes `fetch_yahoo`.
- **Do not coerce a non-datetime cached index with `pd.to_datetime`** — it
  manufactures 1970 timestamps; refuse (empty) instead.
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or
  alter coverage/frozen-contract gates.
- Do not re-audit the already-pinned families without new evidence: cache
  hit index/column normalization+dedup, `max_leverage`/`initial_capital`/
  `max_position_size` boundaries, `record_artifact` DataFrame dedupe,
  `load_metadata` non-dict, path traversal. **This cycle's finding is distinct
  from the pinned "cache hit normalization+dedup":** the pinned work normalized
  the *cache-hit* path (Cycle 144) and thereby left the *fresh* path as the only
  un-normalized one; the unsorted-**unique** case was never considered (Cycle 144
  discussed only the *duplicated* case and called dedup "strictly safer"), and it
  is the one that silently corrupts engine returns because the engine's guard keys
  on `has_duplicates`.
- Do not use `--cov=<dotted.module>` (aborts collection); use `--cov=qtr`.

## One precise next task

**Maintainer (preferred, unblocks CI):** apply and push
`patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then
`python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on
`origin/main`.

**Agent path (new evidence only):** hunt a *reproduced, runner-reachable*
`src/qtr` defect on a public path **not yet closed** — fuzz/boundary probes at
smallest inputs (n=0/1/2, empty, duplicate labels, non-finite, corrupt/partial
state, untrusted names/paths, type-mismatched operands). If `src/qtr` changes,
re-run the full pinned suite (excluding the maintainer-gated workflow file),
`ruff check`/`ruff format --check`, and
`python scripts/backtest_perf_regression_gate.py`, with own evidence. Do **not**
re-audit the pinned families listed above, and do **not** invent a free-data H183
or treat parameter/timeframe/universe variations as new families.