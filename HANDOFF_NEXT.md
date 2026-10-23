# HANDOFF_NEXT — H60 complete: one real defect fixed under src/qtr

## What changed (H60)

**H60:** a real defect in `src/qtr`, found by exercising the package's own cross-module agreement
contract against an input the record contains. It is the first change under `src/qtr` since §H58.

`validate_strategy` annualized the total return with `(1 + total_return) ** (252 / n) - 1` and had no
guard on the base. The engine's own implementation (`VectorizedBacktester._calculate_metrics`,
engine.py:381-382) guards the same expression with `if gross > 0.0: ... else: -1.0`, because a
fractional power of a non-positive base is not a real number. When the gross value
`1 + total_return` was **zero or negative**, `validate_strategy` emitted **`nan`** with a
`RuntimeWarning: invalid value encountered in scalar power`, so the two implementations disagreed
on an input the record actually contains:

```
gross = -0.8562   (equity curve goes negative)
engine annualized_return =  -1.0
validate annualized_return = nan
```

The input class is real. The H58 contaminated families (`exp_2026-10-10T21-58-28-353634Z` and
`exp_2026-10-10T21-59-16-546117Z`) publish an `ensemble_equity.parquet` whose minimum is
**-463,814.84** on a 1,000,000 capital base: their equity curve goes negative. Their summaries do not
publish `annualized_return`, so **no published number moved** -- but `run_baseline.py:192` and
`run_experiment.py:217` both feed `validate_strategy` the engine's returns, so any future run that
loses more than its capital would have produced a `nan` annualized return alongside a `-1.0` from
the engine.

- `src/qtr/validation/statistics.py` — `validate_strategy` now mirrors the engine's guard exactly:
  `ann_return = (gross ** (252 / len(returns)) - 1) if gross > 0.0 else -1.0`, where
  `gross = 1.0 + total_return`. The docstring records that the two implementations must agree for
  every input, including the negative-gross case, and cites the agreement contract.
- `tests/test_engine_metric_agreement.py` — `test_agreement_holds_when_the_curve_goes_negative`
  (parametrized over `loss ∈ {-1.5, -2.0, -10.0}`) and the negative control
  `test_the_contract_rejects_a_nan_annualized_return`, which reconstructs the pre-fix `nan` and
  shows the contract rejecting it. **59 tests** (up from 56).

## The blast radius

The change is a one-line guard that only fires for `gross <= 0`. For every input with `gross > 0`
the arithmetic is bit-identical to before, so every published `annualized_return` that re-derives (the
11 summaries that publish it, all with positive gross) is unchanged; no gate, threshold, verdict or
certified number reads `validate_strategy`'s `annualized_return`; and the certified families (H10,
H21, H22, H25) are unaffected -- none of their equity curves goes negative.

## What was actually verified

- `python -m pytest -q -W error tests/test_engine_metric_agreement.py` → **59 passed**.
- `python -m pytest -q -W error` → **2 056 passed, 13 skipped** (full suite, up from 2 052 + 13).
- `python -m pytest -q --cov=qtr --cov-branch` → `src/qtr` = **1 086 statements, 330 branches,
  0 missed, 0 partial, 100.00%** (up from 1 085 / 330: one statement and one branch in the guard).
- `python -m ruff check src tests run_*.py` → *All checks passed!*; `ruff format --check` →
  **103 files already formatted**.
- The negative control fires: the pre-fix `nan` is rejected by the agreement contract with
  `assert annualized_return disagrees`.
- No published artifact, gate threshold, verdict or certified number was modified; no grid was
  re-run; no hypothesis was added.

## What a next session inherits

- **No task is assigned.** The H47–H60 series is complete; every remaining unresolved item in
  `FINAL_REPORT.md` (§H53–§H60) is a value that is not a function of the committed record (a
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

(End of file - total 66 lines)