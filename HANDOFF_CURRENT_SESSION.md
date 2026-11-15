# HANDOFF — current session (2026-11-15, Cycle 125)

## What changed

**One bounded source fix: `run_backtest` no longer crashes on a duplicated index label.**

The prior handoff (Cycle 124) closed the `qtr.validation.statistics` shape guards and
pointed the next session at the runner-side glue. I fuzzed the *engine* instead — the
most-used public entry point, and the layer every runner funnels into — and found one
genuine, reproduced, deterministic crash.

- **Defect (reproduced before fixing):** `run_backtest` builds its trade log with
  `price = float(prices.loc[ts, sym])` (engine.py:444). When `ts` is a *duplicated*
  index label, `.loc[ts, sym]` returns a Series and `float()` raises
  `TypeError: float() argument must be a string or a real number, not 'Series'`. A
  duplicated `signals` index fails even earlier: `signals.reindex(index=prices.index, ...)`
  raises `ValueError: cannot reindex on an axis with duplicate labels`. Reproduced two
  ways (dup in prices, dup in signals).
- **Reachability (why it is a real defect, not a synthetic fixture):** the documented
  pipeline can emit a duplicated index. `fetch_ccxt` already guards with
  `~df.index.duplicated(keep="first").sort_index()` (fetcher.py:407), but
  `fetch_yahoo`/`fetch_futures` (`_fetch_yahoo_panel`, fetcher.py:215-216) and the cached
  read path (`DataCache.get`, fetcher.py:92-100) do not dedup; a cache entry written
  before dedup / an overlapping vendor window carries the duplicate through. The runners
  `pd.concat(..., axis=1).sort_index()` per-symbol closes (`run_nf_*`, `run_h*`) and hand
  the panel to `run_backtest` with no dedup.
- **Fix:** canonicalize the index once at the top of `run_backtest` (keep first, then
  sort) for both `prices` and `signals`, mirroring the CCXT branch's existing policy. A
  unique index is a no-op, so the clean path is bit-identical. `src/qtr/backtest/engine.py`
  (+14 lines). No other `src/qtr` module touched.
- **Tests:** `tests/test_engine_edge_stress.py` — new `TestDuplicateIndex` with
  `test_duplicate_price_index_with_a_trade_at_the_dup_does_not_crash`,
  `test_duplicate_signal_index_does_not_crash`,
  `test_unique_index_is_untouched_by_the_dedup_guard`, and
  `test_the_contract_rejects_the_pre_fix_duplicate_index_crash` (negative control that
  reconstructs the pre-fix `float(Series)` TypeError). +4 tests.

No gate, artifact, sidecar, hash, frozen number, or workflow change.

## What was actually verified (own evidence)

- `pytest -q tests/test_engine_edge_stress.py` → **16 passed** (was 12).
- `pytest -q tests/test_backtest_engine.py tests/test_engine_edge_stress.py
  tests/test_engine_metric_agreement.py tests/test_engine_total_return_consistency.py
  tests/test_frozen_contract_gates_edge_stress.py tests/test_gate_evaluation_edge_stress.py`
  → **253 passed**.
- Full pinned suite `pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
  --ignore=tests/test_gates_workflow.py` (332s) → **3841 passed, 48 skipped, coverage
  100.00%**. The +4 vs. the prior 3837 is exactly the four new tests; the 48 skips are
  the pre-existing H51/H29/H28/causality skips. `src/qtr/backtest/engine.py` = 100%
  (233 stmts, 80 branches).
- **Negative control:** `git stash push src/qtr/backtest/engine.py` then re-running
  `TestDuplicateIndex` → the two positive tests fail with the exact pre-fix errors
  (`TypeError: float() argument ... not 'Series'`; `ValueError: cannot reindex on an axis
  with duplicate labels`), the negative-control test passes. Restored with `git stash pop`.
- `pytest -q tests/test_gates_workflow.py` → **7 failed** (unchanged; exclusively the
  maintainer-gated `tests/test_gates_workflow.py` block).
- `ruff check src tests run_*.py scripts` → All checks passed.
- `ruff format --check src tests run_*.py scripts` → 335 files already formatted (after
  formatting the new test).
- `git status` → only `src/qtr/backtest/engine.py` and `tests/test_engine_edge_stress.py`
  modified. No commit made by the agent; `.github/scripts/kilo-controller.sh` stages all
  but `.github/workflows/**` and commits with an empty message.

## What remains unresolved

1. **Maintainer-only (CI contract):** `.github/workflows/gates.yml` not updated; 7
   `tests/test_gates_workflow.py` tests red until the maintainer applies
   `patches/0001-gates-workflow-contract-fix.patch` with workflow-scoped credentials.
   Agent cannot land `.github/workflows/**`.
2. **Research queue exhausted under free/public PIT data:** H1–H182 executed/rejected
   (register Cycles 96/116/118). No honest free-data H183 is pre-registrable.
3. **Reproducibility backlog:** `missing_files=197`, `hash_mismatches=11`,
   `orphaned_files=528`, `missing_meta_files=0` unchanged; baseline-frozen where
   contract/citation constraints apply.

## Approaches already failed / must not be repeated

- **Do not re-derive a "H182 is missing from the corpus" finding.** It is false
  (174 records; H182 is record 174). Count the corpus directly.
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or alter
  coverage/frozen-contract gates.
- Do not treat delisted/spliced/unavailable free series as PIT-valid.
- Do not mass-edit runners/tests/gates or frozen artifacts to force green.
- Do not append an H182 record to `experiments.jsonl` without sidecars + coordinated
  baseline/pinned-test updates (ratchet fails).
- Do not make speculative `src/qtr` changes absent an evidenced defect.
- **Do not re-audit the duplicate-index guard** — it is now closed and pinned.
- **Do not re-fuzz the H182 runner's private helpers with malformed frames.** They raise
  `KeyError`/`TypeError` on frames missing `transaction_code`/`available_at`, but that is
  outside the runner's own contract (the corpus builder always supplies those columns);
  not an evidenced defect. Fix only a reproduced crash reachable from a real pipeline.
- Do not change `log_artifact` to always write a sidecar without a coordinated
  `missing_meta_files` baseline + sidecar-schema update (an empty `{}` sidecar for a
  JSON artifact fails the `keys` contract; `test_log_artifact_without_metadata` pins the
  current falsy-metadata branch).

## One precise next task

**Maintainer (preferred, unblocks CI):** apply and push
`patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then run
`python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on `origin/main`.

**Agent alternative if a new evidenced defect is wanted:** fuzz the remaining public
`src/qtr` surface not yet exercised for duplicate/degenerate shapes — e.g.
`qtr.data.fetcher.fetch_ccxt` column-standardization on a short/odd vendor frame, or
`qtr.tracking.experiment` methods on malformed artifact paths — and fix only a reproduced
crash with a real-pipeline reachability argument.

**Constraints:** preserve gates/contracts/100% `src/qtr` coverage; do not alter
published/frozen artifacts or thresholds except a deliberate authorized corpus/baseline
update; no workflow commit from agent.