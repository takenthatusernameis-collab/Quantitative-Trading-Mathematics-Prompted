# HANDOFF_NEXT — After Cycle 61 / H147 (2026-11-08)

## Completed this cycle
- **H147 / NF-20261108-12 — SPY timing from sector participation breadth regime (market structure / participation breadth transmission; resolves held NF-20261107-31 with materially different construction from H115): REJECT (4/8).**
  - Artifact: `.experiments/nf_runs/nf_20261108_12_sector_breadth_spy/summary.json` (+ `grid.csv`, `data_meta.json`, 9.87s, REAL)
  - Runner: `run_nf_20261108_12_sector_breadth_spy.py`
  - Tests: `tests/test_nf_20261108_12_sector_breadth_spy.py` (**6 passed**)
  - Data (free/public yfinance, PIT): SPY + XLF,XLE,XLV,XLI,XLK,XLY,XLP,XLU,XLB daily auto-adjust Close, 3776 rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755).
  - Signal: `breadth_t = mean(1[Close_s,t > MA_s,t(ma_window)])` over 9 sectors; z = z-score of breadth over `z_window`; continuous de-risking of vol-targeted long SPY when breadth z abnormally negative (narrow participation), 1-bar delay, long-only.
  - Selected (train-only 4-fold WF mean Sharpe 0.755): `ma_window=200, z_window=252, entry_scale=2.0, vol_target=0.15`.
  - OOS Val+Test (3320 engine trades, n=1259): Sharpe **0.972** fail, PF **1.199** fail, max DD **-2.75%** pass, trades **3320** pass, WF stability **1.287** pass, worst-regime rolling-252 **-1.852** fail, benchmark p **0.939** / IR **-0.692** fail, perturbation **0.988** pass → **4/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.750/1.153/-33.72%/1; random-exposure-matched **0.518**/1.120/-6.40%/1258 (weaker, no benchmark edge); **inverse regime** (de-risk when breadth strong / positive z) **0.862**/1.168/-2.96%/3587 (weaker Sharpe; direction weakly supported, no benchmark edge).
  - Honest adjacency: repo-new executed *cross-sector MA-participation breadth* observable. Explicitly separated from H115 (RSP/SPY ratio-momentum breadth, REJECT 3/8; different observable/construction), H97 (cap-concentration mean reversion, REJECT), H129 (sector beta dispersion, REJECT). Resolves held NF-20261107-31 as this materially different construction. No validated edge.

## Discovery (Cycle 61, directive §4)
- Reconciled lineage to H146 (H85–H146 rejected/recorded). Proposed >=3 candidates across >=3 broad categories, scored 25/25/20/15/10/5:
  - NF-20261108-12 Cross-sector MA-participation breadth SPY timing (market structure / participation breadth) — **3.60, selected/executed H147**. Honest adjacency to H115 theme acknowledged; materially different observable (sector-count trend participation vs RSP/SPY ratio momentum).
  - NF-20261107-52 EEM-vs-SPY realized-vol divergence timing (cross-asset volatility / global risk transmission) — **3.50, held** (requires concrete separation from RV-divergence class H138/H139).
  - NF-20261108-07 TIP-vs-IEF inflation-compensation (breakeven-proxy) momentum SPY timing (macro term-premium / inflation-compensation transmission) — **3.35, deferred** (ETF breakeven proxy; prior proxy weakness).
- Deferred/held reassessed with concrete evidence (no silent drops): NF-04 **blocked**; NF-05/07/08/10/11/13/15/17/20/21 **deferred**; NF-11r/NF-06-18 same root as NF-11 (TLT-SHY proxy executed H141); NF-06-11 **infeasible**; NF-20261106-03/23/24/28/30/32/33/35 **deferred**; NF-20261107-05 CPI **deferred** (data blocker). Held (materially different design required): NF-20261107-49 (correlation class H96/H127/H134/H137), NF-20261107-52 (RV-div class H138/H139), NF-20261108-04 (OPX subclass H140), NF-20261107-14/48 (IV-spread class H125/H126). NF-20261107-31 **executed as H147 (REJECT)**. Cycle 60 deferred: RV trend/momentum (adj H122/H29/H30), idiosyncratic-skew spread (complexity/weak evidence).

## Invariants preserved
- `src/qtr` unchanged — pinned 100% coverage suite **not rerun**.
- No published/certified/frozen artifacts, thresholds, or verdicts modified.
- Free/public yfinance data only. No gate weakening. No commit/push.

## Verified this session
- `python3 -m py_compile run_nf_20261108_12_sector_breadth_spy.py tests/test_nf_20261108_12_sector_breadth_spy.py` — OK.
- `python3 -m ruff check run_nf_20261108_12_sector_breadth_spy.py tests/test_nf_20261108_12_sector_breadth_spy.py` — clean.
- `python3 -m ruff format --check run_nf_20261108_12_sector_breadth_spy.py tests/test_nf_20261108_12_sector_breadth_spy.py` — clean (after formatting).
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261108_12_sector_breadth_spy.py` — **6 passed**.
- `PYTHONPATH=src python3 run_nf_20261108_12_sector_breadth_spy.py` — **REAL** verdict **REJECT 4/8**; artifact written to `.experiments/nf_runs/nf_20261108_12_sector_breadth_spy/summary.json` (9.87s).

## Unresolved / risks
- H147 passes maxDD/trades/WF/perturbation but fails Sharpe/PF/worst-regime/benchmark; no benchmark-significant edge. Direction is only weakly supported by inverse ablation — do not promote without fresh pre-registration/gates.
- Breadth/participation theme now has H115 (RSP/SPY ratio-momentum, REJECT 3/8) and H147 (sector MA-participation, REJECT 4/8) with different observables; future breadth candidates must demonstrate materially different mechanism/observable beyond these constructions.
- NF-20261107-52 (EEM-SPY RV divergence) remains held but sits adjacent to RV-divergence construction class H138/H139 — requires clearly separated design/evidence if pursued.

## Precise next task (Cycle 62, directive §4)
1. Reconcile lineage to H147 (H85–H147 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring; reassess deferred/held pool (NF-04 blocked; NF-05/07/08/10/11/13/15/17/20/21 deferred; NF-11r/NF-06-18 same root as NF-11; NF-06-11 infeasible; NF-20261106-03/23/24/28/30/32/33/35 deferred; NF-20261107-05 deferred; NF-20261107-49/52/14(48)/NF-20261108-04/05/07/08/10 held/deferred as noted) with concrete evidence (no silent drops). Justify independence from rejected construction classes (correlation H96/H127/H134/H137; RV-divergence H138/H139; OPX proximity H140; TOQ/H91; IV spread H125/H126; overnight/gap direction H18/H87; overnight-gap RV H143; Amihud H121; RV term structure H136; EEM-SPY relmom H144; GLD-SPY relmom H145; IVOL dispersion H146; breadth H115/H147; FX-strength H95/H103/H106).
3. Pre-register highest-expected-information feasible candidate as **H148** with smallest decisive test, PIT timing, costs, splits, gates, ablations, and falsifiers.
4. Implement runner + focused tests, run ruff, run focused pytest, execute, record verdict/artifacts in `HYPOTHESIS_SPEC.md` and `NEW_FAMILY_RESEARCH_REGISTER.md`, update `NEXT_TASK.md`/`HANDOFF_NEXT.md`.
5. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push. If `src/qtr` touched, rerun pinned 100% coverage suite.
