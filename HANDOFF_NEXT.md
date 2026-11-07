# HANDOFF_NEXT — After Cycle 51 / H137 (2026-11-07)

## Completed this cycle
- **H137 / NF-20261107-50 — Realized SPY--GLD return-correlation regime timing SPY: REJECT (2/8).**
  - Artifact: `.experiments/nf_runs/nf_20261107_50_spy_gld_corr/summary.json` (+ `grid.csv`, `data_meta.json`)
  - Runner: `run_nf_20261107_50_spy_gld_corr.py`
  - Tests: `tests/test_nf_20261107_50_spy_gld_corr.py` (7 passed)
  - Data (free/public yfinance, PIT): SPY + GLD daily auto-adjust Close, 3776 aligned rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755).
  - Selected (train-only 4-fold WF): `corr_window=252, z_window=126, entry_scale=2, vol_target=0.10` (WF mean 0.685).
  - OOS Val+Test (1437 trades, n=1260): Sharpe **0.152** fail, PF **1.035** fail, max DD **-14.41%** pass, trades **1437** pass, WF stability **0.161** fail, worst-regime rolling-252 **-0.931** fail, benchmark p **0.977** / IR **-0.895** fail, perturbation **0.243** fail → **2/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.759/1.155; random-exposure-matched 0.174/1.065 (comparable); **inverse** 0.943/1.250/maxDD -8.50% (outperforms — pre-registered falsifier of the directional de-risking mapping; **not** a validated edge under the pre-registered hypothesis).
  - Honest adjacency: repo-new *SPY--GLD* pair/channel (safe-haven co-movement/diversification transmission), but same correlation-regime construction class as H96 (SPY-TLT), H127 (GLD-TLT), H134 (SPY-VIX) — all rejected.

## Discovery (Cycle 51, directive §4)
- Reconciled lineage to H136 (H85–H136 rejected/recorded). Proposed >=3 candidates across >=3 broad categories, scored 25/25/20/15/10/5:
  - NF-20261107-50 SPY--GLD realized correlation regime (safe-haven co-movement/diversification) — **3.95, selected/executed H137**.
  - NF-20261107-49 TLT-SPY realized correlation (rates-equity co-movement/flight-to-quality) — **3.60, held** (adj H127/H96 separation).
  - NF-20261107-51 credit-vs-equity realized-vol divergence `RV(HYG-LQD)` vs `RV(SPY)` (credit stress/vol transmission, NF-20261107-12 concept with distinct design) — **3.50, held** (explicit PIT vol-divergence separation required; sep H94/H100/H125).
  - NF-20261107-14/48 OVX−VIX (cross-asset commodity-options IV spread) — **3.35, held/not selected** (same construction class as H125/H126 — **materially different pre-registered design required**).
- Deferred/held reassessed with concrete evidence (no silent drops): NF-04 **blocked**; NF-05 deferred (turnover; H119 REJECT); NF-07/08/10/11/13/15/17/20/21 deferred; NF-11r/NF-06-18 **SAME root as NF-11**; NF-06-11 **infeasible**; NF-20261106-03/23/24/28/30/32/33/35 deferred; NF-20261107-05 CPI deferred (data blocker). Held: NF-20261107-11/12(51)/14(48)/31/49. NF-20261107-32/36/39/43/46/47/50 executed — not rerun.

## Invariants preserved
- `src/qtr` unchanged — pinned 100% coverage suite **not rerun**.
- No published/certified/frozen artifacts, thresholds, or verdicts modified.
- Free/public yfinance data only. No gate weakening. No commit/push.

## Verified this session
- `python3 -m ruff check run_nf_20261107_50_spy_gld_corr.py tests/test_nf_20261107_50_spy_gld_corr.py` — clean.
- `python3 -m ruff format --check ...` — clean.
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261107_50_spy_gld_corr.py` — **7 passed**.
- `PYTHONPATH=src python3 run_nf_20261107_50_spy_gld_corr.py` — verdict **REJECT 2/8**.

## Unresolved / risks
- Correlation-regime construction class heavily tested across pairs (H96/H127/H134/H137) — all rejected; future correlation work needs clearly distinct mechanism/design, not a new pair alone.
- H137 inverse mapping outperformed but was a *pre-registered falsifier*, not a pre-registered acceptance hypothesis — do not promote to PASS without fresh pre-registration/gates.
- Tracked draft `run_nf_20261107_48_ovx_vix_spread.py` (AR(1) body, mislabeled OVX/H137) remains in repo from prior commit; not Cycle 51 evidence.

## Precise next task (Cycle 52, directive §4)
1. Reconcile lineage to H137 (H85–H137 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring; reassess deferred/held NF-04/05/07/08/10/11/13/15/17/20/21, NF-11r/NF-06-18 (same root as NF-11), NF-06-11, NF-20261106-03/23/24/28/30/32/33/35, NF-20261107-05, NF-20261107-11/12(51)/14(48)/31/49 with concrete evidence (no silent drops).
3. Pre-register highest-expected-information feasible candidate as **H138** with smallest decisive test, PIT timing, costs, splits, gates, ablations, and falsifiers.
4. Implement runner + focused tests, run ruff, run focused pytest, execute, record verdict/artifacts in `HYPOTHESIS_SPEC.md` and `NEW_FAMILY_RESEARCH_REGISTER.md`, update `NEXT_TASK.md`/handoffs.
5. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push. If `src/qtr` touched, rerun pinned 100% coverage suite.
