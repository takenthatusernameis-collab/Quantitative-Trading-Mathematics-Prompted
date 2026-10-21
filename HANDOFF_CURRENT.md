# HANDOFF_CURRENT — session complete (H39)

## State
- **H39 is COMPLETE** as recorded in `NEXT_TASK.md`, `HANDOFF_NEXT.md` and
  `HANDOFF_CURRENT_SESSION.md`: the package's **two Sharpe implementations now agree**, and the
  cross-module agreement contract covers **every metric the package computes twice**.
- **H38 is COMPLETE** as recorded in `NEXT_TASK.md`, `HANDOFF_NEXT.md` and
  `HANDOFF_CURRENT_SESSION.md`: the engine's `total_return` spans every bar.
- **H35, H36, H37 and the remaining-runner extension are COMPLETE**: every gate defect class that
  has surfaced is closed by an executable invariant, and the point-in-time invariant covers every
  `run_*.py` in the repository.
- No published artifact, gate threshold, verdict, certified number or published row was
  modified; no grid was re-run; no hypothesis was added.

## What changed (this session — H39)
- `src/qtr/backtest/engine.py` (`_calculate_metrics`) — the Sharpe denominator is now the
  **population** standard deviation (`returns.std(ddof=0)`), matching
  `qtr.validation.statistics.sharpe_ratio` and therefore `validate_strategy`; and the
  degenerate-series guard now carries the record's **1e-15 tolerance** instead of an exact-zero
  test. The `annualized_volatility` convention (sample std, ddof=1) is deliberately **unchanged** —
  it is the convention the record and the published artifacts use.
- `tests/test_engine_metric_agreement.py` (55 tests; 6 before this session) — the executable
  **cross-module metric-agreement contract**:
  - exact agreement between the engine and `validate_strategy` for all six shared metrics, across
    single/multi-symbol, short, degenerate-flat, two-bar and total-loss (`gross == 0`) cases;
  - the engine-only metrics (Sortino, Calmar, max-drawdown duration, average trade cost) pinned
    by their exact formula, with their absence from `validate_strategy` asserted;
  - the convention itself: the population-std formula, the exact `sqrt(n / (n - 1))` relation to
    the sample-std formula, the uniform (order-preserving) rescaling, the degenerate-series
    guard, and `annualized_sharpe`'s bar-frequency variant as a documented difference;
  - the **published-artifact audit**: both conventions, the ratio, the bar count (2,515), the
    reconstruction of each published Sharpe from the artifact's own equity curve, the benchmark
    block, the volatility convention and the bounded effect (+0.0199%);
  - the **record**: H26's per-family convention classification (every audited family is
    `population_ddof0`, bit-exactly) and the H9 disclosure;
  - **negative controls**: the contract rejects the pre-fix Sharpe and the pre-fix
    `total_return`.
- `FINAL_REPORT.md` §H39 + the re-baselined `Summary statistics` and `Next Task` sections,
  `NEXT_TASK.md`, `HANDOFF_NEXT.md`, `HANDOFF_CURRENT_SESSION.md`, this file.
- No `run_*.py` was touched; no published artifact, gate threshold, verdict, certified number or
  published row was modified; no grid was re-run.

## What was actually verified
- Baseline (before this session): `python -m pytest -q -W error` → **1121 passed, 1 skipped**.
- After: `python -m pytest -q -W error` → **1170 passed, 1 skipped** in 268 s (1121 + the 49 new
  H39 tests; the skip is the pre-existing `buy_and_hold` skip in H36's module).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
  `python -m ruff format --check src tests run_*.py` → the only deviation is on pre-existing
  lines of `tests/test_runner_causality_inventory.py` that this session did not touch (ruff
  0.17.1 style drift); every line this session added is format-clean.
- **Injected negative controls** (into the engine, then restored; `git diff` shows only the
  intended change): reverting the Sharpe to the sample std fails **15** of the 55 contract tests;
  reverting only the degenerate-series guard to an exact-zero test fails **2** of them.
- The **direction of the change is pinned to the committed record**, not to an assertion made
  here: H26's own audit (`.experiments/artifacts/h26_sharpe_scale/summary.json`) classifies every
  audited family's published Sharpe as `population_ddof0` with `abs_diff_ddof0 == 0.0`.
- No published number was recomputed by re-running anything: every figure is read out of the
  committed artifacts, their committed equity curves and the committed H26 audit.

## What remains unresolved
- **The runners compute the same metrics a third time.** Six near-duplicate `_period_metrics`
  helpers (H10, H16, H17, H19, H20, H23) re-implement the Sharpe, the profit factor and the max
  drawdown; their drawdown uses `cum / cum.cummax() - 1` against the library's
  `(equity - rolling_max) / rolling_max` (≤ 5.6e-17 apart), and
  `run_h26_sharpe_scale_audit.py:303` publishes a daily Sharpe on the **sample** convention.
  This is the next task.
- **`run_h18_overnight_intraday_experiment.py:526,637`** — the runner-local `total_return` copy
  still uses the pre-H38 range; the H18 artifacts are frozen, so it stays. Bounded: 6.34 bps on
  the published full-period `total_return` of the selected row; H18's OOS `total_return` is
  consistent with its own OOS return series and with the committed equity curve; H18's nine gates
  do not use `total_return`.
- **H9's published OOS Sharpe is on the sample convention** (gap 1.026e-04 against a 5.6e-02
  margin over its 1.0 gate; the published row is a REJECT on the profit factor). Disclosed and
  pinned; the H9 artifact is frozen.
- The pre-fix `strategy_metrics` / `benchmark_metrics` values of the five affected artifacts
  (including their sample-std Sharpes) are the historical record of the runs as executed; they
  are now pinned by tests.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted and the certified
  families' numbers and verdicts are frozen.

## Approaches already tried / failed (and why)
- **Re-running a grid to quantify the impact was not attempted and is forbidden.** Every number
  is read out of the committed artifacts, their committed equity curves and the committed H26
  audit, which is both cheaper and stronger (the artifacts *are* the published record).
- **The "fix the volatility convention too" option was rejected**: `annualized_volatility` keeps
  the sample std (ddof=1) because that is the convention `validate_strategy` uses for it and the
  one the published artifacts record; changing it would break the agreement in the other
  direction and move a published number for no reason.
- **Rewriting the runners' local metric helpers in place was rejected**: the artifacts are
  frozen, so a rewritten helper would stop reproducing them. The runners' copies are to be
  classified and pinned, not replaced.
- **The coverage figure could not be re-measured in this session** (`pytest-cov`/`coverage` are
  not installed in this environment); the branch argument in §H39 replaces it, and the
  environment gap is recorded rather than papered over.

## Precise next task (one task), with evidence and constraints
- **Extend the metric-agreement contract from the library to the runners' own metric
  implementations** — the six `_period_metrics` helpers and the inline drawdown/profit-factor
  computations — see `NEXT_TASK.md` for the full statement, the inventory to build and the
  constraints. Any follow-up must not modify published artifacts, gates, thresholds, verdicts or
  certified numbers; must not re-run grids; must follow the "change approach after repeated
  failure" rule; and must preserve the existing invariants.
