# HANDOFF — Current Session (Cycle 75 complete, H161 REJECT 4/8)

## What changed
- **Lineage reconciled to H161.** H85–H161 all rejected/recorded. Cycle 75 discovery (directive §4, ≥3 candidates/≥3 categories, honest scoring, no silent drops, NF-root checks) had pre-registered NF-20261109-02 as H161; this session implemented and executed H161 REAL.
- **H161 executed (NF-20261109-02, REAL, REJECT 4/8).** `run_nf_20261109_02_g10_carry.py` + `tests/test_nf_20261109_02_g10_carry.py` (10 passed). `ruff check/format --check` clean. Artifact `.experiments/nf_runs/nf_20261109_02_g10_carry/summary.json` (+grid/data_meta).
- **H161 construction.** G10 carry basket (long AUD/NZD/CAD vs JPY, short EUR/CHF/USD vs JPY; USDJPY=X fetched for coverage, excluded from basket; GBPJPY=X fetched, not in basket). Rolling momentum-sum z-score with hysteresis; vol-targeted long SPY; 1-bar delay; long-only; Equity CostModel defaults; MAX_POS 0.5. Grid 72 valid combos (exit≤entry); train-only 4-fold WF selection.
- **H161 data.** SPY+7 G10 pairs yfinance 2010-01-04→2026-10-30 (4226 rows; OOS Val+Test n=1715).
- **H161 result (OOS Val+Test).** Selected `lookback=252,z_window=252,entry_scale=2.0,exit_scale=0.5,vol_target=0.15` (WF train mean 1.117). Sharpe **0.892** fail, PF **1.221** fail, maxDD **-2.46%** pass, trades **2669** pass, WF **0.929** pass, worst-regime **-1.432** fail, benchmark-p **0.976**/IR **-0.740** fail, perturbation **0.618** pass → **REJECT 4/8**. Ablations: buy-hold 0.793; random-exposure 0.518 (weaker); inverse 0.503 (weaker, direction consistent, no edge). No gate weakened. `src/qtr` unchanged.
- **Docs updated:** `HYPOTHESIS_SPEC.md` §H161, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 75 execution, `NEXT_TASK.md` (Cycle 76), `HANDOFF_NEXT.md`.

## Actually verified (this session)
- `python -m py_compile` runner + tests — OK.
- `python -m ruff check` / `ruff format --check` on H161 files — clean.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261109_02_g10_carry.py` — **10 passed**.
- `PYTHONPATH=src python run_nf_20261109_02_g10_carry.py` — REAL execution completed (70.3s), REJECT 4/8.
- Artifact present/parsable: `.experiments/nf_runs/nf_20261109_02_g10_carry/summary.json` (+grid/data_meta).
- `src/qtr` unchanged; pinned 100% coverage suite **not rerun**.

## Unresolved / constraints
- H85–H161 all REJECTED/recorded. Gaps H24/H68–H73/H76–H79 unassigned (not recycled). **No commit/push** (not authorized). Published/certified artifacts and thresholds unchanged.
- Cycle 76: directive §4 discovery (>=3 candidates, >=3 categories, honest scoring, no silent drops, NF-root checks) before selecting H162. Re-assess NF-09-03 breakeven inflation (3.95), NF-09-04 HYG momentum (3.95), NF-08-29 cross-asset return dispersion (4.10, must separate from H118 REJECT 4/8) alongside >=2 other repo-new mechanisms.
- Deferred/held (no silent drops): NF-04 blocked; NF-05/07/08/10/11/13/15/17/20/21; NF-11r/NF-06-18 same root as NF-11; NF-06-11 infeasible; NF-06-01→H149; NF-06-03/23/24/27/28/30/32/33/35 (NF-06-28 no artifact); NF-07-05 data blocker; NF-07-11/12/14/31/32; NF-08-04/05/07/08/10/13/16/20/21/22/23/26/29; NF-09-03/04. Full list in `NEW_FAMILY_RESEARCH_REGISTER.md`.
- If `src/qtr` touched: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.

## Approaches that failed / evidence (do not blindly repeat)
- H161 failed Sharpe/PF/worst-regime/benchmark; inverse weaker (direction consistent) but no OOS edge. Do not rerun same G10 carry basket construction. Further FX variants must justify separation from H95/H103/H106/H129/H134/H161.
- NF-08-29 adjacent to H118 (within-equity return dispersion REJECT 4/8) — requires honest cross-asset separation justification if selected.

## One precise next task (Cycle 76 / H162)
Reconcile lineage to H161; complete directive §4 discovery (>=3 repo-new/decisive candidates across >=3 broad mechanism categories, honest 25/25/20/15/10/5, concrete deferred reassessment, NF-root checks). Re-assess NF-09-03/NF-09-04/NF-08-29 alongside >=2 other repo-new mechanisms. Pre-register highest-expected-information feasible candidate as **H162** before validation outcomes. Implement runner + focused tests; `ruff check/format --check`; `PYTHONPATH=src pytest -q` focused tests; execute REAL; record in `HYPOTHESIS_SPEC.md` §H162, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 76, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push unless authorized. `src/qtr` unchanged unless evidenced defect (then rerun pinned 100% suite).
