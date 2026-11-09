# HANDOFF_NEXT.md — Cycle 87 (after H172 REJECT 3/8)

## Session summary
- **Cycle 86 complete.** Executed H172 (NF-20261109-01 reused label: Intraday Equity Time-of-Day Seasonality, SPY 1h ET) as a real, honest test.
- **Result:** REJECT 3/8 gates. OOS Val+Test (476 trades): Sharpe **-0.936** (fail), PF **0.737** (fail), max DD **-6.01%** (pass), trades **476** (pass), WF stability **NaN** (fail; train ref non-positive), worst-regime rolling-252 Sharpe **-2.650** (fail), benchmark p **0.975** / IR **-1.938** vs buy-hold SPY 0.330 (fail), perturbation min ratio **0.886** (pass).
- **Mechanism falsified (this construction):** Pre-registered ET hour-window seasonality on SPY 1h (vol-targeted, 1-bar delay) shows no OOS edge; train-only WF Sharpe negative; inverse-hour weak and benchmark strongly negative. Limited by yfinance ~730-bar 1h history (~2y).
- **Artifacts:** `.experiments/nf_runs/nf_20261109_01_intraday_seasonality_20261109_213639/summary.json`, `grid.csv` (4.31s). Data: SPY 1h yfinance ET, 3313 bars 2024-12-02→2026-10-30. Selected (WF mean -0.299): `hour_window=[10,11] ET, vol_target=0.15, vol_window=63`.
- **Files added/modified (uncommitted):** `run_nf_20261109_01_intraday_seasonality.py`, `tests/test_nf_20261109_01_intraday_seasonality.py` (10 passed), `HYPOTHESIS_SPEC.md` §H172, `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 86 execution appended), `NEXT_TASK.md`, this handoff.
- **Integrity (honest):** NF label `NF-20261109-01` reused vs H160 (distinct mechanism/H-ID/artifact). Tests/runner ablation hour universe aligned to ET-native encoding (9–15 ET) during verification (pre-execution test expected UTC 13–19); random/inverse controls corrected to ET 9–15. No gate/threshold/grid/construction weakened; spec clarified to ET. `ruff check/format` clean; focused pytest 10 passed. No published/certified artifact modified.

## Lineage state
- H85–H172 all rejected/recorded. Next unused H-ID: **H173** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged. No commit/push.

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

## Required next work (Cycle 87 / H173)
1. Reconcile lineage to H172; confirm H173 next unused; avoid NF-label reuse.
2. **Directive §4 discovery:** ≥3 repo-new candidates across ≥3 broad mechanism categories, honest 25/25/20/15/10/5 scoring, no silent drops. Search materially different mechanism categories before recycling; scrutinize heavily executed categories.
3. Verify NF roots against executed H-IDs/artifacts/runners.
4. Pre-register H173 before validation outcomes (decision-ready).
5. Implement runner + focused tests; `ruff check/format` clean; focused `pytest` pass.
6. Execute REAL; record verdict in `HYPOTHESIS_SPEC.md` §H173, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 87, `NEXT_TASK.md`, `HANDOFF_NEXT.md`.

## Integrity constraints
- No gate weakening; no published/certified artifact modification; no fabrication; free data only.
- `src/qtr` unchanged unless evidenced defect (then rerun pinned 100% suite).
- No commit/push unless explicitly authorized.
- Selection/validation uses no protected-test feedback.

## Approaches that failed / evidence (do not blindly repeat)
- H172: SPY 1h ET seasonality — train WF negative, OOS -0.936 Sharpe/PF 0.737/worst-regime -2.650/benchmark fail; random/inverse no edge; yfinance 1h history limited.
- H171: ^TYX-^FVX slope de-risking — no benchmark edge.
- H170/H169/H168: leveraged ETF flows, overnight futures lead-lag, index-rebalance window — all failed key gates.
- All H85–H172 rejected on free, point-in-time data. Avoid silent recycling of exhausted construction classes.
