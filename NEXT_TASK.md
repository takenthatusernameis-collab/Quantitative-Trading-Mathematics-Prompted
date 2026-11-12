# NEXT_TASK.md — Suite green after trade-log inventory fix; blocked on authorization/data (2026-11-12)

## Current status (verified this session)
- Full pinned gates are GREEN after fixing the one real failure:
  - `python3 -m pytest -q -W error` → **3730 passed, 51 skipped, 0 failed**
  - `python3 -m ruff check src tests run_*.py` → clean
  - `python3 -m ruff format --check src tests run_*.py` → 321 files already formatted
  - `python3 -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` → **100.00%** `src/qtr`
- The prior handoff's "0 failed" claim was stale/wrong: the suite had **1 failed** on a clean
  checkout (`tests/test_trade_log_cost_reconciliation.py`), now fixed. See `HANDOFF_CURRENT_SESSION.md`.

## §6 fallback audit items (already complete/pinned; do not re-implement)
| Item | Evidence |
|---|---|
| Backtest engine performance profiling | `run_backtest_perf_profile.py`, `.experiments/backtest_perf_profile.csv`, `BACKTEST_PERF_PROFILE_RESULTS.md` |
| Experiment lineage report | `scripts/generate_experiment_lineage_report.py`, `EXPERIMENT_LINEAGE_REPORT.md` |
| Frozen-contract/gate edge stress | `tests/test_frozen_contract_gates_edge_stress.py`, `tests/test_gate_evaluation_edge_stress.py`, `tests/test_engine_edge_stress.py` |
| CI performance regression gate | `tests/test_performance_regression_gate.py`, `.github/workflows/gates.yml` |
| Reproducibility audit + baseline ratchet | `tests/test_reproducibility_audit.py`, `REPRODUCIBILITY_AUDIT_REPORT.md`, `REPRODUCIBILITY_RESTORATION_PLAN.md/csv`, `scripts/plan_artifact_restoration.py` |

**Strategy-family discovery:** exhausted at H181 (Cycle 96), H182 unassigned. No free-data
repo-new candidate clears the directive bar (data-blocked: carry roll/contango, PIT
insider/earnings/options/GEX, breakeven inflation; low-power annual/index events; adjacency to
executed families). See `NEW_FAMILY_RESEARCH_REGISTER.md`.

## What was changed this session
- `tests/test_trade_log_cost_reconciliation.py`: added 11 tracked-but-unpinned trade logs to
  `TRADE_LOG_RECORD` + classification sets; updated stale counts (82→114 logs, eleven→twenty families).
  This strengthens the frozen-record contract; no `src/qtr` or frozen artifact change.
- `HANDOFF_CURRENT_SESSION.md`: rewritten to reflect verified green state and the fix.

## Unresolved / blocked
- **Artifact restoration apply (needs explicit human authorization):** 321 hash-exact recoverable
  rows; baseline `missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`,
  `missing_meta_files=140`. Do not apply without authorization.
- **H182 discovery (needs data/authorization):** blocked on resolving a documented data gap under
  explicit authorization or concluding free-data discovery exhausted per directive §6.

## One precise next task
1. **If restoration is explicitly authorized:** `python scripts/plan_artifact_restoration.py --apply --dry-run`
   → `--apply` → re-run `PYTHONPATH=src python -m pytest tests/test_reproducibility_audit.py -q`
   and capture actual counts → lower baselines in `tests/test_reproducibility_audit.py` and
   `tests/test_artifact_restoration_plan.py` **only** to evidenced values → regenerate
   `REPRODUCIBILITY_RESTORATION_PLAN.md/csv` and update `REPRODUCIBILITY_AUDIT_REPORT.md` →
   rerun full gates (`pytest -q -W error`, ruff check/format, 100% `src/qtr` coverage).
2. **If no authorization:** make no speculative code/test/data changes. Independent useful work:
   audit other pinned inventories for the same "tracked-but-unpinned" drift class (none currently
   failing). Otherwise the next progress requires restoration authorization or an authorized
   PIT/free data source for a materially new mechanism (not a variant of H1–H181).

## Failed approaches / do not repeat
- Do not re-implement completed §6 fallback items; do not invent/execute H182 from exhausted/adjacent families or blocked data.
- Do not run `--apply`, rewrite experiments/artifacts, delete committed data (including trade logs), or weaken baselines/gates/coverage without authorization and evidence.
- Do not trust prior handoff "unresolved"/"0 failed" claims without re-running the gates in this environment.
- Do not claim tests/lint/coverage passed without running them (this session installed tools and ran all gates).

## Constraints
- `src/qtr` unchanged unless evidenced defect (then rerun pinned full gates). No frozen/certified/published artifact, verdict, threshold, or gate weakening. No commit/push unless requested. Free/public data only.