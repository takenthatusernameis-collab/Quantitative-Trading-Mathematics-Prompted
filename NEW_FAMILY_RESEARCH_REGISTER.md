# NEW_FAMILY_RESEARCH_REGISTER.md

**Purpose:** Durable record of new-strategy-family discovery per STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md and NEXT_TASK.md. Updated once per research cycle. Never overwrite historical entries.

**Session:** 2026-11-04
**Repository state:** HEAD `1c3fd75` on `main`, tree clean. Max H-ID: H84. No H-IDs beyond H84 found.

---

## 1. Family-Lineage Map (H1–H84 reconciliation)

Every H-ID classified per directive §3 (six classes). Gaps: H24, H68–H73, H76–H79 never assigned.

### Root strategy families (class 1)

| Root family | H-IDs | Mechanism | Markets / data | Verdict | Known failure mode |
|---|---|---|---|---|---|
| Time-series momentum (TSMOM) | H1, H7, H8, H9, H10, H11, H12, H21, H22, H23, H25 | Price trend persistence; buy own-past winners, sell losers | Futures (ES/NQ/CL/GC/ZB), crypto perp; hourly ~730d free / daily years | Daily: all REJECTED (OOS Sharpe ≤ 0.814). Intraday: H10/H22/H25 published PASS but **CAUSAL_REJECTED** by H27/H28 look-ahead. H23 crypto REJECTED (structural negative edge on 134-bar slice). | H27 look-ahead via `_daily_target_from_hourly` → `resample("1D").last()` expanded back to hourly grid; H26 Sharpe per-bar ×√252 artifact; PF margin CI-fragile on H25 (P(PF≥1.3)=0.6215) |
| Cross-sectional momentum | H2, H16 | Relative strength ranking; long top-K, short bottom-K | ETFs; daily | REJECTED (H2 Sharpe 0.116, H16 Sharpe 0.579) | No persistent relative strength edge after costs |
| Regime-gated vol-scaled momentum | H3, H5, H6 | Momentum + vol targeting + regime filters (VIX/DD) | Futures + ^VIX; daily | REJECTED (H3 Sharpe −0.868, H5 0.509, H6 0.708) | Regime filters not actionable; drawdown conditioning ineffective |
| Volatility risk premium (VRP) | H17 | Short volatility (SVXY) gated by term structure; harvest VRP | SVXY, ^VIX, ^VIX3M; daily | REJECTED (Sharpe 0.742, MDD −16.55%) | Volatility spike risk; gate not protective enough |
| Overnight/intraday decomposition | H18 | Overnight return sign predicts next-day intraday direction | SPY; daily | REJECTED (Sharpe 0.442, benchmark gate vacuous pre-H33/34) | No persistent overnight→intraday predictive edge |
| Volume-predictive decomposition | H19 | Volume (lagged median) predicts return direction | SPY/QQQ/IWM; daily | REJECTED (Sharpe 0.242, IR −0.880, p satisfied by negative alpha pre-H34) | Volume does not predict direction persistently |
| Order-flow imbalance | H20 | Lee-Ready / trade-volume / market-imbalance predicts returns | SPY/QQQ/IWM + ^VIX; daily | REJECTED (Sharpe −0.156, PF 0.973) | Order-flow signal not persistent after costs |

### Variants / extensions (classes 2–3)

| H-ID | Class | Parent family | Nature of variation |
|---|---|---|---|
| H4 | 3 | TSMOM | Ensemble selection (top-K by train Sharpe) layered on TSMOM |
| H9 | 2 | TSMOM | Intraday frequency + path-dependent exits (ATR trailing, time stop, vol stop) |
| H11 | 2 | TSMOM | Robustness certification (frozen H10 config) |
| H12 | 2 | TSMOM | Selection-bias audit (frozen H10 config) |
| H21 | 2 | TSMOM | Multi-contract basket generalization (5 contracts + equal scaling) |
| H22 | 2 | TSMOM | Vol-targeting gap closed on H21 basket |
| H23 | 2 | TSMOM | Instrument variation: crypto perpetuals instead of futures |
| H25 | 2 | TSMOM | PF-margin repair via vol-targeting expansion + basket prune |

### Audits (class 4)

| H-ID | Audit target | Result |
|---|---|---|
| H13 | H10 PF-margin fragility | REJECT on fragility (95% CI [1.190,1.425], P(PF≥1.3)≈0.62) |
| H14 | H10 selection bias | REJECT (top-50 by Val PF margin all fail) |
| H15 | H10 loss-offset | PROBE (CL=F indispensable; LOO PF 1.273 < 1.3) |
| H26 | Sharpe annualization scale | Infrastructure correction; no verdict change |
| H27 | P&L level / look-ahead | **Invalidated intraday family**; look-ahead in daily collapse |
| H28 | Causal re-certification | CAUSAL_REJECTED for all intraday families (H10/H21/H22/H25) |
| H29 | Look-ahead sweep (all remaining) | Daily families certified clean; no daily family passes |

### Engineering / data-quality / infrastructure repairs (class 5)

H31, H32, H33, H34, H35, H36, H37, H38, H39, H40, H41, H42, H43, H44, H45, H47, H48, H49, H50, H51, H52, H53, H54, H55, H56, H57, H58, H59, H60, H61, H62, H63, H64, H65, H66, H67, H74, H75, H80, H81, H82, H83, H84.

### Replication / post-hoc disclosure (class 6)

H45 (public API export), H47 (trade log cost reconciliation), H49 (validation block re-derivation), H53–H55 (metrics block disclosure), H56–H61 (stats/audit disclosure).

### Unassigned H-IDs

H24, H68–H73, H76–H79 — never assigned; available for future use (next is H85).

### Discriminating experiments remaining

None identified for any root family. All seven root families have been tested on free data with negative or invalidated results. The intraday TSMOM family is the only one that ever passed gates, and it is CAUSAL_REJECTED.

---

## 2. New-family candidates (NF-IDs)

Per directive §4.2: at least three candidates spanning at least three broad mechanism categories. Each is demonstrably different from existing families.

### NF-20261104-01: VIX Term Structure Slope Equity Timing

**Category:** Volatility and convexity premia

**Economic mechanism:** The VIX futures term structure (spot ^VIX vs 3-month ^VIX3M) exhibits persistent contango/backwardation cycles. Steep contango (VIX3M ≫ VIX) implies the market expects rising volatility, but VIX mean-reverts toward fair value; backwardation implies the opposite. Equity returns are negatively correlated with volatility changes, so the slope times equity exposure: long SPY in steep contango (expected vol mean reversion down → equity up), flat/short in backwardation.

**Why it persists:** VIX mean reversion is structurally grounded (volatility is mean-reverting by construction of the VIX calculation); the term structure slope is a forward-looking measure of expected vol vs current vol.

**Observable variables:** ^VIX (spot index, daily close), ^VIX3M (3-month VIX futures, daily close). Both on yfinance, years of free daily history. Slope = VIX3M / VIX. Becomes available at daily close; traded at next day's open (no look-ahead).

**Causal chain:** Slope ↑ (contango) → expected future VIX > current VIX → VIX mean-reversion down → equity vol ↓ → SPY expected return ↑. Position: long SPY. Slope ↓ (backwardation) → inverse.

**Construction:** Daily rebalance at close. If VIX3M/VIX > threshold (contango), long SPY vol-targeted to 15% ann; if < inverse threshold (backwardation), flat or short. Threshold = rolling median slope ± z-score. Max position 0.5 (per equity cost model constraints).

**Null hypothesis:** VIX term structure slope does not predict next-day SPY returns beyond random chance after costs.

**Explicit rejection:** OOS Sharpe < 0.5, profit factor < 1.1, < 200 OOS trades, or max DD > 15%.

**Data source:** yfinance daily: ^VIX, ^VIX3M, SPY. Start 2015-01-01 (VIX3M availability), end protected holdout at final 20%. Point-in-time: all values known at daily close.

**Costs:** Equity model: 1 bp commission + 0.5 bp spread + 0.1 bp impact per 1% ADV. One-way daily turnover ≈ 1× position size.

**Capacity:** SPY is highly liquid; capacity not binding at research scale.

**Closest prior family:** H17 (VRP harvesting on SVXY gated by VIX/VIX3M). **Distinction:** H17 trades SVXY (volatility vehicle) based on spot VIX *level* as a regime filter; NF-01 trades SPY (equity) based on VIX term structure *slope* as a directional timing signal. Different instrument, different signal, different mechanism (volatility-timed equity exposure vs VRP harvesting).

**Confounders / leakage risks:** ^VIX3M may have staleness or settlement quirks; VIX spot is not directly tradable (signal only). Falsification: slope computed with one-day lag must still show predictive power.

---

### NF-20261104-02: Cross-Asset Lead-Lag (Sector → Constituent)

**Category:** Information transmission and lead-lag

**Economic mechanism:** Information diffuses slowly across related assets. Liquid sector ETFs (XLF, XLE, XLV, etc.) react first to sector-specific news; constituent stocks within the sector follow with a delay as information propagates. Prior-day sector ETF return predicts next-day constituent stock returns.

**Why it persists:** Information diffusion is bounded by investor attention and processing speed; not all market participants observe sector moves immediately.

**Observable variables:** Sector ETF daily closes (XLF, XLE, XLV, XLI, XLB, XLP, XLU, XLY, XLC, XLK) and constituent stock daily closes. All on yfinance, years of free daily history. Sector return at t−1 known at close of t−1; constituent trade at close of t.

**Causal chain:** Sector ETF return ↑ at t−1 → sector news arrives → constituent stocks in same sector respond at t (delayed) → long constituents in sectors with positive prior ETF return, short those with negative.

**Construction:** Daily universe: 10 sector ETFs + 20–40 large-cap stocks mapped to sectors. Each day, compute prior-day sector ETF return. Rank stocks within each sector by sector return; long top quintile, short bottom quintile, equal-weighted, vol-targeted to 15% ann. Rebalance daily at close.

**Null:** Sector ETF prior-day return does not predict constituent next-day returns after costs.

**Rejection:** OOS Sharpe < 0.5, PF < 1.1, < 200 OOS trades, max DD > 15%.

**Data:** yfinance daily for sector ETFs and stocks. Start 2015-01-01. Protected holdout: final 20%.

**Costs:** Equity model. Daily turnover ≈ full rebalance (high turnover; cost drag significant).

**Capacity:** Moderate; daily turnover in large-cap stocks is feasible.

**Closest prior family:** H2/H16 (cross-sectional momentum). **Distinction:** H2/H16 rank assets by their *own* past returns (relative strength); NF-02 ranks assets by a *different asset's* prior return (cross-asset lead-lag). Different information source, different causal path.

**Confounders:** Lead-lag may decay as markets become more efficient; sector membership changes (survivorship bias if current membership used). Mitigation: use fixed sector mapping from start of window.

---

### NF-20261104-03: Equity–Futures Basis Mean Reversion

**Category:** Relative value and convergence

**Economic mechanism:** Equity index futures (ES=F) and the underlying ETF (SPY) are linked by cost-of-carry arbitrage. The futures basis (futures price / spot price adjusted for financing and dividends) mean-reverts when it deviates from fair value. Large positive basis (futures rich) predicts futures underperformance vs spot; negative basis predicts outperformance.

**Why it persists:** Arbitrage capital is finite; deviations persist briefly until arburs unwind them.

**Observable variables:** ES=F daily close, SPY daily close. Both on yfinance, years of free daily history. Basis ratio = ES=F / SPY, computed at daily close; trade next day.

**Causal chain:** Basis ≫ rolling mean (futures rich) → short ES, long SPY → basis mean-reverts → profit on spread. Basis ≪ rolling mean → long ES, short SPY → inverse.

**Construction:** Daily rebalance. Compute 60-day rolling mean and std of ES/SPY ratio. If z-score > +2, short futures/long spot; if < −2, long futures/short spot. Position size vol-targeted to 10% ann per leg. Costs on both legs (futures + equity).

**Null:** ES/SPY basis ratio deviation from rolling mean does not predict mean-reverting spread returns after costs.

**Rejection:** OOS Sharpe < 0.5, PF < 1.1, < 200 OOS trades, max DD > 15%.

**Data:** yfinance daily ES=F, SPY. Start 2015-01-01. Protected holdout: final 20%.

**Costs:** Combined futures + equity cost model. Two-legged turnover doubles cost drag.

**Capacity:** Limited by futures contract size and equity liquidity; modest at research scale.

**Closest prior family:** None in repository (no relative-value/pairs family tested). **Distinction:** All prior families are directional (momentum, vol, regime, order-flow); NF-03 is mean-reverting relative value on a basis spread.

**Confounders:** Basis deviations are small at daily frequency; roll costs on ES=F continuous contract; dividend/financing adjustments approximate. Falsification: z-score threshold sweep must show a decaying, not flat, response.

---

## 3. Weighted ranking (per directive §4.3)

Scores 1–5. Weights: novelty 25%, plausibility 25%, data 20%, falsifiability 15%, execution 10%, independent support 5%.

| Criterion | W | NF-01 VIX slope | NF-02 Lead-lag | NF-03 Basis MR |
|---|---|---|---|---|
| Mechanism novelty | 0.25 | 4 | 4 | 3 |
| Economic plausibility | 0.25 | 4 | 4 | 2 |
| Data availability | 0.20 | 5 | 5 | 5 |
| Falsifiability | 0.15 | 4 | 4 | 5 |
| Execution feasibility | 0.10 | 4 | 5 | 3 |
| Independent support | 0.05 | 4 | 4 | 3 |
| **Weighted total** | | **4.15** | **4.20** | **3.35** |

**Selection:** NF-20261104-02 (Cross-Asset Lead-Lag) scores highest (4.20), narrowly ahead of NF-01 (4.15). NF-03 is deferred (3.35) due to low plausibility at daily frequency and high cost drag.

**Rationale:** Lead-lag has the best combination of novelty (not tested in repo), plausibility (well-documented information diffusion), data (all free yfinance daily), falsifiability (clean rank-based test), and execution (daily rebalance, liquid equities). The main risk is cost drag from daily turnover, addressed by vol-targeting and quintile selection.

**Decision:** Implement NF-20261104-02 as the smallest high-information experiment. Pre-register below. Assign next unused H-ID (H85) upon formal registration in HYPOTHESIS_SPEC.md.

---

## 4. Pre-registration: NF-20261104-02 (Cross-Asset Lead-Lag)

**Temporary ID:** NF-20261104-02
**Proposed H-ID:** H85 (pending formal registration)

**Hypothesis:** "When a sector ETF's prior-day return is positive, constituent stocks in that sector exhibit positive next-day returns (and vice versa) because sector-level information diffuses with a delay from ETFs to individual stocks."

**Mechanism:** Information transmission and lead-lag (broad category per directive §4.1).

**Null:** Sector ETF prior-day return has no predictive power for constituent next-day returns beyond random chance after costs.

**Observable:** 10 sector ETF daily closes + mapped constituent stock daily closes, all yfinance. Sector return at t−1 known at close t−1; constituent position established at close t.

**Data:** yfinance daily. Universe: XLF, XLE, XLV, XLI, XLB, XLP, XLU, XLY, XLC, XLK + 40 large-cap stocks mapped to sectors. Window: 2015-01-01 → 2026-10-31. Protected holdout: final 20% (~2024-10 → 2026-10). Train/Val/Test: 60/20/20 by time, no overlap.

**Splits:** Train 2015-01-01 → 2020-12-31, Val 2021-01-01 → 2023-12-31, Test 2024-01-01 → 2024-10-31 (protected holdout, never touched during selection).

**Construction:** Daily at close, rank stocks by prior-day sector ETF return within each sector. Long top quintile, short bottom quintile, equal-weight within quintile, vol-target to 15% ann. Max position 0.25 per name.

**Cost model:** Equity: 1 bp commission + 0.5 bp spread (liquid) + 0.1 bp impact per 1% ADV. Two-way daily turnover ≈ full quintile rebalance.

**Gates (PROMPT_V2.md):** OOS Sharpe ≥ 1.0, ≥200 OOS trades, PF ≥ 1.3, max DD ≤ 15%, WF stability (test Sharpe ≥ 0.7× train), parameter sensitivity (±20% on lookback/quintile).

**Baseline:** Buy-and-hold equal-weight of all universe stocks.

**Multiple testing:** Bonferroni for N parameter combos in grid.

**Compute budget:** < 5 CPU-hours (daily data, small grid).

**Rejection conditions:** OOS Sharpe < 0.5 or PF < 1.1 or < 200 OOS trades or max DD > 15%.

**Not yet implemented.** Implemented 2026-11-05 as **H85**; result **REJECT** — see §6.

---

## 5. Implementation status

| Item | Status |
|---|---|
| Family-lineage map (H1–H84) | Complete |
| 3 candidates from 3 categories | Complete |
| Weighted ranking | Complete |
| NF-02 selected | Complete |
| Pre-registered | Above |
| Experiment runner | Complete (`run_nf_20261104_02_cross_asset_leadlag.py`) |
| Test | Complete (`tests/test_nf_20261104_02_cross_asset_leadlag.py`, 10 tests) |
| Gates (ruff/pytest/coverage) | Green: lint, format, 2308 passed / 16 skipped / 100% coverage |
| HYPOTHESIS_SPEC.md registration (H85) | Registered (§H85) |
| Experiment executed | `exp_2026-11-05T01-24-02-934356Z` — REJECT |

---

## 6. NF-20261104-02 outcome (H85) and next candidate

### Result: REJECT (2/8 gates)

OOS Sharpe = **−1.615**, PF = 0.759, max DD = −47.1%, 50,488 OOS trades, WF stability =
1.445 (passes), perturbation min ratio = 0.000 (fails). Train −2.188 / Val −1.140 /
Test −2.073. Benchmark p = 0.0012, IR = −1.247 — the strategy is significantly *worse*
than the equal-weight buy-and-hold benchmark. Selected config: lookback 21,
quintile_share 0.2, vol_target 0.15.

Ablations: random-quintile control Sharpe −0.657 (the loss is not signal-driven — the
long book is short-gamma to the daily rebalance); long-only top quintile Sharpe +0.373,
PF 1.070; EW benchmark Sharpe +0.900, PF 1.198.

### New root family added to the lineage map

| Root family | H-IDs | Mechanism | Markets / data | Verdict | Known failure mode |
|---|---|---|---|---|---|
| Cross-asset lead-lag (sector ETF → constituent) | H85 | Prior-day sector ETF return predicts next-day constituent returns; information diffuses with a delay | 10 sector ETFs + 40 mapped stocks; daily, yfinance | REJECTED (OOS Sharpe −1.615) | Daily rebalance cost drag dominates; signal worse than EW benchmark (IR −1.247) |

### Integrity defects found and fixed during this experiment (not verdict-affecting)

1. **Look-ahead in the ranking.** The original builder ranked stocks by their *concurrent*
   close[t-1] → close[t] return — the very return the position was about to earn. Fixed
   to rank on the stock's own prior-day return minus the sector's prior-day return.
   Pinned by `test_stock_ranking_uses_only_prior_day_information`.
2. **Pandas column-alignment nullified the signal.** `stock_rets.shift(1) -
   sector_ret_lagged` aligned to an empty intersection (disjoint columns), producing
   all-NaN positions. Fixed by subtracting per-sector inside the loop.
3. **Runner polluted the committed cache.** `fetch_yahoo` wrote 50 untracked parquet
   files into `.cache/data/`, breaking the frozen 82-file baseline the H57 audit pins.
   Fixed: isolated per-experiment cache under the runner's own artifact directory.
4. **Comment substring tripped a tripwire.** A comment mentioning the audit's name
   contained "total_return", flagged by the engine's total-return tripwire scan.
   Reworded.

### Next candidate: NF-20261104-01 (VIX Term Structure Slope Equity Timing)

NF-02 is exhausted. The next-highest ranked candidate is **NF-20261104-01** (weighted
total 4.15, category: volatility and convexity premia), which is materially distinct from
every exhausted family — no prior repository family trades equity exposure timed by the
VIX term-structure slope (H17 trades SVXY gated by the spot VIX *level*). It uses only
free yfinance daily data (^VIX, ^VIX3M, SPY), is single-instrument, has low turnover, and
its falsification is clean. Pre-registered as H86 in HYPOTHESIS_SPEC.md (2026-11-05). Runner not yet implemented; next task is to implement `run_nf_20261104_01_vix_termstructure.py` and focused tests, then run gates.
