# NEXT_TASK.md — Cycle 80 (after H165 REJECT 4/8)

## Status: Cycle 79 complete (H165 executed REAL REJECT 4/8) — Cycle 80 discovery required

**Lineage:** H85–H165 all rejected/recorded. Next unused H-ID: **H166** (H24/H68–H73/H76–H79 unassigned, not recycled).

**H165 result (recorded):** NF-20261109-08 realized SPY--VIX correlation regime SPY timing (rolling realized SPY--VIX correlation z-score; de-risk vol-targeted long SPY when correlation strongly negative/stress) — **REJECT 4/8** (OOS Val+Test Sharpe 0.652/PF 1.124/WF 0.865/worst-regime -0.994/benchmark-p 0.974/IR -0.787 fail; trades 3968/maxDD -3.00%/perturbation 0.930 pass). Train WF mean 0.754; selected `corr_window=63,z_window=252,entry_scale=2.0,vol_target=0.15`. **Pre-registered direction falsified** by inverse ablation (de-risk on POSITIVE/benign correlation): inverse 0.950/1.200/-3.08%/3743 materially outperforms base 0.652/1.124 — mapping not supported as specified. Random-exposure 0.615 weaker (no edge). Artifact `.experiments/nf_runs/nf_20261109_08_spy_vix_corr_regime/summary.json`. `src/qtr` unchanged.

**Integrity notes (must respect):**
- Tracked drafts `run_nf_20261109_06_idio_skew_regime` (failing tests/no artifact) and `run_nf_20261109_07_dealer_crowding_spy` (stub) were **removed** in Cycle 79; do not reuse NF-09-06/-07 for H166/H167. NF-20261109-08 verified unused and executed as H165.
- `.experiments/nf_runs/nf_20261108_18_gld_rv_stress_spy/` is **H151 (NF-20261108-18, TLT RV stress) REJECT 5/8** — do not overwrite.
- Do not recycle NF-20261108-26/H164, NF-20261109-05/H163, or NF roots with executed artifacts.

## One precise next task (Cycle 80 / H166)
Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`:
1. **Reconcile lineage/collisions first (evidence-based):** confirm H85–H165 rejected/recorded, H166 next unused. Confirm no tracked draft collides with H166 (NF-09-06/-07 removed Cycle 79).
2. Propose **>=3 repo-new/decisive candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops). Reassess: **NF-09-03** breakeven-inflation (data-limited: ^T5YIE/^T10YIE unavailable on yfinance; TIP/IEF proxy conflated), **NF-06-33** EWH/SPY (3.35, confounded), **NF-08-16** Halloween seasonal (3.90 held, calendar adjacency H91/H140/H142 — prior cycles declined 6x), **NF-08-20** IEF RV stress (adj H151), **NF-08-21/22/23** (UNG-USO/EFA-EEM/USO lead-lag). Justify independence from rejected classes including correlation H127/H96/H134/H137/H165, RV-stress H151/H156/H164 (direction-falsified), credit H94/H108/H146/H163, dispersion H118/H160/H162, FX H95/H103/H106/H161, VIX-complex H158/H159. The carried-forward pool is low-expected-information: search materially different mechanism categories before selecting.
3. Verify NF roots against executed H-IDs/artifacts/runners before selection (no collisions; H99/H149/H164-draft precedents).
4. Pre-register highest-expected-information **feasible** candidate as **H166** before validation outcomes (decision-ready: mechanism, PIT observable, causal path, null/falsifiers, bounded grid, costs, splits, gates).
5. Implement runner `run_nf_...py` + focused tests `tests/test_nf_...py`; run `python -m ruff check/format --check` on new files and `PYTHONPATH=src python -m pytest -q` focused tests (all pass).
6. Execute REAL; record verdict/artifacts in `HYPOTHESIS_SPEC.md` §H166, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 80, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. **Do not fabricate results.** No gate weakening; no published/certified artifact modification.

## Constraints
- Free/public data only; no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modification; no commit/push unless explicitly authorized.
- `src/qtr` unchanged unless evidenced defect. If `src/qtr` touched, rerun pinned 100% suite: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.
- Selection/validation uses no protected-test feedback. All gates fail-closed on pre-registered OOS Val+Test.

## Deferred (no silent drops; full list in NEW_FAMILY_RESEARCH_REGISTER.md)
NF-04 blocked (PIT term-structure/roll); NF-05/07/08/10/11/13/15/17/20/21 deferred; NF-11r/NF-06-18 same root as NF-11 (H141); NF-06-11 infeasible (CBOE PC); NF-06-01→H149; NF-06-03/23/24/27/28/30/32/33/35; NF-07-05 data blocker (CPI); NF-07-14/48 held (IV-spread H125/H126); NF-07-49 held (correlation); NF-07-52→H148; NF-08-04/05/07/08/10; NF-08-13 ES-SPY basis stub; NF-08-16 Halloween held (3.90); NF-08-20 IEF RV stress deferred; NF-08-21/22/23 deferred; NF-09-03 breakeven deferred/data-limited; NF-09-04→H163; NF-09-05→H163.
