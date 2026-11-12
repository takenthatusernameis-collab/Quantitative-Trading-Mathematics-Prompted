# NEXT_TASK.md — §6 fallback audits complete; blocked on authorization/data (2026-11-12)

## Current status (reconciled this session)
STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §6 fallback audit items are implemented and artifacted in-repo; no further free-data fallback audit implementation is pending:

| Item | Evidence |
|---|---|
| Backtest engine performance profiling | `run_backtest_perf_profile.py`, `.experiments/backtest_perf_profile.csv`, `BACKTEST_PERF_PROFILE_RESULTS.md` |
| Experiment lineage report | `scripts/generate_experiment_lineage_report.py`, `EXPERIMENT_LINEAGE_REPORT.md` |
| Frozen-contract/gate edge stress (NaN/extreme leverage/zero-volume/look-ahead) | `tests/test_frozen_contract_gates_edge_stress.py`, `tests/test_gate_evaluation_edge_stress.py`, `tests/test_engine_edge_stress.py` |
| CI performance regression gate | `tests/test_performance_regression_gate.py`, `.github/workflows/gates.yml` (`pytest -q -W error --cov=qtr --cov-branch`) |
| Reproducibility audit + baseline ratchet | `tests/test_reproducibility_audit.py`, `REPRODUCIBILITY_AUDIT_REPORT.md`, `REPRODUCIBILITY_RESTORATION_PLAN.md/csv`, `scripts/plan_artifact_restoration.py`, `tests/test_artifact_restoration_plan.py` |

**Strategy-family discovery:** exhausted at H181 (Cycle 96), H182 unassigned. No free-data repo-new candidate currently clears directive bar (data-blocked: carry roll/contango, PIT insider/earnings/options/GEX, breakeven inflation; low-power annual/index events; adjacency to executed families). See `NEW_FAMILY_RESEARCH_REGISTER.md`.

## What was verified this session
- Inspected artifacts/tests/workflow/docs above and git state (HEAD `b902b04`, clean before edit).
- `python3 -m py_compile tests/test_frozen_contract_gates_edge_stress.py tests/test_gate_evaluation_edge_stress.py tests/test_performance_regression_gate.py scripts/generate_experiment_lineage_report.py run_backtest_perf_profile.py` — **pass**.
- `pytest`/`ruff` not installed in this environment; not re-run. Prior recorded evidence: `HANDOFF_NEXT.md` banner (3619 passed, 51 skipped, 0 failed; 100% `src/qtr` coverage; ruff clean) and `REPRODUCIBILITY_AUDIT_REPORT.md` baseline-ratchet state. Re-verify before relying on green status.

## Unresolved / blocked
- **Artifact restoration apply (needs explicit human authorization):** plan has 321 hash-exact recoverable rows; reproducibility baseline currently `missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=140` (`tests/test_reproducibility_audit.py`). Do not apply without authorization.
- **H182 discovery (needs data/authorization):** blocked on resolving a documented data gap under explicit authorization or concluding free-data discovery exhausted per directive §6.

## One precise next task
1. **If restoration is explicitly authorized:** `python scripts/plan_artifact_restoration.py --apply --dry-run` → `python scripts/plan_artifact_restoration.py --apply` → re-run `PYTHONPATH=src python -m pytest tests/test_reproducibility_audit.py -q` and capture actual counts → lower baselines in `tests/test_reproducibility_audit.py` and `tests/test_artifact_restoration_plan.py` **only** to evidenced new values → regenerate `REPRODUCIBILITY_RESTORATION_PLAN.md/csv` and update `REPRODUCIBILITY_AUDIT_REPORT.md` → run full gates `pytest -q -W error`, `python -m ruff check src tests run_*.py`, `python -m ruff format --check src tests run_*.py`, coverage 100% for `src/qtr`.
2. **If no authorization:** make no speculative code/test/data changes. The next progress requires either restoration authorization or authorized access to a blocker-resolving free/approved PIT data source for a materially new mechanism (not a variant of H1–H181). Record that dependency in handoff and stop.

## Failed approaches / do not repeat
- Do not re-implement completed §6 fallback items; do not invent/execute H182 from exhausted/adjacent families or blocked data.
- Do not run `--apply`, rewrite experiments/artifacts, delete committed data, or weaken baselines/gates/coverage without authorization and evidence.
- Do not claim tests/lint/coverage passed without running them.

## Constraints
- `src/qtr` unchanged unless evidenced defect (then rerun pinned full gates). No frozen/certified/published artifact, verdict, threshold, or gate weakening. No commit/push unless requested. Free/public data only.