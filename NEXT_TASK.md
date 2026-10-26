# Next task — H74: degenerate-input guards in `statistics.py`

## Status

H74 is COMPLETE. Three defects of the H67–H72 class (unguarded division /
degenerate input booked as a number instead of a sentinel) were found in
`src/qtr/validation/statistics.py` -- the module H73 explicitly did **not**
probe -- and all three are fixed with strict early-return guards that are
no-ops on every non-degenerate input.

### What changed

**`src/qtr/validation/statistics.py`** (+37 lines, all guards):

1. `stressed_cost_test` (line 408) — an empty `stress_multipliers` dict
   previously hit `sum(...) / len(stress_multipliers)` → `ZeroDivisionError`.
   Now returns `{"stressed_combined_sharpe": sharpe_ratio(base_returns - base_costs)}`
   (costs applied once, i.e. a stress factor of 1.0 -- the identity of the
   multiplication the combined line performs).

2. `parameter_sensitivity` (line 295) — an empty `param_values` previously hit
   `np.argmax(metrics)` → `ValueError: attempt to get argmax of an empty
   sequence`, and the stability ratio would have divided by `n_params == 0`.
   Now returns the zero-initialised result shape with
   `optimal_param = optimal_metric = nan`, `stability_ratio = 0.0`,
   `metric_std = 0.0`. A one-row grid is not degenerate (pinned).

3. `statistical_power_analysis` (line 754) — a non-positive `effect_size`
   previously raised `RuntimeWarning: divide by zero` then
   `OverflowError: cannot convert float infinity to integer`. Now returns
   `0` ("the experiment is unpowerable"); a caller gating on `n > 0` fails
   closed.

**`tests/test_statistics.py`** (+54 lines, 3 new tests):

- `TestParameterSensitivity::test_empty_grid_returns_no_data_sentinel`
- `TestParameterSensitivity::test_single_parameter_grid_is_not_degenerate`
- `TestStressedCostTest::test_empty_stress_map_is_not_a_division_by_zero`
- `TestStatisticalPowerAnalysis::test_non_positive_effect_size_is_unpowerable`

### What was verified

- **Negative control:** each new test fails on the pre-fix code with the
  exact defect it pins:
  - `test_empty_grid_returns_no_data_sentinel` → `ValueError: attempt to get
    argmax of an empty sequence`
  - `test_empty_stress_map_is_not_a_division_by_zero` → `ZeroDivisionError:
    division by zero`
  - `test_non_positive_effect_size_is_unpowerable` → `OverflowError:
    cannot convert float infinity to integer`
- `python -m pytest -q -W error` → **2139 passed, 16 skipped** (was 2135;
  +4 are the new tests).
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` →
  `src/qtr` **1146 statements, 370 branches, 0 missed, 0 partial, 100.00%**
  (was 1140/364; the guards add statements and branches, all covered).
- `python -m ruff check src tests run_*.py` → *All checks passed!*
- `python -m ruff format --check src tests run_*.py` → **104 files already
  formatted**
- Pinned contracts re-run: `test_engine_metric_agreement.py`,
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

## Constraints

- qtr is left **uninstalled** (bare clone) — the venv used for these gates
  lives under `/home/runner/work/_temp/kilo-tmp/kilo/.venv` and is not part
  of the repo; do not `pip install -e .` unless a test requires it.
- Do not modify frozen published numbers/gates under `src/qtr` without
  re-running pinned contracts (causality / metric agreement / benchmark gate).
- Do not commit unless explicitly asked.