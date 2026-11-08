# HANDOFF_NEXT_SESSION (Cycle 60)

## Completed this session (Cycle 59)
- **H145 / NF-20261108-11 — SPY timing from GLD-vs-SPY relative-momentum regime (safe-haven / real-asset vs equity risk-premium transmission): REJECT (4/8).**
  - Artifact: `.experiments/nf_runs/nf_20261108_11_gld_spy_relmom/summary.json` (+ `grid.csv`, `data_meta.json`, 14.69s)
  - Runner: `run_nf_20261108_11_gld_spy_relmom.py`; Tests: `tests/test_nf_20261108_11_gld_spy_relmom.py` (5 tests)
  - Data (free/public yfinance, PIT): SPY+GLD daily auto-adjust Close, 3776 rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755).
  - Observable: z-score of trailing `(ret(GLD,mom_window)-ret(SPY,mom_window))` over `z_window`; continuous de-risking on positive z (gold flight-to-safety leadership), 1-bar delay, long-only.
  - Selected (train-only 4-fold WF mean Sharpe 0.800): `mom_window=63, z_window=126, entry_scale=2.0, vol_target=0.15`.
  - OOS Val+Test (3455 trades, n=1259): Sharpe **0.761** fail, PF **1.153** fail, max DD **-3.59%** pass, trades **3455** pass, WF stability **0.951** pass, worst-regime rolling-252 **-1.307** fail, benchmark p **0.948** / IR **-0.720** fail, perturbation **0.914** pass → **4/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.750/1.153/-33.72%/1; random-exposure-matched **0.518**/1.120/-5.89%/1258 (weaker than strategy but no benchmark edge); **inverse regime** (pre-registered falsifier, de-risk when GLD underperforms/negative z) **0.909**/1.177/-2.66%/3515 (stronger than pre-registered mapping — **direction not supported**).
  - Honest adjacency: repo-new executed *GLD-vs-SPY relative-momentum* SPY-timing pair. Adjacent to GLD usage in H88 (GLD/USO spread RV, REJECT 1/9; different pair/objective), H99 (GDX timed by GDX/GLD, REJECT 4/9), H101 (GLD timed by GLD/XLE RV, REJECT 3/9), H144 (EEM-SPY relmom, REJECT 3/8; different signal asset), and z-score relmom de-risking construction class. No validated edge.
  - **Integrity note (recorded):** untracked runner/test had copy/sign/output-path issues; repaired to pre-registered safe-haven positive-z mapping before execution; stale wrong-output artifact removed. Artifact is corrected REAL run.
- **Cycle 59 discovery (directive §4):** Reconciled lineage to H144 (H85–H144 rejected/recorded). Proposed/scored >=3 candidates across >=3 broad categories: NF-20261108-11 GLD-vs-SPY relative-momentum (safe-haven/real-asset vs equity risk-premium, 3.60, **selected/executed H145**), NF-20261108-10 FXE EUR-strength momentum (FX macro transmission, 3.60 tied, deferred — FX-family adjacency H95/H103/H106), NF-20261108-07 TIP-IEF inflation-compensation/breakeven-proxy momentum (macro term-premium, 3.35, deferred). Independence justified from rejected construction classes (correlation H96/H127/H134/H137; RV-divergence H138/H139; OPX proximity H140; TOQ/H91 calendar; IV spread H125/H126; overnight/gap direction H18/H87; overnight-gap RV H143; Amihud H121; RV term structure H136; EEM-SPY relative-momentum H144; FX-strength z-score adjacency H95/H103/H106). Held/deferred pool reassessed with concrete evidence (no silent drops): NF-04 **blocked**; NF-05/07/08/10/11/13/15/17/20/21 deferred; NF-11r/NF-06-18 same root as NF-11/H141; NF-06-11 infeasible; NF-20261106-03/23/24/28/30/32/33/35 deferred; NF-20261107-05/11/14(48)/31/49/52 deferred/held per notes; NF-20261108-04/05/07/08/10 deferred/held.

## Invariants preserved
- `src/qtr` unchanged — pinned 100% coverage suite **not rerun**.
- No published/certified/frozen artifacts, thresholds, or verdicts modified.
- Free/public yfinance data only. No gate weakening. No commit/push.

## Verified this session
- `python3 -m py_compile run_nf_20261108_11_gld_spy_relmom.py tests/test_nf_20261108_11_gld_spy_relmom.py` — **clean**.
- `git ls-files` confirms H145 runner/test/docs tracked; artifact dir `.experiments/nf_runs/nf_20261108_11_gld_spy_relmom/` present with `summary.json`/`grid.csv`/`data_meta.json` (REJECT 4/8).
- `HYPOTHESIS_SPEC.md` §H145 and `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 59 record present (artifact-integrity note included).
- **Not verified in this session:** `ruff check/format` and focused `pytest` for H145 files — `ruff`/`pytest` unavailable in environment (`ruff: command not found`, `No module named pytest`). H145 record states focused tests/ruff passed when executed by prior agent; rerun in an environment with repo test deps.

## Approaches / evidence (do not blindly repeat)
- **H145 falsified directionally**: random-exposure weaker (0.518 vs 0.761) but no benchmark edge; **inverse regime outperformed** (0.909 vs 0.761) — do not rerun same GLD-vs-SPY de-risk-on-gold-leadership mapping. Inverse result is an ablation, not a pre-registered PASS; any opposite-direction hypothesis requires fresh pre-registration and independence justification.
- Rejected construction classes remain: correlation (H96/H127/H134/H137), RV-divergence (H138/H139), OPX proximity (H140), TOQ/H91 calendar, IV spread (H125/H126), overnight/gap direction (H18/H87), overnight-gap RV (H143), Amihud (H121), RV term structure (H136), EEM-SPY relative-momentum (H144), **GLD-SPY relative-momentum (H145)**. FX-strength z-score family adjacency H95/H103/H106. Held candidates require **materially different pre-registered designs**.
- NF-04 blocked (no free PIT term-structure/roll proxy). NF-11r is NF-11 resolution path (SAME root), not repo-new. NF-06-11 CBOE PC ratio infeasible.

## Precise next task (Cycle 60, directive §4)
1. Reconcile lineage to H145 (H85–H145 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring; reassess deferred/held pool with concrete evidence (no silent drops). Justify independence from rejected construction classes above (including FX-strength z-score adjacency and EEM/GLD-SPY relmom H144/H145).
3. Pre-register highest-expected-information feasible candidate as **H146** with smallest decisive test, PIT timing, costs, splits, gates, ablations, and falsifiers.
4. Implement runner + focused tests, run ruff, run focused pytest, execute, record verdict/artifacts in `HYPOTHESIS_SPEC.md` and `NEW_FAMILY_RESEARCH_REGISTER.md`, update `NEXT_TASK.md`/handoffs.
5. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push. If `src/qtr` touched, rerun pinned 100% coverage suite.
