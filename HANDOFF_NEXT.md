# HANDOFF_NEXT — After Cycle 62 / H148 (2026-11-08)

## Completed this cycle
- **H148 / NF-20261107-52 — SPY timing from EEM-vs-SPY realized-volatility divergence (cross-asset volatility transmission / global risk; RV-difference z-score): REJECT (4/8).**
  - Artifact: `.experiments/nf_runs/nf_20261107_52_eem_spy_rvdiv/summary.json` (+ `grid.csv`, `data_meta.json`, 5.61s, **corrected REAL**)
  - Runner: `run_nf_20261107_52_eem_spy_rvdiv.py`
  - Tests: `tests/test_nf_20261107_52_eem_spy_rvdiv.py` (**6 passed**)
  - **Integrity note:** an incomplete non-standard runner/artifact was committed earlier in Cycle 62 (commit `d5b8d74` context) without the standard gated/ablation protocol; repaired to the pre-registered standard protocol and re-executed. Committed artifact is the corrected REAL run.
  - Data (free/public yfinance, PIT): SPY + EEM daily auto-adjust Close, 3776 rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755).
  - Signal: z-score of trailing `(rv_EEM − rv_SPY)` (log-return rolling std) over `z_window`; continuous de-risking of vol-targeted long SPY when z abnormally positive (EM stress), 1-bar delay, long-only.
  - Selected (train-only 4-fold WF mean Sharpe 0.995): `rv_window=63, z_window=126, entry_scale=1.0, vol_target=0.15`.
  - OOS Val+Test (2757 engine trades, n=1259): Sharpe **0.946** fail, PF **1.215** fail, max DD **-2.57%** pass, trades **2757** pass, WF stability **0.951** pass, worst-regime rolling-252 **-0.820** fail, benchmark p **0.939** / IR **-0.714** fail, perturbation **0.943** pass → **4/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.750/1.153/-33.72%/1; random-exposure-matched **0.688**/1.168/-3.18%/1258 (weaker, no benchmark edge); **inverse regime** (de-risk when EEM RV abnormally low vs SPY / negative z) **0.540**/1.120/-2.08%/2747 (weaker; **direction supported**, unlike H138/H139 inverse outperformance, but no benchmark edge).
  - Honest adjacency: repo-new executed EEM/SPY RV-*difference* observable/pair. Separated from H138 (HYG−LQD/SPY RV ratio, REJECT 2/8) and H139 (IWM/SPY RV ratio, REJECT 2/8) — different asset pair/channel and difference construction; inverse direction supported here (unlike H138/H139) but no edge. Adjacent to H144 (EEM-SPY relative-momentum, REJECT 3/8; different observable). No validated edge.

## Discovery (Cycle 62, directive §4)
- Reconciled lineage to H147 (H85–H147 rejected/recorded). Proposed >=3 candidates across >=3 broad categories, scored 25/25/20/15/10/5:
  - NF-20261107-52 EEM-vs-SPY realized-vol divergence SPY timing (cross-asset volatility transmission / global risk) — **3.50, selected/executed H148**. Honest adjacency to H138/H139 RV-divergence class and H144 relmom acknowledged; inverse-falsifier tested.
  - NF-20261106-20 XLY/XLP consumer-discretionary-vs-staples ratio momentum — scored **3.55** but **NOT selected**: NF root corresponds to executed **H110** (`nf_20261106_20_xly_xlp_consumer`, REJECT 4/8). Honest correction recorded; do not re-propose executed NF roots.
  - NF-20261106-01 GDX-vs-GLD miner gold-beta RV divergence SPY timing (commodity volatility transmission / sector risk) — **3.50, deferred** (needs concrete separation from H88/H99/H101/H145 and RV-div class).
- Deferred/held reassessed with concrete evidence (no silent drops): NF-04 **blocked**; NF-05/07/08/10/11/13/15/17/20/21 **deferred** (**NF-20 root executed H110**); NF-11r/NF-06-18 same root as NF-11 (H141); NF-06-11 **infeasible**; NF-20261106-01 **deferred** (Cycle 62 scored); NF-20261106-03/23/24/28/30/32/33/35 **deferred**; NF-20261107-05 CPI **deferred** (data blocker). Held (materially different design required): NF-20261107-49 (correlation class H96/H127/H134/H137), NF-20261107-14/48 (IV-spread class H125/H126), NF-20261108-04 (OPX subclass H140). NF-20261107-52 **executed as H148 (REJECT)**. NF-20261108-05/07/08/10 **deferred**. Cycle 60 deferred: RV trend/momentum (adj H122/H29/H30), idiosyncratic-skew spread.

## Invariants preserved
- `src/qtr` unchanged — pinned 100% coverage suite **not rerun**.
- No published/certified/frozen artifacts, thresholds, or verdicts modified.
- Free/public yfinance data only. No gate weakening. No commit/push.

## Verified this session
- `python3 -m py_compile run_nf_20261107_52_eem_spy_rvdiv.py tests/test_nf_20261107_52_eem_spy_rvdiv.py` — OK.
- `python3 -m ruff check run_nf_20261107_52_eem_spy_rvdiv.py tests/test_nf_20261107_52_eem_spy_rvdiv.py` — clean.
- `python3 -m ruff format --check run_nf_20261107_52_eem_spy_rvdiv.py tests/test_nf_20261107_52_eem_spy_rvdiv.py` — clean (after formatting).
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261107_52_eem_spy_rvdiv.py` — **6 passed**.
- `PYTHONPATH=src python3 run_nf_20261107_52_eem_spy_rvdiv.py` — **REAL (corrected)** verdict **REJECT 4/8**; artifact written to `.experiments/nf_runs/nf_20261107_52_eem_spy_rvdiv/summary.json` (5.61s).
- Integrity: repaired earlier incomplete non-standard runner/artifact (commit `d5b8d74` context) to standard gated/ablation protocol and re-executed.

## Unresolved / risks
- H148 passes maxDD/trades/WF/perturbation but fails Sharpe/PF/worst-regime/benchmark; direction supported by inverse ablation but no benchmark-significant edge. Do not promote without fresh pre-registration/gates.
- RV-divergence construction class now has H138 (credit/SPY RV ratio, REJECT 2/8, inverse outperformed), H139 (IWM/SPY RV ratio, REJECT 2/8, inverse outperformed), H148 (EEM/SPY RV difference, REJECT 4/8, inverse weaker). Future RV-divergence candidates must demonstrate materially different mechanism/observable/pair and justify independence from this class.
- NF-20261106-01 (GDX-vs-GLD miner RV divergence, 3.50) deferred — adjacent to gold/miner H88/H99/H101/H145 and RV-div class; requires concrete separation.
- NF roots must be verified against executed H-IDs/artifacts before selection (Cycle 62 caught NF-20/H110 collision).

## Precise next task (Cycle 63, directive §4)
1. Reconcile lineage to H148 (H85–H148 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring; reassess deferred/held pool (NF-04 blocked; NF-05/07/08/10/11/13/15/17/21 deferred; **NF-20 root executed H110**; NF-11r/NF-06-18 same root as NF-11; NF-06-11 infeasible; NF-20261106-01/03/23/24/28/30/32/33/35 deferred; NF-20261107-05 deferred; NF-20261107-49/14(48) held; NF-20261108-04/05/07/08/10 deferred/held as noted) with concrete evidence (no silent drops). **Verify NF roots against executed H-IDs/artifacts.** Justify independence from rejected construction classes (correlation H96/H127/H134/H137; RV-divergence H138/H139/H148; OPX proximity H140; TOQ/H91; IV spread H125/H126; overnight/gap direction H18/H87; overnight-gap RV H143; Amihud H121; RV term structure H136; EEM-SPY relmom H144; GLD-SPY relmom H145; IVOL dispersion H146; breadth H115/H147; FX-strength H95/H103/H106).
3. Pre-register highest-expected-information feasible candidate as **H149** with smallest decisive test, PIT timing, costs, splits, gates, ablations, and falsifiers.
4. Implement runner + focused tests, run ruff, run focused pytest, execute, record verdict/artifacts in `HYPOTHESIS_SPEC.md` and `NEW_FAMILY_RESEARCH_REGISTER.md`, update `NEXT_TASK.md`/`HANDOFF_NEXT.md`.
5. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push. If `src/qtr` touched, rerun pinned 100% coverage suite.
