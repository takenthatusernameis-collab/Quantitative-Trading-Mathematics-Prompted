# HANDOFF_NEXT — After Cycle 64 / H150 (2026-11-08)

## Completed this cycle
- **H150 / NF-20261108-15 — SPY timing from CFTC TFF ES managed-money (leveraged-fund) net positioning flow (institutional positioning / crowding mean-reversion): REJECT (4/8).**
  - Artifact: `.experiments/nf_runs/nf_20261108_15_es_mm_flow_spy/summary.json` (+ `grid.csv`, `data_meta.json`, 18.99s, **REAL**).
  - Runner: `run_nf_20261108_15_es_mm_flow_spy.py`.
  - Tests: `tests/test_nf_20261108_15_es_mm_flow_spy.py` (**7 passed**).
  - Data (free/public, PIT): SPY + ES=F yfinance daily auto-adjust, 3774 rows 2010-01-04→2025-01-03 (train 2514 / val 505 / test 755); CFTC TFF "S&P 500 Consolidated" leveraged-money net position, 755 weekly report rows 2010-07-20→2024-12-31, forward-filled to daily (report date known at close → PIT-safe; multi-era column/date conventions handled; no double-counting of overlapping contracts).
  - Signal: z-score of trailing leveraged-money net position; continuous de-risking of vol-targeted long SPY on positive z; 1-bar delay via engine `signals.shift(1)`, long-only, MAX_POS=0.5, 1bp+1bp equity costs.
  - Selected (train-only 4-fold WF mean Sharpe 1.038): `mm_window=63, z_window=126, entry_scale=1.0, vol_target=0.15`.
  - OOS Val+Test (3186 engine trades, n=1259): Sharpe **0.885** fail, PF **1.185** fail, max DD **-3.14%** pass, trades **3186** pass, WF stability **0.852** pass, worst-regime rolling-252 Sharpe **-1.466** fail, benchmark p **0.936** / IR **-0.711** fail, perturbation min ratio **0.982** pass → **4/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.750/1.153/-33.72%/1; random-exposure-matched **0.577**/1.131/-5.91%/1258 (weaker — not noise — but no benchmark edge); **inverse regime** (de-risk when ES MM net abnormally LOW / negative z) **0.700**/1.148/-2.70%/3171 — weaker than base; direction weakly supported, no benchmark edge.
  - Honest adjacency: repo-new CFTC TFF positioning-flow root family (first execution of regulatory positioning data in repo); distinct from H141 TLT-SHY term-*spread* slope (rates channel, not positioning) and H140 OPX flow-proximity. No validated edge under pre-registered H150. No gate weakened; no published/certified artifact modified; `src/qtr` unchanged.

## Discovery (Cycle 64, directive §4)
- Reconciled lineage to H149; **H85–H150 all rejected/recorded**. Next unused H-ID: **H151** (H24/H68–H73/H76–H79 unassigned, not recycled).
- Candidates scored (25/25/20/15/10/5): NF-20261108-15/H150 **4.00** (executed); NF-20261108-16 Halloween semi-annual seasonal **3.90** held; NF-20261108-17 ^IRX 13-week T-bill yield level **3.70** deferred (adjacent to H141 rates family — level vs slope).
- NF root integrity: every candidate NF root verified against executed H-IDs/artifacts before selection; no H99/H149-style collisions this cycle.
- Deferred/held reassessed (no silent drops): NF-04 **blocked**; NF-05/07/08/10/11/13/15/17/20/21 **deferred**; NF-20 executed H110; NF-11r/NF-06-18 same root as NF-11 (H141); NF-06-11 **infeasible**; NF-06-01 lineage executed H149 (NF-20261108-14); NF-06-03/23/24/28/30/32/33/35 **deferred** (verify roots); NF-07-05 **deferred**; NF-07-14/48 **held**; NF-07-49 **held**; NF-07-52 executed H148; NF-08-04/05/07/08/10 **deferred/held**.

## Invariants preserved
- `src/qtr` unchanged — pinned 100% coverage suite **not rerun**.
- No published/certified/frozen artifacts, thresholds, or verdicts modified.
- Free/public data only (yfinance + CFTC TFF public CSV). No gate weakening. No commit/push.

## Verified this session
- `python3 -m ruff check run_nf_20261108_15_es_mm_flow_spy.py tests/test_nf_20261108_15_es_mm_flow_spy.py` — clean.
- `python3 -m ruff format --check run_nf_20261108_15_es_mm_flow_spy.py tests/test_nf_20261108_15_es_mm_flow_spy.py` — clean.
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261108_15_es_mm_flow_spy.py` — **7 passed**.
- `PYTHONPATH=src python3 run_nf_20261108_15_es_mm_flow_spy.py` — **REAL** verdict **REJECT 4/8**; artifact written.

## Unresolved / risks
- H150 fails Sharpe/PF/worst-regime/benchmark; random exposure weaker (not noise) but no benchmark edge; inverse weaker (direction weakly supported). Do not promote.
- RV-divergence, correlation, calendar, relative-momentum, breadth, IVOL, overnight-gap, FX-strength, and institutional-positioning construction classes all now have executed rejections — future candidates must demonstrate materially different mechanism/observable and justify independence.
- CFTC TFF data ends 2024-12-31 (forward-filled to test end); cftc.gov network dependency — verify fetch before execution if reused.

## Precise next task (Cycle 65, directive §4)
1. Reconcile lineage to H150 (H85–H150 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring. **Verify NF roots against executed H-IDs/artifacts before selection.** Reassess deferred/held pool with concrete evidence (no silent drops): NF-04 blocked; NF-05/07/08/10/11/13/15/17/20/21 deferred; NF-20 executed H110; NF-11r/NF-06-18 same root as NF-11 (H141); NF-06-11 infeasible; NF-06-01 lineage executed H149 (NF-20261108-14); NF-06-03/23/24/28/30/32/33/35 deferred (verify roots); NF-07-05 deferred; NF-07-14/48 held (IV-spread H125/H126); NF-07-49 held (correlation H96/H127/H134/H137); NF-07-52 executed H148; NF-08-04/05/07/08/10 deferred/held; NF-20261108-16 Halloween seasonal held (3.90); NF-20261108-17 ^IRX short-rate level deferred (3.70). Justify independence from rejected construction classes (correlation H96/H127/H134/H137; RV-divergence H138/H139/H148/H149; OPX proximity H140; TOQ/H91; IV spread H125/H126; overnight/gap direction H18/H87; overnight-gap RV H143; Amihud H121; RV term structure H136; EEM-SPY relmom H144; GLD-SPY relmom H145; IVOL dispersion H146; breadth H115/H147; FX-strength H95/H103/H106; institutional positioning H150).
3. Pre-register highest-expected-information feasible candidate as **H151** with smallest decisive test, PIT timing, costs, splits, gates, ablations, and falsifiers.
4. Implement runner + focused tests, run ruff, run focused pytest, execute, record verdict/artifacts in `HYPOTHESIS_SPEC.md` and `NEW_FAMILY_RESEARCH_REGISTER.md`, update `NEXT_TASK.md`/`HANDOFF_NEXT.md`.
5. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push. If `src/qtr` touched, rerun pinned 100% coverage suite.
