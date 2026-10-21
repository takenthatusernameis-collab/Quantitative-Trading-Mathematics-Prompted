# HANDOFF_NEXT — H51: `compare_to_benchmark` is container-independent

## What changed (this session)

- `src/qtr/validation/statistics.py` — `compare_to_benchmark` reduces **both** sides to plain float
  numpy arrays *before* any statistic is computed, and every standard deviation carries an explicit
  `ddof`. The excess volatility (and the information ratio) is taken on **`ddof=0`** (population).
  The docstring states the convention and the container-independence contract.
- `tests/test_h51_benchmark_container_invariance.py` — **new**, 246 tests (12 skipped for documented
  reasons).
- `FINAL_REPORT.md` — new **§H51** section, an updated "Next task" section and an updated "What
  remains unresolved".

## The gap (three container dependencies, not one)

`compare_to_benchmark` built the excess series with the *caller's* container, so the information ratio
and the excess volatility were a function of *how the caller stored its data*:

1. **`excess.std()`** — `pandas.Series.std()` defaults to `ddof=1` (sample) and
   `numpy.ndarray.std()` to `ddof=0` (population). The same data compared as an array and as a
   Series gave `0.2650139223426122` and `0.2646824476383493` — a ratio of exactly
   `sqrt(n / (n - 1))`.
2. **`strat.mean()` / `bench.mean()`** — `pandas.Series.mean()` is a *different reduction* from
   `numpy.ndarray.mean()` whenever pandas is built with bottleneck, so `alpha_annualized` was
   environment-dependent.
3. **the excess series itself** — `pandas.Series - pandas.Series` aligns on the **INDEX**, while
   `ndarray - ndarray` subtracts **POSITIONALLY**, although the function has always aligned the two
   sides by *length* (tail alignment). For a mismatched index the old subtraction silently
   introduced NaNs the `valid` mask (built before it) could not see.

All three are closed by the same change: reduce both sides to numpy arrays **once**, up front.

## Why `ddof=0` — the measured reasons

1. **It keeps the larger set of published numbers unchanged.** Of the **48** committed artifacts
   that publish an `information_ratio`, **26** were produced on `ddof=0` and **22** on `ddof=1` —
   every one re-derived from its own frozen artifact.
2. **It is this package's own convention** (`sharpe_ratio` takes `returns.std(ddof=0)`).
3. **It preserves an existing pin** — `tests/test_runner_metric_agreement.py` asserts that
   `run_cs_momentum`'s local IR and the library's agree exactly on the numpy `ddof=0` convention.
   That agreement held only because the test passes `.values`; it was never a property of the
   library.
4. **It is numpy's default.**

The 22 published values on the other convention move by exactly `sqrt(n / (n - 1))`: **+4.371e-05**
at `n = 11441` and **+1.671e-03** at `n = 300` (H23). No sign changes, so no gate outcome moves.
The published numbers are **disclosed**, not rewritten.

## Two facts worth recording

- **An equity curve has to be inverted against the initial capital.** The engine builds
  `equity = (1 + r).cumprod() * capital`, so the first row already carries the first bar's return:
  `pct_change()` alone loses it and shifts every later row by one. Recovering it
  (`equity[0] / capital - 1`) is what makes the H9 value re-derive to 1.2e-14 instead of 6.4e-05.
- **Three families cannot be discriminated by the data.** ts_momentum, cs_momentum and
  regime_gated published `round(information_ratio, 4)`; the two conventions differ by ~2e-4
  relative at `n = 1257`, so the rounding hides them. Their convention is pinned by the runner's
  **call site** instead — an expression that reaches a `.values` attribute hands the library an
  array — and the contract checks that statically.

## What was actually verified

- `python -m pytest -q -W error tests/test_h51_benchmark_container_invariance.py` → **246 passed,
  12 skipped** (4 skips: the runner published a default `p_value`; 8 skips: the IR was published
  rounded to four decimals).
- `python -m pytest -q -W error` → **1623 passed, 13 skipped** (full suite, up from 1377 + 1).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **94 files already formatted**.
- **The re-derivation is exact** — residual 0.0e+00 for H21/H22/H25, 4.4e-16 for H23, ~1e-15 for
  H16/H17/H19/H20 and the futures families, ~1e-14 for the equity-derived benchmark families. The
  published `alpha_p_value` re-derives with the same residual.
- **Negative control** — the reconstructed pre-H51 implementation was container-dependent and
  reproduces each artifact's published IR *only* under the container its runner passed; the fixed
  library returns one answer for both containers.

## The published record is unaffected

No published artifact, gate threshold, verdict or certified number was modified; no grid was
re-run; no hypothesis was added. The only change under `src/qtr` is in
`src/qtr/validation/statistics.py`, confined to `compare_to_benchmark`; the `beta`/`alpha` path
(`np.cov(..., ddof=1)` over `np.var(..., ddof=1)`) is untouched, and no runner was touched.

## What a next session inherits

- **One task is assigned (H52)** — stated in full in `NEXT_TASK.md`: extend the **H47
  cost-attribution disclosure** from the single artifact it is pinned for to **every** committed
  trade log, and state which artifacts the pre-fix attribution actually changes. The measurement
  behind it: `git ls-files ".experiments/artifacts/*/trades.parquet"` → **41** trade logs, and in
  **all 41** `groupby("timestamp")["cost"].nunique() == 1` — every bar records one aggregate cost
  for all of its trades. A bar holding a single trade cannot be mis-attributed, so the disclosure
  must separate "carries the pre-fix attribution" from "the pre-fix attribution changes a number
  here".
- The runner-up (H53) is to audit the remaining committed `summary.json` files for keys that no
  longer re-derive from the artifacts that published them.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified families
  are frozen.
- **The 22 published `information_ratio` values on the sample convention no longer re-derive** —
  disclosed in §H51, not rewritten.
- **H9's published OOS Sharpe** is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict frozen.
