# HANDOFF_NEXT_SESSION (Cycle 61)

## Completed this session (Cycle 60)
- **H146 / NF-20261107-11 — SPY timing from cross-sectional IVOL dispersion regime (cross-sectional volatility decomposition / higher-moment dispersion): REJECT (4/8).**
  - Artifact: `.experiments/nf_runs/nf_20261107_11_ivol_spread_spy/summary.json` (+ `grid.csv`, `data_meta.json`, 7.88s)
  - Runner: `run_nf_20261107_11_ivol_spread_spy.py`; Tests: `tests/test_nf_20261107_11_ivol_spread_spy.py` (7 passed)
  - Data (free/public yfinance, PIT): SPY + QQQ,IWM,EFA,EEM,XLF,XLE,XLV,XLI,XLK daily auto-adjust Close, 3776 rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755).
  - Signal: z-score of rolling cross-sectional std of per-asset IVOL (OLS residual vol vs SPY over `ivol_lookback`) over `z_window`; continuous de-risking of vol-targeted long SPY when dispersion z abnormally high (idiosyncratic disagreement/stress), 1-bar delay, long-only.
  - Selected (train-only 4-fold WF mean Sharpe 0.827): `ivol_lookback=126, z_window=252, entry_scale=2.0, vol_target=0.15`.
  - OOS Val+Test (3205 engine trades, n=1259): Sharpe **0.962** fail, PF **1.198** fail, max DD **-2.60%** pass, trades **3205** pass, WF stability **1.164** pass, worst-regime rolling-252 **-1.423** fail, benchmark p **0.941** / IR **-0.695** fail, perturbation **0.952** pass → **4/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.750/1.153/-33.72%/1; random-exposure-matched **0.518**/1.120/-6.07%/1258; **inverse regime** (de-risk when dispersion LOW) **0.573**/1.119/-2.66%/3417 (weaker than base — direction supported, but no benchmark edge).
  - Honest adjacency: repo-new executed *cross-sectional IVOL-dispersion* SPY-timing observable. Adjacent to H93 (single-IVOL level), H122 (downside semivar level), H125/H126 (implied-IV spread level), H144/H145 (z-score de-risking class). No validated edge.
- **Cycle 60 discovery (directive §4):** Reconciled lineage to H145 (H85–H145 rejected/recorded). Proposed/scored >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring: NF-20261107-11 cross-sectional IVOL dispersion (3.60, **selected/executed as H146**), RV trend/momentum equity timing (3.40, deferred — adjacency to vol-level timing H122/H29/H30), cross-sectional idiosyncratic-skew spread timing (3.00, deferred — execution complexity/weak skew evidence). Reassessed held/deferred pool with concrete evidence (no silent drops); NF-20261107-11 removed from held (now executed H146).
- **HYPOTHESIS_SPEC.md** §H146 (pre-registration + outcome + lineage map) appended. **NEW_FAMILY_RESEARCH_REGISTER.md** Cycle 60 entry appended. **NEXT_TASK.md** and this handoff updated for Cycle 61.

## Invariants preserved
- `src/qtr` unchanged — pinned 100% coverage suite **not rerun**.
- No published/certified/frozen artifacts, thresholds, or verdicts modified.
- Free/public yfinance data only. No gate weakening. No commit/push.

## Verified this session
- `python3 -m py_compile run_nf_20261107_11_ivol_spread_spy.py tests/test_nf_20261107_11_ivol_spread_spy.py` — clean (runner imports qtr.engine at runtime).
- `ruff check` on new files — **All checks passed**. `ruff format --check` — **clean** (after `ruff format`).
- `PYTHONPATH=src pytest -q tests/test_nf_20261107_11_ivol_spread_spy.py` — **7 passed**.
- `python3 run_nf_20261107_11_ivol_spread_spy.py` — completed; artifact written. Verdict **REJECT 4/8** (REAL run, not fabricated).
- **Not rerun:** full pinned `src/qtr` suite (no `src/qtr` change); ruff/format over `src tests run_*.py` globally (only new files checked).

## Approaches / evidence (do not blindly repeat)
- H146 direction supported (inverse 0.573 < base 0.962) but fails benchmark/risk gates (p=0.941, IR=-0.695, worst-regime -1.423). Reject stands; no validated edge.
- Rejected construction classes remain: correlation H96/H127/H134/H137; RV-divergence H138/H139; OPX proximity H140; TOQ/H91 calendar; IV spread H125/H126; overnight/gap direction H18/H87; overnight-gap RV H143; Amihud H121; RV term structure H136; EEM-SPY relative-momentum H144; GLD-SPY relative-momentum H145; **cross-sectional IVOL dispersion H146**; FX-strength z-score adjacency H95/H103/H106.
- Held candidates require materially different pre-registered designs vs rejected classes. Deferred candidates (RV trend/momentum, idiosyncratic-skew spread) need honest novelty separation.

## Precise next task (Cycle 61, directive §4)
1. Reconcile lineage to H146 (H85–H146 rejected/recorded). Next unused H-ID: **H147** (H24/H68–H73/H76–H79 unassigned, not recycled).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring; reassess deferred/held pool with concrete evidence (no silent drops). Justify independence from rejected construction classes above.
3. Select highest expected-information feasible candidate; **pre-register** as **H147** in `HYPOTHESIS_SPEC.md` before validation outcomes; record Cycle 61 discovery in `NEW_FAMILY_RESEARCH_REGISTER.md`.
4. Add `run_nf_*.py` + focused `tests/test_nf_*.py`. Free/public data only (yfinance ok). `src/qtr` unchanged. No paid data/compute, no live trading. **Pandas 3.x safety:** do not use `if <DataFrame>:` / `if trade_dates:` truthiness on DataFrames.
5. Run `ruff check/format`, focused `pytest`, execute runner; record verdict + artifact path in docs. **Do not fabricate results.** Do not weaken gates; do not modify published/certified artifacts/thresholds/frozen numbers.
6. If `src/qtr` is touched, rerun: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python3 -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.
