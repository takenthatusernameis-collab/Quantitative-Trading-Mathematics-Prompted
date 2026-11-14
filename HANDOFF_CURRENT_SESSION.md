# HANDOFF — current session (2026-11-14)

## What changed
- **`scripts/generate_experiment_lineage_report.py`**: fixed a real extraction bug. `config` and `data_sources` are nested under each record's `metadata` (see `ExperimentTracker._save_experiment`), but `extract_key_info` read them from the top level, so every report row rendered `data_source=unknown` with an empty Config column. Now reads `metadata` first (top-level fallback retained for old records) and tolerates both the dict and list `data_sources` shapes.
- **`EXPERIMENT_LINEAGE_REPORT.md`**: regenerated from the unchanged 173-record corpus. Config/Data-source columns now show real values; category summary and total (173) are unchanged.
- **`tests/test_experiment_lineage_report.py`**: added `test_extract_key_info_reads_config_and_data_sources_from_metadata`, pinning that every record with `metadata.config` / `metadata.data_sources` surfaces a non-empty config / non-`unknown` data source.
- **`src/qtr/tracking/__init__.py`**: exported the seven public names already defined in `qtr.tracking.experiment` but missing from the subpackage API (`AblationSummary`, `DataSummary`, `ExperimentSummary`, `GateResult`, `MetricsSummary`, `SelectionSummary`, `emit_summary`). This fixes a **pre-existing full-suite failure** in `tests/test_public_api_contract.py` (the prior handoff incorrectly claimed only the workflow block was red).

## What was actually verified (own evidence)
- `python -m pytest -q tests/test_experiment_lineage_report.py` → **6 passed**.
- `python -m pytest -q tests/test_public_api_contract.py tests/test_experiment_tracker.py` → **62 passed**.
- `python -m pytest -q tests/test_experiment_lineage_report.py tests/test_reproducibility_audit.py tests/test_experiment_artifact_schema.py` → **118 passed**. Reproducibility baseline unchanged (`missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=0`).
- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` → **7 failed, 3822 passed, 51 skipped**; **coverage 100.00%**. The only failures are the 7 maintainer-gated `tests/test_gates_workflow.py` cases. The previous 8th failure (`test_public_api_contract.py::...tracking`) is fixed.
- `python -m ruff check src tests run_*.py scripts` → **All checks passed**.
- `python -m ruff format --check src tests run_*.py scripts` → **335 files already formatted**.
- `python scripts/backtest_perf_regression_gate.py` → **PASSED** (0.416s, limit 5s).

## What remains unresolved
1. **Maintainer-only:** apply `patches/0001-gates-workflow-contract-fix.patch` to `.github/workflows/gates.yml` and push with workflow-scoped credentials to clear the 7 `tests/test_gates_workflow.py` failures. Agent cannot land `.github/workflows/**` (controller restores it from `origin/main`; token lacks `workflows` scope).
2. **Research queue (free/public PIT data) exhausted:** H1–H182 executed/rejected per `NEW_FAMILY_RESEARCH_REGISTER.md` / directive §6. No honest free-data H183 pre-registrable.
3. **H182 lineage gap:** NF-20261110-08 (insider net-buy, REJECTED) is in `.experiments/nf_runs/` (5 summaries, already counted by `test_experiment_artifact_schema.py`) but absent from `experiments.jsonl` / `EXPERIMENT_LINEAGE_REPORT.md`. Closing it requires appending a tracker-format record + `.meta.json` sidecars and re-deriving lineage/audit baselines (pinned 173→174, category summary, reproducibility baseline). The runner (`run_nf_20261110_08_insider_signal.py`) writes `summary.json` directly and never calls `ExperimentTracker`, so a record cannot be reconstructed without fabricating metadata.
4. **Reproducibility backlog:** 197 missing / 11 hash mismatches / 528 orphans remain baseline-frozen (`REPRODUCIBILITY_AUDIT_REPORT.md`); 172 missing are H28 depth-one contract-blocked, 25 unrecoverable.

## Approaches already failed / must not be repeated
- Re-running exhaustion-only discovery without new data authorization or a directive §6 shift.
- Editing `.github/workflows/**`, weakening `tests/test_gates_workflow.py`, or relaxing coverage/frozen-contract gates.
- Treating delisted/spliced/unavailable free series as PIT-valid (OVX, VIX9D, ^RVX; spliced `=F`; no free crypto funding).
- Mass edits to runners/tests/gates/frozen artifacts to force green; raising the reproducibility baseline instead of remediating drift.
- Appending an H182 record to `experiments.jsonl` without sidecars + coordinated baseline/pinned-test updates (ratchet fails).
- Speculative `src/qtr` changes absent an evidenced defect (this session's `tracking/__init__.py` change is evidenced by `test_public_api_contract.py`).

## One precise next task
**Maintainer (preferred):** apply/push `patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then verify `python -m pytest -q tests/test_gates_workflow.py` → 7 passed. **Authorized research alternative:** secure one paid/PIT data gap (commodity per-contract roll/contango, crypto perpetual funding, or historical options chain/GEX) and run the smallest decisive pre-registered test (no invented free-data H183). **Authorized bookkeeping alternative:** close the H182 lineage gap by appending NF-20261110-08 to `experiments.jsonl` with `.meta.json` sidecars and re-deriving lineage/audit baselines and pinned tests.

**Constraints:** preserve gates/contracts/100% `src/qtr` coverage; do not alter published/frozen artifacts or thresholds except a deliberate authorized corpus/baseline update; no workflow commit from agent.