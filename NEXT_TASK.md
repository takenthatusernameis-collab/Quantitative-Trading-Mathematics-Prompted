# Next Task

## State

H35–H60 complete. **H60 is complete**: a real defect in `src/qtr` was found by exercising the
package's own cross-module agreement contract against an input the record contains, and it is
fixed. `validate_strategy` annualized the total return with `(1 + total_return) ** (252 / n) - 1`
and had no guard on the base; the engine's own implementation guards the same expression with
`if gross > 0.0: ... else: -1.0`. When the gross value was **zero or negative** (the equity curve
goes negative, as the H58 contaminated families' `ensemble_equity.parquet` does, bottoming out
at **-463,814.84** on a 1,000,000 capital base), `validate_strategy` emitted **`nan`** with a
`RuntimeWarning`, so the two implementations disagreed on an input the record actually contains.
The guard is now mirrored in `validate_strategy`, and the contract is extended to cover the
`gross < 0` regime with a behavioural negative control. **No published artifact, gate threshold,
verdict or certified number was modified; no grid was re-run; no hypothesis was added.** The
H47–H60 series is complete.

## What remains assigned

Nothing. Every remaining unresolved item in `FINAL_REPORT.md` (§H53–§H60) is a value that is **not
a function of the committed record** — missing inputs, disclosed convention differences, or
benchmarks/trade logs/signals never committed. None of them can be implemented or verified from this
checkout; they stay disclosed, not quantified, and no gate reads any of them. The dividend/distribution
gap remains omitted (price-return basis) and is disclosed by H57.

The next session inherits a green baseline:

- `python -m pytest -q -W error` → **2 056 passed, 13 skipped** (full suite).
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


## What changed (H60)

**H60:** a real defect in `src/qtr`, found by exercising the package's own cross-module agreement
contract against an input the record contains. It is the first change under `src/qtr` since §H58.

- `src/qtr/validation/statistics.py` — `validate_strategy`'s annualized return now mirrors the
  engine's guard: `ann_return = (gross ** (252 / len(returns)) - 1) if gross > 0.0 else -1.0`,
  where `gross = 1.0 + total_return`. One statement and one branch added to the package
  (coverage 1 086 statements, 330 branches, 100.00%).
- `tests/test_engine_metric_agreement.py` — `test_agreement_holds_when_the_curve_goes_negative`
  (parametrized over `loss ∈ {-1.5, -2.0, -10.0}`) and the negative control
  `test_the_contract_rejects_a_nan_annualized_return`, which reconstructs the pre-fix `nan` and
  shows the contract rejecting it. **59 tests** (up from 56).
- `FINAL_REPORT.md` — new **§H60** section.
- `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`, `HANDOFF_NEXT.md` updated.

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
- Re-run `tests/test_runner_causality_inventory.py`, `tests/test_runner_metric_agreement.py` and
  `tests/test_benchmark_gate_contract.py` after any change in a runner or under
  `src/qtr/validation`.
- The coverage gate (`python -m pytest -q --cov=qtr --cov-branch`) must stay at 100% for
  `src/qtr`; the lint gate (`python -m ruff check src tests run_*.py` and
  `python -m ruff format --check src tests run_*.py`) must stay clean.