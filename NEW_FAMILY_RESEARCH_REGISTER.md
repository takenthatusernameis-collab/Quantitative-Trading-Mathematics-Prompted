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

### NF-20261104-01 outcome (H86) and next candidate

#### Result: REJECT (2/9 gates)

OOS Sharpe = **−0.118**, PF = 0.974, max DD = −19.4%, 594 OOS trades, WF stability =
−3.200 (fails), perturbation min ratio = 0.000 (fails). Train 0.119 / Val 0.117 /
Test −0.373. Benchmark p = 1.0000, IR = −0.478 — strategy does not outperform buy-and-hold SPY.

Selected config: lookback 126, zscore 0.5, vol_target 0.10.

Ablations: long-only Sharpe −0.118, PF 0.974; inverse signal Sharpe +0.118, PF 1.027; SPY benchmark Sharpe +0.828, PF 1.148.

#### New root family added to the lineage map

| Root family | H-IDs | Mechanism | Markets / data | Verdict | Known failure mode |
|---|---|---|---|---|---|
| VIX term structure slope equity timing | H86 | Slope VIX3M/VIX predicts SPY returns via vol mean reversion; long in steep contango, short/flat in backwardation | ^VIX, ^VIX3M, SPY; daily, yfinance | REJECTED (OOS Sharpe −0.118) | Signal weak; inverse performs better than long-side; underperforms SPY benchmark on OOS |

#### Next candidate: none remaining in current ranked set

NF-01 is the second-highest ranked candidate from the initial three (NF-02 done, NF-01 done, NF-03 deferred). No other pre-registered NF candidates remain. Per directive §6, need to search for new mechanisms if queue exhausted. Current state: H1–H30 exhausted, H85/H86 rejected. Next unused H-ID is H87 (H24, H68–H73, H76–H79 unassigned; next sequential unused is H87). Must perform new mechanism search before selecting next experiment.

---

## 7. New-family discovery cycle 2 (2026-11-05) — mechanism search

Queue of pre-registered NF candidates exhausted after H85/H86 rejections. Per directive §4.1 and §6, a fresh mechanism search across new broad categories is required before any further experiment. Three candidates spanning three distinct mechanism categories, none overlapping prior root families (TSMOM, CS-momentum, regime-gated vol, VRP, overnight/intraday, volume-predictive, order-flow, lead-lag, VIX slope timing, basis MR).

### NF-20261105-01: Opening-Gap Fill / Overnight Information (Equity Index)

**Category:** Event / auction mechanisms
**Mechanism:** Overnight price gaps between prior close and next open contain information not yet absorbed by intraday participants; partial gap fill occurs as liquidity returns at the open. Long/short the gap direction with a defined holding period (intraday to next close), mean-reversion of gap.
**Observable:** SPY daily open/close (yfinance). Gap = open[t] - close[t-1]. Signal sign.
**Distinct from:** H18 overnight/intraday decomposition (tested close-to-close sign, not gap-fill holding); H19/H20 volume/order-flow (different information).
**Null:** Gap size does not predict intraday mean-reversion beyond costs.
**Rejection:** OOS Sharpe < 0.5, PF < 1.1, max DD > 15%.
**Data:** yfinance daily SPY 2015→2026, free. Costs: equity model. Capacity: high.
**Scores:** novelty 4, plausibility 3, data 5, falsifiability 5, execution 4, support 3 → weighted 4.05.

### NF-20261105-02: Carry / Term-Structure in Commodity Futures (Roll Yield)

**Category:** Carry and term structure
**Mechanism:** Commodity futures in backwardation earn positive roll yield (carry); in contango earn negative. Long commodities in backwardation, short in contango, rebalanced monthly.
**Observable:** Continuous futures (CL=F, GC=F, ZC=F, etc.) daily settle + front/back month; yfinance limited but free daily front-month available.
**Distinct from:** H17 VRP (volatility, not commodity carry); no prior commodity carry family.
**Null:** Roll-yield signal does not predict next-month returns after costs.
**Rejection:** OOS Sharpe < 0.5, PF < 1.1, max DD > 15%.
**Data:** yfinance daily futures 2015→2026, free; point-in-time monthly rebalance. Costs: futures model. Capacity: moderate.
**Scores:** novelty 4, plausibility 4, data 4, falsifiability 4, execution 3, support 4 → weighted 3.95.

### NF-20261105-03: Liquidity Provision / Reversal on Large Daily Moves

**Category:** Liquidity provision and order-flow effects
**Mechanism:** Extreme daily returns are followed by short-term reversal as liquidity providers absorb order flow and prices revert. Long assets with largest negative daily return, short largest positive, 1-day holding.
**Observable:** Daily returns across a cross-section (ETFs/stocks), yfinance.
**Distinct from:** H2/H16 CS momentum (trend, opposite direction); reversal is a distinct mechanism.
**Null:** Extreme-move reversal does not produce net-of-cost alpha.
**Rejection:** OOS Sharpe < 0.5, PF < 1.1, max DD > 15%.
**Data:** yfinance daily 2015→2026, free. Costs: equity model, high turnover. Capacity: moderate.
**Scores:** novelty 3, plausibility 3, data 5, falsifiability 5, execution 3, support 3 → weighted 3.60.

### Ranking (cycle 2)

| Candidate | Weighted total |
|---|---|
| NF-20261105-01 Opening-gap fill | 4.05 |
| NF-20261105-02 Commodity carry | 3.95 |
| NF-20261105-03 Extreme-move reversal | 3.60 |

**Selection:** NF-20261105-01 (opening-gap fill) scores highest. Pre-register as H87.

## 8. Pre-registration: NF-20261105-01 (Opening-Gap Fill) — H87

**Temporary ID:** NF-20261105-01
**Proposed H-ID:** H87 (pending formal registration in HYPOTHESIS_SPEC.md)

**Hypothesis:** "Overnight gaps in SPY partially fill intraday: a positive gap (open > prior close) is followed by negative intraday return (close < open) and vice versa, because overnight information is overreacted and liquidity returns at the open."

**Mechanism:** Event/auction mechanisms (broad category per directive §4.1).

**Null:** Gap sign/size does not predict intraday return beyond costs.

**Observable:** SPY daily open and close, yfinance, known at close t (open[t], close[t], close[t-1]).

**Data:** yfinance daily SPY, 2015-01-01 → 2026-10-31. Train 2015-01-01→2020-12-31, Val 2021-01-01→2023-12-31, Test 2024-01-01→2026-10-31 (protected holdout final ~20%). Point-in-time: gap computed from close[t-1] and open[t], both known at open[t]; intraday return close[t]/open[t] earned after entry at open.

**Construction:** Daily. Signal = sign(open[t] - close[t-1]) (or z-scored gap). Long SPY if gap negative (expect fill up), short if gap positive (expect fill down), held intraday open→close, vol-targeted to 15% ann. Costs: equity model (1 bp commission + 0.5 bp spread + 0.1 bp impact per 1% ADV). Turnover ~1×/day.

**Grid:** lookback in {1,5,21} for z-score normalization, zscore threshold in {0.0,0.5,1.0}, vol_target in {0.10,0.15,0.20} (27 combos). Selection by train-only walk-forward Sharpe; Test protected.

**Explicit rejection:** OOS Sharpe < 0.5, PF < 1.1, < 200 OOS trades, max DD > 15%.

**Capacity:** SPY highly liquid; not binding.

**Closest prior family:** H18 (overnight/intraday decomposition). **Distinction:** H18 tested whether overnight return sign predicts next-day *intraday* direction (close[t]→close[t+1] style); H87 tests same-day gap fill (open→close) holding intraday only, a distinct timing and holding horizon. Different causal claim (overreaction fill vs overnight information persistence).

**Confounders/leakage:** open prices on yfinance are adjusted for splits/dividends consistently with close; gap computed with no look-ahead (open known at entry). Slippage at open may exceed model; treat as lower bound. Falsification: random-entry control and gap-magnitude monotonicity.

**Next task:** Implement `run_nf_20261105_01_opening_gap.py` + focused tests; formalize H87 in HYPOTHESIS_SPEC.md; run pinned gates. Next unused H-ID after H87 is H88.

---

## 9. NF-20261105-01 outcome (H87) and next candidate

#### Result: REJECT (1/9 gates)

OOS Sharpe = **−0.348**, PF = 0.940, max DD = −40.4%, 0 OOS trades,
WF stability = 0.827 (passes), perturbation min ratio = 0.000 (fails).
Train 0.421 / Val −0.961 / Test 0.348. Benchmark p = 1.0000, IR = −0.577 — strategy does not outperform buy-and-hold SPY.

Selected config: lookback 5, zscore_thresh 0.0, vol_target 0.15.

Ablations: random_entry Sharpe 0.160, PF 1.034; long_only_negative_gaps Sharpe 0.057, PF 1.014; short_only_positive_gaps Sharpe −0.536, PF 0.868; SPY benchmark Sharpe 0.812, PF 1.154.

#### New root family added to the lineage map

| Root family | H-IDs | Mechanism | Markets / data | Verdict | Known failure mode |
|---|---|---|---|---|---|
| Opening-gap fill / overnight information | H87 | Overnight gap sign predicts same-day intraday fill direction; long/short gap direction, open→close holding | SPY daily OHLC; yfinance | REJECTED (OOS Sharpe −0.348) | Zero executable trades after vol targeting; gap information absorbed at open or swamped by costs |

#### Next candidate: new mechanism search required

Per directive §6, H1–H30 exhausted and H85/H86/H87 all rejected. A new mechanism
search across distinct return-generating categories is required before selecting the
next experiment. Next unused H-ID is H88.

## 10. New-family discovery cycle 3 (2026-11-05) — mechanism search

Queue exhausted after H87 (REJECT). Per directive §4.1 and §6, fresh mechanism search across new broad categories required. Three candidates spanning three distinct mechanism categories, checked against the full lineage map (H1–H87): no overlap with TSMOM/trend (H1,H7-12,H21-23,H25), cross-sectional momentum (H2,H16), regime-gated vol-scaled momentum (H3,H5,H6), VRP (H17), overnight/intraday persistence decomposition (H18), volume predictive (H19), order flow (H20), VIX slope equity timing (H86), cross-asset lead-lag sector→stock (H85), or opening-gap fill (H87).

### NF-20261105-04: Commodity Futures Front-Month Roll-Yield Proxy Carry

**Category:** Carry and term structure (distinct broad category).
**Mechanism:** Commodity futures exhibit term-structure carry: backwardation (deferred < front, or negative roll cost) implies positive expected roll yield to long holders; contango implies negative carry. A cross-commodity portfolio long backwardated commodities and flat/short contangoed commodities harvests carry premia driven by storage costs, convenience yield, and hedging pressure (Theory of Storage / hedging-pressure).
**Observable:** Daily continuous front-month prices for liquid commodity futures (CL=F, GC=F, SI=F, HG=F, NG=F, ZC=F, ZS=F, ZW=F) via yfinance. Roll-yield proxy = annualized slope of log-price between front continuous series and a 63-day lagged roll-adjusted proxy, or alternatively the sign of 21-day return momentum of the contango/backwardation state inferred from term slope when second-month data unavailable; *feasibility note*: point-in-time front vs deferred chain construction from yfinance individual contract tickers is operationally complex and may introduce survivorship/roll artifacts — the smallest decisive test must use only continuous front-month with a documented, point-in-time roll proxy and treat contract-construction ambiguity as a rejection risk.
**Null:** Roll-yield/carry proxy does not predict next-month commodity returns after costs.
**Rejection:** OOS Sharpe < 0.5, PF < 1.1, max DD > 15%, < 50 OOS portfolio rebalances.
**Data:** yfinance daily 2010-01-01→2026-10-31 (longer history for carry regimes), free. Monthly rebalance. Costs: futures model. Capacity: moderate (liquid contracts).
**Closest prior family:** H17 VRP (volatility term structure, options/vol vehicle) — different asset class, instrument, and mechanism (commodity storage/convenience yield vs variance risk premium). No prior commodity carry family.
**Scores (1–5):** novelty 4 (repo-new commodity carry), plausibility 4 (established economic basis but crowded/decayed), data 3 (point-in-time roll proxy feasible but noisy with yfinance continuous), falsifiability 4, execution 3 (futures costs/roll), support 4. **Weighted 3.70** (25/25/20/15/10/5).

### NF-20261105-05: Short-Term Cross-Sectional Return Reversal (Liquidity Provision)

**Category:** Liquidity provision and order-flow effects (distinct broad category).
**Mechanism:** Large one-day price moves in liquid equities/ETFs create temporary order imbalances; liquidity providers demand compensation, producing short-horizon reversal as prices revert toward equilibrium. A daily-rebalanced cross-section long recent losers and short recent winners (1-day lookback, 1-day hold) harvests the liquidity premium, opposite in sign to momentum.
**Observable:** Daily close-to-close returns for a liquid, survivorship-managed ETF universe (e.g., SPY sector ETFs XLK,XLF,XLE,XLV,XLI,XLP,XLU,XLB,XLY,XLC plus broad ETFs) via yfinance. All observable at close t for position held t+1.
**Distinct from:** H2/H16 cross-sectional momentum (own-past-return *trend*, multi-day/monthly horizons, opposite direction) — NF-05 is a *reversal* mechanism with 1-day horizon driven by liquidity provision, not relative strength persistence. Different causal path and sign.
**Null:** 1-day cross-sectional reversal does not produce net-of-cost alpha after realistic equity transaction costs.
**Rejection:** OOS Sharpe < 0.5, PF < 1.1, max DD > 15%, < 200 OOS portfolio-days.
**Data:** yfinance daily 2015-01-01→2026-10-31, free. Daily rebalance. Costs: equity model (1 bp commission + 0.5 bp spread + 0.1 bp impact) — high turnover is the key feasibility risk.
**Scores (1–5):** novelty 3 (reversal well-known; repo-new as distinct family vs CS-momentum but mechanism adjacent in literature — scored honestly), plausibility 3 (microstructure effect present but largely arbitraged in liquid ETFs; capacity/decay risk), data 5, falsifiability 5, execution 2 (very high turnover; net-of-cost feasibility is the decisive risk), support 3. **Weighted 3.35**.

### NF-20261105-06: Gold–Oil Relative-Value Spread Mean Reversion

**Category:** Relative value and convergence (distinct broad category).
**Mechanism:** Gold (GC=F/GLD) and crude oil (CL=F/USO) share macro inflation/geopolitical risk exposures but diverge due to supply shocks, demand cycles, and convenience yield. The log-price ratio (or normalized spread) exhibits mean reversion when dislocations exceed transaction-cost bounds, as relative macro pricing corrects. Long the undervalued leg / short the overvalued leg when spread z-score is extreme, targeting convergence.
**Observable:** Daily prices for GC=F and CL=F (or GLD/USO) via yfinance. Spread = log(GC) - β*log(CL), β estimated on rolling train-only window; z-score of spread. All point-in-time.
**Distinct from:** H85 lead-lag (uses *one asset's lagged return* to predict another — directional information transmission). NF-06 uses *contemporaneous spread dislocation* and bets on convergence (mean reversion of a stationary-ish relation), no lead-lag prediction. Different mechanism (relative value/convergence vs information transmission).
**Null:** Extreme gold–oil spread dislocations do not predict spread convergence beyond costs.
**Rejection:** OOS Sharpe < 0.5, PF < 1.1, max DD > 15%, < 50 OOS spread trades, spread non-stationarity (ADF-style diagnostic failure) documented as mechanism failure.
**Data:** yfinance daily 2010-01-01→2026-10-31, free. Daily/weekly evaluation, positions held until convergence or stop. Costs: futures or ETF model. Capacity: high for GC/CL.
**Scores (1–5):** novelty 4 (repo-new relative-value pair), plausibility 3 (economic link exists but cointegration unstable; oil regime shifts break spread), data 5, falsifiability 5, execution 4, support 3. **Weighted 3.95**.

### Ranking (cycle 3)

| Candidate | Mechanism category | Novelty | Plaus | Data | Falsif | Exec | Support | Weighted |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| NF-20261105-06 Gold–oil RV mean reversion | Relative value / convergence | 4 | 3 | 5 | 5 | 4 | 3 | **3.95** |
| NF-20261105-04 Commodity carry (roll proxy) | Carry / term structure | 4 | 4 | 3 | 4 | 3 | 4 | **3.70** |
| NF-20261105-05 Short-term CS reversal | Liquidity provision / order-flow | 3 | 3 | 5 | 5 | 2 | 3 | **3.35** |

**Selection:** NF-20261105-06 (Gold–oil relative-value spread mean reversion) ranks highest. It has a clean, point-in-time observable (two liquid prices), strong falsifiability, and no data-construction ambiguity comparable to NF-04's roll proxy. NF-05's decisive risk is net-of-cost viability under daily turnover in liquid ETFs — a valid but lower-expected-information first test given execution score 2. NF-04 remains credible but deferred behind NF-06 due to yfinance roll-proxy feasibility risk; revisit if NF-06 rejects and a point-in-time roll construction is specified.

## 11. Pre-registration: NF-20261105-06 (Gold–Oil Relative-Value Mean Reversion) — H88

**Temporary ID:** NF-20261105-06
**Proposed H-ID:** H88 (pending formal registration in HYPOTHESIS_SPEC.md)

**Hypothesis:** "The log-price spread between gold and crude oil mean-reverts when dislocated: extreme positive spread z-scores (gold rich vs oil) predict negative spread returns (short gold/long oil convergence) and vice versa, after transaction costs."

**Mechanism:** Relative value and convergence (broad category per directive §4.1).

**Null:** Spread z-score does not predict next-period spread change beyond costs; spread is non-stationary or dislocations are not exploitable net of costs.

**Observables (all point-in-time):** GC=F (COMEX gold front continuous) and CL=F (NYMEX WTI front continuous) daily close, yfinance. Spread `s_t = log(GC_t) - log(CL_t)` (unit hedge ratio fixed for simplicity in baseline; hedge-ratio grid variant documented). Signal = rolling z-score of `s_t` over lookback `L`, computed using only data through t.

**Data:** yfinance daily 2010-01-01→2026-10-31, free/public. Splits: train 2010-01-01→2018-12-31, val 2019-01-01→2022-12-31, test (protected holdout) 2023-01-01→2026-10-31 (~32% holdout by time; protected — no feedback into selection). Point-in-time: z-score uses trailing window ending at t; position entered t+1 close-to-close (or next day) — no look-ahead.

**Construction:** Daily signal evaluation. Long spread (long GC, short CL, dollar-neutral by notional) when z < -entry_z; short spread when z > +entry_z; flat when |z| < exit_z. Vol-target spread returns to 10% ann. Costs: futures model per leg (conservative; document params). Max 1 spread unit.

**Grid (train-only selection):** lookback L ∈ {60, 120, 252}, entry_z ∈ {1.5, 2.0, 2.5}, exit_z ∈ {0.5, 0.75} (18 combos). Selection by train walk-forward Sharpe; val for sanity; test protected final.

**Metrics/gates:** Sharpe, PF, max DD, trade count, perturbation sensitivity (OAT ±20% on L/entry_z), benchmark comparison vs equal-weight GC/CL buy-hold (direction-aware gate), train/val/test stability. **Rejection:** OOS Sharpe < 0.5, PF < 1.1, max DD > 15%, < 30 OOS trades, or perturbation instability indicating selection artifact.

**Capacity/constraints:** GC/CL highly liquid; daily/weekly holding; capacity not binding at research scale. Spread can diverge in oil supply shocks (2014, 2020) — regime fragility is an explicit falsification risk.

**Closest prior family:** H85 (cross-asset lead-lag). **Distinction:** H85 predicts target returns from *lagged leader* returns (directional information transmission). H88 trades *mean reversion of a contemporaneous price ratio* with symmetric long/short convergence; no lead-lag predictor, no directional equity bet — relative value/convergence mechanism.

**Confounders/leakage:** Continuous futures roll adjustments in yfinance data may affect spread level; use consistent adjusted closes and document. Hedge ratio fixed at 1.0 in baseline (log-ratio) avoids look-ahead beta estimation; rolling-beta variant only if train-only. No survivorship in futures continuous series beyond yfinance conventions — disclose.

**Falsification:** (1) Randomized entry control; (2) spread stationarity diagnostic reported (not a gate, but mechanism evidence); (3) subperiod stability including 2020 oil shock.

**Next task:** Formalize H88 in HYPOTHESIS_SPEC.md; implement `run_nf_20261105_06_gold_oil_rv.py` + focused tests; run lint/format + NF tests; run pinned src/qtr gates if `src/qtr` touched (not expected). Execute experiment only if hypothesis is decision-ready and data fetch feasible in-session; otherwise produce decision-ready implementation + tests and leave execution as next task with evidence. Next unused H-ID after H88 is H89.

## 12. NF-20261105-06 / H88 execution outcome — BLOCKED (GC=F/CL=F) → REJECTED (GLD/USO amended, option b)

**Original attempt (blocked):** `exp_2026-11-05T12-16-14-717827Z` (`nf_20261105_06_gold_oil_rv`, git `e5e871fde002`, `git_dirty=false` at start). GC=F/CL=F daily 2010-01-01→2026-10-31 fetched to isolated cache; `DataFetcher._reject_non_positive_prices` raised before any grid/gate evaluation: `CL=F: 4 non-positive price(s)... first np.float64(-14.0) on 2020-04-21 00:00:00` (WTI negative-settlement episode). Status `failed`. **Not evaluated:** grid, OOS metrics, gates, verdict. **Protected holdout not used.** Blocked ≠ rejected.

**2026-11-05 amendment (option b, recorded before outcome evaluation; no protected-test feedback):** Re-specified observables to GLD/USO ETF proxies (verified clean 2026-11-05: 4233 rows each, 0 non-positive, 2010-01-01→2026-10-31). Same sample window/splits/holdout (train 2010-2018, val 2019-2022, test 2023-2026). **Material construction change disclosed:** ETF basis/expense/roll-tracking (especially USO) and equity cost model (`AssetClass.EQUITY`, `CostModel` defaults) replace futures continuous-front-month/tick costs. Mechanism unchanged (relative-value spread mean reversion).

**Amended execution (verified):** `exp_2026-11-05T12-24-33-350043Z` (`nf_20261105_06_gold_oil_rv`, completed, 2026-11-05T12:24:33Z). Command: `PYTHONPATH=src python run_nf_20261105_06_gold_oil_rv.py`. Prices (4233,2), train/val/test 2264/1008/961. Grid 18 (5.0s). Spread diagnostic: n=4233, acf1=0.999231, ar1=0.999288 (high persistence; mechanism-evidence concern, not a gate). Summary artifact: `.experiments/artifacts/exp_2026-11-05T12-24-33-350043Z/summary.json`.

**Selected (train-only WF Sharpe):** lookback=252, entry_z=2.0, exit_z=0.75.

**OOS (Val+Test, 1969 periods, 1766 trades):** Sharpe −0.535, PF 0.866, max DD −34.53%, WF stability 0.000 (train Sharpe −0.278, val −0.666, test −0.395). Benchmark (equal-weight GLD/USO buy-hold) p=0.0872, IR −0.417 (gate fails). Perturbation min ratio 0.000 (fails). Worst regime Sharpe −0.666.

**Ablations:** random_entry Sharpe 0.256, PF 1.056, 2644 trades; gold_oil_equal_benchmark Sharpe 0.740, PF 1.142.

**Gates:** 1/9 passed (trades only). Verdict **REJECT**. Protected holdout was evaluated only as part of the pre-registered OOS (Val+Test) gate set after the amendment was recorded and runner executed — no holdout feedback used in re-specification or selection.

**Lineage map update:**

| Root family | H-IDs | Mechanism | Markets / data | Verdict | Known failure mode |
|---|---|---|---|---|---|
| Gold–oil relative-value spread mean reversion | H88 (NF-20261105-06) | Log(GOLD/OIL) z-score dislocation mean reversion; long/short spread, vol-targeted | GLD/USO daily ETF proxy (yfinance), amended 2026-11-05 from GC=F/CL=F | **REJECTED** (1/9; OOS Sharpe −0.535, PF 0.866, DD −34.5%, WF 0, pert 0) | Spread highly persistent (acf1≈0.999); convergence not realized net of costs; USO ETF roll/tracking basis may distort oil leg; original CL=F futures blocked by non-positive 2020-04-21 bar |

**Next candidate decision (directive §6):** H88 rejected under amended ETF-proxy construction. NF-20261105-04 (commodity carry, roll-proxy point-in-time risk) and NF-20261105-05 (short-term CS reversal, high turnover/net-of-cost risk) remain deferred from cycle 3. Next unused H-ID is H89. New mechanism search/decision-ready selection required before implementation.


## 13. New-family discovery cycle 4 (2026-11-05) — H89 selection (post H88 REJECT)

H85–H88 rejected (H88: GLD/USO amended, 1/9, exp `exp_2026-11-05T12-24-33-350043Z`; original GC=F/CL=F blocked by CL=F non-positive 2020-04-21). Per directive §4/§6, reassess deferred candidates with decisive-risk evidence, add a third materially distinct mechanism, rank, and pre-register/select H89.

### Decisive-risk reassessment (evidenced)

**NF-20261105-04 (commodity carry, roll proxy) — remains DEFERRED (decisive risk unresolved).** Evidence (2026-11-05): yfinance in current pipeline provides continuous front-month futures and ETFs; no free point-in-time deferred/term-structure/second-month series is available through `DataFetcher.fetch_yahoo/fetch_futures`. CL=F continuous shows a non-positive bar in 2012–2026 direct check (`rows=3729, nonpos=1`), consistent with fail-closed `_reject_non_positive_prices` behavior observed in H88's CL=F window; GC/SI/HG/NG/ZC/ZS/ZW continuous had 0 non-positive in that spot check but carry measurement still requires a documented point-in-time term slope/roll proxy. Constructing carry from continuous-only series requires splice/roll assumptions that were not pre-specified as point-in-time and can leak roll/regime artifacts. ETF proxies (DBC/USO/GLD) embed roll/flows/equity-beta confounds and do not provide a clean commodity term-structure carry observable. **Blocker:** data/point-in-time construction for term structure; do not execute without an explicitly pre-registered, point-in-time roll-proxy design.

**NF-20261105-05 (short-term cross-sectional reversal, liquidity provision) — remains DEFERRED (net-of-cost decisive risk unresolved).** Evidence (2026-11-05): liquid sector-ETF universe (SPY, XLK, XLF, XLE, XLV, XLI, XLP, XLU, XLB, XLY, XLC) is free/point-in-time feasible (XLC shorter history but others full 2015–2026; no non-positive). Mechanism is repo-new as a *reversal* family distinct from H2/H16 CS momentum, but the decisive risk is unchanged: 1-day holding with daily cross-sectional rebalancing implies very high turnover. Under `CostModel` equity defaults (commission ~1 bps + spread ~1 bps + impact per side), round-trip/allocation churn can dominate expected microstructure alpha in liquid ETFs. Any turnover cap, entry threshold, or lower rebalance frequency is a design choice that materially changes the mechanism and must be pre-registered before execution; it cannot be tuned post hoc. **Blocker:** execution/net-of-cost realism under pre-registered turnover assumptions.

### NF-20261105-07 (third candidate): CBOE SKEW tail-risk regime equity timing — H89 pre-registration target

**Category:** Volatility/convexity premia — option-implied tail/distribution asymmetry (distinct broad signal dimension from VIX level/slope). Spans a different mechanism category emphasis than deferred NF-04/NF-05.
**Mechanism:** CBOE SKEW (`^SKEW`) measures the implied skewness/tail risk of the S&P 500 return distribution from OTM option prices. Elevated SKEW indicates richer pricing of downside tail protection (crashophobia/hedging demand) relative to ATM volatility; low SKEW indicates complacent tail pricing. The strategy uses SKEW's trailing z-score as a *regime* signal for SPY exposure: reduce or invert equity exposure when tail-risk pricing is unusually elevated (risk-off regime) and allow normal/targeted long exposure when tail pricing is not stressed, harvesting the equity risk premium in non-tail-stress regimes while avoiding fragile periods. Causal path: observable option-implied tail premium at close t → position for t+1.
**Distinct from prior families:** H86 (VIX term structure *slope* VIX3M/VIX equity timing) uses ATM vol term structure/contango; H17 (VRP) trades SVXY gated by VIX *level*/contango; H3/H5/H6 gate momentum by VIX level/regime. NF-07 uses a different observable (`^SKEW`, implied skewness/tail shape) and a different mechanism (tail-risk premium/complacency regime) on a different option-surface dimension. Instrument overlaps H86 (SPY) but signal and mechanism differ; novelty scored honestly below a wholly new instrument.
**Observables (point-in-time):** `^SKEW` and `SPY` daily close via yfinance/`DataFetcher.fetch_yahoo`. Verified 2026-11-05: `^SKEW` 2918 rows 2015–2026, no non-positive; SPY 2975 rows; aligned overlap 2918 rows; SKEW range ~110–183.
**Null:** Trailing SKEW regime does not improve SPY risk-adjusted returns net of costs relative to buy-and-hold SPY.
**Rejection (pre-registered for H89):** OOS Sharpe < 0.5, PF < 1.1, max DD > 15%, < 200 OOS trades, or fails pre-registered PROMPT_V2-style gates applied to OOS Val+Test.
**Data/splits:** 2015-01-01→2026-10-31, train 2015-01-01→2019-12-31, val 2020-01-01→2022-12-31, test 2023-01-01→2026-10-31 (protected holdout). Free/public. Equity costs via `CostModel`/`AssetClass.EQUITY`.
**Feasibility:** Small grid (48 valid combos), daily, two symbols, no `src/qtr` change expected. Capacity high (SPY). Key risk: SKEW is widely followed; signal may be weak/unstable or direction ambiguous — addressed by pre-registering direction and falsifiers.

### Ranking (cycle 4, 1–5)

| Candidate | Mechanism category | Novelty | Plaus | Data | Falsif | Exec | Support | Weighted |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| NF-20261105-07 SKEW tail-risk timing (H89) | Vol/convexity premia (implied tail/skew) | 3 | 3 | 5 | 5 | 5 | 3 | **3.80** |
| NF-20261105-05 Short-term CS reversal | Liquidity provision / order-flow | 3 | 3 | 5 | 5 | 2 | 3 | **3.35** |
| NF-20261105-04 Commodity carry (roll proxy) | Carry / term structure | 4 | 4 | 2 | 4 | 3 | 4 | **3.35** |

Scoring notes: NF-07 novelty reduced because instrument (SPY timing) overlaps H86; signal/mechanism are distinct but adjacent to prior VIX-family work. NF-04 data/execution reduced to 2/3 due evidenced point-in-time term-structure/roll-proxy gap and CL=F non-positive history. NF-05 execution remains 2 due decisive turnover/net-of-cost risk. No novelty/plausibility inflation; NF-07 selected as highest *expected-information feasible* free-data test.

**Selection:** **NF-20261105-07 → H89** (smallest decisive test, clean point-in-time observables, no `src/qtr` change). NF-04/NF-05 remain deferred until decisive risks are explicitly pre-registered and evidenced.

## 14. NF-20261105-07 / H89 execution outcome (2026-11-05) — REJECTED (4/9)

**H89 executed:** `exp_2026-11-05T12-36-06-158635Z` (`nf_20261105_07_skew_tail_timing`, completed). Command: `PYTHONPATH=src python run_nf_20261105_07_skew_tail_timing.py`. `^SKEW`/`SPY` daily 2015-01-01→2026-10-31 (2918 aligned rows), train/val/test 1241/743/934, grid 48 (5.1s). Selected (train-only WF): lookback=63, entry_z=0.5, exit_z=-0.5, vol_target=0.10.

**OOS (Val+Test):** Sharpe 0.524, PF 1.140, max DD −8.53%, trades 368, WF stability 1.800 (train 0.427, val 0.309, test 0.768), worst-regime rolling-252 Sharpe −0.623, benchmark p=1.000 / IR −0.634 vs buy-hold SPY (Sharpe 0.735), perturbation min ratio 0.746. Ablations: random-state Sharpe −0.371/PF 0.913; inverse-threshold ablation produced 0 OOS trades under long/flat construction (recorded). Gates **4/9 pass** (trades, max DD, WF stability, perturbation). Verdict **REJECT**.

**Protected holdout:** used only in pre-registered OOS (Val+Test) gate evaluation after selection; no holdout feedback in discovery/selection/implementation.

**Verification (this session):** `python -m ruff check run_nf_20261105_07_skew_tail_timing.py tests/test_nf_20261105_07_skew_tail_timing.py` and global `python -m ruff check src tests run_*.py` → All checks passed. `python -m ruff format --check src tests run_*.py` → 115 files already formatted. `PYTHONPATH=src python -m pytest tests/test_nf_20261105_07_skew_tail_timing.py -q` → **10 passed**. `src/qtr` not modified; full pinned coverage/`-W error` suite not re-run.

**Lineage update:**

| Root family | H-IDs | Mechanism | Markets / data | Verdict | Known failure mode |
|---|---|---|---|---|---|
| CBOE SKEW tail-risk regime equity timing | H89 (NF-20261105-07) | Trailing `^SKEW` z-score long/flat SPY timing (tail-risk/complacency regime), causal 1-bar delay, vol-targeted | `^SKEW`, SPY daily (yfinance), 2015–2026 | **REJECTED** (4/9; OOS Sharpe 0.524, PF 1.140, bench p=1.000/IR −0.634, worst-regime −0.623) | SKEW regime not additive vs buy-hold SPY net of gates; risk-off gating reduces DD but underperforms benchmark; tail signal may be crowded/collinear with broader vol stress |

**Next candidate decision (directive §6):** H85–H89 rejected. NF-20261105-04 and NF-20261105-05 remain deferred with decisive risks documented (NF-04 point-in-time term-structure/roll proxy unavailable in current free pipeline; NF-05 turnover/net-of-cost under pre-registered daily CS reversal). Next unused H-ID **H90**. New mechanism search must propose at least a third candidate if NF-04/NF-05 remain infeasible; prefer a small, free, point-in-time test in a materially distinct category (e.g., event/auction/calendar-seasonality with pre-registered ex-ante dates — checked for novelty; or bond/equity cross-asset risk-premium signal distinct from H86/VIX families; or volume/dispersion observable with clear mechanism). Do not execute NF-04/NF-05 without resolving decisive risks in a pre-registered, point-in-time design.

## NF-20261105-08 / H90 — FOMC announcement event drift (EXECUTED 2026-11-05, REJECTED 1/9)

- **Category:** Event/auction (pre-scheduled macro calendar).
- **Mechanism:** Post-FOMC statement event-window drift on SPY (long/flat), ex-ante calendar.
- **Decision-ready evidence (resolving blockers):** Federal Reserve Board public FOMC statement dates hardcoded/audited (96 dates, 2015–2026-10-31, includes 2020 emergency meetings). Causal timing: calendar match day t -> exposure days t+1..t+hold_days (1-bar delay), vol-targeted from trailing realized vol. Costs via daily engine defaults; turnover concentrated (110 OOS trades).
- **Implementation:** `run_nf_20261105_08_fomc_event_drift.py`, `tests/test_nf_20261105_08_fomc_event_drift.py` (9 tests). Lint/format clean; focused NF-07/08 tests 19 passed.
- **Experiment:** `exp_2026-11-05T13-22-09-693533Z` (completed). Grid 32 (hold_days/vix_gate/vol_target). Selected 1d hold, no VIX gate, 10% vol target.
- **OOS metrics (Val+Test):** Sharpe -0.633, PF 0.582, maxDD -6.57%, trades 110, WF stability 0, bench p 1.0, IR -0.859, worst-regime -2.268, perturbation min ratio 0. Passes 1/9 (max_drawdown only). Train/Val/Test Sharpe -0.872/-0.886/-0.379. Ablations: SPY benchmark 0.727; random event dates -0.353; no-VIX-gate same.
- **Verdict:** REJECT. Mechanism does not show positive OOS event drift after costs in this pre-registered design; negative edge across Train/Val/Test.
- **Next:** Do not re-optimize same family without a materially different, pre-registered mechanism (e.g., intraday post-announcement window with point-in-time timestamps — only if free/causal data available; not a parameter tweak). Continue new-family discovery.

## Cycle 5 (2026-11-05) — post-H90 mechanism search → NF-20261105-09 / H91 selection

H85–H90 rejected (H90 FOMC event drift 1/9). NF-20261105-04 (commodity carry roll proxy) and NF-20261105-05 (short-term CS reversal) remain deferred with decisive risks documented (NF-04: point-in-time term-structure/roll proxy unavailable in the free pipeline; NF-05: daily turnover/net-of-cost under pre-registered CS reversal). Per directive §4/§6, a fresh mechanism search across new broad categories was required. Three candidates spanning three distinct mechanism categories, checked against the full lineage map (H1–H90), no overlap with any exhausted root family:

| Candidate | Mechanism category | Novelty | Plaus | Data | Falsif | Exec | Support | Weighted |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| NF-20261105-09 Turn-of-month equity seasonality (SPY) | Calendar-seasonality / supply-flow constraints | 4 | 4 | 5 | 5 | 5 | 3 | **4.15** |
| NF-20261105-10 Cross-sectional return dispersion (equity) | Dispersion / cross-section risk premium | 3 | 3 | 5 | 4 | 4 | 3 | 3.35 |
| NF-20261105-11 Treasury term-spread regime timing | Bond/equity cross-asset risk premium | 3 | 3 | 3 | 4 | 3 | 3 | 3.25 |

**Selection:** NF-20261105-09 (turn-of-month equity seasonality) scores highest (4.15). It is the smallest decisive test: single symbol SPY, fixed ex-ante calendar rule (no parameter search on price), low turnover, clean falsification, no `src/qtr` change. Pre-registered as H91. NF-010/NF-011 remain deferred pending decisive-risk resolution.

### NF-20261105-09 / H91 — Turn-of-month equity seasonality (pre-registered; execution pending)

**Temporary lineage ID:** NF-20261105-09. **Proposed H-ID:** H91 (next unused after H90).

**Statement.** Recurring turn-of-month liquidity/flow effects (pension contributions, index rebalancing, window dressing) elevate equity returns around month boundaries. Vol-targeted long SPY during the ex-ante turn-of-month window (last trading day of month m + first `head_days` trading days of month m+1), flat otherwise, clears the PROMPT_V2 gates on OOS Val+Test.

**Mechanism / causal chain.** Month membership and within-month trading-day rank are calendar-known at close t; `build_turn_window_mask` derives membership from the DatetimeIndex alone (last trading day of month m OR first `head_days` trading days of month m+1). Engine applies `signals.shift(1)`: target at close t earns return t→t+1 — strictly causal, no same-day look-ahead. Vol target scales by trailing 21-day realized SPY vol (past-only), capped at `MAX_POS=0.5`, long-only. New family dimension: calendar-seasonality / supply-flow constraints — distinct from all exhausted families.

**Null (H0).** Turn-of-month window membership has no predictive power for next-day SPY returns beyond random chance after costs.

**Universe / data (free).** SPY daily adjusted close via `DataFetcher.fetch_yahoo`, 2010-01-01→2026-10-31; SPY verified clean (no non-positive prices). Single instrument; SPY capacity not binding.

**Splits (pre-registered, protected holdout).** Train 2010-01-01→2019-12-31; Val 2020-01-01→2022-12-31; Test (protected) 2023-01-01→2026-10-31. Selection = train-only 4-fold walk-forward Sharpe; gates on OOS Val+Test; no holdout feedback.

**Costs / constraints.** `AssetClass.EQUITY`, `CostModel` defaults, daily bar engine, max position 0.5, long-only, low month-turn turnover.

**Grid.** `head_days ∈ {1,2,3,4,5}` × `tail=1` (fixed) × `vol_target ∈ {0.10,0.15}` = 10 combos. Selection by train-only WF Sharpe; Test protected.

**Gates (OOS Val+Test).** Sharpe ≥ 1.0, ≥ 200 trades, PF ≥ 1.3, max DD ≤ 15%, WF stability ≥ 0.7×train, worst-regime rolling-252 Sharpe ≥ 0.3, benchmark p ≤ 0.05 vs buy-hold SPY, IR ≥ 0, perturbation min ratio ≥ 0.5 (OAT ±20% on head_days/vol_target).

**Rejection.** OOS Sharpe < 0.5, PF < 1.1, < 200 OOS trades, max DD > 15%, or perturbation/benchmark failure. No gate weakening.

**Runner.** `run_nf_20261105_09_turn_of_month.py` (written, execution pending). Isolated per-experiment cache, grid + WF selection, gate evaluation, perturbation eval, ablations (random-window same-frequency, always-flat, SPY benchmark), artifact + summary.json logging. Deterministic seed 42; compute budget ≤ 2 CPU-h (expected << 1 min).

**Closest prior family / distinction.** H87 (opening-gap fill) and H90 (FOMC event drift) are event/auction families but condition on price gaps or scheduled macro dates, not recurring monthly calendar membership. H18 conditions on returns. H91 is mechanism-distinct: ex-ante calendar month boundaries only.

**Falsifiers.** Random-window ablation matched on window-day frequency; always-flat ablation; SPY buy-hold benchmark; perturbation min ratio; subperiod stability (Val vs Test).

**Status.** Runner + focused tests written; lint/format clean; focused tests 8/8 passed; experiment executed `exp_2026-11-05T13-32-55-648939Z` (2026-11-05). **Verdict: REJECT (3/9 gates)** — OOS Sharpe 0.784 (<1.0), PF 1.296 (<1.3), trades 190 (<200); passes max_drawdown, walkforward_stability, perturbation. Pre-registration recorded in HYPOTHESIS_SPEC.md §H91 and this register cycle 5.

**Lineage map update (H91 REJECT):**

| Root family | H-IDs | Mechanism | Markets / data | Verdict | Known failure mode |
|---|---|---|---|---|---|
| Turn-of-month equity seasonality | H91 (NF-20261105-09) | Vol-targeted long SPY during ex-ante turn-of-month window (last trading day of month m + first head_days days of month m+1); calendar-seasonality / supply-flow constraints | SPY daily (yfinance), 2010–2026 | **REJECTED** (3/9; OOS Sharpe 0.784, PF 1.296, DD −9.4%, trades 190) | Calendar anomaly weak/crowded after costs; train→OOS decay; underperforms SPY benchmark (IR −0.639) |


## Cycle 6 (2026-11-05) — post-H91 mechanism search → NF-20261105-10 / H92 selection

H85–H91 rejected (H91 turn-of-month 3/9, `exp_2026-11-05T13-32-55-648939Z`). NF-20261105-04 (commodity carry roll proxy) and NF-20261105-05 (short-term CS reversal) remain deferred with decisive risks documented (NF-04: point-in-time term-structure/roll proxy unavailable in free pipeline; NF-05: daily turnover/net-of-cost under pre-registered CS reversal). NF-20261105-11 (Treasury term-spread regime timing) was deferred in cycle 5 pending data/mechanism separation from H86/VIX families. Per directive §4/§6, a bounded mechanism search selected NF-20261105-10 (cross-asset risk premium / equity-bond relative momentum) as a decision-ready, free, point-in-time test in a materially distinct category.

### Candidates considered (cycle 6, scored honestly)

| Candidate | Mechanism category | Novelty | Plaus | Data | Falsif | Exec | Support | Weighted |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| NF-20261105-10 Equity/bond relative-momentum timing (H92) | Cross-asset risk premium / relative momentum | 4 | 3 | 5 | 5 | 5 | 3 | **4.05** |
| NF-20261105-11 Treasury term-spread regime timing | Bond/equity cross-asset risk premium (rates level/slope) | 3 | 3 | 3 | 4 | 3 | 3 | 3.25 |
| NF-20261105-12 Cross-sectional equity dispersion regime | Dispersion / cross-section risk premium | 3 | 3 | 5 | 4 | 3 | 3 | 3.40 |

**Selection:** NF-20261105-10 (H92). Smallest decisive test: 2 symbols (SPY, TLT), daily, free yfinance, 16-combo grid, no `src/qtr` change. Distinct from H86/H89 (vol-surface/option-skew signals on SPY), H91 (calendar), H2/H16 (equity-only cross-sectional own-return ranking). NF-11 deferred (free term-spread data quality/point-in-time construction needs explicit pre-registration; mechanism adjacency to macro/rates regime requires careful separation). NF-12 deferred (dispersion measurement/portfolio construction more complex; execution/turnover risk similar to CS strategies).

### NF-20261105-10 / H92 — Equity/bond relative-momentum risk-premium timing

**Temporary lineage ID:** NF-20261105-10. **H-ID:** H92 (next unused).

**Mechanism.** Cross-asset risk premium / relative momentum. Trailing SPY cumulative return minus TLT cumulative return over lookback; positive relmom → long SPY (vol-targeted), negative → flat (long-only) or short (if `allow_short`). Causal: uses prices through close t; engine `shift(1)` earns t→t+1.

**Data/splits.** SPY+TLT daily 2010-01-01→2026-10-31, train 2010–2019, val 2020–2022, test 2023–2026 (protected). Grid 16 (lookback × vol_target × allow_short). Gates: PROMPT_V2 standard on OOS Val+Test.

**Implementation status (2026-11-05).** Runner `run_nf_20261105_10_equity_bond_relmom.py` completed (was committed incomplete in 0c0cabe; `main()` added this session). Tests `tests/test_nf_20261105_10_equity_bond_relmom.py` (10 tests) pass. Lint/format clean for runner+tests and global `src tests run_*.py`. `src/qtr` unchanged. Pre-registered in `HYPOTHESIS_SPEC.md` §H92.

**Execution status.** **Not yet executed in this session** (bounded session; execution requires yfinance data fetch and grid backtests). Next task: run `PYTHONPATH=src python run_nf_20261105_10_equity_bond_relmom.py`, record experiment ID/artifact, evaluate gates, update HYPOTHESIS_SPEC.md and this register with verdict (PASS/REJECT) and lineage map entry. Do not treat non-execution as a verdict.

**Lineage map (provisional, pending execution):**

| Root family | H-IDs | Mechanism | Markets / data | Verdict | Known failure mode |
|---|---|---|---|---|---|
| Equity/bond relative-momentum risk-premium timing | H92 (NF-20261105-10) | Trailing SPY-vs-TLT relative momentum; vol-targeted SPY long/flat(/short) | SPY, TLT daily (yfinance), 2010–2026 | **PENDING** | Equity-bond correlation regime shifts (inflation shocks) can break persistence; crowded cross-asset momentum |
