# Next Task: Intraday Futures TSMOM with CT-Style Path-Dependent Exits (H9)

## Status of H8 (executed 2026-10-11, REJECTED)

H8 built a roll-adjusted returns series from daily `=F` continuous futures
contracts by detecting roll dates (calendar month-end + volume-shift + overnight-gap
heuristics) and adding roll carry (overnight gap = open/prev_close − 1) on detected
roll dates. TSMOM was run on the roll-adjusted price series with a grid over
roll-carry weight w ∈ {0.0, 0.25, 0.5, 1.0, 2.0}, selected by Val-only Sharpe.

- **Best config**: w=0.50 (Val Sharpe 0.900).
- **OOS Sharpe 0.814** (< 1.0), max DD **-20.9%** (> 15%), PF 1.157 (< 1.3),
  201 trades (≥ 200 ✓), WF stability 0.883 (≥ 0.7 ✓), worst-regime SR -1.914
  (< 0.3), benchmark p=0.241 (> 0.05), IR 0.525 (> 0 ✓).
- **Gates: 5/8 FAIL.** Overall **REJECT**.
- **Key finding**: Roll adjustment gives the **highest OOS Sharpe (0.814)** and
  **highest IR (0.525)** of the entire momentum family (H1–H8), but still below
  gates. The roll carry is a small, second-order effect on `=F` returns that
  already embed roll yield. The dominant failure mode remains the 2020-2022
  momentum crash (worst-regime SR -1.9 in sideways/VIX 20-30 regime).

## Cross-Family Progress (H4 → H8)

| Hypothesis | OOS Sharpe | OOS Max DD | Why REJECTED |
|------------|-----------|-----------|--------------|
| H4 (Futures TSMOM) | 0.376 | -47.4% | Signal sign bug (fixed), low Sharpe |
| H5 (DDCV) | 0.509 | -35.3% | DD conditioning adds no Sharpe |
| H6 (VIX+DDCV) | 0.708 | -19.7% | Vol mgmt ceiling, Val weak |
| H7 (Multi-horizon, daily) | 0.789 | -14.5% | Frequency limitation (daily approximation) |
| H8 (Roll-adjusted) | 0.814 | -20.9% | Roll carry is second-order; `=F` already embeds it |

The Sharpe improves monotonically H4→H8 (0.376→0.814), but the gap to 1.0
persists. Each iteration attacks a different failure mode, but the fundamental
constraint remains: **free daily `=F` data cannot certify a Sharpe ≥ 1.0 trend-
following edge on 2015-2024 futures**.

---

## Mission

**Pivot to the frequency dimension.** The most consistently documented gap
across H7 and H8 is that daily data cannot capture intraday trend persistence
and path-dependent exit opportunities. H9 will implement genuine higher-frequency
TSMOM with CT-style path-dependent exits on actual intraday bars (not daily
approximations).

YFinance supports 1-hour (`interval="1h"`) bars for futures `=F` tickers
(2020-present, limited to the most recent ~730 days). H9 will use this
intraday data to build a real CT-style trend system with:

1. **Hourly TSMOM signal**: 252-hour + 63-hour multi-horizon blend with
   regime-weighted mixing (volatility-scaled, per H7 pre-registration, but
   on actual hourly data).
2. **Path-dependent exits** (implemented on real hourly bars):
   - **Trailing stop**: exit when price drops > 2× ATR(14) from the entry
     high-water mark.
   - **Time stop**: flatten position after 5 trading days (120 hourly bars)
     if no trend progress (profit > 0).
   - **Vol stop**: reduce exposure if realized volatility over the past 20
     bars exceeds 2× the target (15% annualized).
3. **Roll-date awareness**: detect roll dates from the hourly data's
   volume/contract transitions (where available) and flag them for analysis.
4. **Cost model**: apply futures per-contract costs scaled to hourly
   turnover (higher turnover × higher costs).

### Pre-registered H9 design

- **Hypothesis**: Intraday (1-hour) vol-scaled TSMOM with CT-style path-dependent
  exits (trailing stop 2× ATR, time stop 120 bars, vol stop 2× target vol) on
  ES/NQ/CL/GC/ZB `=F` generates net pooled OOS Sharpe ≥ 1.0 with ≥ 200 trades,
  PF ≥ 1.3, max DD ≤ 15%, WF stability ≥ 0.7, worst-regime Sharpe ≥ 0.3,
  significant alpha vs equal-weight futures BH (p < 0.05, IR > 0).
- **Null (H0)**: Intraday TSMOM with path-dependent exits OOS Sharpe ≤ 1.0
  OR max DD > 15%.
- **Universe**: ES=F, NQ=F, CL=F, GC=F, ZB=F (hourly bars where available).
- **Splits**: Train 2020-2022, Val 2023, Test 2024 (protected). Test never
  enters selection. (Hourly data is limited to ~2 years from yfinance.)
- **Signal**: vol-scaled TSMOM on hourly prices (lookback=252h, skip=1h,
  long_only=True, target_vol=15% annualized). Portfolio-level vol targeting
  re-estimated hourly.
- **Exits**: trailing stop (2× ATR(14)), time stop (120 bars / 5 trading
  days), vol stop (20-bar realized vol > 2× target). Applied as daily
  position adjustments (reduce/flatten) when triggered.
- **Cost model**: futures per-contract ($0.50 + 0.25 tick spread + 0.5 tick
  slippage), scaled to higher hourly turnover.
- **Selection**: single pre-registered config (no grid on Test); Val for
  gate evaluation only.
- **Gates**: unchanged PROMPT_V2 set (Sharpe ≥ 1.0, ≥ 200 trades, PF ≥ 1.3,
  DD ≤ 15%, WF stability ≥ 0.7, worst-regime Sharpe ≥ 0.3, benchmark p < 0.05
  AND IR > 0).
- **Compute budget**: ≤ 4 CPU-h. Seed 42.

### Evidence-based rationale for H9

1. **H7 proved the design works structurally** (Test Sharpe 1.269) but was
   limited by daily approximation. The H7 pre-registration explicitly noted:
   "True intraday path-dependent execution (tick-level trailing/time/vol stops)
   remains untested with free data."
2. **H8 confirmed roll-yield capture is second-order** — the `=F` continuous
   contracts already embed roll yield. The frequency dimension is the remaining
   lever.
3. **Literature support**: CT-style trend followers (e.g., Covenant Capital,
   Winton) achieve Sharpe 1.0+ using intraday trend-following with stop-losses.
   The `run_alternatives.py` grid-search suggested "path-dependent exits may
   help."
4. **Feasibility**: yfinance 1.7.0 supports `interval="1h"` for futures.
   2020-2024 hourly data covers the COVID crash and 2022 inflation shock — a
   true out-of-sample stress test.
5. **Risk**: hourly TSMOM has higher turnover × higher costs. The cost model
   must be realistic (futures per-contract costs × higher trade frequency).

### What would invalidate H9's hypothesis (if REJECTED)

- If intraday TSMOM fails to beat daily TSMOM after costs (higher turnover
  erodes the frequency premium).
- If path-dependent exits don't improve the Sharpe/DD ratio (intraday noise
  dominates trend persistence).
- If the hourly data from yfinance has insufficient history or quality gaps.

---

## Deliverables for Next Agent

1. `run_h9_intraday_tsmom_experiment.py` — hourly TSMOM signal, CT-style
   path-dependent exits (trailing/time/vol stops), backtest with realistic
   futures cost model, and full gate evaluation. Reuse existing engine/
   tracking/validation.
2. Artifacts in `.experiments/artifacts/exp_<H9>/` (hourly prices, volume,
   signals, exit events, equity curve, trades, param grid if any, ablations,
   summary.json).
3. Update `HYPOTHESIS_SPEC.md` (append H9) and `INEFFICIENCY_RANKING.md`.
4. Final verdict: PASS/REJECT with root-cause attribution. Preserve negative
   results.
5. All 38 regression tests passing (plus any new tests for the exit logic).

---

## Constraints (unchanged)

- Do not weaken evidence gates.
- Test never enters selection.
- Preserve all negative results.
- No live trading, no secrets, no paid data.
- Max 4 CPU-h per experiment.
- Hourly `=F` data is limited to ~2 years from yfinance — document coverage
  gaps and treat the smaller sample as a known limitation.
