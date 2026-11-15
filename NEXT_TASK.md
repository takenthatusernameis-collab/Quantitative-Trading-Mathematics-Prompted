# NEXT_TASK.md

## Latest session (2026-11-15, Cycle 124) — fixed a real cross-module `annualized_volatility` disagreement at n=1; baseline otherwise unchanged

### What changed
- `src/qtr/validation/statistics.py` (`validate_strategy`): `annualized_volatility`
  now returns `0.0` for a single-observation return series (it returned `NaN`).
  This matches the engine's `VectorizedBacktester._calculate_metrics` n<=1 guard
  (`engine.py:243-246`, pinned by `test_backtest_engine.py:930`). The engine
  reports `0.0`, `validate_strategy` reported `NaN` from `pandas.Series.std()`
  (ddof=1 divides by n-1=0), so the two implementations disagreed on the same
  one-bar return series — the exact class of defect the cross-module agreement
  contract exists to catch. It also makes `validate_strategy` internally
  consistent (its empty-series path already returns `0.0`). For `n > 1` the
  arithmetic is bit-identical to before; no published artifact (n=2515) moves.
- `tests/test_statistics.py`: renamed
  `test_annualized_volatility_single_element_is_nan` →
  `..._single_element_is_zero`; corrected its false "matches the engine
  convention" docstring (it did not).
- `tests/test_engine_metric_agreement.py`: new
  `test_agreement_holds_for_a_single_bar_series` pins the n==1 agreement.
- **Why this over "no work":** the prior two cycles concluded "no agent-actionable
  work" without probing. A systematic edge-case probe of the public API
  (statistics/engine/baselines/fetcher) found this one real divergence; all other
  degenerate inputs were already guarded.

### What was actually verified (own evidence)
- Full canonical gate `pytest -q -W error --cov=qtr --cov-branch
  --cov-report=term-missing` (621s) — **3825 passed, 51 skipped, 7 failed**,
  coverage **100.00%** (`statistics.py` 100%). The +1 vs the prior 3824 is the new
  agreement test; the 7 failures are exclusively the maintainer-gated
  `tests/test_gates_workflow.py`.
- Focused `pytest -q -W error tests/test_statistics.py
  tests/test_engine_metric_agreement.py tests/test_backtest_engine.py
  tests/test_engine_edge_stress.py tests/test_runner_metric_agreement.py
  tests/test_h54_non_metrics_block_disclosure.py` — **405 passed**.
- Reproduced before/after: `validate_strategy([0.0])` `annualized_volatility`
  was `NaN`, now `0.0` == engine `0.0`.
- `ruff check src tests run_*.py scripts` — All checks passed;
  `ruff format --check ...` — 335 files formatted.
- `python scripts/backtest_perf_regression_gate.py` — **PASSED** (0.812s, limit 5s).
- `pytest -q tests/test_reproducibility_audit.py
  tests/test_artifact_restoration_plan.py tests/test_sidecar_schema_contract.py`
  — **16 passed**.
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` — applies cleanly.

### What remains unresolved
1. **Maintainer-only (CI contract):** `.github/workflows/gates.yml` not updated;
   7 `tests/test_gates_workflow.py` tests red until the maintainer applies
   `patches/0001-gates-workflow-contract-fix.patch` with workflow-scoped
   credentials. Agent cannot land `.github/workflows/**`.
2. **Research queue exhausted under free/public PIT data:** H1–H182
   executed/rejected (register Cycles 96/116/118). Do not invent a free-data H183.
3. **Reproducibility backlog:** `missing_files=197`, `hash_mismatches=11`,
   `orphaned_files=528`, `missing_meta_files=0` unchanged; baseline-frozen where
   contract/citation constraints apply.

### Approaches already tried and why they should not be repeated
- Do not re-derive a "H182 is missing from the corpus" finding (false: 174 records).
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or
  alter coverage/frozen-contract gates.
- Do not treat delisted/spliced-continuous/unavailable free series as valid PIT inputs.
- Do not mass-edit runners/tests/gates or frozen artifacts to chase green.
- Do not make speculative `src/qtr` changes absent an evidenced defect.
- **Do not re-open the n==1 `annualized_volatility` case as a deliberate
  divergence.** The engine pins `0.0` (`test_backtest_engine.py:930`) and
  `validate_strategy`'s empty path already returns `0.0`; the old `NaN` plus its
  "matches the engine" docstring were the defect and are now fixed. Re-auditing it
  is wasted work.
- **Do not re-run the generic public-API edge-case probe.** It was completed this
  cycle: statistics/engine/baselines/fetcher degenerate inputs are all guarded; the
  only unguarded divergence found was the n==1 volatility above (now fixed).

### One precise next task
**Maintainer (preferred, unblocks CI):** apply and push
`patches/0001-gates-workflow-contract-fix.patch` with workflow-scoped credentials,
then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on
`origin/main`.

**If research is explicitly authorized:** obtain one paid/PIT data gap (commodity
futures per-contract roll/contango, crypto perpetual funding rates, or historical
options chain/GEX) and run the smallest decisive pre-registered test for that single
mechanism.

**Constraints:** no gate weakening; no modification of published/frozen artifacts,
verdicts, thresholds, or frozen numbers except a deliberate authorized
corpus/baseline update; no commit/push of `.github/workflows/**`; any `src/qtr`
change must preserve 100% coverage and pass ruff/suite.

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