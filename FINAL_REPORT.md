# Final Report: Quantitative Trading Mathematics Research

## Executive Summary

The quantitative trading research infrastructure has been successfully built and validated. A critical cost-model defect in the backtesting engine was identified and corrected, which had previously inflated trading costs by approximately 400×. After correction, the infrastructure produces realistic cost estimates.

Systematic hypothesis testing across 23 hypotheses (H1-H23) revealed that only the intraday futures time-series momentum (TSMOM) strategy consistently clears the stringent evidence gates (Sharpe ≥ 1.0, ≥200 OOS trades, profit factor ≥ 1.3, max drawdown ≤ 15%, walk-forward stability, ±20% parameter perturbation, regime stability, and benchmark significance). Specifically:

- **H10**: Intraday futures TSMOM with profit-factor optimization (certified)
- **H11**: Robustness certification of H10 (certified)
- **H12**: Selection-bias audit of H10 (certified)
- **H22**: Vol-targeting gap closed on the multi-contract intraday futures TSMOM basket (certified)
- **H25**: PF-margin repair by vol-targeting expansion on a pruned 4-contract basket (certified; qualified on the PF bootstrap margin)

**Look-ahead finding (H27, 2026-10-19) — the certified family is INVALIDATED.** The
**level** of the certified intraday P&L is arithmetically clean: the dollar P&L implied by the
committed prices, positions and contract specs reproduces the logged returns to **≤4.9e-16**
and the cost drag to **≤1.1e-19** (H27 §L1/L3). There is no unit error. But the *positions
that produced it were not knowable when they were traded*. The daily-target collapse
(`_daily_target_from_hourly` → `resample("1D").last()`, expanded back onto the hourly grid)
positions **every session with that session's own closing signal** — a one-day look-ahead in
H9/H10/H21/H22/H25 alike. Re-running each family's *selected* config with a causal one-day
lag (the minimal possible intervention: the daily series is shifted by one day and nothing
else changes) collapses the certified family:

| Family | Published OOS Sharpe | Causal (1-day lag) | Relative drop | Published full-sample equity | Causal |
|---|---|---|---|---|---|
| H9 (REJECT) | 1.0565 | 0.1860 | 82.4% | 8.02× | 1.26× |
| H10 (PASS) | 1.2758 | 0.2923 | 77.1% | 6.92× | 1.19× |
| H21 (REJECT) | 0.8394 | 0.1317 | 84.3% | 14.96× | 1.27× |
| H22 (PASS) | 1.3725 | 0.3605 | 73.7% | 79.80× | 1.89× |
| H25 (PASS) | 1.3236 | 0.3231 | 75.6% | 100.73× | 2.03× |

The look-ahead is what the edge was made of: **94.7%–97.8% of the published gross P&L is
*intraday* P&L** — the part of the session that the strategy could only have earned by
knowing the session's close in advance (the mean `sign(w_open) × r_intraday` tilt is 5.9×–6.2×
larger than under the causal build). For calibration, the equal-weight buy-and-hold of the
same five futures grows **1.36×** over the same window, while the published H25 grows
**100.7×** under a 5× gross leverage cap. H27 changed no gate, threshold, verdict or
certified number (the published PASS verdicts stand as published), but the certified family
must be treated as **not established** pending an explicitly re-registered re-certification
under a causal daily collapse (H28). See §H27 detail and `HYPOTHESIS_SPEC.md` §H27.

**Causal re-certification (H28, 2026-10-19) — the family is `CAUSAL_REJECTED`.** H28 re-ran
the **full published grids** (H10 13,824 combos; H21 16; H22 8; H25 8) with the daily collapse
lagged by one calendar day and **nothing else changed** — same gates, same 55/25/20 splits, same
Val-only selection, same Test protection, same cost model. Every family's **negative control**
(the published same-day expansion through the identical harness) reproduced the published
artifact **bit-exactly** (max abs diff **0.0** on all artifacts, including every one of the
13,824 H10 grid rows), so the comparison is sound. Under the causal build **every family fails
the unchanged gates**:

| Family | Published | Causal | OOS Sharpe | OOS PF | Max DD | Gates |
|---|---|---|---|---|---|---|
| H10 | PASS | **CAUSAL_REJECTED** | 0.3909 | 1.087 | −10.1% | 3/8 |
| H21 | REJECT | **CAUSAL_REJECTED** | 0.1317 | 1.030 | −26.1% | 3/8 |
| H22 | PASS | **CAUSAL_REJECTED** | 0.3605 | 1.077 | −22.8% | 4/9 |
| H25 | PASS | **CAUSAL_REJECTED** | 0.3231 | 1.069 | −26.2% | 4/9 |

The gates that fail are the same four everywhere: OOS Sharpe (≥ 1.0), PF (≥ 1.3), worst-regime
Sharpe (≥ 0.3) and the benchmark p-value (< 0.05); H10 also fails the information ratio. The
causal re-selection buys the family **at most +0.10 Sharpe** (H10 re-selects
`smooth_span=4, regime_scaling=True`, 0.292 → 0.391) and changes no gate outcome, so the verdict
is not an artefact of holding the configuration fixed. **The certified family does not survive
its own re-certification.** The published PASS verdicts stand as published (H28 changed no gate,
threshold, verdict or certified number) but they are now demonstrated to be **not evidence of a
tradable edge**. See §H28 detail and `HYPOTHESIS_SPEC.md` §H28.

**Look-ahead sweep of the remaining families (H29, 2026-10-19) — the defect's reach is now
mapped, and the daily families are certified clean.** H29 audited **every** remaining family
for the same mechanical defect, deciding each one from the committed artifacts with a detector
that fires on the already-audited intraday family and reports a deliberately *causal*
construction as clean. The discriminator is the **bin label**, probed at run time on the
installed pandas: `resample("1D")` labels each day at the bin **start** with that day's
**close** (a look-ahead: minimum hold lag **−22** bars, 94.7%–96.0% of the bars positioned
with the close of the day they belong to), while `resample("ME")` labels each month at the bin
**end** with the month's close (hold lag **+1** bar, **0** look-ahead bars). Results: **H1, H2,
H3, H4, H5, H6 and H8 are `CAUSAL`** — each verdict rests on a **bit-exact** rebuild of the
committed artifact from the committed prices (max abs diff 0.0) and on 0 unexpected change
points; **H11, H12 and H13 are `LOOKAHEAD`** because they inherit H10's construction (H11's
positions are bit-identical to H10's), so **H11's and H12's PASS verdicts rest on the same
look-ahead positions as H10's** and are not independent evidence; **H23 is `LOOKAHEAD`** (it
*does* use the daily collapse — the inherited brief said otherwise — but it is REJECTED and the
causal fix only moves its OOS Sharpe from −7.19 to −5.89, so the REJECT stands a fortiori and
no re-certification is warranted); **H7 has no committed artifact** and is reported
`INCONCLUSIVE` — a coverage gap, not a pass. **No published artifact, runner, gate, threshold,
verdict or certified number was changed and no grid was re-run.** Two inherited premises were
corrected: **no daily family passes** (H1 0.093 … H8 0.814, all REJECTED), so **the repo now
contains no PASS family that survives a causal construction**; and H23 is not free of the daily
collapse. See §H29 detail and `HYPOTHESIS_SPEC.md` §H29.

**Metric-scale correction (H26, 2026-10-19).** Every published "OOS Sharpe" is a
**√252-per-bar** metric (`sharpe_ratio` with its default `periods_per_year=252`). That is the
correct calendar annualization for the *daily* families, but for the **intraday (1h)** families
the published number is **not** an annualized Sharpe: it understates the annualized value by
**2.55×** (the repo's own `√(252·6.5)` vol-target convention) to **4.76×** (the empirical
calendar convention; 5.92× for the 24/7 crypto family H23). The certified family's annualized
Sharpe is therefore ≈3.25 (H10), ≈3.50
(H22), ≈3.37 (H25) — not 1.28/1.37/1.32. This changes **no verdict and no gate** (the
mis-scaling is conservative, and the profit-factor gate is scale-invariant), but it does mean the
results table's single "OOS Sharpe" column previously mixed two scales, and that the "Sharpe
CI-fragile" caveat was a metric-scale artifact rather than a property of the edge. See §H26
detail and `HYPOTHESIS_SPEC.md` §H26.

All other hypotheses, including various equity-based momentum, mean-reversion, regime-gated, volatility-targeted, volume-based, and crypto perpetual futures strategies, failed to meet the evidence gates, primarily due to insufficient risk-adjusted returns, excessive drawdown, or profit-factor fragility.

The structural barriers to clearing the gates on free data are:
1. The 730-hour limit on hourly futures data from yfinance (paid data required for longer horizon)
2. The joint Sharpe ≥ 1.0 and drawdown ≤ 15% gate, which no long-only free-data equity family has met

The certified edge (intraday futures TSMOM) is a **backtested** result that clears the
pre-registered gates on the available free window and is *qualified* by a CI-fragile profit-factor
margin. It is **not** established as a genuine exploitable market inefficiency: the OOS window is
~730 days, the PF margin is CI-fragile, and the scale-corrected annualized Sharpe (≈3.25–3.50
under the repo's own convention) is far above the ≈0.5–1.5 range of published real-world
futures time-series-momentum results. **H27 has now resolved that open question: the level is
not a unit error, but the edge is a one-day look-ahead.** The published PASS verdicts are
inflated by 74–77% (OOS Sharpe) and are not evidence of a tradable edge; the family's causal
counterfactual OOS Sharpe is 0.29–0.36, far below the 1.0 gate. The family must be
re-certified under a causal daily collapse before any of it is relied upon.

## Phase 1 — Prompt Refinement

Cycles Completed: 2 (of 3 max)
Final Version: PROMPT_V2.md (frozen as execution specification)

| Criterion | Score |
|-----------|-------|
| Objective clarity & alignment | 5 |
| Mathematical & scientific validity | 4 |
| Falsifiability & statistical rigor | 4 |
| Execution efficiency & feasibility | 4 |
| Reproducibility, safety, verification | 5 |

All criteria ≥ 4/5. Prompt frozen.

## Phase 2 — Infrastructure (prior agent) → Bottleneck Found

The prior agent built the engine, fetcher, tracker, strategies and stats suite and established the SPY buy-and-hold baseline (Sharpe ≈ 0.66). **Bottleneck identified during Phase 3-5 execution:** the cost model. Details below.

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
| H15 Loss-offset decomposition probe | ES=F, NQ=F, CL=F, GC=F, ZB=F (H10 artifact) | bar-level per-symbol OOS contribution + leave-one-out PF | — | — | 1.338 (pooled OOS) | — | n/a | **PROBE** (pre-H13; CL=F indispensable: LOO PF 1.273 < 1.3) |
| H16 Cross-sectional equity factor timing | 9 factor ETFs, 3 families, VIX regime filter | lookback=63, skip=5, regime 1.0/0.5/0.25, n_factors=2 | 0.579 | 184 | 1.106 | -19.95% | 1/9 | **REJECTED** |
| H17 Volatility-Risk-Premium Harvesting (Term-Structure-Gated, Vol-Targeted Long SVXY) | SVXY (traded vehicle); ^VIX, ^VIX3M (signal only, not traded); SPY (secondary reference) | gate_thresh=0.00, vol_window=63, target_vol=0.25, max_pos=0.50 | 0.742 | 238 | 1.147 | -16.55% | 3/9 | **REJECTED** |
| H18 Overnight-vs-intraday equity return decomposition | SPY (primary) | predictor=prior_5d_return_sign, hold_convention=next_intraday | 0.442 | 589 | 1.089 | -22.23% | 2/9 | **REJECTED** |
| H19 Volume-predictive return decomposition | SPY (primary), also QQQ/IWM for cross-validation | simple_lagged_median | 0.242 | 940 | 1.066 | -34.8% | 3/9 | **REJECTED** |
| H20 Volume-Sign / Order-Flow Imbalance | SPY daily OHLCV, QQQ/IWM cross-validation, ^VIX regime labels | lee_ready / tv0.05 / mp1.0 / lag3 | -0.156 | 2,958 | 0.973 | -22.1% | 2/9 | **REJECTED** |
| H21 Multi-Contract Intraday Futures TSMOM Generalization | ES=F, NQ=F, CL=F, GC=F, ZB=F (5-contract hourly futures basket) + ^VIX | target_vol_mult=0.5 / max_pos=0.5 / scale_rule=equal / n_assets=5 | 0.839 | 5,920 | 1.206 | -8.60% | 6/8 | **REJECTED** |
| H22 Futures TSMOM basket vol-targeting gap test | ES=F, NQ=F, CL=F, GC=F, ZB=F + ^VIX (2024-10-12 -> 2026-10-11 hourly, 55/25/20 splits, OOS = Val+Test) | target_vol_mult=1.0 (15% ann), max_pos=0.5, scale_rule=equal, n_assets=5 | 1.372 | 3045 | 1.334 | -11.9% | 9/9 | **PASS** |
| H23 Crypto perpetual futures intraday TSMOM | 5 crypto symbols (Coinbase/CCXT hourly OHLCV) | vol_window_long=252, smooth_span=16, regime_scaling=False, min_trade_interval=0, trailing_mult=1.5, max_hold_bars=60, vol_limit_mult=1.5, vol_floor_fraction=0.25 | -7.187 | 107 | 0.002 | -97.6% | 2/9 | **REJECTED** |
| H25 Futures TSMOM basket — PF-margin repair by vol-targeting expansion | ES=F, NQ=F, CL=F, GC=F, ZB=F + ^VIX (2024-10-12 -> 2026-10-11 hourly, 55/25/20 splits, OOS = Val+Test) | target_vol_mult=1.75 (26.25% ann), max_pos=0.5, scale_rule=equal, n_assets=4 (drop CL=F); selection = Val PF margin | 1.324 | 1,712 | 1.320 | -11.9% | 9/9 | **PASS** |
| H25 Robustness bootstrap-CI audit (audit of the H25 config above; mirror of H13 audit of H10) | same artifact `exp_2026-10-14T20-08-34-613690Z` | OOS PF 95% CI [1.2049, 1.4425], P(PF>=1.3)=0.6215; OOS Sharpe 95% CI [0.8834, 1.7506], P(Sharpe>=1.0)=0.9275 (2,000 resamples, seed 42) | 1.320 | — | 1.320 | — | audit | see §Conclusion (qualified) |

> **Table scale note (added by the H26 audit, 2026-10-19 — see §H26 detail below).** The
> "OOS Sharpe" column is **not on one scale**. Every published Sharpe is
> `sharpe_ratio(returns)` with the default `periods_per_year=252`, i.e. the
> **per-bar** mean/vol ratio × `√252`. For the **daily** rows (H1–H8, H16–H20) the bar
> is a trading day, so `√252` *is* the calendar annualization and those numbers are
> genuine annualized Sharpes. For the **intraday (1h)** rows (H9, H10, H11, H13, H21,
> H22, H23, H25) the bar is one hour, so the same multiplier annualizes neither the
> trading year (`√(252·6.5)`, the convention the intraday vol-target code itself
> uses) nor the calendar year (`√(bars_per_year) ≈ 75.5` for the 15.6-bars/day `=F`
> series). The intraday rows are therefore **understated** by **2.55×–4.76×** (the
> 24/7 crypto family H23 is 5.92×) and must not be compared directly against the daily
> rows. Multiplying the intraday Sharpe column by 2.55 (the repo's own, most conservative,
> vol-target convention) gives H9 2.69, H10 3.25, H21 2.14, H22 3.50, H25 3.37 — i.e. the
> intraday family is *under-credited* in the table above, not over-credited. No verdict,
> gate, or certified number changes.
>
> **H27 validity flag (added 2026-10-19 — see §H27 detail below).** The intraday rows
> above (H9, H10, H11, H13, H21, H22, H23, H25) are **not evidence of a tradable edge**:
> the daily-target collapse positions every session with that session's own *closing*
> signal (a one-day look-ahead). Re-running each family's selected config with a causal
> one-day lag gives OOS Sharpe 1.2758→**0.2923** (H10), 1.3725→**0.3605** (H22),
> 1.3236→**0.3231** (H25), and full-sample equity multiples 6.92×/79.80×/100.73× →
> **1.19×/1.89×/2.03×**. The verdicts in the table are as published (H27 changed no gate,
> threshold, verdict or certified number) but the family is **not established**.
>
> **H9 profit-factor footnote.** H9's published PF (1.252) is the **full-sample**
> (train+val+test) profit factor, because the H9 runner read the engine metric
> `result.metrics["profit_factor"]` instead of recomputing it on the OOS slice. The
> correct OOS-window PF is **1.2529**; both are below the 1.3 gate, so H9's REJECT
> verdict is unchanged (the defect was conservative). H10/H21/H22/H25 are unaffected
> (their published PF matches the OOS-window PF exactly).
>
> **H34 benchmark-gate footnote (added 2026-10-20 — see §H34 detail below).** The
> benchmark-significance gate (`p < 0.05` on a two-sided t-test of the excess returns) was
> **direction-blind**: it was satisfied by a significantly *negative* alpha. **H19**
> (p = 0.00260, IR **−0.880**), **H20** (p = 0.01595, IR **−0.704**) and **H23**
> (p = 0.00090, IR **−3.074**) carry such a PASS in the published rows above — their
> benchmark gate is evidence that they *underperform* the benchmark, not that they beat it.
> **H34 re-specified the gate** (`p < 0.05` **and** a positive excess return) and closed it in
> the code; these three rows' `p` passes must be read as "significantly different from the
> benchmark", not "significantly better". The published rows are unchanged. H33 separately
> repaired three *vacuous* benchmark gates (H4's `p`, H18's `benchmark_p`, H7's
> `max_p_value`/`min_information_ratio`); those repairs change no verdict and no published
> number.


### H23 detail (crypto perpetual futures intraday TSMOM)

H23 tested whether the H10/H22 intraday futures TSMOM mechanism generalizes to crypto perpetual futures on Coinbase. The pre-registered 2-year window (2024-10-12 → 2026-10-11) is **not achievable on free data**: Coinbase/CCXT hourly OHLCV returns only ~300 hours (2024-10-12 → 2024-10-24), a hard free-data limit. The experiment proceeded on the available window and is REJECT on a clean, non-degenerate basis.

Latest run (`exp_2026-10-14T18-13-09-457781Z`, 6912-combo grid, 0.039 CPU-h): selected config has OOS Sharpe **−7.187**, trades **107**, PF **0.002**, max DD **−97.6%**, WF stability 0.776, worst-regime Sharpe **−4.552** (sideways), IR −3.07, perturbation min ratio 0.0. Only 2/9 gates pass (walk-forward stability, benchmark p-value).

**Root cause:** the negative edge is structural on this sample. Regime decomposition shows all loss in the sideways regime (bull 0.0, sideways −4.552, bear 0.0), concentrated in ADA/DOGE noise (75 of 107 OOS trades). A sideways-regime filter ablation zeroes all positions (OOS Sharpe 0.0, 0 trades) because the free-data VIX proxy is constant at 20.0 → every bar is labeled "sideways", so filtering is not actionable. A `min_trade_interval=24` ablation improves OOS Sharpe to −2.144 but trades fall to 11 (below the 200-trade gate). Full attribution in `HYPOTHESIS_SPEC.md` §H23.

**What would change the verdict:** a free crypto data source providing ≥ 1 year of hourly OHLCV for major perpetuals, or a paid data subscription (Kaiko/CoinAPI) enabling the pre-registered 2-year window.

### H26 detail — Sharpe annualization-scale audit (executed 2026-10-19)

H26 is a **post-hoc audit of the published record**, not a new hypothesis and not a new
selection: no strategy was re-run, no gate, threshold, verdict, or certified number
was changed. It asks one question — *is the published "OOS Sharpe" an annualized
Sharpe for every family?* — and answers it by reproducing every audited artifact
bit-close from its own frozen returns and rescaling the same series under each
defensible annualization convention. Pre-registered in `HYPOTHESIS_SPEC.md` §H26
before execution; artifacts in `.experiments/artifacts/h26_sharpe_scale/`.

**Verdict: `SCALE_CONFIRMED` / `CONTROL_OK`.** The published metric is a
**√252-per-bar** Sharpe. For the intraday families it is **not** an annualized
Sharpe, and the mis-scaling *understates* the edge:

| Family | Verdict | Published (√252-per-bar) | ×2.5495 (repo vol convention) | ×4.7566 (empirical calendar) | daily-aggregated (independent estimate) |
|---|---|---|---|---|---|
| H10 | PASS | 1.2758 | 3.2526 | 6.0682 | 5.0366 |
| H21 | REJECT | 0.8394 | 2.1400 | 3.9925 | 3.5293 |
| H22 | PASS | 1.3725 | 3.4991 | 6.5283 | 5.1973 |
| H23 | REJECT | −7.1871 | −18.3236 | −42.5481 | −12.5024 |
| H25 | PASS | 1.3236 | 3.3746 | 6.2959 | 5.0916 |
| H16 (daily control) | — | — | — | ratio **0.9995** → already annualized | — |

**What this changes**

1. **Cross-family comparability.** The results table above mixed two scales; the
   intraday rows are now flagged and the corrected values are given. The intraday
   family is *under-credited*, so no rejection becomes a pass.
2. **The "Sharpe CI-fragile" caveat was a scale artifact.** The certified family's
   Sharpe bootstrap CI was quoted in the mis-scaled units. Rescaling the same
   bootstrap distribution (the CI scales linearly with the annualization factor) gives
   for H25: as published CI [0.8834, 1.7506], P(Sharpe ≥ 1.0) = 0.9275 → repo vol
   convention CI [2.2521, 4.4633], **P = 1.0000**; empirical calendar CI [4.2018,
   8.3271]. Same for H10 and H22. The audit reproduces the published CI bit-for-bit
   and then re-characterizes it: the Sharpe CI fragility is a property of the metric
   scale, not of the edge. **The profit-factor CI fragility is scale-invariant and
   stands** — PF is a ratio of gross sums — so the certification remains *qualified*
   for the PF margin, and no longer for the Sharpe.
3. **Two cross-artifact defects found by the reproduction anchor.** H9 failed the
   1e-9 anchor and is excluded from the audited set; its cause was diagnosed:
   (a) H9 was published with the *sample*-std (ddof=1) Sharpe estimator while H10 and
   later use the *population*-std (ddof=0) estimator of the current library
   (relative difference ≈ 1e-4, immaterial but no longer bit-reproducible), and
   (b) H9's published "OOS profit factor" is the **full-sample** PF (train window
   included); the correct OOS-window PF is 1.2529, still below the 1.3 gate, so
   **H9's REJECT verdict is unchanged**.
4. **Dependence check.** Max |lag-1..24 autocorrelation| is 0.026–0.045 and the
   Newey–West long-run-variance ratio is 0.78–0.99 for the four futures families, so
   square-root scaling is sound for them. H23's 134-bar crypto slice is strongly
   autocorrelated (lag-1 0.500), so its rescaled value is not reliable — immaterial,
   because H23 is REJECTED, but recorded.
5. **Flagged, not settled.** A corrected annualized Sharpe of 3.25–6.53 for the
   certified intraday family is *extraordinary* for a futures TSMOM strategy (real
   TSMOM Sharpes are ≈0.5–1.5). H26 does not audit that level and makes no claim
   about it; it records that the "the edge is marginal" framing of the record is at
   least partly a metric-scale artifact, and that the *magnitude* of the backtested
   P&L now deserves its own audit (position sizing / contract-multiplier / cost-scale
   consistency, and the plausibility of a 15% vol target producing ≈10.5%
   calendar-annualized realized vol at ≈32% calendar-annualized return).

**Verified:** 44 new tests in `tests/test_h26_sharpe_scale_audit.py` pin the
reproduction of every audited artifact, the scale factors, the linear CI rescaling,
the recomputed gate fractions, the daily control, the H9 exclusion with both
diagnoses, the dependence diagnostics, and the new `bars_per_year` /
`annualized_sharpe` library helpers (including negative guards that fail if the
scale correction, the frequency inference, or the PF-window diagnosis is undone).

### H27 detail — P&L level audit and look-ahead attribution (executed 2026-10-19)

H27 is a **post-hoc audit of the published record**, not a new hypothesis and not a new
selection: it re-runs no grid, changes no gate, threshold, verdict or certified number.
It asks the two questions H26 left open — *is the P&L level free of a unit/scale error?*
and *was the position that produced it knowable when it was traded?* Pre-registered in
`HYPOTHESIS_SPEC.md` §H27 before execution; artifacts in
`.experiments/artifacts/h27_pnl_level/`; runner `run_h27_pnl_level_audit.py`.

**Verdict: `LEVEL_CONFIRMED` / `LOOKAHEAD_CONFIRMED` → `certified_family_valid = false`.**

#### L1–L3 — the level is clean (no unit or scale error)

| Check | Result |
|---|---|
| L1 dollar P&L vs. logged returns (contract maths) | max abs diff **3.5e-16 – 4.9e-16** (H9/H10/H21/H22/H25) |
| L2 contract specs | `tick_value == tick_size × multiplier` for all 5 symbols; `cost_per_contract == commission + (spread+slippage) × tick_value` holds exactly |
| L3 cost drag recomputed from `trades.parquet` | max abs diff **6.8e-21 – 1.1e-19**; the drag is **1.1%–4.9%** of the gross edge |

`contracts = weight × 1e6 / (price × multiplier)` and `P&L = contracts × Δprice × multiplier`
reproduce the logged return series bar-for-bar. The extraordinary Sharpe is therefore *not* a
factor-of-1000 slip, a mis-scaled contract or a mis-stated capital.

#### L4 — vol-target coherence

The target is applied to the same hourly-return quantity the P&L is built from, so the target
and the realized figure are internally consistent. The *annualization* is not: the code
annualizes hourly bars with `√(252 × 6.5) = 1638` bars/year while the artifacts' own bar
index implies **5,701** bars/year (a factor **1.8657×**). Realized/target vol on the code's
own scale: H10 0.554, H22 1.365, H25 0.847, H9 0.670, H21 2.177 (H21 is the deliberately
under-vol-targeted variant and overshoots). This is the same scale mismatch H26 measured from
the Sharpe side; it is reported, not applied.

#### L5 — the positions were not knowable when they were traded

**The mechanism.** `run_h9_intraday_tsmom_experiment.py::_daily_target_from_hourly` collapses
the hourly signal to `resample("1D").last()` — a day-labelled series holding *that day's
closing* signal. `run_h10_intraday_tsmom_pfopt_experiment.py::build_hourly_target` then
expands it back onto the hourly grid with `reindex(index, method="ffill")`, which assigns
**every bar of day D the value of day D's label**. The session is therefore positioned at its
own open with the signal computed at its own close.

**Three independent proofs.**

1. *Artifact-only.* For all five families the logged daily collapse equals the logged signal at
   that day's **close** to 0.0, while the signal at that day's **open** differs by up to
   3.87–4.0; the expansion puts the close value on the open bar. For H21/H22/H25 the logged
   expanded hourly target matches the **same-day** expansion on **100%** of bars and the
   previous-day expansion on only **38.6%**.
2. *Bit-exact rebuild.* Each family's *selected* config was rebuilt from the committed prices
   and reproduces the committed `positions.parquet` **and** `returns.parquet` with max abs
   diff **0.0**; the rebuilt target matches the same-day expansion on 100% of bars.
3. *Causal counterfactual.* Shifting only the daily series by one day (nothing else in the
   pipeline changes) and re-running the same engine gives the table in the Executive Summary:
   the certified family's OOS Sharpe falls 74–77% and its full-sample equity multiple falls
   from 6.9×/79.8×/100.7× to 1.19×/1.89×/2.03×, against an equal-weight buy-and-hold of the
   same basket of 1.36× under a 5× gross leverage cap.

**Where the money came from.** Splitting the engine's own per-bar chain into the overnight
(previous close → session open) and intraday (open → close) components: the published build
books **94.7%–97.8% of its gross P&L intraday** (H25: 4.574 of 4.832), against 43.4%–76.7%
for the causal build (H25: 0.653 of 0.932) — the intraday P&L itself falls 4.574 → 0.653
for H25, i.e. **7.0×**.

**The model-free fingerprint.** If the position held at a session's *open* is aligned with
*that* session's move, the strategy is trading on information it could not have had at the
open. Measured on the committed artifacts: the mean of `sign(w_open) × r_intraday` is
**+0.00248** in the published build and **+0.00040** in the causal build — a **5.9×–6.2×**
excess tilt, consistent across all five families. The overnight component is earned almost
identically by both constructions (H25: 0.257 vs 0.279), which localises the entire
difference to the intraday, same-day part of the session.

**What H27 does *not* change.** No gate, threshold, verdict or certified number was changed:
H10/H11/H22/H25 remain PASS (8/8, 8/8, 9/9, 9/9) *as published*, and H9/H21 remain REJECT.
What H27 changes is the *interpretation*: the published PASS verdicts are inflated by a
look-ahead and are not evidence of a tradable edge, so the certified family is **not
established** pending an explicitly re-registered re-certification (H28). The counterfactual
re-runs the *selected* config only (no re-selection), so it is a **lower bound** on the defect.

**Verified:** 34 new tests in `tests/test_h27_pnl_level_audit.py` pin the level checks, the
contract-spec arithmetic, the vol-target coherence numbers, the artifact-only look-ahead
chain, the bit-exact reproduction of every audited artifact, the causal counterfactual, the
overnight/intraday attribution, the verdict strings, and negative guards that fail if the
checks are made vacuous (a wrong capital, a wrong contract multiplier, a wrong cost, a
hard-coded annualization, or a *causal* construction).

### H28 detail — causal re-certification of the intraday futures TSMOM family (executed 2026-10-19)

H28 is the **re-certification** H27 asked for. It is not a new hypothesis and not a new
selection: it re-runs the *published* H10/H21/H22/H25 pipelines with exactly one change — the
daily collapse is lagged by one calendar day — and gate-evaluates them with the **unchanged**
gates. Pre-registered in `HYPOTHESIS_SPEC.md` §H28 before execution; artifacts in
`.experiments/artifacts/h28_causal_recertification/`; runner
`run_h28_causal_recertification.py`.

**Verdict: every family `CAUSAL_REJECTED`; the certified family (`H10`, `H22`, `H25`) is
`CAUSAL_REJECTED`.** Runtime 6786.5 s ≈ 1.89 CPU-h, offline, no new data.

**The negative control passed for every family.** Each family's control run — the published
same-day expansion through the identical harness — reproduced the published artifact
**bit-exactly**: H10 9/9 artifacts and H21/H22/H25 12/12 each, **max abs diff 0.0** everywhere,
including `grid_results`, which pins the Val metrics of *every* one of the 13,824 H10 combos.
The selected configuration, every gate boolean and the verdict are identical. The single
documented exception is `metrics.wf_stability`, which moves only because the library's
`walk_forward_splits` was changed on 2026-10-19 09:28 (after the published runs); the published
value is reproduced bit-exactly by the pre-change implementation, and the gate that consumes it
is unchanged. **So the published record is fully reproducible, and the only thing that changes
the result is the causal collapse.**

**The results.** H10 OOS Sharpe **0.3909** / PF 1.087 / DD −10.1% (3/8 gates); H21 **0.1317** /
1.030 / −26.1% (3/8); H22 **0.3605** / 1.077 / −22.8% (4/9); H25 **0.3231** / 1.069 / −26.2%
(4/9). The failing gates are the same four in every family — `sharpe` (≥ 1.0), `pf` (≥ 1.3),
`worst` (worst-regime Sharpe ≥ 0.3) and `p` (benchmark p < 0.05) — plus `ir` for H10.

**The re-selection headroom, now measured.** H27's counterfactual re-ran only the
already-selected configuration and was therefore a lower bound. H28 re-ran the full grids:
H10 re-selects a *different* configuration (`smooth_span` None → 4, `regime_scaling` False →
True), lifting the causal Sharpe from 0.2923 to **0.3909** — real but small, still 2.6× below
the gate, with PF 0.21 short and a negative information ratio. H21/H22/H25 re-select the
published configuration itself, so their causal numbers coincide with H27's to the digit. **The
REJECT is not an artefact of a frozen configuration.**

**What H28 does not change.** No gate, threshold, verdict or certified number: H10/H11/H12/H22/H25
remain PASS as published, H9/H21 remain REJECT, the published artifacts were not rewritten and
the published runners were not edited. H28's verdict is an *additional* statement about the
family's tradability, not a retroactive invalidation of the published record.

**One repo fragility was exposed and closed.** The helpers that resolve a family's artifact
directory pick the *lexicographically last* depth-1 directory carrying that family's
`hypothesis` label; the H28 runs initially sat at depth 1 and were picked up as the published
family runs, which broke four H25-Robustness regression tests. H28's runs are now grouped under
`.experiments/artifacts/h28_causal_recertification/runs/<exp_id>/` and a regression guard fails
if that ever recurs. No published artifact, gate, verdict or certified number was touched.

**Verified:** 47 tests in `tests/test_h28_causal_recertification.py` pin the collapse semantics
(one-day lag, the weekend carry, the calendar guard), the module patch/restore (including on
failure), the experiment-identity and tracker capture, the control's sensitivity (a perturbed
artifact, a changed gate boolean, a changed verdict or an unexpected metric each void the
control), the verdict rule and the pre-registration itself.

## Conclusion

- **Supported:** the cost-model bug is real and fixed; volatility-scaled momentum *implementation* is correct; the infra runs end-to-end.
- **Certified (as published, but see H27):** H10 (intraday futures TSMOM, PF-optimized) passes all 8 gates; H11 certifies robustness; H12 certifies the result against selection bias; H22 (vol-targeting gap closed) passes all 9 gates; H25 (PF-margin repair by vol-targeting expansion on a pruned 4-contract basket, drop CL=F) passes all 9 gates. H22 remains the strongest by Sharpe (1.372); H25 is the strongest PF-margin repair (OOS PF 1.320 at 26.25% ann vol, perturbation-robust min ratio 0.946). **H27 caveat: these published verdicts are inflated by a one-day look-ahead in the daily-target collapse (OOS Sharpe −74% to −77%, equity multiple 6.9×/79.8×/100.7× → 1.19×/1.89×/2.03× under the minimal causal fix). The family is *not established*; the verdicts stand as published because H27 is an audit, not a re-certification.**
- **Invalidated pending re-certification (H27):** the certified intraday family (H10/H11/H12/H22/H25) is built on a construction that positions every session with that session's own closing signal. The P&L *level* is not the problem (L1 ≤ 4.9e-16, L2 exact, L3 ≤ 1.1e-19) — the *information timing* is. Under the minimal causal fix the family's OOS Sharpe is 0.29–0.36, below the 1.0 gate, and 94.7%–97.8% of the published gross P&L is intraday P&L earned with same-day foresight.
- **Re-certified and REJECTED (H28):** the re-certification has now been run. Under a causal daily collapse — same gates, same splits, same Val-only selection, same Test protection, same cost model, full grids re-run — **every family fails** (H10 3/8, H21 3/8, H22 4/9, H25 4/9): OOS Sharpe 0.13–0.39 against a 1.0 gate, PF 1.03–1.09 against 1.3, max DD −10% to −26% against −15%. All four negative controls reproduced the published artifacts bit-exactly, so the comparison is sound; and the causal re-selection buys at most +0.10 Sharpe, so the verdict is not an artefact of a frozen configuration. **The certified family is not a tradable edge.** The published PASS verdicts stand as published (H28 changed no gate, threshold, verdict or certified number), but they are now demonstrated to be worthless as evidence of tradability.
- **Qualified (H13 / H25 Robustness):** the certification is Sharpe-robust (worst-case DSR-adj OOS Sharpe 1.2745, p = 0.001) but the PF margin is fragile/CI-fragile — H13 bootstrap 95% CI [1.190, 1.425] for H10; the H25 Robustness audit gives OOS PF 95% CI [1.2049, 1.4425] with P(PF≥1.3)=0.6215 (point-wise pass, CI lower bound below 1.3). The pre-registered block-bootstrap sensitivity (stationary block bootstrap, b=2 on the 5,148-bar OOS slice) gives PF CI [1.2046, 1.4458] P(PF≥1.3)=0.6460 with block-boot LB ≤ i.i.d. LB, so the fragility is REINFORCED under time-series dependence rather than an i.i.d. artifact. **Correction from the H26 scale audit:** the *Sharpe* half of this caveat was a metric-scale artifact — the published Sharpe is a √252-per-bar metric, and rescaling the same bootstrap distribution to the repo's own annualization convention moves the H25 Sharpe CI from [0.8834, 1.7506] to [2.2521, 4.4633] (P(Sharpe ≥ 1.0) = 1.0000). The **PF margin fragility is scale-invariant and stands**, so the certification remains *qualified* on the PF margin (and only on it); production use still requires a longer OOS window (paid data).
- **Scale-corrected reading of the intraday family (H26):** the published Sharpe of the intraday rows is a **√252-per-bar** metric, not an annualized Sharpe; the correct annualized values are 2.55×–4.76× higher (H10 3.25, H22 3.50, H25 3.37 under the repo's own vol-target convention; 6.07/6.53/6.30 under the empirical calendar convention, confirmed by an independent daily-aggregation estimate of 5.04/5.20/5.09). The daily rows were already correctly annualized and are unaffected. The mis-scaling therefore *understates* the intraday family; it creates no pass and invalidates no verdict. It does mean the single "OOS Sharpe" column of the results table mixed two scales, and that the "the edge is marginal" framing of this record is partly a scale artifact.
- **Rejected:** H1–H9 (momentum/TSMOM on free data), H16 (factor timing), H17 (VRP), H18 (overnight/intraday), H19 (volume-predictive), H20 (signed volume), H21 (multicontract futures TSMOM), H23 (crypto perpetual futures intraday TSMOM — negative edge on the cached 300-hour Coinbase sample, loss concentrated in the sideways regime; full attribution in `HYPOTHESIS_SPEC.md` §H23).

## Summary statistics (H1–H30)

- **29 hypothesis instances** evaluated across 7 families: equity momentum (H1–H3), futures TSMOM (H4–H14), equity factor timing (H16), volatility risk premium (H17), overnight/intraday decomposition (H18), volume-based (H19–H20), multi-contract intraday futures TSMOM (H21–H22), crypto perpetuals (H23), PF-margin repair (H25), plus the H25 Robustness bootstrap-CI audit, the **H26 Sharpe annualization-scale audit**, the **H27 P&L level audit + look-ahead attribution**, the **H28 causal re-certification** and the **H29 systematic look-ahead sweep of the remaining families** (the first three are post-hoc characterizations of the H25/H10 edge, not new selections; H28 is a re-certification of the published pipelines under a corrected construction and H29 is an audit of every family's collapse construction, with no new gate, threshold or selection rule). H15 was a probe (LOO PF 1.273 < 1.3; CL=F indispensable), folded into H13. H24 was report consolidation (not an experiment).
- **5 certified edges** (H10/H11/H12/H22/H25) — all variants of the same intraday futures TSMOM mechanism (**H27: the edge is a one-day look-ahead; H28: re-certified under a causal collapse and `CAUSAL_REJECTED` — 3/8 to 4/9 gates, OOS Sharpe 0.13–0.39; H29/H30: the daily/monthly families are `CAUSAL` on the committed artifacts, including H7 once its artifact was committed, while H11/H12 inherit H10's look-ahead positions and H23 uses the same collapse — so **no certified edge in this record survives a causal construction**); of these H22 has the strongest Sharpe (9/9 gates, OOS Sharpe 1.372, PF 1.334, DD −11.9%) and H25 the strongest PF margin (9/9 gates, OOS Sharpe 1.324, PF 1.320, DD −11.9% at 26.25% ann vol); both are *qualified* by an i.i.d. bootstrap CI whose lower bound sits below the PF gate, and the pre-registered block-bootstrap sensitivity confirms the PF fragility is not an i.i.d. artifact. (H26: the published Sharpe is a √252-per-bar metric — the annualized values are 2.55×–4.76× higher; the *PF* qualification is unaffected because PF is scale-invariant.)
- **19 rejected** hypotheses, each with a documented root-cause attribution in `HYPOTHESIS_SPEC.md` and `INEFFICIENCY_RANKING.md`.
- **Total compute:** ~2.5 CPU-h across all hypotheses (well within the ≤ 2 CPU-h per-hypothesis budget; the largest single run was H12 at 0.652 CPU-h). The H25 Robustness audit added 0.0002 CPU-h; the H26 scale audit added 0.0005 CPU-h; the H27 level/look-ahead audit added 0.0014 CPU-h (5 bit-exact rebuilds, no grid re-run); the **H28 causal re-certification added 1.885 CPU-h** (8 runs: 4 controls + 4 causal, the 13,824-combo H10 grid run twice); the **H29/H30 look-ahead sweep added 0.0002 CPU-h** (8 bit-exact rebuilds of the *selected* configurations, one counterfactual, no grid re-run).
- **Test suite:** 1263 passing, 1 skipped (including the 17-test H25 Robustness audit — 12 i.i.d. bootstrap + 5 block-bootstrap sensitivity — the 23-test H25 regression set, the 44-test H26 scale-audit set, the 36-test H27 level-audit set, the 47-test H28 re-certification set and the 36-test H29 sweep set, plus the 2 new H31 `compare_to_benchmark` DataFrame/ndarray regression tests, plus the 6 new H32 `deflated_sharpe_ratio` + `purged_kfold_splits`/`combinatorial_purged_cv` regression tests, plus the 12 new H33 benchmark-contract tests, plus the 10 new H34 direction-aware benchmark-gate tests, plus the 11 new H35 gate-vacuity contract tests and the 1 new H35 one-sided-vs-gate non-equivalence test, plus the 30 new H36 point-in-time contract tests, plus the 179 new H37 runner-causality inventory tests, plus the 13 new H38 engine-metric-consistency tests, plus the 49 new H39 cross-module metric-agreement tests, plus the 42-test H40/H41 runner-metric-agreement contract — 33 tests in H40 and 9 in H41, plus the 18 new H43 coverage-gate contract tests — 6 gate pins and 12 branch-closure tests, plus the 33 new H45 public-API contract tests — 4 packaging pins, 22 subpackage-declaration pins and 7 top-level/star-import pins). The single skip is `buy_and_hold`, a constant position that cannot react to a perturbation. **H42 added no tests** (whitespace-only change to the inventory file).
- **Coverage (corrected by H33, re-measured by H34 and H38, measured and gated by H43):** the H33 baseline of **94%** was caused by the dead `deflated_sharpe_ratio` body (16 uncovered statements in `src/qtr/validation/statistics.py`). H34 **deleted** that dead code (it was not exported, had no caller and duplicated `run_h12_selection_bias_audit.py:deflated_sharpe_ratio` with the same `max_z` formula). **H43 finally measured the claim** (H39–H42 had re-asserted it from a branch argument because `pytest-cov` was not installed): the recorded figure was exactly right — `src/qtr` had **1014 statements, 0 missed** — but it was a **statement**-coverage figure, and statement coverage cannot see a branch that is never taken. The first branch measurement found **11 partial branches** behind the 100% (99% combined). All 11 are now closed by named tests (§H43) and the gate is committed: `pyproject.toml` declares `[tool.coverage.run] branch = true`, `source = ["src/qtr"]` and `[tool.coverage.report] fail_under = 100`, so `python -m pytest -q --cov=qtr --cov-branch` **fails** below full coverage. Measured now: `src/qtr` = **1038 statements, 316 branches, 0 missed, 0 partial, 100.00%** ("Required test coverage of 100.0% reached"). (The 22 statements added by H45 are the package `__init__.py` files, which the coverage gate now measures as part of the package.) (The H32 handoff's "99%, one uncovered branch" claim was wrong: its named guard — the `walk_forward_splits` empty-window branch at `statistics.py:159-160` — is covered by `tests/test_statistics.py:185`.)
- **Benchmark gates (H33 + H34 + H35):** three published benchmark gates were vacuous (H4's `p`, H18's `benchmark_p`, H7's `max_p_value`/`min_information_ratio`) because the runner read a key the library never returns, passed a boolean mask as `risk_free`, or compared returns against **price levels**. They are repaired and pinned by an executable contract; the recomputed tallies are H4 1/8 (unchanged), H7 5/9 (published 4/9), H18 3/9 (published 2/9); no verdict changes. The pre-registered gate was also *direction-blind* — it is satisfied by a significantly **negative** alpha. **H34 re-specified it** (`p < 0.05` **and** a positive excess return), closed it in the code for all 17 runners and disclosed the impact: four published artifacts (H3, H19, H20, H23) carry a wrong-reason `p` PASS; the certified families (H10, H22, H25) survive; no published row, threshold, verdict or certified number changes. **H35 audited the remaining gate class** — gates that are a constant, or that compare a placeholder, and can therefore never fail — and found three of them: **H7's** `min_perturbed_sharpe_ratio` and `min_worst_regime_sharpe` (hard-coded `True`) and **H18's** `perturbation_ratio` (a placeholder constant). Both families are REJECT, so no published verdict rests on them (H7's published 4/9 is 2/7 on the evaluable gates; H18's published 2/9 is 1/8). Three runners (H4/H5/H6) also read their IR threshold through a permissive default (`GATES.get(..., -1e18)`), which is now a direct subscript so a missing threshold fails loudly. No certified family has a non-evaluating gate.
- **Structural walls on free data:** (a) yfinance hourly `=F` hard-capped at ~730 days (no bars beyond 2026-10-11); (b) Coinbase/CCXT hourly OHLCV capped at ~12 days; (c) the joint Sharpe ≥ 1.0 ∧ DD ≤ 15% gate met by no long-only free-data equity family; (d) PF ≥ 1.3 is fragile across the entire intraday-futures-carry family (H13/H14 for H10; H21 for the basket; H22 margin +0.034; H25 margin +0.020 — all CI-fragile, P(PF≥1.3)≈0.5–0.62 on the free window). **Corrected by H26:** the *Sharpe* side of (c)/(d) is not a further blocker — the published intraday Sharpe is a √252-per-bar metric, and on the repo's own annualization convention the certified family's Sharpe CI lower bound is 2.25 ≫ 1.0. The binding constraint is the **PF bootstrap margin plus the 730-day sample**, both of which are scale-invariant.

## Next Task

FINAL_REPORT.md now reflects H1–H29 (H24 = report consolidation), the H25 Robustness
bootstrap-CI audit, the H26 Sharpe annualization-scale audit, the H27 P&L level audit +
look-ahead attribution, the H28 causal re-certification and the H29 look-ahead sweep of the
remaining families. Current verified state:

- The pre-registered free-data hypothesis space is **exhausted**. The only PASS family on free
  data is the intraday futures TSMOM mechanism (H10/H11/H22/H25); H25 is the strongest PF-margin
  repair. H25 is **qualified**: point-wise it clears all 9 gates (Sharpe 1.324, PF 1.320, DD
  −11.9%, perturbation-robust), but the H25 Robustness audit shows the PF margin is **CI-fragile**
  (95% CI [1.2049, 1.4425], P(PF≥1.3)=0.6215). The residual, irreducible blocker is the free-data
  horizon (yfinance hourly `=F` capped ~730 days; Coinbase ~12 days), not a selection or gate defect.
- **Corrected by H26 (2026-10-19):** the published Sharpe is a √252-**per-bar** metric, so the
  intraday family's Sharpe CI fragility quoted above (95% CI [0.8834, 1.7506]) is a **scale
  artifact** — rescaled to the repo's own annualization convention the CI is [2.2521, 4.4633] with
  P(Sharpe≥1.0)=1.0000. The **PF margin fragility is scale-invariant and remains the binding
  constraint**, together with the 730-day sample. The "Next Task" below is unchanged in substance
  but its justification is now narrower and evidence-based.

*(As written after H26 and **superseded by H27 below**: the paid-data task was the next task
until the level audit found the look-ahead. It is now queued behind H28 — buying more data for
a construction with a look-ahead would be wasted.)*

**H27 (2026-10-19) has now answered that question, and the answer changes the priority.**
The level audit found **no** unit/scale error (the dollar P&L reproduces the logged returns to
≤4.9e-16), but it found that the certified family's positions were **not knowable when they were
traded**: the daily-target collapse positions every session with that session's own closing
signal (a one-day look-ahead in H9/H10/H21/H22/H25 alike). The causal counterfactual collapses
the certified family's OOS Sharpe by 74%–77% (H10 1.276→0.292, H22 1.372→0.361,
H25 1.324→0.323) and its full-sample equity multiple from 6.9×/79.8×/100.7× to
1.19×/1.89×/2.03×, against an equal-weight buy-and-hold of the same basket at 1.36×. The
published PASS verdicts stand as published but are **not evidence of a tradable edge**.

**The next task is therefore no longer the paid-data task: it is H28 — re-certify the intraday
futures TSMOM family under a causal daily collapse** (same gates, same splits, same Val-only
selection, same Test protection; the 13,824-combo H10 grid is now permitted because a defect
was found and the re-registration is explicit). Expect **REJECT**: the causal counterfactual on
the already-selected configs is OOS Sharpe 0.29–0.36, PF 1.06–1.08, max DD −12% to −26%, all
below the gates. Buying more data for a construction with a look-ahead would be wasted, so the
paid-data task stays queued **behind** H28. Full scope: `NEXT_TASK.md`; evidence:
`HYPOTHESIS_SPEC.md` §H27 and `FINAL_REPORT.md` §H27 detail.

**H28 (2026-10-19) has now been executed, and the expectation was correct.**
`HYPOTHESIS_SPEC.md` §H28 (pre-registered before execution) → **`CAUSAL_REJECTED` for every
family**: H10 OOS Sharpe **0.3909** / PF 1.087 / DD −10.1% (3/8 gates), H21 **0.1317** / 1.030 /
−26.1% (3/8), H22 **0.3605** / 1.077 / −22.8% (4/9), H25 **0.3231** / 1.069 / −26.2% (4/9). All
four negative controls reproduced the published artifacts **bit-exactly** (max abs diff 0.0,
including every one of the 13,824 H10 grid rows), so the comparison is sound; and the causal
re-selection buys at most +0.10 Sharpe (H10 re-selects `smooth_span=4, regime_scaling=True`),
so the REJECT is not an artefact of a frozen configuration. The published PASS verdicts stand as
published — H28 changed no gate, threshold, verdict or certified number — but the family is now
**demonstrated not to be a tradable edge**.

**H29 (2026-10-19) has now been executed, and the labelling rule was confirmed on the committed
artifacts.** The verdict is `LOOKAHEAD_FOUND`, but only for families that *inherit or use* the
intraday daily collapse: H11, H12, H13 (inherited from H10, bit-identical positions) and H23
(uses the collapse directly, and is REJECTED anyway). The daily/monthly families H1–H8 are all
**`CAUSAL`** — each rebuilt **bit-exactly** from the committed prices (H7 via H30 below),
minimum hold lag **+1 bar**, **0** look-ahead bars.

**H30 (2026-10-19) has now been executed.** H7's artifact was committed as
`exp_2026-10-19T18-56-08-872500Z` (offline on the completed futures cache; recorded in
`.experiments/experiments.jsonl` through the tracker), the re-run reproduces the published H7
row to reporting precision (OOS Sharpe 0.789 vs 0.7893, 1,005 vs 1,005 trades, PF 1.166 vs
1.1661, max DD −14.5% vs −14.54% OOS, verdict REJECT vs REJECT), with two disclosures logged
explicitly (`compare_to_benchmark` raised advisory in this session; gate tally 3/8 published vs
4/9 recomputed) and the published row left as the historical record. Determinism was confirmed
by a second bit-identical run. The H29 detector re-run with H7 added to `FAMILIES` reports H7
**`CAUSAL`** (min hold lag +1 bar, 0 look-ahead bars, bit-exact equity rebuild, 0 extra change
points, same/prev 0.130/0.970), all four self-checks pass, and the sweep verdict stays
`LOOKAHEAD_FOUND`. The H29 sweep's only coverage gap is **closed**; see §H30 and
`NEXT_TASK.md`.

**There is no further next task in this record.** The pre-registered free-data hypothesis space
(H1–H30) is exhausted: every family has a committed artifact or a documented reason for the
gap, every daily/monthly family is `CAUSAL` and REJECTED, every intraday family is
`CAUSAL_REJECTED` under H28, and the paid-data task (wider OOS window for the PF bootstrap
margin) is unjustified for every family in the repo — H28 closed it for the intraday family and
H29/H30 show the daily families are causal but all REJECT. Buying more free-data-equivalent
data changes no verdict.

**H31 — the H30 advisory was a real defect and is fixed (2026-10-20).** H30 recorded that
`compare_to_benchmark` raised `"The truth value of a Series is ambiguous"` during H7's re-run
and logged it as advisory. It was in fact a bug in `src/qtr/validation/statistics.py`:
`compare_to_benchmark` assumed a 1-D benchmark and raised whenever the caller passed a
multi-column DataFrame (which is what H7 does — `prices[FUTURES_UNIVERSE]`, a 5-column
slice). The function now reduces a DataFrame benchmark to its row-mean series (and likewise a
2-D ndarray) before aligning, so the comparison is computed rather than skipped. The fix is
in the library, not in H7's runner (the runner's `try/except` is preserved), and it changes no
published number: the benchmark is advisory in H7's gate set, both benchmark-fed gates were
already False in the published row's 3/8 count, and the verdict is REJECT either way. The
committed artifact `exp_2026-10-19T18-56-08-872500Z` is untouched (`benchmark: null` is the
historical record of the run as executed); a verification re-run produced `benchmark = {alpha:
NaN, ir: -38.34, p_value: NaN}` with `prices`/`equity_curve`/`returns`/`trades` bit-identical
to the committed artifact and OOS Sharpe (0.7893261992589912), trades (1,005), profit factor
(1.16605221165269), max DD (−14.54%) and verdict (REJECT) unchanged. Two new regression tests
pin the behaviour; the pre-existing `compare_to_benchmark` tests are unchanged in expectation.

**H33 — three benchmark gates were vacuous and are repaired (2026-10-20).** The audit of all 17
`compare_to_benchmark` call sites found three defects that made a published gate evaluate a
constant instead of a statistic (H4's `p`, H18's `benchmark_p`, H7's `max_p_value` /
`min_information_ratio`): a key-name mismatch against the library's return dict, a boolean mask
passed positionally as `risk_free`, and a benchmark that was a **price level** compared against a
**return** series. The library now rejects a non-scalar `risk_free`, drops NaN pairs instead of
returning a half-NaN dict, and fails closed on degenerate inputs; the three runners read the
keys the library actually returns; and `tests/test_benchmark_gate_contract.py` pins the contract
statically over every call site (the same suite run against the pre-fix source fails 8 tests and
names the three sites). Recomputed offline from the committed artifacts: H4 p = 0.4592 (gate
still False, tally 1/8 unchanged), H7 alpha 0.0999 / IR +0.3002 / p 0.3432 (`min_information_ratio`
False → True, recomputed 5/9 vs published 4/9), H18 p = 0.0410 (gate False → True, recomputed 3/9
vs published 2/9). The published IRs are reproduced bit-exactly. **No verdict changes** (all
three families are REJECT with ≥ 5 other failing gates) and no published artifact, gate,
threshold or certified number was modified. The repair also exposes a **disclosure**: the
pre-registered benchmark-significance gate is *direction-blind* (a two-sided `p < 0.05` is
satisfied by a significantly **negative** alpha), and H19 (p = 0.0026, IR −0.880), H20
(p = 0.0159, IR −0.704) and H23 (p = 0.0009, IR −3.074) already carry such a PASS. The gate
definition is pre-registered and is **not** changed here; it is the next task.


---
## Next Task (updated 2026-10-21, after H40 — **superseded**)

> **Superseded.** The task assigned in this section was **completed in H41** (the runner-inline
> metric sites are pinned by `tests/test_runner_metric_agreement.py`). The current assignment is
> in the **§H45 "Next task"** section at the end of this report; `NEXT_TASK.md` carries the same
> statement. The text below is retained as the H40-era record.

**H34 and its follow-up are complete, H35 has closed the last open gate-defect class, H36 has
closed the point-in-time gap in the shared infrastructure, H37 has closed it in the
runners' inline signal code, H38 has closed the `total_return` horizon defect, H39 has closed
the last open metric defect — the package's two Sharpe implementations disagreed — and H40 has
extended the metric-agreement contract to the runners' own metric implementations.** The three
items H34 left behind were finished in the session that followed it; **H35** then audited the
remaining gate class; **H36** pinned the point-in-time contract of the shared signal library and
backtest engine; **H37** extended the same contract to the runners' own position series and
found one look-ahead the record did not state (H18's `vix_regime` predictor); **H38** found that
the engine's `total_return` dropped the first bar and fixed it; **H39** found that the engine's
Sharpe used the *sample* standard deviation while `sharpe_ratio` uses the *population* one and
closed it; **H40** classified and pinned every runner-local metric computation — the six
`_period_metrics` helpers (H10, H16, H17, H19, H20, H23), `train_only_wf_sharpe` (H16),
`window_max_drawdown` (DDCV), H26's daily Sharpe and the CS-momentum information ratio — as
either agreeing exactly with `qtr.validation.statistics` or as a pinned documented difference.

**One task is assigned** (stated in full in `NEXT_TASK.md`):

> **Pin the remaining runner-local metric sites that agree with the library but are not yet
> pinned by test** — the inline drawdowns using
> `(equity - equity.expanding().max()) / equity.expanding().max()`
> (`run_ddcv_experiment.py:386,443`, `run_futures_tsmom_experiment.py:286,467`,
> `run_h11_robustness_experiment.py:548,648`, `run_h18_overnight_intraday_experiment.py:527,641`)
> and H18's runner-local `total_return` copies (`:526, :637`, which use the pre-H38 range on
> frozen artifacts; bounded 6.34 bps, and H18's nine gates do not use `total_return`).
> Extend `tests/test_runner_metric_agreement.py` (or a sibling module) so every metric the
> runners compute locally is either asserted-agreeing or pinned-differing.

The state a next session inherits:

- The pre-registered free-data hypothesis space (H1–H30) remains **exhausted**; no new
  hypothesis is warranted and no grid may be re-run.
- The certified families (H10, H22, H25) are unchanged, and **no certified family owns a
  non-evaluating gate** — the H35 audit covers every gate site in the repository.
- Every published artifact, threshold, verdict and certified number is frozen. Every
  recomputed number in this report is a **disclosure**, not a rewrite.
- The shared library, the engine **and every `run_*.py` in the repository** are now pinned as
  **point-in-time**; keep them that way (re-run `tests/test_causality_invariant.py` after any
  change under `src/qtr`, and `tests/test_runner_causality_inventory.py` after any change in a
  `run_*.py`).
- The test suite now runs **from a bare clone with no install step** (`pyproject.toml` carries
  `pythonpath = ["src"]`); before H36 the suite could not even be collected in an environment
  where the package had not been pip-installed.
- The two small items that H37 listed as open are now closed: the engine's
  `metrics["total_return"]` is **fixed** (§H38 — it now spans every bar, and the two metric
  functions of the package can no longer disagree), and
  `DataFetcher.fetch_sp500_constituents(date=...)` no longer silently returns the *current*
  constituent list (a historical `date` raises `ValueError`, and the branch is tested).
- The **metric surface** of the library and the runners is now internally consistent and pinned
  (§H39 and §H40): the engine and `validate_strategy` agree exactly on all six shared metrics,
  the Sharpe convention is the record's (population std, ddof=0), the six `_period_metrics`
  helpers and their siblings are classified and pinned, H26's daily Sharpe convention is
  disclosed and bounded, and the one published family on the other convention (H9) is disclosed
  and bounded. Keep it that way: re-run `tests/test_engine_metric_agreement.py` after any change
  to `_calculate_metrics` or to `qtr.validation.statistics`, and
  `tests/test_runner_metric_agreement.py` after any change to a runner's local metric helper.

Constraints carried forward: no published artifact, gate threshold, verdict or certified number
may be modified; no grid may be re-run; every recomputed number is a disclosure; the pre-existing
H1–H30 hypothesis space remains exhausted (no new hypothesis is warranted); the certified
families' numbers and verdicts are frozen.


---


## H29 — Systematic look-ahead sweep of the *remaining* families (2026-10-19)

**Verdict: `LOOKAHEAD_FOUND`.** The look-ahead is confined to the **intraday** construction, but
the sweep found that the intraday defect reaches **four families that had not been audited for
it** (H11, H12, H13, H23), and it **certified the daily/monthly families as clean** on the
committed artifacts.

| Family | Construction | Min hold lag | Look-ahead bars | same / prev expansion | Verdict | Published |
|---|---|---|---|---|---|---|
| H1 | `ME` monthly | **+1** | 0.0% | 0.401 / 0.980 | **CAUSAL** | REJECT |
| H2 | `ME` monthly | **+1** | 0.0% | 0.416 / 0.980 | **CAUSAL** | REJECT |
| H3 | `ME` monthly | **+1** | 0.0% | 0.079 / 0.968 | **CAUSAL** | REJECT |
| H4 | `ME` monthly | **+1** | 0.0% | 0.420 / 0.972 | **CAUSAL** | REJECT |
| H5 | `ME` monthly | **+1** | 0.0% | 0.424 / 0.980 | **CAUSAL** | REJECT |
| H6 | `ME` monthly | **+1** | 0.0% | 0.454 / 0.980 | **CAUSAL** | REJECT |
| H7 | `ME` monthly | **+1** | 0.0% | 0.130 / 0.970 | **CAUSAL** | REJECT |
| H8 | `ME` monthly | **+1** | 0.0% | 0.391 / 0.980 | **CAUSAL** | REJECT |
| H11 | `1D` daily (inherited) | **−22** | 94.7% | 1.000 / 0.016 | **LOOKAHEAD** | PASS |
| H12 | `1D` daily (inherited) | **−22** | 94.7% | 1.000 / 0.016 | **LOOKAHEAD** | PASS |
| H13 | `1D` daily (inherited) | **−22** | 94.7% | 1.000 / 0.016 | **LOOKAHEAD** | REJECT |
| H23 | `1D` daily | **−22** | 96.0% | 1.000 / 0.385 | **LOOKAHEAD** | REJECT |

**The discriminator is the bin label, and it was probed, not assumed.** On the installed pandas
(3.0.6) `resample("1D")` labels each bin at its **start** (day D 00:00) with the value of day
D's **close**, while `resample("ME")` labels each bin at its **end** (the calendar month end)
with the value of the month's **close**. The engine trades `signals.shift(1)`, so a value that
first appears on bar `d` is first traded on bar `d+1`; the **hold lag** is `d+1 − s` (`s` = the
bar whose raw signal the value carries). A hold lag ≤ 0 is a look-ahead. The monthly families
have a hold lag of **+1 bar everywhere** (the month-end value is knowable at that bar's own
close and is traded from the next bar); the intraday collapse has **−22 bars** (94.7%–96.0% of
the bars are positioned with the close of the day they belong to).

**Every daily-family verdict rests on a bit-exact rebuild.** H1–H6 and H8 were rebuilt from the
committed `prices.parquet` with each family's *own* runner code and the published configuration,
and reproduced the committed artifact **bit-exactly** (max abs diff `0.0`); the committed
target's change points are a strict subset of the change points the classified construction
predicts (**0 extra**). The sweep's own machinery reproduces H27's result on the already-audited
family (H9/H10/H21/H22/H25 → `LOOKAHEAD`, same/prev = 1.000/0.016 and 1.000/0.382) and reports
H27's *causal* daily collapse as `CAUSAL` (hold lag +2, previous-period expansion on 100% of the
bars) — the detector fires on the defect and stays silent on its repair.

**H11 / H12 / H13 — the defect travels with the PASS.** The three diagnostics inherit H10's
construction, and the inheritance is proved from the committed artifacts: H11's
`baseline_positions` are **bit-identical** to H10's `positions` (max abs diff `0.0`), H12's
`selected_oos_sharpe` equals `h10_artifact_oos_sharpe` to the digit, and H13's
`returns_max_abs_diff_vs_h10` is `0.0`. **H11's and H12's PASS verdicts rest on the same
look-ahead positions as H10's**, so they are *not* independent evidence of an edge, and they
travel with H28's `CAUSAL_REJECTED`. No published verdict was changed.

**H23 (crypto) — the premise was wrong, and the family inherits the defect.** The crypto runner
imports `_daily_target_from_hourly` from H9 and calls it in `build_hourly_target`: it **does**
use the daily collapse (the next-task brief said it did not). The published build was rebuilt
from the committed prices and reproduces the committed positions **bit-exactly** and the
published summary to the digit (OOS Sharpe **−7.187089456116173**, 107 trades, max DD −97.56%);
under the minimal causal fix the OOS Sharpe is **−5.8929** (76 trades, DD −90.5%). A look-ahead
is a *favourable* bias, so removing it cannot rescue the family: **H23 remains REJECTED**, and
no causal re-certification of H23 is warranted. (The intraday/overnight P&L split is not
applicable to a continuous 24/7 market; the equivalent magnitude is the 96.0% look-ahead bar
fraction.)

**H7 is no longer a coverage gap.** H30 (2026-10-19) re-ran
`run_h7_intraday_tsmom_experiment.py` offline on the completed futures cache (all five symbols
served from `.cache/data`; no network), committed the artifact as
`exp_2026-10-19T18-56-08-872500Z` under `.experiments/artifacts/` and recorded the experiment
in `.experiments/experiments.jsonl`. The re-run reproduces the published H7 row to reporting
precision — OOS Sharpe 0.789 vs 0.7893, 1,005 trades vs 1,005, PF 1.166 vs 1.1661, max DD
−14.5% vs −14.54% (OOS window; −21.4% full-sample, which is what the gate measures), verdict
REJECT vs REJECT — with two disclosures logged explicitly (`compare_to_benchmark` raised
advisory in this session, so the re-run's benchmark is null; the gate tally differs by one,
3/8 published vs 4/9 recomputed) and the published row left as the historical record. A
second run confirmed determinism (all four parquets bit-identical). The H29 detector was then
re-run with H7 added to `FAMILIES` (`rebuild_pipeline`, `"ME"` on the daily grid, target
`equity_curve`) and reports H7 **`CAUSAL`**: min hold lag **+1 bar**, **0** look-ahead bars,
committed equity curve reproduced **bit-exactly** (max abs diff `0.0`), **0 extra** change
points, same/prev 0.130 / 0.970 — the same as H1–H6 and H8. The sweep verdict stays
`LOOKAHEAD_FOUND` and all four detector self-checks pass. See §H30.

**Two premises of the next-task brief were corrected.** (i) The brief called the daily families
"the only other PASS family in the repo" — **no daily family passes**: H1 0.093, H2 0.116,
H3 −0.868, H4 0.376, H5 0.509, H6 0.708, H7 0.789 and H8 0.814 are all REJECTED. The only PASS
families (H10, H11, H12, H22, H25) are all intraday, and all are now `CAUSAL_REJECTED` under
H28's causal construction. **The repo contains no PASS family that survives a causal
construction.** (ii) H23 was described as free of a daily collapse — it is not.

**Nothing published was touched.** No artifact, runner, gate, threshold, verdict or certified
number was modified, and no grid was re-run: H29 rebuilds only the *selected* configuration of
the families it measures. Evidence: `HYPOTHESIS_SPEC.md` §H29 (pre-registration, the
pre-execution amendment and the measure log), `run_h29_lookahead_sweep.py`,
`.experiments/artifacts/h29_lookahead_sweep/`, `tests/test_h29_lookahead_sweep.py` (36 tests).

## H30 — Close the H7 coverage gap (2026-10-19)

**Verdict: `REPRODUCED` + `CAUSAL` — the H29 sweep's only coverage gap is closed.**

H7 was the one family H29 could not decide: its published row (OOS Sharpe 0.789, 1,005 trades,
profit factor 1.166, max DD −14.5%, 3/8 gates, verdict REJECTED) had no committed artifact —
no `h7` entry in `.experiments/experiments.jsonl` and no `exp_*` directory. H30 re-ran
`run_h7_intraday_tsmom_experiment.py` (unchanged) offline on the completed futures cache — all
five symbols (`ES=F, NQ=F, CL=F, GC=F, ZB=F`, `2015-01-01..2024-12-31`, `1d`) served from
`.cache/data`, no network — and committed the artifact as
`exp_2026-10-19T18-56-08-872500Z` under `.experiments/artifacts/`, recorded in
`.experiments/experiments.jsonl` through the tracker's normal record format. A second run
confirmed determinism: prices, equity curve, returns and trades are bit-identical across runs
(identical sha256 on all four parquets); `summary.json` differs only in the experiment id.

**Reconciliation with the published H7 row** (field by field; the published row is left
unchanged as the historical record, with discrepancies noted explicitly rather than changed):

| Field | Published | Re-run (`exp_2026-10-19T18-56-08-872500Z`) | Match? |
|---|---|---|---|
| OOS Sharpe | 0.789 | 0.7893 | ✓ (0.789 at 3 dp) |
| Trades (OOS) | 1,005 | 1,005 | ✓ exact |
| Profit factor | 1.166 | 1.1661 | ✓ (1.166 at 3 dp) |
| Max drawdown | −14.5% | −14.54% (OOS window) | ✓ (full-sample −21.4%) |
| Gates | 3/8 pass | 4 of 9 pass | ≈ (one gate off — see below) |
| Verdict | REJECTED | REJECT | ✓ |

Every comparable field reproduces the published row to reporting precision, so H30's verdict is
`REPRODUCED`: H7's published numbers now have committed provenance. Two disclosures:
(i) `compare_to_benchmark` raised in this session ("The truth value of a Series is ambiguous";
advisory and non-fatal — the run continues), so the re-run's benchmark is null and
`max_p_value`/`min_information_ratio` are False; the verdict is unaffected (REJECT either way).
(ii) The gate tally differs by one (published 3/8 vs 4/9 recomputed); the published gate
booleans are not re-derivable from any committed artifact, so the published row stands as the
historical record.

**H31 — the `compare_to_benchmark` defect is fixed, not merely logged (2026-10-20).** The
advisory raised in H30's re-run was a real bug, not a data artefact: `compare_to_benchmark`
assumed a 1-D benchmark and raised `ValueError: The truth value of a Series is ambiguous`
whenever the benchmark was a multi-symbol DataFrame (which is exactly what H7 passes —
`prices[FUTURES_UNIVERSE]`, a 5-column slice). The fix is in `src/qtr/validation/statistics.py`
(`compare_to_benchmark` now reduces a DataFrame benchmark to its row-mean series before
aligning, and likewise a 2-D ndarray), so the benchmark comparison is now computed rather
than skipped. H7's runner is **not** edited: the `try/except` around the call is preserved,
and the committed artifact `exp_2026-10-19T18-56-08-872500Z` is left untouched (its
`benchmark: null` is the historical record of the run as it was executed). A re-run of H7
(`exp_2026-10-20T01-51-28-367059Z`, since deleted from the tree — it was a verification
reproduction, not a committed artifact) now produces `benchmark = {alpha: NaN, ir: -38.34,
p_value: NaN}` with `prices`/`equity_curve`/`returns`/`trades` **bit-identical** to the
committed artifact (identical sha256 on all four parquets) and `summary.json` differing only in
the experiment id and the two gate booleans that the benchmark feeds
(`max_p_value: False`, `min_information_ratio: "False"` instead of `false`); the OOS Sharpe
(0.7893261992589912), trade count (1,005), profit factor (1.16605221165269), max DD
(−14.54%) and verdict (REJECT) are unchanged. **The fix changes no published number**: the
benchmark is advisory in H7's gate set (`max_p_value`, `min_information_ratio`), both were
already False in the published row's 3/8 count, and the verdict is REJECT either way.
Two regression tests (`test_dataframe_benchmark_reduced_to_equal_weighted`,
`test_2d_ndarray_benchmark_reduced`) pin the new behaviour; the pre-existing
`compare_to_benchmark` tests (OLS beta, zero-variance benchmark, unit-interval p-value) are
unchanged in expectation and still pass.

**H32 — the H31 commit introduced a build-breaking defect and is fixed (2026-10-20).** The
H31 commit (`68ec93b`) replaced the `def compare_to_benchmark(...)` signature with a
`def deflated_sharpe_ratio(...)` block but left the original function's *body* in place
immediately after the new function's `return`, without a `def` header. The result was a
**`SyntaxError`-free but unimportable module**: the orphaned body is dead code (a docstring
followed by executable statements at module level that reference undefined names), and
`from qtr.validation.statistics import compare_to_benchmark` raised
`ImportError: cannot import name 'compare_to_benchmark'`. This broke collection of **every**
test that imports `qtr.validation` (18 test files, 713 tests) — the repo was green before the
commit and red after. The fix is a single 8-line insertion: a proper `def compare_to_benchmark(
...)` header is restored immediately before the orphaned body, so the function is again a
named, exported, callable symbol with the same signature and behaviour H31 established
(`np.ndarray | pd.Series` for both return series, DataFrame/2-D-ndarray reduction preserved).
`deflated_sharpe_ratio` is unchanged in position, signature and behaviour. The module imports
cleanly and the full suite is green again (713/713, `pytest -W error` clean, ruff check and
`ruff format --check` clean on `src tests run_*.py`). **Nothing published was touched**: no
runner, gate, threshold, verdict or certified number was modified; no artifact was regenerated;
the committed H7 artifact `exp_2026-10-19T18-56-08-872500Z` is untouched. The defect class is
pinned by the existing H31 `compare_to_benchmark` regression tests (they import the symbol and
exercise the DataFrame/ndarray reduction), which is exactly what caught the breakage.

**H33 — three benchmark gates were vacuous; they are repaired and the record is re-disclosed
(2026-10-20).** H31 fixed the *raising* defect in `compare_to_benchmark` but not its
**consumption contract**. An audit of all **17** call sites in the repository against the
library's actual return-key set found three defects, each of which made a published benchmark
gate evaluate a **constant** instead of a statistic:

| # | Site | Defect | Consequence |
|---|---|---|---|
| D1 | `run_futures_tsmom_experiment.py:522` (H4) | read `alpha_res.get("p_value", 1.0)`; the library returns `alpha_p_value` | `p` always 1.0 → the `p` gate always **False** |
| D2 | `run_h18_overnight_intraday_experiment.py:742` (H18) | (a) `oos_mask` passed as the **3rd positional argument** (`risk_free`); (b) read `.get("p_value", 1.0)` | `alpha_annualized` became an **array**; `benchmark_p` always 1.0 → the gate always **False** |
| D3 | `run_h7_intraday_tsmom_experiment.py:403` (H7) | (a) read `.get("alpha")`/`.get("p_value")`; (b) the benchmark was the **price level** `prices[FUTURES_UNIVERSE]` against a **return** series | `benchmark` = `{alpha: NaN, ir: −38.34, p_value: NaN}`; `max_p_value` compared `NaN < 0.05` → always **False**; the IR was a unit-mismatched number |

The other 14 call sites use the canonical keys and pass no third positional argument. The
published artifacts carry the fingerprints: H4's `alpha_vs_benchmark.p_value` is the literal
`1.0`, H18's `gate_metrics.benchmark_p.value` is the literal `1.0`, H7's `benchmark` is `null`.
Had the key names been right without the unit fix, H7 would have published an alpha p-value of
**0.0** — an apparently significant result computed from returns minus price levels; the NaN
default was the only thing that protected the record.

The repair (library + three runners + a 12-test contract) and the recomputed impact:

| Family | Published | Repaired | Gate effect | Verdict |
|---|---|---|---|---|
| H4 | p = 1.0 (default), IR 0.33150832181222434 | p = **0.4592003515637103**, IR 0.33150832181222434 (bit-identical) | `p` still False → 1/8 → 1/8 | REJECT |
| H7 | `null`; IR −38.34 on price levels | alpha 0.09987, IR **+0.30022**, p 0.34319 | `max_p_value` still False; `min_information_ratio` **False → True** → recomputed 5/9 (artifact 4/9, report row 3/8) | REJECT |
| H18 | `benchmark_p` = 1.0 (default), IR −0.5967666565674836 | p = **0.04098500443612743**, IR −0.5967666565674836 (bit-identical) | `benchmark_p` **False → True** → recomputed 3/9 (published 2/9) | REJECT |

The published information ratios are reproduced **bit-exactly**, which is the direct evidence
that the library change is a no-op on the healthy path. The invariant is now executable:
`tests/test_benchmark_gate_contract.py` statically checks every call site (≤ 2 positional
arguments; every key read off the result is a key the library returns) and the same suite run
against the pre-fix source fails 8 tests, naming exactly the three defect sites.

**Disclosure — the benchmark-significance gate is direction-blind.** The pre-registered gate is
`p < max_p_value` on a **two-sided** t-test of the excess returns, so it is satisfied by a
*significantly negative* alpha — by the strategy being significantly **worse** than the
benchmark. Three published families already carry such a PASS: **H19** (p = 0.00260, IR =
−0.8798), **H20** (p = 0.01595, IR = −0.7040) and **H23** (p = 0.000900, IR = −3.0739); H18's
repaired gate passes for the same reason (p = 0.041, IR = −0.5968). The families whose `p` gate
passes with a *positive* IR (H9 +1.03, H10 +0.92, H22 +1.35, H25 +1.35) are genuine. The gate
**definition** is pre-registered, so H33 does not change it — it is disclosed and named as the
next task.

**Nothing published was touched:** no published artifact, runner gate, threshold, verdict or
certified number was modified; no grid was re-run; the published H4/H7/H18 rows stand as the
historical record and the recomputed tallies above are a disclosure, not a rewrite.

**Timing audit (H29 detector re-run):** H7 was added to `FAMILIES` in
`run_h29_lookahead_sweep.py` (route `rebuild_pipeline`, `rebuild` = `h7`,
`collapse_freq` = `"ME"`, `grid` = `daily`, `target_artifact` = `"equity_curve"`), with a
`rebuild_h7` that rebuilds the collapse from the committed prices with the runner's own code
and the published configuration. The re-run sweep reports H7 **`CAUSAL`**: min hold lag **+1
bar**, **0** look-ahead bars, committed equity curve reproduced **bit-exactly** (max abs diff
`0.0`), **0 extra** change points, same/prev expansion 0.130 / 0.970 — the same result as the
other six monthly families (H1–H6, H8). All four detector self-checks pass and the sweep
verdict stays `LOOKAHEAD_FOUND`.

**Nothing published was touched.** No published artifact, runner, gate, threshold, verdict or
certified number was modified; no grid was re-run; the published H7 row is unchanged and H7 is
not re-labeled. The paid-data task stays downstream and is unjustified for every family in the
repo: H28 closed it for the intraday family, and H29/H30 show the daily families are causal
but all REJECT. Evidence: `HYPOTHESIS_SPEC.md` §H30 (pre-registration and measure log),
`run_h29_lookahead_sweep.py`,
`.experiments/artifacts/h29_lookahead_sweep/`,
`.experiments/artifacts/exp_2026-10-19T18-56-08-872500Z/`,
`tests/test_h29_lookahead_sweep.py` (36 tests, H7's coverage-gap test replaced by the
committed-artifact/causal test).

---

## H34 — the benchmark-significance gate is direction-aware (2026-10-20)

H33 left one defect class open: the benchmark gate was *evaluated* against a real statistic,
but its **definition** was direction-blind. The pre-registered gate is `p < max_p_value` on a
**two-sided** t-test of the excess returns, so it is satisfied by a significantly *negative*
alpha — by the strategy being significantly **worse** than the benchmark. H34 re-specified the
gate, implemented it once, and closed it in every runner.

**The re-specified gate** (`src/qtr/validation/statistics.py:benchmark_significance_gate`,
exported from `qtr.validation`):

```
p_gate = (two-sided p < max_p_value) AND (excess return > 0)
```

The pre-registration proposed "one-sided `P(alpha > 0) < max_p_value`, equivalently the
conjunction". **The two are not equivalent**: the one-sided rule at 5% is a two-sided 10% test
and therefore *loosens* the published gate, while the conjunction keeps the published 5%
two-sided level (it is the one-sided test at 2.5%). The conjunction is implemented because it
can only ever *remove* a pass, never manufacture one, and because it keeps every committed
artifact numerically reproducible (the published `benchmark_p_value` stays the two-sided
p-value; H10's certified `4.790305556723297e-10` is still what the runner publishes). The
direction criterion is the sign of the **excess return** (information ratio > 0) rather than the
CAPM intercept: the information ratio carries the sign of the t-statistic the p-value is
computed from, whereas the CAPM intercept can carry the opposite sign (committed H16: IR =
−0.3531, `alpha_annualized` = +0.0124) and is not recorded in the certified artifacts at all.
The full amendment — including the correction of the frozen pre-registration's own statements —
is in `HYPOTHESIS_SPEC.md` §H34.

**Scope.** The library helper plus the benchmark-significance gate site of all **17** runners
(H1–H13, H16–H20, H23; H21/H22/H25 share H10's `_full_gate_eval`, H12 re-gates H10's frozen
benchmark p-value). The published `benchmark_p_value` remains the two-sided p-value, so every
committed artifact stays reproducible from the code.

**Disclosure — the complete table.** Recomputed offline from the committed artifacts, for
*every* family that owns a benchmark-significance gate (the pre-registration's list omitted H1,
H2, H3, H5, H8 and H21):

| Family | Published artifact | p | IR | published `p`-gate | H34 gate |
|--------|--------------------|---|---|---------------------|----------|
| H1 | `exp_2026-10-14T08-26-18-385545Z` | 0.78174 | −0.1241 | False | False |
| H2 | `exp_2026-10-10T21-09-06-830199Z` | 0.57342 | −0.2523 | False | False |
| H3 | `exp_2026-10-10T21-28-20-920399Z` | 0.046364 | −0.8932 | False | False |
| H4 | `exp_2026-10-14T08-27-02-650342Z` | 1.0 (vacuous) | +0.3315 | False | False |
| H5 | `exp_2026-10-11T00-34-05-381535Z` | 0.37864 | +0.3943 | False | False |
| H6 | `exp_2026-10-11T08-02-22-999214Z` | 0.42178 | +0.3598 | False | False |
| H7 | `exp_2026-10-19T18-56-08-872500Z` | null | — | False | False |
| H8 | `exp_2026-10-11T15-21-31-333870Z` | 0.24133 | +0.5249 | False | False |
| H9 | `exp_2026-10-11T16-52-38-694559Z` | 6.3295e-12 | +1.0210 | True | True |
| H10 | `exp_2026-10-11T17-41-18-169363Z` | 4.7903e-10 | +0.9248 | True | **True (certified)** |
| H12 | frozen H10 p (Bonferroni) | 4.7903e-10 | +0.9248 | True | **True (certified)** |
| H16 | `exp_2026-10-13T21-11-45-843908Z` | 0.20836 | −0.4764 | False | False |
| H17 | `exp_2026-10-13T21-51-45-034237Z` | 0.53389 | −0.2396 | False | False |
| H18 | `exp_2026-10-13T22-14-50-729923Z` | 1.0 (vacuous) | −0.5968 | False | False |
| H19 | `exp_2026-10-13T22-40-41-870350Z` | 0.0026022 | −0.8798 | **True** | **False** |
| H20 | `exp_2026-10-13T23-06-33-191710Z` | 0.0159482 | −0.7040 | **True** | **False** |
| H21 | `exp_2026-10-13T23-27-52-101656Z` | 1.9148e-10 | +0.9459 | True | True |
| H22 | `exp_2026-10-14T18-52-08-943792Z` | 1.3341e-19 | +1.3467 | True | **True (certified)** |
| H23 | `exp_2026-10-14T18-13-09-457781Z` | 0.00089959 | −3.0739 | **True** | **False** |
| H25 | `exp_2026-10-14T20-08-34-613690Z` | 1.4029e-19 | +1.3459 | True | **True (certified)** |

**Four published artifacts carry a wrong-reason PASS** (small two-sided p-value, negative
information ratio): H3's earlier artifact `exp_2026-10-10T21-27-13-928282Z` (p = 0.046364, IR =
−0.8932 — H3's *published* row comes from the later artifact, which already records the gate as
False), H19, H20 and H23. Under the H34 gate their benchmark gate does not pass: their published
gate tallies (3/9, 2/9, 2/9) would read 2/9, 1/9 and 1/9 on a re-run. **No verdict changes**
(all three are REJECT on other gates) and no published row is modified. H18's H33-repaired gate
(p = 0.041, IR = −0.597) stays False under H34, so its repaired tally returns to the published
2/9.

**Certified-family survival: yes.** H10, H22 and H25 pass the direction-aware gate (positive
excess return, p ≪ 0.05), as do H9, H12 and H21. No certified family and no certified number
is affected by the re-specification.

**Executable invariant.** `tests/test_benchmark_gate_contract.py` now also pins the direction
requirement: a static check that **no** runner compares a p-value against `max_p_value`
directly (every benchmark significance gate must go through the helper), a static check that no
runner publishes the one-sided p-value (the committed artifacts must stay reproducible), a
behavioural truth table for the gate, and an artifact sweep that fails if any committed
artifact carries a benchmark p-pass that is **not** evidence for the hypothesis (wrong direction
or not significant). The same test module run against the pre-H34 source (`git stash -u`) fails
**7** tests, so the new tests really bind the change.

**Verification.** `python -m pytest -q` → **735 passed** (726 + 9 new; the suite has since grown
to 748 with the H34 tally-impact pin and the 12 H35 contract tests); `python -m pytest -W error
-q` → clean; `python -m pytest --cov=qtr --cov-report=term-missing` → `src/qtr` coverage
**100%** (1010 statements, 0 missed — the dead `deflated_sharpe_ratio` is deleted, so the H33
baseline of 94% no longer applies); `ruff check` / `ruff format --check` → clean on
`src tests run_*.py`.

**Nothing published was touched:** no published artifact, threshold, verdict, certified number
or published row was modified; no grid was re-run; the recomputed tallies above are a
disclosure, not a rewrite.

---

## H35 — the published gates must fail closed (2026-10-20)

H33 found three benchmark gates that evaluated a **constant** instead of a statistic, and
H34 closed the *direction* half of the same defect class. **H35 closes the remaining half:**
a gate that **is** a constant, or that compares a **placeholder** constant, can never fail,
so it contributes a **free PASS** to the published tally. Such a gate is not evidence for the
hypothesis — it is a gate that never tests anything.

H35 is an **offline static audit** of every gate site in the repository. **No grid was re-run,
no artifact was modified, and no threshold, verdict or certified number changed.**

### The audit

Every gate expression in every `run_*.py` is parsed and classified into *evaluating* (it
depends on a computed statistic), *constant* (the gate is a literal), *placeholder* (the gate
compares a name that is only ever assigned a constant) and *permissive default* (the
threshold is read with a fallback that makes the gate unconditional).

| # | Site | Class | Effect on the published record |
|---|------|-------|------------------------------|
| F1 | `run_h7_intraday_tsmom_experiment.py:466-467` | constant | `min_perturbed_sharpe_ratio` and `min_worst_regime_sharpe` are hard-coded `True` — H7 never computes either statistic. **Two of H7's nine gates can never fail.** |
| F2 | `run_h18_overnight_intraday_experiment.py:764` | placeholder | `perturbation_ratio = 1.0  # Placeholder`, so the `perturbation_ratio` gate (`>= 0.5`) can never fail. **One of H18's nine gates can never fail.** |
| F3 | `run_h18_overnight_intraday_experiment.py:768-807, 831-874` | drift risk | H18 is the only runner that spells its nine thresholds out instead of reading a shared `GATES` dict; a change to the shared set would silently not apply to H18. The values are currently **equal** to the shared PROMPT_V2 gate set. |
| F4 | `run_futures_tsmom_experiment.py:547`, `run_ddcv_experiment.py:457`, `run_h6_vix_ddcv_experiment.py:553` | permissive default | the IR threshold was read as `GATES.get("min_information_ratio", -1e18)`; with that sentinel the gate is unconditionally true whenever the key is absent. **Latent** — the key exists in all three runners, so no published number changes. |

**No certified family is affected.** The audit finds a non-evaluating gate in **H7 and H18
only**; the certified families (H9, H10, H11, H12, H21, H22, H25) and every other family
evaluate all of their gates.

### The disclosed non-evaluating gates

Recomputed **offline from the committed artifacts** (no grid re-run):

| Family | published tally | free PASSes | tally on the evaluable gates | verdict |
|--------|-----------------|-------------|------------------------------|---------|
| H7 | **4/9** (`exp_2026-10-19T18-56-08-872500Z`) | 2 (`min_perturbed_sharpe_ratio`, `min_worst_regime_sharpe`) | **2/7** | REJECT (unchanged) |
| H18 | **2/9** (`exp_2026-10-13T22-14-50-729923Z`) | 1 (`perturbation_ratio`) | **1/8** | REJECT (unchanged) |

Forcing the disclosed gates to False leaves both families short of an all-pass, so **no
published verdict rests on a gate that never tests anything**. The published artifacts are
immutable and are not rewritten; the table above is a disclosure.

### The fix

Only **F4** changes in the runners, and the change is behaviour-preserving: the IR threshold
is read by direct subscript (`GATES["min_information_ratio"]`) instead of through a permissive
default, so a missing threshold now fails loudly instead of silently making the gate
unconditionally true. The key exists in all three runners and its value (`0.0`) is unchanged,
so **no published number, tally, threshold or verdict changes**.

F1, F2 and F3 are **disclosed and pinned, not silently repaired**: implementing the missing
perturbation / worst-regime statistics would require re-running the H7 and H18 grids, which
the constraints forbid, and it would change published tallies.

### The executable invariant

`tests/test_gate_vacuity_contract.py` (11 tests) pins the class: no runner may read a gate
threshold through `GATES.get(key, default)`; every `GATES["key"]` a runner reads must exist in
that runner's `GATES` dict (resolved through the `from X import GATES` chain, so the derived
runners are covered too); the set of gates that are a constant or that compare a placeholder
is **pinned to the disclosed set**, so a new always-true gate fails the suite; forcing the
disclosed gates to False changes no published verdict (recomputed offline from the committed
artifacts); H18's hard-coded thresholds are pinned **equal** to the shared gate set; and the
published H18 artifact is pinned to the one its Measure Log names.

### The `alpha_p_value_one_sided` item (closed)

H34 left one small item open: the library returns `alpha_p_value_one_sided`, an
**informational** one-sided view of the benchmark comparison that no runner reads. It is
**kept**, but `compare_to_benchmark`'s docstring now states explicitly that it is *not* the
gate's statistic — a one-sided test at 5% is a two-sided test at 10%, so it is strictly
*looser* than the published gate and would admit passes the gate rejects. A new test in
`tests/test_benchmark_gate_contract.py` pins that non-equivalence on a sample whose two-sided
p-value is 0.0609 (the gate rejects it) while its one-sided p-value is 0.0304 (the one-sided
rule would accept it).

### A correction to the H34 disclosure tables (citation only)

The H34 tables above and in `HYPOTHESIS_SPEC.md` §H34 cited H18's artifact as
`exp_2026-10-13T22-13-37-475937Z`. H18's **published** row is
`exp_2026-10-13T22-14-50-729923Z` — the experiment named in H18's Measure Log and in the
H33 evidence section, and the only one whose gate tally is the published 2/9. The two earlier
siblings record a 3/9 tally: their `max_drawdown` gate still read `True` although the OOS
drawdown is 22.2% against a 15% limit (the drawdown gate was corrected before the published
run). The H34 rows' **numbers** (p = 1.0 vacuous, IR = −0.5968, p-gate `False`) are
identical in all three artifacts, so only the **pointer** is corrected. No published number
changes.

### Verification

- `python -m pytest -q -W error` → **748 passed** (736 + 12 new).
- `python -m pytest --cov=qtr --cov-report=term-missing` → `src/qtr` coverage **100%**
  (1010 statements, 0 missed).
- **Negative control:** the same test module run against the pre-H35 runner sources fails
  **1** test and names the three permissive-default sites, so the contract really binds the
  change.
- **Nothing published was touched:** no published artifact, threshold, verdict, certified
  number or published row was modified; no grid was re-run; the recomputed tallies above are
  a disclosure, not a rewrite.

---

## H36 — the shared infrastructure must be point-in-time (2026-10-20)

H35 closed the last open **gate-defect** class. H36 closes a different class, in a different
layer: **the shared research infrastructure had no generic look-ahead coverage at all.**

### The gap

`qtr.strategies` (the signal library) and `qtr.backtest` (the vectorized engine) are the code
path behind almost every runner in this repository — `run_experiment.py`, `run_baseline.py`,
`run_param_sweep.py`, `run_alternatives.py`, `run_cs_momentum_experiment.py`,
`run_ts_momentum_experiment.py`, `run_ddcv_experiment.py`, `run_h6_vix_ddcv_experiment.py`,
`run_futures_tsmom_experiment.py`, `run_h7/h9/h10/h18/h21` and more. A look-ahead in either
module would silently inflate every result that uses it, and it would do so *in the direction
of a pass*.

The causality coverage that existed before H36 was:

| Existing coverage | Scope |
|---|---|
| `tests/test_backtest_engine.py::TestLookAheadSafety` | one narrow property (a position established on day 0 earns the day-1 return) |
| `tests/test_h23_crypto_futures_tsmom.py::TestCausality` | H23's own per-contract hourly targets |
| `tests/test_h28_causal_recertification.py` | H28's causal collapse |

**Nothing pinned the shared library itself.** A look-ahead introduced in `baselines.py` or in
`engine.py` would have reached every runner with no test failing — the same blind spot H33–H35
found on the gate side, one layer down.

### The contract and the probe

`tests/test_causality_invariant.py` (30 tests + 1 skip) pins the standard point-in-time
property:

> **No output observed at or before bar `t` may depend on any price strictly after bar `t`.**

It is checked by *future perturbation*: the prices after a cut are replaced by a different
(seeded, deterministic) path, and everything at or before the cut must come out
bit-identical. A perturbation at cut `c` can only expose a leak that reads *past* bar `c`, so
the probe runs at **every bar** of a reduced sample (dense sweep) *and* at nine cut points on
the full sample with the lookbacks the runners actually use (sparse sweep). The first
perturbed bar is halved, so a one-bar-ahead return always changes sign and a sign-based leak
cannot hide behind a return that happened to keep its sign.

| Surface | Coverage |
|---|---|
| `qtr.strategies.STRATEGY_REGISTRY` (8 strategies) | dense + sparse perturbation sweep |
| `qtr.backtest.engine.run_backtest` | returns, positions, equity curve and trade log at bars ≤ cut, bit-identical |
| rebalance cost timing | a trade's cost is charged in the bar in which the new weight is first held (the engine applies positions with a one-bar delay, `signals.shift(1) * price_returns`) |
| `src/qtr` (static) | no negative `shift(...)` and no backward `pct_change(...)`/`diff(...)` period — the two explicit look-ahead operators a per-bar perturbation alone would not catch |

### The probe is shown to bind

- **Negative control (in-module):** a deliberately leaky signal (`pct_change().shift(-1)`) must
  be *detected* by the probe; without this, the passing probes would prove nothing.
- **Non-vacuity:** every reactive strategy must actually *change* after the cut, so a strategy
  that returned constant zeros could not pass trivially. (`buy_and_hold` is a constant
  position and is skipped for that check only.)
- **Coverage pin:** the probes are tied to `STRATEGY_REGISTRY`; registering a new strategy
  fails the suite until it is probed.
- **Injected negative controls (in the library, then reverted):**
  `momentum_signals` with `.shift(-skip)` → **3 tests fail**; `carry_signals` with
  `pct_change(-lookback)` → **4 tests fail**; a *non-leak* control (`vol_scaled_tsmom_signals`
  with the `skip` removed, which still only reads price[t]) → **all 30 tests still pass**, so
  the invariant is not over-strict. `git diff` on `src/qtr/strategies/baselines.py` is empty
  after the experiment.

### The test suite is now runnable from a bare clone

`pyproject.toml` carries `pythonpath = ["src"]` under `[tool.pytest.ini_options]`. The package
uses a `src/` layout and is not required to be pip-installed: before H36, `python -m pytest`
failed at collection with `ModuleNotFoundError: No module named 'qtr'` wherever the package
had not been installed, so the test count quoted throughout this record was not reproducible
from a fresh checkout.

### Verification

- Baseline before this session: `PYTHONPATH=src python -m pytest -q -W error` → **750 passed**.
- After: `python -m pytest -q -W error` (no `PYTHONPATH`, no install) → **780 passed, 1
  skipped** in 167 s.
- `python -m pytest --cov=qtr --cov-report=term-missing` → `src/qtr` coverage **100%** (1011
  statements, 0 missed).
- `ruff check src tests run_*.py` → *All checks passed!*; `ruff format --check src tests
  run_*.py` → *81 files already formatted*.

**Nothing published was touched:** no published artifact, threshold, verdict, certified number
or published row was modified; no grid was re-run; no hypothesis was added. The two
open items recorded in `NEXT_TASK.md` (the engine's `metrics["total_return"]` excluding the
first bar, and `fetch_sp500_constituents` ignoring its `date` argument) are **disclosures**,
not rewrites, because the first is in published artifacts and the second has no published
artifact.

---

## H37 — the runners' inline signal code must be point-in-time (2026-10-20)

H36 closed the point-in-time gap in the *shared* infrastructure. H37 closes the same gap one
layer out: in the **runners' own signal code**, which had no generic coverage at all.

**Verdict: `LOOKAHEAD_CONFIRMED` (the published intraday defect, now reproduced from the
runners' own code) + `LOOKAHEAD_FOUND` (one new instance, in H18).**

### The gap

Every runner builds its position series *inline*, in its own `run_*.py`. Before H37 the only
causality suites were `tests/test_h23_crypto_futures_tsmom.py::TestCausality` (H23's own
per-contract hourly targets) and `tests/test_h28_causal_recertification.py` (H28's causal
collapse). The eleven runners named by the H36 handoff — `run_h10/h12/h16/h18/h19/h20/h21/
h22/h25/h27/h29` — plus their two dependencies (`run_h9`, whose primitives they import, and
`run_h23`, the crypto copy of the H10 pipeline) constructed positions with **no generic
look-ahead coverage**.

### The contract and the probe

`tests/test_runner_causality_inventory.py` (179 tests) extends H36's *future-perturbation*
probe to the runners. The contract is the same, and it is stated on the runner's own
information timing:

> **A decision that is executed at bar `t` may not depend on any observation strictly after
> the moment it is executed.**

Two scopes, because the runners do not all execute their decision at the same moment:

| Scope | Decision executed | May read | Used by |
|---|---|---|---|
| `after` | at the close of bar `t`, traded at bar `t+1` (the engine's one-bar delay) | data up to and including bar `t` | every runner that hands a position series to `run_backtest` |
| `close` | at the **open** of bar `t` | the open of bar `t` and everything before | H18, which trades the leg that the same day's open already realised |

Under either scope the probe replaces the market data after a cut with a different (seeded,
deterministic) path and requires everything at or before the cut to come out bit-identical.
The dense sweep makes every bar of a reduced sample a cut point; the sparse sweep uses the
lookbacks the runners actually use. The perturbation is per-(bar, column) — a factor shared by
`open` and `close` would leave `close - open` (and therefore a sign rule) unchanged — and the
first perturbed bar is halved, so a one-bar-ahead return always changes sign.

### The inventory (137 functions, 13 runners, pinned)

Every module-level function of every in-scope runner is classified, and a new function in an
in-scope runner fails the suite until it is classified:

| Coverage | Count | What it means |
|---|---|---|
| `probed` | 36 | a future-perturbation probe exists and must find no violation |
| `lookahead` | 7 | a **known** look-ahead: the probe must *detect* it, or the call graph that inherits it is pinned |
| `static` | 94 | no dynamic probe applies: a static look-ahead-operator check plus a written argument |

53 probe cases (covering the 36 probed functions, including every grid cell of H19's and
H20's signal constructors) and 2 day-aligned probes for the daily collapses.

The static sweep is exhaustive by construction over the runners' source: a negative
`shift(...)`, a backward `pct_change`/`diff` period, a centred window, a backward fill and a
same-period `resample` collapse are all located by AST, and the **site list is pinned** — a
new look-ahead operator anywhere in the runners fails the suite even if it sits in a function
the inventory does not probe.

### Finding 1 — the published intraday look-ahead, reproduced from the runners' own code

The probe **detects** the H27/H28/H29 defect in the runners' own code, not in a copy of it:

| Constructor | Detection | Verdict |
|---|---|---|
| `run_h10_…:build_hourly_target` | 76/79 dense cuts, 9/9 sparse cuts | the daily collapse's value for day `D` is expanded over day `D` itself |
| `run_h23_…:build_hourly_target` | 76/79 dense cuts, 9/9 sparse cuts | the crypto copy of the same collapse |
| `run_h12_…:_rebuild_grid_oos` | pinned call graph | the OOS matrix is the published (look-ahead) return stream |
| `run_h21/22/25_…:_apply_exits_and_aggregate` | pinned call graph | the per-contract targets are built with `build_hourly_target` |

The three missing dense cuts are the last bar of each day, where the collapse's decision bar
*is* the cut bar — the leak is invisible exactly there, which is what the contract predicts.

The two daily collapses are pinned on their own grid: the published collapse reads the signal
at the **last bar of day `D`** and H27's causal collapse reads the signal at the **last bar of
day `D-1`**; neither reads a later bar.

### Finding 2 (new) — H18's `vix_regime` predictor omits the pre-registered one-day lag

H18's pre-registration (`HYPOTHESIS_SPEC.md` §H18) requires *"Signal (causal, 1-day lag)"*
and *"Position = long the favored component (overnight or intraday leg) at the prior day's
close"*. Two of the three pre-registered predictors implement that lag explicitly
(`lagged_1d_overnight_sign`, `prior_5d_return_sign`); the third does not:

```python
# run_h18_overnight_intraday_experiment.py:100
elif predictor == "vix_regime":
    fav_overnight = vix_close > 30          # no shift: reads vix_close[t]
```

and the runner applies the signal to **day `t`'s own legs**, with no one-bar delay:

```python
# run_h18_overnight_intraday_experiment.py:454-459
overnight_ret = open_ / close.shift(1) - 1   # realised at open_t
intraday_ret = close / open_ - 1             # realised at close_t
position_overnight = (signal == 1).astype(float)
strategy_ret = position_overnight * overnight_ret + position_intraday * intraday_ret
```

The VIX close of day `t` is known only at the close of day `t`, but the signal at day `t`
decides the overnight leg of day `t`, which was realised at the **open** of day `t`. That is a
one-day look-ahead in **2 of the 6 pre-registered grid cells** (`vix_regime × {next_overnight,
next_intraday}`).

The probe detects it: under the `close` scope the `vix_regime` predictor changes the signal
at **79/79** dense cut points and **9/9** sparse cut points, while the two lagged predictors
change at **none**.

**The disclosure is bounded, and the published record is untouched:**

| Item | Value | Consequence |
|---|---|---|
| Published selection (by Val Sharpe) | `prior_5d_return_sign_next_intraday` (Val Sharpe **0.9797**) | the leaky predictor did **not** win the selection |
| The leaky cells' Val Sharpe | `vix_regime_next_overnight` **0.4710**, `vix_regime_next_intraday` **0.5801** | both below the selection |
| Published OOS Sharpe of the selected row | 0.4424 (unchanged) | the published number is not affected |
| Published verdict | **REJECT** (2/9 published, 1/8 evaluable) | a look-ahead can only inflate; the verdict cannot improve |

A test pins all of it against the committed artifact
(`exp_2026-10-13T22-14-50-729923Z`): if the published selection ever changed to a
`vix_regime` cell, the pin would fail and the disclosure would have to be revisited.

### What the probe cannot see, and why

`_apply_exits_and_aggregate` (H21/H22/H25) is **not** probed, and the reason is written down
rather than glossed over: its output is a *sticky* state machine — the exit holds the size it
entered with, so a change in the target's magnitude does not change the position series, and
the only sensitivity left is the sign test. A positional probe of the position series
therefore cannot see the look-ahead that its *input* target carries; the pin for it is the
**call graph** (an executable check that the function still calls `build_hourly_target`),
exactly as for H12's `_rebuild_grid_oos`.

### Verification

- Baseline before this session: `python -m pytest -q` → **780 passed, 1 skipped**.
- After: `python -m pytest -q` → **959 passed, 1 skipped** in 182 s (780 + the 179 new tests;
  the skip is the pre-existing `buy_and_hold` skip in H36's module).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → *82 files already formatted*.
- `src/qtr` was not touched, so its coverage is unchanged at **100%**.
- **Negative controls:** two injected leaks (a `shift(-1)` signal and a `pct_change(-1)`
  signal) must be *detected* by the probe; both are. Every probed constructor must also
  *react* to the perturbation, so an inert (all-zero) output cannot pass trivially.
- **The probe binds the change, and is not over-strict** (injected into the runners, then
  reverted; `git diff` on both files is empty):
  - A) `run_h19_…:build_targets` — `unanticipated = vol - vol_mean` → `(vol -
    vol_mean).shift(-1)` → **8 tests fail** (the dense and sparse sweeps of the four H19
    grid cells).
  - B) *control, not a leak*: `run_h16_…:factor_momentum` — `prices.shift(skip)` →
    `prices` (the momentum now reads `price[t]`, which the engine's one-bar delay permits)
    → **all 14 H16 tests still pass**, so the invariant is not over-strict.

**Nothing published was touched:** no published artifact, threshold, verdict, certified number
or published row was modified; no grid was re-run; no hypothesis was added. The engine's
`metrics["total_return"]` excluding the first bar's return while `annualized_return` counts it
(~a few bps; the values live in published artifacts) remains a **disclosure, not a rewrite**.
The `fetch_sp500_constituents(date=...)` footgun from the earlier record is already closed in
code: a historical `date` raises `ValueError` instead of silently returning the current list,
and the branch is now covered by a test. `src/qtr` coverage is **100%** (1014/1014 statements).

## Runner-causality coverage extended to every run_*.py (2026-10-20)

This session closed the coverage gap H37 carried forward: the point-in-time invariant of
`tests/test_runner_causality_inventory.py` now extends to every `run_*.py` in the repository
(32 files). The nine runners H37 left uncovered -- `run_experiment.py`, `run_baseline.py`,
`run_param_sweep.py`, `run_alternatives.py`, `run_h13_oos_deflation_pf_audit.py`,
`run_h14_pf_margin_selection_audit.py`, `run_h25_pf_robustness.py`,
`run_h26_sharpe_scale_audit.py`, `run_h28_causal_recertification.py` -- are all in scope;
every one of their 48 module-level functions is classified `static` with a written argument
(none builds a position series inline; each composes imported frozen pipelines or audits
committed artifacts), and `run_h26`'s single `resample("1D")` collapse site is pinned in
`RESAMPLE_SITES`. `KNOWN_LOOKAHEAD_CASES` ({h10.build_hourly_target,
h18.signal.vix_regime, h23.build_hourly_target}) and `INHERITED_LOOKAHEAD` are unchanged.

**Predictor-timing audit.** Every predictor of the H29-CAUSAL families is probed clean, and
no same-bar-close predictor (the H37/P3 class: a predictor that reads its own bar's close
while trading that bar's return) was found in any remaining runner -- H37's P3 disclosure
(H18's `vix_regime`) remains the only instance, and it stays bounded against the committed
artifact (`exp_2026-10-13T22-14-50-729923Z`: the published selection was the causal
`prior_5d_return_sign_next_intraday`, so the published row, numbers and REJECT verdict stand).

**Verification.** `python -m pytest -q -W error` → **1102 passed, 1 skipped**;
`python -m ruff check src tests run_*.py` → *All checks passed!*; `src/qtr` coverage
**100%**. The engine's annualized return was also hardened (`src/qtr/backtest/engine.py:317`):
it no longer raises `RuntimeWarning: invalid value encountered in scalar power` when the
dense sweep drives equity to zero or below; it returns -1.0 instead, and the branch is
exercised by the existing dense-sweep tests. No published artifact, gate threshold, verdict,
certified number or published row was modified; no grid was re-run; no hypothesis was added.

---

## H38 — the engine's `total_return` measured the wrong horizon (2026-10-20)

**Verdict: a real defect, found and fixed in the library. No published number, gate, verdict or
certified number changed.**

### The gap

The one open item H37 carried forward was the engine's `metrics["total_return"]`, described as
"inconsistent with its own equity curve (it excludes the first bar's return while
`annualized_return` counts it) — ~a few bps", and left as a **disclosure** because `metrics`
values live in published artifacts.

It was carried forward as too small to touch. The audit below shows it was not a cosmetic
few-bps issue: the metric was measuring **the wrong quantity**, and the error was **invisible in
the published record**.

### The defect

`src/qtr/backtest/engine.py:_calculate_metrics` measured the total return over the *observed*
part of the equity curve:

```python
total_return = equity.iloc[-1] / equity.iloc[0] - 1        # pre-fix
```

The equity curve is `cumprod(1 + net_returns) * initial_capital`, so `equity.iloc[0]` is already
**one bar into the sample**. The first bar is the only bar on which the engine charges the
*initial entry cost* (`position_changes = signals.diff().fillna(signals.iloc[0])` — the position
goes from flat to invested on bar 0). The pre-fix range therefore covered `n - 1` compounding
periods, while `annualized_return` divided by `n_periods = len(returns)`: **the two metrics of
one equity curve described two different horizons.**

The same package computes the same quantity the other way round:
`qtr.validation.statistics.validate_strategy` uses `(1 + returns).prod() - 1`, i.e. the full
`n`-bar product, which equals `equity.iloc[-1] / initial_capital - 1`. `run_experiment.py` writes
**both** into the same artifact (`strategy_metrics` = the engine's, `validation` =
`validate_strategy`'s), so the published artifacts report **two different `total_return` values
for one and the same run**.

### The evidence (all of it inside the committed artifacts)

| Artifact | block | published `total_return` | from the initial capital | gap |
|---|---|---|---|---|
| `exp_2026-10-10T17-05-58-697503Z` (buy & hold, SPY) | `strategy_metrics` | 1.863359741396068 | 1.7456586208201519 | **11.77 pp** |
| " | `validation` | 1.7456586208201519 | 1.7456586208201519 | 0 |
| `exp_2026-10-14T08-26-02-537359Z` (the same run, re-executed) | `strategy_metrics` | 1.8633597413960814 | 1.862786791365549 | 5.73 bps |
| " | `validation` | 1.862786791365549 | 1.862786791365549 | 0 |
| `exp_2026-10-10T17-02-22-080026Z` (MA crossover) | `strategy_metrics` | −0.9998648207588501 | −0.9998648207588501 | 0 |
| " | `benchmark_metrics` | 1.1226267977582687 | 1.0778936803171542 | **4.47 pp** |

The first two rows are **one artifact reporting two values for one run**. The benchmark row has
no `validation` counterpart, so its 4.47-pp error was **invisible** in the artifact. The three
MA-crossover artifacts show a zero gap because their strategy starts flat (the MA warm-up leaves
bar 0 empty), which is exactly why the defect never showed up in the headline runs.

**The metric was blind to the dominant term of the cost model.** The buy-and-hold run was
re-executed on 2026-10-14, after the cost-model fix cut the per-trade cost from **4.11% to
0.02%** of capital — a 205× change in the strategy's entire cost:

| | per-trade cost | published `total_return` | published `annualized_return` | from the initial capital |
|---|---|---|---|---|
| `exp_2026-10-10T17-05-58-697503Z` | 0.041105949376283715 | 1.863359741396068 | 0.11116466309386919 | 1.7456586208201519 |
| `exp_2026-10-14T08-26-02-537359Z` | 0.00020009711746988646 | 1.8633597413960814 | 0.11116466309386963 | 1.862786791365549 |

The published `total_return` and `annualized_return` are **identical to 13 significant digits**
across that 205× cost change: the whole difference lands on the first bar, which the metric
dropped. The cost *was* visible elsewhere (Sharpe 0.6596 → 0.6846, PF 1.1347 → 1.1401), so the
return metrics were the only place it was invisible.

### The fix

`src/qtr/backtest/engine.py` now measures the total return from the initial capital:

```python
total_return = equity.iloc[-1] / self.config.initial_capital - 1.0
```

This is the quantity `validate_strategy` computes, so the two metric functions of the package can
no longer disagree, and `annualized_return` is now the `n`-period annualization of an `n`-period
total return (the pair is invertible).

**Nothing published was rewritten.** The corrected value is *already* in every affected artifact,
under its `validation` block; the `strategy_metrics` / `benchmark_metrics` blocks keep their
pre-fix values — they are the historical record of the runs as executed — and are now pinned by
tests so that a silent change to either convention is caught. No gate, threshold, verdict or
certified number depends on the metric: a new test asserts that **no runner reads
`metrics["total_return"]`**, so no selection, row or verdict can move.

### What remains a disclosure

`run_h18_overnight_intraday_experiment.py:526` (full period) and `:637` (OOS window) carry their
own copy of the pre-fix convention for the runner-local `total_return` the runner publishes. The
H18 artifacts are frozen, so the copy stays; the effect is bounded and pinned:

- the published full-period `all_combo_results[*].total_return` of the selected row is **6.34 bps
  above** the from-the-initial-capital value (2.169671442460739 vs 2.169037508172247); the
  difference is exactly the first bar's 2 bps entry cost;
- H18's **OOS** `total_return` is *not* affected: it is computed on the `oos_equity` window with
  the same convention, so it equals the compounded OOS return series
  (0.7162049014199334 vs `(1 + oos_returns).prod() - 1` = 0.7162049014199359) and reproduces
  the committed equity curve exactly (OOS Sharpe 0.4424368131799029, max DD −0.22230414028780243,
  PF 1.0890543891778597 — all bit-identical to the published block);
- H18's nine gates do not use `total_return` (Sharpe, trades, PF, DD, WF stability, worst-regime
  Sharpe, benchmark p, IR, perturbation ratio), so the disclosure cannot move a verdict.

### Verification

- Baseline before this session: `python -m pytest -q -W error` → **1102 passed, 1 skipped**.
- After: `python -m pytest -q -W error` → **1115 passed, 1 skipped** in 210 s (1102 + the 13 new
  H38 tests; the skip is the pre-existing `buy_and_hold` skip in H36's module).
- `python -m ruff check src tests run_*.py` → *All checks passed!*;
  `python -m ruff format --check src tests run_*.py` → the only deviations are on pre-existing
  lines of `tests/test_runner_causality_inventory.py` that this session did not touch (ruff
  0.17.1 style drift); every line this session added is format-clean.
- `src/qtr` coverage **100%** (the change is one expression, no new branch).
- **Negative control:** re-injecting the pre-fix formula into the engine makes **4 of the 13 new
  tests fail** (the metric contract, the `validate_strategy` agreement, the pre-fix-detection
  control and the horizon check), and the file is restored afterwards (`git diff` on the engine
  shows only the intended change).
- **The published numbers were not recomputed by re-running anything:** every figure in the
  tables above is read out of the committed artifacts and the committed equity curves.

**Nothing published was touched:** no published artifact, gate threshold, verdict, certified number
or published row was modified; no grid was re-run; no hypothesis was added.

---

## H39 — the package's two Sharpe implementations disagreed (2026-10-21)

**Verdict: a real defect, found and fixed in the library. No published number, gate, verdict or
certified number changed; one published disclosure (H9's Sharpe convention) is recorded and
pinned.**

### The gap

H38 closed the last open *metric* defect (the engine's `total_return` horizon) and left exactly
one task: *"make the package's two Sharpe implementations agree, and extend the H38 cross-module
agreement contract to every metric the package computes twice"* (`NEXT_TASK.md`).

### The defect

`src/qtr/backtest/engine.py:_calculate_metrics` divided the mean excess return by the **sample**
standard deviation (pandas `Series.std()`, ddof=1), while
`qtr.validation.statistics.sharpe_ratio` divides by the **population** standard deviation
(`numpy.ndarray.std()`, ddof=0). The two differ by exactly `sqrt(n / (n - 1))`, so the same run
produced two Sharpes — one per implementation.

This is the same class of defect as H38's `total_return`: **one package, one run, two numbers**,
and the two numbers were written into the *same* artifact.

### The evidence (all of it inside the committed artifacts)

The five artifacts that carry engine-produced metrics publish the engine's Sharpe under
`strategy_metrics` and `validate_strategy`'s under `validation` (n = 2,515 bars in all five):

| Artifact | `strategy_metrics.sharpe` | `validation.sharpe` | ratio | `sqrt((n-1)/n)` |
|---|---|---|---|---|
| `exp_2026-10-10T17-02-22-080026Z` (MA crossover) | −1.2468485134505827 | −1.2470964698045208 | 0.9998011730768694 | 0.9998011730768697 |
| `exp_2026-10-10T17-03-39-610858Z` | −1.040271567653521 | −1.0404784427808826 | 0.9998011730768697 | " |
| `exp_2026-10-10T17-04-21-400695Z` | −2.592235014999521 | −2.5927505236085744 | 0.9998011730768697 | " |
| `exp_2026-10-10T17-05-58-697503Z` (buy & hold) | 0.6596071358231974 | 0.6597383095613587 | 0.9998011730768697 | " |
| `exp_2026-10-14T08-26-02-537359Z` (buy & hold, re-run) | 0.6845946588741453 | 0.6847308017926383 | 0.9998011730768697 | " |

The ratio is the *same* number in all five, and it is exactly `sqrt((n-1)/n)`. Each artifact
therefore published **two different Sharpes for one run** — the same defect H38 found for
`total_return`, and invisible in the same way (the two blocks sit next to each other and are
read as if they were the same measurement).

**The reconstruction confirms the direction.** Each published Sharpe is reproducible from the
artifact's *own* equity curve under exactly one convention, and only that one:

| Artifact | published `strategy_metrics.sharpe` | reproduced with **sample** std (ddof=1) | reproduced with **population** std (ddof=0) |
|---|---|---|---|
| `exp_2026-10-10T17-02-22-080026Z` | −1.2468485134505827 | −1.2468485134505833 ✔ | −1.2470964698045213 ✘ |
| `exp_2026-10-10T17-05-58-697503Z` | 0.6596071358231974 | 0.6596071358231966 ✔ | 0.6597383095613579 ✘ |
| `exp_2026-10-14T08-26-02-537359Z` | 0.6845946588741453 | 0.6845946588741482 ✔ | 0.6847308017926412 ✘ |

The `validation` block reproduces under the population convention in all five. The
`benchmark_metrics` block of the MA-crossover artifacts carries the **pre-fix** convention too
(0.49249808266848055 published, sample-std reproduction exact) and, like H38's benchmark row, has
no `validation` counterpart to expose it.

### The decision and its direction (pinned to the committed record)

The record's convention is **ddof=0**, and this is not an assertion made here — **H26's own
Sharpe-scale audit already classified it**, per family, in the committed artifact
`.experiments/artifacts/h26_sharpe_scale/summary.json`:

| family | published OOS Sharpe | `published_convention` | `abs_diff_ddof0` | `abs_diff_ddof1` |
|---|---|---|---|---|
| H10 | 1.2757590680990518 | `population_ddof0` | **0.0** | 1.239e-04 |
| H21 | 0.8393598580201286 | `population_ddof0` | **0.0** | 8.153e-05 |
| H22 | 1.3724750832147166 | `population_ddof0` | **0.0** | 1.333e-04 |
| H23 | −7.187089456116173 | `population_ddof0` | **0.0** | 2.687e-02 |
| H25 | 1.3236288879255962 | `population_ddof0` | **0.0** | 1.286e-04 |

Every audited family's published Sharpe is the **population** convention, bit-exactly. The engine
was the only implementation in the package that was not. The certified numbers are therefore
**already** ddof=0, and the only admissible direction is **engine → ddof=0**: the change moves
*reported* Sharpes by `sqrt(n / (n - 1)) - 1 = +0.0199%` and moves **no** certified number, gate
threshold or verdict.

`src/qtr/backtest/engine.py` now divides by `returns.std(ddof=0)`, matching
`qtr.validation.statistics.sharpe_ratio` and therefore `validate_strategy`. The **volatility**
convention is deliberately *not* changed: `annualized_volatility` keeps the sample std (ddof=1),
because that is the convention `validate_strategy` uses for it and the one every published
artifact records (`annualized_volatility` agrees with the `validation` block to the last digit in
all five artifacts).

### Why no published verdict can move

- **No gate is evaluated on the engine's Sharpe.** An AST sweep of all 32 `run_*.py` finds no
  comparison of an engine Sharpe against a finite numeric threshold; the only comparisons of
  engine Sharpes are `best_sharpe > bh_result.metrics['sharpe']` in `run_alternatives.py` and
  `run_param_sweep.py` — **engine against engine**.
- **That comparison cannot flip.** The change is a *uniform rescaling*: the multiplier depends
  only on the number of bars, never on the returns, so two Sharpes computed on the same series
  are rescaled by the same factor and their order is preserved exactly. Both runners compute
  every side of the comparison from the same `prices` frame, so the bar counts are equal.
- **The certified families never read the engine's metric.** H10/H11/H12/H13/H14/H22/H25 compute
  their Sharpes with `qtr.validation.statistics.sharpe_ratio` (ddof=0).

### A second, independent disagreement: the degenerate-series guard

The engine's guard was `if returns.std(ddof=0) > 0`, while `sharpe_ratio` — whose docstring
documents exactly this trap — uses `if returns.std() <= 1e-15: return 0.0`. A **constant** return
series has a standard deviation of ~2.2e-19 from float noise, not exactly 0.0, so the engine's
exact-zero test let it through and divided by ~1e-19:

| input | engine (pre-fix) | `validate_strategy` |
|---|---|---|
| `pd.Series([0.001] * 10)` | **7.320824597683504e+16** | 0.0 |

A garbage Sharpe of 7.3e16, against 0.0 from the same package on the same series. The engine now
carries the same 1e-15 tolerance, so both implementations agree on the whole domain — including
the degenerate one. The fix is unreachable from the public `run_backtest` path (the engine always
charges an entry cost on bar 0, so a returned series is never perfectly constant), which is
precisely why it survived: it is only visible at the metric surface.

### The contract now pinned

`tests/test_engine_metric_agreement.py` (55 tests) is the executable cross-module contract:

- **exact agreement** between the engine and `validate_strategy` for all six shared metrics
  (`total_return`, `annualized_return`, `annualized_volatility`, `sharpe`, `max_drawdown`,
  `profit_factor`) across single- and multi-symbol portfolios, short portfolios, a degenerate
  flat series, a two-bar series and a total-loss bar (`gross == 0`), plus `num_trades` against
  the validation counter;
- **the engine-only metrics** (Sortino, Calmar, max-drawdown duration, average trade cost) pinned
  by their exact formula, and their **absence** from `validate_strategy` asserted, so a second
  implementation appearing later is a visible change;
- **the convention itself**: the population-std formula, the exact `sqrt(n / (n - 1))` relation to
  the sample-std formula, the uniform-rescaling (order-preserving) property, the degenerate-series
  guard, and the third Sharpe variant in the package (`annualized_sharpe`, the bar-frequency
  annualization) as a *documented* difference of exactly `sqrt(bars_per_year / 252)`;
- **the published-artifact audit**: both conventions, the ratio, the bar count (2,515), the
  reconstruction of each published Sharpe from the artifact's own equity curve, the benchmark
  block, the volatility convention, and the bounded effect (+0.0199%, < 0.1%);
- **the record**: H26's per-family convention classification (every audited family is
  `population_ddof0`, bit-exactly) and the H9 disclosure below;
- **negative controls**: the contract itself rejects the pre-fix Sharpe and the pre-fix
  `total_return`.

### The disclosure: H9 is the one published Sharpe on the sample convention

H26 **excluded** H9 from its audit, and the reason is the convention itself: H9's published OOS
Sharpe reproduces only under the **sample** (ddof=1) estimator (`abs_diff_ddof1 = 0.0`), because
that artifact predates the library's switch to numpy; the population convention gives
1.0564855126690582 against the published 1.0563828964274808 — a gap of **1.026e-04**. H9 is the
only family in the record published on the other convention.

**The gap cannot move H9's verdict.** H9's pre-registered Sharpe gate is 1.0 and its published
OOS Sharpe is 1.0564 — a margin of 5.6e-02, **55× the convention gap** — so both conventions
clear the gate. H9's published row is a REJECT on the profit factor
(`passes.pf = false`, PF 1.2522) in any case. The disclosure is recorded and pinned by
`tests/test_engine_metric_agreement.py::test_h9_is_the_one_published_sharpe_on_the_sample_convention`.

### Verification

- Baseline before this session: `python -m pytest -q -W error` → **1121 passed, 1 skipped**.
- After: `python -m pytest -q -W error` → **1170 passed, 1 skipped** in 268 s (1121 + the 49 new
  H39 tests; the skip is the pre-existing `buy_and_hold` skip inside H36's module).
- `python -m ruff check src tests run_*.py` → *All checks passed!*;
  `python -m ruff format --check src tests run_*.py` → the only deviation is on pre-existing
  lines of `tests/test_runner_causality_inventory.py` that this session did not touch (ruff
  0.17.1 style drift); every line this session added is format-clean.
- `src/qtr` coverage: the engine change is one condition plus comments — the `> 1e-15` branch is
  covered by the new degenerate-series tests and the `> 0` branch by every other metric test, so
  no new branch is introduced. *(The coverage tool is not installed in this environment, so the
  100% figure could not be re-measured here; the branch argument above replaces it.)*
- **Injected negative controls** (into the engine, then restored; `git diff` shows only the
  intended change): reverting the Sharpe to the sample std fails **15** of the 55 tests; reverting
  only the degenerate-series guard to an exact-zero test fails **2** of them.
- Every number in this section is read out of the **committed artifacts** (summary.json + equity
  parquet) or the **committed H26 audit**; nothing was recomputed by re-running a grid.

**Nothing published was touched:** no published artifact, gate threshold, verdict, certified number
or published row was modified; no grid was re-run; no hypothesis was added; `run_*.py` was not
touched.

---

## H40 — the runners' local metrics are classified and pinned (2026-10-21)

**Verdict: the metric-agreement contract is extended from `src/qtr` to the runners' own metric
implementations. No published number, gate, verdict or certified number changed; one test module
(33 tests) pins the contract.**

### The gap

H39 closed the disagreement *inside* `src/qtr`: the engine and `validate_strategy` now agree
exactly on all six shared metrics. But the repository still computes the same metrics a third
time, in the runners:

* six near-duplicate `_period_metrics(ret, n_trades)` helpers
  (H10, H16, H17, H19, H20, H23) re-implement the Sharpe, the profit factor and the max
  drawdown; their Sharpe (`sharpe_ratio(r.values)`, population ddof=0) and profit factor match
  the library exactly, while their max drawdown uses `cum / cum.cummax() - 1` against the
  library's `(equity - rolling_max) / rolling_max` — algebraically identical, differing by
  floating-point noise (≤ 1e-15 measured over 200 random equity curves);
* `run_ddcv_experiment.window_max_drawdown` uses the same cum/cummax variant;
* `run_h26_sharpe_scale_audit.py:303` computes a *daily* Sharpe with the sample std (pandas
  ddof=1) — the same convention split H39 closed in the engine;
* `run_cs_momentum_experiment.py:383` computes a local information ratio with numpy ddof=0,
  consistent with `compare_to_benchmark`.

### The contract now pinned

`tests/test_runner_metric_agreement.py` (33 tests):

* `TestRunnerMetricInventory` — every metric-computing function of every in-scope runner is
  classified `agrees`, `differs_bounded` or `differs_convention`; a new metric-named function of
  an in-scope runner is unclassified and fails the suite (the "new helper fails" pin, mirroring
  the causality inventory).
* `TestExactAgreement` — Sharpe and profit factor in each `_period_metrics` match
  `validate_strategy` exactly; `train_only_wf_sharpe` (H16) agrees exactly; the CS-momentum
  information ratio matches `compare_to_benchmark`'s `information_ratio` exactly.
* `TestBoundedDrawdownVariant` — the runners' max drawdown and `window_max_drawdown` are
  algebraically identical to the library's drawdown and differ by at most 1e-15.
* `TestH26DailySharpeConvention` — H26's daily Sharpe uses the sample std (ddof=1), a documented
  convention split; the difference is exactly `sqrt(n / (n - 1))`, bounded (+0.0199% at
  n = 2,515).
* `TestContractNegativeControl` — a helper returning the sample-std Sharpe or an inverted
  drawdown formula fails the contract, so it is not a tautology.

### Verification

- `python -m pytest -q -W error` → **1203 passed, 1 skipped** (1170 + the 33 new H40 tests;
  the skip is the pre-existing `buy_and_hold` skip in H36's module).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → the new file is format-clean; the only
  deviation is on pre-existing lines of `tests/test_runner_causality_inventory.py` (ruff 0.17.1
  style drift, not touched this session).
- `tests/test_engine_metric_agreement.py`, `tests/test_runner_causality_inventory.py` and
  `tests/test_causality_invariant.py` all pass alongside the new module.
- No `src/qtr` change, so coverage is unchanged (100%); H40 adds no branch.

**Nothing published was touched:** no published artifact, gate threshold, verdict, certified
number or published row was modified; no grid was re-run; no hypothesis was added; no
`run_*.py` was touched. The runner-local copies are classified and pinned, not rewritten (the
artifacts are frozen, so a rewritten helper would no longer reproduce them).

## H41 — the runners' inline metric sites are pinned (2026-10-21)

**Verdict: every metric the runners compute locally — helpers and inline sites alike — is now
classified and pinned against `qtr.validation.statistics`. No published number, gate, verdict
or certified number changed; 9 new tests pin the contract.**

### The gap

H40 pinned the runner-local metric *helpers* (the six `_period_metrics` helpers, H16's
`train_only_wf_sharpe`, DDCV's `window_max_drawdown`, H26's daily Sharpe, the CS-momentum
information ratio). But two classes of runner-local *inline* metric computations were agreeing
yet unpinned:

* Four inline drawdown sites use the library's convention
  (`cum / cummax - 1` or `equity / expanding().max() - 1`, both algebraically identical to
  `(equity - rolling_max) / rolling_max`):
  * `run_h11_robustness_experiment.py:548,648` — cost-multiplier loop drawdown and fresh OOS
    drawdown;
  * `run_h18_overnight_intraday_experiment.py:527,641` — full-period and OOS max drawdown.
* Three inline drawdown sites use the raw formula `(equity - expanding().max()).min()` — a
  dollar drawdown, not the library's percentage drawdown:
  * `run_ddcv_experiment.py:386,443` — OOS drawdown and ablation max drawdown;
  * `run_futures_tsmom_experiment.py:467` — OOS drawdown.
* H18's runner-local `total_return` copies (`:526,:637`) use the pre-H38 range; the formula
  itself matches the library's `(1 + returns).prod() - 1` exactly, but H18 applies it to a
  sliced equity curve. The 6.34-bps effect on the published full-period `total_return` of the
  selected row is disclosed and bounded; H18's nine gates do not use `total_return`.

### The contract now pinned

`tests/test_runner_metric_agreement.py` (42 tests total, 9 new in H41):

* `TestInlineDrawdownConforming` — the four library-conforming inline drawdowns agree with
  `validate_strategy["max_drawdown"]` within 1e-15 (floating-point noise).
* `TestInlineDrawdownRawVariant` — the three raw drawdown variants are pinned as
  `differs_convention`: they compute a dollar drawdown, not the library's ratio drawdown, and
  differ materially from `validate_strategy["max_drawdown"]`.
* `TestH18TotalReturn` — H18's `total_return` copies agree with the library's `total_return`
  exactly on the same data; the sliced-range application is disclosed and bounded.

### Verification

- `python -m pytest -q -W error` → **1212 passed, 1 skipped** (1203 + the 9 new H41 tests;
  the skip is the pre-existing `buy_and_hold` skip in H36's module).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → all format-clean; the only deviation
  across the repo is on pre-existing lines of `tests/test_runner_causality_inventory.py`
  (ruff 0.17.1 style drift).
- `tests/test_engine_metric_agreement.py`, `tests/test_runner_causality_inventory.py` and
  `tests/test_causality_invariant.py` all pass alongside the updated module.
- No `src/qtr` change, so coverage is unchanged (100%); H41 adds no branch.

**Nothing published was touched:** no published artifact, gate threshold, verdict, certified
number or published row was modified; no grid was re-run; no hypothesis was added; no
`run_*.py` was touched. The inline sites are classified and pinned, not rewritten (the
artifacts are frozen, so a rewritten helper would no longer reproduce them).

## H42 — the `ruff` reproducibility gap is closed (2026-10-21)

**Verdict: the lint/format gate is now reproducible from a bare clone.** The last open item in
`HANDOFF.md` was the `ruff` reproducibility gap: the record quoted `ruff check` and
`ruff format --check` as verification steps, but ruff was not declared in `pyproject.toml` or
`requirements.txt`, was not installed in the agent environment, and no ruff configuration was
committed. On inspection the premise was partly stale — `pyproject.toml` (introduced in H38,
commit 944cdc3) already declares `[project.optional-dependencies] lint = ["ruff>=0.6.0"]` and a
`[tool.ruff]` block with `target-version`, `line-length`, a lint `select`/`ignore` set and a format
`quote-style`/`indent-style`. Ruff 0.17.1 is installed in this environment and `python -m ruff
check src tests run_*.py` → *All checks passed!*. The residual gap was a single format deviation.

### The deviation

`python -m ruff format --check src tests run_*.py` → `1 file would be reformatted, 84 files
already formatted`: `tests/test_runner_causality_inventory.py`, introduced in H38 (commit
944cdc3), carries pre-existing style drift on 8 hunks — all pure line-wrapping that ruff's
configured `line-length = 100` wants collapsed or split:

- `_chained_path_dependent_exits` (:533-536) — one positional arg per line;
- `volumes = pd.DataFrame(...)` (:545-548) — `index=` / `columns=` on separate lines;
- three `pd.concat({...}, axis=1)` blocks (:627-642) — the dict literal pulled up onto the call line;
- two `build_roll_adjusted_returns` / `build_roll_adjusted_prices` calls (:676, :685) — wrapped;
- four `"dense"`/`"sparse"` lambda config dicts (:1699, :1736, :1859, :1878) — the nested dict
  reformatted onto its own block.

The file was not touched by H39, H40 or H41, so the drift predates the sessions that quoted the
clean result; each of those sessions disclosed it in its own handoff rather than silently
re-quoting.

### The change

`python -m ruff format tests/test_runner_causality_inventory.py` → `1 file reformatted`. Pure
whitespace: 61 insertions, 22 deletions across the 8 hunks. No `run_*.py`, no `src/qtr`, no
published artifact, gate, threshold, verdict or certified number was touched; no grid was re-run;
no hypothesis was added.

### Verification

- `python -m ruff check src tests run_*.py` → *All checks passed!* (unchanged).
- `python -m ruff format --check src tests run_*.py` → **85 files already formatted** (was 84 + 1
  unformatted; the deviation is gone).
- `python -m pytest -q -W error tests/test_runner_causality_inventory.py` → **321 passed** (the
  module that owns the formatted file; unchanged — formatting cannot change semantics).
- `python -m pytest -q -W error` → **1212 passed, 1 skipped** in 275.34 s (identical to the H41
  baseline: 1212 passed, 1 skipped in 276.17 s; the change is whitespace-only).
- `src/qtr` coverage is unchanged at 100%: the change is confined to a test file, so no branch is
  added or removed. (The coverage tool, `pytest-cov`, is still not installed in this
  environment — `python -m pytest --cov=qtr` → "unrecognized arguments"; the H39/H40/H41 branch
  argument applies unchanged.)

### Why this was worth doing

The lint/format gate was the only verification step in the record that could not be reproduced
from the repository. It is now reproducible: ruff is declared, configured and installed, and
both commands are clean on `src tests run_*.py` from a bare clone with `pip install -e ".[lint]"`.

## H43 — the coverage gate is measured, declared and complete (2026-10-21)

**Verdict: the coverage claim in this record is now a measurement, and the gate it describes is
committed, reproducible and complete.**

### The gap

H39, H40, H41 and H42 each recorded "src/qtr coverage is unchanged at 100%" and each recorded, in
the same breath, that **the coverage tool was not installed** in the session environment
(`python -m pytest --cov=qtr` → "unrecognized arguments"). The figure was therefore never
re-measured in four consecutive sessions: it was re-asserted from an argument — "the change is one
expression, so no new branch is introduced" — and each session added a parenthetical saying that
the measurement could not be repeated here.

Installing `pytest-cov` (already declared in `pyproject.toml` as
`test = ["pytest>=7.4.0", "pytest-cov>=4.1.0"]`) and running the measurement for the first time
since H38 produced two results:

- **The claim's substance was correct.** `src/qtr` had **1014 statements, 0 missed** — exactly the
  recorded number.
- **The claim was narrower than it read.** The quoted command
  (`--cov=qtr --cov-report=term-missing`) measures **statement** coverage. Statement coverage cannot
  see a branch that is never taken, and the first **branch** measurement found **11 partial
  branches** hiding behind the 100%:

  ```
  src/qtr/data/fetcher.py           165      0     54      3    99%   215->173, 284->293, 290->284
  src/qtr/strategies/baselines.py    148      0     70      2    99%   155->131, 267->272
  src/qtr/tracking/experiment.py     197      0     38      3    99%   89->95, 150->155, 326->exit
  src/qtr/validation/statistics.py   272      0     94      3    99%   172->161, 779->766, 816->803
  TOTAL                               1014      0    316     11    99%
  ```

  Every one of the eleven is a **defensive guard that no test had ever executed**: a guard nobody
  has seen work is a guard nobody can vouch for.

### What each partial branch was

| Arc | The untested guard | Closed by |
|---|---|---|
| `fetcher.py:215->173` | `fetch_futures` with `use_cache=False`: the *successful* download path never returned to the loop head, so a download with the cache disabled was never once exercised end-to-end | `test_fetch_futures_with_the_cache_disabled_leaves_the_cache_untouched` |
| `fetcher.py:284->293` | the CCXT pagination loop never ended on its `while` condition — only on an empty or short page, i.e. the normal end of a well-formed download was untested | `test_fetch_ccxt_paginates_until_the_window_is_exhausted` |
| `fetcher.py:290->284` | a full 1000-row page never continued the pagination loop | (same test) |
| `baselines.py:155->131` | `momentum_signals` never saw a bar on which *no* symbol had negative momentum, so the "no short leg to build" path was untested | `test_momentum_without_negative_symbols_leaves_the_short_leg_empty` |
| `baselines.py:267->272` | `time_series_momentum_signals`'s `if vol > 0` guard — **provably unreachable** (see below) | `_vol_scale` extraction + `test_vol_scale_leaves_a_position_unscaled_when_the_volatility_is_not_positive` |
| `experiment.py:89->95` | `start_experiment` never received explicit seeds, so the default was never *overridden* | `test_start_experiment_uses_the_caller_supplied_seeds` |
| `experiment.py:150->155` | `log_artifact` was never called without metadata, so the "no sidecar" path was untested | `test_log_artifact_without_metadata_writes_no_sidecar` |
| `experiment.py:326->exit` | `Experiment.__init__` never met an existing `metadata.json`, so "re-opening must not truncate the metadata" was untested | `test_experiment_constructor_preserves_existing_metadata` |
| `statistics.py:172->161` | `walk_forward_splits` never dropped a fold | `test_walk_forward_drops_a_fold_with_an_empty_test_side`, `test_walk_forward_drops_a_fold_with_an_empty_train_side` |
| `statistics.py:779->766` | `purged_kfold_splits` never dropped a fold | `test_purged_kfold_drops_a_fold_with_no_training_data` |
| `statistics.py:816->803` | `combinatorial_purged_cv` never dropped a fold | `test_combinatorial_purged_cv_drops_a_fold_with_no_training_data` |

The eleven guards are not cosmetic. Three of them decide whether a *leak* can occur
(`purged_kfold_splits` / `combinatorial_purged_cv` emitting a split with an empty training set),
one decides whether a *stale frame* can be served (`use_cache=False` still writing the cache), and
one decides whether a *previous run's* metadata can be truncated.

### The one unreachable branch

`time_series_momentum_signals` computed its realized volatility as
`returns.rolling(63).std() * sqrt(252)` and then sanitized it with
`.replace(0, np.nan).ffill().fillna(0.15)` — a chain that makes the series **strictly positive by
construction** (zeros become NaN, NaN is forward-filled, the leading NaNs become 0.15). The inline
`if vol > 0:` guard could therefore never fire: the false arm was dead code that no test could ever
reach. A 200-trial property check over random and constant price series confirmed the minimum
observed value is 0.15.

The guard was moved into a module-level helper, `_vol_scale(vol, target_vol)`, which returns the
unscaled multiplier `1.0` for a non-positive volatility and `min(target_vol / vol, 2.0)` otherwise.
The behavior is **identical** (the old code simply skipped the scaling, which is what a multiplier of
1.0 does), but the defensive path is now reachable and is covered by a test.
`time_series_momentum_signals` is not called by any `run_*.py` — only `vol_scaled_tsmom_signals`
is — so no published artifact, gate, threshold, verdict or certified number can be affected.

### The gate

`pyproject.toml` now declares the gate the record has been quoting:

```toml
[tool.coverage.run]
branch = true
source = ["src/qtr"]

[tool.coverage.report]
fail_under = 100
show_missing = true
```

`fail_under = 100` is what turns the claim into a gate: `python -m pytest -q --cov=qtr --cov-branch`
now **exits non-zero** if `src/qtr` is not fully covered. The configuration is additionally read
back through the coverage API by `tests/test_coverage_gate_contract.py`, so a section that the
coverage tool would ignore cannot pass for a committed gate. `pytest-cov` was already declared
under `[project.optional-dependencies] test`, so the gate is installable from a bare clone with
`pip install -e ".[test]"`; the package itself is still not required to be installed for
`python -m pytest` to pass.

### The change

- `src/qtr/strategies/baselines.py` — the unreachable inline `if vol > 0:` guard replaced by the
  `_vol_scale` helper (behavior-preserving; +2 statements).
- `pyproject.toml` — the `[tool.coverage.run]` / `[tool.coverage.report]` gate.
- `tests/test_coverage_gate_contract.py` — **new**, 18 tests: 6 gate pins + 12 branch-closure
  tests.
- `FINAL_REPORT.md`, `NEXT_TASK.md` and the `HANDOFF*` files.

No published artifact, gate threshold, verdict, certified number or published row was modified; no
grid was re-run; no hypothesis was added; no `run_*.py` was touched.

### Verification

- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` → **1230 passed,
  1 skipped**; `src/qtr` = **1016 statements, 316 branches, 0 missed, 0 partial, 100.00%**; the
  committed gate reports *"Required test coverage of 100.0% reached. Total coverage: 100.00%"*.
- `python -m pytest -q -W error` → **1230 passed, 1 skipped** in 271.26 s (the bare-clone path: no
  install step, no coverage plugin, no network).
- `python -m pytest -q -W error tests/test_coverage_gate_contract.py` → **18 passed**.
- The bare-clone path was re-checked with the coverage tool *absent* (a shim module raising
  `ModuleNotFoundError` on `import coverage`): **17 passed, 1 skipped** — the gate's tool-dependent
  test skips cleanly and the rest of the module still runs.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **86 files already formatted** (85 + the new
  test module).

### Why this was worth doing

Three things changed. The record's coverage claim is now backed by a measurement instead of an
argument — and the measurement *confirmed* the claim, which is the strongest form of that result.
The gate is now declared and **fails closed** instead of being a sentence in a report. And the
eleven guards it was hiding are no longer untested: each is now exercised by a named test that
asserts the property it exists to protect.

The generalisable lesson for this record: a coverage figure quoted as a *statement* percentage is
not the same claim as "the code is fully exercised", and a verification step that the environment
cannot run is not a verification step. Both are now fixed at the source — the tool is installable
and declared, the gate is committed, and the number is measured.

## H45 — the package's public API is declared, complete and actually exported (2026-10-21)

**Verdict: the convenience-export surface that H44 added was empty, and the check that
certified it could not fail. Both are now fixed at the source and pinned by an executable
contract.**

### The gap

H44 added "convenience exports" to the top-level `qtr` package and recorded the verification as:

```
PYTHONPATH=src python -c "from qtr import *; print('ok')"   ->   ok
```

That check is **vacuous**: `from qtr import *` succeeds whether it exports zero names or five
hundred, and `print('ok')` prints `ok` either way. It is the same defect class this record has
been hunting since §H35 — a check that cannot fail is not a check.

Measuring the surface the check was supposed to certify found three separate defects:

| Defect | Consequence |
|---|---|
| `qtr.__all__` was `["__version__"]` | `from qtr import *` exported **exactly one name**. The wildcard re-exports were unreachable through the very mechanism H44 added them for. |
| `qtr.backtest`, `qtr.data`, `qtr.tracking` had **empty** `__init__.py`; `qtr.utils` had **none at all** | Four of the six subpackages exported nothing. `qtr.run_backtest`, `qtr.get_data_fetcher`, `qtr.create_experiment` and `qtr.get_config` did not exist. |
| `qtr.utils` was a **namespace package**, not a regular package | `setuptools.find_packages(where="src")` returned `['qtr', 'qtr.strategies', 'qtr.tracking', 'qtr.backtest', 'qtr.data', 'qtr.validation']` — **`qtr.utils` was not among them**. The distribution shipped `qtr/utils/config.py` only because setuptools copies the stray file as package data, and it was importable only by PEP 420 luck. Because `qtr/__init__.py` imports it, the *whole package* was one directory away from failing to import. |

The H44 handoff recorded the outcome as "no assigned task; optionally expand top-level exports
with explicit symbols if API ergonomics matter; not critical". The surface was in fact
non-functional, and the *verification* was the reason it went unnoticed.

### The change

- `src/qtr/utils/__init__.py` — **new**. A regular package with explicit re-exports
  (`get_config`, `load_config`, `save_config`) and an `__all__`. This closes the packaging hole:
  `qtr.utils` is now a discovered distribution package.
- `src/qtr/backtest/__init__.py`, `src/qtr/data/__init__.py`, `src/qtr/tracking/__init__.py` —
  explicit re-exports of each module's public API plus an `__all__`, matching the convention
  already used by `qtr/strategies/__init__.py` and `qtr/validation/__init__.py`.
- `src/qtr/__init__.py` — the top level now composes `__all__` **from the subpackages' own
  `__all__` lists**, so the aggregate cannot drift from what it aggregates. The star import
  exports **46 names** plus `__version__` (was: 1).
- `tests/test_public_api_contract.py` — **new**, 33 tests.

### The contract

The new module pins the surface in five layers:

1. **Packaging** (3 tests) — every subpackage is a *regular* package (it has an `__init__.py`),
   and the build backend discovers every one of them. The `qtr.utils` hole cannot return.
2. **Declaration** (22 tests) — every subpackage declares an explicit, non-empty, duplicate-free
   `__all__`; no subpackage uses a star import (so the declaration is checkable); and each
   subpackage's `__all__` is **exactly** the public API of the module it re-exports, computed from
   the AST. This cuts both ways: a new public function nobody exports fails the test, and so does
   an export of a name the module does not define.
3. **Aggregation** (2 tests) — the top-level `__all__` is the union of the subpackages' `__all__`s
   plus `__version__`, and every declared name is bound at runtime.
4. **The star import** (3 tests) — `from qtr import *` exports **exactly** the declared API, the
   declared API is not a one-name set, and the star import reaches a representative of **every**
   subpackage (`run_backtest`, `get_data_fetcher`, `momentum_signals`, `create_experiment`,
   `get_config`, `sharpe_ratio`).
5. **Version** (1 test) — `qtr.__version__` equals the version the distribution ships.

### Verification

- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` → **1263 passed,
  1 skipped**; `src/qtr` = **1038 statements, 316 branches, 0 missed, 0 partial, 100.00%**; the
  committed gate reports *"Required test coverage of 100.0% reached. Total coverage: 100.00%"*.
- **Negative control** — the new module was run against the **pre-H45** sources (`git checkout --
  src/qtr/`, `src/qtr/utils/__init__.py` removed): **15 of the 33 tests fail**, each naming one
  of the defects above. The contract is not vacuous.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **88 files already formatted** (87 + the new
  test module).
- `setuptools.find_packages(where="src")` → now `['qtr', 'qtr.backtest', 'qtr.data', 'qtr.strategies',
  'qtr.tracking', 'qtr.utils', 'qtr.validation']` — **`qtr.utils` present**.
- A wheel was built (`pip wheel --no-deps --no-build-isolation`) and installed into an isolated
  target: the wheel now contains `qtr/utils/__init__.py`, and from the **installed** package
  `from qtr import *` exports the same 46 names, with `qtr.utils` a regular package.

### What was not changed

No published artifact, gate threshold, verdict, certified number or published row was modified;
no grid was re-run; no hypothesis was added; no `run_*.py` was touched. The change is confined to
the package's import surface and adds no computational behaviour: every re-exported symbol is the
*same object* the module defines.

One pre-existing, unrelated observation, recorded rather than fixed: the **committed**
`src/qtr.egg-info/` manifest is stale (it predates eight test modules added since H33).
Regenerating it with the setuptools available in this session (68.1.2) would *degrade* the
committed `PKG-INFO` (it emits `Metadata-Version: 2.1` and drops the `Requires-Dist` entries), so
the generated metadata was left untouched. It is regenerated on every build and does not affect
the wheel, which was verified directly.

### Why this was worth doing

The public API is the one surface every downstream user touches, and it was the one surface in the
repository that no test reached. The lessons are the same two the record has already paid for
twice: **a verification step that cannot fail is not a verification step** (§H43's coverage
re-assertion, and now H44's `print('ok')`), and **a declared gate is only a gate if the
declaration and the code are compared** (§H35's vacuous gates, and now the empty `__all__`s). The
fix is the same in both cases: make the invariant executable, and check the negative control so
the check is known to be able to fail.

## H47 — the engine's trade log did not reconcile with the transaction costs it charges (2026-10-21)

**Verdict: the engine's *charge* was never wrong, but the trade log that is supposed to audit it
recorded the bar's aggregate cost on every trade of that bar. The log now carries each trade's own
cost, and the reconciliation is pinned by an executable contract.**

### The gap

`VectorizedBacktester._extract_trades` wrote the `cost` column of the trade log from the
**per-bar portfolio cost** series:

```python
"cost": costs[idx] if idx in costs.index else 0,     # `costs` is the per-BAR TOTAL
```

Every trade that happened in a bar therefore carried the **whole bar's** transaction cost. A bar
with `k` simultaneous trades reported `k` times the cost that was actually deducted from the
returns, so the trade log no longer reconciled with the P&L it exists to audit, and
`metrics["avg_trade_cost"]` was an average *per trade-bar* rather than per trade.

The defect is invisible in a single-symbol backtest (there, the bar total **is** the trade's own
cost), which is why it survived: the runners that exercise the multi-contract path are the
intraday futures family.

### The evidence (frozen artifacts, read-only)

The certified H10 artifact (`exp_2026-10-11T17-41-18-169363Z`) holds **3,701** trades over
**2,975** bars with up to **5** simultaneous trades per bar:

| Quantity | Value |
|---|---|
| bars whose trades do **not** all record the same number | **0 of 2,975** |
| the per-bar totals (= the engine's charge) | **0.034907** |
| the published `cost` column, summed over all trades | **0.062352** |
| **over-count factor** | **1.786×** |

The charge itself is confirmed correct by the repository's own **H27 `L3` check**, which
recomputes the per-bar cost *from the trade log* (each trade's own cost, summed per bar) and
matches the engine's per-bar cost to **~1e-19** for all five audited families (H9, H10, H21, H22,
H25). The engine already computed the correct per-trade cost; the log simply did not carry it.

### The change

- `src/qtr/backtest/engine.py` — the cost model now keeps the **per-symbol** breakdown
  (`_calculate_costs_by_symbol`), the per-bar charge is their sum (`_total_costs`), and
  `_extract_trades` attributes each trade its own share. `_calculate_costs` is retained (it is
  used by `run_h27_pnl_level_audit.py`) and returns the **same** series as before.
- `tests/test_trade_log_cost_reconciliation.py` — **new**, 13 tests.

### The contract

1. **Reconciliation** — the per-trade costs sum to the charged cost, bar by bar and in total, for
   the equity, futures and crypto cost paths.
2. **Own-share identity** — the cost of a trade is reproduced by an *independent* formula from the
   trade log and the cost model (`|Δw| · bps / 10⁴` for equity; `|Δw| · C / (p · m)` for futures),
   so the attribution is checked, not merely re-derived from the engine's internals.
3. **Strict share** — in a bar with `k > 1` trades, each trade accounts for exactly `1/k` of the
   bar's charge.
4. **The charge is unchanged** — the engine's net returns are still exactly the gross returns minus
   the charged series.
5. **Negative control** — the pre-fix (aggregate) attribution is reconstructed from the fixed log
   and is shown to **fail** the reconciliation, so the invariant is known to be able to fail.
   Against the **pre-fix** engine, **6 of the 13 tests fail**, the first with the exact
   over-count: `log=0.0016` against `charged=0.0008`.
6. **Frozen-record disclosure** — the committed H10 trade log still shows the pre-fix aggregate
   attribution (0 of 2,975 bars disagree; over-count 1.786×), and the H27 `L3` result is pinned as
   the proof that the bar total is the charge. **Scope corrected in §H52**: the disclosure covers
   **every** committed trade log (**82**), not the six families named below.

### What was not changed

No published artifact, gate threshold, verdict or certified number was modified; no grid was
re-run; no hypothesis was added. The fix is **attribution-only**: the net returns, the equity
curve, the positions and every metric except `avg_trade_cost` are **bit-identical** to the pre-fix
engine (verified by running the pre-fix and post-fix engines side by side over nine
equity/futures/crypto cases).

Two disclosures follow, and are pinned rather than rewritten. **Both were measured against the
whole record in §H52, which corrects the scope stated here:**

- The `cost` column of **every** committed trade log — **82** of them, spanning **eleven**
  families (H3, H10, H11, H16, H17, H19, H20, H21, H22, H23, H25) and 44 exploratory artifacts —
  carries the pre-fix aggregate attribution. (This section originally named six families, "H10,
  H11, H16, H21, H22, H25"; the list was narrower than the record.) The artifact files are frozen
  and are left untouched. No gate, threshold, verdict or certified number reads that column; the
  H11 reproduction check compares Sharpe, profit factor, drawdown, the trade *count*,
  walk-forward stability and worst-regime Sharpe — all unaffected.
- The `avg_trade_cost` of the **five** committed summaries that publish it — the three
  exploratory 2026-10-10 MA-crossover baselines (257, 257 and 778 trades) and the two
  single-trade buy-and-hold baselines — is on the pre-fix basis; in the three multi-trade cases it
  over-states the per-trade average by 1.229953×, 1.247109× and 2.868948×. (This section
  originally named three of the five.) The tracker metadata publishes the **benchmark's**
  `avg_trade_cost` in **23** further entries, on the same basis. All of these are engine-only
  diagnostics that no gate uses; `FINAL_REPORT.md` and the reports never quoted them.

## H48 — `parameter_sensitivity` could not be seeded (2026-10-21)

**Verdict: the published record is unaffected — nothing in it reads `parameter_sensitivity` — but the
function was the only bootstrap caller in the package that could not be seeded, so its confidence
intervals changed on every call. It now takes an optional `random_state`, and the reproducibility is
pinned by an executable contract.**

### The gap

`qtr.validation.statistics.parameter_sensitivity` is part of the package's public API
(`qtr.validation.__all__`) and it called `bootstrap_confidence_interval` **without** a
`random_state`:

```python
ci_lower[i], ci_upper[i] = bootstrap_confidence_interval(
    returns[i], metric_func, n_bootstrap=n_bootstrap      # no random_state
)
```

`bootstrap_confidence_interval` seeds its generator with `np.random.default_rng(random_state)`, so
with `random_state=None` the generator draws from **OS entropy**. Two calls on the same input
therefore returned *different* confidence intervals:

| call | `ci_lower` (2 parameter rows, `n_bootstrap=200`) |
|---|---|
| 1 | `[-0.7393122, -2.54308907]` |
| 2 | `[-0.93933284, -3.07895489]` |

The point estimates (`metrics`, `optimal_param`, `optimal_metric`, `stability_ratio`, `metric_std`)
are deterministic — only the bootstrap bounds move — which is why the defect was invisible in every
published number.

Its siblings already did the right thing: `sharpe_ratio_ci` and `bootstrap_confidence_interval`
both accept `random_state`, and **every** runner that calls the bootstrap directly passes one
(`run_cs_momentum_experiment.py:385`, `run_ts_momentum_experiment.py:563`,
`run_regime_gated_momentum_experiment.py:725`). `parameter_sensitivity` was the only bootstrap
caller in the package that could not be seeded.

### The change

- `src/qtr/validation/statistics.py` — `parameter_sensitivity` now takes an optional
  `random_state`. The default stays `None`, so **no existing caller changes behaviour**; an integer
  seed is expanded by the new helper `_bootstrap_seeds` into **one independent stream per parameter
  row** (so the rows are not resampled with a shared pattern), and the call becomes a pure function
  of the seed. A row's seed does not depend on how many rows the grid holds, so extending the grid
  does not perturb the rows already analysed.
- `tests/test_parameter_sensitivity_reproducibility.py` — **new**, 14 tests.

With this change the package's **entire** stochastic surface is seedable: `src/qtr` contains exactly
two randomness sites, both in `statistics.py` (`bootstrap_confidence_interval` and the new
`_bootstrap_seeds`), and every stochastic computation reachable from the public API now takes a
`random_state`.

### The contract

1. **Exact reproducibility** — two calls with the same seed agree bit-for-bit.
2. **Seed isolation** — the legacy global `np.random.seed` cannot move the result.
3. **Seed reaches the bootstrap** — two different seeds give different bounds.
4. **Point estimates are seed-free** — `metrics`, `optimal_param`, `optimal_metric`,
   `stability_ratio` and `metric_std` do not depend on the seed.
5. **Row independence** — two *identical* parameter rows get *different* intervals, so the rows are
   not resampled with a shared pattern.
6. **Grid stability** — extending the grid does not move the intervals of the rows already analysed.
7. **Cross-process reproducibility** — a second interpreter, started from a clean OS entropy pool,
   produces the same bounds.
8. **Negative control** — the unseeded path really does move, and the pre-fix call site (the seed
   accepted but never threaded) is reconstructed and shown to **fail** the reproducibility
   invariant. Against the **pre-fix** implementation, **4 of the 14 tests fail**, and every one of
   them fails *behaviourally* (the bounds move) — the contract is not satisfied by a missing
   keyword. (An earlier draft of this contract failed only with `TypeError: unexpected keyword
   argument 'random_state'`; that measures the *API*, not the behaviour, and was replaced by the
   adapter in `_seeded()`, which calls the pre-fix function on its unseeded path.)
9. **Published-record disclosure** — no `run_*.py` calls `parameter_sensitivity` (AST-checked), and
   `validate_strategy` derives its published `param_stability` from the walk-forward fold Sharpes
   (AST-checked, and recomputed independently in the test), so the `min_param_stability` gate stays
   deterministic and no published number moves.

### What was not changed

No published artifact, gate threshold, verdict or certified number was modified; no grid was
re-run; no hypothesis was added. The default (`random_state=None`) path is **byte-for-byte the
behaviour it always had** — it is the same unseeded bootstrap, just now *documented* as such. No
runner calls `parameter_sensitivity`, and `validate_strategy` computes its published
`param_stability` from the walk-forward fold Sharpes
(`src/qtr/validation/statistics.py`, `param_stability = mean(fold_sharpes > 0)`), **not** from
`parameter_sensitivity`; both facts are pinned by the new contract, so the disclosure cannot
silently lapse.

## Next task

One task is assigned (stated in full in `NEXT_TASK.md`):

> **Extend the executable contract from the package's import surface to the runners' import
> surface.** The `run_*.py` scripts are the other half of the repository's public entry points —
> they are what the record calls "the runners", and they are imported by the test suite and by
> each other — but no test pins *which* modules they import, whether those imports are the
> canonical ones, or whether a runner can still be imported at all. A runner that has been broken
> by an import-level change (a renamed symbol, a moved module, a subpackage that no longer
> re-exports what the runner expects) would fail at run time, not at test time.

**Superseded (2026-10-21, after H46).** The task above was **completed in H46**: the runners'
import surface is declared, classified and pinned by `tests/test_runner_import_contract.py`
(32 runners importable, library imports resolved against `qtr.__all__` / the subpackages' `__all__`,
third-party imports checked against `pyproject.toml` via `tomllib`, local imports restricted to
other `run_*.py`). The current assignment is in `NEXT_TASK.md`; the text above is retained as the
H45-era record.

**Superseded (2026-10-21, after H48).** The assignment that followed H47 was **completed in H48**:
`parameter_sensitivity` now takes an optional `random_state` (§H48) and its reproducibility is
pinned by `tests/test_parameter_sensitivity_reproducibility.py` (14 tests; 4 of them fail
behaviourally against the pre-fix implementation).

**H49 is complete** (2026-10-21): the published `validation` blocks in all five exploratory
summaries re-derive from their own frozen `equity_curve.parquet` under the engine's full return
convention (including the opening bar), and the `walkforward_stability` basis — the sign-unaware
`sharpe(2nd half) / sharpe(1st half)` — is disclosed and pinned by
`tests/test_h49_validation_block_disclosure.py` (11 tests). The two buy-and-hold blocks differ from
each other because they charged different costs baked into their own frozen equity curves. Full
statement with the measured table in **§H49** above.

**H50 is complete** (2026-10-21): the setuptools-generated metadata directory is **untracked** and
ignored, and `pyproject.toml` is now the only declared source of the package's metadata. The
"regenerate and commit" route is closed by measurement — the generated metadata's serialisation
depends on which setuptools built it (`Metadata-Version: 2.1` locally, `2.4` under pip's build
isolation) — and the arrangement is pinned by `tests/test_generated_manifest_contract.py`
(11 tests; 3 of them fail behaviourally against the pre-fix state). Full statement in **§H50**
above.

**H51 is complete** (2026-10-21): `compare_to_benchmark` is now **container-independent** — both
sides are reduced to float numpy arrays before any statistic is computed, every standard deviation
carries an explicit `ddof`, and the excess volatility (and the information ratio) is taken on the
**population** standard deviation (`ddof=0`). The convention was chosen on measured grounds: **26**
of the **48** committed artifacts that publish an `information_ratio` are on `ddof=0` and **22** on
`ddof=1`, so enforcing `ddof=0` keeps the larger set unchanged; it is also this package's own
convention (`sharpe_ratio` uses `ddof=0`) and it preserves the existing
`tests/test_runner_metric_agreement.py` pin that the library's IR and `run_cs_momentum`'s local IR
agree exactly. Every published value was re-derived from its own artifact (bit-exact for the
families that log both return series); the 22 that move move by **+4.371e-05** (n = 11441) and
**+1.671e-03** (H23, n = 300), no sign changes, so no gate outcome can move. Full statement with the
measured table in **§H51** above.

**H52 is complete** (2026-10-21): §H47's cost-attribution disclosure now covers **the whole
committed record**, not one artifact. The §H47-era scan used the pathspec
`".experiments/artifacts/*/trades.parquet"`, which sees only the **41** logs literally named
`trades.parquet`; the record is **82** (`".experiments/artifacts/*trades*.parquet"`), spanning
**eleven** families plus 44 exploratory trade logs. **All 82** carry the pre-fix aggregate
attribution: **70** of them have bars with more than one trade, so the attribution changes a
number there (repetition factor 1.229953× … 20.677528×); **7** have only single-trade bars, where
the two attributions coincide by construction; **5** hold no trade at all. The published numbers
that read the column are disclosed too: **5** summaries publish `avg_trade_cost` (3 of them
over-stated) and **23** tracker-metadata entries publish the **benchmark's** `avg_trade_cost` (9
of them measured at 20× or 5×). The pin now names every log, pins the two sub-sets separately and
carries a behavioural negative control. Full statement with the measured 82-row table in **§H52**
above.

The state a next session inherits:

- **One task is assigned (H53)** — stated in full in `NEXT_TASK.md`: audit the **remaining**
  committed `summary.json` files for keys that no longer re-derive from the artifacts that
  published them — the §H49/§H51 methodology generalised to **every** published block, with the
  per-key convention of each publisher recorded. The measurement behind the task: **80** committed
  `summary.json` files, of which the §H49 pass covered **5** and the §H51 pass covered the **48**
  that publish an `information_ratio`.
- The pre-registered free-data hypothesis space (H1–H30) remains **exhausted**; no new hypothesis
  is warranted and no grid may be re-run.
- The certified families (H10, H22, H25) are unchanged. Every published artifact, threshold,
  verdict and certified number is frozen.
- The shared library, the engine and every `run_*.py` remain pinned as **point-in-time**; re-run
  `tests/test_causality_invariant.py` after any change under `src/qtr`, and
  `tests/test_runner_causality_inventory.py` after any change in a runner.
- The package's public API is now declared, complete and non-vacuously pinned (§H45); re-run
  `tests/test_public_api_contract.py` after any change under `src/qtr`.
- The runners' import surface is declared, classified and non-vacuously pinned (§H46); re-run
  `tests/test_runner_import_contract.py` after any change in a runner or under `src/qtr`.
- The engine's trade log now reconciles with the transaction costs it charges (§H47), and the
  **whole frozen record** is pinned (§H52); re-run
  `tests/test_trade_log_cost_reconciliation.py` after any change under `src/qtr/backtest` **or after
  a new artifact is committed**.
- The package's stochastic surface is seedable and the reproducibility is pinned (§H48); re-run
  `tests/test_parameter_sensitivity_reproducibility.py` after any change under
  `src/qtr/validation`.
- The package's metadata has exactly one declared source of truth (§H50); re-run
  `tests/test_generated_manifest_contract.py` after any change to `pyproject.toml`, `.gitignore`
  or the packaging layout.

Previous state, retained for the record: all assigned tasks H35–H43 are complete. All
metric-agreement sites — library-side (§H39), runner-local helpers (§H40) and runner-inline sites
(§H41) — are classified and pinned; every gate defect class that has surfaced (§H35) is closed by
an executable invariant; the point-in-time contract covers every `run_*.py` (§H36–H37); the
engine's `total_return` spans every bar (§H38); the package's two Sharpe implementations agree
(§H39); the lint/format gate is reproducible (§H42); and the coverage gate is measured, declared
and complete (§H43).

## H49 — the published `validation` blocks re-derive from the frozen artifacts (2026-10-21)

**What changed.** `tests/test_h49_validation_block_disclosure.py` (11 tests) re-derives each
published `validation` block from its own frozen `equity_curve.parquet` and asserts the published
values, so the drift cannot change silently. `FINAL_REPORT.md` §H49 is rewritten below to record
the corrected finding.

### The corrected finding

Re-deriving the block from each artifact's own frozen equity curve reproduces the published
numbers **for all five artifacts**, to float noise (< 1e-9). The earlier handoff's claim that the
last two artifacts "do not re-derive" was based on the wrong return convention.

**The return convention is the missing first bar.** The engine charges costs per bar and compounds
them into the equity curve (`equity = (1 + net_returns).cumprod() * initial_capital`), so the
equity curve carries the full series including the opening bar. Recovering the returns by
`equity.pct_change()` alone drops that bar: for `exp_2026-10-14T08-26-02-537359Z` that yields
Sharpe `0.6849808` against the published `0.6847308` (a 2.5e-4 gap). Including the first bar's
return — `equity[0] / initial_capital - 1`, the cost of the very first position change, charged on
the opening bar — reproduces the published block exactly (`0.6847308`).

| artifact | sharpe | profit_factor | max_drawdown | total_return | walkforward_stability |
|---|---|---|---|---|---|
| `…17-02-22-080026Z` | matches (4e-16) | matches | matches | matches | matches (4e-16) |
| `…17-03-39-610858Z` | matches (2e-15) | matches | matches | matches | matches (2e-16) |
| `…17-04-21-400695Z` | matches (9e-16) | matches | matches | matches | matches (4e-15) |
| `…17-05-58-697503Z` | matches (8e-16) | matches | matches | matches | matches (5e-15) |
| `…08-26-02-537359Z` | matches (3e-15) | matches | matches | matches | matches (4e-15) |

(published vs re-derived; "matches" = |diff| < 1e-9)

### The `walkforward_stability` basis

Every published `walkforward_stability` is exactly `sharpe(second half) / sharpe(first half)`,
taken **unconditionally** — the pre-guard formula. The published `walkforward_folds` also
re-derive from the frozen equity curve under the same convention.

* Three ma_crossover artifacts: **both halves losing** (`−1.5594 / −0.8479 = 1.8391876…`), so the
  sign-unaware ratio **passed** the `0.7` gate on a strategy that lost money in both halves. The
  current sign-aware code reports `0.0` and would report `walkforward_pass: False`.
* Two buy-and-hold artifacts: **both halves profitable**, so the published value and the current
  sign-aware code agree (`1.0277108` and `0.9334875`).

All five published blocks report `walkforward_pass: True` and `all_pass: false`; the current code
would report `walkforward_pass: False` for the three ma_crossover artifacts. **No verdict moves** —
all five are already `false`, and adding the sign-aware guard can only turn `true` into `false`.

### Why the two buy-and-hold blocks differ from each other

`exp_2026-10-10T17-05-58-697503Z` and `exp_2026-10-14T08-26-02-537359Z` run the **same** SPY
buy-and-hold series: their price series are byte-identical and their equity curves are proportional.
But their published blocks differ because they charged **different costs**, baked into their own
frozen equity curves:

* `…17-05-58-697503Z` — real cost model, `avg_trade_cost = 0.041105949376283715`;
* `…08-26-02-537359Z` — fixed `0.0002` per trade, `avg_trade_cost = 0.00020009711746988646`.

Each block re-derives exactly from **its own** frozen equity curve; they do not re-derive from each
other's. This is disclosed, not reconciled: the artifacts are frozen.

### What was verified

- `python -m pytest -q tests/test_h49_validation_block_disclosure.py` → **11 passed**.
- The re-derivation is read-only against the frozen artifacts (no pipeline re-execution, no
  network, no grid re-run).
- The published blocks carry **no `param_stability` key** (they pre-date that gate); pinned.
- The published `all_pass` is `false` for all five and stays `false`.

### What remains unresolved

- The **certified** families are out of scope: they carry no `validation` block, and no gate,
  threshold, verdict or certified number may move.
- The H47 cost-attribution disclosure and the stale `src/qtr.egg-info/` manifest are unchanged.

## H50 — the package's metadata has exactly one source of truth (2026-10-21)

**What changed.** The setuptools-generated metadata directory `src/qtr.egg-info/` is **no longer
tracked**; `*.egg-info/` is now in `.gitignore`, and `tests/test_generated_manifest_contract.py`
(11 tests) makes the arrangement structural rather than advisory: `pyproject.toml` is the only
declared source of the package's metadata, and nothing in the package depends on the build
artifact.

- `.gitignore` — `*.egg-info/` added.
- `src/qtr.egg-info/` — **untracked** (`git rm -r --cached`). The files stay on disk (the editable
  install resolves to them) but they are no longer part of the repository.
- `tests/test_generated_manifest_contract.py` — **new**, 11 tests.
- `FINAL_REPORT.md` — new **§H50** section and an updated "Next task" section.

### The gap

`src/qtr.egg-info/` is a **build artifact**, not a source file. setuptools rewrites it on every
build and every install, so the copy in the repository could only ever be a stale snapshot of the
tree — and it was. The tracked `SOURCES.txt` held **61** entries where the current tree produces
**64**: the three test modules added between H33 and H49 (`test_h49_validation_block_disclosure.py`,
`test_parameter_sensitivity_reproducibility.py`, `test_trade_log_cost_reconciliation.py`) were
missing from it. Nothing in the suite noticed, because a tracked manifest has no invariant: the
drift was invisible for sixteen sessions.

### Why "regenerate and commit" is not the fix — measured

Two earlier sessions rejected regeneration and asked for a materially different route. The
conclusion was right; the stated mechanism was not quite right, and the measurement is worth
recording because it is the argument for untracking.

Building the same tree with the **local setuptools 68.1.2** (no build isolation) against the
committed `PKG-INFO`:

```python
from setuptools import build_meta
build_meta.prepare_metadata_for_build_wheel("<tmp>")
```

```
Metadata-Version: 2.1          <- local setuptools 68.1.2
Requires-Dist: numpy >=1.24.0
Requires-Dist: yfinance >=0.2.0 ; extra == 'data'
```

against the committed file, which was built under pip's build isolation (a newer setuptools):

```
Metadata-Version: 2.4          <- committed
Requires-Dist: numpy>=1.24.0
Requires-Dist: yfinance>=0.2.0; extra == "data"
```

The **same** package, two different serialisations: the metadata version drops `2.4 → 2.1`, the
requirement markers are re-spaced and re-quoted, and the entries are reordered. A **correction to
the earlier record**: the `Requires-Dist` entries are *not* dropped — every base requirement and
every extra's requirement is present in both builds; they are reformatted. What is actually
environment-dependent is the **serialisation**, which is enough to make "regenerate and commit"
irreproducible: the committed bytes would freeze whichever setuptools happened to build them last.

A build artifact is therefore the wrong thing to version. The answer is to **untrack** it and to
make `pyproject.toml` the single declared source of truth — the route the H48 and H49 handoffs
prescribed.

### The contract now pinned

`tests/test_generated_manifest_contract.py` (11 tests) holds six invariants:

1. **Ignored** — `.gitignore` declares the rule, and `git check-ignore` agrees (the textual rule
   and git's matcher can disagree, and git refuses to report a *tracked* path as ignored, so the
   check is made with git).
2. **Not tracked** — no tracked path lives inside a `*.egg-info/` directory.
3. **Only one declaration** — no tracked `setup.py`, `setup.cfg`, `PKG-INFO`, `requires.txt` or
   `top_level.txt`: `pyproject.toml` is the only place the package's metadata is declared.
4. **No dependency** — no module under `src/qtr` references the generated manifest. The package is
   importable from a bare clone with no install step (`pythonpath = ["src"]`), so a module that
   read `src/qtr.egg-info/...` would work in a developer's checkout and fail in a fresh clone.
5. **The build agrees with the declaration** — the generated `PKG-INFO` *and* the installed
   distribution's metadata must reproduce the declared version, python floor, base requirements and
   every extra's requirements. The comparison is normalisation-based (`numpy >=1.24.0` and
   `numpy>=1.24.0` are the same requirement), so it does not depend on which setuptools built it.
6. **No staleness** — a generated `SOURCES.txt` that exists must list the package's current
   modules (the modules the distribution ships; a test module is not part of it, so its absence
   from the manifest says nothing about what would be installed).

Two facts worth recording, both found while writing the contract:

- **`importlib.metadata` resolves the distribution to the source tree** whenever `src` is on the
  import path (which the test suite puts there): `importlib.metadata.distribution("qtr")._path` is
  `src/qtr.egg-info`, not the installed `dist-info`. A developer's tooling therefore reads the
  *generated* manifest as the package's metadata — which is precisely why invariant 5 checks it.
- **The git-backed checks skip cleanly** when the checkout carries no git metadata (a source
  tarball), so the suite still runs from a bare clone; but a git command that *ran and failed*
  (`check-ignore` exiting 1 because nothing matched) is a verdict, not an absence, and now fails
  the contract instead of being silently skipped.

### What was verified

- `python -m pytest -q -W error tests/test_generated_manifest_contract.py` → **11 passed**.
- `python -m pytest -q -W error` → **1377 passed, 1 skipped** (full suite, up from 1366).
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` → `src/qtr` =
  **1054 statements, 320 branches, 0 missed, 0 partial, 100.00%** (unchanged — no module under
  `src/qtr` was touched).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **93 files already formatted**.
- **Negative control** — the contract run against the **pre-fix** state (the manifest re-added to
  the index with `git add -f`): **3 of the 11 tests fail**, and every failure is *behavioural* — the
  detector names the offending paths (`src/qtr.egg-info/PKG-INFO`, `…/requires.txt`,
  `…/top_level.txt`), `check-ignore` exits 1 against a tracked path, and the "only one declaration"
  invariant lists the duplicate metadata files. No failure is an error, a skip, or a missing
  keyword.
- The change is **additive to the repository's history**: the manifest files remain on disk, the
  editable install still resolves (`import qtr` → `src/qtr/__init__.py`), and the working tree is
  clean after `pip install -e .` — where it previously was not, because the tracked copy was
  rewritten by the install.

### What was not changed

No published artifact, gate threshold, verdict or certified number was modified; no grid was
re-run; no hypothesis was added; **no module under `src/qtr` and no runner was touched**.

### What remains unresolved

- The **22 published `information_ratio` values on the sample (`ddof=1`) convention** no longer
  re-derive from the library, which now enforces the population convention. They are **disclosed**,
  not rewritten (§H51): the move is `+4.371e-05` at `n = 11441` and `+1.671e-03` at `n = 300`, no
  sign changes and no gate outcome moves.
- The **H47 cost-attribution disclosure** (the `cost` column of the committed trade logs) covered
  less than the record does — all 41 trade logs the §H47-era scan saw carry the pre-fix
  attribution, and the disclosure was pinned for one of them. **Resolved in §H52**: the record is
  **82** trade logs, all of them carry the attribution, and all of them are pinned.
- **H9's published OOS Sharpe** is on the sample convention; disclosed and pinned, verdict frozen.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified
  families' numbers and verdicts are frozen.

## H51 — `compare_to_benchmark` is container-independent, and the published convention split is disclosed (2026-10-21)

**What changed.**

- `src/qtr/validation/statistics.py` — `compare_to_benchmark` now reduces **both** sides to plain
  float numpy arrays *before* any statistic is computed, and every standard deviation carries an
  explicit `ddof`. The excess volatility (and with it the information ratio) is taken with
  **`ddof=0` (population)**.
- `tests/test_h51_benchmark_container_invariance.py` — **new**, 246 tests (12 skipped for documented
  reasons): the container invariance for all nine keys, the enforced convention, the per-family
  disclosure, and the negative control.
- `FINAL_REPORT.md` — this section, an updated "Next task" section and an updated "What remains
  unresolved".
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT_SESSION.md`, `HANDOFF_NEXT.md` — updated.

### The defect (measured, not assumed)

`compare_to_benchmark` built the excess series with the *caller's* container: `excess = strat - bench`
stayed a `pandas.Series` when the caller passed a Series and became an `ndarray` when the caller
passed an array, and `excess.std()` then used `pandas.Series.std()`'s default **`ddof=1`** in the
first case and `numpy.ndarray.std()`'s default **`ddof=0`** in the second. The information ratio and
`excess_vol_annual` were therefore a function of *how the caller stored its data*, not of the data:
the same strategy and benchmark compared as an array and as a Series produced two different
information ratios, differing by exactly `sqrt(n / (n - 1))` (0.2650139223426122 against
0.2646824476383493 at `n = 400`).

Two further container dependencies were found in the same function and closed by the same change:

- **`alpha_annualized`** used `strat.mean()` / `bench.mean()`, and `pandas.Series.mean()` is a
  *different reduction* from `numpy.ndarray.mean()` whenever pandas is built with bottleneck
  (bottleneck's `nansum` is not numpy's pairwise sum). The value was environment-dependent.
- **the excess series itself**: `pandas.Series - pandas.Series` aligns on the **INDEX**, while
  `ndarray - ndarray` subtracts **POSITIONALLY**. The function has always aligned the two sides by
  *length* (`min_len`, tail alignment), so the index alignment was never what its contract meant —
  and for a mismatched index the old subtraction silently introduced NaNs that the `valid` mask (built
  before it) could not see.

### The fix

Both sides are reduced to float numpy arrays once, up front; the tail alignment, the pair-wise NaN
mask, the CAPM `beta`/`alpha` path (already explicit at `ddof=1`) and the `scipy` t-test are
unchanged. The result is that a `pandas.Series` and an `ndarray` holding the same numbers produce
**bit-identical** values for **all nine keys** — asserted in the new contract for the array/Series
pair, for mixed containers, for a `DataFrame` benchmark against its row-mean series, and with a NaN
row in the data.

### The convention: `ddof=0` (population) — and why

`ddof=0` is enforced. Four independent reasons, in decreasing order of how much they constrain the
choice:

1. **It keeps the larger set of published numbers unchanged.** Measured, not estimated: of the **48**
   committed artifacts that publish an `information_ratio`, **26** were produced on `ddof=0` and
   **22** on `ddof=1`. The other choice would have moved 26 published numbers instead of 22.
2. **It is this package's own convention.** `sharpe_ratio` in the same module takes
   `returns.std(ddof=0)`, and the engine's Sharpe does the same (`returns.std(ddof=0)`). A library
   whose information ratio and Sharpe ratio use different deviation conventions is a defect waiting
   to happen.
3. **It preserves an existing, deliberate contract.** `tests/test_runner_metric_agreement.py` states
   that `run_cs_momentum`'s local IR "computes `information_ratio = e.mean() / e.std() * sqrt(252)`
   with numpy `ddof=0`, **the same convention as `compare_to_benchmark`'s information_ratio**; the
   two agree exactly". That agreement held only because the test passes `.values` — it was never a
   property of the library. Enforcing `ddof=0` makes the *library* true the statement; enforcing
   `ddof=1` would have required weakening that pin.
4. **It is numpy's default**, and it is the convention under which a re-run of any runner would now
   reproduce its published IR.

### The disclosure — every published `information_ratio`, re-derived from its own artifact

Each of the 48 published values was re-derived from the artifact that published it: the strategy
series from the artifact's own `returns.parquet` / `best_equity.parquet` / `selected_equity.parquet` /
`ensemble_equity.parquet`, the benchmark from its `benchmark_returns.parquet` /
`benchmark_equity.parquet`, and the OOS window from the runner's own `TRAIN_END`. An equity curve is
inverted to a return series the way the engine builds it (`equity = (1 + r).cumprod() * capital`), so
the first bar's return is recovered rather than lost.

| Family | Artifacts | Call-site container | Published convention | n | Published IR | IR under the enforced convention | Relative change |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H1/H2 ts_momentum | 4 | ndarray | ddof=0 | 1257 | -0.1241 | -0.1241 | +0.000e+00 |
| H3/H4 cs_momentum | 2 | ndarray | ddof=0 | 1257 | -0.2523 | -0.2523 | +0.000e+00 |
| H5 regime_gated | 2 | ndarray | ddof=0 | 1257 | -0.8932 | -0.8932 | +0.000e+00 |
| H4 futures_tsmom | 4 | ndarray | ddof=0 | 1258 | -0.6399266589647274 | -0.6399266589647274 | +0.000e+00 |
| H4 ddcv | 2 | ndarray | ddof=0 | 1258 | 0.3943394550648367 | 0.3943394550648367 | +0.000e+00 |
| H6 vix_ddcv | 4 | ndarray | ddof=0 | 1258 | 0.35981069144282585 | 0.35981069144282585 | +0.000e+00 |
| H8 roll_adjusted | 1 | ndarray | ddof=0 | 1258 | 0.5248619387848141 | 0.5248619387848141 | +0.000e+00 |
| H9 v1 intraday | 1 | Series | ddof=1 | 11441 | -0.23532720855889727 | -0.2353374936142357 | +4.371e-05 |
| H9 v2 intraday | 4 | Series | ddof=1 | 11441 | 1.02096576542838 | 1.0210103870828855 | +4.371e-05 |
| H10 pfopt | 2 | Series | ddof=1 | 11441 | 1.0172449421222174 | 1.0172894011568805 | +4.371e-05 |
| H16 factor_timing | 4 | ndarray | ddof=0 | 1760 | -0.47636726658916473 | -0.47636726658916473 | +0.000e+00 |
| H17 vrp | 1 | ndarray | ddof=0 | 1700 | -0.23962730807881957 | -0.23962730807881957 | +0.000e+00 |
| H19 volume_predictive | 1 | ndarray | ddof=0 | 2958 | -0.8797993277834989 | -0.8797993277834989 | +0.000e+00 |
| H20 signed_volume | 1 | ndarray | ddof=0 | 2958 | -0.7039784403691635 | -0.7039784403691635 | +0.000e+00 |
| H21 multicontract | 1 | Series | ddof=1 | 11441 | 0.9459483422829976 | 0.9459896852756217 | +4.371e-05 |
| H22 voltarget | 5 | Series | ddof=1 | 11441 | 1.3466905696542812 | 1.3467494272216551 | +4.371e-05 |
| H23 crypto | 7 | Series | ddof=1 | 300 | 0.8001285452997962 | 0.8014654360320734 | +1.671e-03 |
| H25 pfmargin | 2 | Series | ddof=1 | 11441 | 1.3458716250016904 | 1.3459304467768110 | +4.371e-05 |

Reading of the table:

- **26 published numbers are unchanged** (`ddof=0` families) and **22 move** (`ddof=1` families), each
  by exactly `sqrt(n / (n - 1))`: **+4.371e-05** at `n = 11441` and **+1.671e-03** at `n = 300` (H23,
  the only short sample in the record). The largest movement anywhere in the published record is
  **0.17%**.
- **No sign changes**, so **no gate outcome can move**: the direction-aware gate reads
  `information_ratio > 0.0`, and `alpha_p_value` comes from `scipy.stats.ttest_1samp`, which always
  uses `ddof=1` on both paths.
- The three families whose runner published **`round(information_ratio, 4)`** (ts_momentum,
  cs_momentum, regime_gated) cannot be discriminated by the data — the two conventions differ by
  ~2e-4 relative at `n = 1257` and the published value carries only four decimals. Their convention is
  therefore pinned by the runner's **call site**, which the contract now checks statically: an
  expression that reaches a `.values` attribute hands the library an array.
- **No artifact publishes an `excess_vol_annual`** — the key is in the library's return dict but no
  committed `summary.json` carries it, so there is nothing to disclose on that side.

### What was verified

- `python -m pytest -q -W error tests/test_h51_benchmark_container_invariance.py` → **246 passed,
  12 skipped** (the 12 skips are explicit: 4 artifacts whose runner published a default `p_value`
  instead of a t-test p-value, and 8 whose IR was published rounded to four decimals).
- `python -m pytest -q -W error` → **1623 passed, 13 skipped** (full suite, up from 1377 + 1).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **94 files already formatted**.
- **The re-derivation is exact, not approximate.** For the families whose artifacts log both return
  series, the published value is reproduced to the last bit: H21 `0.9459483422829976` (residual
  0.0e+00), H22 `1.3466905696542812` (0.0e+00), H25 `1.3458716250016904` (0.0e+00), H23
  `0.8001285452997962` (4.4e-16), H16 `-0.47636726658916473` (3.2e-15), H19 `-0.8797993277834989`
  (1.6e-14), futures_tsmom `0.33150832181222434` (1.7e-16). For the families whose benchmark is only
  available as an equity curve, the residual is the float round-trip of the equity inversion and
  stays at ~1e-14 (H9 v1: 1.2e-14; H10: 9.2e-15). The published `alpha_p_value` re-derives with the
  same residual.
- **Negative control** — the contract's control reconstructs the **pre-H51 implementation** and shows
  it was container-dependent: the same data gives `0.2646824476383493` as a Series and
  `0.2650139223426122` as an array, a ratio of exactly `sqrt(n / (n - 1))`, and the pre-fix code run
  on each artifact's own data reproduces its published IR *only* under the container its runner
  passed. The fixed library returns one answer for both containers.
- The library's own call sites are unchanged, so `tests/test_runner_metric_agreement.py` and
  `tests/test_benchmark_gate_contract.py` still pass untouched — the former's "the same convention as
  `compare_to_benchmark`'s information_ratio" is now true of the library itself, not only of the
  `.values` path the test happens to exercise.

### What was not changed

No published artifact, gate threshold, verdict or certified number was modified; no grid was re-run;
no runner was touched. The `beta`/`alpha` path (`np.cov(..., ddof=1)` over `np.var(..., ddof=1)`,
which is the OLS slope) is untouched. The only change under `src/qtr` is in
`src/qtr/validation/statistics.py`, and it is confined to `compare_to_benchmark`.

### What remains unresolved

- **The 22 published `information_ratio` values on the `ddof=1` convention no longer re-derive from
  the library.** They are disclosed in the table above (moves of +4.371e-05 and +1.671e-03), not
  rewritten; the artifacts are frozen. The gate's outcome is unaffected in every case.
- The **H47 cost-attribution disclosure** (the `cost` column of the committed trade logs) covered
  less than the record does — all 41 trade logs the §H47-era scan saw carry the pre-fix
  attribution, and the disclosure was pinned for one of them. **Resolved in §H52**: the record is
  **82** trade logs, all of them carry the attribution, and all of them are pinned.
- **H9's published OOS Sharpe** is on the sample convention; disclosed and pinned, verdict frozen.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified families'
  numbers and verdicts are frozen.

## H52 — the cost-attribution disclosure now covers the whole committed record (2026-10-21)

**Verdict: the engine's per-trade attribution (§H47) is unchanged and the published record is
unaffected, but §H47's *disclosure* was narrower than the record it describes. The committed trade
logs are **82**, not the six families §H47 named; the pre-fix attribution is pinned for **every**
one of them, and the set of logs where that attribution actually changes a number is pinned
separately.**

### What changed

- `tests/test_trade_log_cost_reconciliation.py` — the frozen-record section is extended from one
  artifact to the whole record: **24 new tests** (13 → 37). Every committed trade log is named,
  classified and pinned with its measured structure; the two sub-sets — the logs where the
  pre-fix attribution *changes a number* (**70**) and the logs where it *cannot* (**7**) — are
  pinned separately, as are the **5** logs that hold no trade at all.
- `FINAL_REPORT.md` — this section, §H47's two disclosure bullets corrected, and the "Next task"
  section updated.
- **Nothing under `src/qtr` changed.** No artifact, gate threshold, verdict or certified number
  was modified; no grid was re-run; no hypothesis was added.

### The gap in §H47's disclosure (measured, not estimated)

Three things were wrong with the scope §H47 published.

1. **The scan missed half the record.** The pathspec `".experiments/artifacts/*/trades.parquet"`
   matches only the logs literally named `trades.parquet` — **41** of the **82** committed trade
   logs. The other **41** are named `best_trades`, `benchmark_trades`, `selected_trades`,
   `ensemble_trades`, `frozen_trades`, `baseline_trades`, `vix_only_trades`, `best_ddcv_trades` and
   `best_trades_w0.5`. The pathspec that sees the whole record is
   `".experiments/artifacts/*trades*.parquet"` → **82**.
2. **The family list was narrow.** The record spans **eleven** families — H3, H10, H11, H16, H17,
   H19, H20, H21, H22, H23 and H25 — across 36 artifact directories, plus **44** trade logs in 35
   exploratory artifacts that carry no `hypothesis`. §H47 named six families.
3. **The published numbers were under-counted.** §H47 disclosed the `avg_trade_cost` of "the
   three exploratory 2026-10-10 MA-crossover summaries". **Five** committed summaries publish it,
   and the tracker metadata publishes the **benchmark's** `avg_trade_cost` in **23** further
   entries — a number §H47 did not mention at all.

### The measured record

Every one of the **82** committed trade logs shares one schema
(`timestamp, symbol, side, weight_change, price, cost`) and every one records the **aggregate**
attribution: all the trades of a bar carry the bar's whole value.

| class | logs | meaning |
|---|---:|---|
| **aggregate, changes a number** | **70** | at least one bar holds more than one trade, so the bar's value was written on each of its trades |
| **aggregate, coincides** | **7** | every bar holds exactly one trade, so the bar's value *is* that trade's own cost |
| **empty** | **5** | the log holds no trade at all (the empty H23 crypto logs) |

The **repetition factor** — the recorded column's total over the total of the per-bar values — is
the factor by which the column repeats each bar's value. It is **1** exactly when no bar repeats
its value, and it runs from **1.229953** to **20.677528** over the 70 logs where the attribution
changes a number.

### Why "uniform per bar" is the *pre-fix* attribution here — three legs

1. **Provenance (decisive).** The tracker stamps every artifact id with the UTC **start** of the
   run that produced it (`exp_<UTC timestamp>`, `src/qtr/tracking/experiment.py`). Every committed
   trade log's stamp precedes **2026-10-19T18:56:58Z**, while the engine's per-trade attribution
   fix is committed in `3fbef17` (2026-10-21 11:33:35Z). No committed log was written by the
   fixed engine — and the pre-fix `_extract_trades` wrote the per-bar total, `costs[idx]`, on
   every trade of the bar.
2. **The charge anchor.** The repository's own H27 `L3` check recomputes the per-bar cost from the
   trades' `weight_change` and `price` — **never** from the `cost` column — and matches the
   engine's per-bar charge to **~1e-19** for H9, H10, H21, H22 and H25. For those families the
   per-bar recorded value *is* the charge, so the recorded column repeats the charge.
3. **The engine's own definition.** The pre-fix `_extract_trades` wrote the per-bar total on every
   trade of that bar (§H47, "The gap").

**The honest caveat.** Uniformity alone does not separate an aggregate log from a per-trade log
whose trades happen to share the same cost — a two-symbol backtest with identical signals records
the same number either way. That is precisely why the single-symbol case is the *coincides* bucket
and why leg 1 is needed; the contract's negative control shows the classifier does recognise a
per-trade log when the trades' costs differ.

### The published numbers that read the column

Exactly one place in the whole package reads the trade log's `cost` column:
`src/qtr/backtest/engine.py` → `metrics["avg_trade_cost"] = trades["cost"].mean()`. **No runner
reads it** (checked statically over `src/qtr` and every `run_*.py`).

| published number | where | count | over-stated by the pre-fix attribution |
|---|---|---:|---|
| `strategy_metrics.avg_trade_cost` | 5 artifact `summary.json` | 5 | **3** — by 1.229953×, 1.247109× and 2.868948×. The other 2 hold a single trade, so their value is exact. |
| `benchmark_avg_trade_cost_step0` | tracker metadata (`.experiments/experiments.jsonl`) | 23 | **9 verified** — 6 × **20.0×** (measured against the committed benchmark trade log) and 3 × **5×** (measured against the committed `signals_buy_and_hold.parquet`: all five symbols enter on one bar). The other **14** use a 5-contract futures benchmark whose trade log and signals were never committed, so their factor is **not measurable from the record**; they are disclosed as being on the pre-fix basis. |

One further place carries the column without publishing a number: **40** `stats.json` files echo the
head of a trade log (its first row, cost column included) as text.

**No gate, threshold, verdict or certified number reads the column.** The certified families
(H10, H22, H25) publish no `avg_trade_cost` at all, and the H11 reproduction check compares
Sharpe, profit factor, drawdown, the trade *count*, walk-forward stability and worst-regime
Sharpe — none of them is derived from the trade log's cost column.

### The contract (24 new tests)

1. **The whole record is named** — the committed trade logs (`git ls-files
   ".experiments/artifacts/*trades*.parquet"`) are exactly the **82** paths pinned here. A
   committed trade log that is not named fails the contract.
2. **The split is complete and exact** — the three pinned sets (70 / 7 / 5) partition the record;
   each is asserted to be *exactly* the measured set, so a log that moves between classes fails.
3. **The structure is pinned** — every log's trade count, bar count and multi-trade-bar count.
4. **The provenance holds** — every committed log's run stamp precedes the attribution fix's
   commit.
5. **The published numbers are pinned** — the five `avg_trade_cost` values with their repetition
   factors, the 23 benchmark entries, the verified benchmark factors and entry bars, and the fact
   that the engine metric is the *only* reader of the column.
6. **Negative control** — the classifier recognises a per-trade log (the fixed engine over two
   symbols of *different* sizes) as `"per-trade"`, the reconstructed pre-fix log as `"aggregate"`,
   and the single-symbol log as `"aggregate"` with a repetition factor of exactly **1**.

### The record, in full

| artifact | trade log | trades | bars | bars with >1 trade | repetition factor | attribution |
|---|---|---:|---:|---:|---:|---|
| `exp_2026-10-10T17-02-22-080026Z` | `trades.parquet` | 257 | 231 | 21 | 1.229953 | changes a number |
| `exp_2026-10-10T17-03-39-610858Z` | `trades.parquet` | 257 | 231 | 21 | 1.247109 | changes a number |
| `exp_2026-10-10T17-04-21-400695Z` | `trades.parquet` | 778 | 231 | 198 | 2.868948 | changes a number |
| `exp_2026-10-10T17-05-58-697503Z` | `trades.parquet` | 1 | 1 | 0 | 1.000000 | coincides |
| `exp_2026-10-10T17-07-48-008615Z` | `best_trades.parquet` | 9 | 9 | 0 | 1.000000 | coincides |
| `exp_2026-10-10T17-09-34-333145Z` | `best_trades.parquet` | 1 | 1 | 0 | 1.000000 | coincides |
| `exp_2026-10-10T20-56-30-507309Z` | `benchmark_trades.parquet` | 20 | 1 | 1 | 20.000000 | changes a number |
| `exp_2026-10-10T20-56-30-507309Z` | `selected_trades.parquet` | 1471 | 113 | 111 | 12.353926 | changes a number |
| `exp_2026-10-10T20-57-26-136503Z` | `benchmark_trades.parquet` | 20 | 1 | 1 | 20.000000 | changes a number |
| `exp_2026-10-10T20-57-26-136503Z` | `selected_trades.parquet` | 1471 | 113 | 111 | 12.353926 | changes a number |
| `exp_2026-10-10T20-59-28-306148Z` | `selected_trades.parquet` | 714 | 100 | 91 | 6.741312 | changes a number |
| `exp_2026-10-10T21-08-54-188263Z` | `benchmark_trades.parquet` | 20 | 1 | 1 | 20.000000 | changes a number |
| `exp_2026-10-10T21-08-54-188263Z` | `selected_trades.parquet` | 1471 | 113 | 111 | 12.353926 | changes a number |
| `exp_2026-10-10T21-09-06-830199Z` | `selected_trades.parquet` | 714 | 100 | 91 | 6.741312 | changes a number |
| `exp_2026-10-10T21-27-13-928282Z` | `benchmark_trades.parquet` | 20 | 1 | 1 | 20.000000 | changes a number |
| `exp_2026-10-10T21-27-13-928282Z` | `selected_trades.parquet` | 2379 | 115 | 115 | 20.677528 | changes a number |
| `exp_2026-10-10T21-28-20-920399Z` | `benchmark_trades.parquet` | 20 | 1 | 1 | 20.000000 | changes a number |
| `exp_2026-10-10T21-28-20-920399Z` | `selected_trades.parquet` | 2379 | 115 | 115 | 20.677528 | changes a number |
| `exp_2026-10-10T21-58-28-353634Z` | `ensemble_trades.parquet` | 270 | 82 | 79 | 3.492741 | changes a number |
| `exp_2026-10-10T21-59-16-546117Z` | `ensemble_trades.parquet` | 270 | 82 | 79 | 3.492741 | changes a number |
| `exp_2026-10-10T22-59-01-182037Z` | `ensemble_trades.parquet` | 356 | 82 | 80 | 4.536664 | changes a number |
| `exp_2026-10-11T00-26-35-750834Z` | `best_ddcv_trades.parquet` | 353 | 104 | 97 | 3.567370 | changes a number |
| `exp_2026-10-11T00-34-05-381535Z` | `best_ddcv_trades.parquet` | 353 | 104 | 97 | 3.567370 | changes a number |
| `exp_2026-10-11T02-44-40-301520Z` | `best_trades.parquet` | 335 | 99 | 92 | 3.627306 | changes a number |
| `exp_2026-10-11T02-44-40-301520Z` | `vix_only_trades.parquet` | 285 | 82 | 77 | 3.621090 | changes a number |
| `exp_2026-10-11T02-46-37-311994Z` | `best_trades.parquet` | 335 | 99 | 92 | 3.627306 | changes a number |
| `exp_2026-10-11T02-46-37-311994Z` | `vix_only_trades.parquet` | 285 | 82 | 77 | 3.621090 | changes a number |
| `exp_2026-10-11T07-18-39-160945Z` | `best_trades.parquet` | 335 | 99 | 92 | 3.627306 | changes a number |
| `exp_2026-10-11T07-18-39-160945Z` | `vix_only_trades.parquet` | 285 | 82 | 77 | 3.621090 | changes a number |
| `exp_2026-10-11T08-02-22-999214Z` | `best_trades.parquet` | 335 | 99 | 92 | 3.627306 | changes a number |
| `exp_2026-10-11T08-02-22-999214Z` | `vix_only_trades.parquet` | 285 | 82 | 77 | 3.621090 | changes a number |
| `exp_2026-10-11T14-52-29-891596Z` | `trades.parquet` | 441 | 176 | 100 | 3.489164 | changes a number |
| `exp_2026-10-11T14-53-13-076438Z` | `trades.parquet` | 441 | 176 | 100 | 3.489164 | changes a number |
| `exp_2026-10-11T15-21-31-333870Z` | `benchmark_trades.parquet` | 5 | 1 | 1 | 5.000000 | changes a number |
| `exp_2026-10-11T15-21-31-333870Z` | `best_trades_w0.5.parquet` | 374 | 106 | 100 | 3.648485 | changes a number |
| `exp_2026-10-11T15-53-31-819888Z` | `trades.parquet` | 31519 | 11029 | 9216 | 3.509347 | changes a number |
| `exp_2026-10-11T15-54-17-212022Z` | `trades.parquet` | 31519 | 11029 | 9216 | 3.509347 | changes a number |
| `exp_2026-10-11T16-44-06-168529Z` | `trades.parquet` | 2690 | 2176 | 368 | 1.788554 | changes a number |
| `exp_2026-10-11T16-46-06-466282Z` | `trades.parquet` | 2690 | 2176 | 368 | 1.788554 | changes a number |
| `exp_2026-10-11T16-52-38-694559Z` | `trades.parquet` | 2690 | 2176 | 368 | 1.788554 | changes a number |
| `exp_2026-10-11T17-24-14-385352Z` | `trades.parquet` | 2869 | 2320 | 391 | 1.719419 | changes a number |
| `exp_2026-10-11T17-41-18-169363Z` | `trades.parquet` | 3701 | 2975 | 513 | 1.786237 | changes a number |
| `exp_2026-10-11T18-40-37-427062Z` | `frozen_trades.parquet` | 3701 | 2975 | 513 | 1.786237 | changes a number |
| `exp_2026-10-11T20-25-36-443045Z` | `baseline_trades.parquet` | 3701 | 2975 | 513 | 1.786237 | changes a number |
| `exp_2026-10-13T21-11-45-843908Z` | `best_trades.parquet` | 413 | 129 | 129 | 3.691748 | changes a number |
| `exp_2026-10-13T21-13-09-580962Z` | `best_trades.parquet` | 413 | 129 | 129 | 3.691748 | changes a number |
| `exp_2026-10-13T21-18-23-178134Z` | `best_trades.parquet` | 338 | 129 | 129 | 2.899811 | changes a number |
| `exp_2026-10-13T21-22-02-751156Z` | `best_trades.parquet` | 338 | 129 | 129 | 2.899811 | changes a number |
| `exp_2026-10-13T21-51-45-034237Z` | `best_trades.parquet` | 1467 | 1467 | 0 | 1.000000 | coincides |
| `exp_2026-10-13T22-40-41-870350Z` | `best_trades.parquet` | 1424 | 1424 | 0 | 1.000000 | coincides |
| `exp_2026-10-13T23-06-33-191710Z` | `best_trades.parquet` | 4404 | 4404 | 0 | 1.000000 | coincides |
| `exp_2026-10-13T23-27-52-101656Z` | `trades.parquet` | 12624 | 6335 | 2897 | 2.863843 | changes a number |
| `exp_2026-10-14T07-12-35-292010Z` | `trades.parquet` | 4980 | 2695 | 830 | 2.850839 | changes a number |
| `exp_2026-10-14T07-12-59-473353Z` | `trades.parquet` | 4980 | 2695 | 830 | 2.850839 | changes a number |
| `exp_2026-10-14T07-15-23-322705Z` | `trades.parquet` | 4980 | 2695 | 830 | 2.850839 | changes a number |
| `exp_2026-10-14T07-32-43-425839Z` | `trades.parquet` | 4980 | 2695 | 830 | 2.850839 | changes a number |
| `exp_2026-10-14T08-20-16-720432Z` | `trades.parquet` | 441 | 176 | 100 | 3.489164 | changes a number |
| `exp_2026-10-14T08-20-39-255883Z` | `trades.parquet` | 2715 | 2180 | 394 | 1.790820 | changes a number |
| `exp_2026-10-14T08-26-02-537359Z` | `trades.parquet` | 1 | 1 | 0 | 1.000000 | coincides |
| `exp_2026-10-14T08-26-18-385545Z` | `benchmark_trades.parquet` | 20 | 1 | 1 | 20.000000 | changes a number |
| `exp_2026-10-14T08-26-18-385545Z` | `selected_trades.parquet` | 1471 | 113 | 111 | 12.353926 | changes a number |
| `exp_2026-10-14T08-27-02-650342Z` | `ensemble_trades.parquet` | 356 | 82 | 80 | 4.536664 | changes a number |
| `exp_2026-10-14T08-48-49-412372Z` | `trades.parquet` | 0 | 0 | 0 |  | empty |
| `exp_2026-10-14T09-28-59-592390Z` | `trades.parquet` | 0 | 0 | 0 |  | empty |
| `exp_2026-10-14T09-32-25-959733Z` | `trades.parquet` | 0 | 0 | 0 |  | empty |
| `exp_2026-10-14T09-39-07-412533Z` | `trades.parquet` | 0 | 0 | 0 |  | empty |
| `exp_2026-10-14T10-04-52-936640Z` | `trades.parquet` | 0 | 0 | 0 |  | empty |
| `exp_2026-10-14T11-53-37-996139Z` | `trades.parquet` | 107 | 60 | 42 | 1.998340 | changes a number |
| `exp_2026-10-14T18-13-09-457781Z` | `trades.parquet` | 107 | 60 | 42 | 1.998340 | changes a number |
| `exp_2026-10-14T18-52-08-943792Z` | `trades.parquet` | 4980 | 2695 | 830 | 2.850839 | changes a number |
| `exp_2026-10-14T20-02-45-189859Z` | `trades.parquet` | 3056 | 1424 | 570 | 3.038720 | changes a number |
| `exp_2026-10-14T20-08-34-613690Z` | `trades.parquet` | 3056 | 1424 | 570 | 3.038720 | changes a number |
| `exp_2026-10-19T18-56-08-872500Z` | `trades.parquet` | 441 | 176 | 100 | 3.489164 | changes a number |
| `exp_2026-10-19T18-56-58-553612Z` | `trades.parquet` | 441 | 176 | 100 | 3.489164 | changes a number |
| `exp_2026-10-19T15-46-16-261803Z` | `trades.parquet` | 3701 | 2975 | 513 | 1.786237 | changes a number |
| `exp_2026-10-19T16-41-44-683912Z` | `trades.parquet` | 3820 | 3090 | 539 | 1.676227 | changes a number |
| `exp_2026-10-19T17-38-03-570526Z` | `trades.parquet` | 12624 | 6335 | 2897 | 2.863843 | changes a number |
| `exp_2026-10-19T17-38-21-389139Z` | `trades.parquet` | 12669 | 6443 | 2846 | 2.812987 | changes a number |
| `exp_2026-10-19T17-38-39-157337Z` | `trades.parquet` | 4980 | 2695 | 830 | 2.850839 | changes a number |
| `exp_2026-10-19T17-38-50-887609Z` | `trades.parquet` | 5262 | 2754 | 903 | 2.912672 | changes a number |
| `exp_2026-10-19T17-39-02-719690Z` | `trades.parquet` | 3056 | 1424 | 570 | 3.038720 | changes a number |
| `exp_2026-10-19T17-39-12-729639Z` | `trades.parquet` | 3160 | 1465 | 593 | 3.048129 | changes a number |

(The **h28** rows are the re-certification runs under
`.experiments/artifacts/h28_causal_recertification/runs/`; the artifact id is the run's own
timestamp, so the provenance stamp is read from the last path segment.)

### What was verified

- `python -m pytest -q -W error tests/test_trade_log_cost_reconciliation.py` → **37 passed**
  (13 before this session; the 24 new tests are the scope, published-number and negative-control
  sections above).
- `python -m pytest -q -W error` → **1647 passed, 13 skipped** (full suite, up from 1623 + 13).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **94 files already formatted**.
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` → `src/qtr` = **1055
  statements, 318 branches, 0 missed, 0 partial, 100.00%**; *"Required test coverage of 100.0%
  reached. Total coverage: 100.00%"* — unchanged, because nothing under `src/qtr` changed.
- **The measurement is a read of the frozen artifacts** — no pipeline re-execution, no network, no
  grid re-run. Every number in the table above was measured from the committed parquet files
  themselves, and every published value was checked against the artifact that published it.
- **The negative control is behavioural**, not an API check: the classifier is shown to answer
  `"per-trade"` for a log the fixed engine wrote and `"aggregate"` for the pre-fix reconstruction
  of the same data.

### What remains unresolved

- **The 14 benchmark `avg_trade_cost` entries** whose benchmark trade log and signals were never
  committed are on the pre-fix basis (same engine commit) but their over-count factor is **not
  measurable from the record**. They are disclosed, not quantified.
- **The three published `avg_trade_cost` values** over-stated by the pre-fix attribution remain
  published as they are; the artifacts are frozen and no gate reads them.
- **The 22 published `information_ratio` values** on the `ddof=1` convention no longer re-derive
  from the library (§H51); disclosed, not rewritten.
- **H9's published OOS Sharpe** is on the sample convention; disclosed and pinned, verdict frozen.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified
  families' numbers and verdicts are frozen.
