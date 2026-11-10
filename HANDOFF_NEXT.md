# HANDOFF_NEXT.md — Cycle 96 (after H181 REJECT 4/8)

## Session summary (Cycle 95)
- **Directive §4 discovery completed (pre-execution).** Lineage reconciled to H180 (H85–H180 rejected; next H181). Scored ≥3 repo-new/decisive candidates across ≥3 mechanism categories: NF-20261104-03 ES-SPY cash-futures basis mean-reversion timing (relative value / cash-futures basis convergence/index arbitrage, **4.05, selected** — smallest decisive feasible daily test), NF-20261110-07 Russell 2000 annual reconstitution flow (structural flow/discrete index event, 4.05, deferred: annual low power/event alignment; poor expected information), NF-20261110-08 insider Form 4/13F flow (institutional flow/informed trading, 3.80, deferred: PIT parsing/aggregation complexity). Deferred pool reassessed with concrete evidence (no silent drops). NF-root check: NF-20261104-03 previously proposed but never executed (repo-new execution); draft `run_nf_20261110_07_es_basis.py` (NF-20261110-09/TBD, incomplete/unexecuted) not executed.
- **H181 implemented/executed REAL (NF-20261104-03).** `run_nf_20261104_03_es_spy_basis.py` + `tests/test_nf_20261104_03_es_spy_basis.py` (**8 passed**, 1 third-party DeprecationWarning). `py_compile` ok; `ruff check/format --check` clean. Artifact `.experiments/nf_runs/nf_20261104_03_es_spy_basis_20261110_cycle95/summary.json` (+`grid.csv`, ~10.3s).
- **Data (real, PIT):** yfinance daily auto-adjusted closes ES=F + SPY, 2010-01-04→2026-10-30 (4231 rows). Train→2018-12-31, Val→2022-12-31, Test protected→2026-10-30 (OOS 1969). Grid 36; selected (train-only WF 0.234, train 0.246): `basis_window=21, entry_z=2.0, exit_z=0.0, vol_target=0.10`.
- **Result — REJECT 4/8.** OOS Sharpe **0.297** fail, PF **1.162** fail, maxDD **−6.16%** pass, trades **99** pass, WF stability **1.208** pass, worst-regime rolling-252 **−1.410** fail, benchmark p **0.992** / IR **−0.877** vs buy-hold SPY 0.911/+90.75% fail, perturbation min ratio **0.552** pass. Return +6.89%. Ablations: random-signal 0.032/PF 1.014, inverse-signal −0.017/PF 0.995.
- **Docs updated:** `HYPOTHESIS_SPEC.md` §H181, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 95, `NEXT_TASK.md`, `HANDOFF_NEXT.md`, `HANDOFF_CURRENT_SESSION.md`.
- **Integrity:** `src/qtr` unchanged; no gate weakening; no published/certified artifact modified; no commit/push.

## Lineage state
- H85–H181 all rejected/recorded. Next unused H-ID **H182** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged.

## Deferred pool (no silent drops; reassess with concrete evidence)
| Candidate | Score | Category | Status | Evidence / blocker |
|---|---:|---|---|---|
| NF-20261110-07 Russell 2000 annual reconstitution flow | 4.05 | Structural flow / discrete index event | Deferred | Annual frequency → low OOS power; event/calendar alignment complexity |
| NF-20261110-08 Insider transaction signal (Form 4/13F) | 3.80 | Institutional flow / informed trading | Deferred | PIT parsing/aggregation complexity on free data |
| NF-20261109-18 S&P 500 inclusion/deletion | 3.70 | Structural flow / discrete event | Deferred | External calendar dependency; low frequency |
| NF-20261109-19 Options dealer GEX | 3.10 | Market structure / dealer positioning | Deferred | No free historical options chain/GEX |
| NF-20261109-02 Earnings estimate revision momentum | 3.65 | Fundamental / analyst revision | Deferred | No free PIT revision history |
| NF-20261109-22 RSP-SPY breadth relmom | 3.75 | Participation / factor momentum | Deferred | Adjacency to H97 + exhausted relmom families |
| NF-20261109-23 USMV-SPY low-vol relmom | 3.55 | Factor/style momentum | Deferred | USMV inception/style adjacency |
| NF-20261109-12 Holiday/pre-holiday drift | 4.00 | Calendar microstructure | HELD | Calendar adjacency H91/H140/H142/H168 |
| NF-20261110-04 10Y-3M yield-curve inversion depth | 3.80 | Macro term-premium | Deferred | Adjacency to H171/H11r curve families |
| NF-20261110-05 SPY realized jump asymmetry | 3.80 | Higher-moment / jump-risk asymmetry | Deferred | Adjacency to H122/H128/H135; low plausibility/support |
| NF-04 Commodity carry | — | Carry / term structure | **BLOCKED** | No free PIT term-structure/roll proxy |
| NF-05 Short-term CS reversal | — | Liquidity provision | **DEFERRED** | Turnover/net-of-cost; H119 REJECT 3/8 |
| NF-08-16 Halloween seasonal | 3.90 | Calendar seasonal | **HELD** | Calendar adjacency H91/H140/H142 |
| NF-09-03 Breakeven-inflation | 3.40 | Macro regime | **DEFERRED/DATA-LIMITED** | ^T5YIE/^T10YIE unavailable; H175 proxy |
| NF-20261109-20 Stock split effects | — | Corporate action | DEFERRED | Low frequency; incomplete split data |

## Required next work (Cycle 96 / H182)
1. Reconcile lineage to H181; complete directive §4 discovery (≥3 repo-new/decisive candidates across ≥3 broad mechanism categories, honest 25/25/20/15/10/5, concrete deferred reassessment, NF-root checks, no silent drops).
2. Pre-register highest-expected-information feasible candidate as **H182** before validation outcomes.
3. Implement runner + focused tests; `ruff check/format --check`; `PYTHONPATH=src pytest -q` focused tests; execute REAL; record verdict/artifacts in `HYPOTHESIS_SPEC.md` §H182, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. Do not fabricate results.

## Integrity constraints
- No gate weakening; no published/certified artifact modification; no fabrication; free/public data only.
- `src/qtr` unchanged unless evidenced defect (then rerun pinned 100% suite).
- No commit/push unless explicitly authorized.
- Selection/validation uses no protected-test feedback. Gates fail-closed on pre-registered OOS Val+Test.

## Approaches that failed / evidence (do not blindly repeat)
- **H181:** ES-SPY cash-futures basis mean-reversion (NF-20261104-03) REJECT 4/8 (Sharpe 0.297, PF 1.162, worst-regime −1.410, bench p 0.992/IR −0.877). Daily-close basis edge too small/noisy; do not rerun same construction without materially different mechanism/observable.
- **H180:** Ex-dividend capture (NF-20261109-16) REJECT 2/8 (Sharpe 0.194, PF 1.149, WF −0.313, worst-regime −1.980, perturb −3.115, bench fail).
- **H179:** FINRA short-interest z-score timing REJECT 2/8 (Sharpe −0.449, PF 0.920, WF −2.647, worst-regime −1.970); inverse/random outperformed.
- **H178:** CBOE equity P/C z-score REJECT 4/8; random-signal outperformed. **H177:** Treasury auction REJECT 5/8. **H176:** Tax-loss harvesting REJECT 3/8. **H175:** Macro regime REJECT 7/8.
- **H174:** ETF premium/discount invalid without PIT NAV. **H173:** Fed model / ERP REJECT 7/8.
- All H85–H181 rejected on free, point-in-time data. Avoid silent recycling of exhausted construction classes without a *materially different* mechanism/observable and explicit novelty justification.
