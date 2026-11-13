# NEXT_TASK.md — Suite re-verified green (Cycle 102); stale-doc repair only; blocked on authorization/data (2026-11-12)

## Current status (re-verified from scratch this session — do not trust prior claims)
- Full pinned gates are GREEN, re-run in this environment from a clean checkout:
  - `PYTHONPATH=src python3 -m pytest -q` → **3730 passed, 51 skipped, 0 failed** (623s)
  - `PYTHONPATH=src python3 -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` →
    **100.00%** `src/qtr` (1211 stmts / 422 branches / 0 miss)
  - `python3 -m ruff check src tests run_*.py` → All checks passed
  - `python3 -m ruff format --check src tests run_*.py` → 321 files already formatted
- The prior handoff's "0 failed" claim was itself stale/wrong at the time it was written: the
  suite had **1 failed** on a clean checkout (`tests/test_trade_log_cost_reconciliation.py`),
  fixed in commit `7a2305d`. That fix is already on `main`; this session made **no** code/test/
  frozen-artifact change.

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

## What was changed this session (doc-only; no src/qtr, test, gate, or frozen-artifact change)
- `NEXT_TASK.md`: corrected the false "321 hash-exact recoverable rows" claim. Re-running the
  planner reports **Recoverable 0 / Excluded 172 / Unrecoverable 25**, which is exactly what the
  committed `REPRODUCIBILITY_RESTORATION_PLAN.md/csv` and `tests/test_artifact_restoration_plan.py`
  already pin. Rewrote the restoration next-task to state that `--apply` is a no-op.
- `AGENTS.md`: annotated the stale "H1–H30 exhausted / hypotheses through H84" lines with the
  re-verified current inventory (**H1–H181 exhausted/rejected, H182 unassigned**); merged the
  duplicate strategy-family section into `## Notes`.
- `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md`: added a re-verification callout under §1 noting the
  same stale H-range and pointing at the current register.
- No `src/qtr`, test, runner, gate, threshold, verdict, or committed artifact was modified.

## Unresolved / blocked
- **Artifact restoration apply (needs explicit human authorization):** Re-running the planner
  (`python scripts/plan_artifact_restoration.py --dry-run`) on this checkout reports
  **Recoverable rows: 0 / Excluded (contract-blocked): 172 / Unrecoverable: 25** — the committed
  `REPRODUCIBILITY_RESTORATION_PLAN.md/csv` and `tests/test_artifact_restoration_plan.py`
  baselines already match this exactly, so `--apply` is a **no-op** and must not be run.
  Baseline in `tests/test_reproducibility_audit.py`: `missing_files=197`,
  `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=140` (verified passing this
  session). The prior "321 recoverable rows" claim was wrong and has been corrected here.
- **H182 discovery (needs data/authorization):** blocked on resolving a documented data gap under
  explicit authorization or concluding free-data discovery exhausted per directive §6.

## One precise next task
1. **Restoration is a no-op — do not run `--apply`.** The only authorized write path
   (`scripts/plan_artifact_restoration.py --apply`) would copy 0 rows; the 172 hash-exact rows
   are contract-blocked (H28 depth-one invariant) and the 25 unrecoverable rows have no
   hash-matching source. Any reduction in `missing_files`/`orphaned_files`/`missing_meta_files`
   requires editing `experiments.jsonl` paths under explicit authorization, then lowering the
   baselines in `tests/test_reproducibility_audit.py` and
   `tests/test_artifact_restoration_plan.py` **only** to evidenced values, regenerating
   `REPRODUCIBILITY_RESTORATION_PLAN.md/csv` and `REPRODUCIBILITY_AUDIT_REPORT.md`, and rerunning
   the full gates.
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