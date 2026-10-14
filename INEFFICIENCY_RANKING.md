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


#### 12. Selection-Bias Audit (executed 2026-10-13 — H12, **PASS**)

**Status: Executed — PASS.** Artifacts:
`.experiments/artifacts/exp_2026-10-13T12-51-06-515939Z/`
(39.1 min, 0.652 CPU-h). Script:
`run_h12_selection_bias_audit.py`; regression tests:
`tests/test_h12_selection_bias.py` (78/78 passing).

- **(1) Deflated Sharpe Ratio (Bailey & López de Prado 2014),**
  N=13,824 trials, moments of the preserved per-combo
  Val-Sharpe distribution (mean 0.962, SD 0.158) + the
  selected config's Val-return moments (skew 1.415,
  kurtosis 29.13, 2,860 bars): expected max SR under the
  null = **0.6214** vs observed best-of-N Val SR **1.4134**
  (+2.86 grid SD). **DSR-adjusted Sharpe 1.4094, p = 0.00283**
  ⇒ the selection is distinguishable from the expected
  maximum of 13,824 random trials (gate: DSR ≥ 1.0).
- **(2) PBO via CSCV** (grid re-run logging per-combo OOS
  returns; S=12 blocks, T=5,148 OOS bars, 924 combinations):
  **PBO = 0.0552** (gate: < 0.3 pre-registered strict /
  < 0.5 H0). Median OOS rank of the IS-optimal config =
  1,716/13,824 (top 12%); the IS-optimal config ranks in
  the OOS bottom half in only 5.5% of CSCV combinations.
  The re-run reproduces the H10 OOS metrics of the selected
  config bit-exactly (Sharpe 1.275759, PF 1.304165).
- **(3) Family-wide multiple testing:** pooled N = **14,389**
  (H1:18, H2:54, H3:108, H4:18, H5:6, H6:6, H8:5,
  H10:13,824, H11:350). DSR (family) = **1.4093**
  (p = 0.00288); benchmark p 4.79e-10 → Bonferroni
  **6.89e-06**, BH-FDR **6.89e-06**, Šidák ≈ 6.89e-06 —
  all < 0.05. The H10 OOS benchmark alpha survives
  family-wide correction.
- **(4) PF-margin diagnostic:** selected Val PF 1.3527
  (rank 9/13,824); Val PF quantiles 5%/50%/95% =
  1.176/1.243/1.308. Fraction of combos with PF ≥ 1.3:
  **7.26% Val vs 0.32% OOS** — the PF gate is heavily
  selection-pressured on Val, but the selected config
  also clears it OOS (1.304, margin +0.004).
- **Verdict: PASS** — the H10 result is not a selection
  artifact: best-of-N Sharpe is 2.3× the null-expected
  maximum, CSCV finds no overfitting (PBO 0.055), and the
  benchmark alpha is significant after Bonferroni/BH/Šidák
  correction at the pooled family trial count.
- **Caveats carried forward:** (a) CSCV's exchangeability
  assumption holds only approximately for a correlated
  candidate grid — the low PBO partly measures selection
  *stability within* the family, not independence across
  families; (b) the PF margin (+0.004) remains the fragile
  gate; (c) single ~2-year hourly sample and the free-data
  horizon limit (no bars beyond 2026-10-09) bound the
  statistical power — both require a paid data source.
- **Net Opportunity Score:** 7/10 (realized) — unchanged;
  the audit adds statistical confidence, not new edge.


#### 13. OOS-Level Deflation & PF-Margin Fragility Audit (executed 2026-10-13 — H13, **REJECT** on the fragility axes)

**Status: Executed — REJECT (2 of 3 pre-registered
fragility nulls could not be rejected).** Artifacts:
`.experiments/artifacts/exp_2026-10-13T14-35-58-316759Z/`
(< 0.1 CPU-h, artifact-reuse-only). Script:
`run_h13_oos_deflation_pf_audit.py`; regression tests:
`tests/test_h13_oos_deflation_pf.py` (105/105 passing).

- **(1) OOS worst-case deflation — PASS.** DSR of the
  selected config's OOS Sharpe (1.275759) under the
  worst-case assumption that OOS had been the selection
  metric with N=13,824 trials (OOS-Sharpe grid moments
  from the H12 re-run: mean 0.9363, SD 0.1547;
  OOS-return moments: skew 1.006, kurtosis 22.45,
  5,148 bars): expected max SR under the null =
  **0.6095**; **DSR-adjusted OOS Sharpe 1.2745,
  p = 0.00102** (gate ≥ 1.0). Single-peek (N=1, the
  true deflation of one OOS evaluation): DSR =
  **1.2758**, p < 1e-06. The OOS Sharpe survives even
  the absurd peeking bound.
- **(2) PF bootstrap 95% CI — FAIL.** 2,000 seeded
  i.i.d. resamples of the OOS net returns: CI =
  **[1.1900, 1.4248]** (median 1.3022),
  **P(PF ≥ 1.3) = 51.7%** (gate: CI lower bound
  ≥ 1.3). The observed PF 1.304 is statistically
  indistinguishable from the 1.3 gate — the margin
  (+0.004) is ~30× smaller than the CI half-width
  (±0.117).
- **(3) Symbol dispensability — FAIL.** Net per-symbol
  OOS decomposition (per-symbol gross P&L −
  per-symbol costs; reconstruction max |Δ| vs engine
  net returns = 6.9e-18): ES=F net PF 1.218 (P&L
  share 0.214), NQ=F 1.237 (0.242), **CL=F 1.358
  (0.215)**, GC=F 1.224 (0.232), ZB=F 1.118 (0.097).
  Leave-one-out pooled OOS PF: ES 1.3070 ✓,
  NQ 1.3006 ✓, **CL 1.2494 ✗**, **GC 1.2821 ✗**,
  ZB 1.3114 ✓ (gate: every removal keeps PF ≥ 1.3).
  **CL=F and GC=F are indispensable** — the margin
  is single-symbol-dependent.
- **(4) Shifted splits — confirmed bit-exactly**
  (positions fixed, only the OOS mask changes):
  50/25/25 → PF 1.2806 (SR 1.2035), 60/20/20 →
  1.3298 (SR 1.3651), 45/30/25 → 1.2916
  (SR 1.2336) — all reproduce the H11 E4a values
  with |diff| = 0. The two gate-failing splits are
  driven by **CL=F** (net-PF delta −0.076 / −0.084
  vs base OOS) and the **bull regime** (PF delta
  −0.029 / −0.013).
- **(5) Cost break-even — verified.** Fine sweep +
  bisection: **1.5420×** (H11 interpolated 1.5418×,
  |Δ| = 0.0002). Doubling all costs moves OOS PF by
  only −0.008 — costs are NOT the fragility driver.
- **Root-cause attribution.** The H10 PASS rests on a
  PF margin (+0.004) that is (a) within bootstrap
  sampling noise (48.3% of resamples fall below the
  1.3 gate), and (b) carried by the two highest-PF
  symbols — CL=F (the only symbol whose net PF, 1.358,
  exceeds the pooled 1.304) and GC=F (whose losses
  offset other symbols' loss bars). The Sharpe edge is
  deflation-robust; the PF gate is not.
- **Net Opportunity Score:** 6/10 (realized) — the
  certified edge is real in Sharpe terms but the PF
  certification is fragile; any production use requires
  a longer OOS window (paid data) or a PF-targeted
  re-optimization with the PF margin as the selection
  metric.


### H14 (2026-10-13): PF-margin fragility is a family property
From top-50 by Val PF margin (K=50, excluding H10), none satisfied all three H13 gates (PF bootstrap CI LB≥1.3, worst-case DSR-adj OOS Sharpe≥1.0 at N=K, all symbols dispensable). The failure is driven by symbol dispensability (CL=F/GC=F indispensable) rather than Sharpe deflation. Cost is not the driver (H13). Remedy requires longer OOS window (paid data) or different construction (PF-targeted exits).

---

### 14. Cross-Sectional Equity Factor Timing (Value/Momentum/Quality Rotation) (executed 2026-10-13 — H16, **REJECTED**)

- **Net edge measured** (9 factor ETFs — VLUE/IJS/VTV, MTUM/QQQ/SPYG,
  QUAL/SPHQ/USMF — Yahoo daily 2010-2024, point-in-time universe,
  corrected equity cost model): selected config (lookback=63, skip=5,
  regime triple 1.0/0.5/0.25, n_factors=2, selected by train-only
  4-fold walk-forward Sharpe = 1.107) **OOS Sharpe 0.579**, max DD
  -19.95%, PF 1.106, 184 trades, WF stability 0.353, worst-regime
  Sharpe -3.680 (bear), IR -0.353 vs EW benchmark (p = 0.351,
  α = +1.24%/yr). 3.9 s, 0.001 CPU-h.
- **Regime Sharpe**: bull 2.801, sideways -1.929, bear -3.680.
- **Ablations (OOS)**: ungated full exposure 0.758 / DD -30.9%;
  EW benchmark 0.606 / DD -34.9%; value family -0.028; momentum
  family 0.819; quality family 0.555.
- **Gates**: 1/9 PASS (only the ±20% perturbation gate, min ratio
  0.734). **Status: REJECTED.**
- **Root-cause attribution:**
  1. The rotation adds no value over the factor zoo: OOS Sharpe
     0.579 < EW benchmark 0.606 (IR -0.353, p = 0.351) — the
     63-day cross-sectional factor ranking is noise on 2018-2024
     factor ETFs.
  2. The edge is momentum-family exposure: momentum family alone
     (0.819) beats the rotation; value-family momentum is negative
     OOS (-0.028). "Factor timing" is de facto a momentum-factor
     bet with extra turnover.
  3. The VIX regime gate is procyclical: ungated (0.758) beats
     gated (0.579) — exposure cuts removed participation in
     recoveries (replicates H3's finding).
  4. Worst-regime failure is structural: bear Sharpe -3.680; a
     long-only factor-momentum book cannot survive high-vol
     reversal regimes without a short/hedge leg.
  5. Monthly rebalancing with n_factors=2 yields 184 OOS trades
     (< 200): the turnover structure itself misses the trades gate.
- **Net Opportunity Score:** 2/10 (realized). Factor timing on free
  daily factor-ETF data does not clear the evidence gates; the
  measured edge is momentum-like and regime-fragile.
- **What would invalidate the rejection:** factor-timing signals
  beyond 63-252d momentum (macro/valuation-conditioned rotation),
  short/hedge legs for bear regimes, or intra-month rebalancing
  to clear the trades gate (at higher cost).

---

### 15. Volatility-Risk-Premium Harvesting (Term-Structure-Gated, Vol-Targeted Long SVXY) (executed 2026-10-13 — H17, **REJECTED**)

- **Net edge measured** (SVXY traded; ^VIX/^VIX3M signal only; Yahoo daily
  2011-10-04→2026-10-08, ~3,775 bars; corrected equity cost model): selected
  config (gate_thresh=0.00, vol_window=63, target_vol=0.25, max_pos=0.50,
  selected by Val Sharpe = 0.784) **OOS Sharpe 0.742**, max DD -16.55%,
  PF 1.147, 238 trades, WF stability 1.911, worst-regime Sharpe -4.130
  (bear), IR -0.240 vs BH-SVXY benchmark (p = 0.534, α = +5.4%/yr).
  7.3 s grid, 0.00 CPU-h.
- **Regime Sharpe**: bull 3.749, sideways -1.275, bear **-4.130**.
- **Ablations (OOS)**: BH SVXY Sharpe 0.466 / DD -62.2% (volmageddon tail);
  ungated vol-target 0.460 / DD -35.9%; gate-only-no-vol-target 0.721 /
  DD -33.0%; BH SPY 0.752 / DD -34.1%.
- **Gates**: 3/9 PASS (worst-regime, Sharpe, trades, WF-stability,
  perturbation pass = actually trades+stab+perturb; Sharpe/PF/DD/worst/p/IR
  all FAIL). **Status: REJECTED.**
- **Root-cause attribution (the volmageddon binding constraint):**
  1. **The worst-regime tail is un-gateable on daily data.** Bear-regime
     Sharpe -4.130 is driven by 2018-02-05 (-32% in SVXY in one day),
     2020-03-16 (-20.6%), 2020-03-12 (-16.9%) — the worst days arrive
     *inside contango* (VIX prints 37 only on the crash day itself);
     the daily term-structure gate (^VIX3M/^VIX) cannot pre-warn a same-day
     volatility spike. This is the binding constraint, not the carry.
  2. **Max-DD exceeds the 15% budget** at the vol-target that would push
     Sharpe ≥ 1.0: at the DD-compliant 5% target vol, Sharpe ≈ 0.46
     (< 1.0). The joint `(Sharpe ≥ 1.0) AND (DD ≤ 15%)` is infeasible
     on free daily data — confirmed by the gate frontier: higher target_vol
     raises Sharpe but pushes DD past 15%.
  3. **The edge is bull-regime-dependent (momentum-crash structure).**
     Bull Sharpe 3.749 vs sideways/bear net-negative: short-vol harvesting
     is de facto a low-vol beta lever, crashing in high-vol regimes exactly
     like the momentum strategies (H1-H3, H16). The VRP is "carry" only in
     calm markets; the tail is unhedgable with a long-only daily-gated book.
  4. **No statistical edge vs the buy-and-hold benchmark (p = 0.534,
     IR = -0.240):** the gated vol-targeting does not generate significant
     alpha over simply holding SVXY; the term-structure gate adds turnover
     without a statistically detectable Sharpe lift.
  5. **Perturbation passes (0.952 ratio):** the weak signal is stable under
     ±20% parameter moves, confirming this is a genuine (if unharvestable)
     property of the SVXY/VIX term structure, not a data-mining artifact.
- **Net Opportunity Score:** 3/10 (theory, VRP is a documented anomaly)
  → **2/10 (realized within the 15% DD gate on free daily data)**. The VRP
  exists; it is not harvestable within the project's joint Sharpe≥1 / DD≤15%
  gates without a short/hedge leg or higher-frequency entry (which would
  require paid data to clear the 730-day hourly cap for intraday execution).
- **What would invalidate the rejection:** (a) a vol-spike early-warning
  signal on sub-daily resolution (VIX futures micro-structure / realized
  variance of variance), (b) a short/hedge leg (e.g., long VIX calls /
  tail-risk overlay) sized per the regime, or (c) paid higher-frequency data
   to exit the contango tail intra-day.

---

## H19: Volume-Predictive Return Decomposition — REJECTED

**Summary**: Daily volume-decomposition signals (3 methods × 3 thresholds =
9 combos on SPY) do not generate a robust, statistically significant edge
above buy-and-hold within the project gates.

**Key results**:
- Selected: `simple_lagged_median` (Val Sharpe 0.542, Train 0.629, Test 0.092).
- OOS Sharpe 0.242 (gate ≥0.30 — FAIL).
- Max-DD -34.8% (gate ≥-20% — FAIL).
- Profit factor 1.066 (gate ≥1.10 — FAIL).
- Walk-forward stability -0.144 (gate ≥0.40 — FAIL).
- Worst-regime Sharpe -2.867 (bear; gate ≥0.00 — FAIL).
- Information ratio -0.880 (gate ≥0.0 — FAIL).
- Trades 940 (gate >200 — PASS). Benchmark p-value 0.0026 (gate ≤0.05 — PASS).
- Perturbation ratio 0.869 (gate ≥0.80 — PASS).
- Gates: 3/9 PASS → REJECT.

**Root cause**: The volume-decomposition signal overfits in-sample (Train
Sharpe 0.629) and decays severely out-of-sample (Test Sharpe 0.092). OOS
Sharpe (0.242) is below both buy-and-hold SPY (0.733) and random-volume
ablations (0.207). The signal adds turnover without compensating alpha.
Worst-regime Sharpe (-2.867 in bear markets) indicates the decomposition
fails precisely during market stress when protection matters. Negative
information ratio (-0.880) confirms the active share is uncompensated.

**Ablations**:
- BH SPY: Sharpe 0.733, DD -34.1%, PF 1.151.
- Random volume signal: Sharpe 0.207, DD -33.8%, PF 1.056.
- Constant 0.5 position: Sharpe 0.733, DD -18.2%, PF 1.151.

**Cross-validation**: Signal underperforms BH on both QQQ (0.548 vs 0.886)
and IWM (0.242 vs 0.434).

**Net Opportunity Score**: 2/10. Volume-return decomposition is a
well-documented theoretical anomaly (Kyle, 1985; Hasbrouck, 1991) but does
not translate to a daily, unweighted, transaction-cost-inclusive signal
that clears the project gates.

**What would invalidate the rejection**: (a) signed volume (buyer/seller
initiated flow) rather than total volume, (b) microstructure-aware
positioning (order-book depth / flow toxicity), (c) higher-frequency
calibration (intraday volume clustering), or (d) a volatility-regime
interaction that gates volume sensitivity (e.g., volume predicts returns
only in high-VIX regimes).

- **What would invalidate the rejection:** (a) signed volume (buyer/seller
  initiated) rather than total volume, (b) microstructure-aware
  positioning (order-book depth / flow toxicity), (c) higher-frequency
  calibration (intraday volume clustering), or (d) a volatility-regime
  interaction that gates volume sensitivity (e.g., volume predicts returns
  only in high-VIX regimes).
- H20 directly tests (a) above: it replaces total-volume surprise with
  *signed* (buyer/seller-initiated) volume / order-flow imbalance.

## H20: Volume-Sign (Buy/Sell-Initiated) Decomposition + Order-Flow Imbalance — REJECTED

**Summary**: Isolating net demand pressure via signed volume (tick rule /
Lee-Ready algorithm proxy on daily OHLCV) and trading a volatility-targeted
long/short position on the cumulative order-flow imbalance (2 rules × 3
target vols × 2 max positions × 3 lag windows = 36 combos on SPY) does not
generate a robust, statistically significant edge above buy-and-hold within
the project gates. This is the direct invalidation attempt for the H19
"signed volume would help" escape hatch — it does not.

**Key results**:
- Selected: `lee_ready / target_vol=0.05 / max_pos=1.0 / imbalance_lag=3`
  (Val Sharpe 0.170; Train -0.256, Test -0.398).
- OOS Sharpe **-0.156** (gate ≥1.0 — FAIL); below BH SPY (0.733) and below
  the randomized-direction control (-0.080).
- Max-DD -22.1% (gate ≤15% — FAIL).
- Profit factor 0.973 (gate ≥1.3 — FAIL).
- Walk-forward stability -0.480 (gate ≥0.7 — FAIL).
- Worst-regime Sharpe -0.627 (bull; gate ≥0.3 — FAIL).
- Information ratio -0.704 (gate ≥0 — FAIL).
- Trades 2,958 (gate ≥200 — **PASS**). Benchmark p-value 0.0159 (gate ≤0.05 —
  **PASS**). ±20% perturbation 0.000 (gate ≥0.5 — FAIL; selected optimum is
  non-positive so the stability reference is undefined).
- Gates: **2/9 PASS → REJECT**.

**Root cause**: The daily tick/Lee-Ready proxy cannot resolve true
buyer-/seller-initiated flow — the selected signal's OOS Sharpe is negative
and below both the market (BH SPY) and a randomized-direction ablation using
identical turnover. The sign assignment carries no directional information at
daily resolution; worst performance occurs in quiet bull markets where the
proxy is purest noise, confirming the signal is noise, not alpha. Train→Val
Sharpe decay (best Val 0.170 selected from 36 combos) is a selection artifact
that inverts OOS (Test -0.398). Vol-targeting across target_vol ∈ {0.05,
0.10, 0.15} is nearly flat (all negative), so it is not the binding
constraint.

**Ablations (OOS)**:
- BH SPY: Sharpe 0.733, DD -34.1%, PF 1.151.
- Constant 0.5 position: Sharpe 0.733, DD -18.2%, PF 1.151.
- Random signed volume (shuffled direction): Sharpe -0.080, DD -13.2%, PF 0.986.
- Total-volume-only (H19): Sharpe 0.242, DD -34.8%, PF 1.066.

**Cross-validation**: Signal underperforms BH on QQQ (0.124 vs 0.886) and IWM
(-0.287 vs 0.434).

**Net Opportunity Score**: 2/10. Signed-volume / order-flow imbalance is a
well-documented microstructural predictor (Kyle, 1985; Hasbrouck, 2001; Kane,
2002) but requires trade-level or bid/ask data to assign direction; the free
daily OHLCV proxy yields net flow that is statistically indistinguishable
from a random direction sequence.

**What would invalidate the rejection**: (a) intraday / tick-level volume
sign assignment (bid-ask or trade-classification data, e.g. BDAVOL-style
buy/sell volume from a broker or paid microstructure feed); (b) a
higher-frequency volatility estimator so vol-targeting actually scales down
ahead of regime stress; or (c) pooling signed flow across a cross-section of
high-volume names with a market-neutral (dollar-neutral) construction so
that sign noise is averaged out while systematic flow-to-return coupling
survives.

## H21: Multi-Contract Intraday Futures TSMOM Generalization — REJECTED

**Summary**: Generalizing the H10/H11 certified intraday futures TSMOM edge
(vol-scaled, path-dependent exits) across a 5-contract basket (ES=F, NQ=F, CL=F,
GC=F, ZB=F) with equal-weight aggregation. 16-combo grid (target_vol_mult in
{0.25, 0.50} x max_pos in {0.5, 1.0} x scale_rule in {equal, inverse_vol} x
n_assets in {3, 5}), Val-selected, Test-protected on the ~730-hour yfinance
`=F` window (2024-10-12 -> 2026-10-11). The basket is a **real** signal
(random-sign ablation -0.470; benchmark p = 1.9e-10) and is the **most robust
surviving candidate** — it clears DD, worst-regime, IR, WF-stability,
significance and trade-count gates — but fails Sharpe (0.839 < 1.0) and PF
(1.206 < 1.3).

**Key results**:
- Selected: `tv_mult=0.5 / max_pos=0.5 / equal / n_assets=5` (Val Sharpe 0.899,
  argmax of 16 combos).
- OOS (Val+Test, ~730h): Sharpe **0.839** (Val 0.899, Test 0.765) — < 1.0 — FAIL;
  max-DD -8.60% (<=15% — PASS); PF **1.206** (< 1.3 — FAIL); WF stability 0.988
  (>=0.7 — PASS); worst-regime 0.778/sideways (>=0.3 — PASS); benchmark p=1.9e-10
  (<=0.05 — PASS); IR 0.946 (>=0 — PASS); trades 5,920 (>=200 — PASS).
- Gates: **6/8 PASS -> REJECT** (perturbation pre-registered but not evaluated;
  see Deviation notes).
- Ablations (OOS): ES-only 0.608 (diversification adds +0.231); random-sign -0.470
  (signal is real); daily-TSMOM 0.514 (edge is intraday-only, H9).
- Grid degeneracy: `scale_rule` and `max_pos` have **zero** effect on Val
  Sharpe -> 16 combos collapse to 4 effective points (target_vol x n_assets).
  H10's `TARGET_VOL=0.15` (15% ann) was outside H21's grid (max 7.5%).

**Root cause**: (1) Sharpe shortfall from **under-vol-targeting** — H21 swept only
3.75%/7.5% annualized vol vs H10's certified 15% that yields Sharpe 1.276; the edge
is real and intraday but under-capitalized at H21's vol levels. (2) PF < 1.3
across **all** 16 grid combos (max Val PF 1.246) — PF-fragility is a family property
of the intraday-futures-carry edge on the 730h window (H13/H14 for H10; now
confirmed on the diversified basket). (3) The 730-hour `=F` cap is the data wall.

**Net Opportunity Score**: 4/10. The diversified intraday futures TSMOM is the
strongest surviving free-data candidate (real signal, robust DD/regime/IR) but
fails the two value-defining gates (Sharpe, PF) and cannot be repaired by
selection or diversification alone on the free window. The binding constraints are
**data horizon** (730h cap) and **vol-targeting range not swept to H10's level**.

**What would invalidate the rejection**: (a) sweeping `target_vol_mult` to H10's
range (>=1.0 -> 15% ann) and clearing Sharpe >= 1.0 at acceptable DD — i.e. the
shortfall is vol-targeting, not a broken edge (this is H22); or (b) a longer free
hourly futures window narrowing the PF CI so PF >= 1.3 is met by >50% of combos.

**Compute**: 0.005 CPU-h (17.7s). Seed 42. Deterministic.

### 16. Cumulative state of evidence gates (updated with H21)
- The signed-volume escape hatch for H19 is closed: H20 (signed volume) fails
  with an even worse Sharpe (-0.156) and fails the perturbation gate.
- Structural walls unchanged: (a) the yfinance hourly `=F` 730-day cap
  blocks intraday extension beyond H10/H11 without paid data; (b) the
  ≤15–20% DD joint gate has been met by no long-only free-data family except
  the futures-carry edge of H10/H11.
- New finding: direction-classification granularity, not vol-targeting or
  costs, is the binding constraint for *all* volume-based hypotheses (H19
  total volume and H20 signed volume both fail; signing the flow does not
  help on free daily data).
- H21 generalization: cross-sectional diversification of the H10 edge lifts
  OOS Sharpe (0.608 -> 0.839) and clears DD/regime/IR/stability/significance/
  trades, but Sharpe (0.839 < 1.0) and PF (1.206 < 1.3) stay below gates and
  PF < 1.3 across all 16 grid combos confirms PF-fragility is a family property.
  Vol targeting was under-swept (max 7.5% ann vs H10's 15%). The
  intraday-futures carry edge is the strongest surviving free-data candidate
  but does not clear the value-defining gates on the 730h window. -> only H10/H11 PASS.

---

## H23: Crypto Perpetual Futures Intraday TSMOM — REJECTED (Data Limitation)

**Summary**: Testing whether the H10/H22 certified intraday futures TSMOM edge
(vol-scaled signal + CT-style path-dependent exits) generalizes to crypto
perpetual futures on Coinbase. 6912-combo grid (signal smoothing / vol-window /
min-trade-interval / exit parameters) evaluated on the available hourly data.

**Critical data limitation**: Coinbase/CCXT hourly OHLCV for BTC/USD, ETH/USD,
ADA/USD, XRP/USD, DOGE/USD returns only **~300 hours (12.5 days)** of recent
data (2024-10-12 → 2024-10-24), vs. the pre-registered ~17,500-hour window
(2024-10-12 → 2026-10-11). This is a hard free-data limit for the Coinbase
public API via CCXT. The sample is grossly insufficient for the 6912-combo grid
search or meaningful OOS evaluation (Val+Test = only ~135 bars).

**Key results**:
- Selected config: `vol_window_long=1008, smooth_span=none, regime_scaling=False,
  min_trade_interval=0, trailing_mult=1.5, max_hold_bars=60, vol_limit_mult=1.5,
  vol_floor_fraction=0.25` (Val Sharpe 0.0 — no signal on this window).
- OOS (Val+Test, 135 bars): Sharpe **0.0** (Val 0.0, Test 0.0) — FAIL;
  max-DD 0.0% (PASS vacuous); PF ∞ (PASS vacuous: 0 trades); WF stability 0.0
  (FAIL); worst-regime 0.0 (PASS); benchmark p=0.383 (FAIL); IR 0.800 (PASS);
  trades 0 (FAIL); perturbation 0.0 (FAIL).
- Gates: **4/9 PASS → REJECT** (all meaningful gates fail due to insufficient data).
- Ablations: H9 baseline produces 74 trades with catastrophic DD (-97%) and
  Sharpe -6.96; longer vol window (1008) produces 0 trades (signal flat).

**Root cause**: The pre-registered hypothesis is **untestable on free data**.
Coinbase hourly data via CCXT is capped at ~12 days, while the vol-scaled TSMOM
signal requires ~252+ bars (10+ days) just to warm up the volatility estimator,
leaving virtually no data for signal generation or OOS evaluation. This is a
data-availability wall, not a falsified mechanism.

**Net Opportunity Score**: N/A (data-limited). The H10/H22 intraday futures
TSMOM edge remains the sole certified edge on free data; its generalization to
crypto perpetuals remains an open question pending paid hourly data.

**What would invalidate the rejection**: A free or paid crypto data source
providing ≥ 1 year of hourly OHLCV for major perpetuals (BTC/USD, ETH/USD, etc.),
enabling the pre-registered window and a meaningful test of the H10/H22
mechanism on crypto markets.

**Compute**: 0.04 CPU-h (2.3 min). Seed 42. Deterministic.

---

### 17. Cumulative state of evidence gates (updated with H23)
- The intraday futures TSMOM edge (H10/H11/H22) remains the **sole PASS family**
  on free data (Sharpe 1.372, PF 1.334, DD -11.9% at 15% ann vol on 5-contract
  basket).
- H23 crypto generalization: **untestable on free data** — Coinbase hourly
  capped at ~12 days, insufficient for vol-scaled TSMOM warmup + OOS evaluation.
- Structural walls now include: (a) yfinance hourly `=F` 730-day cap for
  traditional futures; (b) Coinbase/CCXT hourly ~12-day cap for crypto
  perpetuals; (c) the joint Sharpe ≥ 1.0 ∧ DD ≤ 15% gate met by no free-data
  family except H10/H11/H22's futures-carry edge.
- All equity-based (H1-H9, H16, H18), volume-based (H19-H20), VRP (H17), and
  roll-adjusted (H8) families on free daily data: **REJECTED**.
- Multi-contract futures basket (H21): **REJECTED** (under-vol-targeted);
  corrected in H22: **PASS** at H10's vol level (15% ann).
- The path forward requires **paid hourly data** (traditional futures beyond
  730 days, crypto perpetuals beyond 12 days) or acceptance that the free-data
  edge is confined to the ~2-year intraday futures window already certified.
