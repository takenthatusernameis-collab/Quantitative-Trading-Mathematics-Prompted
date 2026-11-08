# HANDOFF_NEXT — After Cycle 54 / H140 (2026-11-08)

## Completed this cycle
- **H140 / NF-20261108-01 — SPY timing from monthly options-expiration dealer-flow / pin-proximity regime: REJECT (4/8).**
  - Artifact: `.experiments/nf_runs/nf_20261108_01_spy_opx_flow/summary.json` (+ `grid.csv`, `data_meta.json`, 16.25s)
  - Runner: `run_nf_20261108_01_spy_opx_flow.py`
  - Tests: `tests/test_nf_20261108_01_spy_opx_flow.py` (8 passed)
  - Data (free/public yfinance, PIT): SPY daily auto-adjust Close, 3776 aligned rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755). OPX dates = third Friday of each month, computed deterministically — no external market data for the signal.
  - Selected (train-only 4-fold WF mean Sharpe 1.003): `z_window=126, entry_scale=2.0, vol_target=0.10`.
  - OOS Val+Test (1029 trades, n=1260): Sharpe **0.888** fail, PF **1.196** fail, max DD **-13.45%** pass, trades **1029** pass, WF stability **0.887** pass, worst-regime rolling-252 **-0.727** fail, benchmark p **0.914** / IR **-0.611** fail, perturbation **0.970** pass → **4/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.759/1.155/-33.72%/1; random-exposure-matched **0.325**/1.098/-27.23%/560 (weaker — signal not pure noise); **inverse OPX-flow** **0.158**/1.035/-7.86%/1029 (no opposite edge — unlike H138/H139 inverse falsifiers).
  - Repo-new options-flow / supply-constraints mechanism category (no executed NF/H uses monthly OPX proximity). Honest adjacency to H138/H139 z-score de-risking construction class acknowledged; no validated edge under pre-registered design.
  - `src/qtr` unchanged; no published/certified artifact, verdict, threshold, or frozen number modified; `ruff check/format` clean. No commit/push.

## Discovery (Cycle 54, directive §4)
- Lineage reconciled to H139: H85–H140 all rejected/recorded. Next unused H-ID after H140 (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged.
- Candidates scored 25/25/20/15/10/5:
  - NF-20261108-01 SPY OPX flow/pin-proximity regime (options flow / supply constraints) — **3.70, selected/executed H140** (genuinely new mechanism category; deterministic free data; honest adjacency to H138/H139 form).
  - NF-20261107-49 TLT-SPY realized correlation (held) — **3.60** (adj correlation class H96/H127/H134/H137 all REJECT — materially different design required).
  - NF-20261107-52 EEM-SPY RV divergence (held) — **3.50** (adj rejected H138/H139 RV-divergence class).
- Held/deferred reassessed with concrete evidence (no silent drops): NF-04 **blocked**; NF-05 **deferred**; NF-07/08/10/11/13/15/17/20/21 **deferred**; NF-11r/NF-06-18 same root as NF-11; NF-06-11 **infeasible**; NF-20261106-03/23/24/28/30/32/33/35 **deferred**; NF-20261107-05 CPI **deferred** (data blocker). Held: NF-20261107-11 IVOL spread, NF-20261107-14/48 OVX−VIX, NF-20261107-31 sector breadth, NF-20261107-49 TLT-SPY corr, NF-20261107-52 EEM-SPY RV divergence. Executed not rerun: H138/H139/H140 and NF-20261107-32/36/39/43/46/47/50.

## Invariants preserved
- `src/qtr` unchanged — pinned 100% coverage suite **not rerun**.
- No published/certified/frozen artifacts, thresholds, or verdicts modified.
- Free/public yfinance data only. No gate weakening. No commit/push.

## Verified this session
- `python3 -m ruff check run_nf_20261108_01_spy_opx_flow.py tests/test_nf_20261108_01_spy_opx_flow.py` — clean.
- `python3 -m ruff format --check ...` — clean.
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261108_01_spy_opx_flow.py` — **8 passed**.
- H140 artifact verified REAL: `.experiments/nf_runs/nf_20261108_01_spy_opx_flow/summary.json` = **REJECT 4/8** (Sharpe 0.888 / PF 1.196 / maxDD -13.45% / trades 1029 / WF 0.887 / worst-regime -0.727 / benchmark p 0.914 / IR -0.611 / perturbation 0.970).

## Unresolved / risks
- H140 inverse regime (0.158) shows no opposite edge — unlike H138/H139, the de-risking mapping is not directionally falsified, just unprofitable/insignificant vs benchmark. Random exposure (0.325) is weaker, so the signal is not pure noise, but fails benchmark significance and worst-regime.
- Correlation class (H96/H127/H134/H137) and RV-divergence class (H138/H139) heavily rejected; held NF-49/NF-52 need clearly distinct designs to avoid redundant construction-class testing.
- All H85–H140 rejected: no validated edge found across ~56 hypotheses; continuation requires genuinely new mechanism categories, not pair/parameter variants.

## Precise next task (Cycle 55, directive §4)
1. Reconcile lineage to H140 (H85–H140 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring; reassess held NF-20261107-49/52/11/14(48)/31 and deferred pool with concrete evidence (no silent drops).
3. Pre-register highest expected-information feasible candidate as **next H-ID after H140** in `HYPOTHESIS_SPEC.md` before validation outcomes; record Cycle 55 discovery in `NEW_FAMILY_RESEARCH_REGISTER.md`.
4. Implement runner + focused tests, run ruff, run focused pytest, execute, record verdict/artifacts; update `NEXT_TASK.md`/handoffs.
5. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push. If `src/qtr` touched, rerun pinned 100% coverage suite.
