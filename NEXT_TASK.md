# Next Task — H16 executed (factor timing REJECTED); pivot to VRP harvesting (H17)

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

## Session outcome (2026-10-13 — H17 executed)

**H17 (Volatility-Risk-Premium Harvesting, term-structure-gated, vol-targeted long SVXY): REJECT — 3/9 gates.**

Executed exactly as pre-registered. Selected config `gate_thresh=0.0, vol_window=63, target_vol=0.25, max_pos=0.5` (argmax Val Sharpe 0.784). OOS Sharpe 0.742 (< 1.0), max DD -16.55% (> 15%), PF 1.147 (< 1.3), worst-regime Sharpe -4.130 (bear, < 0.3), benchmark p=0.534 (fail), IR -0.240 (fail). PASS gates: Trades (238≥200), WF stability (1.911≥0.7), perturbation (0.952≥0.5). Compute: 7.3 s, 0.00 CPU-h. Tests: 20 new H17 tests, full suite 198 passing.

**Confirmed hypothesis (publishable falsification):** The VRP is not harvestable within the 15% max-DD budget on free daily data. The binding constraint is the un-gateable 2018-02-05 / 2020-03 volmageddon tail (arrives inside contango, day-of), not the contango carry. The `target_vol → 5%` that satisfies DD ≤ 15% caps Sharpe at ~0.46; any `target_vol` raising Sharpe ≥ 1.0 pushes DD past 15%.

**Verified:**
- 198/198 tests pass (178 prior + 20 new H17 tests pinning gates, grid/selection integrity, causality, weight bounds, regime labels, and the executed REJECT outcome).
- Artifacts in `.experiments/artifacts/exp_2026-10-13T21-51-45-034237Z/`; H17 Measured section added to `HYPOTHESIS_SPEC.md`; root-cause attribution added to `INEFFICIENCY_RANKING.md` §15.

### Cumulative state of evidence gates (all hypotheses)
- PASS families: H10 (intraday futures TSMOM, Sharpe 1.276), H11 (robustness certified), H12 (selection-bias audit PASS).
- REJECT families: H1-H9 (momentum/TSMOM on free data), H16 (factor timing).
- **H17 VRP: REJECTED.**
- Structural walls remain: (a) the yfinance hourly `=F` 730-day cap blocks intraday extension beyond H10/H11 without paid data; (b) the ≤15% DD joint gate has been met by no long-only free-data family except the futures-carry edge of H10/H11.

### Precise next task for the next session
**H18: Overnight-vs-intraday equity return decomposition (daily OHLC).** The highest-information remaining untested family on free data. Rationale: the 2009-2026 daily OHLC sample (~4,200 bars) is the longest free sample; overnight return = openₜ/closeₜ₋₁ − 1; intraday return = closeₜ/openₜ − 1. The "overnight crash / intraday drift" phenomenon (see literature: overnight returns are systematically weak/negative, intraday carries the drift) is a genuinely different mechanism from momentum/volatility. Pre-register with the unchanged PROMPT_V2 gates:

- Universe: SPY (primary), also QQQ/IWM for cross-validation. Traded vehicle = SPY; daily OHLC required.
- Sample: 2009-01-01→2026-10-08 (~4,200 daily bars).
- Splits: Train 2009-01→2014-12, Val 2015-01→2019-12, Test 2020-01→2026-10-08. OOS = Val+Test.
- Signal: classify each day as "overnight-favoring" vs "intraday-favoring" based on a causal predictor (e.g., lagged overnight return sign, VIX level regime, or prior-N-day return sign — pick ONE pre-registered predictor to avoid data-mining); position = long the favored component (overnight or intraday leg) at the prior day's close, flat the other. Use the existing `run_signals`/`run_backtest` engine with per-period return series.
- Grid: predictor ∈ {lagged_1d_overnight_sign, vix_regime, prior_5d_return_sign} × hold_convention ∈ {next_overnight, next_intraday} = 6 combos; selection by Val Sharpe; Test protected.
- Benchmark: buy-and-hold SPY. Report overnight-only and intraday-only BH.
- Ablations: BH overnight leg, BH intraday leg, BH SPY, equal-weight of both legs.
- Expected outcome: REJECT — overnight-only and intraday-only legs each have Sharpe ~0.4-0.5 with high DD; the decomposition is descriptive, not a gate-clearing edge. That is a legitimate falsification: "the overnight/intraday decomposition on free daily OHLC does not yield a Sharpe ≥ 1.0 with DD ≤ 15%; the components are lower-Sharpe than the whole."
- Tests: `tests/test_h18_overnight_intraday.py` mirroring `test_h16_factor_timing.py`/`test_h17_vrp.py`.
- Compute budget ≤ 2 CPU-h. Determinism seed 42.

### Constraints (unchanged)
- No paid data; yfinance/free sources only.
- Pre-register before running; never select on Test.
- All gates from PROMPT_V2.md + HYPOTHESIS_SPEC.md apply; no gate weakening.
- Working-tree changes from this session should be committed per the repo convention (commit-per-experiment): H17 script (`run_h17_vrp_experiment.py`), H17 tests (`tests/test_h17_vrp.py`), updated `HYPOTHESIS_SPEC.md`, `INEFFICIENCY_RANKING.md`, `NEXT_TASK.md`, H17 experiment artifacts, `.cache/data/` parquet fetches — excluding `.pyc` churn.
