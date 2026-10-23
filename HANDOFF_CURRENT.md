# HANDOFF_CURRENT — session complete (H61)

## State

- **H61 is COMPLETE** as recorded in `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_NEXT.md` and
  `HANDOFF_CURRENT_SESSION.md`: a real defect in `src/qtr` was found by exercising the package's
  own row-filter contract against a non-finite input, and it is fixed. `compare_to_benchmark`
  dropped the aligned rows where either side is non-finite with `valid = ~(np.isnan(strat) |
  np.isnan(bench))`, and `isnan` is the wrong predicate: an `inf` or `-inf` is not a missing value,
  it is an impossible return, and `isnan` lets it through. With an `inf` in the strategy side the
  result was internally inconsistent -- `win_rate` a finite fraction of the surviving rows,
  `alpha_p_value` the default 1.0, `excess_return_annual` inf, and `alpha_annualized`/`beta` nan
  -- which silently voids any gate reading those fields. The filter is now
  `np.isfinite(strat) & np.isfinite(bench)`, and the contract is extended to the non-finite regime
  with a behavioural negative control that reconstructs the pre-fix `isnan` mask and shows the
  result it produced is internally inconsistent. **No published artifact, gate threshold, verdict
  or certified number was modified; no grid was re-run; no hypothesis was added.**
- **H60 is COMPLETE** (§H60 of `FINAL_REPORT.md`): `validate_strategy`'s annualized return now
  mirrors the engine's guard for `gross <= 0`, so the cross-module agreement contract holds across
  the negative-gross regime the H58 contaminated families land in.
- **H59 is COMPLETE** (§H59 of `FINAL_REPORT.md`): the full gate blast radius of the H58 price
  contamination is measured -- **thirteen** published gate booleans are decided by one negative
  print in a Yahoo continuous-contract splice: it manufactures nine passes (H58) and destroys two
  passes in each of the two strategy-contaminated families. The screen gap H59 closes is that the
  H58 screen screened the *close* only, while the committed H8 artifact shows the same splice
  printed **-14.0** as the **open** of 2020-04-21; `non_positive_prices` now screens **every price
  column** (`open`, `high`, `low`, `close`).
- **H58 is COMPLETE** (§H58 of `FINAL_REPORT.md`): the committed price panels carry a non-positive
  print that reaches the published gates -- **CL=F closes at -37.63 on 2020-04-20** in twenty-one
  committed `prices.parquet` panels, which the engine's `prices.pct_change()` turns into two
  garbage bars (-305.966% and -126.601%). The root-cause fix at the data boundary is
  `non_positive_prices` + `DataFetcher._reject_non_positive_prices`, which refuses a panel carrying
  a non-positive price on every entry point.
- **H57 is COMPLETE** (§H57 of `FINAL_REPORT.md`): the equity record is on a **price-return**
  basis; distributions measured; **3** PDBC level bars; under total-return counterfactual **no
  published gate boolean moved**.
- **H56 is COMPLETE** (§H56 of `FINAL_REPORT.md`): the `stats.json` text echoes (**40** files) and
  the **14** benchmark `avg_trade_cost` entries are measured to the extent the record allows and
  disclosed where it does not.
- **H55 is COMPLETE** (§H55 of `FINAL_REPORT.md`): the four **nested** `metrics` blocks and the
  top-level `perturbation` block re-derive from the frozen record -- **610** of **736** published
  leaf values re-derive, the **126** that do not are named with the reason the record cannot carry
  each one.
- **H53–H54 are COMPLETE**: the published `metrics` block (37 summaries, 450 values, 441
  re-derive) and the published blocks of the **43** summaries that publish no `metrics` block
  (164 top-level keys, 7 785 leaf values) re-derive from their own frozen artifacts.
- **The one pre-existing suite failure is FIXED** (the attribution-fix commit `3fbef17` timestamp
  is pinned and cross-checked against `git` whenever the commit is present).
- No published artifact, gate threshold, verdict or certified number was modified; no grid was
  re-run; no hypothesis was added.

## What changed (this session — H61)

- `src/qtr/validation/statistics.py` — `compare_to_benchmark`'s row filter is now
  `np.isfinite(strat) & np.isfinite(bench)` instead of `~(np.isnan(strat) | np.isnan(bench))`.
  The docstring records that the predicate is `isfinite`, not `isnan`, and why: an `inf` is an
  impossible return, not a missing value, and letting it through is the silent-void failure the
  filter exists to prevent. For every finite input the computation is bit-identical to before.
- `tests/test_statistics.py` — four additions to `TestCompareToBenchmark`:
  - `test_non_finite_rows_are_dropped` — an `inf` row is dropped and all nine keys come back
    finite, reproducing the published CAPM formula on the surviving rows (beta = 1.0, alpha
    annualized = 2.52).
  - `test_nan_rows_are_still_dropped` — the `isnan` case the mask has always handled still works.
  - `test_negative_infinity_rows_are_dropped` — symmetric to the positive case.
  - `test_the_contract_rejects_the_pre_fix_isnan_mask` — a behavioural negative control that
    reconstructs the pre-fix `isnan` filter, feeds it the same input, and requires the result to
    be internally inconsistent (a finite `win_rate` alongside `nan` alpha and `inf` excess return).
  **77 tests** (up from 73).
- `FINAL_REPORT.md` — new **§H61** section.
- `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`, `HANDOFF_NEXT.md`,
  `NEXT_TASK.md` updated.

## What remains unresolved

All remaining items are **disclosed, not quantified** -- each depends on an input the record does
not hold and none can be resolved without new committed inputs. H1–H30 exhausted; certified
families frozen.

(End of file — this file is regenerated each session from the session handoff)