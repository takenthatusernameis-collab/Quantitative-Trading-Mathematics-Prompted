# Next Task

## State

H35–H61 complete. **H61 is complete**: a real defect in `src/qtr` was found by exercising the
package's own row-filter contract against a non-finite input. `compare_to_benchmark` dropped the
aligned rows where either side is non-finite with `valid = ~(np.isnan(strat) | np.isnan(bench))`,
which is the wrong predicate: an `inf` or `-inf` is not a missing value, it is an impossible
return, and `isnan` lets it through. With an `inf` in the strategy side the result was internally
inconsistent -- `win_rate` a finite fraction of the surviving rows, `alpha_p_value` the default
1.0, `excess_return_annual` inf, and `alpha_annualized`/`beta` nan -- which silently voids any gate
reading those fields. The filter is now `np.isfinite(strat) & np.isfinite(bench)`, and the
contract is extended to the non-finite regime with a behavioural negative control that
reconstructs the pre-fix `isnan` mask and shows the result it produced is internally inconsistent.
**No published artifact, gate threshold, verdict or certified number was modified; no grid was
re-run; no hypothesis was added.** The
H47–H61 series is complete.

## What remains assigned

Nothing. Every remaining unresolved item in `FINAL_REPORT.md` (§H53–§H61) is a value that is **not
a function of the committed record** — missing inputs, disclosed convention differences, or
benchmarks/trade logs/signals never committed. None of them can be implemented or verified from this
checkout; they stay disclosed, not quantified, and no gate reads any of them. The dividend/distribution
gap remains omitted (price-return basis) and is disclosed by H57.

The next session inherits a green baseline:

- `python -m pytest -q -W error` → **2 060 passed, 13 skipped** (full suite).
- `python -m pytest -q --cov=qtr --cov-branch` → `src/qtr` = **1 086 statements, 330 branches,
  0 missed, 0 partial, 100.00%**.
- `python -m ruff check src tests run_*.py` → *All checks passed!*; `ruff format --check` → clean
  (**103 files**).

If the next session wants work, the only honest options are (a) wait for newly committed artifacts
that make a disclosed value measurable, or (b) after any change under `src/qtr`, re-run the pinned
contracts listed under "Constraints carried forward" plus `test_engine_metric_agreement.py`,
`test_h53_published_metrics_disclosure`, `test_h54_non_metrics_block_disclosure`,
`test_h55_nested_metrics_disclosure`, `test_h56_stats_json_echoes`, `test_h57_total_return_audit`,
`test_h58_price_pathology_contamination` and `test_h59_contamination_gate_blast_radius`, and
confirm the gates stay green.


## What changed (H61)

**H61:** a real defect in `src/qtr`, found by exercising the package's own row-filter contract
against a non-finite input. It is the second change under `src/qtr` since §H60.

`compare_to_benchmark` drops the aligned rows where either side is non-finite before computing the
CAPM statistics, because `np.cov`/`np.var` do not skip NaN. The filter was
`valid = ~(np.isnan(strat) | np.isnan(bench))`, and `isnan` is the wrong predicate: an `inf` or
`-inf` is **not a missing value, it is an impossible return**, and `isnan` lets it through. With
an `inf` in the strategy side the result was internally inconsistent -- `win_rate` a finite fraction
of the surviving rows, `alpha_p_value` the default 1.0, `excess_return_annual` inf, and
`alpha_annualized`/`beta` nan -- which silently voids any gate reading those fields. The filter is
now `np.isfinite(strat) & np.isfinite(bench)`, and the contract is extended to the non-finite
regime with a behavioural negative control that reconstructs the pre-fix `isnan` mask and shows
the result it produced is internally inconsistent.

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
    be internally inconsistent.

## Constraints carried forward

- No published artifact, gate threshold, verdict or certified number may be modified.
- No grid may be re-run; the H1–H30 hypothesis space remains exhausted.
- The package's public API (§H45) is pinned by `tests/test_public_api_contract.py`; re-run it
  after any change under `src/qtr`.
- The runners' import surface (§H46) is pinned by `tests/test_runner_import_contract.py`; re-run
  it after any change in a runner or under `src/qtr`.
- The engine's trade-log reconciliation (§H47) and the **whole frozen record** (§H52) are pinned
  by `tests/test_trade_log_cost_reconciliation.py`; re-run it after any change under
  `src/qtr/backtest` **or after a new artifact is committed**.
- The seeded reproducibility of `parameter_sensitivity` (§H48) is pinned by
  `tests/test_parameter_sensitivity_reproducibility.py`; re-run it after any change under
  `src/qtr/validation`.
- The published validation blocks (§H49) are pinned by
  `tests/test_h49_validation_block_disclosure.py`; re-run it after any change under
  `src/qtr/validation`.
- The metadata source of truth (§H50) is pinned by `tests/test_generated_manifest_contract.py`;
  re-run it after any change to `pyproject.toml`, `.gitignore` or the packaging layout.
- The container-independence of `compare_to_benchmark` and the published convention split (§H51)
  are pinned by `tests/test_h51_benchmark_container_invariance.py`; re-run it after any change under
  `src/qtr/validation`.
- The published `metrics` block and its per-producer conventions (§H53) are pinned by
  `tests/test_h53_published_metrics_disclosure.py`; re-run it after any change under
  `src/qtr/validation`, `src/qtr/backtest` **or after a new artifact is committed**.
- The cross-module agreement of the engine and `validate_strategy` (§H60) is pinned by
  `tests/test_engine_metric_agreement.py`; re-run it after any change under `src/qtr/backtest` or
  `src/qtr/validation`.
- The non-finite row filter of `compare_to_benchmark` (§H61) is pinned by
  `tests/test_statistics.py`; re-run it after any change under `src/qtr/validation`.
- Re-run `tests/test_runner_causality_inventory.py`, `tests/test_runner_metric_agreement.py` and
  `tests/test_benchmark_gate_contract.py` after any change in a runner or under
  `src/qtr/validation`.
- The coverage gate (`python -m pytest -q --cov=qtr --cov-branch`) must stay at 100% for
  `src/qtr`; the lint gate (`python -m ruff check src tests run_*.py` and
  `python -m ruff format --check src tests run_*.py`) must stay clean.