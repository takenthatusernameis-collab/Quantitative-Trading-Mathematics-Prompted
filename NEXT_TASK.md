# NEXT_TASK.md

## Latest session (2026-11-15, Cycle 126) — closed the duplicate-**column** label crash class; 100% coverage preserved

### What changed
Cycle 125 closed the duplicate-**index** guard in `run_backtest` and pointed the next session at the remaining public surface for duplicate/degenerate shapes. I fuzzed the public API (engine, statistics, strategies, fetcher, tracking) with degenerate frames and found one reproduced crash class left: **duplicate column labels**.

- **`non_positive_prices(panel)` — `TypeError: float()/pd.to_numeric() argument must be a list, tuple, 1-d array, or Series` on a duplicated column label.** The screen did `panel[column]` (fetcher.py:59/61); when `column` is duplicated that returns a *DataFrame*, and `pd.to_numeric(DataFrame)` raises. Reproduced two ways (duplicate `close` label in a long frame; duplicate symbol label in a wide frame). This is the *first* thing `run_backtest` calls, so the engine crashed before any of its own guards.
- **Reachability (why it is a real defect, not a synthetic fixture):** the documented pipeline builds wide panels with `pd.concat(..., axis=1)` (e.g. `run_nf_*`: `pd.concat(prices_list/frames.values(), axis=1)`), so two frames that share a symbol name — a repeated ticker in a universe, or an overlapping benchmark/universe concatenation — produce a duplicated column. The cached/vendor read path also does not dedup columns. The screen's own contract is "Empty when the panel is clean", i.e. it is a screen, not a crash point.
- **Fix 1 (`non_positive_prices`):** iterate columns **by position** (`panel.iloc[:, i]`) so every column is a `Series` regardless of how many labels share its name. `PRICE_COLUMNS` order is preserved, so the offending-observation order (and the first row the fetcher names in its error) is bit-identical on the clean path. `src/qtr/data/fetcher.py`.
- **Fix 2 (`run_backtest`):** canonicalize duplicate **columns** once on entry (keep first), mirroring the existing duplicate-index guard, for both `prices` and `signals`. Without this the engine would still crash at `signals.reindex(..., columns=columns)` (`ValueError: cannot reindex on an axis with duplicate labels`) even after the screen was fixed. A unique column set is a no-op, so the clean path is bit-identical. `src/qtr/backtest/engine.py` (+16 lines).
- **Tests:** `tests/test_h58_price_pathology_contamination.py::TestDuplicateColumnLabels` (+5: duplicate price label, duplicate wide label, clean duplicate panel, PRICE_COLUMNS order preserved, negative control reconstructing the pre-fix `pd.to_numeric(DataFrame)` TypeError). `tests/test_engine_edge_stress.py::TestDuplicateColumns` (+4: duplicate price columns, duplicate signal columns, unique columns untouched, negative control reconstructing the pre-fix `reindex` ValueError). +9 tests.

### What was actually verified (own evidence)
- `pytest -q tests/test_engine_edge_stress.py tests/test_h58_price_pathology_contamination.py tests/test_data_fetcher.py tests/test_backtest_engine.py` — **177 passed**.
- Full pinned suite `pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py` (335.94s) — **3850 passed, 48 skipped, coverage 100.00%** (+9 vs. the 3841 baseline; the 48 skips are the pre-existing H51/H29/H28/causality skips). `src/qtr/data/fetcher.py` = 100% (219 stmts, 82 branches); `src/qtr/backtest/engine.py` = 100% (237 stmts, 84 branches).
- **Negative control:** `git stash push src/qtr/data/fetcher.py src/qtr/backtest/engine.py` then re-running the two new classes → the 5 positive tests fail with the exact pre-fix errors (`TypeError: arg must be ... not 'Series'` ×4; `ValueError: cannot reindex on an axis with duplicate labels` ×1), the 4 negative-control/unique tests pass. Restored via `git stash pop`.
- `pytest -q tests/test_gates_workflow.py` — **7 failed** (unchanged, exclusively the maintainer-gated block; fix is `patches/0001-gates-workflow-contract-fix.patch`).
- `ruff check src tests run_*.py scripts` — All checks passed. `ruff format --check ...` — 335 files already formatted.

### What remains unresolved
Same three blocked items as Cycle 125: (1) maintainer-only `.github/workflows/gates.yml` patch; (2) H182/H183 research needs data authorization (free-data queue exhausted per register Cycle 116); (3) reproducibility backlog baseline-frozen at 197/11/528/0.

### Approaches already tried and why they should not be repeated
- Do not re-audit the duplicate-**index** guard or the duplicate-**column** guard — both are now closed and pinned with negative controls.
- Do not re-fuzz the H182 runner's private helpers with malformed frames (`_net_buy_ratio_by_signal_day` / `_compute_daily_signals` raise `KeyError`/`TypeError` on frames missing `transaction_code`/`available_at`) — outside the runner's own contract; not an evidenced defect.
- Do not re-fuzz `qtr.validation.statistics` — closed in Cycles 124/125; all public functions are guarded (only the intended `ValueError` on an unknown `multiple_testing_correction` method remains).
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or alter coverage/frozen-contract gates.
- Do not treat delisted/spliced-continuous/unavailable free series as valid PIT inputs.
- Do not append H182/H183 to `experiments.jsonl` without sidecars + coordinated baseline/pinned-test updates.
- Do not make speculative `src/qtr` changes absent an evidenced defect (this session's two guards are each evidenced by a reproduced crash).

### One precise next task
**Maintainer (preferred, unblocks CI):** apply and push `patches/0001-gates-workflow-contract-fix.patch`, then `pytest -q tests/test_gates_workflow.py` (expect 7 passed) on `origin/main`.

**Agent alternative if another evidenced defect is wanted:** the duplicate-label class (index + columns) is now closed on both axes. The remaining public surface not yet exercised for degenerate shapes is `qtr.tracking.experiment` on malformed `experiments.jsonl` (a partial/interleaved append makes `load_experiment`/`list_experiments` raise `JSONDecodeError`/`KeyError` — reproduced, but reachability requires a mid-write crash and the fix is a behavior change, so treat it as a candidate only after confirming the partial-write scenario is real) and `qtr.utils.config.load_config` on malformed YAML (fail-fast is arguably correct). Do not manufacture a fix without a concrete reachability argument.

---

## Prior session (2026-11-15, Cycle 125) — fixed an evidenced engine crash on a duplicated index label; 100% coverage preserved

### What changed
Cycle 124 closed the `qtr.validation.statistics` shape guards and suggested fuzzing the runner-side glue. I fuzzed the *engine* instead (the most-used public entry point, `run_backtest`, and the layer every runner funnels into) and found one genuine, reproduced, deterministic crash — not a malformed-frame curiosity:

- **`run_backtest` — `TypeError: float() argument must be a string or a real number, not 'Series'` on a duplicated index label.** The trade log does `price = float(prices.loc[ts, sym])` (engine.py:444). When `ts` is a *duplicated* index label, `.loc[ts, sym]` returns a Series and `float()` raises. `signals.reindex(index=prices.index, ...)` also raises `ValueError: cannot reindex on an axis with duplicate labels` before that, so a duplicated index crashes the engine two different ways depending on which panel carries it.

  **Reachability (why this is a real defect, not a synthetic fixture):** the documented pipeline can produce a duplicated index. `fetch_ccxt` already guards with `~df.index.duplicated(keep="first").sort_index()` (fetcher.py:407), but `fetch_yahoo`/`fetch_futures` (`_fetch_yahoo_panel`, fetcher.py:215-216) and the cached read path (`DataCache.get`, fetcher.py:92-100) do **not** dedup, and a cache entry written before dedup / an overlapping vendor window carries the duplicate straight through. The runners then `pd.concat(..., axis=1).sort_index()` the per-symbol closes (`run_nf_*`, `run_h*`) and hand the panel to `run_backtest` with no dedup, so the duplicate reaches the engine.

- **Fix:** canonicalize the index once at the top of `run_backtest` (keep first, then sort) for both `prices` and `signals`, mirroring the CCXT branch's existing policy. A unique index is a no-op, so the clean path is **bit-identical**. `src/qtr/backtest/engine.py` (+14 lines, one guard each for prices and signals).

- **Tests:** `tests/test_engine_edge_stress.py` — new `TestDuplicateIndex` with `test_duplicate_price_index_with_a_trade_at_the_dup_does_not_crash`, `test_duplicate_signal_index_does_not_crash`, `test_unique_index_is_untouched_by_the_dedup_guard`, and `test_the_contract_rejects_the_pre_fix_duplicate_index_crash` (negative control reconstructing the pre-fix `float(Series)` TypeError). +4 tests.

### What was actually verified (own evidence)
- `pytest -q tests/test_engine_edge_stress.py` — **16 passed** (was 12).
- `pytest -q tests/test_backtest_engine.py tests/test_engine_edge_stress.py tests/test_engine_metric_agreement.py tests/test_engine_total_return_consistency.py tests/test_frozen_contract_gates_edge_stress.py tests/test_gate_evaluation_edge_stress.py` — **253 passed**.
- Full pinned suite `pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py` (332s) — **3841 passed, 48 skipped, coverage 100.00%** (+4 vs. the 3837 baseline; the 48 skips are the pre-existing H51/H29/H28/causality skips). `src/qtr/backtest/engine.py` = 100% (233 stmts, 80 branches).
- **Negative control:** `git stash`-ing only `engine.py` and re-running `TestDuplicateIndex` → the two positive tests fail with the exact pre-fix errors (`TypeError: float() argument ... not 'Series'` and `ValueError: cannot reindex on an axis with duplicate labels`); the negative-control test passes. Restored via `git stash pop`.
- `pytest -q tests/test_gates_workflow.py` — **7 failed** (unchanged, exclusively the maintainer-gated block; fix is `patches/0001-gates-workflow-contract-fix.patch`).
- `ruff check src tests run_*.py scripts` — All checks passed. `ruff format --check ...` — 335 files already formatted (after formatting the new test).

### What remains unresolved
Same three blocked items as Cycle 124: (1) maintainer-only `.github/workflows/gates.yml` patch; (2) H182 research needs data authorization; (3) reproducibility backlog baseline-frozen at 197/11/528/0.

### Approaches already tried and why they should not be repeated
- Do not re-audit `regime_analysis` / `parameter_sensitivity` (closed in Cycle 124 with negative controls).
- Do not re-fuzz the H182 runner's private helpers with malformed frames (`_net_buy_ratio_by_signal_day` / `_compute_daily_signals` raise `KeyError`/`TypeError` on frames missing `transaction_code`/`available_at`) — those are outside the runner's own contract (the corpus builder always supplies those columns), so they are not evidenced defects. Fix only a reproduced crash reachable from a real pipeline.
- Do not re-audit the duplicate-index guard — it is now closed and pinned.
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or alter coverage/frozen-contract gates.
- Do not treat delisted/spliced-continuous/unavailable free series as valid PIT inputs.
- Do not append H182 to `experiments.jsonl` without sidecars + coordinated baseline/pinned-test updates.
- Do not make speculative `src/qtr` changes absent an evidenced defect (this session's guard is evidenced by a reproduced crash reachable from `fetch_yahoo`/`fetch_futures` + the runners' `pd.concat` panel build).

### One precise next task
**Maintainer (preferred, unblocks CI):** apply and push `patches/0001-gates-workflow-contract-fix.patch`, then `pytest -q tests/test_gates_workflow.py` (expect 7 passed) on `origin/main`. **No further agent-actionable engine crash is known this session.** If another evidenced defect is wanted, the next place to fuzz is the remaining public `src/qtr` surface not yet exercised for duplicate/degenerate shapes — e.g. `qtr.data.fetcher.fetch_ccxt` column-standardization on a short/odd vendor frame, or `qtr.tracking.experiment` methods on malformed artifact paths — and fix only a reproduced crash with a real-pipeline reachability argument.

---

## Prior session (2026-11-15, Cycle 124) — fixed two crash-on-malformed-shape defects in the statistics core; 100% coverage preserved

### What changed
The prior handoff (Cycle 123) claimed "no agent-actionable work remains" and instructed the next session to only re-verify. Per the operating rules (make durable progress; do not passively re-verify), I independently reproduced the baseline (green: 3827 passed / 48 skipped, only the 7 maintainer-gated `tests/test_gates_workflow.py` red) and then fuzzed the public `qtr.validation.statistics` API for the same degenerate-input crash class this repo has been systematically closing (empty / non-finite / degenerate → fail closed, never crash). Two genuine, reproduced crashes remained:

- **`regime_analysis(returns, regime_labels)` — `IndexError` on a length/shape mismatch.** A per-regime statistic pairs each return with the label at the same position, but the function never checked that `len(returns) == len(labels)` or that both are 1-D. A length mismatch walked into `returns[labels == regime]` → `IndexError: boolean index did not match indexed array`; a scalar `returns` raised `too many indices`; a 2-D `returns` silently selected rows instead of observations. Now normalizes both to arrays and fails closed to `{}` unless both are 1-D and equal length. `src/qtr/validation/statistics.py`.
- **`parameter_sensitivity(returns, param_values)` — `TypeError` on a non-2-D `returns`.** The documented contract is `"2D: n_params x n_obs"`, but a long 1-D series has `shape[0] == len`, so it slipped past the existing `shape[0] < n_params` guard and the per-row loop then scored a *scalar*; `bootstrap_confidence_interval` reduced that to a 0-D array and `len()` of it raised `TypeError: len() of unsized object`. A 0-D input failed even earlier on `shape[0]`; a 3-D input scored 2-D slices. Now reduces `returns` to an ndarray once and fails closed to the empty-grid tuple unless it is 2-D with enough rows. `src/qtr/validation/statistics.py`.

Both fixes are the exact pattern the module already uses for every other degenerate-input class (fail closed, no warning, no exception, bit-identical on the valid domain).

- **Tests:** `tests/test_statistics.py` — added to `TestRegimeAnalysis`: `test_length_mismatch_between_returns_and_labels_fails_closed` (2 params), `test_non_1d_inputs_fail_closed` (3 params), `test_the_contract_rejects_the_pre_fix_length_mismatch_crash` (behavioural negative control that reconstructs the pre-fix `IndexError`). Added to `TestParameterSensitivity`: `test_one_dimensional_returns_fail_closed`, `test_scalar_returns_fail_closed`, `test_three_dimensional_returns_fail_closed`, `test_the_contract_rejects_the_pre_fix_one_dimensional_crash` (negative control). +10 tests.

### What was actually verified (own evidence)
- `pytest -q tests/test_statistics.py` — **199 passed** (was 189).
- `pytest -q tests/test_statistics.py tests/test_engine_metric_agreement.py tests/test_parameter_sensitivity_reproducibility.py tests/test_engine_edge_stress.py` — **297 passed**.
- Full pinned suite `pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py` (336s) — **3837 passed, 48 skipped, coverage 100.00%** (+10 vs. the 3827 baseline; the 48 skips are the pre-existing H51/H29/H28/causality skips). `src/qtr/validation/statistics.py` = 100% (337 stmts, 124 branches).
- `pytest -q tests/test_gates_workflow.py` — **7 failed** (unchanged, exclusively the maintainer-gated block; the fix is `patches/0001-gates-workflow-contract-fix.patch`).
- `ruff check src tests run_*.py scripts` — All checks passed. `ruff format --check ...` — 335 files already formatted.
- Behavioural proof (direct calls): every previously-crashing malformed input now returns the empty/empty-grid result; valid inputs are bit-identical (spot-checked `regime_analysis` keys and `parameter_sensitivity` metrics/optimal_param).

### What remains unresolved
Same three blocked items as Cycle 123: (1) maintainer-only `.github/workflows/gates.yml` patch; (2) H182 research needs data authorization; (3) reproducibility backlog baseline-frozen at 197/11/528/0.

### Approaches already tried and why they should not be repeated
- Do not re-derive a "H182 is missing from the corpus" finding (false: 174 records; H182 is record 174).
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or alter coverage/frozen-contract gates.
- Do not treat delisted/spliced-continuous/unavailable free series as valid PIT inputs.
- Do not mass-edit runners/tests/gates or frozen artifacts to chase green, or raise the reproducibility baseline instead of remediating.
- Do not append H182 to `experiments.jsonl` without sidecars + coordinated baseline/pinned-test updates.
- Do not make speculative `src/qtr` changes absent an evidenced defect (this session's two guards are each evidenced by a reproduced crash).
- **Do not re-audit the `regime_analysis` / `parameter_sensitivity` shape guards** — they are now closed and pinned with negative controls. The remaining public-API functions in `statistics.py` (`sharpe_ratio`, `bootstrap_confidence_interval`, `compare_to_benchmark`, `stressed_cost_test`, `capacity_estimate`, `statistical_power_analysis`, `validate_strategy`, `benchmark_significance_gate`, `multiple_testing_correction`, the split generators) were fuzzed this session and are already guarded; the only remaining "crash" is the intended `ValueError` on an unknown `multiple_testing_correction` method.

### One precise next task
**Maintainer (preferred, unblocks CI):** apply and push `patches/0001-gates-workflow-contract-fix.patch`, then `pytest -q tests/test_gates_workflow.py` (expect 7 passed) on `origin/main`. **No further agent-actionable statistics-core crash is known this session.** If another evidenced defect is wanted, fuzz the runner-side glue (`run_*.py`) rather than the pure functions, and fix only a reproduced crash.

---

## Prior session (2026-11-14, Cycle 123) — baseline re-confirmed green; no agent-actionable work

### What changed
None. Working tree clean at `origin/main` (63813d7); the prior session's KeyError fix in `scripts/fetch_h182_insider_data.py` is already committed. No `src/qtr`, test, gate, artifact, sidecar, hash, frozen-number, or workflow change.

### What was actually verified (own evidence)
- `pytest -q tests/test_reproducibility_audit.py tests/test_fetch_h182_insider_data.py` — **14 passed**.
- `python -m ruff check src tests run_*.py scripts` — All checks passed; `ruff format --check src tests run_*.py scripts` — 335 files formatted.
- Baseline green per Cycle 122: full suite **3824 passed / 51 skipped / 7 failed** (all 7 = maintainer-gated `tests/test_gates_workflow.py`); `src/qtr` coverage **100%**.

### What remains unresolved
Same three blocked items as Cycle 122: (1) maintainer-only `.github/workflows/gates.yml` patch; (2) H182 research needs data authorization; (3) reproducibility backlog baseline-frozen at 197/11/528/0.

### One precise next task
Unchanged: maintainer applies and pushes `patches/0001-gates-workflow-contract-fix.patch`, then `pytest -q tests/test_gates_workflow.py` (expect 7 passed). **No agent-actionable code change exists this session — do not make speculative edits.**

---

## Prior session (2026-11-14, Cycle 122) — fixed H182 fetch-script crash on unknown `--symbols`; audited KeyError pattern across all entry points; no gate/artifact/workflow change

### What changed
- `scripts/fetch_h182_insider_data.py`: new `requested_symbols(raw)` normalizes (strip/upper) the `--symbols` list and validates every token against `UNIVERSE` **before any fetch or cache write**. Previously `cik = UNIVERSE[sym]` inside the per-symbol loop raised a bare `KeyError` on an unknown symbol *mid-run*, after partial cache writes but before the manifest was persisted (silently incomplete corpus, opaque traceback). Unknown symbols now raise `SystemExit` listing the offenders + the known set. `src/qtr` untouched.
- `tests/test_fetch_h182_insider_data.py`: 2 new regression cases (`test_unknown_symbol_fails_before_any_fetch_or_cache_write`, `test_requested_symbols_normalizes_case_and_whitespace`).

### What was actually verified (own evidence)
- `pytest -q tests/test_fetch_h182_insider_data.py` — **7 passed** (was 5).
- `pytest -q tests/test_sec_insider.py tests/test_nf_20261110_08_insider_signal.py tests/test_reproducibility_audit.py tests/test_sidecar_schema_contract.py` — **67 passed**.
- Full pinned suite `pytest -q -W error` (375s) — **3824 passed, 51 skipped, 7 failed**; +2 vs 3822 is the two new tests; the 7 are exclusively the maintainer-gated `tests/test_gates_workflow.py`.
- `ruff check src tests run_*.py scripts` — All checks passed. `ruff format --check ...` — 335 files already formatted.
- Behavioral proof (fetch stubbed): `--symbols " aapl "` resolves + writes manifest; `--symbols AAPL,TSLA` → `SystemExit`, 0 fetch calls, empty cache dir.
- **KeyError pattern audit complete:** searched all `scripts/` and `run_*.py` entry points for bare-`KeyError`-after-partial-writes when indexing a dict by CLI/argument value. **No additional instances found.** The only such pattern was in `fetch_h182_insider_data.py` (already fixed). All other runners use only `--out`/`--smoke` flags and iterate over fixed lists, not user-indexed mappings.

### What remains unresolved
1. **Maintainer-only (CI contract):** `.github/workflows/gates.yml` not updated; 7 `tests/test_gates_workflow.py` tests red until the maintainer applies `patches/0001-gates-workflow-contract-fix.patch` with workflow-scoped credentials. Agent cannot land `.github/workflows/**`.
2. **Research queue exhausted under free/public PIT data:** H1–H182 executed/rejected (register Cycles 96/116/118). Do not invent a free-data H183.
3. **Reproducibility backlog:** `missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=0` unchanged; baseline-frozen where contract/citation constraints apply.

### Approaches already tried and why they should not be repeated
- Do not re-derive a "H182 is missing from the corpus" finding (false: 174 records; H182 is record 174).
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or alter coverage/frozen-contract gates.
- Do not treat delisted/spliced-continuous/unavailable free series as valid PIT inputs.
- Do not mass-edit runners/tests/gates or frozen artifacts to chase green, or raise the reproducibility baseline instead of remediating.
- Do not append H182 to `experiments.jsonl` without sidecars + coordinated baseline/pinned-test updates.
- Do not make speculative `src/qtr` changes absent an evidenced defect.
- Do not change `log_artifact` to always write a sidecar without a coordinated `missing_meta_files` baseline + sidecar-schema update (an empty `{}` sidecar fails the JSON `keys` contract; `test_log_artifact_without_metadata` pins the current falsy-metadata branch).
- **Do not re-audit the KeyError pattern** — it is complete; no further entry points exhibit this defect.

### One precise next task
**Maintainer (preferred, unblocks CI):** apply and push `patches/0001-gates-workflow-contract-fix.patch` with workflow-scoped credentials, then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on `origin/main`.

**If research is explicitly authorized:** obtain one paid/PIT data gap (commodity futures per-contract roll/contango, crypto perpetual funding rates, or historical options chain/GEX) and run the smallest decisive pre-registered test for that single mechanism.

**Constraints:** no gate weakening; no modification of published/frozen artifacts, verdicts, thresholds, or frozen numbers except a deliberate authorized corpus/baseline update; no commit/push of `.github/workflows/**`; any `src/qtr` change must preserve 100% coverage and pass ruff/suite.

---

## Prior session (2026-11-14) — closed H182 lineage gap; fixed two evidenced defects; no workflow/artifact baseline change

### What changed
- `scripts/generate_experiment_lineage_report.py`: `extract_key_info` now reads `config` and `data_sources` from each record's `metadata` (tracker format) instead of the top level; tolerates dict/list `data_sources`. Previously every row rendered `data_source=unknown` with an empty Config column.
- `EXPERIMENT_LINEAGE_REPORT.md`: regenerated from the updated 174-record corpus (H182 added; real Config values; totals/category summary updated).
- `tests/test_experiment_lineage_report.py`: new regression test pinning config/data_source extraction from `metadata`; pinned totals updated (173→174, NF-Recent 51→52, failed 14→15).
- `src/qtr/tracking/__init__.py`: exported the 7 public names already defined in `qtr.tracking.experiment` but missing from the subpackage API (`AblationSummary`, `DataSummary`, `ExperimentSummary`, `GateResult`, `MetricsSummary`, `SelectionSummary`, `emit_summary`).
- `.experiments/experiments.jsonl`: appended tracker-format record for NF-20261110-08 (H182, insider net-buy, REJECT) with `metadata.config`, `metadata.data_sources`, and proper `status.verdict`.
- `.experiments/*.meta.json`: created 3 sidecars for the new artifacts (`summary.json`, `corpus_info.json`, `grid.csv`).
- **`REPRODUCIBILITY_AUDIT_REPORT.md`: corrected a stale, factually wrong section.** The "H182 lineage reconciliation" block claimed `experiments.jsonl` held 173 records with 0 `insider` records and that H182 was a lineage gap. Verified false: the corpus is **174** records and H182 is present (record 174, `exp_2026-11-14T11-39-15Z`, REJECT, 3 artifacts on disk under `.experiments/nf_runs/`). The earlier finding was drawn from a stale corpus count. All "173 experiments" prose in the report was updated to 174. Documentation-only: no artifact, sidecar, hash, gate, or frozen number was modified; the four baseline counts are unchanged.

### What was actually verified (own evidence)
- `python -m pytest -q tests/test_experiment_lineage_report.py` — **6 passed**.
- `python -m pytest -q tests/test_reproducibility_audit.py` — **7 passed** (backlog unchanged: missing=197, hash_mismatches=11, orphans=528, missing_meta=0).
- `python -m pytest -q tests/test_public_api_contract.py tests/test_experiment_tracker.py` — **62 passed**.
- `python -m pytest -q tests/test_experiment_artifact_schema.py` — **105 passed**.
- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` — **7 failed, 3822 passed, 51 skipped**, coverage **100.00%**. Only failures are the 7 maintainer-gated `tests/test_gates_workflow.py` cases; the pre-existing `test_public_api_contract.py::...tracking` failure is fixed.
- `python -m ruff check src tests run_*.py scripts` — **All checks passed**.
- `python -m ruff format --check src tests run_*.py scripts` — **335 files already formatted**.
- `python scripts/backtest_perf_regression_gate.py` — **PASSED** (0.426s, limit 5s).

### What remains unresolved
1. **Maintainer-only (CI contract):** `.github/workflows/gates.yml` not updated; 7 `tests/test_gates_workflow.py` tests red until the maintainer applies `patches/0001-gates-workflow-contract-fix.patch` with workflow-scoped credentials. Agent cannot land `.github/workflows/**`.
2. **Research queue exhausted under free/public PIT data:** H1–H182 executed/rejected (register Cycles 96/116/118). Do not invent a free-data H183.
3. **Reproducibility backlog:** `missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=0` unchanged; baseline-frozen where contract/citation constraints apply.

### Approaches already tried and why they should not be repeated
- Do not re-run exhaustion-only discovery without new data authorization or a §6 shift.
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or alter coverage/frozen-contract gates.
- Do not treat delisted/spliced-continuous/unavailable free series as valid PIT inputs.
- Do not mass-edit runners/tests/gates or frozen artifacts to chase green, or raise the reproducibility baseline instead of remediating.
- Do not append H182 to `experiments.jsonl` without sidecars + coordinated baseline/pinned-test updates.
- Do not make speculative `src/qtr` changes absent an evidenced defect (this session's `tracking/__init__.py` fix is evidenced by `test_public_api_contract.py`).
- **Do not re-derive a "H182 is missing from the corpus" finding.** It is false: `experiments.jsonl` holds **174** records and H182 is present (record 174, `exp_2026-11-14T11-39-15Z`, REJECT, 3 artifacts on disk under `.experiments/nf_runs/`). The prior sweep erred by counting a stale 173-record file and by searching for a substring (`insider`) that does match the committed name `nf_20261110_08_insider_signal`. Always count the corpus directly before drawing lineage conclusions.

### One precise next task
**Maintainer (preferred, unblocks CI):** apply and push `patches/0001-gates-workflow-contract-fix.patch` with workflow-scoped credentials, then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on `origin/main`. **If research is explicitly authorized:** obtain one paid/PIT data gap (commodity futures per-contract roll/contango, crypto perpetual funding rates, or historical options chain/GEX) and run the smallest decisive pre-registered test for that single mechanism.

**Constraints:** no gate weakening; no modification of published/frozen artifacts, verdicts, thresholds, or frozen numbers except a deliberate authorized corpus/baseline update; no commit/push of `.github/workflows/**`; any `src/qtr` change must preserve 100% coverage and pass ruff/suite.