# HANDOFF_NEXT

## 1) What changed (Cycle 77 execution complete, H163 REJECT 4/8)

- **Lineage reconciled to H163.** H85–H163 all rejected/recorded. Cycle 77 discovery (directive §4) completed (≥3 candidates across ≥3 categories, honest 25/25/20/15/10/5, no silent drops, NF-root integrity checks) and selected NF-20261109-05 (IG credit spread LQD/IEF → SPY timing) as **H163**.
- **H163 executed (NF-20261109-05, REAL, REJECT 4/8).** `run_nf_20261109_05_ig_credit_spread.py` + `tests/test_nf_20261109_05_ig_credit_spread.py` (**9 passed**). `ruff check/format --check` clean on H163 files. Artifact `.experiments/nf_runs/nf_20261109_05_ig_credit_spread/summary.json` (+`grid.csv`, `data_meta.json`).
- **H163 construction (pre-registered).** IG credit spread = log(LQD/IEF), z-scored over `z_window`; hysteresis de-risks vol-targeted long SPY when `z >= entry_scale` (credit stress), re-enters when `z <= exit_scale` (benign), initial state 1; 1-bar delay via engine `signals.shift(1)`; vol-targeted SPY trailing 21-day realized vol, clipped [0, MAX_POS=0.5]; long-only, Equity CostModel defaults. Bounded grid 36 combos (`lookback {63,126,252} × z_window {126,252} × entry_scale {1.0,1.5,2.0} × exit_scale {0.0,0.5} × vol_target {0.10,0.15}`); train-only 4-fold WF selection by mean train Sharpe; Test protected.
- **H163 data (REAL).** SPY+LQD+IEF yfinance daily auto-adjust Close 2010-01-01→2026-10-30 (4233 rows; train 2515, val 756, test 962; OOS Val+Test n=1716).
- **H163 result (OOS Val+Test, 2650 trades).** Selected `lookback=63, z_window=126, entry_scale=1.5, exit_scale=0.5, vol_target=0.15` (WF train mean Sharpe 0.935). Sharpe **0.657** fail, PF **1.149** fail, maxDD **-3.23%** pass, trades **2650** pass, WF **0.858** pass, worst-regime **-1.176** fail, benchmark-p **0.978**/IR **-0.785** fail, perturbation **0.760** pass → **REJECT 4/8**. Ablations: buy-hold 0.792; random-exposure 0.363 (weaker); inverse 0.873 (direction consistent but base fails OOS gates). No gate weakened. `src/qtr` unchanged.
- **Docs updated:** `HYPOTHESIS_SPEC.md` §H163 (PRE-REGISTERED → REJECT 4/8, full REAL result), `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 77 execution/lineage, `NEXT_TASK.md` Cycle 78.

## 2) Actually verified (this session)
- `python -m py_compile` runner + tests — OK.
- `python -m ruff check` / `ruff format --check` on H163 files — clean.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261109_05_ig_credit_spread.py` — **9 passed**.
- `PYTHONPATH=src python run_nf_20261109_05_ig_credit_spread.py` — REAL execution completed (~55s); verdict REJECT 4/8.
- Artifact present/parsable: `.experiments/nf_runs/nf_20261109_05_ig_credit_spread/summary.json` (+`grid.csv`, `data_meta.json`).
- `src/qtr` unchanged; pinned 100% coverage suite **not rerun** (no `src/qtr` change).

## 3) Remains unresolved / constraints
- H85–H163 all REJECTED/recorded. Lineage gaps H24/H68–H73/H76–H79 unassigned (not recycled). **No commit/push** (not authorized).
- The credit-channel family now has three executed rejects (H94 HYG-IEF REJECT 3/9, H108 LQD/HYG REJECT 4/8, H163 LQD/IEF REJECT 4/8). Further credit variants must justify clear separation from the executed IG spread level family.
- The dispersion de-risking construction class has three executed rejects (H118 within-equity sector dispersion REJECT 4/8, H160 cross-sectional IVOL dispersion REJECT 4/8, H162 cross-asset return dispersion REJECT 4/8). Further dispersion variants must justify clear separation.
- Cycle 78 must complete directive §4 discovery (≥3 repo-new/decisive candidates across ≥3 broad mechanism categories, honest scoring, no silent drops, NF-root checks) before selecting/pre-registering **H164**. Carried-forward NF-20261109-03 (breakeven inflation, 3.95) and NF-20261109-04 (HYG momentum, 3.95) re-assessed alongside ≥2 other repo-new mechanisms.
- Deferred/held (no silent drops; full list in `NEW_FAMILY_RESEARCH_REGISTER.md`): NF-04 blocked; NF-05/07/08/10/11/13/15/17/20/21; NF-11r/NF-06-18 same root as NF-11; NF-06-11 infeasible; NF-06-01→H149; NF-06-03/23/24/27/28/30/32/33/35; NF-07-05 data blocker; NF-07-11/12/14/31/32 held; NF-08-04/05/07/08/10 deferred/held; NF-08-13 stub/deferred; NF-08-16 Halloween held (3.90); NF-08-20/21/22/23/26 deferred; NF-20261108-27 EWJ relmom executed H157 REJECT; NF-09-03/04 carried forward.
- Published/certified artifacts and thresholds unchanged.

## 4) Approaches that failed (do not blindly repeat)
- **H163** (IG credit spread LQD/IEF, Cycle 77) failed Sharpe/PF/worst-regime/benchmark; random-exposure weaker, inverse direction consistent but base fails OOS gates; no OOS edge. Do not rerun same IG credit spread construction. Credit-channel family (H94/H108/H163) all REJECT — further variants need honest separation.
- **H162** (cross-asset return dispersion, Cycle 76) failed Sharpe/PF/worst-regime/benchmark; random-exposure much weaker and inverse weaker (direction consistent) but no OOS edge. Do not rerun same dispersion construction. Dispersion class (H118/H160/H162) all REJECT — further variants need honest separation.
- **H161** (G10 carry basket, Cycle 75) failed Sharpe/PF/worst-regime/benchmark; inverse weaker (direction consistent) but no edge. Further FX variants must justify separation from H95/H103/H106/H129/H134/H161.
- Do not reuse NF roots without integrity check (H99/H149 collision precedent).

## 5) One precise next task (Cycle 78 / H164)
Reconcile lineage to H163; complete directive §4 discovery (≥3 repo-new/decisive candidates across ≥3 broad mechanism categories, honest 25/25/20/15/10/5, concrete deferred reassessment, NF-root checks). Re-assess NF-20261109-03/NF-20261109-04 alongside ≥2 other repo-new mechanisms. Pre-register highest-expected-information feasible candidate as **H164** before validation outcomes. Implement runner + focused tests; `ruff check/format --check` on new files; `PYTHONPATH=src pytest -q` focused tests; execute REAL; record verdict/artifacts in `HYPOTHESIS_SPEC.md` §H164, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 78, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. Justify independence from rejected classes including the credit-channel families (H94/H108/H163) and dispersion class (H118/H160/H162). Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push unless authorized. If `src/qtr` touched, rerun pinned 100% coverage suite.
