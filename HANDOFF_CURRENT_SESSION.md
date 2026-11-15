# HANDOFF — current session (2026-11-15, Cycle 126)

## What changed

**Two bounded source fixes closing the duplicate-`column` label crash class; 100%
coverage preserved.**

The prior handoff (Cycle 125) closed the duplicate-`index` guard in `run_backtest`
and pointed the next session at the remaining public surface for
duplicate/degenerate shapes. I fuzzed the public API (engine, statistics,
strategies, fetcher, tracking) with degenerate frames and found one reproduced
crash class left.

- **Defect 1 (reproduced before fixing):** `non_positive_prices(panel)` built its
  per-column series with `panel[column]` (fetcher.py:59/61). When `column` is a
  *duplicated* label, `panel[column]` returns a **DataFrame**, and
  `pd.to_numeric(DataFrame, errors="coerce")` raises
  `TypeError: arg must be a list, tuple, 1-d array, or Series`. Reproduced two
  ways: a duplicated `close` label in a long frame, and a duplicated symbol label
  in a wide frame. This is the **first** call `run_backtest` makes, so the engine
  crashed before any of its own guards.
- **Reachability (why it is a real defect, not a synthetic fixture):** the
  documented pipeline builds wide panels with `pd.concat(..., axis=1)`
  (`run_nf_*`: `pd.concat(prices_list, axis=1)` / `pd.concat(frames.values(),
  axis=1)`), so two frames that share a symbol name — a repeated ticker in a
  universe, or an overlapping benchmark/universe concatenation — produce a
  duplicated column; the cached/vendor read path also does not dedup columns.
  The screen's own contract is "Empty when the panel is clean": it is a screen,
  not a crash point.
- **Fix 1 (`non_positive_prices`):** iterate columns **by position**
  (`panel.iloc[:, i]`) so every column is a `Series` regardless of how many
  labels share its name. `PRICE_COLUMNS` order is preserved, so the
  offending-observation order (and the first row the fetcher names in its error)
  is bit-identical on the clean path. `src/qtr/data/fetcher.py`.
- **Defect 2 (reproduced before fixing):** even with the screen fixed,
  `run_backtest` still crashed on a duplicated `prices`/`signals` **column** at
  `signals.reindex(index=index, columns=columns)`
  (`ValueError: cannot reindex on an axis with duplicate labels`), and the trade
  log's `float(prices.loc[ts, sym])` returns a Series.
- **Fix 2 (`run_backtest`):** canonicalize duplicate **columns** once on entry
  (keep first) for both `prices` and `signals`, mirroring the existing
  duplicate-index guard. A unique column set is a no-op, so the clean path is
  bit-identical. `src/qtr/backtest/engine.py` (+16 lines). No other `src/qtr`
  module touched.
- **Tests:** `tests/test_h58_price_pathology_contamination.py` — new
  `TestDuplicateColumnLabels` (5 tests: duplicate price label, duplicate wide
  label, clean duplicate panel, `PRICE_COLUMNS` order preserved, and a negative
  control reconstructing the pre-fix `pd.to_numeric(DataFrame)` `TypeError`).
  `tests/test_engine_edge_stress.py` — new `TestDuplicateColumns` (4 tests:
  duplicate price columns, duplicate signal columns, unique columns untouched, and
  a negative control reconstructing the pre-fix `reindex` `ValueError`). +9 tests.

No gate, artifact, sidecar, hash, frozen number, or workflow change.

## What was actually verified (own evidence)

- `pytest -q tests/test_engine_edge_stress.py tests/test_h58_price_pathology_contamination.py tests/test_data_fetcher.py tests/test_backtest_engine.py`
  → **177 passed**.
- Full pinned suite `pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
  --ignore=tests/test_gates_workflow.py` (335.94s) → **3850 passed, 48 skipped,
  coverage 100.00%**. The +9 vs. the prior 3841 is exactly the nine new tests; the
  48 skips are the pre-existing H51/H29/H28/causality skips.
  `src/qtr/data/fetcher.py` = 100% (219 stmts, 82 branches);
  `src/qtr/backtest/engine.py` = 100% (237 stmts, 84 branches).
- **Negative control:** `git stash push src/qtr/data/fetcher.py src/qtr/backtest/engine.py`
  then re-running the two new classes → the 5 positive tests fail with the exact
  pre-fix errors (`TypeError: arg must be a list, tuple, 1-d array, or Series` ×4;
  `ValueError: cannot reindex on an axis with duplicate labels` ×1), and the 4
  negative-control/unique tests pass. Restored with `git stash pop`.
- `pytest -q tests/test_gates_workflow.py` → **7 failed** (unchanged; exclusively the
  maintainer-gated `tests/test_gates_workflow.py` block).
- `ruff check src tests run_*.py scripts` → All checks passed.
- `ruff format --check src tests run_*.py scripts` → 335 files already formatted.
- `git status` → only `src/qtr/data/fetcher.py`, `src/qtr/backtest/engine.py`,
  `tests/test_h58_price_pathology_contamination.py`, `tests/test_engine_edge_stress.py`
  modified. No commit made by the agent; `.github/scripts/kilo-controller.sh` stages all
  but `.github/workflows/**` and commits with an empty message.

## What remains unresolved

1. **Maintainer-only (CI contract):** `.github/workflows/gates.yml` not updated; 7
   `tests/test_gates_workflow.py` tests red until the maintainer applies
   `patches/0001-gates-workflow-contract-fix.patch` with workflow-scoped credentials.
   Agent cannot land `.github/workflows/**`.
2. **Research queue exhausted under free/public PIT data:** H1–H182 executed/rejected
   (register Cycles 96/116); no honest free-data H183 is pre-registrable.
3. **Reproducibility backlog:** `missing_files=197`, `hash_mismatches=11`,
   `orphaned_files=528`, `missing_meta_files=0` unchanged; baseline-frozen where
   contract/citation constraints apply.

## Approaches already failed / must not be repeated

- **Do not re-audit the duplicate-index guard or the duplicate-column guard** — both
  are now closed and pinned with negative controls.
- Do not re-fuzz the H182 runner's private helpers with malformed frames. They raise
  `KeyError`/`TypeError` on frames missing `transaction_code`/`available_at`, but that
  is outside the runner's own contract; not an evidenced defect.
- Do not re-fuzz `qtr.validation.statistics` — closed in Cycles 124/125; every public
  function is guarded (only the intended `ValueError` on an unknown
  `multiple_testing_correction` method remains).
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or alter
  coverage/frozen-contract gates.
- Do not treat delisted/spliced/unavailable free series as PIT-valid.
- Do not mass-edit runners/tests/gates or frozen artifacts to force green.
- Do not append an H182/H183 record to `experiments.jsonl` without sidecars + coordinated
  baseline/pinned-test updates (ratchet fails).
- Do not make speculative `src/qtr` changes absent an evidenced defect.

## One precise next task

**Maintainer (preferred, unblocks CI):** apply and push
`patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then run
`python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on `origin/main`.

**Agent alternative if another evidenced defect is wanted:** the duplicate-label class
(index + columns) is now closed on both axes. The remaining public surface not yet
exercised for degenerate shapes is `qtr.tracking.experiment` on a malformed
`experiments.jsonl` (a partial/interleaved append makes `load_experiment`/
`list_experiments` raise `JSONDecodeError`/`KeyError` — reproduced, but reachability
requires a mid-write crash and the fix is a behaviour change, so treat it as a candidate
only after confirming the partial-write scenario is real) and
`qtr.utils.config.load_config` on malformed YAML (fail-fast is arguably correct). Do not
manufacture a fix without a concrete reachability argument.

**Constraints:** preserve gates/contracts/100% `src/qtr` coverage; do not alter
published/frozen artifacts or thresholds except a deliberate authorized corpus/baseline
update; no workflow commit from agent.