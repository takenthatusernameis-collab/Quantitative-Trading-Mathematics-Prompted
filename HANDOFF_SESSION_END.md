# Session End Handoff — Cycle 314 Verification (2026-11-25)

## Summary
Verified the authoritative status documented in `NEXT_TASK.md`: **free-data equity/fund cross-section program formally CLOSED**. Baseline confirmed green. No new changes made; both blocked items await maintainer action.

## What Was Verified (Evidence)

### Test Baseline (all `-W error`)
| Test Suite | Result |
|------------|--------|
| `test_runner_import_contract.py` | 316 passed |
| `test_verify_hypothesis_inventory.py` | 28 passed |
| `test_probe_broad_universe_shares_availability.py` | 20 passed |
| `test_nf_20261122_04_size_premium.py` | 23 passed |
| `test_nf_20261125_01_institutional_flow.py` + `test_nf_20261125_02_short_interest.py` | 16 passed |
| `test_backtest_engine.py` + `test_data_fetcher.py` + `test_config.py` | 214 passed |
| `test_causality_invariant.py` + `test_gate_vacuity_contract.py` | 50 passed, 1 skipped |
| `test_experiment_tracker.py` + `test_experiment_artifact_schema.py` | 169 passed |
| H187–H191 (`test_nf_20261120_01/02`, `test_nf_20261121_01/02`) | 78 passed |
| H193–H195 (`test_nf_20261121_03/04/05`) | 60 passed |
| H196–H198 (`test_nf_20261122_01/02/03`) | 71 passed |

### Code Quality
- `ruff check src tests run_*.py scripts` → **All checks passed**
- `ruff format --check src tests run_*.py scripts` → **407 files already formatted**

### Gates Workflow Patch
- `python scripts/verify_gates_workflow_patch.py` → **PATCH VERIFIED**: `patches/0001-gates-workflow-contract-fix.patch` applies cleanly and resolves all 7 contract violations
- Live `gates.yml` fails 7 assertions (missing ruff steps, missing `pip install -e .`, missing `backtest_perf_regression_gate.py`, missing `scripts/**` in push/PR triggers)
- **Agent cannot land**: `.github/workflows/**` is controller-restored; GitHub token lacks `workflows` scope

### Program Status
- **H1–H201 exhausted/rejected**; H189 data-blocked (gross profitability share overlap < 40 names)
- H187–H201 median OOS Sharpe: **0.187**
- Free-data sources probed and exhausted: SEC 13F, FINRA Reg SHO, FRED, SEC N-CEN (no Item C dollar flow), SEC N-PORT (holdings only, not flows), CBOE options (403)
- Evidence registered in `.cache/remaining_family_sources.json` (gitignored)

## Unresolved (Maintainer Action Required)

1. **Workflow contract patch** — Apply `patches/0001-gates-workflow-contract-fix.patch`:
   ```bash
   git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am "fix(ci): satisfy gates workflow contract" && git push origin main
   ```

2. **Paid/consensus source authorization for H202** — Next H-ID is H202 (requires maintainer-authorized paid/consensus data source per `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 313). Agent cannot authorize or purchase data.

## Approaches Already Failed — Do NOT Repeat
- Re-running the 750 s baseline as deliverable
- Adding more guards or reconciling docs (make-work)
- Fabricating H202 or running another equity cross-section on exhausted universe (directive §2)
- Editing `.github/workflows/**` in a commit (controller-restored)
- Re-declaring 13F/FINRA/FRED/N-CEN "data-blocked" without named-source probe
- Chasing `src/qtr` audit candidates as "bugs" (verified documented conventions)

## Next Task (Choose ONE, Priority Order)

**Await maintainer action on the two blocked items above, then:**
- If paid/consensus source authorized: bump H-ID to **H202** in `AGENTS.md` and `HYPOTHESIS_SPEC.md` (bump together per AGENTS.md contract), open the new family per `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 313, and execute H202 on the paid source.
- If not authorized: confirm the free-data equity/fund cross-section program remains closed; no further free-data cross-sections (directive §2 forbids H187–H198 re-tests and universe/parameter variants).

**Do NOT**: re-run the 750 s baseline, add more guards, re-declare 13F/FINRA/FRED/N-CEN blocked, fabricate H202.

---

*Working tree clean. `src/qtr` unchanged. All verification evidence captured above.*