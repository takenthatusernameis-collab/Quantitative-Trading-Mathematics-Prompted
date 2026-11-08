# HANDOFF_NEXT — After Cycle 63 / H149 (2026-11-08)

## Completed this cycle
- **H149 / NF-20261106-01 lineage (executed as NF-20261108-14) — SPY timing from GDX-vs-GLD realized-volatility divergence (commodity volatility transmission / gold-miner sector risk): REJECT (4/8).**
  - Artifact: `.experiments/nf_runs/nf_20261108_14_gdx_gld_rv_spy/summary.json` (+ `grid.csv`, `data_meta.json`, 5.71s, **REAL**)
  - Runner: `run_nf_20261108_14_gdx_gld_rv_spy.py`
  - Tests: `tests/test_nf_20261108_14_gdx_gld_rv_spy.py` (**6 passed**)
  - **NF-root collision / integrity (honest):** H149 was pre-registered as NF-20261106-01, but NF-20261106-01 was already executed as **H99** (`nf_20261106_01_miner_gold_rv`, GDX/GLD spread mean-reversion, REJECT) with committed artifacts. H149 implemented/executed under **NF-20261108-14** following the pre-registered mechanism/protocol; **H99 artifacts preserved**.
  - Data (free/public yfinance, PIT): SPY + GDX + GLD daily auto-adjust Close, 3776 rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755).
  - Signal: z-score of trailing `(rv_GDX − rv_GLD)` (log-return rolling std) over `z_window`; continuous de-risking of vol-targeted long SPY when z abnormally positive (miner stress vs bullion), 1-bar delay, long-only.
  - Selected (train-only 4-fold WF mean Sharpe 1.068): `rv_window=21, z_window=126, entry_scale=2.0, vol_target=0.15`.
  - OOS Val+Test (3435 engine trades, n=1259): Sharpe **0.939** fail, PF **1.189** fail, max DD **-2.18%** pass, trades **3435** pass, WF stability **0.879** pass, worst-regime rolling-252 **-1.106** fail, benchmark p **0.939** / IR **-0.698** fail, perturbation **0.885** pass → **4/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.750/1.153/-33.72%/1; random-exposure-matched **0.524**/1.116/-4.75%/1258 (weaker); **inverse regime** (de-risk when GDX RV abnormally LOW vs GLD / negative z, pre-registered falsifier) **0.931**/1.183/-3.24%/3610 — **near base** (no decisive directional edge; unlike H138/H139 inverse outperformance, but pre-registered direction not benchmark-validated).
  - Honest adjacency: repo-new executed GDX/GLD RV-*difference* observable/pair. Separated from H88/H99/H101/H145 (gold-miner/GLD-SPY families, different observables/constructions) and RV-divergence class H138/H139/H148 (different asset pair/channel; difference vs H138/H139 ratio). No validated edge.

## Discovery (Cycle 63, directive §4)
- Reconciled lineage to H148 (H85–H148 rejected/recorded). Pre-registered H149 (NF-20261106-01 lineage) selected/executed per NEXT_TASK Cycle 63; NF-root collision with H99 resolved transparently (exec key NF-20261108-14).
- Candidates scored (25/25/20/15/10/5): NF-20261106-01/H149 3.50 (executed); NF-20261106-03 XLU defensive relative-momentum 3.50 **deferred** (verify NF root vs executed sector artifacts; separation from H110/H147/sector rejects); NF-20261107-49 TLT-SPY realized-correlation 3.25 **held** (correlation class H96/H127/H134/H137 requires materially different design).
- Deferred/held reassessed (no silent drops): NF-04 **blocked**; NF-05/07/08/10/11/13/15/17/21 **deferred**; **NF-20 root executed H110**; NF-11r/NF-06-18 same root as NF-11 (H141); NF-06-11 **infeasible**; NF-20261106-01 lineage **executed H149 (NF-20261108-14)**; NF-20261106-03/23/24/28/30/32/33/35 **deferred (verify roots)**; NF-20261107-05 **deferred** (data blocker); NF-20261107-14/48 **held** (IV-spread H125/H126); NF-20261107-49 **held** (correlation class); NF-20261107-52 executed H148; NF-20261108-04/05/07/08/10 **deferred/held**.

## Invariants preserved
- `src/qtr` unchanged — pinned 100% coverage suite **not rerun**.
- No published/certified/frozen artifacts, thresholds, or verdicts modified. H99 artifacts preserved.
- Free/public yfinance data only. No gate weakening. No commit/push.

## Verified this session
- `python3 -m ruff check run_nf_20261108_14_gdx_gld_rv_spy.py tests/test_nf_20261108_14_gdx_gld_rv_spy.py` — clean.
- `python3 -m ruff format --check run_nf_20261108_14_gdx_gld_rv_spy.py tests/test_nf_20261108_14_gdx_gld_rv_spy.py` — clean (after formatting).
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261108_14_gdx_gld_rv_spy.py tests/test_nf_20261107_52_eem_spy_rvdiv.py` — **12 passed**.
- `PYTHONPATH=src python3 run_nf_20261108_14_gdx_gld_rv_spy.py` — **REAL** verdict **REJECT 4/8**; artifact `.experiments/nf_runs/nf_20261108_14_gdx_gld_rv_spy/summary.json` (5.71s).

## Unresolved / risks
- H149 fails Sharpe/PF/worst-regime/benchmark; inverse near base (no decisive directional edge) and benchmark not significant. Do not promote.
- RV-divergence construction class now H138 (credit/SPY RV ratio, REJECT 2/8, inverse outperformed), H139 (IWM/SPY RV ratio, REJECT 2/8, inverse outperformed), H148 (EEM/SPY RV difference, REJECT 4/8, inverse weaker), H149 (GDX/GLD RV difference, REJECT 4/8, inverse near base). Future RV-divergence candidates must demonstrate materially different mechanism/observable/pair and justify independence.
- **NF-root collisions observed (Cycle 62 NF-20/H110, Cycle 63 NF-06-01/H99):** always verify NF roots against executed H-IDs/artifacts before implementation/selection.

## Precise next task (Cycle 64, directive §4)
1. Reconcile lineage to H149 (H85–H149 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring. **Verify NF roots against executed H-IDs/artifacts before selection.** Reassess deferred/held pool with concrete evidence (no silent drops): NF-04 blocked; NF-05/07/08/10/11/13/15/17/21 deferred; NF-20 executed H110; NF-11r/NF-06-18 same root as NF-11 (H141); NF-06-11 infeasible; NF-06-01 lineage executed H149 (NF-20261108-14); NF-06-03/23/24/28/30/32/33/35 deferred (verify roots); NF-07-05 deferred; NF-07-14/48 held (IV-spread H125/H126); NF-07-49 held (correlation H96/H127/H134/H137); NF-07-52 executed H148; NF-08-04/05/07/08/10 deferred/held. Justify independence from rejected construction classes (correlation H96/H127/H134/H137; RV-divergence H138/H139/H148/H149; OPX proximity H140; TOQ/H91; IV spread H125/H126; overnight/gap direction H18/H87; overnight-gap RV H143; Amihud H121; RV term structure H136; EEM-SPY relmom H144; GLD-SPY relmom H145; IVOL dispersion H146; breadth H115/H147; FX-strength H95/H103/H106).
3. Pre-register highest-expected-information feasible candidate as **H150** with smallest decisive test, PIT timing, costs, splits, gates, ablations, and falsifiers.
4. Implement runner + focused tests, run ruff, run focused pytest, execute, record verdict/artifacts in `HYPOTHESIS_SPEC.md` and `NEW_FAMILY_RESEARCH_REGISTER.md`, update `NEXT_TASK.md`/`HANDOFF_NEXT.md`.
5. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push. If `src/qtr` touched, rerun pinned 100% coverage suite.
