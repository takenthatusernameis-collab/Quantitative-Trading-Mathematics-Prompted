# HANDOFF — Current Session (Cycle 95 complete, H181 REJECT 4/8)

## What changed
- **Lineage:** H85–H181 all rejected/recorded. Next unused H-ID **H182** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged.
- **Directive §4 discovery completed (pre-execution).** Scored ≥3 repo-new/decisive candidates across ≥3 broad mechanism categories with honest 25/25/20/15/10/5: NF-20261104-03 ES-SPY cash-futures basis mean-reversion timing (relative value / cash-futures basis convergence/index arbitrage, **4.05, selected** — smallest decisive feasible daily test), NF-20261110-07 Russell 2000 annual reconstitution flow (structural flow/discrete index event, 4.05, deferred: annual low power/event alignment; poor expected information), NF-20261110-08 insider Form 4/13F flow (institutional flow/informed trading, 3.80, deferred: PIT parsing/aggregation complexity). Deferred pool reassessed with concrete evidence (no silent drops).
- **NF-label/root check:** NF-20261104-03 previously proposed but never executed/pre-registered as H — repo-new execution as H181. Tracked draft `run_nf_20261110_07_es_basis.py` (NF-20261110-09/TBD, incomplete/unexecuted, no `main`) not selected/executed. Distinct from directional futures TSMOM families (H1/H7–H12/H21–H23/H25).
- **H181 implemented/executed REAL (NF-20261104-03).** `run_nf_20261104_03_es_spy_basis.py` + `tests/test_nf_20261104_03_es_spy_basis.py` (**8 passed**, 1 third-party DeprecationWarning). `py_compile` ok; `ruff check/format --check` clean. Artifact `.experiments/nf_runs/nf_20261104_03_es_spy_basis_20261110_cycle95/summary.json` (+`grid.csv`, ~10.3s).
- **Data/splits (real, PIT, free).** yfinance daily auto-adjusted closes ES=F + SPY, aligned 2010-01-04→2026-10-30 (4231 rows). Train→2018-12-31, Val→2022-12-31, Test protected→2026-10-30 (OOS Val+Test 1969). Train-only 4-fold WF selection; gates on OOS only.
- **Construction/grid.** Trailing z-score of ES/SPY basis (`ES/SPY - 1`) gates vol-targeted long SPY convergence exposure (hysteresis), 1-bar delay, Equity CostModel defaults (1bp+1bp), `MAX_POS=0.5`, long-only minimal decisive test. Grid 36: `basis_window {21,63,126} × entry_z {1.0,1.5,2.0} × exit_z {0.0,0.5} × vol_target {0.10,0.15}`. Selected (WF 0.234, train 0.246): `basis_window=21, entry_z=2.0, exit_z=0.0, vol_target=0.10`.
- **H181 result (OOS Val+Test) — REJECT 4/8.** Sharpe **0.297** fail, PF **1.162** fail, maxDD **−6.16%** pass, trades **99** pass, WF stability **1.208** pass, worst-regime rolling-252 **−1.410** fail, benchmark p **0.992** / IR **−0.877** vs buy-hold SPY 0.911/+90.75% fail, perturbation min ratio **0.552** pass. Return **+6.89%**. Ablations: random-signal 0.032/PF 1.014, inverse-signal −0.017/PF 0.995.
- **Docs updated:** `HYPOTHESIS_SPEC.md` §H181, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 95, `NEXT_TASK.md`, `HANDOFF_NEXT.md`, this handoff.

## Actually verified (this session)
- `python3 -m py_compile run_nf_20261104_03_es_spy_basis.py tests/test_nf_20261104_03_es_spy_basis.py` — OK.
- `python3 -m ruff check run_nf_20261104_03_es_spy_basis.py tests/test_nf_20261104_03_es_spy_basis.py` — clean.
- `python3 -m ruff format --check run_nf_20261104_03_es_spy_basis.py tests/test_nf_20261104_03_es_spy_basis.py` — clean (formatted once).
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261104_03_es_spy_basis.py` — **8 passed** (1 third-party DeprecationWarning).
- `PYTHONPATH=src timeout 600 python3 run_nf_20261104_03_es_spy_basis.py --out .experiments/nf_runs/nf_20261104_03_es_spy_basis_20261110_cycle95` — REAL execution completed (~10.3s), **REJECT 4/8**.
- Artifact present/parsable: `.experiments/nf_runs/nf_20261104_03_es_spy_basis_20261110_cycle95/summary.json` (+`grid.csv`).
- `src/qtr` unchanged; pinned 100% coverage suite **not rerun** (no `src/qtr` change).

## Unresolved / constraints
- H85–H181 all REJECTED/recorded. Gaps H24/H68–H73/H76–H79 unassigned (not recycled). **No commit/push** (not authorized). Published/certified artifacts and thresholds unchanged.
- Cycle 96: directive §4 discovery (≥3 candidates, ≥3 categories, honest scoring, no silent drops, NF-root checks) before selecting H182. Reassess deferred pool with evidence (NF-20261110-07, NF-20261110-08, NF-18/19/02/22/23/12/20/04/05/08-16/09-03/10-04/10-05). Draft `run_nf_20261110_07_es_basis.py` is NF-20261110-09/TBD incomplete/unexecuted.
- If `src/qtr` touched: rerun pinned 100% suite with `-W error --cov=qtr --cov-branch`.

## Approaches that failed / evidence (do not blindly repeat)
- **H181:** ES-SPY cash-futures basis mean-reversion timing (NF-20261104-03) REJECT 4/8 (Sharpe 0.297, PF 1.162, worst-regime −1.410, perturb 0.552, bench p 0.992/IR −0.877 vs buy-hold 0.911/+90.75%). Daily-close basis edge too small/noisy; inverse/random ablations unprofitable/near-zero. Do not rerun same basis-z construction on same daily ES/SPY closes without materially different mechanism/observable.
- **H180:** Ex-dividend capture (NF-20261109-16) REJECT 2/8 (Sharpe 0.194, PF 1.149, WF −0.313, worst-regime −1.980, perturb −3.115, bench fail).
- **H179:** FINRA short-interest z-score timing REJECT 2/8 (Sharpe −0.449, PF 0.920, WF −2.647, worst-regime −1.970; inverse/random outperformed).
- **H178:** CBOE equity P/C z-score REJECT 4/8; random-signal outperformed. **H177:** Treasury auction supply-pressure REJECT 5/8. **H176:** Tax-loss harvesting REJECT 3/8. **H175:** Macro regime timing REJECT 7/8.
- **H174:** ETF premium/discount invalid without point-in-time NAV. **H173:** Fed model / ERP timing REJECT 7/8.

## One precise next task (Cycle 96 / H182)
Reconcile lineage to H181; complete directive §4 discovery (≥3 repo-new/decisive candidates across ≥3 broad mechanism categories, honest 25/25/20/15/10/5, concrete deferred reassessment, NF-root checks). Reassess NF-20261110-07 (annual reconstitution, low power), NF-20261110-08 (insider 13F/Form 4, PIT complexity), NF-18/19/02/22/23/12/20/04/05/08-16/09-03/10-04/10-05 with evidence. Pre-register highest-expected-information feasible candidate as **H182** before validation outcomes. Implement runner + focused tests; `ruff check/format --check`; `PYTHONPATH=src pytest -q` focused tests; execute REAL; record in `HYPOTHESIS_SPEC.md` §H182, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push unless authorized. `src/qtr` unchanged unless evidenced defect (then rerun pinned 100% suite).
