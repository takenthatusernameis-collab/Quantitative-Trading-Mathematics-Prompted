# H74 — degenerate-input guards in `statistics.py`

## What changed

The carried-forward task from `NEXT_TASK.md` (run the full verification gates
after H73) was executed first and confirmed the baseline is green at HEAD
`b41d3d1`. While running it, the H67–H72 defect class (unguarded division /
degenerate input booked as a number instead of a sentinel) was hunted in
the one `src/qtr` module H73 explicitly did **not** probe —
`src/qtr/validation/statistics.py`, the largest numeric surface in the
package (963 lines, ~12% coverage before this suite). Three defects were
reproduced by hand before any code change and all three are fixed.

**`src/qtr/validation/statistics.py`** (+37 lines, all guards):

1. `stressed_cost_test` — an empty `stress_multipliers` dict previously hit
   `sum(...) / len(stress_multipliers)` → `ZeroDivisionError`. Now returns
   `{"stressed_combined_sharpe": sharpe_ratio(base_returns - base_costs)}`
   (costs applied once, i.e. a stress factor of 1.0 — the identity of the
   multiplication the combined line performs).

2. `parameter_sensitivity` — an empty `param_values` previously hit
   `np.argmax(metrics)` → `ValueError: attempt to get argmax of an empty
   sequence`, and the stability ratio would have divided by
   `n_params == 0`. Now returns the zero-initialised result shape with
   `optimal_param = optimal_metric = nan`, `stability_ratio = 0.0`,
   `metric_std = 0.0`. A one-row grid is not degenerate (pinned separately).

3. `statistical_power_analysis` — a non-positive `effect_size` previously
   raised `RuntimeWarning: divide by zero` then
   `OverflowError: cannot convert float infinity to integer`. Now returns
   `0` ("the experiment is unpowerable"); a caller gating on `n > 0` fails
   closed.

**`tests/test_statistics.py`** (+54 lines, 4 new tests):

- `TestParameterSensitivity::test_empty_grid_returns_no_data_sentinel`
- `TestParameterSensitivity::test_single_parameter_grid_is_not_degenerate`
- `TestStressedCostTest::test_empty_stress_map_is_not_a_division_by_zero`
- `TestStatisticalPowerAnalysis::test_non_positive_effect_size_is_unpowerable`

## What was verified

- **Negative control:** each new test fails on the pre-fix code with the
  exact defect it pins — `ValueError: attempt to get argmax of an empty
  sequence`, `ZeroDivisionError: division by zero`, and
  `OverflowError: cannot convert float infinity to integer`. Restored the
  fix and all 85 tests in `test_statistics.py` pass.
- `python -m pytest -q -W error` → **2139 passed, 16 skipped** (was 2135;
  +4 are the new tests; the 16 skips are unchanged and all
  intentional/self-declaring).
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` →
  `src/qtr` **1146 statements, 370 branches, 0 missed, 0 partial, 100.00%**
  (was 1140 statements / 364 branches; the guards add statements and
  branches, all covered).
- `python -m ruff check src tests run_*.py` → *All checks passed!*
- `python -m ruff format --check src tests run_*.py` → **104 files already
  formatted**
- Pinned contracts re-run after the change: `test_engine_metric_agreement.py`,
  `test_h53_published_metrics_disclosure`, `test_h54_non_metrics_block_disclosure`,
  `test_h55_nested_metrics_disclosure`, `test_h56_stats_json_echoes`,
  `test_h57_total_return_audit`, `test_h58_price_pathology_contamination`,
  `test_h59_contamination_gate_blast_radius`, `test_runner_causality_inventory`,
  `test_runner_metric_agreement`, `test_benchmark_gate_contract`,
  `test_public_api_contract`, `test_ruff_reproducibility`,
  `test_trade_log_cost_reconciliation`, `test_tsmom_signal` → **942 passed**.
- The guards are strict early-returns placed before any numeric work, so
  for every non-degenerate input the arithmetic is bit-identical to before:
  no published number, gate threshold, verdict or certified number moved.

## Remaining unresolved

- Disclosures in `FINAL_REPORT.md` §H53–§H61 remain unquantified (missing
  committed inputs). No action possible without new committed artifacts.
- H1–H30 exhausted; certified families frozen. H35–H74 complete.

## Failed approaches

- **Empty `stress_multipliers` returning the raw `base_returns` (no cost
  deduction).** Verified empirically: the first guard returned
  `sharpe_ratio(base_returns)`, which disagreed with the cost-adjusted
  baseline the test asserted against. The guard is the identity of the
  combined-stress multiplication (a factor of 1.0), so it must apply
  costs once: `sharpe_ratio(base_returns - base_costs)`.

## Next task

**None assigned.** See `NEXT_TASK.md` for the constraints that carry forward:
no published artifact, gate threshold, verdict or certified number may be
modified; no grid may be re-run; the H1–H30 hypothesis space remains
exhausted; and the pinned contracts listed under "Constraints" must be
re-run after any change under `src/qtr`.

Constraints: qtr is left **uninstalled** (bare clone) — do not
`pip install -e .` unless a test requires it, and restore that state if you
do. Do not modify frozen published numbers/gates under `src/qtr` without
re-running pinned contracts (causality / metric agreement / benchmark gate).