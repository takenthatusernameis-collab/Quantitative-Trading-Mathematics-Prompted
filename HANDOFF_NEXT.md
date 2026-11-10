# HANDOFF_NEXT.md — Cycle 93 (after H178 REJECT 4/8, H179 PRE-REGISTERED)

## Session summary
- **Cycle 92 complete.** Performed directive §4 discovery (≥3 candidates across ≥3 categories, honest scoring, deferred reassessment, NF-root checks), pre-registered and executed **H178 (NF-20261110-03: CBOE Equity Put/Call Ratio Regime Timing)** as a real, honest test.
- **Result:** REJECT 4/8 gates. OOS Val+Test (2117 periods, 115 trades): Sharpe **0.557** (fail), PF **1.407** (pass), max DD **−2.78%** (pass), trades **115** (pass), WF stability **0.658** (fail), worst-regime rolling-252 Sharpe **−1.002** (fail), benchmark p **0.983** / IR **−0.731** vs buy-hold SPY 0.819/+85.03% (fail), perturbation min ratio **0.588** (pass).
- **Mechanism assessment:** No certifiable sentiment edge. Random-signal ablation **outperformed** strategy (0.835 vs 0.557); inverse-mode −0.156. Train-only WF selected momentum mode (0.957) decayed OOS; worst-regime fragile.
- **Artifacts:** `.experiments/nf_runs/nf_20261110_03_equity_pc_ratio_20261110_cycle92/summary.json`, `grid.csv` (~29s). Data: SPY yfinance + CBOE equity P/C CSV (free PIT), 2010-01-04→2026-10-30 (4233 aligned rows). Selected `pc_window=20, entry_z=0.5, exit_z=-0.5, vol_target=0.10, mode=momentum`.
- **Files added/modified:** `run_nf_20261110_03_equity_pc_ratio.py`, `tests/test_nf_20261110_03_equity_pc_ratio.py` (14 passed), `HYPOTHESIS_SPEC.md` §H178, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 92, `NEXT_TASK.md`, `HANDOFF_NEXT.md`, `HANDOFF_CURRENT_SESSION.md`.
- **Integrity (honest):** `ruff check/format --check` clean on new runner/tests; focused pytest 14 passed. No gate/threshold/grid/construction weakened; `src/qtr` unchanged. No published/certified artifact modified.

- **Cycle 93 discovery complete.** Performed directive §4 discovery (4 repo-new candidates across 4 broad mechanism categories, honest scoring, deferred pool reassessed with evidence, NF-root checks). Pre-registered **H179 (NF-20261110-06: Short Interest / Securities Lending Flow Timing)** as highest-expected-information candidate (weighted 4.40). Implementation pending.

## Lineage state
- H85–H178 all rejected/recorded. H179 pre-registered. Next unused H-ID after H179: **H180** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged. No commit/push.

## Deferred pool (no silent drops; reassess with concrete evidence)
| Candidate | Score | Category | Status | Evidence / blocker |
|---|---:|---|---|---|
| NF-20261109-16 Dividend capture / ex-dividend microstructure premium | 4.05 | Corporate action / microstructure | Deferred | Overnight/open slippage risk decisive on free data; tax-clientele/microstructure fragility; mixed literature post-costs |
| NF-20261109-18 S&P 500 inclusion/deletion discrete event flow | 3.70 | Structural flow / discrete event | Deferred | Low frequency (~20-40 events/yr); external index-change calendar dependency |
| NF-20261109-19 Options dealer gamma exposure (GEX) | 3.10 | Market structure / dealer positioning | Deferred | No free historical options chain/GEX (yfinance snapshot only) |
| NF-20261109-02 Earnings estimate revision momentum | 3.65 | Fundamental / analyst revision | Deferred | No free PIT revision history |
| NF-20261109-22 RSP-SPY breadth-participation relmom | 3.75 | Cross-asset participation / factor momentum | Deferred | Adjacency to H97 + exhausted relmom families; mechanism distinction must be explicit |
| NF-20261109-23 USMV-SPY low-vol factor relmom | 3.55 | Factor anomaly / style momentum | Deferred | USMV inception 2011; style adjacency to exhausted factor families |
| NF-20261109-12 Holiday / pre-holiday drift SPY timing | 4.00 | Calendar microstructure | HELD | Calendar adjacency to H91/H140/H142/H168 |
| NF-20261110-04 10Y-3M yield-curve inversion depth de-risking | 3.80 | Macro term-premium / recession-risk transmission | Deferred | Honest adjacency to H171/H11r yield-slope/level families (same observable class) |
| NF-20261110-05 SPY realized upside/downside jump asymmetry | 3.80 | Higher-moment / jump-risk asymmetry | Deferred | Low plausibility/support post-costs; adjacency to H122/H128/H135 |
| NF-04 Commodity carry | — | Carry / term structure | **BLOCKED** | No free PIT term-structure/roll proxy |
| NF-05 Short-term CS reversal | — | Liquidity provision | **DEFERRED** | Turnover/net-of-cost; H119 weekly REJECT 3/8 |
| NF-08-16 Halloween seasonal | 3.90 | Calendar seasonal | **HELD** | Calendar adjacency H91/H140/H142 |
| NF-09-03 Breakeven-inflation | 3.40 | Macro regime | **DEFERRED/DATA-LIMITED** | ^T5YIE/^T10YIE unavailable on yfinance |
| NF-20261109-20 Stock split announcement effects | — | Corporate action / microstructure | DEFERRED | Low frequency; corporate action data on yfinance incomplete for splits |

## Required next work (Cycle 93 / H179 implementation)
1. Implement runner `run_nf_20261110_06_short_interest.py` + focused tests `tests/test_nf_20261110_06_short_interest.py`.
2. Run `ruff check/format --check` on new files; focused `pytest -q` pass.
3. Execute REAL; record verdict in `HYPOTHESIS_SPEC.md` §H179, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 93, `NEXT_TASK.md`, `HANDOFF_NEXT.md`.

## Integrity constraints
- No gate weakening; no published/certified artifact modification; no fabrication; free data only.
- `src/qtr` unchanged unless evidenced defect (then rerun pinned 100% suite).
- No commit/push unless explicitly authorized.
- Selection/validation uses no protected-test feedback. Gates fail-closed on pre-registered OOS Val+Test.

## Approaches that failed / evidence (do not blindly repeat)
- H178: CBOE equity put/call ratio z-score regime timing REJECT 4/8 (Sharpe 0.557, WF 0.658, worst-regime −1.002, bench p 0.983/IR −0.731). **Random-signal ablation outperformed (0.835)**. Do not rerun same P/C z-score construction without materially different mechanism/observable.
- H177: Treasury auction supply-pressure timing REJECT 5/8 (Sharpe 0.720, worst-regime −1.133, bench fail); synthetic auction data limitation.
- H176: Tax-loss harvesting REJECT 3/8 (Sharpe 0.628, trades 8, WF 0.540, worst-regime −1.443).
- H175: Macro regime timing REJECT 7/8; inverse-regime falsifier outperformed.
- H174: ETF premium/discount invalid without point-in-time NAV.
- H173: Fed model / ERP timing REJECT 7/8; inverse-signal outperformed.
- All H85–H178 rejected on free, point-in-time data. Avoid silent recycling of exhausted construction classes without a *materially different* mechanism/observable and explicit novelty justification.
