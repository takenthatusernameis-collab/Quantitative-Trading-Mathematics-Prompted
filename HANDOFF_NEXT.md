# HANDOFF_NEXT.md — Cycle 88 (after H174 REJECT 2/8)

## Session summary
- **Cycle 88 complete.** Executed H174 (NF-20261109-26: ETF Creation/Redemption Premium-Discount Mean Reversion) as a real, honest test.
- **Result:** REJECT 2/8 gates. OOS Val+Test (484 trades): Sharpe **0.074** (fail), PF **1.019** (fail), max DD **−18.95%** (fail), trades **484** (pass), WF stability **0.740** (pass), worst-regime rolling-252 Sharpe **−1.753** (fail), benchmark p **0.982** / IR **−0.721** vs buy-hold SPY 0.819 (fail), perturbation min ratio **0.000** (fail).
- **Mechanism falsified (this construction):** ETF premium/discount mean reversion with approximated NAV (no free point-in-time NAV source) shows no OOS edge; random-premium ablation outperforms the strategy (Sharpe 0.282 vs 0.074), confirming no information in the z-score timing. The NAV data limitation is the decisive blocker; without point-in-time NAV, the creation/redemption arbitrage mechanism cannot be fairly tested.
- **Artifacts:** `.experiments/nf_runs/nf_20261109_26_etf_nav_arbitrage_20261109_234241/summary.json`, `grid.csv` (68.0s). Data: SPY daily yfinance 2010-01-04→2026-10-30 (4233 rows). NAV approximated via mean-reverting noise process (documented limitation). Selected (train-only WF mean Sharpe 0.027): `z_window=21, entry_z=1.5, exit_z=0.5, vol_target=0.10, universe={SPY}`.
- **Files added/modified (uncommitted):** `run_nf_20261109_26_etf_nav_arbitrage.py`, `tests/test_nf_20261109_26_etf_nav_arbitrage.py` (13 passed), `HYPOTHESIS_SPEC.md` §H174, `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 88 execution appended), `NEXT_TASK.md`, this handoff.
- **Integrity (honest):** `ruff check/format` clean; focused pytest 13 passed. No gate/threshold/grid/construction weakened; `src/qtr` unchanged. No published/certified artifact modified.

## Lineage state
- H85–H174 all rejected/recorded. Next unused H-ID: **H175** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged. No commit/push.

## Deferred pool (no silent drops; reassess with concrete evidence)
| Candidate | Score | Category | Status | Evidence / blocker |
|---|---:|---|---|---|
| NF-20261109-15 Tax-loss harvesting / year-end selling | 4.20 | Institutional/behavioral constraint | Deferred | Survivorship-managed constituent/YTD-loser universe decisive risk on free yfinance; sector-ETF proxy weakens mechanism |
| NF-20261109-16 Dividend capture / ex-dividend microstructure | 3.95 | Corporate action / microstructure | Deferred | Event alignment, overnight/open costs, tax-clientele/microstructure fragility |
| NF-20261109-12 Holiday / pre-holiday drift SPY timing | 4.00 | Calendar microstructure | Deferred | Adjacency to H91/H140/H142/H168 calendar families |
| NF-20261109-22 RSP-vs-SPY breadth-participation relmom | 3.75 | Cross-asset participation / factor momentum | Deferred | Adjacency to H97 (same pair) — mechanism distinction must be explicit |
| NF-20261109-23 USMV-vs-SPY low-vol factor relmom | 3.55 | Factor anomaly / style momentum | Deferred | USMV inception 2011, style adjacency |
| NF-20261109-18 S&P 500 inclusion/deletion discrete event | 3.90 | Structural flow / discrete event | Deferred | Low frequency, external index-change data dependency |
| NF-20261109-19 Options dealer gamma exposure | 3.50 | Market structure / dealer positioning | Deferred | Options chain/GEX construction complexity; free data history limits |
| NF-20261109-20 Stock split announcement effects | 3.10 | Corporate action / behavioral | Deferred | Low frequency |
| NF-20261109-02 Earnings estimate revision momentum | 3.65 | Fundamental / analyst revision | Deferred (Cycle 86 runner-up) | Revision-history PIT construction risk; yfinance snapshot/history limits |
| NF-20261109-03 Cross-asset macro growth/inflation proxies | 3.85 | Macro factor regime | Deferred (Cycle 86 runner-up) | Market-proxy noise vs official data; adjacency to macro/rates families requires explicit separation |
| NF-04 Commodity carry | — | Carry / term structure | **BLOCKED** | No free PIT term-structure/roll proxy |
| NF-05 Short-term CS reversal | — | Liquidity provision | **DEFERRED** | Turnover/net-of-cost; H119 weekly REJECT 3/8 |
| NF-08-16 Halloween seasonal | 3.90 | Calendar seasonal | **HELD** | Calendar adjacency H91/H140/H142 |
| NF-09-03 Breakeven-inflation | 3.40 | Macro regime | **DEFERRED/DATA-LIMITED** | ^T5YIE/^T10YIE unavailable on yfinance |

## Required next work (Cycle 89 / H175)
1. Reconcile lineage to H174; confirm H175 next unused; avoid NF-label reuse.
2. **Directive §4 discovery:** ≥3 repo-new candidates across ≥3 broad mechanism categories, honest 25/25/20/15/10/5 scoring, no silent drops. Search materially different mechanism categories before recycling; scrutinize heavily executed categories.
3. Verify NF roots against executed H-IDs/artifacts/runners.
4. Pre-register H175 before validation outcomes (decision-ready).
5. Implement runner + focused tests; `ruff check/format` clean; focused `pytest` pass.
6. Execute REAL; record verdict in `HYPOTHESIS_SPEC.md` §H175, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 89, `NEXT_TASK.md`, `HANDOFF_NEXT.md`.

## Integrity constraints
- No gate weakening; no published/certified artifact modification; no fabrication; free data only.
- `src/qtr` unchanged unless evidenced defect (then rerun pinned 100% suite).
- No commit/push unless explicitly authorized.
- Selection/validation uses no protected-test feedback.

## Approaches that failed / evidence (do not blindly repeat)
- H174: ETF premium/discount mean reversion (NAV approximated) failed 6/8 gates (Sharpe 0.074, PF 1.019, DD −18.95%, worst-regime −1.753, benchmark p 0.982/IR −0.721, perturbation 0.0); random-premium ablation outperforms signal; NAV approximation invalidates mechanism test — **without point-in-time NAV, creation/redemption arbitrage cannot be fairly tested**.
- H173: Fed model / ERP timing (div yield − 10Y yield) failed 7/8 gates (Sharpe 0.310, PF 1.170, DD −16.89%, trades 114, WF 0.264, worst-regime −1.326, benchmark p 0.991/IR −0.813); inverse-signal outperformed (0.739); train WF 1.363 → OOS 0.310 decay.
- H172: SPY 1h intraday seasonality (ET windows) failed Sharpe/PF/WF/worst-regime/benchmark; train WF negative; limited ~2y 1h history (yfinance 730-bar constraint). Do not rerun same hour-window construction without materially different mechanism/data.
- H171: ^TYX-^FVX slope de-risking failed Sharpe/PF/worst-regime/benchmark.
- H170: Leveraged ETF rebalancing flow failed Sharpe/PF/worst-regime/benchmark/perturbation.
- H169: Overnight futures lead-lag failed Sharpe/PF/worst-regime/benchmark.
- H168: Quarterly index-rebalance window de-risking failed; random-window control matched base.
- All H85–H174 rejected on free, point-in-time data. Avoid silent recycling of exhausted construction classes without a *materially different* mechanism/observable and explicit novelty justification.