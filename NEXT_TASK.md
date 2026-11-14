# NEXT_TASK.md

## Latest session (2026-11-14) — fixed two evidenced defects; no workflow/artifact baseline change

### What changed
- `scripts/generate_experiment_lineage_report.py`: `extract_key_info` now reads `config` and `data_sources` from each record's `metadata` (tracker format) instead of the top level; tolerates dict/list `data_sources`. Previously every row rendered `data_source=unknown` with an empty Config column.
- `EXPERIMENT_LINEAGE_REPORT.md`: regenerated from the unchanged 173-record corpus (real Config values; totals/category summary unchanged).
- `tests/test_experiment_lineage_report.py`: new regression test pinning config/data_source extraction from `metadata`.
- `src/qtr/tracking/__init__.py`: exported the 7 public names already defined in `qtr.tracking.experiment` but missing from the subpackage API (`AblationSummary`, `DataSummary`, `ExperimentSummary`, `GateResult`, `MetricsSummary`, `SelectionSummary`, `emit_summary`).

### What was actually verified (own evidence)
- `python -m pytest -q tests/test_experiment_lineage_report.py` — **6 passed**.
- `python -m pytest -q tests/test_public_api_contract.py tests/test_experiment_tracker.py` — **62 passed**.
- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` — **7 failed, 3822 passed, 51 skipped**, coverage **100.00%**. Only failures are the 7 maintainer-gated `tests/test_gates_workflow.py` cases; the pre-existing `test_public_api_contract.py::...tracking` failure is fixed.
- `python -m ruff check src tests run_*.py scripts` — **All checks passed**.
- `python -m ruff format --check src tests run_*.py scripts` — **335 files already formatted**.
- `python scripts/backtest_perf_regression_gate.py` — **PASSED** (0.416s, limit 5s).

### What remains unresolved
1. **Maintainer-only (CI contract):** `.github/workflows/gates.yml` not updated; 7 `tests/test_gates_workflow.py` tests red until the maintainer applies `patches/0001-gates-workflow-contract-fix.patch` with workflow-scoped credentials. Agent cannot land `.github/workflows/**`.
2. **Research queue exhausted under free/public PIT data:** H1–H182 executed/rejected (register Cycles 96/116/118). Do not invent a free-data H183.
3. **H182 lineage gap:** NF-20261110-08 (insider net-buy, REJECTED) is in `.experiments/nf_runs/` (5 summaries, counted by `test_experiment_artifact_schema.py`) but absent from `experiments.jsonl` / `EXPERIMENT_LINEAGE_REPORT.md`. Closing it needs a tracker-format record + `.meta.json` sidecars and re-derived lineage/audit baselines (pinned total 173→174, category summary, reproducibility baseline). The runner writes `summary.json` directly and never calls `ExperimentTracker`.
4. **Reproducibility backlog:** `missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=0` unchanged; baseline-frozen where contract/citation constraints apply.

### Approaches already tried and why they should not be repeated
- Do not re-run exhaustion-only discovery without new data authorization or a §6 shift.
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or alter coverage/frozen-contract gates.
- Do not treat delisted/spliced-continuous/unavailable free series as valid PIT inputs.
- Do not mass-edit runners/tests/gates or frozen artifacts to chase green, or raise the reproducibility baseline instead of remediating.
- Do not append H182 to `experiments.jsonl` without sidecars + coordinated baseline/pinned-test updates.
- Do not make speculative `src/qtr` changes absent an evidenced defect (this session's `tracking/__init__.py` fix is evidenced by `test_public_api_contract.py`).

### One precise next task
**Maintainer (preferred, unblocks CI):** apply and push `patches/0001-gates-workflow-contract-fix.patch` with workflow-scoped credentials, then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on `origin/main`. **If research is explicitly authorized:** obtain one paid/PIT data gap (commodity futures per-contract roll/contango, crypto perpetual funding rates, or historical options chain/GEX) and run the smallest decisive pre-registered test for that single mechanism. **Alternative (authorized bookkeeping):** close the H182 lineage gap by appending NF-20261110-08 to `experiments.jsonl` with `.meta.json` sidecars and re-deriving `REPRODUCIBILITY_AUDIT_REPORT` baseline plus pinned expectations in `tests/test_experiment_lineage_report.py` and `tests/test_reproducibility_audit.py`.

**Constraints:** no gate weakening; no modification of published/frozen artifacts, verdicts, thresholds, or frozen numbers except a deliberate authorized corpus/baseline update; no commit/push of `.github/workflows/**`; any `src/qtr` change must preserve 100% coverage and pass ruff/suite.