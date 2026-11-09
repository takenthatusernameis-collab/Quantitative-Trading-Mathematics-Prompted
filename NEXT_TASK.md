# NEXT_TASK.md — Cycle 79 (after H164 REJECT 3/8)

## Status: Cycle 78 complete (H164 executed REAL REJECT 3/8) — Cycle 79 discovery required

**Lineage:** H85–H164 all rejected/recorded. Next unused H-ID: **H165** (H24/H68–H73/H76–H79 unassigned, not recycled).

**H164 result (recorded):** NF-20261108-26 GLD realized-volatility stress regime SPY timing (trailing GLD RV z-scored, continuous de-risk on abnormally positive/high GLD RV, vol-targeted SPY) — **REJECT 3/8** (OOS Val+Test Sharpe 0.569/PF 1.114/WF 0.624/worst-regime -1.123/benchmark-p 0.977/IR -0.788 fail; trades 3784/maxDD -3.04%/perturbation 0.948 pass). **Pre-registered direction falsified** by inverse ablation (de-risk on LOW GLD RV): inverse 1.108/1.230/-2.10%/3927 materially outperforms base 0.569/1.114 — mapping not supported as specified. Random-exposure 0.472 weaker (no benchmark edge). Artifact `.experiments/nf_runs/nf_20261108_26_gld_rv_stress_spy/summary.json`. `src/qtr` unchanged.

**Integrity notes (must respect):**
- `.experiments/nf_runs/nf_20261108_18_gld_rv_stress_spy/` is **H151 (NF-20261108-18, TLT RV stress) REJECT 5/8** — do not overwrite. H164 GLD RV artifacts are in `nf_20261108_26_gld_rv_stress_spy/`.
- **Tracked draft collision to reconcile before execution:** `run_nf_20261109_06_idio_skew_regime.py` / `tests/test_nf_20261109_06_idio_skew_regime.py` (commit 60e71c6) claim NF-20261109-06/H164 but focused tests were **3 failed, 7 passed** in Cycle 78 and there is **no REAL execution/artifact** — not an executed result; do not reuse NF-09-06/H164 for it. `run_nf_20261109_07_dealer_crowding_spy.py` (commit 4b0c93b) is a stub with no NF root/mechanism/tests/artifact. Verify NF roots/IDs against executed lineage, rename/remove or fix with evidence before any run. NF-20261109-08 appears unused as an NF root (verify).

## One precise next task (Cycle 79 / H165)
Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`:
1. **Reconcile lineage/collisions first (evidence-based):** confirm H85–H164 rejected/recorded, H165 next unused. Reconcile tracked `nf_20261109_06_idio_skew_regime` (H164 claim, failing tests/no artifact) and `nf_20261109_07_dealer_crowding_spy` (stub) — assign unused NF/H IDs only if made decision-ready, or document/rename/remove collision with evidence. Do not recycle NF-20261108-26/H164, NF-20261109-05/H163, or NF roots with executed artifacts.
2. Propose **>=3 repo-new/decisive candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops). Reassess: **NF-20261109-03** breakeven-inflation (data-limited: ^T5YIE/^T10YIE unavailable on yfinance probe 2026-11-09; TIP/IEF proxy conflated), **NF-20261106-33** EWH/SPY China-exposure (3.35), **NF-20261108-16** Halloween seasonal (3.35, calendar adjacency H91/H140/H142), **NF-20261108-20** IEF RV stress (adj H151), **NF-20261108-21/22/23** (UNG-USO/EFA-EEM/USO lead-lag). Justify independence from rejected classes including RV-stress H151/H156/**H164(direction-falsified)**, credit H94/H108/H146/H163, dispersion H118/H160/H162, FX H95/H103/H106/H161.
3. Verify NF roots against executed H-IDs/artifacts/runners before selection (no collisions; H99/H149/H164-draft precedents).
4. Pre-register highest-expected-information feasible candidate as **H165** before validation outcomes (decision-ready: mechanism, PIT observable, causal path, null/falsifiers, bounded grid, costs, splits, gates).
5. Implement runner `run_nf_...py` + focused tests `tests/test_nf_...py`; run `python -m ruff check/format --check` on new files and `PYTHONPATH=src python -m pytest -q` focused tests (all pass).
6. Execute REAL; record verdict/artifacts in `HYPOTHESIS_SPEC.md` §H165, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 79, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. **Do not fabricate results.** No gate weakening; no published/certified artifact modification.

## Constraints
- Free/public data only; no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modification; no commit/push unless explicitly authorized.
- `src/qtr` unchanged unless evidenced defect. If `src/qtr` touched, rerun pinned 100% suite: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.
- Selection/validation uses no protected-test feedback. All gates fail-closed on pre-registered OOS Val+Test.

## Deferred (no silent drops; full list in NEW_FAMILY_RESEARCH_REGISTER.md)
NF-04 blocked (PIT term-structure/roll); NF-05/07/08/10/11/13/15/17/20/21; NF-11r/NF-06-18 same root as NF-11; NF-06-11 infeasible (CBOE PC); NF-06-01→H149; NF-06-03/23/24/27/28/30/32/33/35; NF-07-05 data blocker (CPI); NF-07-14/48 held (IV-spread H125/H126); NF-07-49 held (correlation); NF-07-52→H148; NF-08-04/05/07/08/10/13/16/20/21/22/23; NF-08-24→H155; NF-08-26→H164 (REJECT 3/8, direction falsified by inverse); NF-08-27→H157; NF-08-29→H162; NF-09-03 deferred/downgraded (data-limited); NF-09-04 mechanism consumed as NF-09-05/H163. Tracked drafts nf_09_06 idio_skew/nf_09_07 dealer_crowding require NF/H reconciliation before execution.
