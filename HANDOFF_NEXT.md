# HANDOFF_NEXT.md — Cycle 92 (after H177 REJECT 5/8)

## Session summary
- **Cycle 91 complete.** Executed H177 (NF-20261110-01: Treasury Auction Supply-Pressure Timing — vol-targeted SPY from auction demand composite) as a real, honest test.
- **Result:** REJECT 5/8 gates. OOS Val+Test (2117 periods, 98 trades): Sharpe **0.720** (fail), PF **1.367** (pass), max DD **−4.51%** (pass), trades **98** (pass), WF stability **1.612** (pass), worst-regime rolling-252 Sharpe **−1.133** (fail), benchmark p **0.900** / IR **−0.442** vs buy-hold SPY 0.819 (fail), perturbation min ratio **0.651** (pass).
- **Mechanism assessment:** Direction correct (inverse-signal −0.730, random-auction −0.448 both weaker than strategy 0.720), but effect size insufficient to clear gates. Synthetic auction data limitation (no free point-in-time Treasury Direct CSV); auction-equity transmission weak on daily horizon. Train WF 0.436 → OOS 0.720 improvement but below certification threshold.
- **Artifacts:** `.experiments/nf_runs/nf_20261110_01_treasury_auction_20261110_050114/summary.json`, `grid.csv` (~17s). Data: SPY daily yfinance 2010-01-04→2026-10-30 (4233 rows); synthetic 10Y/30Y auction calendar (269 auctions). Selected (train-only 4-fold WF Sharpe 0.436): `score_window=20, entry_z=1.0, exit_z=0.0, vol_target=0.10, tenor=10Y`.
- **Files added/modified (uncommitted):** `run_nf_20261110_01_treasury_auction.py`, `tests/test_nf_20261110_01_treasury_auction.py` (17 passed), `HYPOTHESIS_SPEC.md` §H177 (execution/verdict appended), `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 91 execution appended), `NEXT_TASK.md`, this handoff.
- **Integrity (honest):** `ruff check/format` clean; focused pytest 17 passed. No gate/threshold/grid/construction weakened; `src/qtr` unchanged. No published/certified artifact modified.

## Lineage state
- H85–H177 all rejected/recorded. Next unused H-ID: **H178** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged. No commit/push.

## Deferred pool (no silent drops; reassess with concrete evidence)
| Candidate | Score | Category | Status | Evidence / blocker |
|---|---:|---|---|---|
| NF-20261109-16 Dividend capture / ex-dividend microstructure | 4.05 | Corporate action / microstructure | Deferred | Overnight/open slippage risk; tax-clientele/microstructure fragility; mixed literature post-costs |
| NF-20261109-18 S&P 500 inclusion/deletion discrete event | 3.70 | Structural flow / discrete event | Deferred | Low frequency (~20-40 events/yr); external index-change calendar dependency (S&P/Wikipedia) |
| NF-20261109-19 Options dealer gamma exposure (GEX) | 3.10 | Market structure / dealer positioning | Deferred | yfinance options chain current snapshot only; no free historical GEX series; construction complexity |
| NF-20261109-02 Earnings estimate revision momentum | 3.65 | Fundamental / analyst revision | Deferred | Revision-history PIT construction risk; yfinance snapshot only, no revision history |
| NF-20261109-22 RSP-SPY breadth-participation relmom | 3.75 | Cross-asset participation / factor momentum | Deferred | Adjacency to H97 (same pair) — mechanism distinction must be explicit |
| NF-20261109-23 USMV-SPY low-vol factor relmom | 3.55 | Factor anomaly / style momentum | Deferred | USMV inception 2011, style adjacency to exhausted factor families |
| NF-20261109-12 Holiday / pre-holiday drift SPY timing | 4.00 | Calendar microstructure | HELD | Calendar adjacency to H91/H140/H142/H168 exhausted calendar families |
| NF-04 Commodity carry | — | Carry / term structure | **BLOCKED** | No free PIT term-structure/roll proxy |
| NF-05 Short-term CS reversal | — | Liquidity provision | **DEFERRED** | Turnover/net-of-cost; H119 weekly REJECT 3/8 |
| NF-08-16 Halloween seasonal | 3.90 | Calendar seasonal | **HELD** | Calendar adjacency H91/H92/H142 |
| NF-09-03 Breakeven-inflation | 3.40 | Macro regime | **DEFERRED/DATA-LIMITED** | ^T5YIE/^T10YIE unavailable on yfinance; TIP/IEF proxy subsumed in H175 |

## Required next work (Cycle 92 / H178)
1. Reconcile lineage to H177; confirm H178 next unused; avoid NF-label reuse.
2. **Directive §4 discovery:** ≥3 repo-new candidates across ≥3 broad mechanism categories, honest 25/25/20/15/10/5 scoring, no silent drops. Search materially different mechanism categories before recycling; scrutinize heavily executed categories.
3. Verify NF roots against executed H-IDs/artifacts/runners.
4. Pre-register H178 before validation outcomes (decision-ready).
5. Implement runner + focused tests; `ruff check/format` clean; focused `pytest` pass.
6. Execute REAL; record verdict in `HYPOTHESIS_SPEC.md` §H178, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 92, `NEXT_TASK.md`, `HANDOFF_NEXT.md`.

## Integrity constraints
- No gate weakening; no published/certified artifact modification; no fabrication; free data only.
- `src/qtr` unchanged unless evidenced defect (then rerun pinned 100% suite).
- No commit/push unless explicitly authorized.
- Selection/validation uses no protected-test feedback.
- All gates fail-closed on pre-registered OOS Val+Test.

## Approaches that failed / evidence (do not blindly repeat)
- H177: Treasury auction supply-pressure timing (vol-targeted SPY from auction demand composite) REJECT 5/8 (Sharpe 0.720, worst-regime −1.133, benchmark p 0.900/IR −0.442). Direction correct (inverse −0.730, random-auction −0.448) but effect size insufficient; synthetic auction data limitation (no free point-in-time Treasury Direct CSV); auction-equity transmission weak on daily horizon. Train WF 0.436 → OOS 0.720 improvement but below certification threshold.
- H176: Tax-loss harvesting / year-end selling pressure (long YTD losers in Dec, hold into Jan) REJECT 3/8 (Sharpe 0.628, trades 8, WF stability 0.540, worst-regime −1.443, benchmark p 0.977/IR −0.975). Direction correct (inverse −0.365, random-year 0.098) but effect size too small; low frequency (8 trades/4yr OOS) limits power; train WF 1.212 → OOS 0.628 decay. Structural tax-flow edge does not clear gates on free daily data.
- H175: Cross-asset macro regime timing (z(HG=F/GC=F) − z(TIP/IEF) → SPY) failed 7/8 gates (Sharpe −0.005, PF 0.998, trades 123, WF −0.004, worst-regime −1.31, benchmark p 0.996/IR −0.931, perturbation −32.37); only maxDD passes; inverse-regime falsifier outperforms (1.009 vs −0.005); train WF 1.288 → OOS −0.005 decay. Composite macro regime has no OOS edge on free daily data after costs.
- H174: ETF premium/discount mean reversion (NAV approximated) failed 6/8 gates (Sharpe 0.074, PF 1.019, DD −18.95%, worst-regime −1.753, benchmark p 0.982/IR −0.721, perturbation 0.0); random-premium ablation outperforms signal; NAV approximation invalidates mechanism test — **without point-in-time NAV, creation/redemption arbitrage cannot be fairly tested**.
- H173: Fed model / ERP timing (div yield − 10Y yield) failed 7/8 gates (Sharpe 0.310, PF 1.170, DD −16.89%, trades 114, WF 0.264, worst-regime −1.326, benchmark p 0.991/IR −0.813); inverse-signal outperformed (0.739); train WF 1.363 → OOS 0.310 decay.
- H172: SPY 1h intraday seasonality (ET windows) failed Sharpe/PF/WF/worst-regime/benchmark; train WF negative; limited ~2y 1h history (yfinance 730-bar constraint). Do not rerun same hour-window construction without materially different mechanism/data.
- H171: ^TYX-^FVX slope de-risking failed Sharpe/PF/worst-regime/benchmark.
- H170: Leveraged ETF rebalancing flow failed Sharpe/PF/worst-regime/benchmark/perturbation.
- H169: Overnight futures lead-lag failed Sharpe/PF/worst-regime/benchmark.
- H168: Quarterly index-rebalance window de-risking failed; random-window control matched base.
- All H85–H177 rejected on free, point-in-time data. Avoid silent recycling of exhausted construction classes without a *materially different* mechanism/observable and explicit novelty justification.

(End of file)