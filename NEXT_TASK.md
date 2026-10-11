# Next Task: Pivot from Momentum Family — Intraday Futures / Roll-Yield / Multi-Horizon

## Status of H6 (executed 2026-10-11, REJECTED)

H6 (VIX+DDCV combo on futures TSMOM) was executed and **rejected** (6/8 gates fail). The combination achieved the **best metrics of the entire momentum family** on free daily data:
- OOS Sharpe **0.708** (highest across H1–H6)
- Max DD **−19.7%** (lowest across H1–H6)
- Walk-forward stability **0.803** (PASS — only variant to pass)
- Information ratio **0.360** (PASS)
- Profit factor 1.160, 188 trades

However, neither the Sharpe ≥ 1.0 gate nor the DD ≤ 15% gate clears. The DDCV layer added only **0.3% incremental DD reduction** on top of the VIX gate (VIX-only DD −20.0% → VIX+DDCV −19.7%), making it effectively redundant when regime gating is present. The remaining gap is a **signal-strength ceiling** on 2015–2024 free daily data.

**Key H6 finding:** The VIX-gate ablation (H5c) remains the single best result: Sharpe 0.711, DD −20.0%. Six hypotheses (H1–H6) tested across ETFs, futures, CS, TS, regime-gated, vol-conditioned, and combined variants — all REJECTED. The momentum family is **exhausted on free daily data**.

---

## Mission

The evidence establishes a hard floor: no momentum-family variant on 2015–2024 free daily data can certify the PROMPT_V2 gates. To make further progress, the research must pivot to one of the **invalidation pathways** identified in H4–H6 root-cause attribution:

1. **Higher-frequency (intraday) futures data** enabling CT-style path-dependent trend following with stops, dynamic position management, and true intraday vol targeting.
2. **Futures roll-yield model** capturing true roll-date P&L (the `=F` continuous contracts smooth/mask the roll edge that is the primary return source for managed futures).
3. **Dynamic multi-horizon signal** (e.g., combining 252-day and 63-day momentum with regime-weighted blending) that survives 2020/2022 stress without manual gating.
4. **Extended sample** including pre-2015 decades where TSMOM literature reports stronger edges (the 2015–2024 window includes two major momentum crashes and a 10-year equity bull unfavorable for trend-following).

---

## Recommended Next Hypothesis: H7 — Intraday Futures TSMOM with Path-Dependent Exits

**H7**: Apply a multi-horizon TSMOM signal (252-day + 63-day blend) on **intraday futures data** (1-minute or 5-minute bars for ES, NQ, CL, GC, ZB) with **path-dependent exit rules** (trailing stop, time stop, volatility stop) so that:

- Signal: weighted blend of slow (252-day) and fast (63-day) momentum, regime-weighted by realized vol.
- Entry: monthly rebalance at market open (or intraday VWAP).
- Exit: intraday trailing stop (e.g., 2× ATR from entry), time stop (max 5 days), vol stop (realized vol > 2× target).
- Cost model: realistic futures per-contract costs + slippage model calibrated to intraday spreads.
- Gates: same PROMPT_V2 set (Sharpe ≥ 1.0, DD ≤ 15%, etc.) on protected OOS.

**Null (H0):** Intraday multi-horizon TSMOM with path-dependent exits OOS Sharpe ≤ 1.0 OR max DD > 15%.

### Pre-registered design

- **Universe**: ES, NQ, CL, GC, ZB (CME/ICE continuous front-month).
- **Data source**: Databento (free tier) or similar for 1-min/5-min bars; or synthetic intraday from daily OHLC + volatility scaling (documented limitation).
- **Splits**: Train 2018-2020, Val 2021-2022, Test 2023-2024 (protected). If data starts later, adjust proportionally.
- **Base signal**: `vol_scaled_tsmom_signals` extended to multi-horizon:
  - `w_slow = sign(mom_252) / vol_63`
  - `w_fast = sign(mom_63) / vol_21`
  - Blend weight = `1 / (1 + realized_vol / target_vol)` (more fast weight in high vol).
- **Path-dependent exits** (applied per-position, intraday):
  - Trailing stop: `max(price_since_entry) - 2 * ATR_14` for longs.
  - Time stop: flatten after 5 trading days if not stopped.
  - Vol stop: flatten if 5-day realized vol > 2 × target_vol.
- **Selection**: single pre-registered config (no grid on Test); Val for gate eval only.
- **Gates**: unchanged PROMPT_V2.
- **Compute budget**: ≤ 4 CPU-h. Seed 42.

### Fallback / Ablation plan

If intraday data is unavailable or the experiment exceeds compute budget:

1. **Synthetic intraday from daily**: Use daily OHLC + Parkinson/Garman-Klass vol estimator to simulate intraday paths (Monte Carlo, 100 paths per day) — documented approximation.
2. **Roll-yield capture**: Build a `roll_adjusted_returns` series from daily `=F` contracts by detecting roll dates (volume/OI shifts) and adding the roll carry (next contract price - front contract price) / front price. Test whether roll-adjusted TSMOM improves Sharpe.
3. **Multi-horizon on daily**: Test 252+63 blend with regime-weighted blending on daily data (lower compute) as a stepping stone.

---

## Constraints (unchanged)

- Do **not** weaken evidence gates; they survived H1–H6 intact.
- Do not optimize against Test; Val/Test used only for gate evaluation.
- Test never enters selection.
- Preserve all negative results.
- No live trading, no secrets, no paid data (use Databento free tier or public sources).
- Max 4 CPU-h per experiment.
- Regression tests must pass before finishing (`python3 -m pytest tests/ -q` — currently 38 passing).

---

## Context for the Next Agent

### Summary of H1–H6 (all REJECTED)

| Exp | Strategy | OOS Sharpe | Max DD | IR | Status |
|-----|----------|-----------|--------|----|--------|
| H1 | TSMOM (20 ETFs) | 0.093 | −34.8% | −0.124 | REJECTED |
| H2 | CS Momentum (10 ETFs) | 0.116 | −38.7% | −0.252 | REJECTED |
| H3 | VIX-gated + VXX hedge | −0.868 | −48.3% | −0.893 | REJECTED |
| H4 | Futures TSMOM (ensemble) | 0.376 | −47.4% | +0.332 | REJECTED |
| H5 | DDCV on Futures TSMOM | 0.509 | −35.3% | +0.394 | REJECTED |
| H5c | VIX-gate ablation | **0.711** | **−20.0%** | +0.39 | best ablation |
| H6 | VIX+DDCV combo | **0.708** | **−19.7%** | +0.360 | best overall |

### Key architectural notes (preserved for continuity)

- Canonical TSMOM signal: `src/qtr/strategies/baselines.py::vol_scaled_tsmom_signals` (sign invariant pinned by `tests/test_tsmom_signal.py`).
- Backtest engine cost model corrected (equity costs in bps of portfolio value; futures per-contract with multiplier/tick_value).
- Data cached at `.cache/data/` (Yahoo `=F` continuous futures, `^VIX`).
- Experiment tracking via `src/qtr/tracking/experiment.py` (JSONL + Parquet, full reproducibility metadata).
- Start experiment scripts from repo root — adds `src/` to Python path internally.

### The central research question for H7

**Can intraday path-dependent exits (stops, time limits, vol limits) on a multi-horizon momentum signal overcome the signal-strength ceiling observed on daily data?** The daily-frequency VIX+DDCV combo (H6) is the best possible vol-management overlay on daily data — it achieves the highest Sharpe (0.708) and lowest DD (−19.7%) in the family but cannot breach the gates. The only remaining degrees of freedom are **signal frequency** (intraday vs daily) and **exit mechanics** (path-dependent vs monthly rebalance). H7 tests whether this pivot can invalidate the rejection.

---

## Deliverables for Next Agent

1. `run_h7_intraday_tsmom_experiment.py` — H7 pipeline + gates (reuses `vol_scaled_tsmom_signals`, `run_backtest`, `compare_to_benchmark`; adds intraday data fetcher, path-dependent exit engine).
2. Artifacts in `.experiments/artifacts/exp_<H7>/`.
3. Updated `HYPOTHESIS_SPEC.md` (append H7) and `INEFFICIENCY_RANKING.md`.
4. Final verdict: PASS all gates, or REJECT with root-cause attribution (preserve all negative results).
5. All 38 regression tests passing.