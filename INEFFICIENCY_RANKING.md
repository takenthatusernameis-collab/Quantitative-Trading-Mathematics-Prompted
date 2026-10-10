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

#### 5. Regime-Switching Momentum (executed — H3)
- VIX-gated momentum exposure (bull 1.0 / sideways 0.25 / bear 0.10)
  + VXX crisis hedge (long only when VIX > 30).
- **Net edge measured (20 ETFs + VXX, 2015-2024):** **OOS Sharpe
  -0.868** (95% CI [-1.69, -0.00]); Train 0.401 → Val -0.548 →
  **Test -1.102**. Selected config: short-allowed, 63-day lookback,
  skip 21, hedge ablated (0.0).
- **Crash mitigation WORKS:** 2020-03 DD **-1.5%**, 2022 DD **-2.7%**
  (gate ≤ 20% — both PASS), vs -34.8% / -38.7% max DD in H1/H2.
  Worst-regime Sharpe is *sideways* (-2.07), not bear (-0.66).
- **Net Opportunity Score:** 4/10 (theory) → **1/10 (realized)**.
- **Status: REJECTED** (8/10 gates fail; alpha -11.98%/yr, IR -0.89,
  p=0.046 — significantly *worse* than EW benchmark; PF 0.83; DD -48%).
- **Why it failed:** the VIX<20 "bull" definition misclassifies
  2020-2021 (VIX 20-30 = "sideways" at 25% exposure) — exposure was
  cut during the strongest momentum stretch while the short side bled
  in the bull market. The regime *mechanism* (crash gating) is
  validated; the *signal* has no positive edge on this sample.
- **What would invalidate the rejection:** a regime definition that
  does not procyclically cut bull exposure (e.g., VIX *change* or
  trend-based regimes), or futures-based TSMOM where the literature
  edge is strongest (deferred — see NEXT_TASK.md).

---

### Invalidation Criteria (updated with measured outcomes)

**TS Momentum invalidated** (and the experiment confirms it on this sample) if:
- OOS Sharpe < 0.5 → **measured 0.093** ✓ invalidated on this sample.
- Max drawdown > 25% in a 12-month period → **measured -34.8% (2020+2022)**.
- Bear-regime Sharpe < 0 → **measured -2.40** (VIX > 30 periods).
- Train Sharpe − OOS Sharpe > 0.4 → **0.589 − 0.093 = 0.496** (overfit).

**CS Momentum invalidated** if:
- OOS Sharpe < 0.5 → **0.116**; worst-regime Sharpe < 0 → **-3.03**.

**Regime-gated momentum invalidated** if:
- OOS Sharpe < 0.5 → **-0.868**; crisis-DD gate PASSED (**-1.5% / -2.7%**)
  but worst-regime (sideways) Sharpe < 0 → **-2.07**; alpha < 0 →
  **-11.98%/yr (IR -0.89, p=0.046)**.

**Cross-cutting finding (H1→H3):** train→OOS decay is the dominant
failure mode (H1: 0.589→0.093; H2: 0.636→0.116; H3: 0.401→-0.868).
Walk-forward selection on 2015-2019 daily ETF data selects noise;
no momentum-family variant tested has positive OOS alpha on
2020-2024. The momentum family is **exhausted on free daily ETF
data** — see NEXT_TASK.md for the futures/contango pivot.

---

### Universe Used (final)

20 liquid ETFs across 5 asset classes (+ ^VIX for regime labels;
+ VXX as H3's crisis-hedge leg, ablated by selection):
- Equities (6): SPY, QQQ, IWM, EFA, EEM, VWO
- Bonds (3): TLT, AGG, HYG
- Commodities (4): GLD, USO, PDBC, GSG
- Currencies (3): UUP, FXE, FXY
- Intl / REIT (4): VNQ, EWJ, EWZ, INDA
- Crisis hedge: VXX (Yahoo history from 2018-01-25; -97% total
  return 2018-2024, 75% annualized vol — contango decay)

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

- **H4 (executed 2026-10-10, REJECTED)**: Futures TSMOM + ensemble
  selection on ES/NQ/CL/GC/ZB `=F` continuous contracts. A sign-inversion
  bug in the first H4 run (signal was mean-reversion, not trend-following)
  was found and fixed; the canonical TSMOM was moved to the shared library
  `src/qtr/strategies/baselines.py` and pinned by
  `tests/test_tsmom_signal.py`. Corrected result: ensemble OOS Sharpe
  0.376, best single combo 0.786, IR 0.33 (positive alpha vs equal-weight
  futures benchmark), but DD −47% and 177 trades — fails all gates.
  Ranking: futures rank **above ETFs** for raw TSMOM edge (positive OOS
  alpha, IR 0.33 vs −0.89 for H3), but still cannot certify the
  PROMPT_V2 Sharpe ≥ 1.0 / DD ≤ 15% gate. See HYPOTHESIS_SPEC.md H4.
