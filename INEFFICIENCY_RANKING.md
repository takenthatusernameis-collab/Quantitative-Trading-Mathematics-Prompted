# Inefficiency Ranking

## Phase 4: Market Ranking & Net Opportunity Estimates

### Ranking Methodology

`Net Opportunity ≈ (Gross Edge − Transaction Costs) × Capacity × (1 − Competition Decay)`,
scored 1–5 on six factors per PROMPT_V2.md. Estimates are updated **after** the
cost-model correction (the previous cost bug inflated trading costs hundreds of
basis points per trade, which had masked the true net edge of every active
strategy; see EXECUTION_REPORT.md). All costs use the corrected equity model:
1 bp commission + 1 bp spread + 0.1 bp per 1% ADV.

---

### Ranked Candidates

#### 1. Time-Series Momentum on Liquid ETFs (executed — H1)
- **Gross Edge (lit.):** Sharpe 0.6–0.8 (Moskowitz et al. 2012).
- **Net edge measured (20 ETFs, 2015-2024, corrected costs):** **OOS Sharpe 0.093**
  (95% CI [-0.76, 0.96]); Train 0.589 → Val 0.245 → **Test -0.039**.
- **Capacity:** $1B+ (ETFs); $10B+ (futures, not tested here).
- **Competition:** High (managed-futures, retail).
- **Net Opportunity Score:** 7/10 (theory) → **2/10 (realized on sample)**.
- **Status: REJECTED by evidence gates** (Sharpe < 1.0, DD -34.8% > 15%,
  PF 1.02 < 1.3, not significant vs EW benchmark p=0.78, train→OOS collapse).
- **Why ranked #1:** strongest provenance and testability; the experiment was
  run first. The realized net opportunity on 2015-2024 is ~zero.

#### 2. Cross-Sectional Momentum on Equity ETFs (executed — H2)
- **Gross Edge (lit.):** Sharpe 0.6–0.9 net of factors (Jegadeesh & Titman 1993;
  Asness et al. 2013).
- **Net edge measured (10 equity ETFs, 2015-2024):** **OOS Sharpe 0.116**
  (95% CI [-0.71, 1.02]); Test 0.092.
- **Capacity:** $500M+.
- **Net Opportunity Score:** 5/10 (theory) → **2/10 (realized)**.
- **Status: REJECTED** (Sharpe < 1.0, DD -38.7%, PF 1.02, p=0.57; only trade-count passes).
- **Why:** most-replicated anomaly; cleanest test. The realized edge is ~zero,
  consistent with heavy crowding and momentum-crash events.

#### 3. Carry / Term Structure (reviewed, NOT executed)
- **Gross Edge:** Sharpe 0.8–1.2 (Koijen et al. 2018).
- **Net edge (estimated):** Sharpe 0.5–0.8 after costs; **but** 2021–22 bond
  massacre and 2008 replay risk; requires futures/contango roll data not on the
  free Yahoo pipeline.
- **Capacity:** $500M+ (diversified).
- **Net Opportunity Score:** 6/10 (theory) → withheld (data gap).
- **Status: DEFERRED.** Invalidated if 2022-style yield-curve repricing repeats
  without futures roll to capture the roll-down.

#### 4. Mean Reversion on Intraday Data (reviewed, NOT executed)
- Requires tick/1-min data + low-latency infra. Net sharpe estimated 0.2–0.5 after
  HFT costs. **Net Opportunity Score: 3/10.** Rejected by execution feasibility.

#### 5. Regime-Switching Momentum (control, reviewed)
- Switches momentum exposure off in bear regimes. Theory suggests crash-mitigation.
- **Net Opportunity Score: 4/10.** Strong candidate for the *next* cycle: gating
  momentum on a VIX / vol-regime filter is the natural fix for the cash found
  here (bear-regime Sharpe ≈ -2.4 to -3.0).

---

### Invalidation Criteria (updated with measured outcomes)

**TS Momentum invalidated** (and the experiment confirms it on this sample) if:
- OOS Sharpe < 0.5 → **measured 0.093** ✓ invalidated on this sample.
- Max drawdown > 25% in a 12-month period → **measured -34.8% (2020+2022)**.
- Bear-regime Sharpe < 0 → **measured -2.40** (VIX > 30 periods).
- Train Sharpe − OOS Sharpe > 0.4 → **0.589 − 0.093 = 0.496** (overfit).

**CS Momentum invalidated** if:
- OOS Sharpe < 0.5 → **0.116**; worst-regime Sharpe < 0 → **-3.03**.

---

### Universe Used (final)

20 liquid ETFs across 5 asset classes (+ ^VIX for regime labels only):
- Equities (6): SPY, QQQ, IWM, EFA, EEM, VWO
- Bonds (3): TLT, AGG, HYG
- Commodities (4): GLD, USO, PDBC, GSG
- Currencies (3): UUP, FXE, FXY
- Intl / REIT (4): VNQ, EWJ, EWZ, INDA

`EGGV` (from the draft spec) was dropped — delisted/no data on Yahoo. Futures
(ES, NQ, CL, GC, ZB) were excluded: yfinance futures require `=F` tickers and the
engine's per-contract cost path is unimplemented/untuned; this is a documented
scope decision (see NEXT_TASK.md).

### Cost Model (corrected)
- ETFs: 1 bp commission + 1 bp spread + 0.1 bp per 1% ADV participation.
- Verified: buy-and-hold SPY cost ≈ 3 bps round-trip; buy-and-hold EW-20
  Sharpe 0.295 (vs 0.685 single SPY due to 2022 bond/commodity drag — *not* costs).

### Capacity Estimates
- ETFs: $1B+ (based on $100M+ ADV); 2022 stress showed several ETFs (USO) with
  extreme single-day gap risk that would impair scaling — a separate capacity risk.
