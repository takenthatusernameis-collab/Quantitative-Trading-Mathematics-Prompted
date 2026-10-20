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
- **Test suite:** 748/748 passing (including the 17-test H25 Robustness audit — 12 i.i.d. bootstrap + 5 block-bootstrap sensitivity — the 23-test H25 regression set, the 44-test H26 scale-audit set, the 36-test H27 level-audit set, the 47-test H28 re-certification set and the 36-test H29 sweep set, plus the 2 new H31 `compare_to_benchmark` DataFrame/ndarray regression tests, plus the 6 new H32 `deflated_sharpe_ratio` + `purged_kfold_splits`/`combinatorial_purged_cv` regression tests, plus the 12 new H33 benchmark-contract tests, plus the 10 new H34 direction-aware benchmark-gate tests, plus the 11 new H35 gate-vacuity contract tests and the 1 new H35 one-sided-vs-gate non-equivalence test).
- **Coverage (corrected by H33, re-measured by H34):** the H33 baseline of **94%** was caused by the dead `deflated_sharpe_ratio` body (16 uncovered statements in `src/qtr/validation/statistics.py`). H34 **deleted** that dead code (it was not exported, had no caller and duplicated `run_h12_selection_bias_audit.py:deflated_sharpe_ratio` with the same `max_z` formula), and the measured coverage is now **100%** — `src/qtr` has **1010 statements, 0 missed** (`python -m pytest --cov=qtr --cov-report=term-missing`), with H34's new gate helper fully covered. (The H32 handoff's "99%, one uncovered branch" claim was wrong: its named guard — the `walk_forward_splits` empty-window branch at `statistics.py:159-160` — is covered by `tests/test_statistics.py:185`.)
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

## Next Task (updated 2026-10-20, after H35)

**H34 and its follow-up are complete, and H35 has closed the last open gate-defect class.
No further task is assigned.** The three items H34 left behind were finished in the session
that followed it (the artifact-adjacent assertions for H20 and H23 now assert the *disclosed*
state, the tally impact is pinned in `tests/test_benchmark_gate_contract.py`, and the
`Summary statistics` bullets were re-baselined); **H35** then audited the remaining gate
class — gates that are a constant, or that compare a placeholder, and can therefore never
fail — found three of them (H7 ×2, H18 ×1), disclosed them, and pinned them with an
executable contract.

The state a next session inherits:

- The pre-registered free-data hypothesis space (H1–H30) remains **exhausted**; no new
  hypothesis is warranted and no grid may be re-run.
- The certified families (H10, H22, H25) are unchanged, and **no certified family owns a
  non-evaluating gate** — the H35 audit covers every gate site in the repository.
- Every published artifact, threshold, verdict and certified number is frozen. Every
  recomputed number in this report is a **disclosure**, not a rewrite.
- Two small, self-contained items remain open and are listed in `NEXT_TASK.md`:
  the library's informational `alpha_p_value_one_sided` field (kept, but explicitly *not* the
  gate's statistic — a one-sided 5% test is a two-sided 10% test and is therefore **looser**
  than the published gate), and the reproduction of the `ruff` verification step from the
  declared dependency set (ruff is used throughout this record but is not declared in
  `pyproject.toml`/`requirements.txt`).

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
