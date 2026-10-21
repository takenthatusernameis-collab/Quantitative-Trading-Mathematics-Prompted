# HANDOFF_NEXT — H39: the package's Sharpe implementations agree; the runners' copies are next

## What changed (this session)

1. **`src/qtr/backtest/engine.py:_calculate_metrics`** — two changes, both in the metric
   surface:
   - the **Sharpe denominator is now the population standard deviation**
     (`returns.std(ddof=0)`), matching `qtr.validation.statistics.sharpe_ratio` and therefore
     `validate_strategy`. The engine used the **sample** std (pandas `Series.std()`, ddof=1), so
     every artifact with engine metrics published **two different Sharpes for one run**
     (ratio exactly `sqrt((n-1)/n) = 0.9998011730768697`, n = 2,515);
   - the **degenerate-series guard** now carries the record's 1e-15 tolerance
     (`returns.std(ddof=0) > 1e-15`) instead of an exact-zero test. A constant return series has
     a std of ~2.2e-19 from float noise, so the engine divided by ~1e-19 and reported a garbage
     Sharpe of **7.3e16** where `validate_strategy` reports 0.0.

   `annualized_volatility` is deliberately **unchanged** (sample std, ddof=1): that is the
   convention `validate_strategy` uses for it and the one every published artifact records.

2. **`tests/test_engine_metric_agreement.py`** (55 tests, 6 before this session) — the executable
   cross-module contract: exact agreement on all six shared metrics across five engine shapes;
   the engine-only metrics pinned by formula; the convention itself (population-std formula, the
   exact `sqrt(n/(n-1))` relation, the order-preserving uniform rescaling, the degenerate guard,
   `annualized_sharpe`'s bar-frequency variant); the published-artifact audit (both conventions,
   the ratio, the bar count, the reconstruction of each published Sharpe from the artifact's own
   equity curve, the benchmark block, the bounded +0.0199% effect); the record (H26's per-family
   convention classification and the H9 disclosure); the certified-numbers guard (the certified
   runners never read the engine's metric; no runner gates on an engine Sharpe; every engine
   Sharpe comparison is engine-against-engine); and the negative controls.

3. **`FINAL_REPORT.md`** — new §H39 and a rewritten `## Next Task` section; the `Summary
   statistics` test count is re-baselined (1115 → 1170).

4. **`NEXT_TASK.md`**, **`HANDOFF_CURRENT_SESSION.md`**, **`HANDOFF_CURRENT.md`**, this file.

No published artifact, gate threshold, verdict, certified number or published row was modified;
no grid was re-run; no hypothesis was added; `run_*.py` was not touched.

## What was actually verified

- `python -m pytest -q -W error` → **1170 passed, 1 skipped** (baseline before: 1121 passed,
  1 skipped).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → the only deviation is on pre-existing
  lines of `tests/test_runner_causality_inventory.py` that this session did not touch.
- **Injected negative controls**: reverting the Sharpe to the sample std fails **15** of the 55
  contract tests; reverting only the degenerate-series guard fails **2** of them. The engine is
  restored afterwards and `git diff` shows only the intended change.
- Every number quoted in §H39 is read out of the committed artifacts, their committed equity
  curves and the committed H26 audit — nothing was recomputed by re-running anything.
- **The direction of the convention change is pinned to the record**: H26's own audit classifies
  every audited family's published Sharpe as `population_ddof0` with `abs_diff_ddof0 == 0.0`
  (H10, H21, H22, H23, H25). The engine was the only outlier in the package.
- The coverage tool (`pytest-cov` / `coverage`) is **not installed in this environment**, so the
  `src/qtr` 100% figure could not be re-measured here; the engine change adds no new branch (the
  `> 1e-15` branch is covered by the new degenerate-series tests, the other branch by every other
  metric test).

## The finding in one paragraph

The engine and `qtr.validation.statistics` divided the mean excess return by *different* standard
deviations — the engine by the **sample** std (pandas, ddof=1), the library by the **population**
std (numpy, ddof=0) — so the same run produced two Sharpes, differing by exactly
`sqrt(n / (n - 1))` (0.02% at n = 2,515). Both were written into the *same* artifact
(`strategy_metrics` vs `validation`), exactly as H38's `total_return` was. A second,
independent disagreement sat in the degenerate-series guard: a constant return series has a std
of ~2.2e-19 from float noise, so the engine's exact-zero test let it through and reported a
Sharpe of 7.3e16 where the library reported 0.0. Both are fixed; the record's convention
(population std, already used by every certified family's published Sharpe) is now the only one
in the package, and no certified number, gate or verdict moves.

## What remains unresolved (disclosures, not rewrites)

- **H9's published OOS Sharpe is on the sample convention** (1.0563828964274808 vs 1.0564855126690582
  under the population convention; gap 1.026e-04). H26 excluded H9 from its audit for that
  reason. The gap cannot move H9's verdict: its margin over its 1.0 Sharpe gate is 5.6e-02 (55×
  the gap) and its published row is a REJECT on the profit factor.
- **The runners compute the same metrics a third time** — six near-duplicate `_period_metrics`
  helpers (H10, H16, H17, H19, H20, H23) whose drawdown uses `cum / cum.cummax() - 1` against
  the library's `(equity - rolling_max) / rolling_max` (≤ 5.6e-17 apart), plus
  `run_h26_sharpe_scale_audit.py:303`'s sample-std daily Sharpe. This is the next task.
- **H18's runner-local `total_return` copy** (`run_h18_overnight_intraday_experiment.py:526`,
  `:637`) still uses the pre-H38 range; the H18 artifacts are frozen, so it stays. Bounded: 6.34
  bps on the published full-period `total_return` of the selected row; H18's OOS `total_return`
  is consistent with its own OOS return series and with the committed equity curve; H18's nine
  gates do not use `total_return`.
- The pre-fix `strategy_metrics` / `benchmark_metrics` values of the five affected artifacts
  (including their sample-std Sharpes) are history and are now pinned by tests.

## Approaches already tried / failed (this session)

- **Re-running a grid to quantify the impact was not attempted and is forbidden.** Every number
  in §H39 is read out of the committed artifacts, their committed equity curves and the committed
  H26 audit, which is both cheaper and stronger.
- **"Normalising the volatility convention too" was rejected**: `annualized_volatility` keeps the
  sample std because that is the convention `validate_strategy` uses for it and the one the
  published artifacts record; changing it would break the agreement in the other direction and
  move a published number for no reason.
- **Rewriting the runners' local metric helpers in place was rejected**: the artifacts are
  frozen, so a rewritten helper would no longer reproduce them. The copies are to be classified
  and pinned, not replaced.

## Precise next task (one task)

**Extend the metric-agreement contract from the library to the runners' own metric
implementations — the six near-duplicate `_period_metrics` helpers and their siblings.**

*Evidence.* The repository computes the Sharpe, the profit factor and the max drawdown a third
time, in the runners: `run_h10_intraday_tsmom_pfopt_experiment.py:243`,
`run_h16_factor_timing_experiment.py:218`, `run_h17_vrp_experiment.py:157`,
`run_h19_volume_predictive_experiment.py:192`, `run_h20_signed_volume_experiment.py:211` and
`run_h23_crypto_futures_tsmom.py:245` each carry their own `_period_metrics(ret, n_trades)`.
Their Sharpe and profit factor match the library exactly; their **max drawdown uses a different
formula** (`cum / cum.cummax() - 1` against the library's
`(equity - rolling_max) / rolling_max`), a difference of up to 5.6e-17 measured over 200 random
equity curves. `run_h26_sharpe_scale_audit.py:303` publishes a daily Sharpe on the **sample**
convention (the same split H39 just closed in the engine), and
`run_cs_momentum_experiment.py:383` computes a local information ratio on the population
convention (consistent with `compare_to_benchmark`, but unpinned).

*Deliverable.* An executable contract in the style of
`tests/test_engine_metric_agreement.py` and `tests/test_runner_causality_inventory.py`: an
inventory of every metric the runners compute locally, classified and pinned, where each entry
asserts exact agreement with the library or pins the documented difference with its exact
formula and its bounded effect on the published artifacts. A new runner-local metric helper must
fail the suite.
