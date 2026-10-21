# HANDOFF_CURRENT_SESSION — H39: the package's two Sharpe implementations disagreed

## What changed

1. **`src/qtr/backtest/engine.py:_calculate_metrics`** — the Sharpe denominator is now the
   **population** standard deviation (`returns.std(ddof=0)`, was the sample std via pandas
   `Series.std()`), matching `qtr.validation.statistics.sharpe_ratio` and therefore
   `validate_strategy`; and the degenerate-series guard now uses the record's **1e-15 tolerance**
   instead of an exact-zero test. `annualized_volatility` keeps the sample std (ddof=1) on
   purpose — that is the convention the record and the published artifacts use.
2. **`tests/test_engine_metric_agreement.py`** (55 tests, 6 before) — the executable contract for
   the metric surface:
   - **exact agreement** between the engine and `validate_strategy` for all six shared metrics
     (`total_return`, `annualized_return`, `annualized_volatility`, `sharpe`, `max_drawdown`,
     `profit_factor`) across single/multi-symbol, short, degenerate-flat, two-bar and total-loss
     (`gross == 0`) engine shapes, plus `num_trades` against the validation counter;
   - the **engine-only metrics** (Sortino, Calmar, max-drawdown duration, average trade cost)
     pinned by their exact formula, with their absence from `validate_strategy` asserted;
   - the **convention itself**: the population-std formula, the exact `sqrt(n / (n - 1))` relation
     to the sample-std formula, the uniform (order-preserving) rescaling that protects the
     runners' "beats benchmark" comparisons, the degenerate-series guard, and
     `annualized_sharpe`'s bar-frequency variant as a documented difference of
     `sqrt(bars_per_year / 252)`;
   - the **published-artifact audit**: both conventions, the ratio, the bar count (2,515), the
     reconstruction of each published Sharpe from the artifact's own equity curve, the benchmark
     block, the volatility convention, and the bounded effect (+0.0199%, < 0.1%);
   - the **record**: H26's per-family convention classification (every audited family is
     `population_ddof0`, `abs_diff_ddof0 == 0.0`) and the H9 disclosure;
   - the **certified-numbers guard**: the certified runners never read the engine's metric, no
     runner gates on an engine Sharpe against a finite threshold, and every engine-Sharpe
     comparison is engine-against-engine;
   - **negative controls**: the contract rejects the pre-fix Sharpe and the pre-fix
     `total_return`.
3. **`FINAL_REPORT.md`** — new §H39 (the defect, the evidence tables, the decision and its
   direction, the second guard defect, the contract, the H9 disclosure) and a rewritten
   `## Next Task` section; the `Summary statistics` test count is re-baselined (1115 → 1170).
4. **`NEXT_TASK.md`**, **`HANDOFF_NEXT.md`**, **`HANDOFF_CURRENT.md`**, this file.

No published artifact, gate threshold, verdict, certified number or published row was touched.
No grid was re-run. No hypothesis was added. `run_*.py` was not touched at all.

## What was actually verified

- Baseline before this session: `python -m pytest -q -W error` → **1121 passed, 1 skipped**.
- After: `python -m pytest -q -W error` → **1170 passed, 1 skipped** in 268 s (1121 + the 49 new
  H39 tests; the skip is the pre-existing `buy_and_hold` skip inside H36's module).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → the only deviation is on pre-existing
  lines of `tests/test_runner_causality_inventory.py` that this session did not touch (ruff
  0.17.1 style drift); every line this session added is format-clean.
- **Injected negative controls** (into the engine, then restored; `git diff` shows only the
  intended change): reverting the Sharpe to the sample std makes **15 of the 55** contract tests
  fail; reverting only the degenerate-series guard makes **2** fail.
- Every number in §H39 is read out of the **committed artifacts** (summary.json + equity
  parquet) or the **committed H26 audit**; nothing was recomputed by re-running a grid.
- **Not verified here:** the `src/qtr` coverage figure — `pytest-cov`/`coverage` are not
  installed in this environment. The engine change adds no new branch (the `> 1e-15` branch is
  covered by the new degenerate-series tests, the other branch by every other metric test), but
  the 100% figure itself could not be re-measured.

## The finding

- **F1 — the two implementations divided by different standard deviations.** The engine used the
  **sample** std (pandas `Series.std()`, ddof=1), `qtr.validation.statistics.sharpe_ratio` uses
  the **population** std (numpy `ndarray.std()`, ddof=0). The two differ by exactly
  `sqrt(n / (n - 1))` — measured as `strategy_metrics.sharpe / validation.sharpe =
  0.9998011730768697` in **all five** artifacts with engine metrics (n = 2,515) — so each of
  them published **two different Sharpes for one run**, in two blocks of the same artifact.
- **F2 — the direction is pinned by the record, not by an assertion.** H26's own Sharpe-scale
  audit classified the convention of every audited family's published Sharpe: H10, H21, H22,
  H23 and H25 are all `population_ddof0` with `abs_diff_ddof0 == 0.0`. The engine was the only
  implementation in the package that was not.
- **F3 — a second, independent disagreement in the degenerate-series guard.** The engine's
  `if returns.std(ddof=0) > 0` let a *constant* return series through (its std is ~2.2e-19 from
  float noise), producing a Sharpe of **7.320824597683504e+16** where `validate_strategy`
  reports 0.0. The record's `sharpe_ratio` has documented this trap since it was fixed there;
  the engine never got the same guard.
- **F4 — no published verdict can move.** No runner gates on the engine's Sharpe (AST sweep of
  all 32 runners); the only engine-Sharpe comparisons are engine-against-engine, and the change
  is a *uniform* rescaling whose multiplier depends only on the bar count, so the order of two
  Sharpes on the same series is preserved exactly. The certified families never read the
  engine's metric.
- **F5 — H9 is the one published Sharpe on the other convention** (sample std; gap 1.026e-04
  against a 5.6e-02 margin over its 1.0 gate; its published row is a REJECT on the profit
  factor). Disclosure, bounded, pinned.

## What remains unresolved (disclosures, not rewrites)

- **H9's published OOS Sharpe convention** (see F5).
- **The runners compute the metrics a third time** — six near-duplicate `_period_metrics`
  helpers (H10, H16, H17, H19, H20, H23) whose max drawdown uses `cum / cum.cummax() - 1`
  against the library's `(equity - rolling_max) / rolling_max` (≤ 5.6e-17 apart), plus
  `run_h26_sharpe_scale_audit.py:303`'s sample-std daily Sharpe and the inline drawdown
  computations in H11/H18/ddcv/futures. The next task.
- **H18's runner-local `total_return` copy** (`run_h18_overnight_intraday_experiment.py:526`
  and `:637`) still uses the pre-H38 range. The H18 artifacts are frozen, so the copy stays.
  Bounded: the published full-period `total_return` of the selected row is **6.34 bps** above
  the from-capital value; H18's *OOS* `total_return` is unaffected; its nine gates do not use
  `total_return`.
- The pre-fix `strategy_metrics` / `benchmark_metrics` values of the five affected artifacts
  (including their sample-std Sharpes) are history and are now pinned.

## Approaches already tried / failed (and why)

- **Re-running a grid to quantify the impact was not attempted and is forbidden.** Every number
  in §H39 is read out of the committed artifacts, their committed equity curves and the committed
  H26 audit, which is both cheaper and stronger (the artifacts *are* the published record).
- **"Normalise the volatility convention as well" was rejected**: `annualized_volatility` keeps
  the sample std because that is the convention `validate_strategy` uses for it and the one the
  published artifacts record (the five artifacts' `annualized_volatility` equals the
  `validation` block's to the last digit). Changing it would break the agreement in the other
  direction and move a published number for no reason.
- **Rewriting the runners' local metric helpers in place was rejected**: the artifacts are
  frozen, so a rewritten helper would no longer reproduce them. The copies are to be classified
  and pinned, not replaced.
- **The coverage figure could not be re-measured** (the tool is not installed in this
  environment); the branch argument is recorded in its place rather than claiming an
  unverified number.

## Precise next task (one task), with evidence and constraints

**Extend the metric-agreement contract from the library to the runners' own metric
implementations — the six near-duplicate `_period_metrics` helpers and their siblings.**

*Evidence.* The repository computes the Sharpe, the profit factor and the max drawdown a third
time, in the runners: `run_h10_intraday_tsmom_pfopt_experiment.py:243`,
`run_h16_factor_timing_experiment.py:218`, `run_h17_vrp_experiment.py:157`,
`run_h19_volume_predictive_experiment.py:192`, `run_h20_signed_volume_experiment.py:211` and
`run_h23_crypto_futures_tsmom.py:245` each carry their own `_period_metrics(ret, n_trades)`.
Their Sharpe (`sharpe_ratio`) and profit factor match the library exactly; their **max drawdown
uses a different formula** (`cum / cum.cummax() - 1` against the library's
`(equity - rolling_max) / rolling_max`), a difference of up to 5.6e-17 measured over 200 random
equity curves. `run_h26_sharpe_scale_audit.py:303` publishes a daily Sharpe on the **sample**
convention — the same split H39 just closed in the engine — and
`run_cs_momentum_experiment.py:383` computes a local information ratio on the population
convention (consistent with `compare_to_benchmark`, but unpinned).

*Deliverable.* An executable contract in the style of
`tests/test_engine_metric_agreement.py` and `tests/test_runner_causality_inventory.py`: an
inventory of every metric the runners compute locally, classified and pinned, where each entry
asserts exact agreement with `qtr.validation.statistics` (or the engine) or pins the documented
difference with its exact formula and its bounded effect on the published artifacts. A new
runner-local metric helper must fail the suite.

*Constraints.* Do not re-run any grid; do not modify a published artifact, gate threshold,
verdict or certified number; do not add a hypothesis; do not rewrite the runners' metric
helpers in place (their artifacts are frozen) — classify, probe and pin them. Keep
`src/qtr` at 100% coverage; `python -m pytest -q -W error` and `ruff check` /
`ruff format --check` must pass from a bare clone (no install step); re-run
`tests/test_causality_invariant.py` after any change under `src/qtr`,
`tests/test_runner_causality_inventory.py` after any change in a `run_*.py`, and
`tests/test_engine_metric_agreement.py` after any change to `_calculate_metrics` or to
`qtr.validation.statistics`.
