# HANDOFF_NEXT_SESSION (Cycle 59)

## Completed this session (Cycle 58)
- **H144 / NF-20261108-09 — SPY timing from EEM-vs-SPY relative-momentum regime (global cross-market leadership transmission): REJECT (3/8).**
  - Artifact: `.experiments/nf_runs/nf_20261108_09_eem_spy_relmom/summary.json` (+ `grid.csv`, `data_meta.json`, 14.24s)
  - Runner: `run_nf_20261108_09_eem_spy_relmom.py`; Tests: `tests/test_nf_20261108_09_eem_spy_relmom.py` (**5 passed**)
  - Data (free/public yfinance, PIT): SPY+EEM daily auto-adjust Close, 3776 rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755).
  - Observable: z-score of trailing `(ret(EEM,mom_window)-ret(SPY,mom_window))` over `z_window`; continuous de-risking on negative z (EM leadership weak), 1-bar delay, long-only.
  - Selected (train-only 4-fold WF mean Sharpe 0.961): `mom_window=21, z_window=126, entry_scale=2.0, vol_target=0.15`.
  - OOS Val+Test (3579 trades, n=1259): Sharpe **0.537** fail, PF **1.102** fail, max DD **-3.81%** pass, trades **3579** pass, WF stability **0.559** fail, worst-regime rolling-252 **-1.627** fail, benchmark p **0.957** / IR **-0.756** fail, perturbation **0.919** pass → **3/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.750/1.153/-33.72%/1; random-exposure-matched **0.518**/1.120/-5.71%/1258 (comparable — no clear edge); **inverse regime** (pre-registered falsifier, de-risk when EM leadership strong) **0.878**/1.175/-2.29%/3584 (outperforms pre-registered mapping — **direction falsified**).
  - Honest adjacency: repo-new executed *EEM-vs-SPY relative-momentum* leadership pair. Adjacent to H85 (lead-lag, different causal form), NF-15 (EEM/EFA deferred, different pair), H139 (IWM/SPY RV-div, different observable). No validated edge.
- **Cycle 58 discovery (directive §4):** Reconciled lineage to H143 (H85–H143 rejected/recorded). Proposed/scored >=3 candidates across >=3 broad categories: NF-20261108-09 EEM-vs-SPY relative-momentum regime (global cross-market leadership/EM transmission, 3.60, **selected/executed H144**), NF-20261108-10 FXE EUR-strength momentum (FX macro transmission, 3.60 tied, deferred — FX-family adjacency H95/H103/H106 + rough sanity mixed), NF-20261108-07 TIP-IEF inflation-compensation/breakeven-proxy momentum (macro term-premium, 3.35, deferred — weak proxy/sanity). Rough sanity checks (2022–2025, arbitrary, **not holdout-selected, not for selection/gates**) recorded in register; EEM-SPY mixed/weakly promising, FXE mixed, TIP-IEF weak. Reassessed held/deferred pool with concrete evidence (no silent drops): NF-04 **blocked**; NF-05 deferred; NF-07/08/10/11/13/15/17/20/21 deferred (NF-15 adjacent to H144, different pair); NF-11r/NF-06-18 same root as NF-11/H141; NF-06-11 infeasible; NF-20261106-03/23/24/28/30/32/33/35 deferred; NF-20261107-05/11/14(48)/31/49/52 held/deferred per notes; NF-20261108-04/05/07/08/10 deferred/held.

## Invariants preserved
- `src/qtr` unchanged — pinned 100% coverage suite **not rerun**.
- No published/certified/frozen artifacts, thresholds, or verdicts modified.
- Free/public yfinance data only. No gate weakening. No commit/push.

## Verified this session
- `python3 -m ruff check run_nf_20261108_09_eem_spy_relmom.py tests/test_nf_20261108_09_eem_spy_relmom.py` — clean.
- `python3 -m ruff format --check run_nf_20261108_09_eem_spy_relmom.py tests/test_nf_20261108_09_eem_spy_relmom.py` — clean (after format).
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261108_09_eem_spy_relmom.py` — **5 passed**.
- `PYTHONPATH=src python3 run_nf_20261108_09_eem_spy_relmom.py` — verdict **REJECT 3/8** (real run).

## Approaches / evidence (do not blindly repeat)
- **H144 falsified by ablations**: random-exposure matched (0.518 vs 0.537) showed no clear edge; **inverse regime outperformed** (0.878 vs 0.537, PF 1.175) — do not rerun same EEM-vs-SPY de-risk-on-weak-EM mapping. Inverse result is an ablation, not a pre-registered PASS; any opposite-direction hypothesis would require fresh pre-registration, a materially clear mechanism, and independence justification.
- Rejected construction classes remain: correlation (H96/H127/H134/H137), RV-divergence (H138/H139), OPX proximity (H140), TOQ/H91 calendar, IV spread (H125/H126), overnight/gap direction (H18/H87), overnight-gap RV (H143), Amihud (H121), RV term structure (H136), EEM-SPY relative-momentum (H144). FX-strength z-score family adjacency H95/H103/H106. Held candidates require **materially different pre-registered designs**.
- NF-04 blocked (no free PIT term-structure/roll proxy). NF-11r is NF-11 resolution path (SAME root), not repo-new. NF-06-11 CBOE PC ratio infeasible.

## Precise next task (Cycle 59, directive §4)
1. Reconcile lineage to H144 (H85–H144 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring; reassess deferred/held pool with concrete evidence (no silent drops). Justify independence from rejected construction classes above (including FX-strength z-score adjacency and EEM-SPY relmom H144).
3. Pre-register highest-expected-information feasible candidate as **H145** with smallest decisive test, PIT timing, costs, splits, gates, ablations, and falsifiers.
4. Implement runner + focused tests, run ruff, run focused pytest, execute, record verdict/artifacts in `HYPOTHESIS_SPEC.md` and `NEW_FAMILY_RESEARCH_REGISTER.md`, update `NEXT_TASK.md`/handoffs.
5. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push. If `src/qtr` touched, rerun pinned 100% coverage suite.
