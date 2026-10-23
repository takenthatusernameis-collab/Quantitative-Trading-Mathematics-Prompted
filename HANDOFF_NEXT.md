# HANDOFF_NEXT — H61 complete: one real defect fixed under src/qtr

## What changed (H61)

**H61:** a real defect in `src/qtr`, found by exercising the package's own row-filter contract
against a non-finite input. It is the second change under `src/qtr` since §H60.

`compare_to_benchmark` drops the aligned rows where either side is non-finite before computing the
CAPM statistics, because `np.cov`/`np.var` do not skip NaN. The filter was
`valid = ~(np.isnan(strat) | np.isnan(bench))`, and `isnan` is the wrong predicate: an `inf` or
`-inf` is **not a missing value, it is an impossible return**, and `isnan` lets it through. With
an `inf` in the strategy side the result was internally inconsistent:

```
excess.mean()       = inf
excess.std(ddof=0)  = nan      -> information_ratio = 0 (the `excess_std > 0` guard)
alpha_annualized    = nan      (np.cov/var of an inf)
beta                = nan
alpha_p_value       = 1.0      (the `excess.std() > 1e-12` guard fails)
win_rate            = 1.0      (finite fraction of the surviving rows)
excess_return_annual = inf
```

A gate reading any of those fields would see a plausible-looking number while the comparison had
actually broken. The input class is real: every runner that builds a return series from
`prices.pct_change()` can produce an `inf` if a price crosses zero (the H58 pathology) or if a roll
gap is unbounded, and `run_h27_pnl_level_audit.py:443` and `run_h26_sharpe_scale_audit.py` both
call `compare_to_benchmark` on derived series.

- `src/qtr/validation/statistics.py` — the row filter is now `np.isfinite(strat) & np.isfinite(bench)`.
  The docstring records that the predicate is `isfinite`, not `isnan`, and why. For every finite
  input the computation is bit-identical to before.
- `tests/test_statistics.py` — four additions to `TestCompareToBenchmark`:
  - `test_non_finite_rows_are_dropped` — an `inf` row is dropped and all nine keys come back
    finite, reproducing the published CAPM formula on the surviving rows (beta = 1.0, alpha
    annualized = 2.52).
  - `test_nan_rows_are_still_dropped` — the `isnan` case the mask has always handled still works.
  - `test_negative_infinity_rows_are_dropped` — symmetric to the positive case.
  - `test_the_contract_rejects_the_pre_fix_isnan_mask` — a behavioural negative control that
    reconstructs the pre-fix `isnan` filter, feeds it the same input, and requires the result to
    be internally inconsistent (a finite `win_rate` alongside `nan` alpha and `inf` excess return).

## The blast radius

The change is a one-symbol predicate (`isnan` -> `isfinite`) that only fires for a non-finite row.
For every finite input the mask is identical, so every published `information_ratio`,
`alpha_p_value`, `alpha_annualized`, `beta`, `win_rate`, `excess_return_annual` and
`excess_vol_annual` that re-derives is unchanged; no gate, threshold, verdict or certified number
reads a field of `compare_to_benchmark` that could have been affected; and the certified families
(H10, H21, H22, H25) are unaffected.

## What was actually verified

- `python -m pytest -q -W error tests/test_statistics.py` → **77 passed** (73 before).
- `python -m pytest -q -W error` → **2 060 passed, 13 skipped** (full suite).
- `python -m pytest -q --cov=qtr --cov-branch` → `src/qtr` = **1 086 statements, 330 branches,
  0 missed, 0 partial, 100.00%** (unchanged: the predicate swap adds no statement and no branch).
- `python -m ruff check src tests run_*.py` → *All checks passed!*; `ruff format --check` →
  **103 files already formatted**.
- The pinned contracts re-run after the change: `test_engine_metric_agreement.py`,
  `test_h53_published_metrics_disclosure`, `test_h54_non_metrics_block_disclosure`,
  `test_h55_nested_metrics_disclosure`, `test_h56_stats_json_echoes`, `test_h57_total_return_audit`,
  `test_h58_price_pathology_contamination`, `test_h59_contamination_gate_blast_radius`,
  `test_h51_benchmark_container_invariance`, `test_benchmark_gate_contract`,
  `test_runner_metric_agreement`, `test_runner_causality_inventory`,
  `test_parameter_sensitivity_reproducibility`, `test_h49_validation_block_disclosure`,
  `test_public_api_contract`, `test_runner_import_contract`, `test_trade_log_cost_reconciliation`,
  `test_generated_manifest_contract`, `test_gate_vacuity_contract`, `test_coverage_gate_contract` →
  **1 295 passed, 12 skipped**.
- The negative control fires: the pre-fix `isnan` path produces a finite `win_rate` alongside
  `nan` alpha and `inf` excess return, which the contract rejects.
- No published artifact, gate threshold, verdict or certified number was modified; no grid was
  re-run; no hypothesis was added.

## What a next session inherits

- **No task is assigned.** The H47–H61 series is complete; every remaining unresolved item in
  `FINAL_REPORT.md` (§H53–§H61) is a value that is not a function of the committed record (a
  missing input such as the H9 VIX series, or a disclosed convention difference) and none of them
  can be implemented or verified from this checkout. They stay disclosed, not quantified, and no
  gate reads any of them.
- The inherited baseline is green; after any change under `src/qtr`, re-run the pinned contracts
  -- including `test_engine_metric_agreement.py`, `test_h53_published_metrics_disclosure`,
  `test_h54_non_metrics_block_disclosure`, `test_h55_nested_metrics_disclosure`,
  `test_h56_stats_json_echoes`, `test_h57_total_return_audit`,
  `test_h58_price_pathology_contamination` and `test_h59_contamination_gate_blast_radius` -- and
  confirm the gates stay green.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified families
  are frozen.

(End of file — total 66 lines)