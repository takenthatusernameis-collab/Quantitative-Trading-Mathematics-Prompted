# HANDOFF_CURRENT_SESSION — H51: `compare_to_benchmark` is container-independent

## What changed

- `src/qtr/validation/statistics.py` — `compare_to_benchmark` reduces **both** sides to plain float
  numpy arrays *before* any statistic is computed, and every standard deviation carries an explicit
  `ddof`. The excess volatility (and the information ratio) is taken on **`ddof=0`** (population).
  The docstring states the convention and the container-independence contract.
- `tests/test_h51_benchmark_container_invariance.py` — **new**, 246 tests (12 skipped for documented
  reasons).
- `FINAL_REPORT.md` — new **§H51** section, an updated "Next task" section and an updated "What
  remains unresolved".

### The gap (three container dependencies, not one)

`compare_to_benchmark` built the excess series with the *caller's* container, so the information ratio
and the excess volatility were a function of *how the caller stored its data*:

1. **`excess.std()`** — `pandas.Series.std()` defaults to `ddof=1` (sample) and
   `numpy.ndarray.std()` to `ddof=0` (population). The same data compared as an array and as a
   Series gave `0.2650139223426122` and `0.2646824476383493` — a ratio of exactly
   `sqrt(n / (n - 1))`.
2. **`strat.mean()` / `bench.mean()`** — `pandas.Series.mean()` is a *different reduction* from
   `numpy.ndarray.mean()` whenever pandas is built with bottleneck (bottleneck's `nansum` is not
   numpy's pairwise sum), so `alpha_annualized` was environment-dependent.
3. **the excess series itself** — `pandas.Series - pandas.Series` aligns on the **INDEX**, while
   `ndarray - ndarray` subtracts **POSITIONALLY**. The function has always aligned the two sides by
   *length* (tail alignment, `min_len`), so the index alignment was never what its contract meant —
   and for a mismatched index the old subtraction silently introduced NaNs that the `valid` mask
   (built before it) could not see.

All three are closed by the same change: reduce both sides to numpy arrays **once**, up front.

### The convention: `ddof=0` (population) — and why

1. **It keeps the larger set of published numbers unchanged.** Measured, not estimated: of the **48**
   committed artifacts that publish an `information_ratio`, **26** were produced on `ddof=0` and
   **22** on `ddof=1`.
2. **It is this package's own convention.** `sharpe_ratio` in the same module takes
   `returns.std(ddof=0)`, and the engine's Sharpe does the same.
3. **It preserves an existing, deliberate contract.**
   `tests/test_runner_metric_agreement.py` states that `run_cs_momentum`'s local IR "computes
   `information_ratio = e.mean() / e.std() * sqrt(252)` with numpy `ddof=0`, **the same convention as
   `compare_to_benchmark`'s information_ratio**; the two agree exactly". That agreement held only
   because the test passes `.values` — it was never a property of the library. Enforcing `ddof=0`
   makes the *library* true the statement.
4. **It is numpy's default**, and it is the convention under which a re-run of any runner would now
   reproduce its published IR.

### The disclosure — every published `information_ratio`, re-derived from its own artifact

Each of the 48 published values was re-derived from the artifact that published it: the strategy
series from the artifact's own `returns.parquet` / `best_equity.parquet` / `selected_equity.parquet` /
`ensemble_equity.parquet`, the benchmark from its `benchmark_returns.parquet` /
`benchmark_equity.parquet`, and the OOS window from the runner's own `TRAIN_END`. An equity curve is
inverted to a return series the way the engine builds it (`equity = (1 + r).cumprod() * capital`),
so the first bar's return is recovered rather than lost.

| Family | Artifacts | Call-site container | Published convention | n | Published IR | IR under the enforced convention | Relative change |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H1/H2 ts_momentum | 4 | ndarray | ddof=0 | 1257 | -0.1241 | -0.1241 | +0.000e+00 |
| H3/H4 cs_momentum | 2 | ndarray | ddof=0 | 1257 | -0.2523 | -0.2523 | +0.000e+00 |
| H5 regime_gated | 2 | ndarray | ddof=0 | 1257 | -0.8932 | -0.8932 | +0.000e+00 |
| H4 futures_tsmom | 4 | ndarray | ddof=0 | 1258 | -0.6399266589647274 | -0.6399266589647274 | +0.000e+00 |
| H4 ddcv | 2 | ndarray | ddof=0 | 1258 | 0.3943394550648367 | 0.3943394550648367 | +0.000e+00 |
| H6 vix_ddcv | 4 | ndarray | ddof=0 | 1258 | 0.35981069144282585 | 0.35981069144282585 | +0.000e+00 |
| H8 roll_adjusted | 1 | ndarray | ddof=0 | 1258 | 0.5248619387848141 | 0.5248619387848141 | +0.000e+00 |
| H9 v1 intraday | 1 | Series | ddof=1 | 11441 | -0.23532720855889727 | -0.2353374936142357 | +4.371e-05 |
| H9 v2 intraday | 4 | Series | ddof=1 | 11441 | 1.02096576542838 | 1.0210103870828855 | +4.371e-05 |
| H10 pfopt | 2 | Series | ddof=1 | 11441 | 1.0172449421222174 | 1.0172894011568805 | +4.371e-05 |
| H16 factor_timing | 4 | ndarray | ddof=0 | 1760 | -0.47636726658916473 | -0.47636726658916473 | +0.000e+00 |
| H17 vrp | 1 | ndarray | ddof=0 | 1700 | -0.23962730807881957 | -0.23962730807881957 | +0.000e+00 |
| H19 volume_predictive | 1 | ndarray | ddof=0 | 2958 | -0.8797993277834989 | -0.8797993277834989 | +0.000e+00 |
| H20 signed_volume | 1 | ndarray | ddof=0 | 2958 | -0.7039784403691635 | -0.7039784403691635 | +0.000e+00 |
| H21 multicontract | 1 | Series | ddof=1 | 11441 | 0.9459483422829976 | 0.9459896852756217 | +4.371e-05 |
| H22 voltarget | 5 | Series | ddof=1 | 11441 | 1.3466905696542812 | 1.3467494272216551 | +4.371e-05 |
| H23 crypto | 7 | Series | ddof=1 | 300 | 0.8001285452997962 | 0.8014654360320734 | +1.671e-03 |
| H25 pfmargin | 2 | Series | ddof=1 | 11441 | 1.3458716250016904 | 1.3459304467768110 | +4.371e-05 |

- **26 published numbers are unchanged** and **22 move**, each by exactly `sqrt(n / (n - 1))`. The
  largest movement anywhere in the record is **0.17%** (H23, n = 300).
- **No sign changes**, so **no gate outcome can move**: the direction-aware gate reads
  `information_ratio > 0.0`, and `alpha_p_value` comes from `scipy.stats.ttest_1samp`, which always
  uses `ddof=1` on both paths.
- The three families whose runner published **`round(information_ratio, 4)`** cannot be discriminated
  by the data (the conventions differ by ~2e-4 relative at `n = 1257` and the published value carries
  only four decimals). Their convention is pinned by the runner's **call site**, which the contract
  now checks statically: an expression that reaches a `.values` attribute hands the library an array.
- **No artifact publishes an `excess_vol_annual`**, so there is nothing to disclose on that side.

### The contract now pinned (246 tests, 12 skipped)

1. **Nine keys, one answer** — an array and a Series (and mixed containers, and a `DataFrame`
   benchmark against its row-mean series, and a NaN row) give **bit-identical** values for all nine
   keys.
2. **The convention is the population deviation** — the IR is `mean / std(ddof=0)`, and it is
   provably *not* the sample one.
3. **The disclosure is complete and pinned** — every committed artifact that publishes an IR is in
   the table, the table matches the artifacts, the 26/22 split is pinned, each published value
   re-derives **under the convention it was published on** (and not under the other), the move is
   bounded and never flips a sign, and no gate outcome moves.
4. **The call sites are checked statically** — an expression that reaches `.values` hands the
   library an array; the runners' containers are pinned.
5. **Negative control** — the pre-H51 implementation is reconstructed: it was container-dependent,
   and it reproduces each artifact's published IR *only* under the container its runner passed.

## What was actually verified

- `python -m pytest -q -W error tests/test_h51_benchmark_container_invariance.py` → **246 passed,
  12 skipped** (4 skips: the runner published a default `p_value` rather than a t-test p-value;
  8 skips: the runner published `round(information_ratio, 4)`).
- `python -m pytest -q -W error` → **1623 passed, 13 skipped** (full suite, up from 1377 + 1).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **94 files already formatted**.
- **The re-derivation is exact, not approximate** — residual 0.0e+00 for H21/H22/H25, 4.4e-16 for
  H23, ~1e-15 for H16/H17/H19/H20 and the futures families, ~1e-14 for the equity-derived benchmark
  families. The published `alpha_p_value` re-derives with the same residual.
- **Negative control** — the same data gives `0.2646824476383493` as a Series and
  `0.2650139223426122` as an array under the reconstructed pre-fix code (ratio exactly
  `sqrt(n / (n - 1))`), and the fixed library returns one answer for both.
- `tests/test_runner_metric_agreement.py` and `tests/test_benchmark_gate_contract.py` still pass
  untouched.

## What remains unresolved

- **The 22 published `information_ratio` values on the sample (`ddof=1`) convention no longer
  re-derive from the library.** They are disclosed in the table above, not rewritten; the artifacts
  are frozen. The gate's outcome is unaffected in every case.
- The **H47 cost-attribution disclosure** (the `cost` column of the committed trade logs) is
  narrower than the record: **all 41** committed trade logs carry the pre-fix attribution, and the
  disclosure is pinned for one of them. This is the assigned task (H52).
- **H9's published OOS Sharpe** is on the sample convention; disclosed and pinned, verdict frozen.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified families'
  numbers and verdicts are frozen.
