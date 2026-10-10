# Next Task: H5 — Drawdown-Conditioned Vol Targeting (DDCV) on Futures TSMOM

## Status of H4 (executed 2026-10-10, REJECTED)

H4 was executed and **rejected**. A sign-inversion bug in the first H4 run
(signal was `w = -mom/vol`, i.e. mean-reversion instead of trend-following)
was found and fixed; the canonical TSMOM was moved to the shared library
`src/qtr/strategies/baselines.py::vol_scaled_tsmom_signals` and pinned by
`tests/test_tsmom_signal.py` (38 tests, all passing). Corrected H4 result:
ensemble OOS Sharpe 0.376, best single combo 0.786, IR 0.33, but DD −47%
and 177 trades — fails all gates. Full attribution in
`HYPOTHESIS_SPEC.md` (H4 section) and artifact
`exp_2026-10-10T22-59-01-182037Z`.

## Mission

The momentum family is **exhausted on free daily data**: H1 (TSMOM,
OOS Sharpe 0.093), H2 (CS momentum, 0.116), H3 (regime-gated, −0.868),
and now H4 (futures TSMOM + ensemble, 0.376) were all REJECTED against the
unchanged PROMPT_V2 gates. The corrected H4 is the **closest to passing yet**
(best single combo OOS Sharpe 0.786, IR 0.33, positive alpha) — and its
dominant remaining failure is **max drawdown (−47% vs ≤15% gate)**, not
signal direction. The signal is now correct and trend-following; what
remains is a **drawdown-control mechanism**.

## Hypothesis H5: Drawdown-Conditioned Vol Targeting (DDCV)

**H5**: Apply a drawdown-conditioned volatility target to the corrected
futures TSMOM (best H4 combo: long-only, lookback 252, skip 1, OOS Sharpe
0.786, IR 0.33) so that when the portfolio is in a drawdown from its
rolling peak, the target volatility is **reduced** (e.g. halved), and when
recovered it is restored to the base 15%. This directly attacks the
dominant H4 failure (max DD −47% vs ≤15% gate) without touching the
signal or the selection process.

**Null (H0):** DDCV futures TSMOM OOS Sharpe ≤ 1.0 OR max DD > 15%.

### Pre-registered design

- **Universe**: ES=F, NQ=F, CL=F, GC=F, ZB=F (unchanged; all 5 available).
- **Splits**: Train 2015-2019, Val 2020-2021, Test 2022-24 (protected).
- **Base signal**: `vol_scaled_tsmom_signals` from
  `src/qtr/strategies/baselines.py` (long_only=True, lookback=252, skip=1,
  target_vol=0.15) — the corrected H4 best combo.
- **DDCV mechanism** (pre-registered, applied *after* signal construction,
  before the engine): compute the portfolio equity curve from the base
  signals, then per day:
  ```
  dd = equity / equity.rolling(peak_window).max() - 1.0   # ≤ 0
  vol_target_day = base_target_vol * (1.0 - dd_dd_factor * max(0, -dd).clip(0, dd_trigger))
  ```
  with pre-registered grid over `dd_trigger` ∈ {0.10, 0.20, 0.30} and
  `dd_factor` ∈ {0.5, 0.75} (how much to cut the vol target in a DD).
  The scale is applied to the whole book (same as the existing
  portfolio-level vol targeting inside `vol_scaled_tsmom_signals`).
- **Selection**: single pre-registered combo (no grid search on Test);
  Val used only for gate evaluation. Train→OOS decay is *not* the target
  of H5 — the signal is fixed at the H4 best.
- **Gates** (unchanged PROMPT_V2): Sharpe ≥ 1.0, ≥ 200 trades, PF ≥ 1.3,
  DD ≤ 15%, WF stability ≥ 0.7, ±20% perturbation, worst-regime Sharpe
  ≥ 0.3, benchmark p < 0.05 **and IR > 0**.
- **Compute budget**: ≤ 2 CPU-h. Seed 42.

### Deliverables

1. `run_ddcv_experiment.py` — H5 pipeline + gates (reuses
   `vol_scaled_tsmom_signals`, `run_backtest`, `compare_to_benchmark`).
2. Artifacts in `.experiments/artifacts/exp_<H5>/`.
3. Updated `HYPOTHESIS_SPEC.md` (append H5) and `INEFFICIENCY_RANKING.md`.
4. Final verdict: PASS all gates, or REJECT with root-cause attribution
   (preserve all negative results).

### Fallback

If DDCV cannot bring max DD ≤ 15% without destroying Sharpe, run the
**ablation**: compare DDCV against (a) base TSMOM, (b) a fixed 50%
vol-target cut (no DD condition), (c) VIX-gated vol target (H3-style).
This isolates whether the DD condition itself adds value over a blunt
vol cut. Document the result either way.

### Constraints (unchanged)

- Do **not** weaken evidence gates; they survived H1-H4 intact.
- Do not optimize against Test; Val/Test used only for gate evaluation.
- Test never enters selection.
- Preserve all negative results.
- No live trading, no secrets, no paid data.
- Max 2 CPU-h per experiment.
- Regression tests must pass before finishing
  (`python3 -m pytest tests/ -q` — currently 38 passing).