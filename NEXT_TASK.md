# NEXT_TASK.md — Cycle 76 (after H161 REJECT 4/8)

## Status: Cycle 75 complete (H161 executed REAL REJECT 4/8) — Cycle 76 discovery required

**Lineage:** H85–H161 all rejected/recorded. Next unused H-ID: **H162** (H24/H68–H73/H76–H79 unassigned, not recycled).

**H161 result (recorded):** NF-20261109-02 G10 currency carry basket momentum z-score (hysteresis, vol-targeted SPY, 1-bar delay) — **REJECT 4/8** (OOS Sharpe 0.892/PF 1.221/worst-regime -1.432/benchmark-p 0.976 IR -0.740 fail; trades/maxDD/WF/perturbation pass). Ablations: buy-hold 0.793; random-exposure 0.518 (weaker); inverse 0.503 (weaker, direction consistent but no edge). Artifact `.experiments/nf_runs/nf_20261109_02_g10_carry/summary.json`. `src/qtr` unchanged.

## One precise next task (Cycle 76 / H162)
Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4` and prior handoffs:
1. Reconcile lineage to H161 (H85–H161 rejected/recorded). Do not recycle H24/H68–H73/H76–H79.
2. Propose **>=3 repo-new/decisive candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops). Re-assess carried-forward candidates alongside >=2 other repo-new mechanisms: **NF-20261109-03** TIPS breakeven inflation level regime (3.95, adjacency NF-08/H154/H155), **NF-20261109-04** HYG momentum regime (3.95, adjacency H94/H108/H146), **NF-20261108-29** cross-asset return dispersion (4.10, must justify separation from H118 within-equity return dispersion REJECT 4/8).
3. Verify NF roots against executed H-IDs/artifacts/runners before selection (no root collisions; H99/H149 precedent).
4. Pre-register highest-expected-information feasible candidate as **H162** before validation outcomes (decision-ready: mechanism, PIT observable, causal path, null/falsifiers, bounded grid, costs, splits, gates).
5. Implement runner `run_nf_...py` + focused tests `tests/test_nf_...py`; run `python -m ruff check/format --check` on new files and `PYTHONPATH=src python -m pytest -q` focused tests (all pass).
6. Execute REAL; record verdict/artifacts in `HYPOTHESIS_SPEC.md` §H162, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 76, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. Justify independence from rejected classes including H161/FX families (H95/H103/H106/H129/H134).

## Constraints
- Free/public data only; no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modification; no commit/push unless explicitly authorized.
- `src/qtr` unchanged unless evidenced defect. If `src/qtr` touched, rerun pinned 100% suite: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.
- Selection/validation uses no protected-test feedback. All gates fail-closed on pre-registered OOS Val+Test.

## Deferred (no silent drops; full list in NEW_FAMILY_RESEARCH_REGISTER.md)
NF-04 blocked (PIT term-structure/roll); NF-05/07/08/10/11/13/15/17/20/21; NF-11r/NF-06-18 same root as NF-11; NF-06-11 infeasible (CBOE PC); NF-06-01→H149; NF-06-03/23/24/27/28/30/32/33/35; NF-07-05 data blocker (CPI surprise); NF-07-11/12/14/31/32; NF-08-04/05/07/08/10/13/16/20/21/22/23/26/29; NF-09-03/04 carried forward for Cycle 76 recheck.
