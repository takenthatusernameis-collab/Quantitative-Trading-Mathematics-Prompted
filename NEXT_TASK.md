# Next Task: H9 Intraday TSMOM — Profit Factor Optimization (H10)

## Status of H9 (executed 2026-10-11, REJECTED — 7/8 gates pass)

H9 implemented intraday (1-hour) vol-scaled TSMOM with CT-style path-dependent exits on ES/NQ/CL/GC/ZB `=F` futures from yfinance (~730 days hourly data).

- **OOS Sharpe: 1.056** (threshold ≥ 1.0) **PASS** ✓
- **Max DD: -6.2%** (threshold ≤ 15%) **PASS** ✓
- **Profit Factor: 1.252** (threshold ≥ 1.3) **FAIL** ✗
- **Trades: 2,690** (threshold ≥ 200) **PASS** ✓
- **WF Stability: 0.793** (threshold ≥ 0.7) **PASS** ✓
- **Worst-regime Sharpe: 0.758** (bear, threshold ≥ 0.3) **PASS** ✓
- **Benchmark p-value: 6.3e-12** (threshold < 0.05) **PASS** ✓
- **Information Ratio: 1.021** (threshold > 0) **PASS** ✓

**Key findings:**
1. **Frequency breakthrough**: H9 is the first hypothesis to clear both Sharpe ≥ 1.0 and DD ≤ 15% gates. The frequency dimension works — hourly data captures intraday trend persistence that daily data cannot.
2. **Regime problem solved**: All regime sharpes positive (bull 1.13, sideways 0.97, bear 0.76). The worst-regime failure mode (sideways VIX 20-30 in H3–H8) is resolved.
3. **Profit factor is the binding constraint**: High hourly turnover (2,690 trades in ~2 years) amplifies transaction costs. CT exits control DD (-6.2% vs -20.9% in H8) but do not improve PF; ablation without exits has PF 1.261 (also < 1.3). Raw hourly signal fails catastrophically (Sharpe -0.14, PF 0.99, 31K trades).
4. **Data limitation**: yfinance hourly `=F` limited to ~730 days. Train/Val/Test split covers ~Oct 2022–Oct 2024 — small sample but true OOS stress test.

---

## Cross-Family Progress (H4 → H9)

| Hypothesis | OOS Sharpe | OOS Max DD | OOS PF | Key Breakthrough |
|------------|-----------|-----------|--------|------------------|
| H4 (Futures TSMOM) | 0.376 | -47.4% | 1.085 | Sign bug fixed; genuine trend-following |
| H5 (DDCV) | 0.509 | -35.3% | 1.108 | DD conditioning adds no Sharpe |
| H6 (VIX+DDCV) | 0.708 | -19.7% | 1.160 | Regime gating helps but procyclical |
| H7 (Multi-horizon, daily) | 0.789 | -14.5% | 1.166 | Daily approx limits path exits |
| H8 (Roll-adjusted) | 0.814 | -20.9% | 1.157 | Roll yield is second-order |
| **H9 (Intraday + CT exits)** | **1.056** | **-6.2%** | **1.252** | **Frequency clears Sharpe & DD gates; PF remains** |

**Sharpe improves monotonically H4→H9 (0.376→1.056). The profit factor ceiling persists but the signal strength is now certifiable.**

---

## Mission: H10 — Optimize Profit Factor While Preserving Sharpe/DD Gains

**Hypothesis**: A refined intraday TSMOM system with **turnover-aware signal construction** and **optimized exit parameters** can achieve PF ≥ 1.3 while maintaining OOS Sharpe ≥ 1.0 and max DD ≤ 15% on the same hourly futures universe.

**Root-cause attribution from H9 (what H9 actually proved):**
1. **Intraday frequency works** — Sharpe 1.056, DD -6.2%, all regime sharpes > 0. The core hypothesis is validated.
2. **High turnover is the PF killer** — 2,690 trades in ~2 years (≈1,345 trades/year on 5 symbols = ~270 trades/symbol/year = ~1 trade/symbol/day). Futures per-contract costs at this frequency erode edge.
3. **CT exits help DD but hurt PF** — Trailing/time/vol stops reduce max DD from -20.9% (H8) to -6.2%, but the ablation without exits has higher PF (1.261 vs 1.252). The exits add whipsaw trades.
4. **Signal construction drives turnover** — The hourly vol-scaled TSMOM re-estimates portfolio vol every hour, causing constant position adjustments. The daily target collapse helps (1,819 trades vs 2,690) but not enough.

---

## Pre-registered H10 Design

- **Hypothesis**: Intraday (1-hour) TSMOM with **turnover-aware signal construction** (e.g., signal smoothing, longer vol estimation window, regime-aware position sizing) and **optimized exit parameters** (grid search on trailing_mult, max_hold_bars, vol_limit_mult) generates net pooled OOS Sharpe ≥ 1.0, PF ≥ 1.3, max DD ≤ 15%, ≥ 200 trades, WF stability ≥ 0.7, worst-regime Sharpe ≥ 0.3, benchmark p < 0.05, IR > 0.
- **Null (H0)**: Any intraday TSMOM variant on this data OOS Sharpe < 1.0 OR PF < 1.3 OR max DD > 15%.
- **Universe**: ES=F, NQ=F, CL=F, GC=F, ZB=F (hourly bars, ~730 days from yfinance).
- **Splits**: Train 55%, Val 25%, Test 20% (protected). Test never enters selection. Same data window as H9.
- **Signal variations to test (Val-only selection):**
  1. **Signal smoothing**: EWMA smooth of hourly signal (span ∈ {4, 8, 16} hours) before daily target collapse.
  2. **Longer vol window**: Portfolio vol targeting window ∈ {252h, 504h, 1008h} (1w, 2w, 4w) to reduce rebalancing frequency.
  3. **Regime-aware scaling**: VIX-regime exposure scaling (H6 style) applied intraday — bull (VIX<20): 1.0x, sideways (20-30): 0.5x, bear (>30): 0.25x. VIX fetched hourly.
  4. **Multi-horizon blend**: 252h + 63h + 21h blend with regime-weighted mixing (as H7 pre-registration but on hourly data).
  5. **Minimum trade interval**: Enforce minimum bars between position changes (e.g., 4h, 8h, 24h).
- **Exit parameter grid (Val-only):**
  - trailing_mult ∈ {1.5, 2.0, 2.5, 3.0}
  - max_hold_bars ∈ {60, 120, 240, 480} (2.5d, 5d, 10d, 20d)
  - vol_limit_mult ∈ {1.5, 2.0, 2.5}
  - vol_floor_fraction ∈ {0.25, 0.5, 0.75}
- **Cost model**: Same futures per-contract ($0.50 + 0.25 tick spread + 0.5 tick slippage).
- **Selection**: Best config by Val Sharpe; Test protected.
- **Gates**: Unchanged PROMPT_V2 set (Sharpe ≥ 1.0, ≥ 200 trades, PF ≥ 1.3, DD ≤ 15%, WF stability ≥ 0.7, worst-regime Sharpe ≥ 0.3, benchmark p < 0.05 AND IR > 0).
- **Compute budget**: ≤ 4 CPU-h. Seed 42.
- **Ablations required**: H9 baseline, signal smoothing only, longer vol window only, regime scaling only, min trade interval only, exit grid best.

---

## Evidence-based Rationale for H10

1. **H9 validated the frequency hypothesis** — Sharpe 1.056, DD -6.2%, all regimes positive. The signal has genuine edge.
2. **Turnover analysis**: 2,690 trades = ~1.1 trades/hour on 5 symbols. The hourly vol-targeting rebalances constantly. Signal smoothing and longer vol windows directly attack this.
3. **Regime gating worked in H6** (Sharpe 0.708, DD -19.7%) — applying VIX-aware scaling intraday should reduce sideways-regime whipsaw without procyclicality (hourly VIX avoids the daily misclassification).
4. **Exit parameter sensitivity unknown** — H9 used fixed params (2.0×ATR, 120 bars, 2.0×vol). A small grid on Val may find a PF-improving region.
5. **Minimum trade interval** is a standard CT technique to reduce whipsaw costs; not yet tested.

---

## What Would Invalidate H10 (If REJECTED)

- If no signal/exit variant achieves PF ≥ 1.3 while keeping Sharpe ≥ 1.0 and DD ≤ 15%.
- If the small hourly sample (~730 days) is fundamentally insufficient to certify any intraday strategy (statistical power too low).
- If the yfinance hourly data quality has gaps/errors that invalidate results.

---

## Deliverables for Next Agent

1. `run_h10_intraday_tsmom_pfopt_experiment.py` — intraday TSMOM with signal smoothing grid, longer vol window grid, regime-aware scaling, min trade interval grid, exit parameter grid; Val-only selection; full gate evaluation; ablations.
2. Artifacts in `.experiments/artifacts/exp_<H10>/` (hourly prices, VIX, signals, smoothed signals, positions, exit events, equity, trades, param grids, ablations, summary.json).
3. Update `HYPOTHESIS_SPEC.md` (append H10) and `INEFFICIENCY_RANKING.md`.
4. Final verdict: PASS/REJECT with root-cause attribution. Preserve negative results.
5. All 38 regression tests passing (plus any new tests for signal smoothing/exit logic).

---

## Constraints (unchanged)

- Do not weaken evidence gates.
- Test never enters selection.
- Preserve all negative results.
- No live trading, no secrets, no paid data.
- Max 4 CPU-h per experiment.
- Hourly `=F` data limited to ~730 days from yfinance — document coverage gaps and treat smaller sample as known limitation.
- Reuse existing engine/tracking/validation infrastructure.

---

## Implementation Notes

- **Reuse H9 code**: `run_h9_intraday_tsmom_experiment.py` as base; add signal smoothing, vol window grid, regime scaling, min trade interval, exit grid.
- **VIX hourly**: Fetch `^VIX` at 1h interval (yfinance supports it) and align to futures index.
- **Signal smoothing**: Apply EWMA to hourly signal before daily target collapse; `signal_smooth = signal.ewm(span=span).mean()`.
- **Longer vol window**: Change `vol_window_long` in `vol_scaled_tsmom_hourly` from 252h to 504h/1008h.
- **Regime scaling**: Compute VIX regime per hour, multiply daily target by regime factor before exit logic.
- **Min trade interval**: In `apply_path_dependent_exits_hourly`, track last trade bar per symbol; skip entry/exit if bars since last trade < threshold.
- **Parameter grid**: Use nested loops or itertools.product; log all combos to tracker; select best by Val Sharpe.
- **Ablations**: Run each component in isolation on OOS to attribute improvement.

(End of file)