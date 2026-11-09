# HANDOFF_NEXT

## 1) What changed (Cycle 75 execution complete, H161 REJECT 4/8)

- **Lineage reconciled to H161.** H85–H161 all rejected/recorded. Cycle 75 discovery (directive §4) was completed previously (≥3 candidates across ≥3 categories, honest 25/25/20/15/10/5, no silent drops, NF-root integrity checks) and selected NF-20261109-02 (G10 currency carry basket risk-appetite timing SPY) as **H161**.
- **H161 executed (NF-20261109-02, REAL, REJECT 4/8).** `run_nf_20261109_02_g10_carry.py` + `tests/test_nf_20261109_02_g10_carry.py` (**10 passed**). `ruff check/format --check` clean on H161 files. Artifact `.experiments/nf_runs/nf_20261109_02_g10_carry/summary.json` (+`grid.csv`, `data_meta.json`).
- **H161 construction (pre-registered).** Equal-weight G10 carry basket (long AUD/NZD/CAD vs JPY, short EUR/CHF/USD vs JPY; USDJPY=X fetched for coverage, excluded from basket legs; GBPJPY=X fetched, not in basket). Rolling basket-return momentum sum (lookback) z-scored (z_window), hysteresis (`z<=-entry` de-risk, `z>=exit` full), vol-targeted long SPY, 1-bar delay via engine `signals.shift(1)`, long-only, Equity CostModel defaults, MAX_POS=0.5. Bounded grid 72 valid combos (`exit<=entry`); train-only 4-fold WF selection.
- **H161 data (REAL).** SPY + 7 FX pairs yfinance daily auto-adjust Close 2010-01-04→2026-10-30 (4226 rows; train 2510, val 756, test 960; OOS Val+Test n=1715).
- **H161 result (OOS Val+Test, 2669 trades).** Selected `lookback=252,z_window=252,entry_scale=2.0,exit_scale=0.5,vol_target=0.15` (WF train mean 1.117). Sharpe **0.892** fail, PF **1.221** fail, maxDD **-2.46%** pass, trades **2669** pass, WF **0.929** pass, worst-regime **-1.432** fail, benchmark-p **0.976**/IR **-0.740** fail, perturbation **0.618** pass → **REJECT 4/8**.
- **H161 ablations/falsifiers.** Buy-hold SPY 0.793; random-exposure-matched **0.518** (much weaker — structure present, not the failure mode); inverse-regime (de-risk on positive z) **0.503** (weaker — direction consistent with carry-unwind de-risking, but base fails OOS gates). Benchmark/worst-regime/Sharpe/PF fail; perturbation stable. No gate weakened. `src/qtr` unchanged.
- **Docs updated:** `HYPOTHESIS_SPEC.md` §H161 (PRE-REGISTERED → REJECT 4/8, full REAL result), `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 75 execution/lineage, `NEXT_TASK.md` Cycle 76.

## 2) Actually verified (this session)
- `python -m py_compile run_nf_20261109_02_g10_carry.py tests/test_nf_20261109_02_g10_carry.py` — OK.
- `python -m ruff check run_nf_20261109_02_g10_carry.py tests/test_nf_20261109_02_g10_carry.py` — All checks passed.
- `python -m ruff format --check run_nf_20261109_02_g10_carry.py tests/test_nf_20261109_02_g10_carry.py` — 2 files already formatted.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261109_02_g10_carry.py` — **10 passed**.
- `PYTHONPATH=src python run_nf_20261109_02_g10_carry.py` — REAL execution completed (70.3s); verdict REJECT 4/8.
- Artifact present/parsable: `.experiments/nf_runs/nf_20261109_02_g10_carry/summary.json`, `grid.csv`, `data_meta.json`.
- `src/qtr` unchanged; pinned 100% coverage suite **not rerun** (no `src/qtr` change). Deps present (numpy/pandas/scipy/pytest/ruff/yfinance).

## 3) Remains unresolved
- H85–H161 all REJECTED/recorded. Lineage gaps H24/H68–H73/H76–H79 unassigned (not recycled). **No commit/push performed** (not authorized).
- Cycle 76 must complete directive §4 discovery (>=3 repo-new/decisive candidates across >=3 broad mechanism categories, honest scoring, no silent drops, NF-root integrity checks) before selecting/pre-registering **H162**.
- Carried-forward candidates for Cycle 76 recheck (honest adjacency required): **NF-20261109-03** TIPS breakeven inflation level regime (3.95, adj NF-08/H154/H155), **NF-20261109-04** HYG momentum regime (3.95, adj H94/H108/H146), **NF-20261108-29** cross-asset return dispersion (4.10, must justify separation from H118 within-equity return dispersion REJECT 4/8). Must be re-assessed alongside >=2 other repo-new mechanisms.
- Deferred/held (no silent drops; full list in `NEW_FAMILY_RESEARCH_REGISTER.md`): NF-04 blocked (PIT term-structure/roll); NF-05/07/08/10/11/13/15/17/20/21; NF-11r/NF-06-18 same root as NF-11; NF-06-11 infeasible (CBOE PC); NF-06-01→H149; NF-06-03/23/24/27/28/30/32/33/35 (NF-06-28 no artifact, credit adj H94/H108); NF-07-05 data blocker (CPI surprise); NF-07-11/12/14/31/32 held; NF-08-04/05/07/08/10 deferred/held; NF-08-13 stub/deferred; NF-08-16 Halloween held (3.90); NF-08-20/21/22/23/26 deferred; NF-08-29 deferred (4.10).
- Published/certified artifacts and thresholds unchanged.

## 4) Approaches that failed (do not blindly repeat)
- **H161** (G10 carry basket, Cycle 75) failed Sharpe/PF/worst-regime/benchmark; random-exposure much weaker and inverse weaker (direction consistent) but no OOS edge. Do not rerun same construction. Note FX-channel adjacency to H95/H103/H106/H129/H134 — further FX carry variants must justify clear separation.
- **H160** (IVOL dispersion) inverse ≈ base (direction falsified) and return-dispersion control ≈ base. **H159** (VVIX-VIX) no edge/perturbation-stable. Do not rerun.
- Do not reuse NF roots without integrity check (H99/H149 collision precedent). NF-08-13 stub not decision-ready; NF-06-28 no artifact. NF-08-29 adjacent to H118 — requires honest cross-asset vs within-equity separation if selected.

## 5) One precise next task (Cycle 76 / H162)
Reconcile lineage to H161; complete directive §4 discovery (>=3 repo-new/decisive candidates across >=3 broad mechanism categories, honest 25/25/20/15/10/5, concrete deferred reassessment, NF-root checks). Re-assess NF-09-03/NF-09-04/NF-08-29 alongside >=2 other repo-new mechanisms. Pre-register highest-expected-information feasible candidate as **H162** before validation outcomes. Implement runner + focused tests; `ruff check/format --check` on new files; `PYTHONPATH=src pytest -q` focused tests; execute REAL; record verdict/artifacts in `HYPOTHESIS_SPEC.md` §H162, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 76, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. Justify independence from rejected classes including H161 and all FX/credit/vol families. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push unless authorized. If `src/qtr` touched, rerun pinned 100% coverage suite.
