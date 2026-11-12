# REPRODUCIBILITY AUDIT REPORT

**Session:** 2026-11-12
**Task:** Verify all experiment artifacts can be re-derived from tracked metadata (STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §6 fallback path)

---

## Summary

Created and executed `tests/test_reproducibility_audit.py` — a comprehensive audit of the experiment tracking system against `.experiments/experiments.jsonl` (173 experiments, 1,129,171 bytes).

**Audit Status:** **GAPS IDENTIFIED** — The audit test fails as designed, revealing concrete reproducibility gaps that must be addressed before claiming full artifact re-derivability.

---

## Findings

| Check | Status | Count | Details |
|-------|--------|-------|---------|
| Experiments log exists & nonempty | ✅ PASS | 173 experiments | All records parseable |
| Artifact files exist on disk | ❌ FAIL | 346 missing | Referenced parquet/JSON files not found |
| Artifact hashes match recorded values | ❌ FAIL | 11 mismatches | SHA-256 prefix differs from artifact name |
| No orphaned files in artifacts dir | ❌ FAIL | 528 orphaned | Files on disk not referenced by any experiment |
| Experiment metadata completeness | ✅ PASS | 173/173 complete | All required fields present |
| Git commit consistency | ✅ PASS | 173/173 valid | No "unknown" commits |
| Artifact .meta.json files exist | ❌ FAIL | 1,059 missing | Per-artifact metadata not written |

---

## Root Cause Analysis

### 1. Missing Artifact Files (346)
Experiments reference artifact paths under `.experiments/artifacts/<exp_id>/` but those directories/files were never created or were cleaned up. Common pattern: experiment trackers logged artifact *names* with hashes but the actual `log_dataframe` / `log_artifact` calls didn't persist files to the expected locations.

**Most affected experiments:** `h11_robustness_certification`, `h17_vrp`, early TSMOM/CS momentum runs.

### 2. Hash Mismatches (11)
Multiple experiments reference the same logical artifact name (e.g., `param_grid_results_3c3ca96bf45b5f28`) but the file on disk has different content — likely because the same artifact name was reused across experiments with different outputs, or files were overwritten.

**Examples:**
- `param_grid_results_3c3ca96bf45b5f28` expected `3c3ca96bf45b5f28`, actual `2cfbb88200656d0d` (4 experiments)
- `summary_b8cf0dae88579c7a` expected `b8cf0dae88579c7a`, actual `63139e710dc45c09`

### 3. Orphaned Artifact Files (528)
Files exist under `.experiments/artifacts/` but are not referenced by any experiment in `experiments.jsonl`. Includes:
- Entire experiment directories (e.g., `exp_2026-10-14T08-20-16-720432Z/`)
- Shared directories (`h29_lookahead_sweep/`, `h26_sharpe_scale/`)
- Script copies (`run_h9_intraday_tsmom_experiment.py`)

### 4. Missing .meta.json Files (1,059)
The `ExperimentTracker.log_artifact()` writes `.meta.json` only when explicit `metadata` dict is passed. Most historical `log_dataframe()` / `log_artifact()` calls omitted this, so per-artifact metadata (shape, dtypes, index type) was never persisted.

---

## Implications

| Claim | Supported? | Evidence |
|-------|------------|----------|
| "All 173 experiments are fully reproducible from tracked metadata" | ❌ No | 346 missing files, 11 hash mismatches |
| "Artifact hashes in experiment records match on-disk content" | ❌ No | 11 mismatches prove divergence |
| "Every file in .experiments/artifacts/ is accounted for" | ❌ No | 528 orphaned files |
| "Per-artifact metadata (schema, shape) is preserved" | ❌ No | 1,059 missing .meta.json |

**However:** Experiment-level metadata (git commit, dependencies, seeds, config) is **complete and valid** for all 173 experiments. The code version and configuration for every run are recoverable.

---

## Recommended Remediation

1. **Backfill missing artifacts** — Re-run affected experiments (or their artifact-generation steps) to recreate missing parquet/JSON files at expected paths.

2. **Fix hash recording** — Ensure `log_artifact` / `log_dataframe` computes and records hash *after* writing, and that artifact names in `experiments.jsonl` use that exact hash.

3. **Clean or catalog orphaned files** — Either add references to `experiments.jsonl` (if valid) or archive/delete unused artifact directories.

4. **Enforce metadata logging** — Modify `ExperimentTracker.log_dataframe()` to always write `.meta.json` with schema/shape info (currently optional).

5. **Add CI gate** — Run `test_reproducibility_audit.py` in CI to prevent future drift.

---

## Verification Evidence

| Check | Command | Result |
|-------|---------|--------|
| Core unit tests (359) | `pytest tests/test_backtest_engine.py tests/test_config.py tests/test_cost_model.py tests/test_statistics.py tests/test_data_fetcher.py -q` | ✅ 359 passed |
| Edge stress tests | `pytest tests/test_engine_edge_stress.py -q` | ✅ 12 passed |
| Performance regression gate | `pytest tests/test_performance_regression_gate.py -q` | ✅ 1 passed |
| Lint (ruff) | `ruff check src tests run_*.py` | ✅ Clean |
| Format (ruff) | `ruff format --check src tests run_*.py` | ✅ Clean |

---

## Artifacts Created

- `tests/test_reproducibility_audit.py` — Re-runnable audit test (7 checks)
- This report: `REPRODUCIBILITY_AUDIT_REPORT.md`

---

## Next Steps

The audit test is now part of the test suite and will fail until the above gaps are closed. This provides a **measurable, executable definition of "reproducibility"** that can be tracked over time.

Per STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §6, this completes the "Reproducibility audit" fallback item. All four fallback items are now executed:
1. ✅ Performance profiling of backtest engine
2. ✅ Experiment lineage documentation
3. ✅ CI/CD hardening (performance regression gate)
4. ✅ Reproducibility audit (gaps identified, test in place)

**Strategy family discovery remains exhausted at H181 pending data authorization.**