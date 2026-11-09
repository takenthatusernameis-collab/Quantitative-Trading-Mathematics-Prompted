# NEXT_TASK.md — Cycle 78 (after H163 REJECT 4/8)

## Status: Cycle 77 complete (H163 executed REAL REJECT 4/8) — Cycle 78 discovery required

**Lineage:** H85–H163 all rejected/recorded. Next unused H-ID: **H164** (H24/H68–H73/H76–H79 unassigned, not recycled).

**H163 result (recorded):** NF-20261109-05 IG credit spread (LQD/IEF) regime timing SPY — **REJECT 4/8** (OOS Sharpe 0.657/PF 1.149/worst-regime -1.176/benchmark-p 0.978/IR -0.785 fail; trades/maxDD/WF/perturbation pass). Ablations: buy-hold 0.792; random-exposure 0.363 (weaker); inverse 0.873 (direction consistent but base fails). Artifact `.experiments/nf_runs/nf_20261109_05_ig_credit_spread/summary.json`. `src/qtr` unchanged.

**Credit-channel families now have three executed rejects:** H94 HYG-IEF (REJECT 3/9), H108 LQD/HYG (REJECT 4/8), H146 JNK/LQD (unexecuted), H163 LQD/IEF (REJECT 4/8). Further credit variants must justify clear separation from the executed IG spread level family.

## One precise next task (Cycle 78 / H164)
Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4` and prior handoffs:
1. Reconcile lineage to H163 (H85–H163 rejected/recorded). Do not recycle H24/H68–H73/H76–H79.
2. Propose **>=3 repo-new/decisive candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops). Carried-forward NF-20261109-03 (breakeven inflation, 3.95) and NF-20261109-04 (HYG momentum, 3.95) must be re-assessed alongside >=2 other repo-new mechanisms.
3. Verify NF roots against executed H-IDs/artifacts/runners before selection (no root collisions; H99/H149 precedent).
4. Pre-register highest-expected-information feasible candidate as **H164** before validation outcomes (decision-ready: mechanism, PIT observable, causal path, null/falsifiers, bounded grid, costs, splits, gates).
5. Implement runner `run_nf_...py` + focused tests `tests/test_nf_...py`; run `python -m ruff check/format --check` on new files and `PYTHONPATH=src python -m pytest -q` focused tests (all pass).
6. Execute REAL; record verdict/artifacts in `HYPOTHESIS_SPEC.md` §H164, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 78, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. Justify independence from rejected classes including the credit-channel families (H94/H108/H163) and dispersion class (H118/H160/H162).

## Constraints
- Free/public data only; no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modification; no commit/push unless explicitly authorized.
- `src/qtr` unchanged unless evidenced defect. If `src/qtr` touched, rerun pinned 100% suite: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.
- Selection/validation uses no protected-test feedback. All gates fail-closed on pre-registered OOS Val+Test.

## Deferred (no silent drops; full list in NEW_FAMILY_RESEARCH_REGISTER.md)
NF-04 blocked (PIT term-structure/roll); NF-05/07/08/10/11/13/15/17/20/21; NF-11r/NF-06-18 same root as NF-11; NF-06-11 infeasible (CBOE PC); NF-06-01→H149; NF-06-03/23/24/27/28/30/32/33/35; NF-07-05 data blocker (CPI surprise); NF-07-11/12/14/31/32; NF-08-04/05/07/08/10/13/16/20/21/22/23/26/29; NF-09-03/04 carried forward for Cycle 78 recheck.
