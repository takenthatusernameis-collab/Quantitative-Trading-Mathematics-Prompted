# HANDOFF_NEXT — After Cycle 65 / H151 (2026-11-08)

## Completed this cycle
- **H151 / NF-20261108-18 — SPY timing from TLT realized-volatility stress regime (bond-market volatility transmission): REJECT (5/8).**
  - Artifact: `.experiments/nf_runs/nf_20261108_18_tlt_rv_stress_spy/summary.json` (+ `grid.csv`, `data_meta.json`, 14.09s, **REAL**).
  - Runner: `run_nf_20261108_18_tlt_rv_stress_spy.py`.
  - Tests: `tests/test_nf_20261108_18_tlt_rv_stress_spy.py` (**6 passed**).
  - Data (free/public, PIT): SPY + TLT yfinance daily auto-adjust, 3776 rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755), 0 non-positive.
  - Signal: z-score of trailing TLT realized volatility (`rolling_std(pct_change(TLT), rv_window)*sqrt(252)` over `z_window`); continuous de-risking of vol-targeted long SPY on positive z; 1-bar delay via engine `signals.shift(1)`, long-only, MAX_POS=0.5, 1bp+1bp equity costs.
  - Selected (train-only 4-fold WF mean Sharpe 0.935): `rv_window=63, z_window=252, entry_scale=1.0, vol_target=0.15`.
  - OOS Val+Test (2705 engine trades, n=1259): Sharpe **1.060** pass, PF **1.251** fail, max DD **-1.94%** pass, trades **2705** pass, WF stability **1.133** pass, worst-regime rolling-252 Sharpe **-1.193** fail, benchmark p **0.937** / IR **-0.684** fail, perturbation min ratio **0.957** pass → **5/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.750/1.153/-33.72%/1; random-exposure-matched **0.273**/1.062/-7.10%/1258 (much weaker — signal not noise — but no benchmark edge); **inverse regime** (de-risk when TLT RV abnormally LOW / negative z) **0.532**/1.114/-3.15%/2769 — materially weaker (direction supported, no benchmark edge).
  - Honest adjacency: repo-new executed *TLT realized-volatility* observable; distinct from H141 TLT-SHY term-spread *momentum* (REJECT 5/8), H96/H127 TLT *correlations*, H100 ^MOVE *implied* rates vol (REJECT 5/9). No validated edge under pre-registered H151. No gate weakened; no published/certified artifact modified; `src/qtr` unchanged.

## Discovery (Cycle 65, directive §4)
- Reconciled lineage to H150; **H85–H151 all rejected/recorded**. Next unused H-ID: **H152** (H24/H68–H73/H76–H79 unassigned, not recycled).
- **NF root integrity (honest):** NF-20261108-17 short-rate level stub is tracked (HEAD 2f9c68e) but **deferred/incomplete** (docstring-only, no tests/artifacts, unverified signal-direction mapping) — not executed/reused. NF-08-16 held (no runner/artifact). NF-08-18/19/20 verified unused before selection. No H99/H149-style collisions.
- Candidates scored (25/25/20/15/10/5): NF-20261108-18 TLT RV stress **3.65** (executed as H151); NF-20261108-19 SLV-vs-GLD precious-metals relmom **3.65** deferred (adjacency H88/H145/GLD families); NF-20261108-16 Halloween semi-annual seasonal **3.90** raw **held** (calendar adjacency H91/H140/H142; not selected despite raw score).
- Deferred/held reassessed (no silent drops): NF-04 **blocked**; NF-05/07/08/10/11/13/15/17/20/21 **deferred**; NF-20 executed H110; NF-11r/NF-06-18 same root as NF-11 (H141); NF-06-11 **infeasible**; NF-06-01 lineage executed H149 (NF-20261108-14); NF-06-03/23/24/28/30/32/33/35 **deferred** (verify roots); NF-07-05 **deferred** (data blocker); NF-07-14/48 **held** (IV-spread H125/H126); NF-07-49 **held** (correlation H96/H127/H134/H137); NF-07-52 executed H148; NF-08-04/05/07/08/10 **deferred/held**; NF-08-13 ES-SPY basis **stub/deferred**; NF-08-16 Halloween seasonal **held** (3.90); NF-08-17 short-rate level **deferred/incomplete** (tracked stub); NF-08-19 SLV-GLD relmom **deferred** (3.65).

## Invariants preserved
- `src/qtr` unchanged — pinned 100% coverage suite **not rerun**.
- No published/certified/frozen artifacts, thresholds, or verdicts modified.
- Free/public data only (yfinance). No gate weakening. No commit/push.

## Verified this session
- `python -m ruff check run_nf_20261108_18_tlt_rv_stress_spy.py tests/test_nf_20261108_18_tlt_rv_stress_spy.py` — clean.
- `python -m ruff format --check run_nf_20261108_18_tlt_rv_stress_spy.py tests/test_nf_20261108_18_tlt_rv_stress_spy.py` — clean.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261108_18_tlt_rv_stress_spy.py` — **6 passed**.
- `PYTHONPATH=src python run_nf_20261108_18_tlt_rv_stress_spy.py` — **REAL** verdict **REJECT 5/8**; artifact written.

## Unresolved / risks
- H151 passes Sharpe but fails PF/worst-regime/benchmark; random exposure much weaker (not noise) but no benchmark edge; direction supported (inverse weaker). Do not promote.
- NF-20261108-17 tracked stub is incomplete/unverified — do not execute as-is.
- Calendar, RV-divergence, correlation, IV/vol, rates/term, relmom, breadth, IVOL, overnight/gap, FX-strength, institutional-positioning, and TLT realized-vol construction classes have executed rejections — future candidates must demonstrate materially different mechanism/observable and justify independence.

## Precise next task (Cycle 66, directive §4)
1. Reconcile lineage to H151 (H85–H151 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring. **Verify NF roots against executed H-IDs/artifacts before selection.** Reassess deferred/held pool with concrete evidence (no silent drops): NF-04 blocked; NF-05/07/08/10/11/13/15/17/20/21 deferred; NF-20 executed H110; NF-11r/NF-06-18 same root as NF-11 (H141); NF-06-11 infeasible; NF-06-01 lineage executed H149 (NF-20261108-14); NF-06-03/23/24/28/30/32/33/35 deferred (verify roots); NF-07-05 deferred (data blocker); NF-07-14/48 held (IV-spread H125/H126); NF-07-49 held (correlation H96/H127/H134/H137); NF-07-52 executed H148; NF-08-04/05/07/08/10 deferred/held; NF-08-13 ES-SPY basis stub/deferred; NF-08-16 Halloween seasonal held (3.90); NF-08-17 short-rate level deferred/incomplete (tracked stub); NF-08-19 SLV-GLD relmom deferred (3.65). Justify independence from rejected construction classes (correlation H96/H127/H134/H137; RV-divergence H138/H139/H148/H149; OPX proximity H140; TOQ/H91; IV spread H125/H126; overnight/gap direction H18/H87; overnight-gap RV H143; Amihud H121; RV term structure H136; EEM-SPY relmom H144; GLD-SPY relmom H145; IVOL dispersion H146; breadth H115/H147; FX-strength H95/H103/H106; institutional positioning H150; calendar seasonality H91/H142/H140; TLT realized-vol stress H151).
3. Pre-register highest-expected-information feasible candidate as **H152** with smallest decisive test, PIT timing, costs, splits, gates, ablations, and falsifiers.
4. Implement runner + focused tests, run ruff, run focused pytest, execute, record verdict/artifacts in `HYPOTHESIS_SPEC.md` and `NEW_FAMILY_RESEARCH_REGISTER.md`, update `NEXT_TASK.md`/`HANDOFF_NEXT.md`.
5. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push. If `src/qtr` touched, rerun pinned 100% coverage suite.
