# HANDOFF_NEXT_SESSION (Cycle 58)

## Completed this session (Cycle 57)
- **H143 / NF-20261108-06 — SPY timing from overnight gap realized-volatility regime (liquidity/microstructure): REJECT (4/8).**
  - Artifact: `.experiments/nf_runs/nf_20261108_06_spy_overnight_gap_rv/summary.json` (+ `grid.csv`, `data_meta.json`, 18.21s)
  - Runner: `run_nf_20261108_06_spy_overnight_gap_rv.py`; Tests: `tests/test_nf_20261108_06_spy_overnight_gap_rv.py` (**5 passed**)
  - Data (free/public yfinance, PIT): SPY daily OHLC (`auto_adjust=False`), 3776 rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755).
  - Observable: `z` of trailing `RV(log(Open/prev Close), rv_window)` over `z_window`; continuous de-risking, 1-bar delay, long-only.
  - Selected (train-only 4-fold WF mean Sharpe 0.7645): `rv_window=63, z_window=126, entry_scale=2.0, vol_target=0.10`.
  - OOS Val+Test (3403 trades, n=1260): Sharpe **0.739** fail, PF **1.154** fail, max DD **-1.54%** pass, trades **3403** pass, WF stability **1.007** pass, worst-regime rolling-252 **-1.907** fail, benchmark p **0.930** / IR **-0.661** fail, perturbation **0.932** pass → **4/8 REJECT**. Mean OOS exposure **0.0565** (near-cash).
  - Ablations OOS: buy-hold SPY 0.676/1.137/-34.10%/1 (close-based in run); random-exposure-matched **0.137**/1.030/-2.31%/3776 (much weaker — not noise); inverse regime **0.680**/1.133/-1.25%/3602 (comparable, no opposite edge).
  - Honest adjacency: repo-new *overnight gap/jump realized-vol* component. Distinct from H18/H87 (overnight/gap direction), H121 (Amihud), H136 (close-to-close RV term structure), H122/H128/H132/H135 (total-return higher moments/VoV). No validated edge.
- **Cycle 57 discovery (directive §4):** Reconciled lineage to H142 (H85–H142 rejected/recorded). Proposed/scored >=3 candidates across >=3 broad categories: NF-20261108-06 overnight gap RV (liquidity/microstructure, 3.80, **selected/executed H143**), NF-20261108-07 TIP-IEF breakeven-proxy momentum (macro term-premium/inflation-compensation, 3.35, reassessed NF-08/NF-13 root, lower expected info), NF-20261108-08 DBC-SPY commodity-complex momentum (commodity-complex, 3.10, reassessed NF-32, ETF roll/flow confounds). Reassessed held/deferred pool with concrete evidence (no silent drops): NF-04 **blocked** (no free PIT term-structure/roll proxy; DBC/ETF confounds), NF-05 deferred, NF-07/08/10/11/13/15/17/20/21 deferred, NF-11r/NF-06-18 same root as NF-11 (H141 proxy executed), NF-06-11 infeasible, NF-20261106-03/23/24/28/30/32/33/35 deferred, NF-20261107-05 deferred (data), NF-20261107-11/14(48)/31/49/52 held (materially different designs required for 14/48/49/52/04 subclass noted), NF-20261108-04 held (subclass of H140), NF-20261108-05 deferred.

## Invariants preserved
- `src/qtr` unchanged — pinned 100% coverage suite **not rerun**.
- No published/certified/frozen artifacts, thresholds, or verdicts modified.
- Free/public yfinance data only. No gate weakening. No commit/push.

## Verified this session
- `python3 -m ruff check run_nf_20261108_06_spy_overnight_gap_rv.py tests/test_nf_20261108_06_spy_overnight_gap_rv.py` — clean.
- `python3 -m ruff format --check run_nf_20261108_06_spy_overnight_gap_rv.py tests/test_nf_20261108_06_spy_overnight_gap_rv.py` — clean.
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261108_06_spy_overnight_gap_rv.py` — **5 passed**.
- `PYTHONPATH=src python3 run_nf_20261108_06_spy_overnight_gap_rv.py` — verdict **REJECT 4/8**.

## Unresolved / risks
- H143 selected config is a near-cash overlay (mean exposure 5.65%); it reduces DD but is not a benchmark-significant timing edge (p 0.930). Do not promote to PASS.
- Benchmark buy-hold in H143 uses raw Close (`auto_adjust=False`) — 0.676/-34.10% differs from adjusted-close BH in other NF runs; gates are internal/benchmark-relative within run (no cross-run gate comparison issue).
- Rejected construction classes remain: correlation (H96/H127/H134/H137), RV-divergence (H138/H139), OPX proximity (H140), TOQ/H91 calendar, IV spread (H125/H126), overnight/gap direction (H18/H87), overnight-gap RV (H143), Amihud (H121), RV term structure (H136). Held candidates require **materially different pre-registered designs**.

## Precise next task (Cycle 58, directive §4)
1. Reconcile lineage to H143 (H85–H143 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring; reassess deferred/held NF-04/05/07/08/10/11/13/15/17/20/21, NF-11r/NF-06-18 (same root), NF-06-11, NF-20261106-03/23/24/28/30/32/33/35, NF-20261107-05/11/14(48)/31/49/52, NF-20261108-04/05/07/08 with concrete evidence (no silent drops). Justify independence from rejected construction classes above.
3. Pre-register highest-expected-information feasible candidate as **H144** with smallest decisive test, PIT timing, costs, splits, gates, ablations, and falsifiers.
4. Implement runner + focused tests, run ruff, run focused pytest, execute, record verdict/artifacts in `HYPOTHESIS_SPEC.md` and `NEW_FAMILY_RESEARCH_REGISTER.md`, update `NEXT_TASK.md`/handoffs.
5. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push. If `src/qtr` touched, rerun pinned 100% coverage suite.
