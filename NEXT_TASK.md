# NEXT_TASK.md — Cycle 78 (after H163 REJECT 3/8)

## Status: Cycle 77 complete (H163 executed REAL REJECT 3/8) — Cycle 78 discovery required

**Lineage:** H85–H163 all rejected/recorded. Next unused H-ID: **H164** (H24/H68–H73/H76–H79 unassigned, not recycled).

**H163 result (recorded):** NF-20261109-05 HYG high-yield credit-momentum regime SPY timing (trailing HYG return-momentum z-scored, hysteresis de-risk-on-weak-momentum, vol-targeted SPY) — **REJECT 3/8** (OOS Sharpe 0.935/PF 1.224/worst-regime -1.336/benchmark-p 0.903/IR -0.545 fail; trades/maxDD/WF/perturbation pass). Ablations: buy-hold 0.792; random-exposure 0.209 (much weaker, structure present); inverse 0.148 (much weaker, direction supported) — no benchmark edge. Artifact `.experiments/nf_runs/nf_20261109_05_hyg_momentum_spy/summary.json`. `src/qtr` unchanged.

**Credit-family note (honest):** H94 (HYG-IEF excess level, REJECT 4/8), H108 (LQD-HYG ratio level, REJECT 4/8), H146 (JNK/LQD ratio level, REJECT 4/8), H163 (HYG momentum z-score, REJECT 3/8). Further HY/IG credit observables must justify clear separation from these executed rejects.

## One precise next task (Cycle 78 / H164)
Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4` and prior handoffs:
1. Reconcile lineage to H163 (H85–H163 rejected/recorded). Do not recycle H24/H68–H73/H76–H79.
2. Propose **>=3 repo-new/decisive candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops). Reassess carried-forward candidates: **NF-20261109-03** breakeven-inflation (downgraded/data-limited: ^T5YIE/^T10YIE unavailable on yfinance probe 2026-11-09; TIP/IEF ETF proxy weak/confounded), **NF-20261106-33** EWH/SPY China-exposure (3.35, confounds), **NF-20261108-16** Halloween seasonal (3.35, calendar adjacency), **NF-20261108-26** GLD RV stress (3.50, adj H151/H149).
3. Verify NF roots against executed H-IDs/artifacts/runners before selection (no root collisions; H99/H149 precedent). NF-20261109-05/H163 executed; NF-09-04 mechanism consumed as NF-09-05 (document honestly).
4. Pre-register highest-expected-information feasible candidate as **H164** before validation outcomes (decision-ready: mechanism, PIT observable, causal path, null/falsifiers, bounded grid, costs, splits, gates).
5. Implement runner `run_nf_...py` + focused tests `tests/test_nf_...py`; run `python -m ruff check/format --check` on new files and `PYTHONPATH=src python -m pytest -q` focused tests (all pass).
6. Execute REAL; record verdict/artifacts in `HYPOTHESIS_SPEC.md` §H164, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 78, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. Justify independence from rejected classes including credit families H94/H108/H146/H163 and dispersion H118/H160/H162.

## Constraints
- Free/public data only; no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modification; no commit/push unless explicitly authorized.
- `src/qtr` unchanged unless evidenced defect. If `src/qtr` touched, rerun pinned 100% suite: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.
- Selection/validation uses no protected-test feedback. All gates fail-closed on pre-registered OOS Val+Test.

## Deferred (no silent drops; full list in NEW_FAMILY_RESEARCH_REGISTER.md)
NF-04 blocked (PIT term-structure/roll); NF-05/07/08/10/11/13/15/17/20/21; NF-11r/NF-06-18 same root as NF-11; NF-06-11 infeasible (CBOE PC); NF-06-01→H149; NF-06-03/23/24/27/28/30/32/33/35; NF-07-05 data blocker (CPI); NF-07-14/48 held (IV-spread H125/H126); NF-07-49 held (correlation); NF-07-52→H148; NF-08-04/05/07/08/10/13/16/20/21/22/23/26; NF-08-24→H155; NF-08-27→H157; NF-08-29→H162; NF-09-03 deferred/downgraded (data-limited); NF-09-04 mechanism consumed as NF-09-05/H163.
