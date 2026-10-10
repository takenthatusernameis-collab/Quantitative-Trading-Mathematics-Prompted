# Next Task: Regime-Aware, Crisis-Resilient Momentum

## Mission
Close the *identified* failure mode of the two rejected hypotheses (H1 TS momentum,
H2 CS momentum): raw momentum fails the evidence gates on 2015-2024 liquid ETFs
because of **train→OOS decay** and catastrophic **momentum crashes in 2020/2022**
(bear-regime Sharpe ≈ -2.4 to -3.0), plus zero alpha vs the equal-weight
benchmark. Build a momentum variant that survives regime crashes and re-test
against the **unchanged** PROMPT_V2 gates (do not weaken them).

## Current State (completed)
- ✅ Infrastructure functional; **cost-model units bug fixed**
  (`src/qtr/backtest/engine.py:208`): equity/crypto cost is now
  `weight_delta * bps/1e4` (fraction of capital), not `* price * bps/1e4`.
  Verified: buy-and-hold SPY Sharpe 0.685; MA 30/200 0.655.
- ✅ `time_series_momentum` / `momentum` strategies exist; `run_ts_momentum_experiment.py`
  and `run_cs_momentum_experiment.py` implement the full walk-forward / gate pipeline.
- ✅ H1 (`exp_2026-10-10T21-08-54-188263Z`) and H2
  (`exp_2026-10-10T21-09-06-830199Z`) both **REJECTED** (artifacts in `.experiments/`).
- ✅ Reports: `MATHEMATICAL_DISCOVERY_REPORT.md`, `INEFFICIENCY_RANKING.md`,
  `HYPOTHESIS_SPEC.md`, `FINAL_REPORT.md` all finalized with real numbers.

## Root-Cause Summary (why the edges failed)
1. **Train→OOS decay**: selected params (train Sharpe 0.59–0.64) produced
   Test Sharpe -0.039 / 0.092. The 2015-2019 train window was a strong bull
   regime; walk-forward selection on train overfit.
2. **Momentum crashes**: bear regimes (VIX > 30) gave Sharpe -2.4 (H1) / -3.0 (H2).
   2020-03 and 2022 were the two largest contributors to drawdown (-34.8% / -38.7%).
3. **No alpha vs EW benchmark**: IR -0.12 / -0.25, p = 0.78 / 0.57.
4. **Crowding/decay** (theory): post-2012 CS momentum is heavily traded
   (Fleming et al. 2021).

## Next Experiment — H3: Regime-Gated, Volatility-Scaled Momentum

### Hypothesis
When the market is in a **bull regime (VIX < 20)**, volatility-scaled TSMOM on
20 liquid ETFs generates positive risk-adjusted returns; when in a **bear/sideways
regime** the strategy **reduces exposure to ≤ 25% of target vol and/or shifts to a
crisis hedge** (long volatility / short beta). Net pooled OOS (Val+Test) Sharpe
≥ 1.0 with ≥ 200 trades, PF ≥ 1.3, max DD ≤ 15%, worst-regime Sharpe ≥ 0.3,
significant vs benchmark (p < 0.05).

**Null (H0):** the regime filter is a data-mining artifact; gated Sharpe ≤
benchmark Sharpe in OOS.

### Concrete design (minimum viable)
- **Universe:** same 20 ETFs + `^VIX` + add `VXX` (short-term vol ETN) as a
  **crisis hedge** (long VXX only when VIX > 30). Document VXX's known decay
  (do NOT hold long in calm markets).
- **Signal (train-selected):** portfolio-level vol-scaled TSMOM (12-1, 6-5, 3-1),
  BUT scale = `target_vol * regime_factor`, where `regime_factor ∈ {1.0 (bull),
  0.25 (sideways), 0.10 (bear)}` derived from VIX. In bear regime, allocate a
  fixed 10% to a VXX hedge.
- **Selection:** grid over `(lookback, skip, regime_factor_triple, hedge_weight)`
  selected by **train-only walk-forward Sharpe**, with a **penalty** for
  configs whose train Sharpe / train-vol is extreme (overfit guard). Enforce
  via code that Test dates never enter selection.
- **Gates:** unchanged PROMPT_V2 set (Sharpe ≥ 1.0, ≥ 200 trades, PF ≥ 1.3,
  DD ≤ 15%, WF stability ≥ 0.7, ±20% perturbation, worst-regime Sharpe ≥ 0.3,
  benchmark p < 0.05). Additionally require **2020-03 and 2022 drawdowns ≤ 20%**
  (the regime gate).
- **Compute budget:** ≤ 2 CPU-h. Seed 42.

### Required infra work (NOT yet ready)
- **Futures/contango layer** (deferred from Phase 4): add `=F` futures tickers
  (ES, NQ, CL, GC, ZB) via yfinance and implement the engine's **Futures** cost path
  (per-contract; currently a stub). Futures are where TSMOM has real capacity.
- **Point-in-time constituents** (no survivorship bias): for SPY sub-universe.
- **Stressed-cost test** already in `qtr.validation.statistics` — use it.

### Deliverables for this task
1. `run_regime_gated_momentum_experiment.py` — H3 pipeline + gates.
2. Updated `HYPOTHESIS_SPEC.md` (append H3) and `INEFFICIENCY_RANKING.md`.
3. New `tests/test_cost_model.py` and `tests/test_backtest_engine.py` regression
   tests (the cost bug should never regress).
4. Artifacts in `.experiments/artifacts/exp_<H3>/`.
5. Final verdict: PASS all gates, or REJECT with root-cause attribution.

## Constraints (unchanged)
- Do **not** weaken evidence gates; the Sharpe/DD/PF gates survived the cost fix
  and must remain strict.
- Do not optimize against Test; Val/Test used only for final gate evaluation.
- Preserve all negative results.
- No live trading, no secrets, no paid data (futures via free yfinance `=F`).
- Max 2 CPU-h per experiment.

## Bottleneck Ownership
The previous agent's "no strategy passes" problem is now **decomposed**, not
solved:
- *Artifact* of infrastructure → fixed (cost model).
- *Real* signal weakness on this sample + regime crashes → next experiment.
