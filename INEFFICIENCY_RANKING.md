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

**Cross-cutting finding (H1→H6):** train→OOS decay is the dominant
failure mode (H1: 0.589→0.093; H2: 0.636→0.116; H3: 0.401→-0.868; H4: 0.712→0.376;
H5: 0.797→0.509; H6: 0.882→0.708). Walk-forward selection on 2015-2019 daily data selects noise;
no momentum-family variant tested has positive OOS Sharpe ≥ 1.0 on 2020-2024.
The momentum family is **exhausted on free daily data** — the strongest result
remains the H5 VIX-gate ablation at OOS Sharpe 0.711 — see NEXT_TASK.md for the
next pivot.

---

### 7. VIX-Gated + DDCV Combo on Futures TSMOM (executed — H6, REJECTED)
- **Net edge measured** (ES/NQ/CL/GC/ZB `=F`, 2015-2024, corrected cost model):
  best combo (dd_trigger=0.10, dd_factor=0.50) **OOS Sharpe 0.708**,
  max DD -19.7%, PF 1.160, 188 trades, IR 0.360 vs EW futures benchmark
  (p=0.422). Train Sharpe 0.882 → OOS 0.708.
- **VIX+DDCV grid** (6 combos): all land in OOS Sharpe 0.707–0.708, max DD
  -19.7% to -19.8% — the DDCV layer adds minimal incremental DD reduction
  (0.3%) on top of the VIX gate.
- **Ablations** (OOS): base TSMOM Sharpe 0.495 / DD -38.5%; VIX-gate only
  Sharpe 0.711 / DD -20.0%; DDCV-only Sharpe 0.509 / DD -35.3%; **VIX+DDCV
  Sharpe 0.708 / DD -19.7%** (best on both dimensions among all H1-H6).
- **Walk-forward stability: 0.803 (PASS)** — the only H1-H6 variant to pass
  this gate. IR > 0 (PASS).
- **Net Opportunity Score:** 3/10 (realized) — highest of the family but still
  below the ≥1.0 Sharpe gate.
- **Status: REJECTED.** 6/8 gates fail. The combination is the best-performing
  variant in the entire momentum family (highest Sharpe, lowest DD, passes
  stability and IR gates), but the signal strength on 2015-2024 free daily data
  is fundamentally insufficient to clear the PROMPT_V2 evidence gates. The
  DDCV layer is redundant when VIX-gating is present; the VIX gate alone
  achieves nearly identical results. The remaining gap is a signal-strength
  ceiling, not a vol-management problem.
- **What would invalidate the rejection:** higher-frequency (intraday) futures
  data for CT-style path-dependent trend following, a futures roll-yield model
  capturing true roll-date P&L, or extending the sample to pre-2015 decades
  where TSMOM literature reports stronger edges.

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

`EGGV` (from the draft spec) was dropped — delisted/no data on Yahoo. Starting
with H4, futures (`=F` continuous contracts) were added to the universe: ES, NQ,
CL, GC, ZB (all 5 available). The engine's futures per-contract cost path was
already implemented in `src/qtr/backtest/engine.py::_calculate_costs`
(`contracts_traded = weight * capital / (price * multiplier)`, cost per
contract from `futures_specs`). See H4/H5 sections below.

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

#### 6. Drawdown-Conditioned Vol Targeting on Futures TSMOM (executed — H5, REJECTED)
- **Net edge measured** (ES/NQ/CL/GC/ZB `=F`, 2015-2024, corrected cost model):
  best DDCV combo (dd_trigger=0.30, dd_factor=0.75) **OOS Sharpe 0.509**,
  max DD -35.3%, PF 1.108, 188 trades, IR 0.394 vs EW futures benchmark
  (p=0.379). Train Sharpe 0.797 → OOS 0.509.
- **DDCV grid** (6 combos): all land in OOS Sharpe 0.498–0.509, max DD
  -31% to -33% — the DD condition reduces drawdown by ~8% relative but does
  **not** bring it below the 15% gate.
- **Ablations** (OOS): base TSMOM Sharpe 0.495 / DD -38.5%; fixed 50% vol-cut
  Sharpe 0.495 / DD -19.2% (would pass DD gate but same Sharpe); **VIX-gate
  Sharpe 0.711 / DD -20.0%** (best on both dimensions).
- **Net Opportunity Score:** 2/10 (realized) — even the best variant
  (VIX-gated) stays below the ≥1.0 Sharpe gate.
- **Status: REJECTED.** 7/8 gates fail. DDCV adds no Sharpe benefit over a
  blunt vol cut; the DD gate is a risk-scaling problem, not a drawdown-timing
  problem. The VIX-gate ablation confirms regime-level exposure cuts are more
  effective than portfolio-level DD conditioning on this sample.
- **What would invalidate the rejection:** futures roll-yield model that
  captures true roll-date P&L (the `=F` continuous contracts may smooth this),
  or higher-frequency data for a CT-style path-dependent trend system.

#### 7. Multi-Horizon TSMOM with Regime-Weighted Blending + Path-Dependent Exits (executed — H7, REJECTED)
- **Net edge measured** (ES/NQ/CL/GC/ZB `=F`, 2018-2024, daily approximation; Train 2018-2020, Val 2021-2022, Test 2023-2024 protected):
  **OOS Sharpe 0.789**, max DD -14.5%, PF 1.166, 1005 trades, WF stability 1.0. Train Sharpe 0.738, Val 0.188, Test 1.269 (asymmetric performance).
- **Gates:** trades PASS, DD PASS (boundary), WF stability PASS, IR/perturbation regime flags mixed; **Sharpe FAIL (0.789<1.0)**, PF FAIL (1.166<1.3). Overall REJECT.
- **Takeaway:** Multi-horizon regime-weighted blending produces strong test period but weak 2021–2022 Val (choppy regimes). Daily-approximated path exits reduce DD to boundary but cannot lift Sharpe above 0.79 on 2018–2024 daily data. Frequency (intraday) remains the untested dimension.
- **Net Opportunity Score:** 2/10 (realized). Signal strength ceiling persists on daily data.
- **What would invalidate the rejection:** true intraday (1–5 min) implementation with tick-level trailing/time/vol stops, roll-yield capture from contract rolls (continuous `=F` may mask), or extended sample pre-2015 where literature reports stronger TSMOM.

---

#### 8. Roll-Adjusted Futures TSMOM (executed — H8, REJECTED)

- **Net edge measured** (ES/NQ/CL/GC/ZB `=F`, 2015-2024, corrected cost model):
  roll-carry weight w=0.50 selected by Val Sharpe (0.900). **OOS Sharpe
  0.814**, max DD -20.9%, PF 1.157, 201 trades, WF stability 0.883,
  worst-regime Sharpe -1.914 (sideways), IR 0.525 vs EW futures benchmark
  (p=0.241, α=+4.8%/yr). Train Sharpe 0.922 → Val 0.900 → Test 0.753.
- **Roll-carry weight grid** (5 configs, sorted by Val Sharpe):

  | w | Train SR | Val SR | Test SR | OOS SR | OOS DD | OOS PF | OOS Trades |
  |---|----------|--------|---------|--------|--------|--------|------------|
  | 0.50 | 0.922 | 0.900 | 0.753 | 0.814 | -20.9% | 1.157 | 201 |
  | 0.25 | 0.955 | 0.863 | 0.756 | 0.798 | -21.0% | 1.154 | 200 |
  | 1.0 | 0.982 | 0.862 | 0.752 | 0.797 | -20.4% | 1.153 | 201 |
  | 0.0 (base) | 0.936 | 0.847 | 0.768 | 0.797 | -21.1% | 1.154 | 197 |
  | 2.0 | 1.036 | 0.687 | 0.658 | 0.666 | -21.9% | 1.128 | 201 |

- **Ablation**: base TSMOM (w=0.0, no roll adjustment) OOS Sharpe 0.797.
  Roll adjustment (w=0.50) improves OOS Sharpe by ~2.1% relative (0.797 →
  0.814) and is the **best-performing variant** of the entire momentum family
  (H1–H8) on both OOS Sharpe and IR (0.525 vs H6's 0.360).
- **Roll detection**: calendar-based (last BD of roll months) + volume spikes
  + overnight gaps. 63–263 roll dates detected per symbol (ES, NQ, ZB
  quarterly; CL, GC monthly). The overnight gaps on roll dates are small
  (ES/NQ ≤ 0.5%, CL/GC ≤ 2%), so the roll-adjustment effect is limited.
- **Net Opportunity Score:** 3/10 (realized) — the highest of the family but
  still below the ≥1.0 Sharpe gate.
- **Status: REJECTED.** 5/8 gates fail. Roll-yield capture provides a modest
  Sharpe lift (0.797 → 0.814) but the Sharpe, PF, DD, worst-regime, and
  benchmark-significance gates remain unmet. The roll carry is a second-order
  effect on `=F` continuous returns that already embed roll yield.
- **What would invalidate the rejection:** individual futures contract data
  with explicit roll timing (not `=F` continuous), intraday futures data for
  CT-style path-dependent exits, or pre-2015 sample extension.

---

### Updated Cross-Family Summary (H1→H9)

The momentum family has been tested exhaustively on free daily data (2015-2024) and intraday data (H9):

| Hypothesis | OOS Sharpe | OOS Max DD | OOS PF | OOS Trades | IR vs BH | Verdict |
|------------|-----------|-----------|-------|-----------|----------|---------|
| H1 (TS, 20 ETFs) | 0.093 | -34.8% | 1.017 | 768 | -0.124 | REJECT |
| H2 (CS, 10 ETFs) | 0.116 | -38.7% | 1.024 | 388 | -0.252 | REJECT |
| H3 (Regime-gated) | -0.868 | -48.3% | 0.832 | 1239 | -0.893 | REJECT |
| H4 (Futures TSMOM) | 0.376 | -47.4% | 1.085 | 177 | 0.332 | REJECT |
| H5 (DDCV) | 0.509 | -35.3% | 1.108 | 188 | 0.394 | REJECT |
| H6 (VIX+DDCV) | 0.708 | -19.7% | 1.160 | 188 | 0.360 | REJECT |
| H7 (Multi-horizon, daily) | 0.789 | -14.5% | 1.166 | 1005 | ~0 | REJECT |
| H8 (Roll-adjusted) | 0.814 | -20.9% | 1.157 | 201 | 0.525 | REJECT |
| **H9 (Intraday TSMOM + CT exits)** | **1.056** | **-6.2%** | 1.252 | 2690 | 1.021 | REJECT (PF only) |
| **H10 (Intraday TSMOM + PF opt)** | **1.276** | **-5.8%** | **1.304** | 2416 | 0.925 | **PASS** |
| **H11 (Robustness certification of H10)** | **1.276** (reproduced bit-exactly) | **-5.8%** | **1.304** | 2416 | 0.925 | **PASS (certified robust)** |

**Best OOS Sharpe across all hypotheses: 1.276 (H10).**
**Best max DD: -5.8% (H10).**
**Best profit factor: 1.304 (H10) — clears the 1.3 gate for the first time.**
The momentum family shows monotonic improvement H4→H10 (0.376→1.276 Sharpe, -47.4%→-5.8% DD).
The frequency dimension (H9/H10) is the breakthrough: intraday data resolves the worst-regime
failure (all regime sharpes > 0) and delivers the first Sharpe ≥ 1.0 result.
**H10 clears the final bottleneck (profit factor ≥ 1.3)** via a longer 4-week portfolio-vol
estimation window (1008h) plus an exit-parameter grid (trailing 2.0×, vol_limit 1.5×,
vol_floor 0.25). Signal smoothing and regime scaling were not selected.
**Net Opportunity Score: 7/10 (realized) — first and only hypothesis to pass all 8 gates.**

### Invalidation Criteria (updated with H8)

**Roll-adjusted futures TSMOM invalidated** (H8) — does not clear gates:
- OOS Sharpe < 1.0 → **0.814** (improves monotonically but still fails).
- Max drawdown > 15% → **-20.9%**.
- Worst-regime Sharpe < 0 → **-1.914** (sideways, captures 2020-2021).
- Benchmark IR not significant → **p=0.241, α=+4.8%/yr (not significant)**.
#### 9. Intraday Futures TSMOM with CT-Style Path-Dependent Exits (executed — H9, REJECTED)

- **Net edge measured** (ES/NQ/CL/GC/ZB `=F` hourly, ~730 days from yfinance; Train/Val/Test split on available window):
  **OOS Sharpe 1.056**, max DD -6.2%, PF 1.252, 2,690 trades, WF stability 0.793, worst-regime Sharpe 0.758 (bear), IR 1.021 vs EW futures benchmark (p=6.3e-12).
- **Ablations** (OOS):
  | Variant | OOS Sharpe | OOS Max DD | OOS PF | OOS Trades |
  |---------|-----------|-----------|--------|------------|
  | H9 full (CT exits) | **1.056** | **-6.2%** | 1.252 | 2,690 |
  | Daily target, no CT exits | 1.162 | -6.2% | 1.261 | 1,819 |
  | Raw hourly, no exits | -0.141 | -25.3% | 0.988 | 31,492 |
- **Regime Sharpe**: bull 1.13, sideways 0.97, bear 0.76 — **all positive**, worst-regime gate PASSES for the first time in the momentum family.
- **Gate status**: 7/8 PASS — only profit factor fails (1.252 < 1.3). This is the **closest any hypothesis has come to full PASS**.
- **Takeaway**: The frequency pivot works — hourly data + CT exits delivers the highest Sharpe and lowest DD of the entire H1–H9 family. The binding constraint is **cost-adjusted edge (profit factor)**, driven by high hourly turnover (2,690 trades in ~2 years). CT exits control DD but don't improve PF; the raw hourly signal fails catastrophically (noise + excessive turnover).
- **Data limitation**: yfinance hourly `=F` limited to ~730 days; sample is Oct 2022–Oct 2024. The small sample is a known limitation.
- **Net Opportunity Score:** 4/10 (realized) — highest of the family; Sharpe and DD gates finally clear, PF is the last hurdle.
- **Status: REJECTED** (profit factor gate). The hypothesis that intraday TSMOM can achieve Sharpe ≥ 1.0 is **supported**; the cost-adjusted edge needs refinement.
- **What would invalidate the rejection:** A modest turnover reduction or cost efficiency gain that pushes PF ≥ 1.3 while maintaining Sharpe ≥ 1.0; extending the intraday data window (requires paid data); alternative exit parameterization reducing whipsaw trades.

#### 10. Intraday Futures TSMOM — Profit Factor Optimization (executed — H10, PASS)

- **Net edge measured** (ES/NQ/CL/GC/ZB `=F` hourly, ~730 days from yfinance; Train 55% / Val 25% / Test 20% protected):
  **OOS Sharpe 1.276**, max DD -5.8%, PF 1.304, 2,416 trades, WF stability 0.781,
  worst-regime Sharpe 1.046 (bull), IR 0.925 vs EW futures benchmark (p=4.8e-10).
- **Full 13,824-combo grid** (signal smoothing / vol-window / regime-scaling / min-trade-interval
  / exit-parameter) evaluated in 0.48 CPU-h; selected by Val Sharpe; Test never entered selection.
- **Selected config**: vol_window_long=1008 (4-week vol window), smooth_span=none,
  regime_scaling=False, min_trade_interval=0, trailing_mult=2.0, max_hold_bars=60,
  vol_limit_mult=1.5, vol_floor_fraction=0.25.
- **Ablations** (OOS):
  | Variant | OOS Sharpe | OOS Max DD | OOS PF | OOS Trades |
  |---------|-----------|-----------|--------|------------|
  | H9 baseline (vw=252, H9 exits) | 1.066 | -6.2% | 1.253 | 1,795 |
  | Longer vol window only (vw=1008) | 1.142 | -5.8% | 1.273 | 1,721 |
  | Regime scaling only | 1.021 | -6.2% | 1.249 | 1,830 |
  | Min trade interval only (mi=8) | 1.087 | -6.3% | 1.254 | 809 |
  | Exit grid best (selected config) | **1.276** | **-5.8%** | **1.304** | 2,416 |
  → The **longer vol window alone** recovers most of the Sharpe/PF gain; the **exit grid**
  delivers the final PF push (1.304) and the highest Sharpe (1.276). Signal smoothing and
  regime scaling were not selected.
- **Regime Sharpe**: bull 1.046, sideways 1.170, bear 1.753 — all positive; worst-regime
  gate passes comfortably. Bear is the strongest regime (momentum pays in trends).
- **Gate status**: 8/8 PASS → **OVERALL: PASS** (first hypothesis in the H1–H10 family to
  clear all gates).
- **Data limitation**: yfinance hourly `=F` limited to ~730 days (2024-10-13 → 2026-10-09).
  Small sample but a true OOS stress test; coverage gaps filled by ffill/bfill.
- **Infrastructure defect found and fixed during H10 execution:** the script did not
  normalize the tz-aware (America/New_York) yfinance futures index to tz-naive before
  reindexing against the tz-naive hourly VIX index (TypeError). Fixed with `tz_convert(None)`;
  also removed a duplicated `pos[i] = cur_pos` block in `apply_exits_hourly`.
- **Net Opportunity Score:** 7/10 (realized) — highest of the family; first and only
  hypothesis to pass all 8 gates.
- **Status: PASS.** The hypothesis that a turnover-aware intraday TSMOM variant can achieve
  PF ≥ 1.3 while maintaining Sharpe ≥ 1.0 and DD ≤ 15% is **supported**.
- **What would invalidate the PASS (if re-run):** a different seed/data window producing
  PF < 1.3 or Sharpe < 1.0; a longer intraday data window (paid data) that changes the
  vol-window/exit-parameter ranking; a cost-model misspecification at ~2,400-trade turnover.

---

#### 11. Robustness / Certification of the H10-selected config (executed — H11, PASS)

- **Net edge measured** (frozen H10 config, ES/NQ/CL/GC/ZB `=F` hourly,
  2024-10-13 → 2026-10-09; 0.016 CPU-h): the H10 result reproduces
  **bit-exactly** (OOS Sharpe 1.275759, PF 1.304165, DD −5.843%,
  2,416 trades, WF stability 0.780571, worst-regime SR 1.045718,
  p 4.79e-10, IR 0.924789 — all 8 gates re-verified, max |Δ| = 0 vs
  the H10 artifact).
- **E1 seed robustness:** deterministic pipeline — seeds {42, 7, 123, 2026}
  give bit-identical equity curves (seeds are inert; no stochastic
  component). Bootstrap OOS Sharpe 95% CI **[0.839, 1.698]**,
  P(Sharpe ≥ 1.0) = 0.888 (2,000 resamples).
- **E2 ±20% perturbation (10 OAT + 2 joint):** min perturbed OOS
  Sharpe **1.027 = 0.805 × optimum** — the previously-unevaluated
  `min_perturbed_sharpe_ratio` gate (≥ 0.5) **PASSES**. All 14
  variants keep Sharpe ≥ 1.0. Most sensitive: `vol_limit_mult`
  (1.052 at −20%) and `target_vol` (1.027 at −20%).
- **E3 cost stress (±50%):** PF 1.308 (0.5×) / 1.300 (1.5×) —
  **PASS**; break-even cost multiplier for PF = 1.3 is **1.542×**.
  Doubling all costs moves PF by only −0.008 (per-trade cost is
  ~0.3 bp of equity at this turnover).
- **E4 window diagnostics:** Sharpe ≥ 1.0 on all shifted splits
  (50/25/25 → 1.204; 60/20/20 → 1.365; 45/30/25 → 1.234) and
  93.75% of 16 rolling 25%-windows (min 0.709). Shifted-window
  (50/25/25) coarse-grid re-selection (324 combos) **re-selects the
  identical config** (vw=1008, tm=2.0, mhb=60, vlm=1.5, vff=0.25) —
  the selection is stable, but the shifted-window OOS PF is 1.281
  (< 1.3). Live (uncached) fetch confirms **no fresh bars beyond
  2026-10-09** — the free source is hard-limited to ~730 hourly days.
- **E5 per-symbol concentration:** HHI(|P&L| shares) = **0.214**
  (equal-weight = 0.200), max gross-profit share 0.233, all 5 symbols
  positive OOS Sharpe (0.337–0.797) — the edge is **diversified**,
  not concentrated. CL carries 68% of turnover (1,652/2,416 trades)
  but only 21% of P&L.
- **Verdict: PASS** — the H10 certification is robust on the
  pre-registered window.
- **Critical caveat (the thin margin):** OOS PF 1.304 clears the 1.3
  gate by only **+0.004 (+0.3%)**. Under +50% costs PF = 1.300
  (margin +0.0003); on shifted OOS windows PF = 1.281–1.292 (gate
  fails). **Sharpe is the robust metric; profit factor is the
  fragile one.** Any H12+ work must treat PF-margin, not Sharpe, as
  the binding constraint.
- **Net Opportunity Score:** 7/10 (realized) — unchanged; the
  certification adds confidence, not new edge.
- **Status: PASS (robustness-certified).**
- **What would invalidate it:** fresh hourly bars (paid data) pushing
  OOS PF < 1.3 or Sharpe < 1.0; a cost-model misspecification
  > 1.54×; a ±20% perturbation region with OOS Sharpe < 0.638
  (currently worst case 1.027); evidence that CL's 68% turnover
  share is a roll-date artifact of the `=F` continuous contract.
