# Next Task: H4 — Futures Time-Series Momentum + Ensemble Selection

## Mission

The momentum family is **exhausted on free daily ETF data**: H1
(TSMOM, OOS Sharpe 0.093), H2 (CS momentum, 0.116), and H3
(regime-gated, -0.868) were all REJECTED against the unchanged
PROMPT_V2 gates. The dominant, cross-cutting failure mode is
**train→OOS decay** (selection on 2015-2019 daily ETF data
selects noise), not the crash problem — H3 proved the
regime-gating *mechanism* works (2020-03 DD -1.5%, 2022 DD
-2.7%) but the underlying signal has no positive OOS alpha on
this sample (alpha -11.98%/yr, IR -0.89).

TSMOM's literature edge (Moskowitz, Ooi & Pedersen 2012) is
measured on **58 futures contracts**, not ETFs. Pivot to the
asset class where the edge was discovered, and fix the
selection process that keeps producing train→OOS decay.

## Current State (completed)

- ✅ H1/H2/H3 executed and REJECTED; artifacts in
  `.experiments/artifacts/` (`exp_2026-10-10T21-08-54-188263Z`,
  `exp_2026-10-10T21-09-06-830199Z`, `exp_2026-10-10T21-28-20-920399Z`).
- ✅ Cost-model units bug fixed and locked by regression tests
  (`tests/test_cost_model.py`, `tests/test_backtest_engine.py` —
  28 tests, all passing; run `python3 -m pytest tests/ -q`).
- ✅ Regime-gating infrastructure (VIX regimes, crisis hedge
  plumbing) exists in `run_regime_gated_momentum_experiment.py`.
- ✅ Stressed-cost, bootstrap CI, BH multiple-testing, and
  benchmark-comparison pipelines all wired into the H3 runner.
- ❌ **Futures layer NOT built** (deferred from Phase 4):
  yfinance `=F` tickers not fetched; the engine's Futures cost
  path (`engine.py:215-221`) is a stub that assumes 1 contract
  per unit weight — materially wrong for real futures sizing.

## Root-Cause Summary (why the ETF momentum family failed)

1. **Train→OOS decay** (dominant): argmax selection on 5 years
   of daily data fits noise. H3 added an overfit-guard penalty
   (robust z of train Sharpe/train-vol) — it did not trigger;
   mean-of-fold WF Sharpe is too noisy a selection criterion.
2. **No positive alpha**: every variant's OOS alpha vs equal-weight
   is ≈ 0 or negative (H1 p=0.78, H2 p=0.57, H3 p=0.046 with
   IR **-0.89**).
3. **ETF-specific**: TSMOM's edge is a futures phenomenon
   (diversified across 50+ contracts, roll-return driven);
   a 20-ETF book is too concentrated and too correlated.

## Next Experiment — H4: Futures TSMOM with Ensemble Selection

### Hypothesis
Volatility-scaled TSMOM on liquid futures (ES, NQ, CL, GC, ZB),
selected by **ensemble** (equal-weight average of the top-K
configs' weights, K pre-registered) rather than argmax,
generates net pooled OOS Sharpe ≥ 1.0 with ≥ 200 trades,
PF ≥ 1.3, max DD ≤ 15%, worst-regime Sharpe ≥ 0.3, ±20%
perturbation robust, significant positive alpha vs an
equal-weight futures benchmark (p < 0.05, IR > 0).

**Null (H0):** ensemble futures TSMOM Sharpe ≤ benchmark in OOS.

### Required infra work (do this first)
1. **Futures data** via yfinance `=F` continuous tickers
   (`ES=F`, `NQ=F`, `CL=F`, `GC=F`, `ZB=F`; add `ZN=F`, `TY=F`,
   `SI=F`, `HG=F`, `KC=F`, `JB=F` if available). Document the
   roll-adjustment limitation (Yahoo continuous futures are
   spliced; roll-date drift biases long-horizon returns —
   quantify it if possible, else state it as a limitation).
2. **Fix the engine's Futures cost path** (`src/qtr/backtest/engine.py`):
   per-contract dollar cost (`future_cost_per_contract()`) must be
   converted to a capital fraction via actual contract sizing
   (`weight * portfolio_value / (price * multiplier)`), not the
   current 1-contract-per-unit-weight stub. Add regression tests
   in `tests/test_backtest_engine.py` (extend the existing
   `TestOtherAssetClasses`).
3. **Ensemble selection**: pre-register K (e.g. 5); average the
   monthly weights of the top-K configs by train WF Sharpe. This
   directly attacks the train→OOS decay (argmax overfits; ensembles
   average out selection noise). Keep the overfit-guard penalty.

### Design (minimum viable)
- Universe: 5-10 liquid futures across equity index, energy,
  metals, rates. `^VIX` for regimes (optional gating ablation —
  H3 showed gating helps crashes; test it as an ablation, not a
  requirement).
- Splits: Train 2015-2019, Val 2020-2021, Test 2022-2024
  (protected) — unchanged.
- Signal: same vol-scaled TSMOM construction (lookback, skip,
  long/short, vol target 15%), monthly rebalance.
- Grid: same families as H1 (lookback ∈ {63,126,252} × skip ∈
  {1,5,21} × long_only ∈ {T,F}), plus ensemble-vs-argmax as a
  pre-registered ablation arm.
- Gates: unchanged PROMPT_V2 set (Sharpe ≥ 1.0, ≥ 200 trades,
  PF ≥ 1.3, DD ≤ 15%, WF stability ≥ 0.7, ±20% perturbation,
  worst-regime Sharpe ≥ 0.3, benchmark p < 0.05 **and IR > 0**).
- Compute budget: ≤ 2 CPU-h. Seed 42.

### Deliverables
1. `run_futures_tsmom_experiment.py` — H4 pipeline + gates.
2. Engine futures-cost fix + regression tests (must not regress
   the corrected equity/crypto paths).
3. Updated `HYPOTHESIS_SPEC.md` (append H4) and
   `INEFFICIENCY_RANKING.md` (futures ranking entry).
4. Artifacts in `.experiments/artifacts/exp_<H4>/`.
5. Final verdict: PASS all gates, or REJECT with root-cause
   attribution (preserve all negative results).

### Fallback (if `=F` data is unavailable on Yahoo)
Run the **ensemble-selection ablation** on the existing 20-ETF
universe (argmax vs top-K ensemble, H1 grid): a cheap, decisive
test of whether selection noise — not the signal family — caused
the train→OOS decay. Document the data limitation either way.

## Constraints (unchanged)

- Do **not** weaken evidence gates; they survived H1-H3 intact.
- Do not optimize against Test; Val/Test used only for gate
  evaluation. Test never enters selection.
- Preserve all negative results (H1, H2, H3 rejected — keep them
  in the spec and ranking).
- No live trading, no secrets, no paid data.
- Max 2 CPU-h per experiment.
- Regression tests must pass before finishing
  (`python3 -m pytest tests/ -q`).

## Bottleneck Ownership

- *Infrastructure* → futures cost path + `=F` data (this task).
- *Selection process* → ensemble vs argmax ablation (this task).
- *Signal family* → futures TSMOM (the asset class where the
  literature edge lives). If H4 is also rejected, the evidence
  supports a **process** conclusion: free daily data +
  walk-forward argmax selection cannot certify a Sharpe ≥ 1.0
  edge on this timeline, and the research agenda should shift
  to either (a) higher-frequency data (paid, out of scope), or
  (b) accepting that the PROMPT_V2 gates are not certifiable
  with the available data — documented as an honest negative
  result, not a gate weakening.
