# Next Task — H39 done: the package's Sharpe implementations agree; the runners' copies are next

## State

**H35, H36, H37, the remaining-runner extension, H38 and H39 are COMPLETE.**

- The engine and `qtr.validation.statistics.validate_strategy` now agree **exactly** on all six
  metrics the package computes twice (`total_return`, `annualized_return`,
  `annualized_volatility`, `sharpe`, `max_drawdown`, `profit_factor`), and the engine-only
  metrics (Sortino, Calmar, max-drawdown duration, average trade cost) are pinned by their exact
  formula (`tests/test_engine_metric_agreement.py`, 55 tests).
- The **Sharpe convention is settled**: the package uses the **population** standard deviation
  (ddof=0), which is what `qtr.validation.statistics.sharpe_ratio` already used and what every
  audited family's published Sharpe uses (H26's own per-family classification, pinned). The
  engine was the only outlier; it now matches.
- The engine's **degenerate-series guard** now carries the record's 1e-15 tolerance, so a constant
  return series yields 0.0 in both implementations instead of 7.3e16 in the engine.
- The five artifacts that carry engine metrics published **two different Sharpes for one run**
  (ratio exactly `sqrt((n-1)/n) = 0.9998011730768697`, n = 2,515). They are frozen history; both
  conventions are pinned against each artifact's own equity curve.
- **H9 is the one family in the record published on the other convention** (sample std, ddof=1);
  the gap is 1.026e-04 against a margin of 5.6e-02 above its 1.0 Sharpe gate, and its published
  row is a REJECT on the profit factor in any case. Disclosed and pinned.

## The next task (one task)

**Extend the metric-agreement contract from the library to the runners' own metric
implementations — the six near-duplicate `_period_metrics` helpers and their siblings.**

*Evidence (measured, not assumed).* H39 closed the disagreement *inside* `src/qtr`. The
repository still computes the same metrics a **third** time, in the runners:

* `run_h10_intraday_tsmom_pfopt_experiment.py:243`, `run_h16_factor_timing_experiment.py:218`,
  `run_h17_vrp_experiment.py:157`, `run_h19_volume_predictive_experiment.py:192`,
  `run_h20_signed_volume_experiment.py:211` and `run_h23_crypto_futures_tsmom.py:245` each carry
  their own `_period_metrics(ret, n_trades)` — six near-identical re-implementations of the
  Sharpe, the profit factor and the max drawdown. Their Sharpe (`sharpe_ratio`) and profit
  factor match the library exactly, but their **max drawdown uses a different formula**:
  `float((cum / cum.cummax() - 1.0).min())` against the library's
  `(equity - rolling_max) / rolling_max` — a difference of up to **5.6e-17** (measured over 200
  random equity curves), i.e. the same quantity computed two ways.
* `run_h26_sharpe_scale_audit.py:303` computes its `daily_aggregated_sqrt252` diagnostic Sharpe
  with the **sample** std (`daily.mean() / daily.std() * np.sqrt(252)`) while the library uses the
  population std — the same convention split H39 just closed in the engine. The file already
  computes *both* conventions at `:191-192`, so the diagnostic is the one place in the record
  that publishes a Sharpe on a convention the library does not use.
* `run_cs_momentum_experiment.py:383` computes a local **information ratio**
  (`e.mean() / e.std() * np.sqrt(252)`) — numpy, ddof=0, i.e. consistent with
  `compare_to_benchmark`; it must be *pinned* as agreeing, not assumed to be.
* `run_ddcv_experiment.py:207,386,443`, `run_futures_tsmom_experiment.py:286,467`,
  `run_h11_robustness_experiment.py:548,648`, `run_h18_overnight_intraday_experiment.py:527,641`
  and `run_h16/h17/h19/h20` compute drawdowns inline, each with its own formula variant
  (`cum / cum.cummax() - 1` vs `(equity - equity.expanding().max()) / equity.expanding().max()`).

*Deliverable.* An executable contract in the style of
`tests/test_engine_metric_agreement.py` and `tests/test_runner_causality_inventory.py`: an
**inventory** of every metric the runners compute locally (Sharpe, Sortino, profit factor, max
drawdown, max-drawdown duration, annualized return and volatility, total return, information
ratio), classified and pinned, where each entry asserts either exact agreement with
`qtr.validation.statistics` / the engine, or pins the *documented* difference with its exact
formula and its bounded effect on the published artifacts. A new runner-local metric helper must
fail the suite, as a new function in an in-scope runner does for the causality inventory.

*Constraints.* No published artifact, gate threshold, verdict, certified number or published row
may be modified; no grid may be re-run; no new hypothesis; the runner-local copies are **not** to
be rewritten in place (the artifacts are frozen, so a rewritten helper would no longer reproduce
them) — they are to be classified, probed and pinned.

## What was actually verified (this session)

- `python -m pytest -q -W error` → **1170 passed, 1 skipped** (baseline 1121 + the 49 new H39
  tests; the skip is the pre-existing `buy_and_hold` skip in H36's module).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → the only deviation is on pre-existing
  lines of `tests/test_runner_causality_inventory.py` that this session did not touch (ruff
  0.17.1 style drift); every line this session added is format-clean.
- **Injected negative controls** (into the engine, then restored; `git diff` shows only the
  intended change): reverting the Sharpe to the sample std fails **15** of the 55 contract tests;
  reverting only the degenerate-series guard to an exact-zero test fails **2** of them.
- No published artifact, gate threshold, verdict, certified number or published row was modified;
  no grid was re-run; no hypothesis was added; `run_*.py` was not touched.
- The coverage tool (`pytest-cov` / `coverage`) is **not installed in this environment**, so the
  `src/qtr` 100% figure could not be re-measured here. The engine change introduces no new
  branch (the `> 1e-15` branch is covered by the new degenerate-series tests, the other branch by
  every other metric test).

## Remaining items (disclosures, not rewrites)

- `run_h18_overnight_intraday_experiment.py:526,637` — the runner-local `total_return` copy
  still uses the pre-H38 range; the H18 artifacts are frozen, so it stays. Bounded: 6.34 bps on
  the published full-period `total_return` of the selected row; H18's OOS `total_return` is
  consistent with its own OOS return series and with the committed equity curve; H18's nine gates
  do not use `total_return`.
- The pre-fix `strategy_metrics` / `benchmark_metrics` values of the five affected artifacts
  (including their sample-std Sharpes) are the historical record of the runs as executed; they
  are now pinned by tests.
- **H9's published OOS Sharpe is on the sample convention** (gap 1.026e-04); the verdict cannot
  move (55× margin over its gate, and a REJECT on the profit factor).

## Constraints carried forward

- No published artifact, gate threshold, verdict or certified number may be modified; no grid
  may be re-run; no new hypothesis (the H1–H30 space is exhausted; the certified families
  H10/H11/H12/H22/H25 are frozen).
- `python -m pytest -q -W error` and `ruff check src tests run_*.py` must pass from a bare
  clone (no install step); keep `src/qtr` at 100% coverage; re-run
  `tests/test_runner_causality_inventory.py` after any change in a `run_*.py`,
  `tests/test_causality_invariant.py` after any change under `src/qtr`, and
  `tests/test_engine_metric_agreement.py` after any change to `_calculate_metrics` or to
  `qtr.validation.statistics`.
