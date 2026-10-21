# Next Task — H41 done: all metric-agreement sites are classified and pinned

## State

**H35, H36, H37, the remaining-runner extension, H38, H39, H40 and H41 are COMPLETE.**

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

## What changed this session (H40 + H41)

**`tests/test_runner_metric_agreement.py`** (42 tests total) — the executable cross-runner
metric-agreement contract:

- **H40 (33 tests):** `TestRunnerMetricInventory`, `TestExactAgreement`,
  `TestBoundedDrawdownVariant`, `TestH26DailySharpeConvention`, `TestContractNegativeControl`,
  plus the `TestInventoryCompleteness` static sweep. Every runner-local metric helper classified
  and pinned.
- **H41 (9 tests):** `TestInlineDrawdownConforming` (4 tests), `TestInlineDrawdownRawVariant`
  (3 tests), `TestH18TotalReturn` (2 tests). Every inline drawdown and total_return site in the
  runners is now pinned: library-conforming sites agree within 1e-15; raw drawdown variants are
  pinned as `differs_convention`; H18's `total_return` copies agree exactly.

No published artifact, gate threshold, verdict, certified number or published row was modified;
no grid was re-run; no hypothesis was added; no `run_*.py` was touched.

## What was actually verified (this session — H41)

- `python -m pytest -q -W error` → **1212 passed, 1 skipped** (baseline before this session:
  1203 passed after H40).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → all format-clean; the only deviation
  across the repo is on pre-existing lines of `tests/test_runner_causality_inventory.py`
  (ruff 0.17.1 style drift).
- `tests/test_engine_metric_agreement.py`, `tests/test_runner_causality_inventory.py` and
  `tests/test_causality_invariant.py` all pass alongside the updated module.

## Constraints carried forward

- No published artifact, gate threshold, verdict or certified number may be modified; no grid
  may be re-run; no new hypothesis (the H1–H30 space is exhausted; the certified families
  H10/H11/H12/H22/H25 are frozen).
- `python -m pytest -q -W error` and `ruff check src tests run_*.py` must pass from a bare
  clone (no install step); keep `src/qtr` at 100% coverage; re-run
  `tests/test_runner_causality_inventory.py` after any change in a `run_*.py`,
  `tests/test_causality_invariant.py` after any change under `src/qtr`,
  `tests/test_engine_metric_agreement.py` after any change to `_calculate_metrics` or to
  `qtr.validation.statistics`, and `tests/test_runner_metric_agreement.py` after any change to
  a runner's local metric helper or inline metric site.

## Next task

None. All assigned tasks (H35–H41) are complete. All metric-agreement sites — library-side
(§H39), runner-local helpers (§H40) and runner-inline sites (§H41) — are classified and pinned.
