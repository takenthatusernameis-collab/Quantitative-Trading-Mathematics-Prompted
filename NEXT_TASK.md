# NEXT_TASK.md — Cycle 82 (after H167 REJECT 4/8)

## Status: Cycle 81 complete (H166 + H167 executed REAL; both REJECT) — Cycle 82 discovery required

**Lineage:** H85–H167 all rejected/recorded. Next unused H-ID: **H168** (H24/H68–H73/H76–H79 unassigned, not recycled).

**This session (Cycle 80→81):**
- **H166 (NF-20261109-09, KRE/XLF intermediation-stress spread SPY timing) — REAL EXECUTION: REJECT 5/8.** Runner `run_nf_20261109_09_kre_xlf_stress_spy.py` + tests `tests/test_nf_20261109_09_kre_xlf_stress_spy.py` (7 passed). `ruff check/format` clean. Artifact `.experiments/nf_runs/nf_20261109_09_kre_xlf_stress_spy/summary.json`. OOS: Sharpe **1.105** (pass ≥1.0; first H-ID to clear Sharpe gate), trades **1127** pass, PF **1.229** fail, maxDD **-2.22%** pass, WF **0.975** pass, worst-regime **-0.963** fail, benchmark-p **0.961**/IR **-0.688** fail, perturbation **0.912** pass. Documented in `HYPOTHESIS_SPEC.md` §H166 and `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 80.
- **H167 (NF-20261109-10, equity volatility risk premium SPY timing) — REAL EXECUTION: REJECT 4/8.** Runner `run_nf_20261109_10_equity_vrp_timing.py` + tests `tests/test_nf_20261109_10_equity_vrp_timing.py` (7 passed). `ruff check/format` clean. Artifact `.experiments/nf_runs/nf_20261109_10_equity_vrp_timing/summary.json`. OOS: Sharpe **0.916** fail, trades **946** pass, PF **1.176** fail, maxDD **-3.20%** pass, WF **0.968** pass, worst-regime **-1.758** fail, benchmark-p **0.974**/IR **-0.718** fail, perturbation **0.986** pass. Documented in `HYPOTHESIS_SPEC.md` §H167 and `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 81.
- `src/qtr` unchanged; pinned 100% coverage suite not rerun (no `src/qtr` change). No commit/push.

## One precise next task (Cycle 82 / H168)
Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`:
1. **Reconcile lineage/collisions first (evidence-based):** confirm H85–H167 rejected/recorded, H168 next unused. Confirm no tracked draft collides with H168 (NF-09-06/-07 removed Cycle 79; do not reuse).
2. Propose **>=3 repo-new/decisive candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops). Reassess carried-forward pool with evidence: **NF-04** commodity carry (BLOCKED — no free PIT term-structure/roll proxy), **NF-05** short-term CS reversal (DEFERRED — turnover/net-of-cost; H119 weekly REJECT 3/8), **NF-08-16** Halloween seasonal (held 3.90, calendar adjacency H91/H140/H142), **NF-09-03** breakeven-inflation (data-limited — ^T5YIE/^T10YIE unavailable on yfinance). The carried-forward pool is low-expected-information: **search materially different mechanism categories before selecting.**
3. Verify NF roots against executed H-IDs/artifacts/runners before selection (no collisions; H99/H149/H164-draft precedents).
4. Pre-register highest-expected-information **feasible** candidate as **H168** before validation outcomes (decision-ready: mechanism, PIT observable, causal path, null/falsifiers, bounded grid, costs, splits, gates).
5. Implement runner `run_nf_...py` + focused tests `tests/test_nf_...py`; run `python -m ruff check/format --check` on new files and `PYTHONPATH=src python -m pytest -q` focused tests (all pass).
6. Execute REAL; record verdict/artifacts in `HYPOTHESIS_SPEC.md` §H168, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 82, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. **Do not fabricate results.** No gate weakening; no published/certified artifact modification.

## Constraints
- Free/public data only; no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modification; no commit/push unless explicitly authorized.
- `src/qtr` unchanged unless evidenced defect. If `src/qtr` touched, rerun pinned 100% suite: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.
- Selection/validation uses no protected-test feedback. All gates fail-closed on pre-registered OOS Val+Test.

## Deferred (no silent drops; full list in NEW_FAMILY_RESEARCH_REGISTER.md)
NF-04 blocked (PIT term-structure/roll); NF-05/07/08/10/11/13/15/17/20/21 deferred; NF-11r/NF-06-18 same root as NF-11 (H141); NF-06-11 infeasible (CBOE PC); NF-06-01→H149; NF-06-03/23/24/27/28/30/32/33/35; NF-07-05 data blocker (CPI); NF-07-14/48 held (IV-spread H125/H126); NF-07-49 held (correlation); NF-07-52→H148; NF-08-04/05/07/08/10; NF-08-13 ES-SPY basis stub; NF-08-16 Halloween held (3.90); NF-08-20 IEF RV stress deferred; NF-08-21/22/23 deferred; NF-09-03 breakeven deferred/data-limited.

## Approaches that failed / evidence (do not blindly repeat)
- H166 passed Sharpe (1.105) but failed PF/worst-regime/benchmark; inverse weaker, direction consistent but no edge. Do not rerun same KRE/XLF basket construction.
- H167 failed Sharpe/worst-regime/benchmark/PF; inverse weaker, direction consistent but no edge. Do not rerun same VRP-spread construction.
- All H85–H167 rejected on free, point-in-time data. Rejection classes to avoid silently recycling: correlation-regime H96/H127/H134/H137/H165; RV-stress H151/H156/H164; credit H94/H108/H146/H163; dispersion H118/H160/H162; FX H95/H103/H106/H161; VIX-complex H158/H159; VRP H17/H100/H167; carry H161.
