# HANDOFF_CURRENT_SESSION — H37: the runners' inline signal code is point-in-time

## What changed

1. **`tests/test_runner_causality_inventory.py`** (new: 179 tests) — the point-in-time
   contract for the **runners' own** signal code, extending H36's invariant from the shared
   library to the layer above it.
   - **Scope.** 13 runners: the eleven named by the H36 handoff
     (`run_h10/h12/h16/h18/h19/h20/h21/h22/h25/h27/h29`) plus their two dependencies —
     `run_h9` (which owns the primitives the others import) and `run_h23` (the crypto copy
     of the H10 pipeline).
   - **The probe** is H36's *future perturbation* on the runners' own constructors: the
     market data after a cut is replaced by a different (seeded, deterministic) path and
     everything at or before the cut must come out bit-identical. Dense sweep (every bar of
     a reduced sample is a cut point) + sparse sweep (nine cuts at the lookbacks the
     runners actually use). The perturbation is per-(bar, column) — a factor shared by
     `open` and `close` would leave `close - open` (and therefore a sign rule) unchanged —
     and the first perturbed bar is halved so a one-bar-ahead return always changes sign.
   - **Two scopes**, because the runners do not execute their decision at the same moment:
     `after` (the engine's one-bar delay: the signal may read its own bar) and `close`
     (H18, whose decision is executed at the **open** of the bar: the signal may not read
     that bar's close).
   - **The inventory**: all **137** module-level functions of the 13 runners are classified
     as `probed` (36), `lookahead` (7) or `static` (94). A new function in an in-scope
     runner fails the suite until it is classified. 53 probe cases + 2 day-aligned probes
     for the daily collapses.
   - **The static sweep** is exhaustive by construction over the runners' source: negative
     `shift(...)`, backward `pct_change`/`diff` period, centred window, backward fill and
     same-period `resample` collapse are located by AST and the **site list is pinned**.
   - **The known look-aheads are pinned as *detections***: the probe must find the
     violation, so a disclosure cannot be silently dropped and a defect cannot be silently
     repaired without updating the record.
2. **`FINAL_REPORT.md`** — new §H37 (the gap, the contract, the inventory, the findings, the
   verification) and a rewritten `## Next Task` section; the `Summary statistics` test count
   is re-baselined (780 → 959).
3. **`NEXT_TASK.md`**, **`HANDOFF_NEXT.md`**, this file.

No source file, gate, threshold, artifact, verdict, certified number or published row was
touched. `src/qtr` was not touched at all.

## What was actually verified

- Baseline before this session: `python -m pytest -q` → **780 passed, 1 skipped**.
- After: `python -m pytest -q` → **959 passed, 1 skipped** in 182 s (780 + the 179 new
  tests; the skip is the pre-existing `buy_and_hold` skip inside H36's module).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → *82 files already formatted*.
- `src/qtr` untouched → its coverage is unchanged at **100%**.
- **Injected negative controls** (into the runners, then reverted; `git diff` on both files
  is empty):
  - A) `run_h19_…:build_targets`: `unanticipated = vol - vol_mean` → `(vol -
    vol_mean).shift(-1)` → **8 tests fail** (the dense and sparse sweeps of the four H19
    grid cells).
  - B) *control, not a leak*: `run_h16_…:factor_momentum`: `prices.shift(skip)` → `prices`
    (the momentum now reads `price[t]`, which the engine's one-bar delay permits) → **all
    14 H16 tests still pass**, so the invariant is not over-strict.
  - In-module negative controls: a `shift(-1)` signal and a `pct_change(-1)` signal must be
    *detected* by the probe — both are. Every probed constructor must also *react* to the
    perturbation, so an inert all-zero output cannot pass trivially.
- The published intraday look-ahead is detected **from the runners' own code**
  (`build_hourly_target` in H10 and H23: 76/79 dense cuts, 9/9 sparse cuts), not from a copy
  of it.
- The H18 finding is checked against the committed artifact: the published selection was
  `prior_5d_return_sign_next_intraday` (Val Sharpe 0.9797), the two leaky cells scored
  0.4710 / 0.5801, and the published verdict is REJECT — so the published row, numbers and
  verdict are unaffected. A test pins the selection.

## The findings (disclosures)

- **P1 — the published intraday look-ahead, reproduced from the runners' own code.** The
  daily collapse's value for day `D` is expanded over day `D` itself. This is H27/H28/H29's
  defect; H37's contribution is that it is now *executable* against the runner source and
  pinned as a detection, and that the two daily collapses are pinned on their own grid (the
  published one reads the last bar of day `D`, H27's causal one the last bar of day `D-1`).
- **P2 — the inherited look-ahead.** H12's `_rebuild_grid_oos` and H21/H22/H25's
  `_apply_exits_and_aggregate` build their returns/positions with `build_hourly_target`; the
  inheritance is pinned by an executable call-graph check. These are **not** probed, and the
  reason is written down: the exit state machine is *sticky* (it holds the size it entered
  with), so a positional probe of the position series cannot see a look-ahead in its input
  target.
- **P3 — new: H18's `vix_regime` predictor omits the pre-registered one-day lag.** The
  pre-registration requires *"Signal (causal, 1-day lag)"* and *"at the prior day's close"*;
  the predictor reads `vix_close[t]` (`run_h18_overnight_intraday_experiment.py:100`) and the
  runner applies the signal to **day `t`'s own legs** with no one-bar delay
  (`run_h18_overnight_intraday_experiment.py:454-459`). The probe detects it (79/79 dense
  cuts, 9/9 sparse) while the two lagged predictors are clean (0 cuts). Bounded: the
  published selection was a *causal* predictor, so no published number or verdict changes.

## What remains unresolved

- **The remaining runners are still uncovered.** `run_experiment.py`, `run_baseline.py`,
  `run_param_sweep.py`, `run_alternatives.py`, `run_cs_momentum_experiment.py`,
  `run_ts_momentum_experiment.py`, `run_ddcv_experiment.py`,
  `run_futures_tsmom_experiment.py`, `run_h6_vix_ddcv_experiment.py`,
  `run_h7_intraday_tsmom_experiment.py`, `run_h8_rolladjusted_tsmom_experiment.py`,
  `run_regime_gated_momentum_experiment.py`, `run_h1_*`, `run_h11_*`, `run_h13_*`,
  `run_h17_*` and the H25–H36 audit runners still build position series inline with no
  generic coverage.
- **The *predictor timing* class is only audited in H18 so far.** H29's sweep classified the
  **collapse** constructions of the remaining families as CAUSAL; it did not audit whether a
  family's *predictor* reads its own bar's close while trading that bar's return — the class
  H37 found in H18. The same defect is plausible elsewhere and is currently invisible.
- **The engine's `metrics["total_return"]` is inconsistent with its own equity curve** (it
  excludes the first bar's return while `annualized_return` counts it). ~a few bps;
  **not fixed here** because `metrics` values are in published artifacts — a *disclosure*,
  not a rewrite.
- **`DataFetcher.fetch_sp500_constituents(date=...)` silently ignores its `date` argument**
  and always returns the *current* constituent list — a latent survivorship-bias footgun in
  the shared library. No runner calls it, so nothing published is affected; unlike the item
  above, it **can** be fixed.

## Approaches already tried / failed (and why)

- **Probing `_apply_exits_and_aggregate` (H21/H22/H25) positionally was abandoned.** The
  probe is insensitive by construction: the exit state machine holds the size it entered
  with, so a change in the target's magnitude does not change the position series, and the
  only sensitivity left is a sign test that the dense sample does not reliably flip. Two
  further obstacles confirmed the choice: `vol_scaled_tsmom_hourly`'s 252-bar lookback is
  not configurable through the module's frozen `SEL`, so on a reduced dense sample the base
  signal is identically zero and the probe would be *vacuous*; and the full-size rebuild of
  five contracts per cut is far too slow for a dense sweep. The **call graph** is the pin
  instead, and the written argument says exactly why.
- **A single "collapse" contract was rejected.** The published collapse and H27's causal
  collapse are correct on their own daily grid (the value of day `D` is decided at the last
  bar of `D` resp. `D-1`); the look-ahead is created by *expanding* that value back over
  day `D`, which only a probe on the hourly grid can see. The two are therefore pinned
  separately: a day-aligned probe for the collapses and an hourly probe for the expansion.
- **Quantifying the H18 inflation by re-running the two affected cells was not attempted.**
  It would need the SPY/QQQ/IWM/^VIX daily bars, which are not identifiable in the local
  cache by symbol, and the standing constraint forbids re-running a grid. The disclosure is
  therefore *structural* (the predictor's timing) and *bounded* by the committed artifact
  (the leaky cells did not win the Val selection) — no number was recomputed.
- **Re-running any grid, or repairing the disclosed H7/H18 non-evaluating gates, remains
  forbidden** by the carried-forward constraints.

## Precise next task (one task), with evidence and constraints

**Extend the point-in-time invariant to the *remaining* runners, and audit the predictor
timing (not just the collapse construction) in the families H29 certified as CAUSAL.**

*Evidence.* H37 covered 13 runners; the rest still build position series inline with no
generic coverage (the list is in `NEXT_TASK.md`). H29's sweep classified the **collapse**
constructions of the remaining families as CAUSAL (min hold lag +1), but it did not audit
the *information timing of the predictors themselves* — the class H37 found a new instance
of in H18 (P3): a predictor that reads its own bar's close while trading that bar's return.
No test in the repository covers that class today.

*Deliverable.* The same treatment as H37: an inventory of the remaining runners' signal
constructors, pinned by a test, in which every constructor is either probed by a
future-perturbation probe (dense + sparse cuts, with the negative control retained) or
pinned by a static check plus a written, tested argument for why a dynamic probe does not
apply; **plus** a report of every predictor that reads its own bar's close while trading
that bar's return, with each family's published selection checked against the committed
artifacts so that every disclosure is bounded the way P3 is.

*Also open:* the engine's `metrics["total_return"]` (disclosure only) and
`DataFetcher.fetch_sp500_constituents(date=...)` (fixable — no published artifact depends on
it).

*Constraints.* Do not re-run any grid; do not modify a published artifact, gate threshold,
verdict or certified number; do not add a hypothesis; keep `src/qtr` at 100% coverage;
`python -m pytest -q -W error` and `ruff check` / `ruff format --check` must pass from a bare
clone (no install step).
