# Next Task

## State

H35–H51 complete (the coverage gate is measured, declared and complete at 100% statement + branch;
the package's public API and the runners' import surface are both declared and pinned; the engine's
trade log reconciles with the costs it charges; the package's stochastic surface is seedable; the
published validation blocks re-derive from the frozen artifacts; the package's metadata has exactly
one declared source of truth; **`compare_to_benchmark` is container-independent and the published
convention split is disclosed**).
**H51 is complete**: `compare_to_benchmark` reduces both sides to float numpy arrays before any
statistic is computed, takes every standard deviation with an explicit `ddof`, and enforces the
**population** convention (`ddof=0`) for the excess volatility and the information ratio. The
arrangement is pinned by `tests/test_h51_benchmark_container_invariance.py` (246 tests).

## What changed (H51)

- `src/qtr/validation/statistics.py` — `compare_to_benchmark` reduces both sides to plain float numpy
  arrays **once**, up front; every standard deviation carries an explicit `ddof`; the excess
  volatility and the information ratio are taken on **`ddof=0`** (population). The docstring states
  the convention and the container-independence contract.
- `tests/test_h51_benchmark_container_invariance.py` — **new**, 246 tests (12 skipped for documented
  reasons).
- `FINAL_REPORT.md` — new **§H51** section, an updated "Next task" section and an updated "What
  remains unresolved".
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT_SESSION.md`, `HANDOFF_NEXT.md` updated.

## What was actually verified

- `python -m pytest -q -W error tests/test_h51_benchmark_container_invariance.py` → **246 passed,
  12 skipped** (4 skips: the runner published a default `p_value` rather than a t-test p-value;
  8 skips: the runner published `round(information_ratio, 4)`).
- `python -m pytest -q -W error` → **1623 passed, 13 skipped** (full suite, up from 1377 + 1).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **94 files already formatted**.
- **The published record was re-derived, not assumed.** All 48 committed artifacts that publish an
  `information_ratio` were re-derived from their own frozen artifact (strategy series from the
  artifact's own returns/equity parquet, benchmark from `benchmark_returns.parquet` /
  `benchmark_equity.parquet`, OOS window from the runner's own `TRAIN_END`; an equity curve is
  inverted the way the engine builds it, so the first bar's return is recovered). The residual is
  **0.0e+00** for H21/H22/H25, 4.4e-16 for H23, ~1e-15 for H16/H17/H19/H20 and the futures
  families, and ~1e-14 for the equity-derived benchmark families. The published `alpha_p_value`
  re-derives with the same residual.
- **The convention split is measured**: **26** published IRs on `ddof=0`, **22** on `ddof=1`. The
  enforced convention keeps the larger set unchanged, and moves the other 22 by exactly
  `sqrt(n / (n - 1))`: **+4.371e-05** at `n = 11441`, **+1.671e-03** at `n = 300` (H23). **No sign
  changes**, so no gate outcome moves.
- **Negative control** — the contract reconstructs the **pre-H51 implementation** and shows it was
  container-dependent: the same data gives `0.2646824476383493` as a Series and `0.2650139223426122`
  as an array (ratio exactly `sqrt(n / (n - 1))`), and the pre-fix code on each artifact's own data
  reproduces that artifact's published IR *only* under the container its runner passed.

## The corrected finding

Three container dependencies were found in `compare_to_benchmark`, not one:

1. **`excess.std()`** — `ddof=1` for a `pandas.Series`, `ddof=0` for an `ndarray`. This is the
   assigned defect.
2. **`strat.mean()` / `bench.mean()`** — `pandas.Series.mean()` is a *different reduction* from
   `numpy.ndarray.mean()` whenever pandas is built with bottleneck (bottleneck's `nansum` is not
   numpy's pairwise sum), so `alpha_annualized` was environment-dependent.
3. **the excess series itself** — `pandas.Series - pandas.Series` aligns on the INDEX,
   `ndarray - ndarray` subtracts POSITIONALLY. The function has always aligned by *length* (tail
   alignment), so the index alignment was never what its contract meant, and a mismatched index
   silently introduced NaNs the `valid` mask (built before the subtraction) could not see.

All three are closed by the same change: reduce both sides to numpy arrays once, up front.

## What remains unresolved

- **The 22 published `information_ratio` values on the `ddof=1` convention no longer re-derive from
  the library.** They are disclosed in §H51 (moves of `+4.371e-05` and `+1.671e-03`), not rewritten;
  the artifacts are frozen. The gate's outcome is unaffected in every case.
- **The H47 cost-attribution disclosure covers less than the record does.** §H47 publishes that the
  `cost` column of "the committed trade logs (H10, H11, H16, H21, H22, H25)" carries the pre-fix
  aggregate attribution, and `tests/test_trade_log_cost_reconciliation.py` pins that disclosure for
  **one** artifact (H10). A read-only scan of the repository's committed artifacts
  (`git ls-files ".experiments/artifacts/*/trades.parquet"` → **41** trade logs) shows that
  **every** one of them carries the pre-fix attribution: in each, all trades of a bar record the
  same number (`groupby("timestamp")["cost"].nunique() == 1` holds for all 41). The published list is
  therefore **narrower than the truth**, and the disclosure is pinned for one of them. The measured
  scope, from the same scan:

  | artifact | trades | bars | bars with >1 trade | pre-fix attribution |
  |---|---|---|---|---|
  | `exp_2026-10-10T17-02-22-080026Z` | 257 | 231 | 21 | yes |
  | `exp_2026-10-11T15-53-31-819888Z` | 31,519 | 11,029 | 9,216 | yes |
  | `exp_2026-10-11T17-41-18-169363Z` (H10) | 3,701 | 2,975 | 513 | yes |
  | `exp_2026-10-13T23-27-52-101656Z` | 12,624 | 6,335 | 2,897 | yes |
  | `exp_2026-10-14T07-12-35-292010Z` | 4,980 | 2,695 | 830 | yes |
  | `exp_2026-10-10T17-05-58-697503Z` | 1 | 1 | 0 | n/a (single trade: the attributions coincide) |

  (excerpt; the full set is 41 logs and 80 committed `summary.json` files.)
- **H9's published OOS Sharpe** is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict cannot move (REJECT on the profit factor, 55× margin over its 1.0 gate).
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified families'
  numbers and verdicts are frozen.

## Approaches already tried / failed (and why)

- **Fixing the H10 trade-log cost by changing the charge** — rejected: the charge was never wrong.
  The H27 `L3` check proves it (the per-bar cost recomputed from the trade log matches the engine's
  per-bar cost to ~1e-19 for all five audited families). Only the *attribution* inside the log was
  wrong, so the fix moves the log, not the charge.
- **A negative control that only asserted the new API exists** — rejected for the same reason in
  H47/H48/H50: the control must be behavioural, not a missing-keyword error.
- **Enforcing `ddof=1` (the sample convention) instead** — rejected on measured grounds: it would
  move **26** published numbers instead of 22, it would contradict this package's own
  `sharpe_ratio` (which uses `ddof=0`), and it would require weakening the existing
  `tests/test_runner_metric_agreement.py` pin that the library's IR and `run_cs_momentum`'s local IR
  agree exactly.
- **Deriving the benchmark from `equity.pct_change()` alone** — rejected after measurement: the
  engine builds `equity = (1 + r).cumprod() * capital`, so the first row already carries the first
  bar's return and `pct_change` loses it (and shifts every later row by one). The equity has to be
  inverted against the initial capital; only then does the H9 value re-derive to 1.2e-14 instead of
  6.4e-05.
- **Fixing the H10 trade-log cost by changing the charge** — (duplicate of the first bullet; kept as
  the standing rejection for the H52 family.)

## Constraints carried forward

- No published artifact, gate threshold, verdict or certified number may be modified.
- No grid may be re-run; the H1–H30 hypothesis space remains exhausted.
- The package's public API (§H45) is pinned by `tests/test_public_api_contract.py`; re-run it
  after any change under `src/qtr`.
- The runners' import surface (§H46) is pinned by `tests/test_runner_import_contract.py`; re-run
  it after any change in a runner or under `src/qtr`.
- The engine's trade-log reconciliation (§H47) is pinned by
  `tests/test_trade_log_cost_reconciliation.py`; re-run it after any change under
  `src/qtr/backtest`.
- The seeded reproducibility of `parameter_sensitivity` (§H48) is pinned by
  `tests/test_parameter_sensitivity_reproducibility.py`; re-run it after any change under
  `src/qtr/validation`.
- The published validation blocks (§H49) are pinned by
  `tests/test_h49_validation_block_disclosure.py`; re-run it after any change under
  `src/qtr/validation`.
- The metadata source of truth (§H50) is pinned by
  `tests/test_generated_manifest_contract.py`; re-run it after any change to `pyproject.toml`,
  `.gitignore` or the packaging layout.
- **The container-independence of `compare_to_benchmark` and the published convention split (§H51)
  are pinned by `tests/test_h51_benchmark_container_invariance.py`; re-run it after any change under
  `src/qtr/validation`.**
- Re-run `tests/test_runner_causality_inventory.py`, `tests/test_runner_metric_agreement.py` and
  `tests/test_benchmark_gate_contract.py` after any change in a runner or under
  `src/qtr/validation`.
- The coverage gate (`python -m pytest -q --cov=qtr --cov-branch`) must stay at 100% for
  `src/qtr`; the lint gate (`python -m ruff check src tests run_*.py` and
  `python -m ruff format --check src tests run_*.py`) must stay clean.

## The next task (H52)

> **Extend the H47 cost-attribution disclosure from the one artifact it is pinned for to every
> committed trade log, and state which artifacts the pre-fix attribution actually changes.**

### The gap (measured)

The engine charges a transaction cost **per bar** and, since H47, attributes it **per trade**. The
committed trade logs were written **before** that change, so in each of them every trade of a bar
records the bar's whole cost. §H47 discloses this for "the committed trade logs (H10, H11, H16, H21,
H22, H25)" and pins it for **one** artifact (H10) in
`tests/test_trade_log_cost_reconciliation.py`.

The record is wider than the disclosure: a read-only scan of the committed artifacts finds **41**
trade logs (`git ls-files ".experiments/artifacts/*/trades.parquet"`), and in **all 41**
`groupby("timestamp")["cost"].nunique() == 1` — every bar records one aggregate cost for all of its
trades. The published list is therefore narrower than the truth, and the disclosure is pinned for one
of the 41.

The scope is not uniform, and that is the point of the task: a bar that holds a single trade cannot
be mis-attributed, so the pre-fix attribution only *changes* anything for the logs that have **bars
with more than one trade**. The measured excerpt:

| artifact | trades | bars | bars with >1 trade | pre-fix attribution |
|---|---|---|---|---|
| `exp_2026-10-10T17-02-22-080026Z` | 257 | 231 | 21 | yes |
| `exp_2026-10-11T15-53-31-819888Z` | 31,519 | 11,029 | 9,216 | yes |
| `exp_2026-10-11T17-41-18-169363Z` (H10) | 3,701 | 2,975 | 513 | yes |
| `exp_2026-10-13T23-27-52-101656Z` | 12,624 | 6,335 | 2,897 | yes |
| `exp_2026-10-14T07-12-35-292010Z` | 4,980 | 2,695 | 830 | yes |
| `exp_2026-10-10T17-05-58-697503Z` | 1 | 1 | 0 | n/a (single trade: the attributions coincide) |

### The work

1. **Measure the whole record, not an excerpt** — scan every committed trade log and record, per
   artifact: the number of trades, the number of bars, the number of bars holding more than one
   trade, and whether the log carries the pre-fix aggregate attribution (the per-bar
   `groupby("timestamp")["cost"].nunique() == 1` test). The per-bar cost must still reconcile with
   the engine's charge — that check already exists in `tests/test_trade_log_cost_reconciliation.py`
   and must keep passing; the attribution is a separate question from the charge.
2. **Publish the corrected scope** in `FINAL_REPORT.md`: the full list of the 41 logs, which of them
   the pre-fix attribution actually *changes* (those with multi-trade bars), and which do not (single
   trade per bar, where the attributions coincide by construction).
3. **Extend the pin** — `tests/test_trade_log_cost_reconciliation.py` currently pins the disclosure
   for one artifact. Extend it to the whole set: every committed trade log that carries the pre-fix
   attribution must be *named*, and the set of logs where the attribution changes a number must be
   pinned separately. A log that is **not** in the set and does not carry the attribution must fail.
4. **Correct the §H47 wording** where it enumerates "H10, H11, H16, H21, H22, H25", so the published
   disclosure and the pinned set agree with the measured record.

### Constraints

- No published artifact may be modified: the trade logs are frozen and the `cost` column is part of
  the record. The task is to **disclose the true scope**, not to rewrite the logs.
- The engine's per-bar charge must not move — the H27 `L3` check (per-bar cost recomputed from the
  trade log matches the engine's per-bar cost to ~1e-19) must keep passing for every audited family.
- The disclosure must distinguish "the log carries the pre-fix attribution" from "the pre-fix
  attribution changes a number in this log": a log whose bars each hold a single trade is affected
  in neither sense.

### The runner-up (H53, if H52 is closed)

Audit the remaining committed `summary.json` files for keys that no longer re-derive from the
artifacts that published them — the H49/H51 methodology generalised to every published block, with
the per-key convention of each publisher recorded.
