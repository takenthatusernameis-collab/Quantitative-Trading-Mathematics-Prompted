# Next Task

## State

H35–H50 complete (the coverage gate is measured, declared and complete at 100% statement +
branch; the package's public API and the runners' import surface are both declared and pinned; the
engine's trade log reconciles with the costs it charges; the package's stochastic surface is
seedable; the published validation blocks re-derive from the frozen artifacts; the package's
metadata has exactly one declared source of truth).
**H50 is complete**: the setuptools-generated metadata directory `src/qtr.egg-info/` is **untracked**
and ignored, `pyproject.toml` is the only declared source of the package's metadata, and the
arrangement is pinned by `tests/test_generated_manifest_contract.py` (11 tests).

## What changed (H50)

- `.gitignore` — `*.egg-info/` added.
- `src/qtr.egg-info/` — **untracked** (`git rm -r --cached`); the files stay on disk (the editable
  install resolves to them) but they are no longer part of the repository.
- `tests/test_generated_manifest_contract.py` — **new**, 11 tests.
- `FINAL_REPORT.md` — new **§H50** section and an updated "Next task" section.
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`,
  `HANDOFF_NEXT.md` updated.

## What was actually verified

- `python -m pytest -q -W error tests/test_generated_manifest_contract.py` → **11 passed**.
- `python -m pytest -q -W error` → **1377 passed, 1 skipped** (full suite, up from 1366).
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` → `src/qtr` = **1054
  statements, 320 branches, 0 missed, 0 partial, 100.00%** (unchanged — nothing under `src/qtr`
  was touched); the committed gate reports *"Required test coverage of 100.0% reached. Total
  coverage: 100.00%"*.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **93 files already formatted**.
- **Negative control** — the contract run against the **pre-fix** state (the manifest re-added to
  the index with `git add -f`): **3 of the 11 tests fail**, every failure behavioural — the
  detector names the offending paths, `git check-ignore` exits 1 against a tracked path, and the
  "only one declaration" invariant lists the duplicate metadata files.
- The manifest files remain on disk and the editable install still resolves (`import qtr` →
  `src/qtr/__init__.py`); the working tree is clean after `pip install -e .`, where it previously
  was not.

## The corrected finding

The tracked manifest was stale (61 of 64 entries; the three test modules added between H33 and H49
were missing), and the earlier reason for rejecting regeneration was **not quite right**: building
the same tree with the local setuptools 68.1.2 writes `Metadata-Version: 2.1` with re-spaced,
re-quoted requirement markers, where the committed file was built under pip's build isolation as
`2.4`. The `Requires-Dist` entries are **not dropped** — every base requirement and every extra's
requirement is present in both builds; they are reformatted and reordered. What is
environment-dependent is the **serialisation**, which is enough to make "regenerate and commit"
irreproducible. Untracking is therefore the right fix, and it is now pinned.

## What remains unresolved

- **`compare_to_benchmark` publishes two different numbers for the same statistic, depending on the
  container its caller happens to pass** (verified below). The information ratio and the excess
  volatility are computed with `excess.std()`, which uses **ddof=1** for a `pandas.Series` and
  **ddof=0** for an `ndarray`. The published record contains **both** conventions.
- **The H47 cost-attribution disclosure covers less than the record does.** §H47 publishes that the
  `cost` column of "the committed trade logs (H10, H11, H16, H21, H22, H25)" carries the pre-fix
  aggregate attribution, and `tests/test_trade_log_cost_reconciliation.py` pins that disclosure for
  **one** artifact (H10). A read-only scan of the repository's committed artifacts
  (`git ls-files ".experiments/artifacts/*/trades.parquet"` → **41** trade logs) shows that
  **every** one of them carries the pre-fix attribution: in each, all trades of a bar record the
  same number (`groupby("timestamp")["cost"].nunique() == 1` holds for all 41). The published list
  is therefore **narrower than the truth**, and the disclosure is pinned for one of them. The
  measured scope, from the same scan:

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
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified
  families' numbers and verdicts are frozen.


## Approaches already tried / failed (and why)

- **Regenerating `src/qtr.egg-info/` with the local setuptools** — rejected, and the stated reason
  was corrected in H50: setuptools 68.1.2 writes `Metadata-Version: 2.1` with re-spaced, re-quoted
  markers, but it does **not** drop the `Requires-Dist` entries. The real problem is that the
  *serialisation* is a function of the build environment, so "regenerate and commit" cannot be
  reproduced. The manifest was **untracked** instead (§H50).
- **Regenerating the manifest with pip's build isolation** — rejected: the resulting bytes depend
  on whichever setuptools pip resolves, which is the same irreproducibility by another route.
- **A git helper that returns "no result" for any non-zero exit code** — rejected inside H50
  itself: it made `git check-ignore` exiting 1 (nothing matched) a *skip* instead of a failure.
  Only a missing git executable or a checkout without a repository may skip.
- **Fixing the H10 trade-log cost by changing the charge** — rejected: the charge was never wrong.
  The H27 `L3` check proves it (the per-bar cost recomputed from the trade log matches the
  engine's per-bar cost to ~1e-19 for all five audited families). Only the *attribution* inside the
  log was wrong, so the fix moves the log, not the charge.
- **A negative control that only asserted the new API exists** — rejected for the same reason in
  H47/H48: the control must be behavioural, not a missing-keyword error.

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
- Re-run `tests/test_runner_causality_inventory.py` and `tests/test_runner_metric_agreement.py`
  after any change in a runner.
- The coverage gate (`python -m pytest -q --cov=qtr --cov-branch`) must stay at 100% for
  `src/qtr`; the lint gate (`python -m ruff check src tests run_*.py` and
  `python -m ruff format --check src tests run_*.py`) must stay clean.

## The next task (H51)

> **Make `compare_to_benchmark`'s output independent of the container it is given, and disclose
> which published `information_ratio` / `excess_vol_annual` numbers are on which convention.**

### The defect (verified)

`compare_to_benchmark` computes the excess return as `excess = strat - bench`. When the caller
passes a `pandas.Series`, `excess` is a Series and `excess.std()` uses **ddof=1** (sample); when
the caller passes an `ndarray`, `excess.std()` uses **ddof=0** (population). The information ratio
and `excess_vol_annual` are therefore a function of the *caller's container*, not of the data.
Every other key is container-independent (`beta` uses `np.cov(..., ddof=1)` explicitly, `alpha`
comes from the OLS slope, and `alpha_p_value` comes from `scipy.stats.ttest_1samp`, which always
uses ddof=1).

```python
rng = np.random.default_rng(1)
s = rng.normal(0.001, 0.01, 400); b = rng.normal(0.0005, 0.01, 400)
st.compare_to_benchmark(s, b)["information_ratio"]              # 0.2650139223426122
st.compare_to_benchmark(pd.Series(s), pd.Series(b))["information_ratio"]  # 0.2646824476383493
```

The ratio between the two is exactly `sqrt(n/(n-1))` (`1.0012523486435179` for `n = 400`), and
`excess_vol_annual` differs by the same factor. `alpha_annualized`, `beta`,
`alpha_p_value`, `alpha_p_value_one_sided` and `win_rate` are identical.

### The published record contains both conventions (verified, two families)

The runners are split — **5 pass a Series**, the rest pass `.values`/ndarrays:

| artifact | runner | call site | published `information_ratio` | re-derives under |
|---|---|---|---|---|
| `exp_2026-10-11T15-54-17-212022Z` | `run_h9_intraday_tsmom_experiment.py` | `compare_to_benchmark(result.returns, bh_result.returns)` → Series | `-0.23532720855889727` | **ddof=1** (matches to 1.2e-14) |
| `exp_2026-10-10T22-59-01-182037Z` | `run_cs_momentum_experiment.py` | `compare_to_benchmark(oos_arr, bench_arr)` → ndarray | `0.33150832181222434` | **ddof=0** (matches to 1.7e-16) |

Neither re-derives under the other convention. The Series call sites are `run_h9_intraday_tsmom`
(:498), `run_h10_intraday_tsmom_pfopt` (:315), `run_h23_crypto_futures_tsmom` (:317),
`run_h7_intraday_tsmom` (:315) and `run_h18_overnight_intraday` (:703); the ndarray call sites are
`run_h6_vix_ddcv`, `run_h8_rolladjusted_tsmom`, `run_h16_factor_timing`, `run_h17_vrp`,
`run_h19_volume_predictive`, `run_h20_signed_volume`, `run_cs_momentum`, `run_ts_momentum`,
`run_ddcv` and `run_regime_gated_momentum`.

The repository's own record already asserts the *intended* convention, but only for the ndarray
path: `tests/test_runner_metric_agreement.py` states that `run_cs_momentum`'s local IR "computes
information_ratio = e.mean() / e.std() * sqrt(252) with numpy ddof=0, **the same convention as
compare_to_benchmark's information_ratio**; the two agree exactly". That agreement holds only
because the test passes `.values` — it is not a property of the library.

### No verdict can move

The gate is `p_value < max_p_value AND information_ratio > 0.0` (`benchmark_significance_gate`,
`src/qtr/validation/statistics.py:480`), and the information ratio carries the **sign** of the mean
excess return, which ddof does not change. `alpha_p_value` is computed by `scipy.stats.ttest_1samp`
(ddof=1 in both paths). So **no pass/fail can flip**; what moves is the *magnitude* of the
published `information_ratio` and `excess_vol_annual` (by `sqrt(n/(n-1))` ≈ 0.08% at n=1258 and
0.2% at n=252).

### The work

1. **Choose one convention and make the library enforce it** — the excess series must be reduced to
   a numpy array and the standard deviation taken with an explicit `ddof`, so that all nine keys
   are container-independent. The `beta`/`alpha` path is already explicit and must not move.
2. **Decide which side moves** — the published numbers are frozen, so whichever convention is
   chosen, the families on the *other* convention have a published number that no longer
   re-derives. Quantify the change per family and state it in `FINAL_REPORT.md` §H51. Prefer the
   convention that keeps the larger set of published numbers unchanged, and say why.
3. **Re-derive and disclose** — for every family that publishes an `information_ratio` or an
   `excess_vol_annual`, re-derive it from the frozen artifact (the H9 method above is the
   template: strategy returns from the artifact's own equity/returns, the benchmark from
   `benchmark_returns.parquet` or `benchmark_equity.parquet`, the OOS window from the runner's
   own `TRAIN_END`) and record which convention the published value is on.
4. **Pin it** with `tests/test_h51_benchmark_container_invariance.py`: assert that
   `compare_to_benchmark` returns identical values for ndarray and Series inputs **for all nine
   keys**, assert the per-family published values still re-derive under the convention they were
   published on, and include a **negative control** that reconstructs the pre-fix
   container-dependent behaviour and shows it fails the invariance.

### Constraints

- No published artifact, gate threshold, verdict or certified number may be modified; the artifacts
  are frozen. A published number that no longer re-derives is **disclosed**, not rewritten.
- The gate's `information_ratio > 0` sign test and `alpha_p_value` must not move.
- `tests/test_runner_metric_agreement.py` and `tests/test_benchmark_gate_contract.py` must be
  re-run after any change under `src/qtr/validation` — the first asserts an exact agreement
  between `run_cs_momentum`'s local IR and the library's, and the second pins the library's key
  set and the runners' call sites.

### The runner-up (H52, if H51 is closed)

Extend the H47 cost-attribution disclosure from the one artifact it is pinned for to every
committed trade log (41 of them carry the pre-fix attribution), and state which artifacts the
pre-fix attribution actually changes (those with bars holding more than one trade).

