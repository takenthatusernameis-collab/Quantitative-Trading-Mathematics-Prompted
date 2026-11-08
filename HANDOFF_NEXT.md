# HANDOFF_NEXT — After Cycle 67 / H153 (2026-11-08)

## Completed this cycle
- **H153 / NF-20261108-25 — SPY timing from TLT Treasury flight-to-quality lead-lag (bond safe-haven flow → equity risk-off): REJECT (4/8).**
  - Artifact: `.experiments/nf_runs/nf_20261108_25_tlt_spy_flight_quality_spy/summary.json` (+ `grid.csv`, `data_meta.json`, 23.32s, **REAL**).
  - Runner: `run_nf_20261108_25_tlt_spy_flight_quality_spy.py`.
  - Tests: `tests/test_nf_20261108_25_tlt_spy_flight_quality_spy.py` (**6 passed**).
  - Data (free/public, PIT): SPY + TLT yfinance daily auto-adjust, 3776 rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755), 0 non-positive.
  - Signal: z-score of trailing TLT return; continuous de-risking of vol-targeted long SPY when TLT rallies (**positive** z, pre-registered flight-to-quality); 1-bar delay via engine `signals.shift(1)`, long-only, MAX_POS=0.5, 1bp+1bp equity costs.
  - Selected (train-only 4-fold WF mean Sharpe 0.603): `mom_window=21, z_window=126, entry_scale=2.0, vol_target=0.15`.
  - OOS Val+Test (3698 engine trades, n=1259): Sharpe **0.792** fail, PF **1.149** fail, max DD **-2.45%** pass, trades **3698** pass, WF stability **1.315** pass, worst-regime rolling-252 Sharpe **-0.671** fail, benchmark p **0.948** / IR **-0.725** fail, perturbation min ratio **0.997** pass → **4/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.750/1.153/-33.72%/1; random-exposure-matched **0.546**/1.127/-5.31%/1258 (weaker — not pure noise — but no benchmark edge); **inverse regime** (de-risk when TLT weak / negative z) **0.891**/1.175/-3.25%/3700 — inverse outperforms base (0.891 vs 0.792), **pre-registered flight-to-quality direction falsified**; no validated directional edge.
  - Honest adjacency: repo-new executed directional TLT-to-SPY flight-to-quality lead-lag; distinct from H85 (equity-internal lead-lag), H141 (TLT-SHY term-spread momentum), H151 (TLT realized-vol stress), H92 (SPY-TLT relative momentum). No validated edge under pre-registered H153. No gate weakened; no published/certified artifact modified; `src/qtr` unchanged.

## Discovery (Cycle 67, directive §4)
- Reconciled lineage to H152; **H85–H153 all rejected/recorded**. Next unused H-ID: **H154** (H24/H68–H73/H76–H79 unassigned, not recycled).
- **NF root integrity (honest):** NF-20261108-25 verified unused before selection/execution. NF-20261108-23 (USO oil-price→SPY lead-lag, 3.25) and NF-20261108-24 (^TNX 10y yield-level→SPY, 3.70) scored but **deferred** (NF-24 same-root risk vs NF-17 short-rate level stub; NF-23 ambiguous oil→equity direction + USO roll/flow confounds). No H99/H149-style collisions.
- Candidates scored (25/25/20/15/10/5): NF-20261108-23 **3.25** deferred; NF-20261108-24 **3.70** deferred; NF-20261108-25 **3.70** selected/executed as H153 (tie-break: clearest separation from executed observables).
- Deferred/held reassessed (no silent drops): NF-04 blocked; NF-05/07/08/10/11/13/15/17/20/21 deferred; NF-20 executed H110; NF-11r/NF-06-18 same root as NF-11 (H141); NF-06-11 infeasible; NF-06-01 lineage executed H149 (NF-20261108-14); NF-06-03/23/24/28/30/32/33/35 deferred; NF-07-05 deferred (data blocker); NF-07-14/48 held (IV-spread H125/H126); NF-07-49 held (correlation H96/H127/H134/H137); NF-07-52 executed H148; NF-08-04/05/07/08/10 deferred/held; NF-08-13 ES-SPY basis stub/deferred; NF-08-16 Halloween seasonal held (3.90); NF-08-17 short-rate level deferred/incomplete (tracked stub); NF-08-19 executed H152; NF-08-20 IEF RV stress deferred (adj H151/TLT RV); NF-08-21 UNG-USO relmom deferred (3.30); NF-08-22 EFA-EEM relmom deferred (adj H144); NF-20261108-23 deferred (3.25); NF-20261108-24 deferred (3.70).

## Invariants preserved
- `src/qtr` unchanged — pinned 100% coverage suite **not rerun**.
- No published/certified/frozen artifacts, thresholds, or verdicts modified.
- Free/public data only (yfinance). No gate weakening. No commit/push.

## Verified this session
- `python -m ruff check run_nf_20261108_25_tlt_spy_flight_quality_spy.py tests/test_nf_20261108_25_tlt_spy_flight_quality_spy.py` — clean.
- `python -m ruff format --check run_nf_20261108_25_tlt_spy_flight_quality_spy.py tests/test_nf_20261108_25_tlt_spy_flight_quality_spy.py` — clean.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261108_25_tlt_spy_flight_quality_spy.py` — **6 passed**.
- `PYTHONPATH=src python run_nf_20261108_25_tlt_spy_flight_quality_spy.py` — **REAL** verdict **REJECT 4/8**; artifact written.

## Unresolved / risks
- H153 fails Sharpe/PF/worst-regime/benchmark; random exposure weaker (not pure noise) but no benchmark edge; inverse outperforms base (flight-to-quality direction falsified). Do not promote.
- NF-20261108-17 tracked stub is incomplete/unverified — do not execute as-is.
- NF-06-28 has legacy runner/test but no artifact; root/credit adjacency must be verified before any use.
- Correlation, RV-divergence, relmom, IV/vol, rates/term, breadth, IVOL, overnight/gap, FX-strength, institutional positioning, calendar seasonality, TLT RV, SLV-GLD relmom, and TLT flight-to-quality lead-lag classes have executed rejections — future candidates must demonstrate materially different mechanism/observable and justify independence.
- Search space heavily depleted (H85–H153 all rejected); Cycle 68 must complete the >=3-candidate, >=3-category discovery before selecting H154.

## Precise next task (Cycle 68, directive §4)
See `NEXT_TASK.md`. In summary: reconcile lineage to H153; propose >=3 repo-new candidates across >=3 broad categories with honest scoring; verify NF roots; pre-register highest-expected-information feasible candidate as **H154**; implement runner + focused tests; run ruff + focused pytest; execute; record verdict/artifacts; update docs. Free/public data only; no gate weakening; no commit/push. If `src/qtr` touched, rerun pinned 100% coverage suite.
