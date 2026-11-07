# HANDOFF_NEXT — After Cycle 44 / H130 (2026-11-07)

## Completed this cycle
- **H130 / NF-20261107-30 — Cross-sectional average sector IVOL regime timing SPY: REJECT (3/8).**
  - Artifact: `.experiments/nf_runs/nf_20261107_30_avg_ivol_regime/summary.json` (+ `grid.csv`, `data_meta.json`)
  - Runner: `run_nf_20261107_30_avg_ivol_regime.py`
  - Tests: `tests/test_nf_20261107_30_avg_ivol_regime.py` (8 passed)
  - Data (free/public yfinance): SPY + XLB/XLE/XLF/XLI/XLK/XLP/XLU/XLV/XLY, 3776 aligned rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755). XLC/XLRE excluded for 2010+ history (feasibility, as H117/H129).
  - Selected (train-only WF): `beta_window=21, z_window=126, entry_scale=2, vol_target=0.10`.
  - OOS Val+Test (1549 trades): Sharpe **0.809** fail, PF **1.163** fail, max DD **-15.40%** fail (≤15%), trades **1549** pass, WF stability **1.0** pass, worst-regime rolling-252 **-1.715** fail, benchmark p **0.770** / IR **-0.331** fail, perturbation **0.737** pass → **3/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.760/1.155; random-exposure-matched 0.796/1.174 (comparable; benchmark fails); inverse IVOL-regime 0.160/1.102. No validated edge.
  - Honest adjacency: repo-new *aggregate mean sector IVOL regime* z-score overlay (continuous de-risking, different construction/objective/trade structure from H93's cross-sectional IVOL-level ranking REJECT 2/9), but same IVOL concept and sector-stat/dispersion class adjacency acknowledged.

## Discovery (Cycle 44, directive §4)
- Reconciled lineage to H129 (H85–H129 rejected/recorded). Proposed >=3 candidates across >=3 broad categories, scored 25/25/20/15/10/5:
  - NF-20261107-30 avg sector IVOL regime timing SPY (idiosyncratic-risk/dispersion) — **3.60, selected/executed H130**.
  - NF-20261107-31 sector breadth %>200d MA timing SPY (market structure/participation) — **3.25, held** (adj H115 RSP/SPY REJECT 1/8; needs materially different observable/construction).
  - NF-20261107-32 cross-sectional return-dispersion regime timing SPY (dispersion) — **3.25, held**.
  - NF-20261107-33 credit-quality relative momentum HYG vs LQD (credit risk-appetite) — 3.40 scored but **not selected**: repo contains prior `run_nf_20261107_16_credit_relmom.py`/artifact (OOS Sharpe 0.767, trades 121, DD -17.97%, underperformed buy-hold/random ablation evidence in runner header context) and adjacent to H94/H108; not repo-new root / not materially different decisive test.
- Deferred/held reassessed with concrete evidence (no silent drops): NF-04 carry **blocked** (no free PIT term-structure/roll proxy); NF-05 CS reversal deferred (turnover; H119 REJECT 3/8); NF-07/08/10/11/13/15/17 deferred (weak/adj/proxy); NF-11r/NF-06-18 **same root as NF-11** (data feasible, not new root); NF-20 auction deferred (calendar/timestamp); NF-21 month-end deferred (weak/adj H91); NF-06-11 PC ratio **infeasible**; NF-20261106-03/23/24/28/30/32/33/35 deferred (adj/confounds); NF-20261107-05 CPI drift deferred (adj H90). Held: NF-20261107-11 (IVOL spread, sep from H93; larger scope), NF-20261107-12 (credit-vs-equity vol divergence, sep from H94/H100/H125), NF-20261107-14 (OVX−VIX, same class as H125/H126 — materially different design required), NF-20261107-31/32. NF-20261107-16/33 HYG-LQD not selected (adjacent/previously-artifacted). NF-20261107-29/H130 executed/rejected — not rerun.

## Invariants preserved
- `src/qtr` unchanged (no evidenced defect) — pinned 100% coverage suite **not rerun** (expensive; rerun if `src/qtr`/core touched).
- No published/certified/frozen artifacts, thresholds, or verdicts modified.
- Free/public yfinance data only. No gate weakening. No commit/push.

## Verified this session
- `python -m ruff check run_nf_20261107_30_avg_ivol_regime.py tests/test_nf_20261107_30_avg_ivol_regime.py` — clean.
- `python -m ruff format --check ...` — clean.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261107_30_avg_ivol_regime.py` — **8 passed**.
- `PYTHONPATH=src python run_nf_20261107_30_avg_ivol_regime.py` — executed; verdict **REJECT 3/8**; summary/grid/data_meta written.

## Unresolved / risks
- H93/H130 IVOL-related constructions both rejected (ranking vs aggregate overlay); any future IVOL work requires a clearly distinct mechanism/design and explicit separation.
- NF-20261107-11/12 remain feasible but need explicit PIT/separation pre-registration (larger scope); NF-20261107-14 requires materially different design vs H125/H126.
- NF-20261107-16 credit-relmom runner/artifact exists in repo history/HEAD context (REJECT-like evidence) — not newly executed this cycle; do not treat as a new root or rerun without materially different design.
- Coverage gate for `src/qtr` remains pinned but was not rerun (no `src/qtr` change).

## Precise next task (Cycle 45, directive §4)
1. Reconcile lineage to H130 (H85–H130 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring; reassess deferred/held NF-04/05/07/08/10/11/13/15/17/20/21, NF-11r/NF-06-18 (same root as NF-11), NF-06-11, NF-20261106-03/23/24/28/30/32/33/35, NF-20261107-05, NF-20261107-11/12/14/31/32 with concrete evidence (no silent drops). Do not rerun NF-20261107-29/H129 or NF-20261107-30/H130. Avoid adjacent H93/H130 IVOL constructions without clearly distinct mechanism/design.
3. Pre-register highest-expected-information feasible candidate as **H131** (next unused H-ID; do not recycle H24/H68–H73/H76–H79) with smallest decisive test, PIT timing, costs, splits, gates, ablations, and falsifiers.
4. Implement runner + focused tests, run ruff, run focused pytest, execute, record verdict/artifacts in `HYPOTHESIS_SPEC.md` and `NEW_FAMILY_RESEARCH_REGISTER.md`, update `NEXT_TASK.md`/handoffs.
5. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push. If `src/qtr` touched, rerun pinned 100% coverage suite.
