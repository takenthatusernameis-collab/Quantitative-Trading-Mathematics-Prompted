# HANDOFF_NEXT

## 1) What changed (Cycle 71 complete, H157 REJECT 5/8)

- **Lineage reconciled to H156.** H85–H156 all rejected/recorded. Next unused H-ID assigned: **H157** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged.
- **Cycle 71 discovery (directive §4).** Proposed/scored 3 candidates across 3 broad mechanism categories (honest 25/25/20/15/10/5) with concrete deferred reassessment (no silent drops) and NF-root integrity checks against executed H-IDs/artifacts before selection.
  - NF-20261108-27 EWJ-vs-SPY relative-momentum SPY timing (3.55, **H157 selected/executed**, tie-break) — international equity / regional developed-market (Japan) leadership/funding-spillover transmission. Repo-new executed pair (EWJ unexecuted as SPY-timing signal despite H2/artifact presence; NF root verified). Honest relmom/z-score construction adjacency to H144 EEM-SPY (REJECT 3/8, inverse outperformed), H145 GLD-SPY (REJECT 4/8), H152 SLV-GLD relmom→SPY (REJECT 4/8) — different pair/mechanism.
  - NF-20261108-22 EFA-vs-EEM DM/EM relmom (3.55, deferred) — international DM/EM spread; relmom-class/H144 adjacency.
  - NF-20261108-20 IEF realized-vol stress (3.50, deferred) — intermediate-duration bond RV, maturity/bond-RV adjacency H151 (TLT RV, REJECT 5/8).
  - NF-20261108-16 Halloween seasonal retained held (3.90 raw, calendar adj H91/H140/H142).
- **H157 executed (NF-20261108-27, REAL).** `run_nf_20261108_27_ewj_spy_relmom.py` + `tests/test_nf_20261108_27_ewj_spy_relmom.py` (**7 passed**). `ruff check/format` clean. Artifact `.experiments/nf_runs/nf_20261108_27_ewj_spy_relmom/summary.json` (+grid/data_meta, 13.54s). Data SPY+EWJ yfinance auto-adjust 3776 rows 2010-01-04→2025-01-03 (train 2516/val 505/test 755). Selected (train-only 4-fold WF mean 0.930): `mom_window=63, z_window=126, entry_scale=1.0, vol_target=0.15`. OOS Val+Test (2846 trades): Sharpe **1.202** pass, PF **1.273** fail, maxDD **-2.47%** pass, trades **2846** pass, WF **1.346** pass, worst-regime **-0.543** fail, benchmark-p **0.932**/IR **-0.688** fail, perturbation **0.988** pass → **REJECT 5/8**. Ablations: buy-hold 0.750; random-exposure-matched **-0.323** (much weaker, not pure noise, no benchmark edge); inverse **0.222** (much weaker than base — direction supported, no benchmark edge).
- **Verdict:** No validated edge. PF/worst-regime/benchmark fail; random/inverse support direction/structure but no benchmark-significant timing edge (p=0.932, IR=−0.688). Honest relmom-class adjacency disclosed. No gate weakened.

## 2) Actually verified
- `python -m ruff check run_nf_20261108_27_ewj_spy_relmom.py tests/test_nf_20261108_27_ewj_spy_relmom.py` — All checks passed.
- `python -m ruff format --check run_nf_20261108_27_ewj_spy_relmom.py tests/test_nf_20261108_27_ewj_spy_relmom.py` — 2 files already formatted.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261108_27_ewj_spy_relmom.py` — **7 passed**.
- `PYTHONPATH=src python run_nf_20261108_27_ewj_spy_relmom.py` — completed; artifact `.experiments/nf_runs/nf_20261108_27_ewj_spy_relmom/summary.json` (+ `grid.csv`, `data_meta.json`, 13.54s). Verdict **REJECT 5/8**.
- `src/qtr` unchanged; pinned 100% coverage suite **not rerun**.

## 3) Remains unresolved
- H85–H157 all REJECTED/recorded. Lineage gaps H24/H68–H73/H76–H79 unassigned (not recycled). No commit/push. H157 runner/tests/docs/artifacts are uncommitted local changes.
- Deferred/held (no silent drops): NF-04 blocked; NF-05/07/08/10/11/13/15/20/21 deferred (NF-17 H154, NF-20 H110); NF-11r/NF-06-18 same root as NF-11 (H141); NF-06-11 infeasible; NF-06-01→H149; NF-06-03/23/24/28/30/32/33/35 deferred (NF-06-28 legacy runner/test no artifact, credit adj H94/H108); NF-07-05 data blocker; NF-07-14/48 held (IV-spread H125/H126); NF-07-49 held (corr H96/H127/H134/H137); NF-07-52→H148; NF-08-04/05/07/08/10 deferred/held; NF-08-13 ES-SPY basis stub/deferred; NF-08-16 Halloween held (3.90); NF-08-20 IEF RV stress deferred (3.50, adj H151/TLT RV maturity); NF-08-21 UNG-USO relmom deferred (3.30); NF-08-22 EFA-EEM relmom deferred (3.55, relmom-class/H144 adj); NF-08-23 USO oil-price→SPY lead-lag deferred (3.25); NF-20261108-26 GLD RV stress deferred (3.50, adj H151/H149).
- Search space heavily depleted (H85–H157 all rejected); Cycle 72 must complete >=3-candidate, >=3-category discovery before selecting H158.

## 4) Approaches that failed (do not blindly repeat)
- H157 (EWJ-SPY relmom, this cycle) failed PF/worst-regime/benchmark (Sharpe passed); random-exposure much weaker (structure) and inverse much weaker (direction supported) but no benchmark edge. Do not rerun same construction.
- Do not reuse NF roots without integrity check (see H99/H149 collision precedent). Verify runner/artifact/H-ID mapping before selection.
- NF-08-13 ES-SPY basis stub only (not decision-ready). NF-06-28 legacy runner/test but no artifact (credit adjacency H94/H108). NF-08-20 IEF RV adjacent to H151 — must justify maturity separation if selected. NF-08-22 EFA-EEM relmom adjacent to relmom class/H144 — modest expected information.

## 5) One precise next task
See `NEXT_TASK.md`. In summary: reconcile lineage to H157; propose >=3 repo-new candidates across >=3 broad categories with honest scoring; verify NF roots; pre-register highest-expected-information feasible candidate as **H158**; implement runner + focused tests; run ruff + focused pytest; execute; record verdict/artifacts; update docs. Justify independence from rejected classes including EWJ-SPY relmom H157 and all prior listed classes. Free/public data only; no gate weakening; no commit/push. If `src/qtr` touched, rerun pinned 100% coverage suite.
