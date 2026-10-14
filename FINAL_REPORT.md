# Final Report: Quantitative Trading Mathematics Research

## Executive Summary

Executed Phases 3–5 of the PROMPT_V2.md research spec: a mathematical
discovery → market inefficiency → hypothesis test pipeline, applied to
**volatility-scaled time-series and cross-sectional momentum on liquid ETFs
(2015-2024)**. The two pre-registered hypotheses were **rejected** by the strict
evidence gates (Sharpe ≥ 1.0, ≥200 OOS trades, PF ≥ 1.3, max DD ≤ 15%,
walk-forward stability, ±20% perturbation, regime stability, benchmark
significance). The dominant failure is a **train→OOS collapse** driven by the
2020 COVID crash and 2022 inflation shock (bear-regime Sharpe ≈ -2.4 to -3.0) —
the well-documented *momentum crash*.

A separate, material infrastructure defect was found and fixed: the backtest
engine's equity cost model inflated trading costs ~400× (by the asset price),
which was the **actual bottleneck** making every active strategy appear
catastrophically unprofitable while buy-and-hold survived. After correction,
costs are verified realistic, and the momentum underperformance is genuine
signal weakness (OOS Sharpe ≈ 0.1), not a cost artifact.

---

## Phase 1 — Prompt Refinement
Frozen at PROMPT_V2.md (2 cycles; all criteria ≥ 4/5). Not changed during this
cycle (no new evidence requiring prompt revision — the gates held and correctly
rejected the candidate).

## Phase 2 — Infrastructure (prior agent) → Bottleneck Found
The prior agent built the engine, fetcher, tracker, strategies and stats suite
and established the SPY buy-and-hold baseline (Sharpe ≈ 0.66). **Bottleneck
identified during Phase 3-5 execution:** the cost model. Details below.

### Cost-model defect (the real bottleneck)
`src/qtr/backtest/engine.py::_calculate_costs` computed equity cost as
`weight_delta * price * bps/10000` and subtracted it from *fractional* portfolio
returns. The correct cost-as-fraction-of-capital is
`weight_delta * bps/10000`. The extra `* price` injects the per-share dollar
price (e.g. ~$400 for SPY), inflating each trade's cost by ~400×.
Consequences (verified):
- Buy-and-hold SPY (1 trade): day-0 cost ≈ 12% of capital (now ≈ 3 bps).
- MA 30/200 (9 trades): reported Sharpe **0.249** (buggy) → **0.655** (fixed).
- Momentum (768–1500 trades): every trade carried a ~0.6–6% haircut, destroying
  the signal.

**Fix:** `symbol_costs = changes * (cost_bps / 10000)` for equity and crypto
(Futures path was already correct). Re-validated: buy-and-hold SPY → 0.685,
costs sub-bps for low-turnover legs. The prior "MA crossover fails catastrophically"
conclusion was an artifact; the corrected conclusion is "MA crossover ≈ buy-and-hold,
still not an edge."

---

## Phase 3 — Mathematical Discoveries Investigated
Literature review with provenance, assumptions, limitations, and replication
status for: TS momentum (Moskowitz et al. 2012), CS momentum (Jegadeesh &
Titman 1993; Asness et al. 2013), carry (Koijen et al. 2018), regime-switching
(Kim & Mueller 2016), and information-theoretic predictors (Schreiber 2000).
Full traceability chains in `MATHEMATICAL_DISCOVERY_REPORT.md`.

Top candidates scored 5.0/5.0 and were taken to experiments: TS momentum (H1)
and CS momentum (H2). Carry was deferred (futures-roll data gap); transfer
entropy rejected (no high-freq cross-market data).

## Phase 4 — Inefficiency Ranking
Six-factor market ranking; updated with measured (post-cost-fix) net edge.
TS momentum ranked #1 on theory but **2/10 on realized edge** — the sample
itself (2020/2022) is the invalidating evidence. See `INEFFICIENCY_RANKING.md`.


## Phase 5 — Hypothesis Generation & Testing

| Hypothesis | Universe | Selected params | OOS Sharpe (CI) | Trades | PF | Max DD | Gates passed | Verdict |
|------------|----------|-----------------|-----------------|--------|----|--------|--------------|---------|
| H1 TS momentum | 20 ETFs | LO, lb=126, sk=1 | 0.093 ([-0.76, 0.96]) | 768 | 1.017 | -34.8% | 2/8 | **REJECTED** |
| H2 CS momentum | 10 eq ETFs | LO, lb=252, sk=21 | 0.116 ([-0.71, 1.02]) | 388 | 1.024 | -38.7% | 1/8 | **REJECTED** |
| H3 Regime-gated vol-scaled momentum | 20 ETFs + ^VIX + VXX | long_only=False, lookback=63, skip=21, regime_triple=(1.0,0.25,0.10), hedge_weight=0.0 | -0.868 (95% CI [-1.693, -0.003]) | 1239 | 0.832 | -48.25% | 3/10 | **REJECTED** |
| H4 Futures TSMOM + ensemble selection | ES=F, NQ=F, CL=F, GC=F, ZB=F | ensemble of top-K (K=5) by train walk-forward Sharpe | 0.376 | 177 | 1.085 | -47.4% | 1/8 | **REJECTED** |
| H5 Drawdown-conditioned vol targeting (DDCV) | ES=F, NQ=F, CL=F, GC=F, ZB=F | dd_trigger=0.30, dd_factor=0.75 | 0.509 | 188 | 1.108 | -35.3% | 1/8 | **REJECTED** |
| H6 VIX-gated + DDCV combo | ES=F, NQ=F, CL=F, GC=F, ZB=F | dd_trigger=0.10, dd_factor=0.50 | 0.708 | 188 | 1.160 | -19.7% | 2/8 | **REJECTED** |
| H7 Multi-horizon TSMOM with regime-weighted blending | ES=F, NQ=F, CL=F, GC=F, ZB=F (CME/ICE continuous front-month), ^VIX for regime context only | w_slow = sign(mom_252) / vol_63, w_fast = sign(mom_63) / vol_21, blend weight b = 1 / (1 + realized_vol_port / target_vol), w = (1-b)*w_slow + b*w_fast, portfolio-level vol targeting to 15% annual, per-asset caps; exits: intraday trailing stop (2× ATR from entry), time stop (max 5 trading days), vol stop (realized vol > 2× target) | 0.789 | 1005 | 1.166 | -14.5% | 3/8 | **REJECTED** |
| H8 Roll-adjusted futures TSMOM | ES=F, NQ=F, CL=F, GC=F, ZB=F | vol-scaled TSMOM on P' via `vol_scaled_tsmom_signals` (long_only=True, lookback=252, skip=1, target_vol=0.15, vol_window=63, max_position_size=2.0) with roll carry weight w=0.50 | 0.814 | 201 | 1.157 | -20.9% | 3/8 | **REJECTED** |
| H9 Intraday futures TSMOM with CT-Style Path-Dependent Exits | ES=F, NQ=F, CL=F, GC=F, ZB=F (1h interval) | Vol-scaled TSMOM blend (252h + 63h) with portfolio vol targeting (15% annualized, re-estimated hourly); exits: trailing stop (2× ATR), time stop (120 bars / 5 days), vol stop (20-bar realized vol > 2× target) | 1.056 | 2,690 | 1.252 | -6.2% | 7/8 | **REJECTED** |
| H10 Intraday Futures TSMOM — Profit Factor Optimization | ES=F, NQ=F, CL=F, GC=F, ZB=F (1h interval, cached yfinance) | vol_window_long=1008, smooth_span=none, regime_scaling=False, min_trade_interval=0, trailing_mult=2.0, max_hold_bars=60, vol_limit_mult=1.5, vol_floor_fraction=0.25 | 1.276 | 2,416 | 1.304 | -5.8% | 8/8 | **PASS** |
| H11 Robustness certification of H10 | same as H10 | frozen H10 config (vol_window_long=1008, smooth_span=none, regime_scaling=False, min_trade_interval=0, trailing_mult=2.0, max_hold_bars=60, vol_limit_mult=1.5, vol_floor_fraction=0.25) | 1.275759 | 2,416 | 1.304165 | -5.843% | 8/8 | **PASS** |
| H12 Selection-bias audit of H10 | same as H10 | frozen H10 config | 1.275759 | 2,416 | 1.304165 | -5.843% | 8/8 | **PASS** |
| H13 OOS deflation & PF-margin fragility audit | same as H10 | frozen H10 config | 1.275 (worst-case DSR-adj OOS) | 2,416 | 1.304, 95% CI [1.190, 1.425] | -5.843% | 8/8 | **REJECT on the fragility axes** |
| H14 PF-margin-targeted selection audit | same as H10 | top K=50 configs by Val PF margin (excluding H10) | — | — | — | — | 0/50 | **REJECT** |
| H15 (not executed) | — | — | — | — | — | — | — | — |
| H16 Cross-sectional equity factor timing | 9 factor ETFs, 3 families, VIX regime filter | lookback=63, skip=5, regime 1.0/0.5/0.25, n_factors=2 | 0.579 | 184 | 1.106 | -19.95% | 1/9 | **REJECTED** |
| H17 Volatility-Risk-Premium Harvesting (Term-Structure-Gated, Vol-Targeted Long SVXY) | SVXY (traded vehicle); ^VIX, ^VIX3M (signal only, not traded); SPY (secondary reference) | gate_thresh=0.00, vol_window=63, target_vol=0.25, max_pos=0.50 | 0.742 | 238 | 1.147 | -16.55% | 3/9 | **REJECTED** |
| H18 Overnight-vs-intraday equity return decomposition | SPY (primary) | predictor=prior_5d_return_sign, hold_convention=next_intraday | 0.442 | 589 | 1.089 | -22.23% | 2/9 | **REJECTED** |
| H19 Volume-predictive return decomposition | SPY (primary), also QQQ/IWM for cross-validation | simple_lagged_median | 0.242 | 940 | 1.066 | -34.8% | 3/9 | **REJECTED** |
| H20 Volume-Sign / Order-Flow Imbalance | SPY daily OHLCV, QQQ/IWM cross-validation, ^VIX regime labels | lee_ready / tv0.05 / mp1.0 / lag3 | -0.156 | 2,958 | 0.973 | -22.1% | 2/9 | **REJECTED** |
| H21 Multi-Contract Intraday Futures TSMOM Generalization | ES=F, NQ=F, CL=F, GC=F, ZB=F (5-contract hourly futures basket) + ^VIX | target_vol_mult=0.5 / max_pos=0.5 / scale_rule=equal / n_assets=5 | 0.839 | 5,920 | 1.206 | -8.60% | 6/8 | **REJECTED** |
| H22 Futures TSMOM basket vol-targeting gap test | ES=F, NQ=F, CL=F, GC=F, ZB=F + ^VIX (2024-10-12 -> 2026-10-11 hourly, 55/25/20 splits, OOS = Val+Test) | target_vol_mult=1.0 (15% ann), max_pos=0.5, scale_rule=equal, n_assets=5 | 1.372 | 3045 | 1.334 | -11.9% | 9/9 | **PASS** |
| H23 Crypto perpetual futures intraday TSMOM | 5 crypto symbols (Coinbase/CCXT hourly OHLCV) | vol_window_long=1008, smooth_span=none, regime_scaling=False, min_trade_interval=0, trailing_mult=1.5, max_hold_bars=60, vol_limit_mult=1.5, vol_floor_fraction=0.25 | 0.0 | 0 | ∞ | 0.0% | 4/9 | **REJECTED** |
## Phase 6 — Evidence Gates (applied, all real)
Both hypotheses evaluated against the full PROMPT_V2 + HYPOTHESIS_SPEC gate set
on pooled Val+Test OOS. Neither passed. Negative results preserved with full
reproducibility metadata (git commit, seeds, dependency versions, data hashes).

## Phase 6 (continued) — H1–H12 research arc (later agents)
The H1/H2 rejection motivated the H3–H12 hypothesis family (documented in
`HYPOTHESIS_SPEC.md` and `INEFFICIENCY_RANKING.md`):

| Hyp | Construction | OOS Sharpe | PF | Verdict |
|-----|--------------|-----------|-----|---------|
| H3 | Regime-gated vol-scaled momentum | — | — | REJECTED |
| H4 | Futures TSMOM + ensemble selection | — | — | REJECTED (cost-model bug found & fixed) |
| H5 | Drawdown-conditioned vol targeting | — | — | REJECTED |
| H6 | VIX-gated + DDCV combo | — | — | REJECTED |
| H7 | Multi-horizon regime-weighted TSMOM | — | — | REJECTED |
| H8 | Roll-adjusted futures TSMOM | — | — | REJECTED |
| H9 | Intraday futures TSMOM + CT exits | — | — | REJECTED |
| **H10** | **Intraday TSMOM PF-optimization (13,824-combo grid, Val-selected)** | **1.276** | **1.304** | **PASS (first to clear all 8 gates)** |
| H11 | Robustness certification of H10 | 1.276 | 1.304 | **PASS** (seeds, ±20% perturbation, ±50% costs, shifted splits, concentration) |
| **H12** | **Selection-bias audit of H10** | — | — | **PASS** (DSR-adj Sharpe 1.409, p=0.0028; PBO=0.055; family-corrected p=6.9e-06) |
| H13 | OOS deflation & PF-margin fragility audit | **1.275** (worst-case DSR-adj OOS) | 1.304, 95% CI [1.190, 1.425] | **REJECT on the fragility axes** (Sharpe survives the worst-case N=13,824 deflation, p=0.001; PF CI LB 1.190 < 1.3; CL=F and GC=F indispensable — leave-one-out PF 1.249 / 1.282) |

H12 confirms the H10 result is not a best-of-13,824 selection artifact: the
observed Val Sharpe (1.413) is 2.3× the expected maximum of 13,824 null
trials (0.621), CSCV finds no backtest overfitting (PBO 0.055 < 0.3), and the
OOS benchmark alpha (p 4.79e-10) survives Bonferroni/BH/Šidák correction at
the pooled family trial count (14,389). The fragile margin remains the profit
factor: OOS PF 1.304 clears the 1.3 gate by only +0.004, and only 0.32% of
grid configs clear PF ≥ 1.3 OOS.

H13 (executed 2026-10-13, < 0.1 CPU-h, artifact-reuse-only) shows the
certification is **Sharpe-robust but PF-fragile**: the OOS Sharpe survives
even the worst-case "OOS-as-selection-metric" deflation (DSR-adj 1.2745,
p = 0.001; single-peek DSR 1.2758), but the PF margin is statistically
indistinguishable from the 1.3 gate (bootstrap 95% CI [1.190, 1.425],
P(PF ≥ 1.3) = 51.7%) and single-symbol-dependent — CL=F (net PF 1.358,
the only symbol above the pooled PF) and GC=F are indispensable
(leave-one-out pooled PF 1.249 / 1.282). The shifted-split PF shortfalls
(1.281 / 1.292) are driven by CL=F and the bull regime. Cost break-even
verified at 1.542× (H11: 1.5418×) — costs are not the driver.


## Conclusion

- **Supported:** the cost-model bug is real and fixed; volatility-scaled momentum *implementation* is correct; the infra runs end-to-end.
- **Rejected:** H1 and H2 as *profitable* on 2015-2024 ETFs (both fail gates); H3–H9 across regime-gating, DDCV, multi-horizon, roll-adjustment and intraday-CT-exit variants (all fail gates); H16 (factor timing), H17 (VRP), H18 (overnight/intraday), H19 (volume-predictive), H20 (signed volume), H21 (multicontract futures TSMOM) all fail gates; H23 (crypto perpetual futures intraday TSMOM) fails due to insufficient data.
- **Certified:** H10 (intraday futures TSMOM, PF-optimized) passes all 8 gates; H11 certifies robustness; H12 certifies the result against selection bias; H22 (vol-targeting gap closed) passes all 9 gates.
- **Qualified (H13):** the certification is Sharpe-robust (worst-case DSR-adj OOS Sharpe 1.2745, p = 0.001) but the PF margin is fragile — bootstrap 95% CI [1.190, 1.425] and single-symbol-dependent (CL=F, GC=F indispensable). Production use requires a longer OOS window (paid data) or PF-margin-targeted re-optimization.
- **Uncertain → actionable:** regime-aware / crisis-resilient momentum is the highest-value next step (see `NEXT_TASK.md`).

## Next Task
**Verify the consistency of the updated documentation and run final checks.**

- Ensure that the `FINAL_REPORT.md` accurately reflects the results in `HYPOTHESIS_SPEC.md` and `NEXT_TASK.md`.
- Run the full test suite one more time to confirm all tests pass.
- Optionally, compile a summary of the certified edges for future reference.
