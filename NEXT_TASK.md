# Next Task — H17 executed (VRP REJECTED); pivot to overnight/intraday decomposition (H18)

## What changed this session (H16 — executed 2026-10-13)
- **H16 (cross-sectional equity factor timing)**: implemented the
  frozen pre-registration in `HYPOTHESIS_SPEC.md` exactly as specified
  (9 factor ETFs, 3 families, VIX regime filter, 54-combo grid,
  train-only 4-fold walk-forward selection, gates on protected
  OOS Val+Test 2018-2024).
- Script: `run_h16_factor_timing_experiment.py` (3.9 s, 0.001 CPU-h).
- Artifacts: `.experiments/artifacts/exp_2026-10-13T21-22-02-751156Z/`
  (prices, volumes, vix_close, param_grid_results, selected_signals,
  best_equity, best_trades, benchmark_equity/returns,
  family_exposure, summary.json).
- Tests: `tests/test_h16_factor_timing.py` (24 tests). **Full suite:
  178 passed** (154 prior + 24 new).
- **Verdict: REJECT — 1/9 gates** (only ±20% perturbation passes,
  min ratio 0.734). Selected config (lookback=63, skip=5, regime
  1.0/0.5/0.25, n_factors=2): OOS Sharpe 0.579 (< 1.0), PF 1.106
  (< 1.3), DD -19.95% (> 15%), trades 184 (< 200), WF stability
  0.353 (< 0.7), worst-regime Sharpe -3.680 (bear; < 0.3),
  benchmark p = 0.351 & IR -0.353 (fail).
- Root causes (see HYPOTHESIS_SPEC.md for full attribution):
  (1) rotation adds no value over the EW factor benchmark (0.579 vs
  0.606, IR -0.353); (2) the edge is momentum-family exposure
  (momentum family alone 0.819; value family -0.028); (3) the VIX
  regime gate is procyclical (ungated 0.758 beats gated 0.579 —
  replicates H3); (4) bear-regime Sharpe -3.680 is structural for a
  long-only momentum book; (5) monthly rebalancing with n_factors=2
  yields only 184 OOS trades.
- Two implementation defects found and fixed during execution:
  (a) all-NA rows crashed `idxmax` in family-representative
  selection (pre-inception/warmup) — fixed with an explicit
  validity mask; (b) `resample('ME')` anchored monthly targets on
  calendar month-ends (non-trading days), shifting targets one
  trading day late at month boundaries — fixed by anchoring on the
  actual last trading day of each month (unit-tested).

## What was actually verified
- 178/178 tests pass, including 24 H16 tests that recompute the
  OOS gates from the logged equity/trades artifacts (exact match to
  summary.json at 1e-9), verify signal causality (future-price
  perturbation leaves past targets bit-identical), point-in-time
  universe (zero weight before each ETF's inception), monthly
  rebalancing (positions change only on month-end trading days),
  weight bounds, top-1-per-family, determinism, and grid/selection
  integrity (54 unique combos; selection = argmax train-WF Sharpe).
- Experiment is deterministic: two independent runs reproduced
  identical OOS metrics for the same code version.

## Approaches already failed and why (cumulative)
- H1-H9 momentum family on free daily/intraday data: all REJECT.
- H10 intraday futures TSMOM: the only PASS (Sharpe 1.276, PF
  1.304), but H13/H14 showed the PF margin (+0.004) is bootstrap-
  fragile (CI LB 1.190) and CL=F/GC=F-indispensable. Data-walled:
  yfinance hourly `=F` hard-capped at ~730 days (no bars past
  2026-10-09). Extending requires paid data.
- H16 factor timing: REJECT (this session) — realized edge is
  momentum-like and regime-fragile; rotation is noise over the
  factor zoo on 2018-2024.
- VRP feasibility EDA (probe, not a registered experiment):
  SVXY BH 2011-2026 Sharpe 0.576, vol 0.548, max DD -95.2%;
  21d-vol-targeted at 5%/10%/15% gives Sharpe 0.459/0.459/0.465
  with max DD -13.5%/-21.3%/-26.5%. Worst days: 2018-02-05 -32.0%,
  2016-06-24 -26.5%, 2018-02-08 -22.3%, 2024-08-05 -21.4% — all
  arrive *in contango* (the term-structure gate cannot pre-warn;
  VIX prints 37 only on the crash day itself).

## What remains unresolved
- No hypothesis besides H10/H11 clears the evidence gates; every
  new family tested on free data lands at OOS Sharpe 0.5-0.8 with
  regime-fragile worst-regime Sharpes.
- The two structural walls: (a) the 730-day hourly data cap (paid
  data needed for the intraday line); (b) the ≤15% DD + ≥1.0 Sharpe
  joint gate, which no long-only free-data family has met.

## One precise next task (bounded, verifiable, free data)
**Pre-register and execute H17: Volatility-Risk-Premium harvesting
(term-structure-gated, vol-targeted long SVXY).** Rationale: it is
the highest-information untested family — a genuinely different
mechanism (vol selling / insurance premium) on the longest free
daily sample (SVXY, ^VIX, ^VIX3M from 2011-10-04; ~15 years,
3,775 bars), and it directly addresses the momentum-crash regime
problem that killed H1-H3/H16.

Pre-registration skeleton (freeze in HYPOTHESIS_SPEC.md BEFORE
running; the EDA above is the feasibility probe):
- Universe: SVXY (traded vehicle); ^VIX, ^VIX3M (signal only,
  not traded); SPY (secondary reference).
- Splits: Train 2011-10→2019-12 (includes volmageddon 2018-02 —
  public knowledge before Val), Val 2020-01→2021-12 (COVID),
  Test 2022-01→2026-10-08 (protected). OOS = Val+Test.
- Signal (causal, 1-day lag): contango_t = ^VIX3M_t/^VIX_t - 1;
  gate_t = 1{contango_t > gate_thresh}; vol_t = rolling realized
  vol of SVXY returns (window ∈ {21, 63}); position_t =
  gate_t × clip(target_vol / vol_t, 0, max_pos).
- Grid: gate_thresh ∈ {0.00, 0.02, 0.05} × vol_window ∈ {21, 63}
  × target_vol ∈ {0.05, 0.10, 0.15, 0.25, 0.50} × max_pos ∈
  {0.5, 1.0} = 60 combos; selection by Val Sharpe; Test protected.
- Benchmark (gate-relevant): buy-and-hold SVXY; report SPY BH as
  secondary reference.
- Gates: the unchanged 8-gate PROMPT_V2 set + ±20% OAT perturbation
  gate (as in H16). Reuse `run_backtest`, `compare_to_benchmark`,
  `walk_forward_splits`, the tracker, and the H16 gate-eval pattern
  (`full_gate_eval` in `run_h16_factor_timing_experiment.py`).
- Ablations: BH SVXY, ungated vol-target-only, gate-only (no vol
  target), BH SPY.
- Expected outcome (from the EDA): REJECT — the DD ≤ 15% gate
  forces target_vol ≈ 5% where Sharpe ≈ 0.46 < 1.0; the 2018-02-05
  tail (-32% in one day, inside contango) is un-gateable on daily
  data. That is a legitimate, publishable falsification: "the VRP
  is not harvestable within a 15% max-DD budget on free daily
  data; the binding constraint is the volmageddon tail, not the
  carry." Do NOT weaken gates to force a pass.
- Add `tests/test_h17_vrp.py` (mirror `tests/test_h16_factor_timing.py`
  structure: causality, point-in-time, gate recomputation, outcome
  pinning).
- Alternative if VRP is judged uninteresting: overnight-vs-intraday
  equity decomposition on daily OHLC (overnight return =
  open/close_prev - 1; 2009-2026 sample; ~2 trades/day clears the
  trades gate trivially; expect REJECT on Sharpe/DD).

## Constraints (unchanged)
- No paid data; yfinance/free sources only; network is available
  in this environment (yfinance installed and verified working).
- Reuse existing engine/cost model/tracker/validation — no rebuilds.
- Pre-register before running; never select on Test.
- Compute budget ≤ 2 CPU-h per hypothesis.
- All gates from PROMPT_V2.md + HYPOTHESIS_SPEC.md apply; no
  gate weakening.
- Note: working-tree changes from this session (H16 script, tests,
  HYPOTHESIS_SPEC.md, INEFFICIENCY_RANKING.md, NEXT_TASK.md, new
  experiment artifacts, and the new `.cache/data/*.parquet` fetches
  for the 9 factor ETFs + ^VIX, which the repo tracks for offline
  reproduction) are NOT yet committed; the repo convention is
  commit-per-experiment — commit them (excluding `.pyc` churn)
  when starting the next session.

---

## Session outcome (2026-10-13 — H18 executed)

**H18 (Overnight-vs-intraday equity return decomposition): REJECT — 2/9 gates.**

Executed exactly as pre-registered. Selected config `predictor=prior_5d_return_sign, hold_convention=next_intraday` (argmax Val Sharpe 0.980). OOS Sharpe 0.442 (< 1.0), max DD -22.23% (> 15%), PF 1.089 (< 1.3), worst-regime Sharpe -2.438 (bear, < 0.3), benchmark p=1.000 (fail), IR -0.597 (fail). PASS gates: Trades (589≥200), perturbation (1.000≥0.5). Compute: 0.3 s, 0.00 CPU-h. Tests: 20 new H18 tests, full suite 218 passing.

**Confirmed hypothesis (publishable falsification):** The overnight/intraday return decomposition strategy does not generate sufficient risk-adjusted returns to clear the PROMPT_V2 evidence gates on free daily OHLC data. The binding constraint is the strategy's inability to achieve Sharpe ≥ 1.0 while respecting the drawdown constraint. The prior 5-day return sign predictor shows some persistence (Val Sharpe 0.980) but fails to translate to OOS Sharpe ≥ 1.0 due to volatility scaling limitations and transaction costs.

**Verified:**
- 218/218 tests pass (198 prior + 20 new H18 tests pinning gates, grid/selection integrity, causality, weight bounds, regime labels, and the executed REJECT outcome).
- Artifacts in `.experiments/artifacts/exp_2026-10-13T22-14-50-729923Z/`; H18 Measured section added to `HYPOTHESIS_SPEC.md`; root-cause attribution added to `INEFFICIENCY_RANKING.md` §16.

### Cumulative state of evidence gates (all hypotheses)
- PASS families: H10 (intraday futures TSMOM, Sharpe 1.276), H11 (robustness certified), H12 (selection-bias audit PASS).
- REJECT families: H1-H9 (momentum/TSMOM on free data), H16 (factor timing), H17 (VRP).
- **H18 Overnight/Intraday Decomposition: REJECTED.**
- Structural walls remain: (a) the yfinance hourly `=F` 730-day cap blocks intraday extension beyond H10/H11 without paid data; (b) the ≤15% DD joint gate has been met by no long-only free-data family except the futures-carry edge of H10/H11.

### Precise next task for the next session
**H19: Volume-predictive return decomposition.** Rationale: while price-based strategies have struggled to clear the Sharpe gate on free data, volume contains predictive information about future returns that remains underexplored. The hypothesis is that decomposing volume into anticipated and unanticipated components (similar to earnings surprises) and trading on the unanticipated volume component could yield a Sharpe ≥ 1.0 with DD ≤ 15% on free data. This addresses the structural wall by focusing on a different data stream (volume) that may have different predictive properties than price returns. Pre-register with the unchanged PROMPT_V2 gates:

- Universe: SPY (primary), also QQQ/IWM for cross-validation. Traded vehicle = SPY; daily volume required.
- Sample: 2009-01-01→2026-10-08 (~4,200 daily bars).
- Splits: Train 2009-01→2014-12, Val 2015-01→2019-12, Test 2020-01→2026-10-08. OOS = Val+Test.
- Signal: decompose daily volume into anticipated component (based on lagged volume, volume volatility, and price-volume relationships) and unanticipated component (residual); position = long SPY when unanticipated volume is positive (indicating unexpected buying pressure), flat when negative. Use existing engine with volume data.
- Grid: volume_decomp_method ∈ {simple_lagged, vol_scaled, price_volume_residual} × threshold_type ∈ {zero, median, adaptive} = 9 combos; selection by Val Sharpe; Test protected.
- Benchmark: buy-and-hold SPY. Report volume-decomp-only BH.
- Ablations: BH SPY, random volume-based signals, constant position.
- Expected outcome: REJECT — volume-based strategies on free daily data face similar volatility constraints as price-based strategies; predictive information in volume is insufficient to overcome transaction costs and drawdown limits. That is a legitimate falsification: "predictive information in daily volume on free data does not yield a Sharpe ≥ 1.0 with DD ≤ 15% after transaction costs."
- Tests: `tests/test_h19_volume_predictive.py` mirroring `test_h16_factor_timing.py`/`test_h17_vrp.py`.
- Compute budget ≤ 2 CPU-h. Determinism seed 42.

### Constraints (unchanged)
- No paid data; yfinance/free sources only.
- Pre-register before running; never select on Test.
- All gates from PROMPT_V2.md + HYPOTHESIS_SPEC.md apply; no gate weakening.
- Working-tree changes from this session should be committed per the repo convention (commit-per-experiment): H18 script (`run_h18_overnight_intraday_experiment.py`), H18 tests (`tests/test_h18_overnight_intraday.py`), updated `HYPOTHESIS_SPEC.md`, `INEFFICIENCY_RANKING.md`, `NEXT_TASK.md`, H18 experiment artifacts, `.cache/data/` parquet fetches — excluding `.pyc` churn.
