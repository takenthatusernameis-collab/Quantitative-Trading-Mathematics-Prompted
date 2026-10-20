# HANDOFF_CURRENT — session complete (H37)

## State
- **H37 is COMPLETE** as recorded in `NEXT_TASK.md`, `HANDOFF_NEXT.md` and
  `HANDOFF_CURRENT_SESSION.md`: the **runners' inline signal code** is now pinned by an
  executable **point-in-time (no look-ahead) invariant**, and one new look-ahead was found
  and disclosed.
- **H36 is COMPLETE** as recorded in `NEXT_TASK.md`, `HANDOFF_NEXT.md` and
  `HANDOFF_CURRENT_SESSION.md`: the shared research infrastructure (`qtr.strategies` +
  `qtr.backtest`) is pinned by an executable point-in-time invariant, and the test suite runs
  from a bare clone with no install step.
- **H35 is COMPLETE** as recorded in `NEXT_TASK.md`, `HANDOFF.md` and `HANDOFF_NEXT.md`.
- Every gate defect class that has surfaced in this repository is now closed by an
  executable invariant: H33 (vacuous benchmark gates), H34 (direction-blind benchmark
  gate), H35 (non-evaluating gates: a constant, or a comparison against a placeholder).
- The H35 audit found **three** non-evaluating gates — H7's `min_perturbed_sharpe_ratio`
  and `min_worst_regime_sharpe` (hard-coded `True`) and H18's `perturbation_ratio` (a
  placeholder constant) — and **one** latent permissive default (H4/H5/H6 read the IR
  threshold as `GATES.get("min_information_ratio", -1e18)`), now fixed.
- **No certified family owns a non-evaluating gate.** The certified families (H9, H10,
  H11, H12, H21, H22, H25) and every other family evaluate all of their gates.
- No published artifact, gate threshold, verdict, certified number or published row was
  modified; no grid was re-run; no hypothesis was added.

## What changed (this session — H37)
- `tests/test_runner_causality_inventory.py` (new, 179 tests) — the executable
  **point-in-time invariant for the runners' inline signal code**:
  - all **137** module-level functions of **13** runners (`run_h9/h10/h12/h16/h18/h19/h20/
    h21/h22/h23/h25/h27/h29`) classified as `probed` (36) / `lookahead` (7) / `static` (94)
    and pinned — **a new function in an in-scope runner fails the suite**;
  - **53 future-perturbation probe cases** (dense per-bar sweep + sparse sweep at the
    runners' lookbacks, two negative controls, non-vacuity) + 2 day-aligned collapse probes;
  - an exhaustive, **pinned** AST sweep for negative shifts, backward periods, centred
    windows, backward fills and same-period collapses;
  - the known look-aheads are pinned as **detections**, so a disclosure cannot be silently
    dropped and a defect cannot be silently repaired.
- `FINAL_REPORT.md` §H37 + the re-baselined `Summary statistics` and `Next Task` sections,
  `NEXT_TASK.md`, `HANDOFF_NEXT.md`, `HANDOFF_CURRENT_SESSION.md`, this file.
- No `src/qtr` source file was changed; no published artifact, gate threshold, verdict,
  certified number or published row was modified; no grid was re-run.

## What was actually verified
- Baseline (before this session): `python -m pytest -q` → **780 passed, 1 skipped**.
- After: `python -m pytest -q` → **959 passed, 1 skipped** in 182 s (780 + the 179 new
  tests; the skip is the pre-existing `buy_and_hold` skip in H36's module).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
  `python -m ruff format --check src tests run_*.py` → *82 files already formatted*.
- `src/qtr` untouched → its coverage is unchanged at **100%**.
- **Injected negative controls** (into the runners, then restored; `git diff` on both files
  is empty): a `shift(-1)` in `run_h19_…:build_targets` → **8 tests fail**; a *non-leak*
  control (`prices.shift(skip)` → `prices` in `run_h16_…:factor_momentum`, which still only
  reads `price[t]`) → **all 14 H16 tests still pass**, so the invariant is not over-strict.
- The published intraday look-ahead is detected **from the runners' own code**
  (`build_hourly_target` in H10/H23: 76/79 dense cuts, 9/9 sparse cuts), not from a copy.
- The H18 disclosure is checked against the committed artifact: the published selection was
  the causal `prior_5d_return_sign_next_intraday` (Val Sharpe 0.9797), the two leaky cells
  scored 0.4710 / 0.5801, and the published verdict is REJECT — no published number or
  verdict changes. The selection is pinned by a test.

## What remains unresolved
- **The remaining runners are not covered** by a generic causality probe (`run_experiment.py`,
  `run_baseline.py`, `run_param_sweep.py`, `run_alternatives.py`, the cs/ts/ddcv/futures/h6/
  h7/h8 runners, `run_h1/h11/h13/h17_*` and the H25–H36 audit runners).
- **The *predictor timing* class is audited only in H18 so far.** H29 classified the
  **collapse** constructions of the remaining families as CAUSAL; it did not audit whether a
  family's *predictor* reads its own bar's close while trading that bar's return — the class
  H37 found a new instance of in H18. The same defect is plausible elsewhere and is
  invisible to every test in the repository.
- The engine's `metrics["total_return"]` excludes the first bar and is therefore inconsistent
  with its own equity curve and with `annualized_return`'s period count. **Disclosure only**:
  `metrics` values are in published artifacts and the record is frozen.
- `DataFetcher.fetch_sp500_constituents(date=...)` silently ignores `date` and returns the
  *current* constituent list — a latent survivorship-bias footgun; no runner calls it (and,
  unlike the item above, it **can** be fixed).
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted and the
  certified families' numbers and verdicts are frozen.

## Approaches already tried / failed (and why)
- **Probing `_apply_exits_and_aggregate` (H21/H22/H25) positionally was abandoned**: the exit
  state machine is *sticky* (it holds the size it entered with), so a positional probe of the
  position series cannot see a look-ahead in its input target; and `vol_scaled_tsmom_hourly`'s
  252-bar lookback is not configurable through the frozen `SEL`, so a reduced dense sample
  would make the probe vacuous. The **call graph** is the pin instead.
- **A single "collapse" contract was rejected**: the published collapse and H27's causal
  collapse are correct on their own daily grid; the look-ahead is created by *expanding* the
  daily value back over the same day, which only a probe on the hourly grid can see.
- **Quantifying the H18 inflation by re-running the two affected cells was not attempted**: the
  SPY/QQQ/IWM/^VIX daily bars are not identifiable in the local cache by symbol and
  re-running a grid is forbidden, so the disclosure stays *structural* and *bounded* by the
  committed artifact.
- **Repairing the disclosed gates for real was rejected**: it needs the H7/H18 grids re-run
  (forbidden) and would change published tallies. They are disclosed and pinned instead.
- **Re-deriving the intraday Sharpe scale was not attempted**: H26 already audited it and
  concluded the mis-scaling understates the intraday family and invalidates no verdict.

## Precise next task (one task), with evidence and constraints
- **Extend the point-in-time invariant to the *remaining* runners, and audit the predictor
  timing (not just the collapse construction) in the families H29 certified as CAUSAL** —
  see `NEXT_TASK.md` for the full statement, the inventory to build and the constraints. Any
  follow-up must not modify published artifacts, gates, thresholds, verdicts or certified
  numbers; must not re-run grids; must follow the "change approach after repeated failure"
  rule; and must preserve the existing invariants.
