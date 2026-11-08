# HANDOFF_NEXT — After Cycle 66 / H152 (2026-11-08)

## Completed this cycle
- **H152 / NF-20261108-19 — SPY timing from SLV-vs-GLD precious-metals relative-momentum regime (industrial silver-beta vs gold safe-haven transmission): REJECT (4/8).**
  - Artifact: `.experiments/nf_runs/nf_20261108_19_slv_gld_relmom_spy/summary.json` (+ `grid.csv`, `data_meta.json`, 21.38s, **REAL**).
  - Runner: `run_nf_20261108_19_slv_gld_relmom_spy.py`.
  - Tests: `tests/test_nf_20261108_19_slv_gld_relmom_spy.py` (**6 passed**).
  - Data (free/public, PIT): SPY + SLV + GLD yfinance daily auto-adjust, 3776 rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755), 0 non-positive.
  - Signal: z-score of trailing `ret(SLV,w)-ret(GLD,w)`; continuous de-risking of vol-targeted long SPY when silver underperforms gold (**negative** z, pre-registered); 1-bar delay via engine `signals.shift(1)`, long-only, MAX_POS=0.5, 1bp+1bp equity costs.
  - Selected (train-only 4-fold WF mean Sharpe 0.970): `mom_window=63, z_window=126, entry_scale=2.0, vol_target=0.15`.
  - OOS Val+Test (3536 engine trades, n=1259): Sharpe **0.780** fail, PF **1.158** fail, max DD **-3.27%** pass, trades **3536** pass, WF stability **0.804** pass, worst-regime rolling-252 Sharpe **-1.226** fail, benchmark p **0.949** / IR **-0.720** fail, perturbation min ratio **0.920** pass → **4/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.750/1.153/-33.72%/1; random-exposure-matched **0.572**/1.134/-5.14%/1258 (weaker — not pure noise — but no benchmark edge); **inverse regime** (de-risk when SLV leads GLD / positive z) **0.761**/1.150/-2.66%/3446 — near base (no decisive directional edge; benchmark fails).
  - Honest adjacency: repo-new executed SLV-GLD relative-momentum SPY-timing observable; distinct from H88 (GLD/SLV/DXY RV, REJECT 1/9 — different observable/mechanism), H145 (GLD-vs-SPY relmom, REJECT 4/8 — different signal pair), H99/H101 (GDX/GLD, GLD/XLE). No validated edge under pre-registered H152. No gate weakened; no published/certified artifact modified; `src/qtr` unchanged.

## Discovery (Cycle 66, directive §4)
- Reconciled lineage to H151; **H85–H152 all rejected/recorded**. Next unused H-ID: **H153** (H24/H68–H73/H76–H79 unassigned, not recycled).
- **NF root integrity (honest):** NF-20261108-19 verified unused before selection/execution (Cycle 65 deferred 3.65). NF-20261108-17 tracked stub remains **deferred/incomplete** (docstring-only, no tests/artifacts, unverified mapping) — not executed. NF-08-16 held (no runner/artifact). NF-08-20/21/22 verified unused in assessment. NF-06-28 has legacy runner/test but no artifact; credit adjacency H94/H108 — not selected. No H99/H149-style collisions.
- Candidates scored (25/25/20/15/10/5): NF-20261108-19 SLV-vs-GLD relmom **3.65** (executed as H152); NF-20261108-16 Halloween semi-annual seasonal **3.90 raw held** (calendar adjacency H91/H140/H142, decayed evidence); NF-20261108-21 UNG-vs-USO natgas/oil relmom **3.30** deferred (ETF roll/flow confounds).
- Deferred/held reassessed (no silent drops): NF-04 **blocked**; NF-05/07/08/10/11/13/15/17/20/21 **deferred**; NF-20 executed H110; NF-11r/NF-06-18 same root as NF-11 (H141); NF-06-11 **infeasible**; NF-06-01 lineage executed H149 (NF-20261108-14); NF-06-03/23/24/28/30/32/33/35 **deferred** (verify roots; NF-06-28 legacy stub/no artifact, credit adjacency); NF-07-05 **deferred** (data blocker); NF-07-14/48 **held** (IV-spread H125/H126); NF-07-49 **held** (correlation H96/H127/H134/H137); NF-07-52 executed H148; NF-08-04/05/07/08/10 **deferred/held**; NF-08-13 ES-SPY basis **stub/deferred**; NF-08-16 Halloween seasonal **held** (3.90); NF-08-17 short-rate level **deferred/incomplete** (tracked stub); NF-08-19 executed H152; NF-08-20 IEF RV stress **deferred** (adj H151/TLT RV); NF-08-21 UNG-USO relmom **deferred** (3.30); NF-08-22 EFA-EEM relmom **deferred** (adj H144).

## Invariants preserved
- `src/qtr` unchanged — pinned 100% coverage suite **not rerun**.
- No published/certified/frozen artifacts, thresholds, or verdicts modified.
- Free/public data only (yfinance). No gate weakening. No commit/push.

## Verified this session
- `python -m ruff check run_nf_20261108_19_slv_gld_relmom_spy.py tests/test_nf_20261108_19_slv_gld_relmom_spy.py` — clean.
- `python -m ruff format --check run_nf_20261108_19_slv_gld_relmom_spy.py tests/test_nf_20261108_19_slv_gld_relmom_spy.py` — clean.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261108_19_slv_gld_relmom_spy.py` — **6 passed**.
- `PYTHONPATH=src python run_nf_20261108_19_slv_gld_relmom_spy.py` — **REAL** verdict **REJECT 4/8**; artifact written.

## Unresolved / risks
- H152 fails Sharpe/PF/worst-regime/benchmark; random exposure weaker (not noise) but no benchmark edge; inverse near base (direction not validated). Do not promote.
- NF-20261108-17 tracked stub is incomplete/unverified — do not execute as-is.
- NF-06-28 has legacy runner/test but no artifact; root/credit adjacency must be verified before any use.
- Calendar, RV-divergence, correlation, IV/vol, rates/term, relmom, breadth, IVOL, overnight/gap, FX-strength, institutional-positioning, TLT realized-vol, and SLV-GLD relmom construction classes have executed rejections — future candidates must demonstrate materially different mechanism/observable and justify independence.

## Precise next task (Cycle 67, directive §4)
1. Reconcile lineage to H152 (H85–H152 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring. **Verify NF roots against executed H-IDs/artifacts before selection.** Reassess deferred/held pool with concrete evidence (no silent drops): NF-04 blocked; NF-05/07/08/10/11/13/15/17/20/21 deferred; NF-20 executed H110; NF-11r/NF-06-18 same root as NF-11 (H141); NF-06-11 infeasible; NF-06-01 lineage executed H149 (NF-20261108-14); NF-06-03/23/24/28/30/32/33/35 deferred (verify roots; NF-06-28 legacy stub/no artifact, credit adjacency H94/H108); NF-07-05 deferred (data blocker); NF-07-14/48 held (IV-spread H125/H126); NF-07-49 held (correlation H96/H127/H134/H137); NF-07-52 executed H148; NF-08-04/05/07/08/10 deferred/held; NF-08-13 ES-SPY basis stub/deferred; NF-08-16 Halloween seasonal held (3.90, calendar adjacency H91/H140/H142); NF-08-17 short-rate level deferred/incomplete (tracked stub); NF-08-19 executed H152; NF-08-20 IEF RV stress deferred (adj H151/TLT RV); NF-08-21 UNG-USO relmom deferred (3.30, ETF roll/flow confounds); NF-08-22 EFA-EEM relmom deferred (adj H144). Justify independence from rejected construction classes (correlation H96/H127/H134/H137; RV-divergence H138/H139/H148/H149; OPX proximity H140; TOQ/H91; IV spread H125/H126; overnight/gap direction H18/H87; overnight-gap RV H143; Amihud H121; RV term structure H136; EEM-SPY relmom H144; GLD-SPY relmom H145; IVOL dispersion H146; breadth H115/H147; FX-strength H95/H103/H106; institutional positioning H150; calendar seasonality H91/H142/H140; TLT realized-vol stress H151; SLV-GLD relmom H152).
3. Pre-register highest-expected-information feasible candidate as **H153** with smallest decisive test, PIT timing, costs, splits, gates, ablations, and falsifiers.
4. Implement runner + focused tests, run ruff, run focused pytest, execute, record verdict/artifacts in `HYPOTHESIS_SPEC.md` and `NEW_FAMILY_RESEARCH_REGISTER.md`, update `NEXT_TASK.md`/`HANDOFF_NEXT.md`.
5. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push. If `src/qtr` touched, rerun pinned 100% coverage suite.
