# HANDOFF_NEXT.md — Cycle 89 (after H175 REJECT 1/8)

## Session summary
- **Cycle 89 complete.** Executed H175 (NF-20261109-03: Cross-Asset Macro Regime Timing — growth HG=F/GC=F − inflation TIP/IEF composite → vol-targeted SPY) as a real, honest test.
- **Bug fixed during implementation:** regime composite `(g_z - i_z).fillna(0)` poisoned the entire signal to zero whenever either component had zero rolling std (constant series); fixed to `g_z.fillna(0) - i_z.fillna(0)` in both the runner and the inverse-regime direction falsifier. Verified via focused tests.
- **Result:** REJECT 1/8 gates. OOS Val+Test (123 trades): Sharpe **−0.005** (fail), PF **0.998** (fail), max DD **−9.7%** (pass), trades **123** (fail), WF stability **−0.004** (fail), worst-regime rolling-252 Sharpe **−1.31** (fail), benchmark p **0.996** / IR **−0.931** vs buy-hold SPY 0.810 (fail), perturbation min ratio **−32.37** (fail).
- **Mechanism falsified (this construction):** Train WF Sharpe 1.288 → OOS Sharpe −0.005 (classic train→OOS collapse); inverse-regime direction falsifier OOS Sharpe 1.009/PF 1.217 **outperforms the signal** (382 trades), confirming the "favorable regime → long SPY" causal chain is not supported on this sample. Only maxDD clears its gate. No gate weakening.
- **Artifacts:** `.experiments/nf_runs/nf_20261109_03_macro_regime_20261110_004316/summary.json`, `grid.csv` (~11s). Data: SPY + HG=F, GC=F, TIP, IEF daily yfinance 2010-01-01→2026-10-31 (4233 aligned rows). Selected (train-only 4-fold WF Sharpe 1.288): `lookback=126, entry_z=1.0, exit_z=0.0, vol_target=0.10`.
- **Files added/modified (uncommitted):** `run_nf_20261109_03_macro_regime.py`, `tests/test_nf_20261109_03_macro_regime.py` (10 passed), `HYPOTHESIS_SPEC.md` §H175 (execution/verdict appended), `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 89 execution appended), `NEXT_TASK.md`, this handoff.
- **Integrity (honest):** `ruff check/format` clean; focused pytest 10 passed. No gate/threshold/grid/construction weakened; `src/qtr` unchanged. No published/certified artifact modified.

## Lineage state
- H85–H175 all rejected/recorded. Next unused H-ID: **H176** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged. No commit/push.

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
| NF-04 Commodity carry | — | Carry / term structure | **BLOCKED** | No free PIT term-structure/roll proxy |
| NF-05 Short-term CS reversal | — | Liquidity provision | **DEFERRED** | Turnover/net-of-cost; H119 weekly REJECT 3/8 |
| NF-08-16 Halloween seasonal | 3.90 | Calendar seasonal | **HELD** | Calendar adjacency H91/H140/H142 |
| NF-09-03 Breakeven-inflation | 3.40 | Macro regime | **DEFERRED/DATA-LIMITED** | ^T5YIE/^T10YIE unavailable on yfinance |
| NF-20261105-11r TNX/FVX slope | — | Rates term-structure | Deferred (data-resolved variant of NF-11) | Novelty scored honestly lower (same root mechanism) |
| NF-20261105-12 Cross-sectional equity dispersion | — | Dispersion / cross-section | Deferred | Complexity/turnover vs smallest decisive test |
| NF-20261105-17 Volume-shock reversal | — | Liquidity provision | Deferred | Turnover/cost-sensitive |
| NF-20261105-20 Treasury auction supply-pressure | — | Event-driven | Deferred | Event calendar/point-in-time timestamp construction |
| NF-20261105-21 Month-end pension rebalancing | — | Calendar/flow | Deferred | Weak evidence/adjacency risk |
| NF-20261106-03 VVIX vol-of-vol | — | Vol uncertainty | Deferred | VIX-complex adjacency; novelty 3 |

## Required next work (Cycle 90 / H176)
1. Reconcile lineage to H175; confirm H176 next unused; avoid NF-label reuse.
2. **Directive §4 discovery:** ≥3 repo-new candidates across ≥3 broad mechanism categories, honest 25/25/20/15/10/5 scoring, no silent drops. Search materially different mechanism categories before recycling; scrutinize heavily executed categories.
3. Verify NF roots against executed H-IDs/artifacts/runners.
4. Pre-register H176 before validation outcomes (decision-ready).
5. Implement runner + focused tests; `ruff check/format` clean; focused `pytest` pass.
6. Execute REAL; record verdict in `HYPOTHESIS_SPEC.md` §H176, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 90, `NEXT_TASK.md`, `HANDOFF_NEXT.md`.

## Integrity constraints
- No gate weakening; no published/certified artifact modification; no fabrication; free data only.
- `src/qtr` unchanged unless evidenced defect (then rerun pinned 100% suite).
- No commit/push unless explicitly authorized.
- Selection/validation uses no protected-test feedback.

## Approaches that failed / evidence (do not blindly repeat)
- H175: Cross-asset macro regime timing failed 7/8 gates (Sharpe −0.005, PF 0.998, trades 123, WF −0.004, worst-regime −1.31, benchmark p 0.996/IR −0.931, perturbation −32.37); inverse-regime falsifier outperforms signal (1.009 vs −0.005); train WF 1.288 → OOS −0.005 decay. **Composite macro regime has no OOS edge on free daily data after costs.**
- H174: ETF premium/discount mean reversion (NAV approximated) failed 6/8 gates (Sharpe 0.074, PF 1.019, DD −18.95%, worst-regime −1.753, benchmark p 0.982/IR −0.721, perturbation 0.0); random-premium ablation outperforms signal; NAV approximation invalidates mechanism test — **without point-in-time NAV, creation/redemption arbitrage cannot be fairly tested**.
- H173: Fed model / ERP timing (div yield − 10Y yield) failed 7/8 gates (Sharpe 0.310, PF 1.170, DD −16.89%, trades 114, WF 0.264, worst-regime −1.326, benchmark p 0.991/IR −0.813); inverse-signal outperformed (0.739); train WF 1.363 → OOS 0.310 decay.
- H172: SPY 1h intraday seasonality (ET windows) failed Sharpe/PF/WF/worst-regime/benchmark; train WF negative; limited ~2y 1h history (yfinance 730-bar constraint). Do not rerun same hour-window construction without materially different mechanism/data.
- H171: ^TYX-^FVX slope de-risking failed Sharpe/PF/worst-regime/benchmark.
- H170: Leveraged ETF rebalancing flow failed Sharpe/PF/worst-regime/benchmark/perturbation.
- H169: Overnight futures lead-lag failed Sharpe/PF/worst-regime/benchmark.
- H168: Quarterly index-rebalance window de-risking failed; random-window control matched base.
- All H85–H175 rejected on free, point-in-time data. Avoid silent recycling of exhausted construction classes without a *materially different* mechanism/observable and explicit novelty justification.
