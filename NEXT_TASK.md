# NEXT_TASK.md — Cycle 96 (after H181 REJECT 4/8)

## Status: Cycle 95 complete (H181 executed REAL; REJECT) — Cycle 96 discovery required

## H181 result (REAL, not fabricated) — REJECT 4/8
- Runner `run_nf_20261104_03_es_spy_basis.py` (NF-20261104-03, relative value / cash-futures basis convergence). Tests `tests/test_nf_20261104_03_es_spy_basis.py` (**8 passed**, 1 third-party DeprecationWarning). `py_compile` ok; `ruff check/format --check` clean. Artifact `.experiments/nf_runs/nf_20261104_03_es_spy_basis_20261110_cycle95/summary.json` (+`grid.csv`, ~10.3s).
- Data (real, free, PIT): yfinance daily auto-adjusted closes ES=F + SPY, aligned 2010-01-04→2026-10-30 (4231 rows). Train→2018-12-31, Val→2022-12-31, Test protected→2026-10-30 (OOS Val+Test 1969). Train-only 4-fold WF selection; gates on OOS Val+Test only.
- Grid (36): `basis_window {21,63,126} × entry_z {1.0,1.5,2.0} × exit_z {0.0,0.5} × vol_target {0.10,0.15}`. Equity CostModel defaults (1bp+1bp), `MAX_POS=0.5`, 1-bar delay, long-only SPY convergence exposure.
- Selected (WF 0.234, train 0.246): `basis_window=21, entry_z=2.0, exit_z=0.0, vol_target=0.10`.
- OOS Val+Test (1969 periods, 99 trades): Sharpe **0.297** fail, PF **1.162** fail, maxDD **−6.16%** pass, trades **99** pass, WF stability **1.208** pass, worst-regime rolling-252 **−1.410** fail, benchmark p **0.992** / IR **−0.877** vs buy-hold SPY 0.911/+90.75% fail, perturbation min ratio **0.552** pass. Return **+6.89%**. → **REJECT 4/8**.
- Ablations: random-signal Sharpe 0.032/PF 1.014; inverse-signal Sharpe −0.017/PF 0.995. Buy-hold dominates.
- **Integrity:** `src/qtr` unchanged; no gate weakening; no published/certified artifact/verdict/threshold/frozen-number modification; no commit/push.

## Lineage
- H85–H181 all rejected/recorded. Next unused H-ID **H182** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged. Selection/validation uses no protected-test feedback. Free/public data only.

## Required next work (Cycle 96 / H182)
1. Reconcile lineage to H181; complete directive §4 discovery (≥3 repo-new/decisive candidates across ≥3 broad mechanism categories, honest 25/25/20/15/10/5 scoring, no silent drops, NF-root checks).
2. Reassess deferred pool with concrete evidence (including NF-20261110-07, NF-20261110-08, NF-18/NF-19/NF-02/NF-22/NF-23/NF-12/NF-20/NF-04/NF-05/NF-08-16/NF-09-03/NF-20261110-04/NF-20261110-05) and verify no NF-label reuse against executed runners/artifacts. Note: tracked draft `run_nf_20261110_07_es_basis.py` is NF-20261110-09/TBD (incomplete/unexecuted) — do not treat as executed.
3. Pre-register highest-expected-information feasible candidate as **H182** before validation outcomes (decision-ready: mechanism, PIT observables/availability, causal chain, null/falsifiers, splits, grid, gates, costs, novelty justification).
4. Implement runner + focused tests; `ruff check/format --check`; `PYTHONPATH=src pytest -q` focused tests; execute REAL; record verdict/artifacts in `HYPOTHESIS_SPEC.md` §H182, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. **Do not fabricate results.**

## Constraints
- Free/public data only; no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modification; no commit/push unless explicitly authorized.
- `src/qtr` unchanged unless evidenced defect. If `src/qtr` touched, rerun pinned 100% suite: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.
- Selection/validation uses no protected-test feedback. All gates fail-closed on pre-registered OOS Val+Test.

## Approaches that failed / evidence (do not blindly repeat)
- **H181 (NF-20261104-03) REJECT 4/8:** ES-SPY cash-futures basis mean-reversion timing — OOS Sharpe 0.297, PF 1.162, worst-regime −1.410, bench p 0.992/IR −0.877 (buy-hold 0.911/+90.75%). Daily-close basis signal too small/noisy; inverse ablation weak/negative, random near zero. Do not rerun same basis-z construction on same daily ES/SPY closes without materially different observable/mechanism and explicit novelty justification.
- **H180 (NF-20261109-16) REJECT 2/8:** Ex-dividend capture — OOS Sharpe 0.194, PF 1.149, WF −0.313, worst-regime −1.980, perturb −3.115, bench fail. No certifiable microstructure edge on free daily data.
- **H179 (NF-20261110-06) REJECT 2/8:** FINRA short-interest z-score timing — Sharpe −0.449, PF 0.920, WF −2.647, worst-regime −1.970; inverse/random ablations outperformed.
- **H178:** CBOE equity P/C z-score REJECT 4/8; random-signal ablation outperformed.
- **H177:** Treasury auction supply-pressure REJECT 5/8. **H176:** Tax-loss harvesting REJECT 3/8. **H175:** Macro regime timing REJECT 7/8.
- **H174:** ETF premium/discount invalid without point-in-time NAV. **H173:** Fed model / ERP timing REJECT 7/8.
- All H85–H181 rejected on free, point-in-time data. Avoid silent recycling of exhausted construction classes without a *materially different* mechanism/observable and explicit novelty justification.
