# HANDOFF_NEXT

## 1) What changed (Cycle 70 complete, H156 REJECT 5/8)

- **Lineage reconciled to H155.** H85–H155 all rejected/recorded. Next unused H-ID: **H157** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged.
- **Cycle 70 discovery (directive §4).** Proposed/scored 3 candidates across 3 broad mechanism categories (honest 25/25/20/15/10/5) with concrete deferred reassessment (no silent drops) and NF-root integrity checks against executed H-IDs/artifacts before selection.
  - NF-20261108-28 UUP realized-volatility stress SPY timing (3.70, **H156 selected/executed**) — FX volatility / global financial-conditions uncertainty (second-moment USD risk). Repo-new executed *UUP RV* observable; honest adjacency: same instrument as H95 UUP *direction* (REJECT 3/9, 88 trades, first moment) but different moment/channel; RV-stress construction class adj H151/H143/H149 (different asset/mechanism).
  - NF-20261108-27 EWJ-vs-SPY Japan equity relmom (3.55, deferred) — international/regional leadership; relmom-class adj H144/H145/H152; EWJ only in H2 universe spec.
  - NF-20261108-20 IEF realized-vol stress (3.50, deferred) — intermediate-duration bond RV, maturity/bond-RV adjacency H151 (TLT RV, REJECT 5/8).
  - NF-20261108-16 Halloween seasonal retained held (3.90 raw, calendar adj H91/H140/H142).
- **H156 executed (NF-20261108-28, REAL).** `run_nf_20261108_28_uup_rv_stress_spy.py` + `tests/test_nf_20261108_28_uup_rv_stress_spy.py` (**7 passed**). `ruff check/format` clean. Artifact `.experiments/nf_runs/nf_20261108_28_uup_rv_stress_spy/summary.json` (+grid/data_meta, 13.24s). Data SPY+UUP yfinance auto-adjust 3776 rows 2010-01-04→2025-01-03 (train 2516/val 505/test 755). Selected (train-only 4-fold WF mean 0.970): `rv_window=63, z_window=252, entry_scale=1.0, vol_target=0.15`. OOS Val+Test (2885 trades): Sharpe **1.158** pass, PF **1.262** fail, maxDD **-2.21%** pass, trades **2885** pass, WF **1.380** pass, worst-regime **-1.620** fail, benchmark-p **0.948**/IR **-0.670** fail, perturbation **0.986** pass → **REJECT 5/8**. Ablations: buy-hold 0.750; random-exposure-matched **0.229** (much weaker, not pure noise, no benchmark edge); inverse **0.485** (much weaker than base — direction supported, no benchmark edge).
- **Verdict:** No validated edge. PF/worst-regime/benchmark fail; random/inverse support direction/structure but no benchmark-significant timing edge (p=0.948, IR=−0.670). Honest adjacency disclosed (UUP RV vs H95 direction; RV-stress class vs H151/H143/H149). No gate weakened.

## 2) Actually verified
- `python -m ruff check run_nf_20261108_28_uup_rv_stress_spy.py tests/test_nf_20261108_28_uup_rv_stress_spy.py` — All checks passed.
- `python -m ruff format --check run_nf_20261108_28_uup_rv_stress_spy.py tests/test_nf_20261108_28_uup_rv_stress_spy.py` — 2 files already formatted.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261108_28_uup_rv_stress_spy.py` — **7 passed**.
- `PYTHONPATH=src python run_nf_20261108_28_uup_rv_stress_spy.py` — completed; artifact `.experiments/nf_runs/nf_20261108_28_uup_rv_stress_spy/summary.json` (+ `grid.csv`, `data_meta.json`, 13.24s). Verdict **REJECT 5/8**.
- `src/qtr` unchanged; pinned 100% coverage suite **not rerun**.

## 3) Remains unresolved
- H85–H156 all REJECTED/recorded. Lineage gaps H24/H68–H73/H76–H79 unassigned (not recycled). No commit/push. H156 runner/tests/docs/artifacts are uncommitted local changes.
- Deferred/held (no silent drops): NF-04 blocked; NF-05/07/08/10/11/13/15/20/21 deferred (NF-17 H154, NF-20 H110); NF-11r/NF-06-18 same root as NF-11 (H141); NF-06-11 infeasible; NF-06-01→H149; NF-06-03/23/24/28/30/32/33/35 deferred (NF-06-28 legacy runner/test no artifact, credit adj H94/H108); NF-07-05 data blocker; NF-07-14/48 held (IV-spread H125/H126); NF-07-49 held (corr H96/H127/H134/H137); NF-07-52→H148; NF-08-04/05/07/08/10 deferred/held; NF-08-13 ES-SPY basis stub/deferred; NF-08-16 Halloween held (3.90); NF-08-20 IEF RV stress deferred (3.50, adj H151/TLT RV maturity); NF-08-21 UNG-USO relmom deferred (3.30); NF-08-22 EFA-EEM relmom deferred (3.55); NF-08-23 USO oil-price→SPY lead-lag deferred (3.25); NF-20261108-26 GLD RV stress deferred (3.50, adj H151/H149); NF-20261108-27 EWJ-vs-SPY relmom deferred (3.55, relmom class adj).
- Search space heavily depleted (H85–H156 all rejected); Cycle 71 must complete >=3-candidate, >=3-category discovery before selecting H157.

## 4) Approaches that failed (do not blindly repeat)
- H156 (UUP RV stress, this cycle) failed PF/worst-regime/benchmark (Sharpe passed); random-exposure much weaker (structure) and inverse much weaker (direction supported) but no benchmark edge. Do not rerun same construction.
- Do not reuse NF roots without integrity check (see H99/H149 collision precedent). Verify runner/artifact/H-ID mapping before selection.
- NF-08-13 ES-SPY basis stub only (not decision-ready). NF-06-28 legacy runner/test but no artifact (credit adjacency H94/H108). NF-08-20 IEF RV adjacent to H151 — must justify maturity separation if selected.

## 5) One precise next task
See `NEXT_TASK.md`. In summary: reconcile lineage to H156; propose >=3 repo-new candidates across >=3 broad categories with honest scoring; verify NF roots; pre-register highest-expected-information feasible candidate as **H157**; implement runner + focused tests; run ruff + focused pytest; execute; record verdict/artifacts; update docs. Justify independence from rejected classes including UUP RV stress H156 and all prior listed classes. Free/public data only; no gate weakening; no commit/push. If `src/qtr` touched, rerun pinned 100% coverage suite.
