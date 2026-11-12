# NEXT_TASK.md — Experiment Lineage Report Generated; Apply Still Awaits Authorization

## Session Summary (2026-11-12T20:48Z → 2026-11-12T21:00Z)

**Assigned task (from HANDOFF_CURRENT_SESSION.md fallback path):** Document experiment lineage — automated report from `.experiments/experiments.jsonl`.

**Status: Completed and verified.**

### What Changed This Session

- `scripts/generate_experiment_lineage_report.py` — New script to generate comprehensive markdown lineage report from `experiments.jsonl`
- `EXPERIMENT_LINEAGE_REPORT.md` — Generated report (333 lines) documenting all 173 experiment records across 10 categories
- Updated `NEXT_TASK.md` — This file

### Files Not Changed

- `src/qtr/` — **Unchanged** (0 modifications)
- Test suite — Unchanged
- Frozen contracts, gates, thresholds — Unchanged
- Published artifacts, verdicts — Unchanged
- `.experiments/experiments.jsonl` — Read-only source

---

## What Was Verified

| Check | Command | Result |
|-------|---------|--------|
| Core unit tests | `PYTHONPATH=src python -m pytest tests/test_config.py tests/test_cost_model.py tests/test_statistics.py tests/test_backtest_engine.py tests/test_data_fetcher.py -q -W error` | ✅ **359 passed** |
| Lint (ruff) | `python -m ruff check src tests scripts` | ✅ **Clean** |
| Format (ruff) | `python -m ruff format --check src tests scripts` | ✅ **Clean (182 files)** |
| Lineage script execution | `python scripts/generate_experiment_lineage_report.py` | ✅ **Success** — 173 experiments processed, report generated |

---

## Experiment Lineage Report Summary

The generated `EXPERIMENT_LINEAGE_REPORT.md` contains:

- **173 total experiments** parsed from `.experiments/experiments.jsonl`
- **10 categories** with pass/fail/error breakdown:
  - Baseline / MA Crossover: 9 (6 passed, 3 errors)
  - Time-Series Momentum: 60 (41 passed, 16 errors)
  - Cross-Sectional Momentum: 2 (2 passed)
  - Regime-Gated: 5 (5 passed)
  - Volatility / VRP: 9 (5 passed, 2 failed, 2 errors)
  - Volume Predictive: 6 (3 passed, 3 errors)
  - Hypothesis H10-H29: 23 (16 passed, 7 errors)
  - New Family (NF) - Recent: 51 (27 passed, 14 failed, 10 errors)
  - New Family (NF) - Factor/Other: 5 (4 passed, 1 error)
  - Other / Uncategorized: 3 (2 passed, 1 error)
- **Git commit timeline** mapping 42 unique commits to experiment batches and categories
- **Detailed per-experiment records** with timestamps, verdicts, key metrics, configs, artifact counts, and errors

---

## Remaining Unresolved (from previous session)

### Apply is not executed (needs authorization)
The artifact restoration plan (321 hash-exact recoverable files) is ready but blocked on explicit human authorization.

| Backlog | Count | Notes |
|---------|-------|-------|
| Missing referenced files | 346 | 321 hash-exact recoverable (plan exists); 25 unrecoverable |
| Hash mismatches | 11 | Overwritten `param_grid_results`; 3 `summary.json` under `nf_runs` |
| Orphaned files | 528 | Unreferenced files/dirs; deletion would destroy committed data |
| Missing `.meta.json` sidecars | 140 | 118 are `summary.json`; 22 parquet |

Full analysis: `REPRODUCIBILITY_AUDIT_REPORT.md`.

### Strategy family discovery
**Queue exhausted at H181.** H182 unassigned. Cycle 96 blockers remain:
commodity carry, insider transactions, earnings revisions, options dealer GEX,
breakeven inflation, and statistical power for annual events. No free-data
candidate clears the directive bar.

---

## Failed Approaches / Do Not Blindly Repeat

- Do not run `--apply` without explicit human authorization.
- Do not restore the audit to a zero-backlog assertion — it makes the suite and CI red with no signal.
- Do not "fix" the sidecar count by rewriting history; the real count is 140.
- Do not delete orphaned artifacts to make the orphan check pass.
- Do not edit `experiments.jsonl` paths or hashes without authorization.
- Do not modify `src/qtr` for a test-only path mismatch.
- Do not trust a handoff doc's green claim — re-run the suite.
- Do not commit the plan with absolute paths (already fixed: repo-relative).

---

## One Precise Next Task

**Run the apply only after a human explicitly authorizes it.**

Concretely, after authorization:
1. Preview: `python scripts/plan_artifact_restoration.py --apply --dry-run` (prints every target; writes nothing).
2. Apply: `python scripts/plan_artifact_restoration.py --apply` (copies 321 files; refuses to overwrite).
3. Re-run `PYTHONPATH=src python -m pytest tests/test_reproducibility_audit.py -q` and confirm `missing_files` drops 346 → 25.
4. Lower, together and deliberately:
   - `tests/test_reproducibility_audit.py::REPRODUCIBILITY_BASELINE["missing_files"]` 346 → 25
   - `tests/test_artifact_restoration_plan.py::RECOVERABLE_BASELINE` 321 → 0 (unrecoverable stays 25)
5. Regenerate `REPRODUCIBILITY_RESTORATION_PLAN.{md,csv}` (the tool now writes LF and is byte-reproducible) and update `REPRODUCIBILITY_AUDIT_REPORT.md`.
6. Re-run `pytest -q -W error`, ruff check/format, and the coverage gate.

If authorization is **not** granted, close out the reproducibility fallback item and return to strategy-family discovery at H182, documenting that discovery remains blocked on the same six data constraints.

### Fallback audit work remaining (per STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §6):
1. ~~Document experiment lineage — automated report from `.experiments/experiments.jsonl`~~ ✅ **COMPLETED**
2. Stress-test frozen-contract gates against edge cases (NaN prices, extreme leverage, zero-volume, look-ahead boundaries)
3. CI/CD hardening — performance regression gate (e.g., fail if 100-symbol backtest > 5s)
4. Reproducibility audit — verify all artifacts re-derivable from tracked metadata

**Evidence to start from:**
- `REPRODUCIBILITY_RESTORATION_PLAN.csv` — 321 rows, every `source_hash == recorded_hash`, LF endings.
- `scripts/plan_artifact_restoration.py` — `apply_plan()` is the apply source of truth; `--apply` is off by default.
- `tests/test_artifact_restoration_plan.py` — baseline ratchet + apply tests.
- `tests/test_reproducibility_audit.py` — audit baseline to lower after apply.
- `scripts/generate_experiment_lineage_report.py` — lineage report generator.
- `EXPERIMENT_LINEAGE_REPORT.md` — generated lineage report.

**Constraints:**
- `src/qtr` unchanged unless an evidenced defect requires the full gates.
- No artifact deletion, no `experiments.jsonl` rewrite, no gate weakening.
- No commit/push unless requested.
- Do not run `--apply` without explicit authorization.

---
*Updated 2026-11-12T21:00Z: Experiment lineage report generated and verified; core tests 359 passed; lint/format clean. Apply path still blocked on authorization. Next fallback audit item: stress-test frozen-contract gates.*