# HANDOFF_NEXT.md — Cycle 94 (after H179 REJECT 2/8)

## Session summary
- **Cycle 93 implementation/execution complete.** H179 (NF-20261110-06, Short Interest / Securities Lending Flow Timing) was pre-registered in prior discovery; this session implemented runner/tests, fixed defects, and executed REAL.
- **Defects fixed (evidenced):** `tests/test_nf_20261110_06_short_interest.py` referenced `_align_short_interest_to_daily` and passed dict to `_align_si_to_daily` (mismatch) and used wrong `run_backtest` API assumptions — corrected to match runner; `run_nf_20261110_06_short_interest.py` needed `csv.field_size_limit(sys.maxsize)` for large FINRA CSVs and `ruff format` — fixed.
- **Verification:** `py_compile` ok; `ruff check/format --check` clean on H179 runner/tests; `PYTHONPATH=src pytest -q tests/test_nf_20261110_06_short_interest.py` **8 passed** (1 third-party DeprecationWarning).
- **H179 REAL result — REJECT 2/8.** Artifact `.experiments/nf_runs/nf_20261110_06_short_interest_20261110_cycle93/summary.json` (+`grid.csv`, `finra_cache/`, 107.0s). Data: real FINRA exchange-listed bi-weekly short interest (145 settlement dates, PIT publication lag) + yfinance SPY/sector ETFs, 2018-02-07→2026-10-30 (2195 aligned rows). Train→2022-06-16, Val→2024-08-23, Test protected→2026-10-30 (OOS 1098). Grid 72; selected (train-only WF 1.099, train 0.170): `si_window=24, entry_z=1.5, exit_z=0.0, vol_target=0.15, universe=SPY_SECTORS`.
- **OOS Val+Test:** Sharpe **−0.449** fail, PF **0.920** fail, maxDD **−16.95%** fail, trades **3437** pass, WF stability **−2.647** fail, worst-regime rolling-252 **−1.970** fail, benchmark p **0.996** / IR **−1.202** vs buy-hold SPY 1.195/+50.07% fail, perturbation min ratio **1.869** pass. Return −13.93%. Ablations: random-SI 0.124, inverse-signal 0.382 (both outperformed selected). Severe train→OOS collapse.
- **Docs updated:** `HYPOTHESIS_SPEC.md` §H179, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 93, `NEXT_TASK.md`, `HANDOFF_NEXT.md`, `HANDOFF_CURRENT_SESSION.md`.
- **Integrity:** `src/qtr` unchanged; no gate/threshold/grid/construction weakening; no published/certified artifact modified; no commit/push.

## Lineage state
- H85–H179 all rejected/recorded. Next unused H-ID **H180** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged.

## Deferred pool (no silent drops; reassess with concrete evidence)
| Candidate | Score | Category | Status | Evidence / blocker |
|---|---:|---|---|---|
| NF-20261110-07 Russell 2000 annual reconstitution flow | 4.05 | Structural flow / discrete index event | Deferred | Annual frequency → low statistical power; event alignment complexity |
| NF-20261109-16 Dividend capture / ex-dividend microstructure premium | 4.05 | Corporate action / microstructure | Deferred | Overnight/open slippage risk decisive on free data; mixed literature post-costs |
| NF-20261110-08 Insider transaction signal (Form 4/13F) | 3.80 | Institutional flow / informed trading | Deferred | PIT construction/parsing complexity on free data |
| NF-20261109-18 S&P 500 inclusion/deletion discrete event flow | 3.70 | Structural flow / discrete event | Deferred | External calendar dependency; low frequency |
| NF-20261109-19 Options dealer gamma exposure (GEX) | 3.10 | Market structure / dealer positioning | Deferred | No free historical options chain/GEX |
| NF-20261109-02 Earnings estimate revision momentum | 3.65 | Fundamental / analyst revision | Deferred | No free PIT revision history |
| NF-20261109-22 RSP-SPY breadth-participation relmom | 3.75 | Cross-asset participation / factor momentum | Deferred | Adjacency to H97 + exhausted relmom families |
| NF-20261109-23 USMV-SPY low-vol factor relmom | 3.55 | Factor anomaly / style momentum | Deferred | USMV inception/style adjacency |
| NF-20261109-12 Holiday / pre-holiday drift SPY timing | 4.00 | Calendar microstructure | HELD | Calendar adjacency to H91/H140/H142/H168 |
| NF-20261110-04 10Y-3M yield-curve inversion depth de-risking | 3.80 | Macro term-premium / recession-risk transmission | Deferred | Honest adjacency to H171/H11r yield-slope/level families |
| NF-20261110-05 SPY realized upside/downside jump asymmetry | 3.80 | Higher-moment / jump-risk asymmetry | Deferred | Adjacency to H122/H128/H135; low plausibility/support |
| NF-04 Commodity carry | — | Carry / term structure | **BLOCKED** | No free PIT term-structure/roll proxy |
| NF-05 Short-term CS reversal | — | Liquidity provision | **DEFERRED** | Turnover/net-of-cost; H119 weekly REJECT 3/8 |
| NF-08-16 Halloween seasonal | 3.90 | Calendar seasonal | **HELD** | Calendar adjacency H91/H140/H142 |
| NF-09-03 Breakeven-inflation | 3.40 | Macro regime | **DEFERRED/DATA-LIMITED** | ^T5YIE/^T10YIE unavailable; H175 proxy |
| NF-20261109-20 Stock split announcement effects | — | Corporate action / microstructure | DEFERRED | Low frequency; incomplete split data |

## Required next work (Cycle 94 / H180)
1. Reconcile lineage to H179; complete directive §4 discovery (≥3 repo-new/decisive candidates across ≥3 broad mechanism categories, honest 25/25/20/15/10/5, concrete deferred reassessment, NF-root checks, no silent drops).
2. Pre-register highest-expected-information feasible candidate as **H180** before validation outcomes.
3. Implement runner + focused tests; `ruff check/format --check`; `PYTHONPATH=src pytest -q` focused tests; execute REAL; record verdict/artifacts in `HYPOTHESIS_SPEC.md` §H180, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 94, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. Do not fabricate results.

## Integrity constraints
- No gate weakening; no published/certified artifact modification; no fabrication; free/public data only.
- `src/qtr` unchanged unless evidenced defect (then rerun pinned 100% suite).
- No commit/push unless explicitly authorized.
- Selection/validation uses no protected-test feedback. Gates fail-closed on pre-registered OOS Val+Test.

## Approaches that failed / evidence (do not blindly repeat)
- **H179:** FINRA bi-weekly short-interest z-score timing (SPY+sector ETFs) REJECT 2/8 (Sharpe −0.449, PF 0.920, maxDD −16.95%, WF −2.647, worst-regime −1.970, bench p 0.996/IR −1.202). **Inverse-signal 0.382 and random-SI 0.124 outperformed selected mapping**; severe train→OOS collapse. Do not rerun same z-score/hysteresis short-interest construction without materially different observable/mechanism.
- **H178:** CBOE equity P/C z-score REJECT 4/8; random-signal ablation outperformed (0.835).
- **H177:** Treasury auction supply-pressure REJECT 5/8 (Sharpe 0.720, worst-regime −1.133); synthetic auction data limitation.
- **H176:** Tax-loss harvesting REJECT 3/8 (trades 8, WF/worst-regime/bench fail).
- **H175:** Macro regime timing REJECT 7/8; inverse-regime falsifier outperformed.
- **H174:** ETF premium/discount invalid without point-in-time NAV.
- **H173:** Fed model / ERP timing REJECT 7/8; inverse-signal outperformed.
- All H85–H179 rejected on free, point-in-time data. Avoid silent recycling of exhausted construction classes without a *materially different* mechanism/observable and explicit novelty justification.
