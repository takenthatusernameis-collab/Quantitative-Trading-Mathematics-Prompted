# HANDOFF_NEXT

## 1) What changed (Cycle 76 execution complete, H162 REJECT 4/8)

- **Lineage reconciled to H162.** H85–H162 all rejected/recorded. Cycle 76 discovery (directive §4) completed (≥3 candidates across ≥3 categories, honest 25/25/20/15/10/5, no silent drops, NF-root integrity checks) and selected NF-20261108-29 (cross-asset return-dispersion SPY timing) as **H162**.
- **H162 executed (NF-20261108-29, REAL, REJECT 4/8).** `run_nf_20261108_29_cross_asset_return_dispersion.py` + `tests/test_nf_20261108_29_cross_asset_return_dispersion.py` (**11 passed**). `ruff check/format --check` clean on H162 files. Artifact `.experiments/nf_runs/nf_20261108_29_cross_asset_return_dispersion/summary.json` (+`grid.csv`, `data_meta.json`).
- **H162 construction (pre-registered).** Cross-asset return dispersion = cross-sectional std of daily returns across SPY/TLT/GLD/UUP (equities/Treasuries/gold/USD), z-scored over `z_window`; hysteresis de-risks vol-targeted long SPY when `z >= entry_scale` (cross-asset stress), full exposure when `z <= exit_scale` (benign), initial state 1; 1-bar delay via engine `signals.shift(1)`; vol-targeted SPY trailing 21-day realized vol, clipped [0, MAX_POS=0.5]; long-only, Equity CostModel defaults. Bounded grid 24 combos (`z_window {126,252} × entry_scale {1.0,1.5,2.0} × exit_scale {0.0,0.5} × vol_target {0.10,0.15}`); train-only 4-fold WF selection by mean train Sharpe; Test protected.
- **H162 data (REAL).** SPY+TLT+GLD+UUP yfinance daily auto-adjust Close 2010-01-01→2026-10-30 (4233 rows; train 2515, val 756, test 962; OOS Val+Test n=1716).
- **H162 result (OOS Val+Test, 4012 trades).** Selected `z_window=126, entry_scale=1.5, exit_scale=0.5, vol_target=0.15` (WF train mean Sharpe 0.970). Sharpe **0.819** fail, PF **1.158** fail, maxDD **-3.69%** pass, trades **4012** pass, WF **0.913** pass, worst-regime **-1.550** fail, benchmark-p **0.970**/IR **-0.755** fail, perturbation **0.893** pass → **REJECT 4/8**. Ablations: buy-hold 0.792; random-exposure 0.492 (weaker); inverse ~0.000 (weaker, direction consistent but no edge). No gate weakened. `src/qtr` unchanged.
- **Docs updated:** `HYPOTHESIS_SPEC.md` §H162 (PRE--REGISTERED → REJECT 4/8, full REAL result), `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 76 execution/lineage, `NEXT_TASK.md` Cycle 77.

## 2) Actually verified (this session)
- `python -m py_compile` runner + tests — OK.
- `python -m ruff check` / `ruff format --check` on H162 files — clean.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261108_29_cross_asset_return_dispersion.py` — **11 passed**.
- `PYTHONPATH=src python run_nf_20261108_29_cross_asset_return_dispersion.py` — REAL execution completed (34.5s); verdict REJECT 4/8.
- Artifact present/parsable: `.experiments/nf_runs/nf_20261108_29_cross_asset_return_dispersion/summary.json` (+`grid.csv`, `data_meta.json`).
- `src/qtr` unchanged; pinned 100% coverage suite **not rerun** (no `src/qtr` change).

## 3) Remains unresolved / constraints
- H85–H162 all REJECTED/recorded. Lineage gaps H24/H68–H73/H76–H79 unassigned (not recycled). **No commit/push** (not authorized).
- The dispersion de-risking construction class now has three executed rejects (H118 within-equity sector dispersion REJECT 4/8, H160 cross-sectional IVOL dispersion REJECT 4/8, H162 cross-asset return dispersion REJECT 4/8). Further dispersion variants must justify clear separation.
- Cycle 77 must complete directive §4 discovery (≥3 repo-new/decisive candidates across ≥3 broad mechanism categories, honest scoring, no silent drops, NF-root checks) before selecting/pre-registering **H163**. Carried-forward NF-20261109-03 (breakeven inflation, 3.95) and NF-20261109-04 (HYG momentum, 3.95) re-assessed alongside ≥2 other repo-new mechanisms.
- Deferred/held (no silent drops; full list in `NEW_FAMILY_RESEARCH_REGISTER.md`): NF-04 blocked; NF-05/07/08/10/11/13/15/17/20/21; NF-11r/NF-06-18 same root as NF-11; NF-06-11 infeasible; NF-06-01→H149; NF-06-03/23/24/27/28/30/32/33/35; NF-07-05 data blocker; NF-07-11/12/14/31/32 held; NF-08-04/05/07/08/10 deferred/held; NF-08-13 stub/deferred; NF-08-16 Halloween held (3.90); NF-08-20/21/22/23/26 deferred; NF-20261108-27 EWJ relmom executed H157 REJECT; NF-09-03/04 carried forward.
- Published/certified artifacts and thresholds unchanged.

## 4) Approaches that failed (do not blindly repeat)
- **H162** (cross-asset return dispersion, Cycle 76) failed Sharpe/PF/worst-regime/benchmark; random-exposure much weaker and inverse weaker (direction consistent) but no OOS edge. Do not rerun same dispersion construction. Dispersion class (H118/H160/H162) all REJECT — further variants need honest separation.
- **H161** (G10 carry basket, Cycle 75) failed Sharpe/PF/worst-regime/benchmark; inverse weaker (direction consistent) but no edge. Further FX variants must justify separation from H95/H103/H106/H129/H134/H161.
- Do not reuse NF roots without integrity check (H99/H149 collision precedent).

## 5) One precise next task (Cycle 77 / H163)
Reconcile lineage to H162; complete directive §4 discovery (≥3 repo-new/decisive candidates across ≥3 broad mechanism categories, honest 25/25/20/15/10/5, concrete deferred reassessment, NF-root checks). Re-assess NF-20261109-03/NF-20261109-04 alongside ≥2 other repo-new mechanisms. Pre-register highest-expected-information feasible candidate as **H163** before validation outcomes. Implement runner + focused tests; `ruff check/format --check` on new files; `PYTHONPATH=src pytest -q` focused tests; execute REAL; record verdict/artifacts in `HYPOTHESIS_SPEC.md` §H163, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 77, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. Justify independence from rejected classes including the dispersion class (H118/H160/H162) and H161/FX families. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push unless authorized. If `src/qtr` touched, rerun pinned 100% coverage suite.
