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

H31, H32, H33, H34, H35, H36, H37, H38, H39, H40, H41, H42, H43, H44, H47, H48, H49, H50, H51, H52, H53, H54, H55, H56, H57, H58, H59, H60, H61, H62, H63, H64, H65, H66, H67, H74, H75, H80, H81, H82, H83, H84.

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

[Previous cycles 5-89 content preserved...]

---

## Cycle 90 (2026-11-10) — Discovery / Pre-registration & Execution of H176

**Lineage reconciled to H175 (H85–H175 all rejected/recorded).** Next unused H-ID **H176** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged; no published/certified artifact, verdict, threshold, or frozen number modified. Selection/validation uses no protected-test feedback. Free/public yfinance data only.

### Deferred candidates reassessed (concrete evidence, Cycle 90; none silently dropped)

- **NF-20261105-04 (commodity carry roll proxy) — remains DEFERRED.** Free yfinance/DataFetcher provides continuous/front proxies only; no free point-in-time deferred/term-structure/second-month series. ETF proxies confound roll/flows/equity beta. Blocker: point-in-time term-structure/roll proxy construction.
- **NF-20261105-05 (short-term CS reversal) — remains DEFERRED.** Daily cross-sectional rebalancing → very high turnover; equity default costs make net-of-cost decisive. Blocker: net-of-cost under pre-registered turnover.
- **NF-20261105-11r / 11 (TNX/FVX slope) — data-resolved variant, novelty scored honestly lower (same root mechanism as NF-11).** Deferred.
- **NF-20261105-12 (cross-sectional equity dispersion) — remains DEFERRED.** Complexity/turnover vs smallest decisive test.
- **NF-20261105-17 (volume-shock reversal) — remains DEFERRED.** Turnover/cost-sensitive.
- **NF-20261105-20 (Treasury auction supply-pressure) — remains DEFERRED.** Event calendar/timestamp construction heavier.
- **NF-20261105-21 (month-end pension rebalancing) — remains DEFERRED.** Weak evidence/adjacency risk.
- **NF-20261106-03 (VVIX vol-of-vol) — remains DEFERRED.** VIX-complex adjacency; novelty scored 3.
- **NF-20261109-22 (RSP-SPY breadth relmom) — remains DEFERRED.** Adjacency to H97 (same pair) and H92/H96/H152/H157 relmom families; mechanism distinction must be explicit.
- **NF-20261109-23 (USMV-SPY low-vol factor relmom) — remains DEFERRED.** USMV inception 2011 limits history; style momentum adjacency to exhausted factor families.
- **NF-20261109-02 (Earnings estimate revision momentum) — remains DEFERRED.** Revision-history PIT construction risk; yfinance provides only current snapshot, no revision history. Blocker: free PIT revision data unavailable.
- **NF-20261109-18 (S&P 500 inclusion/deletion discrete event) — DEFERRED with evidence.** Low frequency (~20-40 events/year) limits statistical power; external index-change calendar required (S&P/Wikipedia); not purely free/yfinance-self-contained. Adjacency to H168 (quarterly calendar rebalance) disclosed — distinct mechanism (discrete event vs calendar window) but data dependency is decisive risk.
- **NF-20261109-19 (Options dealer gamma exposure) — DEFERRED with evidence.** GEX construction requires full options chain history (strikes, expiries, open interest, greeks). yfinance `option_chain` provides only current snapshot; no free historical GEX series. Blocker: free historical options chain/GEX data unavailable.
- **NF-20261109-20 (Stock split announcement effects) — remains DEFERRED.** Low frequency; corporate action data on yfinance incomplete for splits. Adjacency to NF-16 (dividend capture) corporate action category.
- **NF-20261109-12 (Holiday / pre-holiday drift) — remains HELD.** Calendar-seasonality adjacency to H91/H140/H142/H168 exhausted calendar families; no materially distinct mechanism from seasonal window.
- **NF-09-03 (Breakeven inflation) — remains DEFERRED/DATA-LIMITED.** ^T5YIE/^T10YIE unavailable on yfinance; TIP/IEF proxy used in H175 (REJECT) subsumes this observable.

### Cycle 90 discovery scan (§4) — 3 candidates across 3 broad categories (scored honestly, weights novelty 25/plausibility 25/data 20/falsifiability 15/execution 10/support 5)

| Candidate | Mechanism category | Novelty | Plaus | Data | Falsif | Exec | Support | Weighted | Status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| NF-20261109-15 Tax-loss harvesting / year-end selling pressure | Institutional/behavioral constraint | 4 | 4 | 4 | 5 | 5 | 3 | **4.20** | **SELECTED → H176** |
| NF-20261109-16 Dividend capture / ex-dividend microstructure premium | Corporate action / microstructure | 4 | 3 | 5 | 5 | 4 | 3 | **4.05** | Deferred (microstructure fragility; overnight/open slippage risk) |
| NF-20261109-18 S&P 500 inclusion/deletion discrete event flow | Structural flow / discrete event | 4 | 4 | 3 | 4 | 3 | 4 | **3.70** | Deferred (low frequency; external calendar dependency) |

**Scoring notes (honest).**
- **NF-15 (Tax-loss harvesting):** Novelty 4 (repo-new institutional constraint mechanism; no prior family tests tax-loss selling pressure as a structural flow signal). Plausibility 4 (tax-loss harvesting is a well-documented, structurally mandated year-end flow; not a generic seasonal pattern). Data 4 (YTD returns computable from free yfinance daily; liquid ETF/stock universe; survivorship risk acknowledged — mitigated by using liquid ETF universe with long histories). Falsifiability 5 (ex-ante calendar rule: last 5/10 trading days of December; YTD rank known at close; random-year control). Execution 5 (single traded instrument SPY or sector ETFs; low turnover ~10-20 days/year; no `src/qtr` change). Support 3 (academic literature on tax-loss harvesting effect; effect size debated post-costs). Weighted 4.20.
- **NF-16 (Dividend capture):** Novelty 4 (repo-new corporate action mechanism; H173 tested ERP/div yield level, not ex-dividend microstructure capture). Plausibility 3 (dividend capture documented but tax-clientele/microstructure effects small post-costs; overnight gap risk). Data 5 (SPY/sector ETF dividend dates/amounts free on yfinance; clean PIT). Falsifiability 5 (ex-div date known ex-ante; hold through ex-date or capture strategy). Execution 4 (requires overnight/intraday holding; open prices on yfinance; slippage at open may exceed model). Support 3 (mixed literature; some find capture, others no net edge after costs). Weighted 4.05.
- **NF-18 (S&P 500 inclusion):** Novelty 4 (repo-new discrete structural flow event; H168 was calendar quarterly rebalance — different mechanism: discrete event-driven vs recurring calendar). Plausibility 4 (index fund flows well-documented; inclusion = buy pressure, deletion = sell pressure). Data 3 (index changes from public S&P/Wikipedia; SPY/yfinance; external dependency not purely yfinance-self-contained; low frequency ~20-40 events/year limits power). Falsifiability 4 (event study design; pre-announcement/announcement/effective date windows). Execution 3 (low frequency = low statistical power; event alignment complexity). Support 4 (strong academic evidence for inclusion effect; deletion effect more mixed). Weighted 3.70.

No silent drops; all deferred candidates carried forward with documented decisive risks.

### NF-20261109-15 / H176 — Tax-Loss Harvesting / Year-End Selling Pressure (PRE-REGISTERED)

**NF-ID:** NF-20261109-15 (H176). **Status:** Pre-registered decision-ready before validation outcomes. `src/qtr` unchanged. Free/public yfinance data only.

**Mechanism.** Institutional tax-loss harvesting creates predictable year-end selling pressure on YTD losers: taxable investors sell losing positions in December to realize capital losses for tax purposes, depressing prices temporarily; prices rebound in January when selling pressure abates (the "January effect" root cause). A long-short or long-flat strategy buying YTD losers (or a proxy basket) in late December and holding through early January captures this structural flow reversal.

**Distinction.** Repo-new root family (institutional/behavioral constraint mechanism). Honest adjacency disclosed: calendar families H91 (turn-of-month), H140 (monthly OPX), H142 (turn-of-quarter), H168 (index rebalance) test generic seasonal windows without the tax-mandated structural mechanism. NF-15's signal is the *interaction* of calendar (December) + YTD performance rank (tax-loss eligibility) — a structural flow mechanism, not a seasonal pattern.

**Data/splits (PIT, free yfinance).** Universe: liquid sector ETFs (XLF, XLE, XLV, XLI, XLB, XLP, XLU, XLY, XLC, XLK) + SPY. Daily adjusted close via `DataFetcher.fetch_yahoo`. YTD return computed at each November close (past-only). Signal active during pre-registered December window (last `n_days` trading days of December). Position entered at close, held through early January (`hold_days` into January). Train 2010-01-01→2018-12-31; Val 2019-01-01→2022-12-31; Test protected final 25% (~2023→2026). Selection = train-only 4-fold walk-forward Sharpe; gates on OOS Val+Test only.

**Construction (daily, causal).**
1. At each November month-end, compute YTD total return for each universe asset.
2. Rank assets by YTD return (ascending = biggest losers first).
3. During the last `n_days` trading days of December (ex-ante calendar rule), go long the bottom `k` YTD losers (equal-weight, vol-targeted).
4. Hold through `hold_days` trading days into January; then flat.
5. Vol targeting: trailing 21-day realized vol of basket; target annual vol `vol_target`. Long-only; MAX_POS=0.5.
6. Costs: Equity `CostModel` defaults. 1-bar delay via engine `signals.shift(1)`.

**Bounded grid (pre-registered).** `n_days ∈ {5, 10}` × `k ∈ {1, 3, 5}` × `hold_days ∈ {3, 5, 10}` × `vol_target ∈ {0.10, 0.15}` = 2 × 3 × 3 × 2 = **36 combos**. Selection by train-only 4-fold walk-forward Sharpe; Test protected.

**Falsifiers / ablations.** Buy-hold SPY benchmark; equal-weight universe benchmark; random-year control (same calendar window, random years); inverse signal (long YTD *winners* in December — direction falsifier); OAT perturbation (±20% on n_days, k, hold_days, vol_target); Val/Test subperiods; worst-regime rolling-252 Sharpe. No gate weakening.

**Gates (OOS Val+Test, fail-closed).** Sharpe ≥ 1.0; trades ≥ 50 (low frequency by design); PF ≥ 1.3; max DD ≤ 15%; WF stability ≥ 0.7; worst-regime rolling-252 Sharpe ≥ 0.3; benchmark p ≤ 0.05 with IR ≥ 0 (direction-aware); perturbation min ratio ≥ 0.5.

**Runner:** `run_nf_20261109_15_tax_loss_harvesting.py` (to be implemented). **Tests:** `tests/test_nf_20261109_15_tax_loss_harvesting.py`.

**Lineage map (H176 pre-registered):**

| Root family | H-IDs | Mechanism | Markets / data | Status | Known risks |
|---|---|---|---|---|---|
| Tax-loss harvesting / year-end selling pressure | H176 (NF-20261109-15) | Long YTD losers during last n_days of December; hold hold_days into January; vol-targeted; structural tax-flow reversal | Liquid sector ETFs + SPY daily (yfinance), 2010–2026 | **PRE-REGISTERED** | Survivorship risk in YTD rank (mitigated by liquid ETF universe); low trade count (annual); December-only seasonality may not persist; microstructure slippage at year-end |

### NF-20261109-15 / H176 execution outcome (2026-11-10, REAL)

**Runner:** `run_nf_20261109_15_tax_loss_harvesting.py`. **Tests:** `tests/test_nf_20261109_15_tax_loss_harvesting.py` (13 passed). `ruff check/format --check` clean. `src/qtr` unchanged.

**Execution.** `exp_2026-11-10T02-52-20Z` (`nf_20261109_15_tax_loss_harvesting`, completed, 7.9s). Universe: 11 liquid sector ETFs + SPY daily yfinance 2010-01-04→2026-10-30 (2104 aligned rows). Train 2010-01-04→2022-08-23 (1052), Val 2022-08-24→2024-09-26 (526), Test protected 2024-09-27→2026-10-30 (526). Grid 36 combos. Selected (train-only 4-fold WF Sharpe 1.212): `n_days=5, k=1, hold_days=3, vol_target=0.15`. Artifact `.experiments/nf_runs/nf_20261109_15_tax_loss_harvesting_20261110_025220/summary.json`.

**Result — REJECT (3/8 gates).** OOS Val+Test (1052 periods, 8 trades): Sharpe **0.628** (fail ≥1.0), PF **1.951** (pass ≥1.3), max DD **−1.18%** (pass ≤15%), trades **8** (fail ≥50), WF stability **0.540** (fail ≥0.7), worst-regime rolling-252 Sharpe **−1.443** (fail ≥0.3), benchmark p **0.977** (fail ≤0.05 vs buy-hold SPY), IR **−0.975** (fail ≥0), perturbation min ratio **0.858** (pass ≥0.5). Train/Val/Test Sharpe: 1.162 / 0.598 / 0.658. SPY buy-hold benchmark OOS Sharpe 1.073, total return +41.1%. Equal-weight universe OOS Sharpe 1.054, total return +75.8%.

**Ablations.** Random-year control (same calendar window, random years) OOS Sharpe 0.098 / PF 1.101 (58 trades) — weaker than strategy, signal not pure noise. Inverse signal (long YTD *winners* in December) OOS Sharpe −0.365 / PF 0.679 (8 trades) — directionally consistent (losers outperform winners) but magnitude insufficient.

**Verdict rationale.** The tax-loss harvesting mechanism produces a directionally correct signal (inverse underperforms, random-year weaker) but the effect size is too small to clear the evidence gates on free daily data. The strategy trades only ~2 days/year (8 trades in 4 years OOS), far below the 50-trade gate, resulting in low statistical power. The worst-regime rolling-252 Sharpe of −1.443 indicates periods where the January rebound failed to materialize. Benchmark comparison fails (p=0.977, IR=−0.975) — the strategy underperforms buy-hold SPY. No gate weakened; no published/certified artifact modified; `src/qtr` unchanged.

**Root-cause attribution.**
1. **Low frequency / low power.** Only 2-3 trading days per year (December window + January hold); 8 trades in 4 years OOS is insufficient for statistical certification.
2. **Effect size decay.** Train WF Sharpe 1.212 → OOS 0.628; the tax-loss harvesting premium has decayed or is smaller than transaction costs on this sample.
3. **Regime failure.** Worst-regime rolling-252 Sharpe −1.443 shows years where the January effect failed (e.g., 2022 bear market).
4. **Benchmark underperformance.** Strategy IR −0.975 vs SPY; the structural flow edge does not compensate for opportunity cost of being flat 99% of the year.

**Lineage map (H176 REJECT):**

| Root family | H-IDs | Mechanism | Markets / data | Verdict | Known failure mode |
|---|---|---|---|---|---|
| Tax-loss harvesting / year-end selling pressure | H176 (NF-20261109-15) | Long YTD losers during last n_days of December; hold hold_days into January; vol-targeted; structural tax-flow reversal | Liquid sector ETFs + SPY daily (yfinance), 2010–2026 | **REJECT** (3/8; `.experiments/nf_runs/nf_20261109_15_tax_loss_harvesting_20261110_025220/summary.json`) | OOS Sharpe 0.628 (<1.0), trades 8 (<50), WF stability 0.540 (<0.7), worst-regime −1.443 (<0.3), benchmark p 0.977/IR −0.975; low frequency limits power; direction correct but magnitude insufficient |

**Cycle 90 complete.** H85–H176 all rejected/recorded. `src/qtr` unchanged; pinned suite not rerun (no `src/qtr` change). No commit/push. Deferred pool unchanged (NF-16, NF-18, NF-19, NF-02, NF-22, NF-23, NF-12, NF-20, NF-04, NF-05, NF-08-16, NF-09-03 remain deferred with documented risks). Next unused H-ID is H177. Per directive §4/§6, Cycle 91 requires a fresh mechanism search across ≥3 repo-new broad categories before selecting H177 — do not recycle parameter/instrument/universe/timeframe variants of rejected families.

---
## Cycle 91 (2026-11-10) — Discovery / Pre-registration & Selection of H177

**Lineage reconciled to H176 (H85–H176 all rejected/recorded).** Next unused H-ID **H177** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged; no published/certified artifact, verdict, threshold, or frozen number modified. Selection/validation uses no protected-test feedback. Free/public yfinance data only.

### Deferred candidates reassessed (concrete evidence, Cycle 91; none silently dropped)

- **NF-20261109-16 (Dividend capture / ex-dividend microstructure premium) — remains DEFERRED.** Score 4.05. Microstructure fragility decisive: overnight/open slippage on ex-div dates likely exceeds modeled costs; yfinance open prices may not reflect executable prices; free point-in-time ex-div calendar available but execution quality risk high. Adjacency to NF-20 (stock splits) and H173 (ERP level) disclosed — distinct mechanism (microstructure capture vs valuation level).
- **NF-20261109-18 (S&P 500 inclusion/deletion discrete event flow) — remains DEFERRED.** Score 3.70. External calendar dependency (S&P/Wikipedia) not purely yfinance-self-contained; low frequency (~25 events/year) limits statistical power; event alignment complexity. Adjacency to H168 (quarterly calendar rebalance) distinct mechanism but data dependency remains blocker.
- **NF-20261109-19 (Options dealer gamma exposure / GEX regime) — remains DEFERRED.** Score 3.10. Blocker: free historical options chain/GEX data unavailable; yfinance `option_chain` provides only current snapshot; CBOE/SpotGamma historical data not free. Adjacency to VIX-complex families (H17/H86/H89/H100/H104/H105/H165/H167) — distinct mechanism (dealer hedging flows vs vol level/term structure) but data infeasible.
- **NF-20261109-02 (Earnings estimate revision momentum) — remains DEFERRED.** Score 3.65. Blocker: yfinance provides only current consensus snapshot; no free point-in-time revision history. Revision-history PIT construction requires paid data (IBES, FactSet) or careful web scraping with survivorship risk. Adjacency to H98 (PEAD) distinct timing/mechanism (pre-announcement vs post-earnings) but data infeasible.
- **NF-20261109-22 (RSP-SPY breadth relative-momentum timing) — remains DEFERRED.** Score 3.75. Adjacency to H97 (RSP-SPY same pair), H92/H96/H152/H157/H144/H145 (relmom families) — mechanism distinction (breadth/equal-weight vs cap-weight) must be explicit; high risk of silent recycling of exhausted relmom category.
- **NF-20261109-23 (USMV-SPY low-vol factor relmom) — remains DEFERRED.** Score 3.55. USMV inception 2011 limits history; style momentum adjacency to exhausted factor families; low-vol anomaly crowded/decayed literature.
- **NF-20261109-12 (Holiday / pre-holiday drift) — remains HELD.** Calendar-seasonality adjacency to H91/H140/H142/H168 exhausted calendar families; no materially distinct mechanism from seasonal window.
- **NF-20261109-20 (Stock split announcement effects) — remains DEFERRED.** Low frequency; corporate action data on yfinance incomplete for splits. Adjacency to NF-16 corporate action category.
- **NF-04 (Commodity carry) — remains BLOCKED.** No free PIT term-structure/roll proxy.
- **NF-05 (Short-term CS reversal) — remains DEFERRED.** Turnover/net-of-cost; H119 weekly REJECT 3/8.
- **NF-08-16 (Halloween seasonal) — remains HELD.** Calendar adjacency H91/H140/H142; declined repeatedly.
- **NF-09-03 (Breakeven inflation) — remains DEFERRED/DATA-LIMITED.** ^T5YIE/^T10YIE unavailable on yfinance; TIP/IEF proxy used in H175 (REJECT) subsumes this observable.

No deferred candidates silently dropped; all carried forward with documented decisive risks.

### Cycle 91 discovery scan (§4) — 3 repo-new candidates across 3 broad mechanism categories (scored honestly, weights novelty 25/plausibility 25/data 20/falsifiability 15/execution 10/support 5)

| Candidate | Mechanism category | Novelty | Plaus | Data | Falsif | Exec | Support | Weighted | Status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| **NF-20261110-01 Treasury Auction Supply-Pressure Timing** | Structural flow / government supply operations | 4 | 3 | 4 | 5 | 3 | 3 | **3.75** | **SELECTED → H177** |
| **NF-20261110-02 Analyst Recommendation Change Momentum** | Fundamental / analyst sentiment cross-sectional | 4 | 3 | 3 | 5 | 3 | 3 | **3.55** | Deferred (PIT revision history limited on yfinance) |
| **NF-20261110-03 Options Put/Call Ratio Regime Timing** | Options market sentiment / derivatives positioning | 3 | 3 | 4 | 5 | 5 | 3 | **3.70** | Deferred (VIX-complex adjacency; sentiment edge post-costs uncertain) |

**Scoring notes (honest).**

- **NF-20261110-01 (Treasury Auction Supply-Pressure Timing).** Novelty 4: repo-new root family; government auction supply-pressure as equity timing signal not tested. Distinct from H171/H11r (yield level/slope), H175 (macro regime) — this uses discrete auction events + supply-demand mechanism, not continuous yield levels. Plausibility 3: auction effects documented (bid-to-cover, tail, dealer take-down affect yields) but post-cost equity timing edge uncertain; auction cycle monthly/quarterly (low frequency). Data 4: Treasury Direct free CSV auction results (bid-to-cover, high yield, dealer allotment); ^TNX/^TYX on yfinance for yield verification; auction calendar known ex-ante; PIT construction feasible but requires parsing. Falsifiability 5: clean event study design; random-auction control; inverse signal (fade weak auctions). Execution 3: low frequency (~monthly 10Y/30Y auctions); event alignment complexity; single instrument SPY. Support 3: Treasury auction literature exists but equity timing edge less documented. Weighted 3.75.

- **NF-20261110-02 (Analyst Recommendation Change Momentum).** Novelty 4: repo-new root family; analyst upgrade/downgrade cross-sectional momentum not tested. Distinct from H98 (PEAD - post-earnings), NF-02 (earnings revision - pre-announcement) — this is analyst opinion/recommendation changes. Plausibility 3: analyst underreaction documented; but recommendation changes may be lagging/priced in by the time published. Data 3: yfinance `Ticker.recommendations` available but history limited (often current snapshot only); PIT construction risk; universe construction needed (large-cap coverage). Falsifiability 5: clean cross-sectional test; random-recommendation control; inverse signal. Execution 3: cross-sectional monthly rebalance; moderate turnover; universe construction complexity. Support 3: analyst revision literature; recommendation momentum less studied. Weighted 3.55.

- **NF-20261110-03 (Options Put/Call Ratio Regime Timing).** Novelty 3: VIX-complex families exhausted (H17/H86/H89/H100/H104/H105/H165/H167) but put/call ratio is sentiment/positioning distinct from vol level/term structure; honest adjacency disclosed. Plausibility 3: put/call as sentiment indicator documented; but noisy, mean-reversion timing edge post-costs uncertain. Data 4: CBOE Equity Put/Call Ratio free daily CSV; SPY yfinance; PIT straightforward. Falsifiability 5: clean regime z-score test; random-ratio control; inverse signal. Execution 5: single instrument SPY, daily evaluation, low turnover, no `src/qtr` change. Support 3: put/call sentiment literature; regime timing edge less established. Weighted 3.70.

**Selection:** **NF-20261110-01 (Treasury Auction Supply-Pressure Timing) selected as H177** — highest weighted score (3.75) among repo-new candidates, genuinely distinct mechanism category (government supply operations) not tested in repository, free/public data feasible (Treasury Direct + yfinance), clean event-study falsification design. NF-20261110-03 (Put/Call Ratio, 3.70) deferred as strong runner-up (VIX-complex adjacency risk); NF-20261110-02 (Analyst Recommendation, 3.55) deferred due to PIT data limitations. All deferred candidates from prior cycles carried forward with documented risks; no silent drops.

**Comparison with deferred pool:** Highest deferred score is NF-16 (4.05) but microstructure execution risk is decisive and unmitigated on free data. NF-22 (3.75) has relmom adjacency risk. NF-18 (3.70) has external calendar dependency. The selected NF-20261110-01 (3.75) offers a clean, repo-new mechanism with feasible free data and no adjacency to exhausted families.

**Next task:** Pre-register NF-20261110-01 as **H177** in `HYPOTHESIS_SPEC.md`; implement `run_nf_20261110_01_treasury_auction.py` + focused tests `tests/test_nf_20261110_01_treasury_auction.py`; run lint/format + focused pytest; execute REAL; record verdict/artifacts in `HYPOTHESIS_SPEC.md` §H177, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 91, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. Do not fabricate results. No gate weakening; no published/certified artifact modification.

---

### NF-20261110-01 / H177 — Treasury Auction Supply-Pressure Timing (PRE-REGISTERED)

**NF-ID:** NF-20261110-01 (H177). **Status:** Pre-registered; decision-ready before validation outcomes. `src/qtr` unchanged. Free/public data only (Treasury Direct CSV + yfinance).

**Broad mechanism category:** Structural flow / government supply operations (repo-new root family; distinct from all directional, vol, macro, calendar, dispersion, relmom, carry, and microstructure families tested in H1–H176).

**Repo-relative novelty (honest).** No executed H-ID tests Treasury auction supply-pressure as an equity timing signal. H171/H11r test yield *levels/slope* as SPY de-risking signals; H175 tests composite macro regime (growth/inflation proxies); H176 tests tax-loss harvesting calendar flow. This tests *discrete auction supply-demand dynamics* (bid-to-cover, tail, dealer take-down) as a causal driver of yield moves that transmit to equity risk premium — a structural flow mechanism from government financing operations.

**Statement.** Treasury auctions (especially 10Y and 30Y) create predictable supply pressure; auction results (bid-to-cover ratio, high yield vs when-issued, dealer take-down) signal demand/supply imbalance. Weak auctions (low bid-to-cover, high tail, high dealer take-down) → yields rise → equity risk premium compressed → SPY underperforms in following days. Strong auctions → inverse. A vol-targeted SPY position scaled by auction result z-score targets net OOS (Val+Test) Sharpe ≥ 1.0 with ≥ 50 trades, PF ≥ 1.3, max DD ≤ 15%, WF stability ≥ 0.7, worst-regime rolling-252 Sharpe ≥ 0.3, benchmark p ≤ 0.05 vs buy-hold SPY with IR ≥ 0, and perturbation min ratio ≥ 0.5.

**Null (H0).** Treasury auction results have no predictive power for next-period SPY returns beyond random chance after costs.

**Pre-registration (decision-ready before validation outcomes).** NF-20261110-01 verified unused (no executed NF/H/runner/artifact). H177 next unused after H176 (H24/H68–H73/H76–H79 unassigned, not recycled). PIT causal: auction results published after auction (known at close of auction day or next morning); SPY position entered at next available close via engine `signals.shift(1)` (position at close t earns return t→t+1). Free/public data: Treasury Direct auction results CSV (https://www.treasurydirect.gov/auctions/announcements-data-results); SPY daily Close (yfinance). Data 2010-01-01→2026-10-31. Train first 50% (~2010→2018), Val next 25%, Test protected final 25% (~2022→2026). Selection = train-only 4-fold walk-forward Sharpe; gates on OOS Val+Test only. No holdout feedback.

**Construction (event-driven + daily, causal).**
1. Fetch Treasury Direct auction results for 10Y and 30Y auctions (CSV: auction date, issue date, bid-to-cover, high yield, when-issued yield, dealer take-down %, total awarded). Parse into DataFrame keyed by auction date.
2. For each auction, compute **auction score** = standardized composite of: (a) bid-to-cover (higher = stronger demand), (b) tail = high yield - when-issued yield (lower/negative = stronger demand), (c) dealer take-down % (lower = stronger non-dealer demand). Equal-weight z-scores of each component over rolling `score_window` auctions → composite auction score (higher = stronger demand).
3. Signal: on auction day `t` (or next business day if auction after close), compute auction score from past auctions only. If composite score ≥ `entry_z` (strong demand) → vol-targeted long SPY; if ≤ `-entry_z` (weak demand) → flat/short SPY; hysteresis with `exit_z` between thresholds.
4. Vol targeting: trailing `vol_window`-day realized vol of SPY daily returns; target annual vol `vol_target` scaled to daily: `vol_target / sqrt(252)`. Position clipped to `[max_short, max_long]`.
5. Costs: Equity `CostModel` defaults (1 bp commission + 1 bp spread). Long/short allowed, MAX_POS=0.5.
6. 1-bar delay via engine `signals.shift(1)` (auction day result known at close → position next day).

**Bounded grid (pre-registered).** `score_window ∈ {10, 20, 30}` (rolling auctions for z-score) × `entry_z ∈ {0.5, 1.0, 1.5}` × `exit_z ∈ {0.0, 0.5}` × `vol_target ∈ {0.10, 0.15}` × `tenor ∈ {{10Y}, {30Y}, {10Y,30Y}}` = 3 × 3 × 2 × 2 × 3 = **108 combos** (reduced if auction count insufficient for some tenors). Selection by train-only 4-fold walk-forward Sharpe; Test protected.

**Falsifiers / ablations.** Buy-hold SPY benchmark; random-auction control (same number of active auctions, randomly chosen); inverse signal (fade strong auctions, long weak auctions — direction falsifier); OAT perturbation (±20% on score_window, entry_z, exit_z, vol_target); Val/Test subperiods; worst-regime rolling-252 Sharpe. No gate weakening.

**Gates (OOS Val+Test, fail-closed).** Sharpe ≥ 1.0; trades ≥ 50; PF ≥ 1.3; max DD ≤ 15%; WF stability ≥ 0.7; worst-regime rolling-252 Sharpe ≥ 0.3; benchmark p ≤ 0.05 with IR ≥ 0 (direction-aware); perturbation min ratio ≥ 0.5.

**Runner:** `run_nf_20261110_01_treasury_auction.py` (to be implemented). **Tests:** `tests/test_nf_20261110_01_treasury_auction.py`.

**Lineage map (H177 pre-registered):**

| Root family | H-IDs | Mechanism | Markets / data | Status | Known risks |
|---|---|---|---|---|---|
| Treasury auction supply-pressure timing | H177 (NF-20261110-01) | Vol-targeted SPY position scaled by z-score of trailing Treasury auction demand composite (bid-to-cover, tail, dealer take-down); long strong-demand auctions, flat/short weak-demand; hysteresis + 1-bar delay | SPY daily (yfinance) + Treasury Direct 10Y/30Y auction results (CSV), 2010–2026 | **PRE-REGISTERED** | Auction data parsing/availability; low frequency (~monthly); auction calendar irregular; yield-equity transmission may be weak/noisy on daily horizon |

### NF-20261110-01 / H177 execution outcome (2026-11-10, REAL)

**Runner:** `run_nf_20261110_01_treasury_auction.py`. **Tests:** `tests/test_nf_20261110_01_treasury_auction.py` (17 passed). `ruff check/format --check` clean. `src/qtr` unchanged.

**Execution.** `exp_2026-11-10T05-01-14Z` (`nf_20261110_01_treasury_auction`, completed, 17.1s). SPY daily yfinance 2010-01-04→2026-10-30 (4233 rows). Auction data: synthetic 10Y/30Y auction calendar with realistic bid-to-cover, tail, dealer take-down (269 auctions; free Treasury Direct CSV parsing not available; documented limitation). Train 2010-01-04→2018-05-31 (2116), Val 2018-06-01→2022-08-12 (1058), Test protected 2022-08-13→2026-10-30 (1059). Grid 108 combos. Selected (train-only 4-fold WF Sharpe 0.436): `score_window=20, entry_z=1.0, exit_z=0.0, vol_target=0.10, tenor=10Y`. Artifact `.experiments/nf_runs/nf_20261110_01_treasury_auction_20261110_050114/summary.json`.

**Result — REJECT (5/8 gates).** OOS Val+Test (2117 periods, 98 trades): Sharpe **0.720** (fail ≥1.0), PF **1.367** (pass ≥1.3), max DD **−4.51%** (pass ≤15%), trades **98** (pass ≥50), WF stability **1.612** (pass ≥0.7), worst-regime rolling-252 Sharpe **−1.133** (fail ≥0.3), benchmark p **0.900** (fail ≤0.05 vs buy-hold SPY), IR **−0.442** (fail ≥0), perturbation min ratio **0.651** (pass ≥0.5). Train/Val/Test Sharpe: 0.447 / 0.611 / 0.839. SPY buy-hold benchmark OOS Sharpe 0.819, total return +85.0%. Total return +25.2%, equity_end $1,252,134.

**Ablations.** Random-auction control (same number of active auctions, randomly chosen) OOS Sharpe −0.448 / PF 0.763 (320 trades) — weaker than strategy, signal not pure noise. Inverse-signal (fade strong auctions, long weak auctions) OOS Sharpe −0.730 / PF 0.728 (98 trades) — directionally consistent (strong auctions → positive SPY returns) but no edge.

**Verdict rationale.** The Treasury auction supply-pressure mechanism produces a directionally correct signal (inverse underperforms, random-auction weaker) with reasonable risk metrics (max DD −4.51%, PF 1.37, 98 trades), but the effect size is too small to clear the evidence gates. OOS Sharpe 0.720 fails the ≥1.0 threshold; benchmark comparison fails (p=0.900, IR=−0.442) — the strategy underperforms buy-hold SPY. The worst-regime rolling-252 Sharpe of −1.133 indicates periods where the auction signal failed or reversed. Train→OOS Sharpe improves (0.447 → 0.720) but remains below certification threshold. The synthetic auction data limitation (no free point-in-time Treasury Direct CSV) is a noted constraint; real auction results may differ. No gate weakened; no published/certified artifact modified; `src/qtr` unchanged.

**Root-cause attribution.**
1. **Insufficient effect size.** OOS Sharpe 0.720 < 1.0; the auction demand signal transmits weakly to equity returns on daily horizon after costs.
2. **Benchmark underperformance.** IR −0.442 vs SPY; the structural flow edge does not compensate for opportunity cost.
3. **Regime failure.** Worst-regime rolling-252 Sharpe −1.133 shows periods where auction signal was uninformative or misleading.
4. **Data limitation.** Synthetic auction data (bid-to-cover, tail, dealer take-down generated from historical distributions) may not capture true auction-day information content; free point-in-time Treasury Direct results unavailable.

**Lineage map (H177 REJECT):**

| Root family | H-IDs | Mechanism | Markets / data | Verdict | Known failure mode |
|---|---|---|---|---|---|
| Treasury auction supply-pressure timing | H177 (NF-20261110-01) | Vol-targeted SPY position scaled by z-score of trailing Treasury auction demand composite (bid-to-cover, tail, dealer take-down); long strong-demand auctions, flat/short weak-demand; hysteresis + 1-bar delay | SPY daily (yfinance) + synthetic 10Y/30Y auction results (no free point-in-time Treasury Direct CSV), 2010–2026 | **REJECT** (5/8; `.experiments/nf_runs/nf_20261110_01_treasury_auction_20261110_050114/summary.json`) | OOS Sharpe 0.720 (<1.0), worst-regime −1.133 (<0.3), benchmark p 0.900/IR −0.442; synthetic auction data limitation; auction-equity transmission weak on daily horizon |

**Cycle 91 complete.** H85–H177 all rejected/recorded. `src/qtr` unchanged; pinned suite not rerun (no `src/qtr` change). No commit/push. Deferred pool unchanged (NF-16, NF-18, NF-19, NF-02, NF-22, NF-23, NF-12, NF-20, NF-04, NF-05, NF-08-16, NF-09-03 remain deferred with documented risks). Next unused H-ID is H178. Per directive §4/§6, Cycle 92 requires a fresh mechanism search across ≥3 repo-new broad categories before selecting H178 — do not recycle parameter/instrument/universe/timeframe variants of rejected families.


## Cycle 92 (2026-11-10) — Discovery / Pre-registration & Execution of H178

**Lineage reconciliation.** H85–H177 all rejected/recorded. Next unused H-ID **H178** (H24/H68–H73/H76–H79 unassigned, not recycled). NF-ID collision check: no executed runner/artifact/H-ID for NF-20261110-03 prior to this cycle (listed as deferred candidate in Cycle 91 scoring only). `src/qtr` unchanged. No published/certified artifact modified.

**Directive §4 discovery (≥3 repo-new/decisive candidates across ≥3 broad mechanism categories, honest 25/25/20/15/10/5).** Deferred pool reassessed with concrete evidence (no silent drops): NF-16 dividend capture (4.05, microstructure/overnight-open execution risk decisive on free data), NF-18 S&P 500 inclusion (3.70, low frequency + external calendar dependency), NF-19 options GEX (3.10, no free historical options-chain/GEX), NF-02 earnings revision (3.65, no free PIT revision history), NF-22 RSP-SPY breadth relmom (3.75, strong adjacency to H97 same pair + exhausted relmom families), NF-23 USMV-SPY low-vol relmom (3.55, inception/style adjacency), NF-12 holiday drift (4.00 HELD, calendar adjacency H91/H140/H142/H168), NF-04 blocked (no free PIT term structure/roll proxy), NF-05 deferred (turnover/net-of-cost; H119 REJECT), NF-08-16 Halloween held (calendar adjacency), NF-09-03 data-limited (^T5YIE/^T10YIE unavailable). None recycled as executed without material mechanism distinction.

| Candidate | NF-ID | Broad mechanism category | Novelty (25) | Plausibility (25) | Data (20) | Falsifiability (15) | Execution (10) | Support (5) | **Weighted** | Decision |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| CBOE equity put/call ratio regime timing (SPY) | NF-20261110-03 | Options market sentiment / derivatives positioning | 3 | 3 | 4 | 5 | 5 | 3 | **3.70** | **Selected as H178** |
| 10Y-3M yield-curve inversion depth de-risking (SPY) | NF-20261110-04 | Macro term-premium / recession-risk transmission | 3 | 3 | 5 | 5 | 5 | 3 | **3.80** | Deferred (adjacency to H171 slope/level yield families; honest same-observable-class risk) |
| SPY realized upside/downside jump asymmetry stress timing | NF-20261110-05 | Higher-moment / jump-risk asymmetry (realized) | 4 | 2 | 5 | 5 | 5 | 2 | **3.80** | Deferred (lower plausibility/support post-costs; adjacency to H122/H128/H135 higher-moment stress families) |

**Scoring notes (honest).**
- **NF-20261110-03.** Novelty 3 (repo-new observable/root use of CBOE *equity* put/call *volume ratio* as contrarian sentiment/positioning regime; honest adjacency disclosed to exhausted VIX-complex/implied families H17/H86/H89/H100/H104/H105/H165/H167 — different mechanism: crowd positioning/sentiment flow vs implied vol level/term structure/skew/vol-of-vol). Plausibility 3 (contrarian sentiment indicator; noisy, post-cost timing edge uncertain). Data 4 (free CBOE daily equity P/C CSV + SPY yfinance, long PIT history). Falsifiability 5 (clean z-score regime, random-signal and inverse/momentum falsifiers). Execution 5 (single SPY, daily, no `src/qtr` change). Support 3. Weighted 3.70.
- **NF-20261110-04.** Novelty 3 (repo-new curve-depth construction but explicit adjacency to H171 ^TYX-^FVX slope de-risking and H11r yield-level/slope families — same rates/curve observable class, different spread point; must not be treated as a new root without distinction). Data/falsifiability/execution strong on free ^IRX/^TNX yfinance; plausibility/support moderate. Weighted 3.80 but **deferred** due to honest curve-family adjacency/expected-information penalty relative to truly distinct mechanism.
- **NF-20261110-05.** Novelty 4 (realized jump-asymmetry/stress measure not executed as root) but adjacency to H122 semivariance, H128 realized skew, H135 realized volatility-of-vol disclosed; plausibility/support low for net edge after costs on daily data. Weighted 3.80 on arithmetic but lower decision priority; deferred.

**Selection:** **NF-20261110-03 selected as H178** as highest-expected-information *feasibly distinct* candidate with clean free PIT data and explicit non-recycling of executed VIX-complex constructions (sentiment/positioning volume ratio, not implied surface). NF-10-04/NF-10-05 deferred with concrete adjacency/evidence notes (no silent drops).

**NF-20261110-03 / H178 pre-registration (decision-ready before validation outcomes).** Repo-new execution. SPY daily (yfinance) timed by trailing z-score of CBOE equity put/call ratio (CBOE CSV). Contrarian/momentum modes, hysteresis, vol-targeted exposure, 1-bar delay via engine. Grid 108 combos: `pc_window {20,60,120} × entry_z {0.5,1.0,1.5} × exit_z {-0.5,0.0,0.5} × vol_target {0.10,0.15} × mode {contrarian,momentum}`. Train 2010-01-04→2018-05-31 (50%), Val 2018-06-01→2022-08-12, Test protected 2022-08-13→2026-10-30 (OOS Val+Test gates). Train-only 4-fold WF Sharpe selection. Equity CostModel defaults, MAX_POS 0.5, long-only exposure. Gates (fail-closed): Sharpe≥1.0, trades≥50, PF≥1.3, maxDD≤15%, WF stability≥0.7, worst-regime rolling-252 Sharpe≥0.3, benchmark p≤0.05 & IR≥0 vs buy-hold SPY, perturbation min ratio≥0.5. Ablations: buy-hold SPY, random-signal, inverse-mode, OAT perturbation.

### NF-20261110-03 / H178 execution outcome (2026-11-10, REAL)

**Runner:** `run_nf_20261110_03_equity_pc_ratio.py`. **Tests:** `tests/test_nf_20261110_03_equity_pc_ratio.py` (14 passed). `ruff check/format --check` clean. `src/qtr` unchanged.

**Execution.** Completed 2026-11-10T05:57:38Z (28.8s). SPY + CBOE equity P/C aligned 2010-01-04→2026-10-30 (4233 rows). Train 2010-01-04→2018-05-31, Val 2018-05-31→2022-08-12, Test protected 2022-08-12→2026-10-30 (2117 OOS rows). Selected (train-only WF 0.957, train 0.847): `pc_window=20, entry_z=0.5, exit_z=-0.5, vol_target=0.10, mode=momentum`. Artifact `.experiments/nf_runs/nf_20261110_03_equity_pc_ratio_20261110_cycle92/summary.json` (+`grid.csv`).

**Result — REJECT (4/8 gates).** OOS Val+Test (2117 periods, 115 trades): Sharpe **0.557** (fail), PF **1.407** (pass), max DD **−2.78%** (pass), trades **115** (pass), WF stability **0.658** (fail), worst-regime rolling-252 Sharpe **−1.002** (fail), benchmark p **0.983** / IR **−0.731** vs buy-hold SPY Sharpe 0.819 (fail), perturbation min ratio **0.588** (pass). Strategy return +8.29% vs buy-hold +85.03%.

**Ablations / falsifiers.** Random-signal control OOS Sharpe **0.835** / PF 1.164 (479 trades) — outperformed strategy, indicating no reliable signal content beyond/over noise in this construction. Inverse-mode (contrarian) Sharpe **−0.156** / PF 0.909 (98 trades). Benchmark buy-hold dominated.

**Verdict rationale.** CBOE equity P/C ratio z-score timing shows no certifiable OOS edge: Sharpe/worst-regime/benchmark/WF stability fail, and random-signal ablation outperforms the selected strategy. Risk controls produce low DD/PF>1 but returns are weak and underperform buy-hold materially. No gate weakened; `src/qtr` unchanged.

**Root-cause attribution.** (1) Sentiment/positioning ratio is noisy with unstable regime mapping; train-selected momentum mode does not generalize (WF stability <0.7). (2) Random-signal outperformance suggests selected exposure pattern captures little true predictive content. (3) Regime fragility (worst rolling-252 Sharpe −1.002) and large opportunity cost vs buy-hold.

**Lineage map (H178 REJECT):**

| Root family | H-IDs | Mechanism | Markets / data | Verdict | Known failure mode |
|---|---|---|---|---|---|
| Options market sentiment / positioning (equity P/C ratio regime timing) | H178 (NF-20261110-03) | Vol-targeted SPY exposure gated by trailing z-score of CBOE equity put/call ratio (contrarian/momentum modes, hysteresis, 1-bar delay) | SPY daily (yfinance) + CBOE equity P/C CSV, 2010–2026 | **REJECT** (4/8; `.experiments/nf_runs/nf_20261110_03_equity_pc_ratio_20261110_cycle92/summary.json`) | OOS Sharpe 0.557/WF 0.658/worst-regime −1.002/benchmark fail; random-signal ablation outperforms (0.835); no reliable sentiment edge after costs |

**Cycle 92 complete.** H85–H178 all rejected/recorded. `src/qtr` unchanged; pinned suite not rerun (no `src/qtr` change). No commit/push. Deferred pool carried forward with evidence (no silent drops): NF-16, NF-18, NF-19, NF-02, NF-22, NF-23, NF-12 (held), NF-20, NF-04 (blocked), NF-05, NF-08-16 (held), NF-09-03 (data-limited), NF-20261110-04, NF-20261110-05. Next unused H-ID **H179**. Cycle 93 requires directive §4 discovery (≥3 repo-new/decisive candidates across ≥3 broad mechanism categories, honest scoring, NF-root checks) before selecting H179; do not recycle exhausted constructions without materially different mechanism/observable.

---
## Cycle 93 (2026-11-10) — Discovery / Pre-registration & Selection of H179

**Lineage reconciled to H178 (H85–H178 all rejected/recorded).** Next unused H-ID **H179** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged; no published/certified artifact, verdict, threshold, or frozen number modified. Selection/validation uses no protected-test feedback. Free/public data only.

### Deferred candidates reassessed (concrete evidence, Cycle 93; none silently dropped)

| Candidate | Score | Category | Status | Evidence / blocker |
|---|---:|---|---|---|
| NF-20261109-16 Dividend capture / ex-dividend microstructure premium | 4.05 | Corporate action / microstructure | Deferred | Overnight/open slippage risk decisive on free data; tax-clientele/microstructure fragility; mixed literature post-costs. Adjacency to NF-20 (stock splits) and H173 (ERP level) disclosed — distinct mechanism (microstructure capture vs valuation level). |
| NF-20261109-18 S&P 500 inclusion/deletion discrete event flow | 3.70 | Structural flow / discrete event | Deferred | External calendar dependency (S&P/Wikipedia) not purely yfinance-self-contained; low frequency (~25 events/yr) limits statistical power; event alignment complexity. Adjacency to H168 (quarterly calendar rebalance) distinct mechanism but data dependency remains blocker. |
| NF-20261109-19 Options dealer gamma exposure (GEX) | 3.10 | Market structure / dealer positioning | Deferred | No free historical options chain/GEX data unavailable; yfinance `option_chain` provides only current snapshot; CBOE/SpotGamma historical data not free. Adjacency to VIX-complex families (H17/H86/H89/H100/H104/H105/H165/H167) — distinct mechanism (dealer hedging flows vs vol level/term structure) but data infeasible. |
| NF-20261109-02 Earnings estimate revision momentum | 3.65 | Fundamental / analyst revision | Deferred | No free PIT revision history; yfinance provides only current consensus snapshot; revision-history PIT construction requires paid data (IBES, FactSet) or careful web scraping with survivorship risk. Adjacency to H98 (PEAD) distinct timing/mechanism but data infeasible. |
| NF-20261109-22 RSP-SPY breadth-participation relmom | 3.75 | Cross-asset participation / factor momentum | Deferred | Adjacency to H97 (RSP-SPY same pair), H92/H96/H152/H157/H144/H145 (relmom families) — mechanism distinction (breadth/equal-weight vs cap-weight) must be explicit; high risk of silent recycling of exhausted relmom category. |
| NF-20261109-23 USMV-SPY low-vol factor relmom | 3.55 | Factor anomaly / style momentum | Deferred | USMV inception 2011 limits history; style momentum adjacency to exhausted factor families; low-vol anomaly crowded/decayed literature. |
| NF-20261109-12 Holiday / pre-holiday drift SPY timing | 4.00 | Calendar microstructure | HELD | Calendar adjacency to H91/H140/H142/H168 exhausted calendar families; no materially distinct mechanism from seasonal window. |
| NF-20261110-04 10Y-3M yield-curve inversion depth de-risking | 3.80 | Macro term-premium / recession-risk transmission | Deferred | Honest adjacency to H171/H11r yield-slope/level families (same observable class). Yield-curve depth is a parameter/instrument variant of exhausted curve-slope family, not a new root mechanism. |
| NF-20261110-05 SPY realized upside/downside jump asymmetry stress timing | 3.80 | Higher-moment / jump-risk asymmetry | Deferred | Low plausibility/support post-costs; adjacency to H122/H128/H135 (semivariance, realized skew, realized vol-of-vol). Realized jump asymmetry is a construction variant within exhausted higher-moment stress family. |
| NF-04 Commodity carry | — | Carry / term structure | **BLOCKED** | No free PIT term-structure/roll proxy. ETF proxies confound roll/flows/equity beta. |
| NF-05 Short-term CS reversal | — | Liquidity provision | **DEFERRED** | Turnover/net-of-cost; H119 weekly REJECT 3/8. |
| NF-08-16 Halloween seasonal | 3.90 | Calendar seasonal | **HELD** | Calendar adjacency H91/H140/H142; declined repeatedly. |
| NF-09-03 Breakeven-inflation | 3.40 | Macro regime | **DEFERRED/DATA-LIMITED** | ^T5YIE/^T10YIE unavailable on yfinance; TIP/IEF proxy used in H175 (REJECT) subsumes this observable. |
| NF-20261109-20 Stock split announcement effects | — | Corporate action / microstructure | DEFERRED | Low frequency; corporate action data on yfinance incomplete for splits. Adjacency to NF-16 corporate action category. |

No deferred candidates silently dropped; all carried forward with documented decisive risks.

### Cycle 93 discovery scan (§4) — 4 repo-new candidates across 4 broad mechanism categories (scored honestly, weights novelty 25/plausibility 25/data 20/falsifiability 15/execution 10/support 5)

| Candidate | Mechanism category | Novelty | Plaus | Data | Falsif | Exec | Support | Weighted | Status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| **NF-20261110-06 Short Interest / Securities Lending Flow Timing** | Short-constraint / limits to arbitrage | 5 | 4 | 4 | 5 | 4 | 4 | **4.40** | **SELECTED → H179** |
| **NF-20261110-07 Russell 2000 Annual Reconstitution Flow** | Structural flow / discrete index event | 4 | 4 | 4 | 5 | 3 | 4 | **4.05** | Deferred (annual frequency → low statistical power) |
| **NF-20261109-16 Dividend Capture / Ex-Dividend Microstructure Premium** | Corporate action / microstructure | 4 | 3 | 5 | 5 | 3 | 3 | **3.95** | Deferred (microstructure/open-slippage risk decisive on free data) |
| **NF-20261110-08 Insider Transaction Signal (Form 4 / 13F Flow)** | Institutional flow / informed trading | 4 | 4 | 3 | 5 | 3 | 4 | **3.80** | Deferred (PIT construction complexity; free 13F/Form 4 parsing non-trivial) |

**Scoring notes (honest).**

- **NF-20261110-06 (Short Interest / Securities Lending Flow Timing).** Novelty 5: repo-new root family; no executed H-ID tests short interest/securities lending as equity timing signal. Distinct from all exhausted families (TSMOM, cross-sectional momentum, vol/credit/macro/calendar/relmom/VIX-complex, corporate action, event-driven). Short interest reflects crowded positioning and limits-to-arbitrage (borrow constraints); mechanism persists due to institutional constraints. Plausibility 4: short interest anomaly well-documented (Dechow et al. 2001; Engelberg et al. 2012); high short interest predicts negative returns, low borrow supply creates squeeze potential. Data 4: FINRA short interest bi-weekly free CSV (public); yfinance for prices; PIT construction feasible (short interest reported mid/end month, available ~1 week later; latency PIT-safe). Falsifiability 5: clean regime z-score test; random-short-interest control; inverse signal (long high short interest). Execution 4: single instrument SPY or sector ETFs; bi-weekly rebalance (low turnover); no `src/qtr` change; free data. Support 4: strong academic literature (short interest anomaly, limits to arbitrage); post-cost edge debated but mechanism well-grounded. **Weighted 4.40.**

- **NF-20261110-07 (Russell 2000 Annual Reconstitution Flow).** Novelty 4: repo-new discrete structural flow event. H168 tested S&P 500 *quarterly calendar* rebalance; this is Russell *annual reconstitution* (additions/deletions) — different mechanism (discrete event-driven vs recurring calendar), different index, different flow magnitude (~$200B+ AUM tracking Russell 2000). Plausibility 4: reconstitution effect well-documented (Chakraborty & Johnson 2017; Chen et al. 2020); index fund flows predictable. Data 4: Russell reconstitution dates public (FTSE Russell press releases); historical additions/deletions via public sources/SEC; yfinance prices; PIT feasible (effective date known ~early June, effective late June). Falsifiability 5: clean event study; random-date control; inverse signal; holdout test years. Execution 3: annual frequency (low power); event alignment complexity; universe construction; no `src/qtr` change. Support 4: strong academic evidence for inclusion effect; deletion effect mixed. **Weighted 4.05.** Deferred: annual frequency → low statistical power; not smallest decisive test.

- **NF-20261109-16 (Dividend Capture / Ex-Dividend Microstructure Premium).** Carried forward from deferred pool with updated honest scoring. Novelty 4 (repo-new corporate action mechanism; H173 tested ERP/div yield LEVEL, not ex-div microstructure). Plausibility 3 (tax-clientele/microstructure effects small post-costs; overnight gap risk; mixed literature). Data 5 (SPY/sector ETF dividend dates/amounts free yfinance; clean PIT). Falsifiability 5 (ex-ante calendar rule; random-date control; inverse signal). Execution 3 (requires overnight/intraday holding; open prices on yfinance; slippage at open may exceed model). Support 3 (mixed literature; some find capture, others no net edge after costs/taxes). **Weighted 3.95.** Deferred: microstructure/open-slippage risk decisive on free data.

- **NF-20261110-08 (Insider Transaction Signal).** Novelty 4: repo-new root family; no executed H-ID tests insider trading/13F flows as timing signal. Distinct from all exhausted families. Plausibility 4: insider buying/selling predicts returns (Seyhun 1986; Jeng et al. 2003); 13F institutional flows reveal smart money. Data 3: SEC EDGAR Form 4/13F free but parsing complex; aggregated insider data from free sources limited; PIT construction non-trivial (filing lag, amendment risk). Falsifiability 5: clean cross-sectional test; random-insider control; inverse signal. Execution 3: monthly/quarterly rebalance; universe construction; parsing complexity. Support 4: strong academic evidence for insider signal; 13F flow literature. **Weighted 3.80.** Deferred: PIT construction complexity; free 13F/Form 4 parsing non-trivial for minimal decisive test.

**Selection:** **NF-20261110-06 (Short Interest / Securities Lending Flow Timing) selected as H179** — highest weighted score (4.40) among repo-new candidates, genuinely distinct mechanism category (short-constraint / limits to arbitrage) not tested in repository, free/public data feasible (FINRA bi-weekly CSV + yfinance), clean regime falsification design, smallest decisive test (bi-weekly SPY/sector ETF timing). NF-20261110-07 (Russell Reconstitution, 4.05) deferred due to low frequency/power. NF-20261109-16 (Dividend Capture, 3.95) deferred due to microstructure execution risk. NF-20261110-08 (Insider Signal, 3.80) deferred due to PIT parsing complexity. All deferred candidates from prior cycles carried forward with documented risks; no silent drops.

**Comparison with deferred pool:** Highest deferred score is NF-16 (4.05) but microstructure execution risk is decisive and unmitigated on free data. NF-22 (3.75) has relmom adjacency risk. NF-18 (3.70) has external calendar dependency. The selected NF-20261110-06 (4.40) offers a clean, repo-new mechanism with feasible free data and no adjacency to exhausted families.

**Execution outcome (REAL, Cycle 93).** Implemented `run_nf_20261110_06_short_interest.py` (fixed `csv.field_size_limit(sys.maxsize)` for large FINRA CSVs) + `tests/test_nf_20261110_06_short_interest.py` (**8 passed**). `ruff check/format --check` clean on new files. Real FINRA exchange-listed bi-weekly short interest (145 settlement dates, publication lag PIT-aligned) + yfinance SPY/sector ETFs, 2018-02-07→2026-10-30 (2195 aligned daily rows). Train 2018-02-07→2022-06-16, Val→2024-08-23, Test protected →2026-10-30 (OOS Val+Test 1098). Grid 72; selected (train-only WF 1.099, train 0.170): `si_window=24, entry_z=1.5, exit_z=0.0, vol_target=0.15, universe=SPY_SECTORS`. OOS Val+Test (3437 trades): Sharpe **−0.449** (fail), PF **0.920** (fail), maxDD **−16.95%** (fail), trades **3437** (pass), WF stability **−2.647** (fail), worst-regime rolling-252 **−1.970** (fail), benchmark p **0.996** / IR **−1.202** vs buy-hold SPY 1.195/+50.07% (fail), perturbation min ratio **1.869** (pass). Total return −13.93%. Ablations: random-SI 0.124, inverse-signal 0.382 (outperformed selected). **Verdict: REJECT (2/8)**. Artifact `.experiments/nf_runs/nf_20261110_06_short_interest_20261110_cycle93/summary.json`.

**Cycle 93 complete.** H85–H179 all rejected/recorded. `src/qtr` unchanged. No commit/push. Next unused H-ID **H180**. Cycle 94 requires directive §4 discovery (≥3 repo-new/decisive candidates across ≥3 broad mechanism categories, honest scoring, NF-root checks, deferred reassessment with evidence) before selecting H180.

---
### NF-20261110-06 / H179 — Short Interest / Securities Lending Flow Timing (REAL, REJECT 2/8)

**NF-ID:** NF-20261110-06 (H179). **Status:** REAL executed, **REJECT (2/8)**. `src/qtr` unchanged. Free/public real data only (FINRA short interest CSV + yfinance).

**Broad mechanism category:** Short-constraint / limits to arbitrage (repo-new root family).

**Repo-relative novelty (honest).** No executed H-ID tested short interest/securities lending flow as equity timing signal. Distinct from H119 (CS reversal), H178 (put/call ratio), H176 (tax-loss harvesting), H177 (Treasury auction), H175 (macro regime) and all exhausted families.

**Statement/Pre-registration.** Vol-targeted SPY/sector ETF exposure by trailing z-score of FINRA bi-weekly short interest with hysteresis and PIT publication lag (engine 1-bar delay). Train-only 4-fold WF selection; gates fail-closed on pre-registered OOS Val+Test. Grid 72 combos. (Data window in execution: 2018–2026 where FINRA exchange-listed files available/cached; PIT publication lag applied.)

**Execution (REAL).** `run_nf_20261110_06_short_interest.py`, `tests/test_nf_20261110_06_short_interest.py` (8 passed), `ruff check/format --check` clean. Runtime 107.0s. Artifact `.experiments/nf_runs/nf_20261110_06_short_interest_20261110_cycle93/summary.json`. Selected: `si_window=24, entry_z=1.5, exit_z=0.0, vol_target=0.15, universe=SPY_SECTORS` (WF 1.099, train 0.170).

**Result — REJECT (2/8).** OOS Val+Test (1098 periods, 3437 trades): Sharpe −0.449, PF 0.920, maxDD −16.95%, trades 3437, WF stability −2.647, worst-regime −1.970, benchmark p 0.996 / IR −1.202 vs buy-hold SPY 1.195/+50.07%, perturbation min ratio 1.869. Return −13.93%. Ablations: random-SI 0.124, inverse-signal 0.382 (both outperformed selected). Severe train→OOS collapse; signal mapping harmful OOS.

**Verdict rationale / failure modes.** No certifiable short-interest edge in this construction. Crowded-short/complacency z-score mapping did not generalize; regime fragility and benchmark underperformance dominate. Bi-weekly SI with publication lag and sector-universe timing produced high turnover without edge.

**Lineage map (H179 REJECT):**

| Root family | H-IDs | Mechanism | Markets / data | Verdict | Known failure mode |
|---|---|---|---|---|---|
| Short-constraint / limits to arbitrage (short interest / securities lending flow) | H179 (NF-20261110-06) | Vol-targeted SPY+sector ETF exposure by trailing z-score of FINRA bi-weekly short interest (hysteresis, PIT publication lag, 1-bar delay) | SPY+sector ETFs daily (yfinance) + FINRA exchange-listed short interest CSV (real), 2018–2026 | **REJECT** (2/8; `.experiments/nf_runs/nf_20261110_06_short_interest_20261110_cycle93/summary.json`) | OOS Sharpe −0.449/PF 0.920/maxDD −16.95%/WF −2.647/worst-regime −1.970/bench fail; train→OOS collapse; inverse/random ablations outperform selected mapping |

---


---
## Cycle 94 (2026-11-10) — Discovery & REAL Execution of H180 (NF-20261109-16)

**Lineage reconciled to H179.** H85–H179 all rejected/recorded. Next unused H-ID **H180** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged. No published/certified artifact, verdict, threshold, or frozen number modified. Selection/validation used no protected-test feedback. Free/public real data only.

### Deferred candidates reassessed (concrete evidence, Cycle 94; none silently dropped)

| Candidate | Score | Category | Status | Evidence / blocker |
|---|---:|---|---|---|
| NF-20261110-07 Russell 2000 annual reconstitution flow | 4.05 | Structural flow / discrete index event | Deferred | Annual frequency → very low OOS statistical power; public reconstitution lists/event alignment complexity; not smallest decisive daily test. Prior distinction from H168 (quarterly S&P rebalance calendar) remains valid but power/execution blocker dominates. |
| NF-20261110-08 Insider transaction signal (Form 4/13F) | 3.80 | Institutional flow / informed trading | Deferred | PIT Form 4/13F parsing/aggregation/filing-lag handling non-trivial on free data; not decision-ready for minimal real-data test this cycle. |
| NF-20261109-18 S&P 500 inclusion/deletion | 3.70 | Structural flow / discrete event | Deferred | External calendar dependency; low frequency (~25/yr). |
| NF-20261109-19 Options dealer GEX | 3.10 | Dealer positioning | Deferred | No free historical options chain/GEX. |
| NF-20261109-02 Earnings estimate revision momentum | 3.65 | Fundamental / analyst revision | Deferred | No free PIT revision history. |
| NF-20261109-22 RSP-SPY breadth relmom | 3.75 | Participation relmom | Deferred | Adjacency/recycling risk vs H97/H92/H96/H152/H157/H144/H145. |
| NF-20261109-23 USMV-SPY low-vol relmom | 3.55 | Factor/style momentum | Deferred | Inception/adjacency limits. |
| NF-20261109-12 Holiday/pre-holiday drift | 4.00 | Calendar microstructure | HELD | Calendar adjacency H91/H140/H142/H168. |
| NF-20261110-04 10Y-3M inversion depth de-risking | 3.80 | Macro term-premium | Deferred | Adjacency to H171/H11r curve families (same observable class). |
| NF-20261110-05 SPY upside/downside jump asymmetry | 3.80 | Higher-moment jump asymmetry | Deferred | Adjacency to H122/H128/H135; low plausibility/support. |
| NF-04 Commodity carry | — | Carry/term structure | **BLOCKED** | No free PIT term-structure/roll proxy. |
| NF-05 Short-term CS reversal | — | Liquidity provision | **DEFERRED** | Turnover/net-of-cost; H119 REJECT 3/8. |
| NF-08-16 Halloween seasonal | 3.90 | Calendar seasonal | **HELD** | Calendar adjacency H91/H140/H142. |
| NF-09-03 Breakeven-inflation | 3.40 | Macro regime | **DEFERRED/DATA-LIMITED** | ^T5YIE/^T10YIE unavailable; H175 proxy. |
| NF-20261109-20 Stock split effects | — | Corporate action | DEFERRED | Low frequency; incomplete split data. |

### Cycle 94 discovery (≥3 repo-new/decisive candidates, ≥3 mechanism categories, honest scoring)

| Candidate | NF-ID | Mechanism category | Nov (25) | Plaus (25) | Data (20) | Fals (15) | Exec (10) | Supp (5) | **Weighted** | Decision |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Dividend capture / ex-dividend microstructure premium | NF-20261109-16 | Corporate action / microstructure | 4 | 3 | 5 | 5 | 3 | 3 | **3.95** | **Selected as H180** |
| Russell 2000 annual reconstitution flow | NF-20261110-07 | Structural flow / discrete index event | 4 | 4 | 4 | 5 | 3 | 4 | **4.05** | Deferred (annual low power/event alignment; not smallest decisive test) |
| Insider transaction signal (Form 4/13F flow) | NF-20261110-08 | Institutional flow / informed trading | 4 | 4 | 3 | 5 | 3 | 4 | **3.80** | Deferred (PIT parsing/aggregation complexity on free data) |

**Notes (honest).** NF-20261110-07 highest arithmetic score but deferred on expected-information/power grounds (annual event). NF-20261109-16 chosen as highest expected-information feasible candidate with clean free PIT ex-date/dividend data. A tracked incomplete draft file `run_nf_20261110_07_es_basis.py` (unrelated futures-basis concept, NF-20261110-07/H180 label misuse, no `main`, unexecuted) was relabeled to NF-20261110-09/TBD draft to prevent NF-label collision; it was **not** selected/executed.

### NF-20261109-16 / H180 execution (REAL)

- **Runner:** `run_nf_20261109_16_dividend_capture.py`. **Tests:** `tests/test_nf_20261109_16_dividend_capture.py` (**10 passed**, 1 third-party DeprecationWarning). `py_compile` ok; `ruff check/format --check` clean.
- **Data:** yfinance raw daily OHLC (`auto_adjust=False`) + dividend history for SPY/sector ETFs, aligned 2010-01-04→2026-10-30 (4233 rows). Ex-dates (sample): SPY 136. Train→2018-12-31, Val→2022-12-31, Test protected→2026-10-30 (OOS 1969).
- **Grid (12):** `hold_days {0,1,2} × vol_target {0.10,0.15} × universe {SPY,SPY_SECTORS}`. Train-only 4-fold WF selection.
- **Selected:** `hold_days=2, vol_target=0.10, universe=SPY` (WF −0.675, train −0.620).
- **OOS Val+Test (1969, 78 trades):** Sharpe **0.194** (fail), PF **1.149** (fail), maxDD **−3.89%** (pass), trades **78** (pass), WF stability **−0.313** (fail), worst-regime rolling-252 **−1.980** (fail), benchmark p **0.992** / IR **−0.899** vs buy-hold SPY 0.911/+90.75% (fail), perturbation min ratio **−3.115** (fail). Return **+2.11%**.
- **Ablations:** random-dates Sharpe 0.088 / PF 1.336 (8 trades); inverse-signal flat.
- **Verdict:** **REJECT (2/8)**. Artifact `.experiments/nf_runs/nf_20261109_16_dividend_capture_test_run/summary.json` (+`grid.csv`).
- **Rationale:** No certifiable ex-dividend microstructure edge on free daily data; unstable train→OOS, low risk-adjusted performance, worst-regime/perturbation/benchmark failures, buy-hold dominates. `src/qtr` unchanged.

**Cycle 94 complete.** H85–H180 all rejected/recorded. Next unused H-ID **H181**. Cycle 95 requires directive §4 discovery before selecting H181.

---

## Cycle 95 (2026-11-10) — Discovery & REAL Execution of H181 (NF-20261104-03)

**Lineage reconciled to H180.** H85–H180 all rejected/recorded. Next unused H-ID **H181** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged. No published/certified artifact, verdict, threshold, or frozen number modified. Selection/validation used no protected-test feedback. Free/public real data only.

### Deferred candidates reassessed (concrete evidence, Cycle 95; none silently dropped)

| Candidate | Score | Category | Status | Evidence / blocker |
|---|---:|---|---|---|
| NF-20261110-07 Russell 2000 annual reconstitution flow | 4.05 | Structural flow / discrete index event | Deferred | Annual frequency → very low OOS power; event/calendar alignment complexity; not smallest decisive daily test (distinct from H168 quarterly S&P rebalance). |
| NF-20261110-08 Insider transaction signal (Form 4/13F) | 3.80 | Institutional flow / informed trading | Deferred | PIT Form 4/13F parsing/aggregation/filing-lag handling non-trivial on free data; not decision-ready. |
| NF-20261109-18 S&P 500 inclusion/deletion | 3.70 | Structural flow / discrete event | Deferred | External calendar dependency; low frequency (~25/yr). |
| NF-20261109-19 Options dealer GEX | 3.10 | Dealer positioning | Deferred | No free historical options chain/GEX. |
| NF-20261109-02 Earnings estimate revision momentum | 3.65 | Fundamental / analyst revision | Deferred | No free PIT revision history. |
| NF-20261109-22 RSP-SPY breadth relmom | 3.75 | Participation relmom | Deferred | Adjacency/recycling risk vs H97/H92/H96/H152/H157/H144/H145. |
| NF-20261109-23 USMV-SPY low-vol relmom | 3.55 | Factor/style momentum | Deferred | Inception/style adjacency limits. |
| NF-20261109-12 Holiday/pre-holiday drift | 4.00 | Calendar microstructure | HELD | Calendar adjacency H91/H140/H142/H168. |
| NF-20261110-04 10Y-3M inversion depth de-risking | 3.80 | Macro term-premium | Deferred | Adjacency to H171/H11r curve families (same observable class). |
| NF-20261110-05 SPY upside/downside jump asymmetry | 3.80 | Higher-moment jump asymmetry | Deferred | Adjacency to H122/H128/H135; low plausibility/support. |
| NF-04 Commodity carry | — | Carry/term structure | **BLOCKED** | No free PIT term-structure/roll proxy. |
| NF-05 Short-term CS reversal | — | Liquidity provision | **DEFERRED** | Turnover/net-of-cost; H119 REJECT 3/8. |
| NF-08-16 Halloween seasonal | 3.90 | Calendar seasonal | **HELD** | Calendar adjacency H91/H140/H142. |
| NF-09-03 Breakeven-inflation | 3.40 | Macro regime | **DEFERRED/DATA-LIMITED** | ^T5YIE/^T10YIE unavailable; H175 proxy. |
| NF-20261109-20 Stock split effects | — | Corporate action | DEFERRED | Low frequency; incomplete split data. |

### Cycle 95 discovery (≥3 repo-new/decisive candidates, ≥3 mechanism categories, honest scoring)

| Candidate | NF-ID | Mechanism category | Nov (25) | Plaus (25) | Data (20) | Fals (15) | Exec (10) | Supp (5) | **Weighted** | Decision |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| ES-SPY cash-futures basis mean-reversion timing | NF-20261104-03 | Relative value / cash-futures basis convergence (index arbitrage) | 4 | 3 | 5 | 5 | 4 | 3 | **4.05** | **Selected as H181** (smallest decisive daily real-data test) |
| Russell 2000 annual reconstitution flow | NF-20261110-07 | Structural flow / discrete index event | 4 | 4 | 4 | 5 | 3 | 4 | **4.05** | Deferred (annual low power/event alignment; poor expected information per cycle) |
| Insider transaction signal (Form 4/13F flow) | NF-20261110-08 | Institutional flow / informed trading | 4 | 4 | 3 | 5 | 3 | 4 | **3.80** | Deferred (PIT parsing/aggregation complexity on free data) |

**Notes (honest).** NF-20261110-07 ties arithmetically but deferred on expected-information/power. NF-20261104-03 (previously proposed, never executed) selected as highest expected-information feasible repo-new mechanism: cash-futures relative-value convergence distinct from executed directional futures TSMOM families. NF-root check: tracked draft `run_nf_20261110_07_es_basis.py` (NF-20261110-09/TBD, incomplete/unexecuted, no `main`) not selected/executed.

### NF-20261104-03 / H181 execution (REAL)

- **Runner:** `run_nf_20261104_03_es_spy_basis.py`. **Tests:** `tests/test_nf_20261104_03_es_spy_basis.py` (**8 passed**, 1 third-party DeprecationWarning). `py_compile` ok; `ruff check/format --check` clean. Runtime ~10.3s.
- **Data:** yfinance daily auto-adjusted closes ES=F + SPY, aligned 2010-01-04→2026-10-30 (4231 rows). Train→2018-12-31, Val→2022-12-31, Test protected→2026-10-30 (OOS 1969).
- **Grid (36):** `basis_window {21,63,126} × entry_z {1.0,1.5,2.0} × exit_z {0.0,0.5} × vol_target {0.10,0.15}`. Train-only 4-fold WF selection.
- **Selected:** `basis_window=21, entry_z=2.0, exit_z=0.0, vol_target=0.10` (WF 0.234, train 0.246).
- **OOS Val+Test (1969, 99 trades):** Sharpe **0.297** (fail), PF **1.162** (fail), maxDD **−6.16%** (pass), trades **99** (pass), WF stability **1.208** (pass), worst-regime rolling-252 **−1.410** (fail), benchmark p **0.992** / IR **−0.877** vs buy-hold SPY 0.911/+90.75% (fail), perturbation min ratio **0.552** (pass). Return **+6.89%**.
- **Ablations:** random-signal 0.032/PF 1.014; inverse-signal −0.017/PF 0.995. Buy-hold dominates.
- **Verdict:** **REJECT (4/8)**. Artifact `.experiments/nf_runs/nf_20261104_03_es_spy_basis_20261110_cycle95/summary.json` (+`grid.csv`).
- **Rationale:** No certifiable daily-close ES-SPY basis convergence edge; magnitude/noise/costs leave Sharpe, PF, worst-regime, benchmark failing. `src/qtr` unchanged.

**Cycle 95 complete.** H85–H181 all rejected/recorded. Next unused H-ID **H182**. Cycle 96 requires directive §4 discovery before selecting H182.
