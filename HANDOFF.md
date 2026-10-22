# HANDOFF — H54 complete (session handoff)

## What changed (H54)

**H54:** the published blocks of the summaries that publish no `metrics` block now re-derive
from their own frozen artifacts, and every convention the record carries is recorded. Of the **43**
non-`metrics` summaries (**24** shapes, **164** distinct top-level keys, **7 785** published leaf
values), **52** of the keys re-derive in full, **4** re-derive with a *named* disclosed leaf, and
**108** are declarations or audit verdicts about other artifacts. **Ten** convention profiles are
recorded and pinned, and three behavioural negative controls prove the checks fire.

- `tests/test_h54_non_metrics_block_disclosure.py` — the H54 contract: **21 tests**. The
  re-derivation walks the published structure; every reached leaf must agree, every
  unreached leaf must be *named* in `NOT_REDERIVABLE` with the reason the artifact cannot
  carry it, and every reconstructed-but-unpublished leaf must be named in `NOT_PUBLISHED`.
- `FINAL_REPORT.md` — new **§H54** section (the measured record, the classification of the
  **164** top-level keys, the **ten** conventions and the disclosure list).
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`,
  `HANDOFF_NEXT.md` updated.
- **Nothing under `src/qtr` changed.** No artifact, gate threshold, verdict or certified
  number was modified; no grid was re-run; no hypothesis was added.

## What changed (H53)

**H53:** the published `metrics` block re-derives from its own frozen artifact, key by key. Of the
**450** values the **37** `metrics` blocks publish, **441** re-derive exactly (residuals 0 … 5.2e-14);
the **9** that do not are the H9 family's regime block, whose VIX input was never committed. The
**ten** convention profiles the **nineteen** producer tags used are recorded and pinned, and four
behavioural negative controls prove the checks fire.

- `tests/test_h53_published_metrics_disclosure.py` — the module that previously only enumerated the
  `metrics` summaries is replaced by the full re-derivation contract: **19 tests** (3 → 19).
- `FINAL_REPORT.md` — new **§H53** section (with the full 450-row measured table), and the
  "Next task" section updated.
- `NEXT_TASK.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`, `HANDOFF_NEXT.md` updated.
- **Nothing under `src/qtr` changed.** No artifact, gate threshold, verdict or certified number was
  modified; no grid was re-run; no hypothesis was added.

### The conventions, per producer family

| producer | summaries | Sharpe std | profit factor | trades | WF folds | regime Sharpes | benchmark | `val_sharpe` holds |
|---|---:|---|---|---|---|---|---|---|
| `h9_intraday_tsmom_ctexits_v1` | 1 | **sample** (`ddof=1`) | **full sample** | **full sample** | pre-fix | full | full | val window |
| `h9_intraday_tsmom_ctexits_v2` | 4 | **sample** (`ddof=1`) | **full sample** | **full sample** | pre-fix | full | full | val window |
| `h10_intraday_tsmom_pfopt` | 2 | population | OOS | OOS | pre-fix | full | full | **`null`** |
| `h16_factor_timing` | 4 | population | OOS | OOS | pre-fix | OOS | OOS | val window (**3 publish train+val**) |
| `h17_vrp` | 1 | population | OOS | OOS | pre-fix | OOS | OOS | val window |
| `h19_volume_predictive` | 1 | population | OOS | OOS | pre-fix | OOS | OOS | val window |
| `h20_signed_volume` | 1 | population | OOS | OOS | pre-fix | OOS | OOS | val window |
| `h21_futures_tsmom_multicontract` | 1 | population | OOS | OOS | pre-fix | full | full | **the OOS Sharpe** |
| `h22_futures_tsmom_voltarget` | 5 | population | OOS | OOS | pre-fix | full | full | val window |
| `h23_crypto_futures_tsmom` | 7 | population | OOS | OOS | pre-fix | full | full | val window |
| `h25_futures_tsmom_pfmargin` | 2 | population | OOS | OOS | pre-fix | full | full | val window |
| `h28_h{10,21,22,25}_{control,causal}` | 8 | *as the parent* | OOS | OOS | **post-fix** | full | full | *as the parent* |

### The six findings

1. **The walk-forward stability gate was published on the PRE-FIX fold convention.** The library's
   `walk_forward_splits` used to end its last window at `n_splits * window_size`, silently dropping
   the tail of the return series; it was later changed so the last window absorbs it. **29** of the
   **37** published `wf_stability` values are pre-fix and **8** are post-fix — the split follows the
   production date (every post-fix summary is an H28 causal re-certification run of
   **2026-10-19**). All **8** post-fix summaries and **21** of the pre-fix ones are *discriminated* by
   the data (**29** of the 37); the other **8** — the H23 summaries, whose series length is an exact
   multiple of the fold count — coincide, because the tail is empty.
2. **`benchmark_alpha_annual` was published on the PRE-H51 beta convention** —
   `np.cov(strat, bench, ddof=1)[0, 1] / np.var(bench)`, a mixed ddof that inflates beta by
   `n / (n - 1)`. All **7** published alphas (H16 ×4, H17, H19, H20) are pre-fix; they differ from
   the library's current alpha by **2.7e-05 … 3.7e-05**.
3. **The H9 family publishes the SAMPLE standard deviation** (`ddof=1`) because it passed a
   `pandas.Series` to `sharpe_ratio`; every other family passes an `ndarray` and publishes the
   POPULATION standard deviation (`ddof=0`). The same container split decides the information
   ratio's excess volatility — §H51's disclosure, extended here to the **8** H28 runs it did not
   cover.
4. **The H9 family publishes a whole-sample profit factor and trade count**, not the OOS-window
   ones every other family publishes.
5. **Three of the four H16 summaries publish the TRAIN+VAL window Sharpe under the key
   `val_sharpe`** (n = 2769 bars) while the fourth publishes the val-window Sharpe (n = 756 bars).
   Their own `param_grid_results.parquet` carries the val-window value in all four cases, so the
   summaries and their own grids disagree in three of them. **No gate reads the key.**
6. **`val_sharpe` holds three different things across the record**: `null` (H10), the OOS Sharpe
   (H21), and the val-window Sharpe (everybody else, except the three H16 summaries above).

The `metrics` block also publishes four nested keys the contract pins but does not re-derive:
`ablations` (**35** summaries — **28** re-derivable from their committed equity files, **7** not),
`perturbation` / `perturbation_min_ratio` (**14**, none re-derivable) and `cross_validation`
(**2**, none re-derivable).

### The contract now pinned

`tests/test_h53_published_metrics_disclosure.py` holds: the 37 summaries, the 17-key union of what
they publish and the 450 published values; the re-derivation of every one of them from its own
frozen artifact under the recorded convention; the nine exceptions checked against the artifact
directories' own file lists; the per-producer conventions; the library's *current* fold convention
checked against `qtr.validation.statistics.walk_forward_splits`; and four behavioural negative
controls — the *current* fold convention breaks all **21** discriminable pre-fix summaries, the
*current* beta breaks all **7** published alphas, the val-only window breaks the three H16
summaries, and a value nudged by one part in a thousand fails the residual check. The blast radius
is empty: no published `passes` block reads `train_sharpe` or `val_sharpe`.

## What changed (H52)

**H52:** §H47's cost-attribution disclosure now covers **the whole committed record**, not one
artifact. The committed trade logs are **82**, not the six families §H47 named; the pre-fix
attribution is pinned for **every** one of them, and the set of logs where that attribution
actually changes a number is pinned separately.

- `tests/test_trade_log_cost_reconciliation.py` — the frozen-record section is extended from one
  artifact to the whole record: **24 new tests** (13 → 37). Every committed trade log is named,
  classified and pinned with its measured structure; the two sub-sets — the logs where the pre-fix
  attribution *changes a number* (**70**) and the logs where it *cannot* (**7**) — are pinned
  separately, as are the **5** logs that hold no trade at all.
- `FINAL_REPORT.md` — new **§H52** section (with the full 82-row measured table), §H47's two
  disclosure bullets **corrected**, and the "Next task" and "What remains unresolved" sections
  updated.
- `NEXT_TASK.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`, `HANDOFF_NEXT.md` updated.
- **Nothing under `src/qtr` changed.** No artifact, gate threshold, verdict or certified number was
  modified; no grid was re-run; no hypothesis was added.

### The gap, measured

§H47's disclosure was narrower than the record on **three** counts.

1. **The scan missed half the record.** The pathspec `".experiments/artifacts/*/trades.parquet"`
   matches only the logs literally named `trades.parquet` — **41** of the **82** committed trade
   logs. The other **41** are named `best_trades`, `benchmark_trades`, `selected_trades`,
   `ensemble_trades`, `frozen_trades`, `baseline_trades`, `vix_only_trades`, `best_ddcv_trades` and
   `best_trades_w0.5`. The pathspec that sees the whole record is
   `".experiments/artifacts/*trades*.parquet"` → **82**.
2. **The family list was narrow.** The record spans **eleven** families — H3, H10, H11, H16, H17,
   H19, H20, H21, H22, H23 and H25 — across 36 artifact directories, plus **44** trade logs in 35
   exploratory artifacts that carry no `hypothesis`. §H47 named six families.
3. **The published numbers were under-counted.** §H47 disclosed the `avg_trade_cost` of "the three
   exploratory 2026-10-10 MA-crossover summaries". **Five** committed summaries publish it, and the
   tracker metadata publishes the **benchmark's** `avg_trade_cost` in **23** further entries — a
   number §H47 did not mention at all.

### The measured record

| class | logs | meaning |
|---|---:|---|
| aggregate, **changes a number** | **70** | at least one bar holds more than one trade, so the bar's value was written on each of its trades |
| aggregate, **coincides** | **7** | every bar holds exactly one trade, so the bar's value *is* that trade's own cost |
| empty | **5** | the log holds no trade at all (the empty H23 crypto logs) |

The **repetition factor** (the recorded column's total over the total of the per-bar values) runs
from **1.229953** to **20.677528** over the 70 logs where the attribution changes a number.

### Why "uniform per bar" is the *pre-fix* attribution here — three legs

1. **Provenance (decisive).** The tracker stamps every artifact id with the UTC **start** of the
   run that produced it (`exp_<UTC timestamp>`). Every committed trade log's stamp precedes
   **2026-10-19T18:56:58Z**, while the engine's per-trade attribution fix is committed in
   `3fbef17` (2026-10-21 11:33:35Z). No committed log was written by the fixed engine.
2. **The charge anchor.** The H27 `L3` check recomputes the per-bar cost from the trades'
   `weight_change` and `price` — **never** from the `cost` column — and matches the engine's
   per-bar charge to **~1e-19** for H9, H10, H21, H22 and H25.
3. **The engine's own definition.** The pre-fix `_extract_trades` wrote the per-bar total on every
   trade of that bar.

**The honest caveat.** Uniformity alone does not separate an aggregate log from a per-trade log
whose trades happen to share the same cost; that is why the single-symbol case is the *coincides*
bucket and why leg 1 is needed. The contract's negative control shows the classifier does recognise
a per-trade log when the trades' costs differ.

### The published numbers that read the column

Exactly one place in the package reads the trade log's `cost` column:
`src/qtr/backtest/engine.py:448` → `metrics["avg_trade_cost"] = trades["cost"].mean()`. **No runner
reads it.** Five summaries publish the strategy's `avg_trade_cost` (**3** over-stated, by
1.229953×, 1.247109× and 2.868948×) and 23 tracker-metadata entries publish the **benchmark's**
(**9 verified** at 20× or 5×; the other 14 not measurable from the record). 40 `stats.json` files
echo the head of a trade log as text. **No gate, threshold, verdict or certified number reads the
column.**

## What changed (H51)

**H51:** `compare_to_benchmark` is now **container-independent**, and the convention split in the
published record is disclosed and pinned.

- `src/qtr/validation/statistics.py` — `compare_to_benchmark` reduces **both** sides to plain float
  numpy arrays *before* any statistic is computed, and every standard deviation carries an explicit
  `ddof`. The excess volatility (and the information ratio) is taken on **`ddof=0`** (population).
  The docstring states the convention and the container-independence contract.
- `tests/test_h51_benchmark_container_invariance.py` — **new**, 246 tests (12 skipped for documented
  reasons): the invariance for all nine keys, the enforced convention, the per-family disclosure,
  and the negative control.
- `FINAL_REPORT.md` — new **§H51** section, an updated "Next task" section and an updated "What
  remains unresolved".

### The defect (measured)

`excess = strat - bench` kept the *caller's* container, so `excess.std()` used `ddof=1` for a
`pandas.Series` and `ddof=0` for an `ndarray`: the same data compared as an array and as a Series
gave `0.2650139223426122` and `0.2646824476383493` — a ratio of exactly `sqrt(n / (n - 1))`. Two
further container dependencies were found in the same function: `alpha_annualized` used
`Series.mean()` (a different reduction from `ndarray.mean()` whenever pandas has bottleneck), and
`Series - Series` aligns on the **index** while `ndarray - ndarray` subtracts **positionally**,
although the function has always aligned by *length*. All three are closed by reducing both sides to
numpy arrays once, up front.

### The convention: `ddof=0`, on measured grounds

Of the **48** committed artifacts that publish an `information_ratio`, **26** were produced on
`ddof=0` and **22** on `ddof=1` — every one re-derived from its own frozen artifact (bit-exact for
the families that log both return series). Enforcing `ddof=0` therefore keeps the larger set
unchanged; it is also this package's own convention (`sharpe_ratio` uses `ddof=0`) and it preserves
the existing `tests/test_runner_metric_agreement.py` pin that the library's IR and
`run_cs_momentum`'s local IR agree exactly. The 22 that move move by exactly `sqrt(n / (n - 1))`:
**+4.371e-05** at `n = 11441`, **+1.671e-03** at `n = 300` (H23). **No sign changes**, so no gate
outcome moves. The published values are **disclosed**, not rewritten.

### The contract now pinned

`tests/test_h51_benchmark_container_invariance.py` holds: the nine keys are **bit-identical** for an
array and a Series (and for mixed containers, and for a `DataFrame` benchmark against its row-mean
series, and with a NaN row); the enforced convention is the population deviation and is *not* the
sample one; every published IR re-derives from its own artifact **under the convention it was
published on** (and the other convention does not reproduce it); the 26/22 split is pinned; the move
is bounded and never flips a sign; the runners' call sites are checked **statically** (an expression
that reaches a `.values` attribute hands the library an array); and the **negative control**
reconstructs the pre-H51 implementation, shows it was container-dependent, and shows it reproduces
each artifact's published IR *only* under the container its runner passed.

## What changed (H50)

**H50:** the setuptools-generated metadata directory is **untracked** and ignored, and
`pyproject.toml` is the only declared source of the package's metadata.

- `.gitignore` — `*.egg-info/` added.
- `src/qtr.egg-info/` — **untracked** (`git rm -r --cached`); the files stay on disk (the editable
  install resolves to them) but they are no longer part of the repository.
- `tests/test_generated_manifest_contract.py` — **new**, 11 tests.
- `FINAL_REPORT.md` — new **§H50** section and an updated "Next task" section.

### The corrected finding

The tracked manifest was stale (61 of 64 entries; the three test modules added between H33 and H49
were missing), and the two earlier sessions' reason for rejecting regeneration was **not quite
right**: building the same tree with the local setuptools 68.1.2 writes `Metadata-Version: 2.1`
with re-spaced, re-quoted requirement markers (`numpy >=1.24.0`,
`yfinance >=0.2.0 ; extra == 'data'`), where the committed file was built under pip's build
isolation as `2.4` (`numpy>=1.24.0`, `yfinance>=0.2.0; extra == "data"`). The `Requires-Dist`
entries are **not dropped** — every base requirement and every extra's requirement is present in
both builds. What is environment-dependent is the **serialisation**, which is enough to make
"regenerate and commit" irreproducible: the committed bytes would freeze whichever setuptools
happened to build them last.

Reproduction (no network): `from setuptools import build_meta;
build_meta.prepare_metadata_for_build_wheel("<tmp>")`.

### The contract now pinned

`tests/test_generated_manifest_contract.py` (11 tests) holds six invariants: the generated
manifest is **ignored** (and `git check-ignore` agrees); it is **not tracked**; `pyproject.toml` is
the **only** declared source of package metadata; **no module under `src/qtr` depends on it**; the
generated `PKG-INFO` and the installed distribution's metadata both **agree with the declaration**
(comparison is normalisation-based, so it does not depend on the setuptools version); and a
generated `SOURCES.txt` that exists is **not stale**.

Two facts worth recording: **`importlib.metadata` resolves the distribution to the source tree**
whenever `src` is on the import path (the test suite puts it there), so a developer's tooling
reads the *generated* manifest as the package's metadata — which is why the agreement invariant
checks it; and **a git command that ran and failed is a verdict, not an absence** — the first draft
masked a failing `check-ignore` as a skip.

## What changed (H49)

**H49:** the published `validation` blocks in all five exploratory summaries re-derive from their
own frozen `equity_curve.parquet`, and the `walkforward_stability` basis they were written on is
disclosed and pinned.

- `tests/test_h49_validation_block_disclosure.py` — **new**, 11 tests: re-derives each published
  `validation` block from its own frozen equity curve and asserts the published values — including
  the pre-guard `walkforward_stability` ratio, the `walkforward_folds`, the absence of the
  `param_stability` key, the fact that the two buy-and-hold blocks differ by cost model, and that
  `all_pass` stays `false`.
- `FINAL_REPORT.md` — new **§H49** section (rewritten from the H48-era draft) and an updated
  "Next task" section.
- `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`, `HANDOFF_NEXT.md`,
  `NEXT_TASK.md` updated.

### The corrected finding

The H48-era handoff claimed the last two artifacts "do not re-derive" and that the two buy-and-hold
blocks were written by *different* code versions on the *same* series. **Both claims were based on
the wrong return convention.** The engine charges costs per bar and compounds them into the equity
curve (`equity = (1 + net_returns).cumprod() * initial_capital`), so the equity curve carries the
full series including the opening bar; `equity.pct_change()` alone drops that bar. Including the
first bar's return — `equity[0] / initial_capital - 1`, the cost of the very first position change
charged on the opening bar — reproduces the published block for **all five** artifacts to float
noise (< 1e-9).

The published `walkforward_stability` is exactly `sharpe(second half) / sharpe(first half)`, taken
**unconditionally** (the pre-guard formula). In three ma_crossover artifacts both halves are losing,
so the sign-unaware ratio **passed** the `0.7` gate on a strategy that lost money in both halves;
the current sign-aware code reports `0.0`. In the two buy-and-hold artifacts both halves are
profitable, so the published value and the current code agree. All five published blocks report
`walkforward_pass: True` and `all_pass: false`; the current code would report
`walkforward_pass: False` for the three ma_crossover artifacts. **No verdict moves.**

The two buy-and-hold blocks differ because they charged **different costs** baked into their own
frozen equity curves (real cost model, `avg_trade_cost = 0.041106`, vs a fixed `0.0002` per trade),
on the **same** SPY price series. Each block re-derives exactly from **its own** frozen equity
curve; they do not re-derive from each other's. Disclosed, not reconciled.

## What changed (H48)

**H48:** `qtr.validation.statistics.parameter_sensitivity` is now seedable, so its bootstrap
confidence intervals are reproducible instead of redrawn from OS entropy on every call.

- `src/qtr/validation/statistics.py`
  - `parameter_sensitivity` takes an **optional** `random_state` (default `None`, so **no existing
    caller changes behaviour** — the unseeded path is byte-for-byte what it always was).
  - `_bootstrap_seeds` (new) expands an integer seed into **one independent stream per parameter
    row** (`np.random.SeedSequence(seed).spawn(n)`), so the rows are not resampled with a shared
    pattern; a row's seed does not depend on how many rows the grid holds, so extending the grid
    does not perturb the rows already analysed. The unseeded path passes `None` straight through.
- `tests/test_parameter_sensitivity_reproducibility.py` — **new**, 14 tests: exact reproducibility
  under a fixed seed, seed isolation from the legacy global `np.random.seed`, different seeds →
  different bounds, seed-free point estimates, row independence, grid-extension stability,
  **cross-process** reproducibility, a **negative control** (the unseeded path really moves; the
  pre-fix call site is reconstructed and shown to fail the invariant), and the published-record
  disclosure.
- `FINAL_REPORT.md` — new **§H48** section and an updated "Next task" section.
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`,
  `HANDOFF_NEXT.md` updated.

### The defect

`parameter_sensitivity` is exported in `qtr.validation.__all__` but called
`bootstrap_confidence_interval` **without** a `random_state`, so `np.random.default_rng(None)` drew
from OS entropy and two calls on the same input returned **different** confidence intervals
(measured: `ci_lower` = `[-0.7393122, -2.54308907]` then `[-0.93933284, -3.07895489]` on the same
input). Its siblings `sharpe_ratio_ci` and `bootstrap_confidence_interval` both accept
`random_state`, and all three runners that call the bootstrap directly pass `random_state=SEED`;
`parameter_sensitivity` was the only bootstrap caller in the package that could not be seeded.

The point estimates (`metrics`, `optimal_param`, `optimal_metric`, `stability_ratio`,
`metric_std`) were always deterministic — only the bootstrap bounds move — which is why the defect
was invisible in every published number.

With this change the package's **entire** stochastic surface is seedable: `src/qtr` contains exactly
two randomness sites, both in `statistics.py`, and every stochastic computation reachable from the
public API now takes a `random_state`.

## What was actually verified

- **H52**: `python -m pytest -q -W error tests/test_trade_log_cost_reconciliation.py` → **37
  passed** (13 before this session); `python -m pytest -q -W error` → **1647 passed, 13 skipped**
  (full suite, up from 1623 + 13); `python -m ruff check src tests run_*.py` → *All checks passed!*;
  `python -m ruff format --check src tests run_*.py` → **94 files already formatted**;
  `python -m pytest -q --cov=qtr --cov-branch` → `src/qtr` = **1055 statements, 318 branches, 0
  missed, 0 partial, 100.00%**. Every number is a read of
  the frozen artifacts — no pipeline re-execution, no network, no grid re-run — and the negative
  control is behavioural (the classifier answers `"per-trade"` for a log the fixed engine wrote and
  `"aggregate"` for the reconstructed pre-fix log of the same data).

- **H51**: `python -m pytest -q -W error tests/test_h51_benchmark_container_invariance.py` → **246
  passed, 12 skipped**; `python -m pytest -q -W error` → **1623 passed, 13 skipped** (full suite, up
  from 1377 + 1); `python -m ruff check src tests run_*.py` → *All checks passed!*;
  `python -m ruff format --check src tests run_*.py` → **94 files already formatted**. The
  re-derivations are exact (residual 0.0e+00 for H21/H22/H25, ~1e-15 … ~1e-14 elsewhere), and the
  negative control is behavioural.

- `python -m pytest -q -W error tests/test_parameter_sensitivity_reproducibility.py` → **14 passed**.
- `python -m pytest -q -W error` → **1355 passed, 1 skipped**; `src/qtr` =
  **1054 statements, 320 branches, 0 missed, 0 partial, 100.00%**; the committed gate reports
  *"Required test coverage of 100.0% reached. Total coverage: 100.00%"*.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **91 files already formatted**.
- **Negative control** — the new contract run against the **pre-fix** implementation: **4 of the 14
  tests fail**, and every failure is **behavioural** (the bounds move; e.g. `-0.5059` against
  `-0.7423`) rather than a `TypeError` for a missing keyword.
- **Preconditions verified before the change** — no `run_*.py` calls `parameter_sensitivity` (AST
  scan of all 32 runners), and `validate_strategy` derives its published `param_stability` from the
  walk-forward fold Sharpes (`src/qtr/validation/statistics.py:714`), **not** from
  `parameter_sensitivity`; both facts are now pinned by the new contract.

## What remains unresolved

- **H53 is COMPLETE** (2026-10-21): every published value in the **37** `metrics` blocks re-derives
  from the artifact that published it — **441** of **450** values re-derive exactly, and the
  remaining **9** (the H9 regime block) are indeterminable because the producer's VIX series was
  never committed. The **ten** convention profiles the **nineteen** producer tags used are recorded
  and pinned by `tests/test_h53_published_metrics_disclosure.py` (19 tests). The **29** pre-fix
  `wf_stability` values, the **7** pre-H51 `benchmark_alpha_annual` values and the **3** H16
  `val_sharpe` values that publish the train+val window are **disclosed, not rewritten**; no gate
  reads any of them. The four nested keys (`ablations`, `perturbation`,
  `perturbation_min_ratio`, `cross_validation`) are pinned but not re-derived — **28** of the
  ablation blocks are re-derivable from their committed equity files, the rest are not.
  Full statement with the measured table in `FINAL_REPORT.md` §H53.
- **H49 is COMPLETE** (2026-10-21): the published `validation` blocks in all five exploratory
  summaries re-derive from their own frozen `equity_curve.parquet` under the engine's full return
  convention (including the opening bar), and the `walkforward_stability` basis — the
  sign-unaware `sharpe(2nd half) / sharpe(1st half)` — is disclosed and pinned by
  `tests/test_h49_validation_block_disclosure.py` (11 tests). The two buy-and-hold blocks differ
  from each other because they charged different costs baked into their own frozen equity curves.
  Full statement with the measured table in `FINAL_REPORT.md` §H49.
- **H50 is COMPLETE** (2026-10-21): the setuptools-generated metadata directory is untracked and
  ignored, `pyproject.toml` is the only declared source of the package's metadata, and the
  arrangement is pinned by `tests/test_generated_manifest_contract.py` (11 tests; 3 of them fail
  behaviourally against the pre-fix state). The "regenerate and commit" route is closed by
  measurement — the generated metadata's serialisation depends on which setuptools built it.
  Full statement in `FINAL_REPORT.md` §H50.
- **H51 is COMPLETE** (2026-10-21): `compare_to_benchmark` is container-independent (both sides
  reduced to float numpy arrays up front, every standard deviation explicit), the enforced
  convention is the **population** one (`ddof=0`), and the published convention split is disclosed
  and pinned by `tests/test_h51_benchmark_container_invariance.py` (246 tests). **26** of the **48**
  published `information_ratio` values keep re-deriving unchanged; the **22** on the sample
  convention move by `+4.371e-05` (n = 11441) and `+1.671e-03` (H23, n = 300), with no sign change
  and no gate outcome moving. Full statement with the measured table in `FINAL_REPORT.md` §H51.
- **Disclosure (H47)** — the `cost` column of **every** committed trade log carries the pre-fix
  aggregate attribution. **Resolved in §H52**: the record is **82** trade logs (not the 41 the
  §H47-era pathspec saw), **all 82** carry it, and **all 82** are pinned; the set where the
  attribution changes a number (**70**) is pinned separately from the set where it cannot (**7**)
  and the logs that hold no trade (**5**). The published numbers that read the column are disclosed
  too: 5 summaries publish the strategy's `avg_trade_cost` (3 over-stated) and 23 tracker entries
  publish the benchmark's (9 verified at 20× or 5×). No gate, threshold, verdict or certified number
  reads them.
- H9's published OOS Sharpe is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict cannot move (REJECT on the profit factor, 55× margin over its 1.0 gate).
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified
  families' numbers and verdicts are frozen.

## Approaches already tried / failed (and why)

- **A negative control that only asserted the new keyword exists** — rejected: it failed against
  the pre-fix implementation with `TypeError` (the parameter was *missing*), not because the
  behaviour was wrong. The contract now goes through the `_seeded()` adapter, so the pre-fix
  implementation is driven down its unseeded path and the control is **behavioural**.
- **Regenerating `src/qtr.egg-info/` with the local setuptools** — rejected, and the stated reason
  was corrected in H50: setuptools 68.1.2 writes `Metadata-Version: 2.1` with re-spaced, re-quoted
  requirement markers, but it does **not** drop the `Requires-Dist` entries. The real problem is
  that the *serialisation* is a function of the build environment, so "regenerate and commit"
  cannot be reproduced. The manifest was **untracked** instead (§H50).
- **Regenerating the manifest with pip's build isolation** — rejected: the resulting bytes depend
  on whichever setuptools pip happens to resolve, which is the same irreproducibility by another
  route.
- **Fixing the trade log by changing the charge** — rejected: the charge was never wrong (H27's
  `L3` check proves it to ~1e-19). Only the attribution inside the log was wrong, so the fix moves
  the log, not the charge.
- **A negative control that only asserted the new API exists** (H47) — rejected for the same reason
  as above; the H47 spy now hooks both `_total_costs` and `_calculate_costs`, so that control is
  behavioural too.
- **Using the per-bar *first* recorded value as the bar total for every log** (H52) — rejected
  after measurement: that is only the bar total for an *aggregate* log. For a per-trade log the
  first value is one trade's own share, so the "over-count" computed from it is meaningless. The
  contract classifies the recorded form first and only computes the repetition factor on an
  aggregate log.
- **Deciding each log from the `cost` column alone** (H52) — rejected: a per-trade log whose
  trades happen to share the same cost is indistinguishable from an aggregate log by that column
  (a two-symbol backtest with identical signals records the same number either way). The
  disclosure therefore rests on the **provenance** leg — the artifact id's run stamp against the
  fix's commit — which is measured, with the negative control showing the classifier can still
  recognise a per-trade log when the costs differ.
- **Re-deriving every artifact's cost model to decide each log independently** (H52) — rejected as
  disproportionate: it needs each runner's cost model, ADV and volume inputs, and the published
  record does not carry all of them (two buy-and-hold artifacts used a fixed `0.0002` per trade).
- **Treating a value that does not re-derive as a defect** (H53) — rejected: measurement showed
  every non-re-deriving value is a *convention* difference (a ddof, a window, a fold rule) or a
  missing input (the VIX series), never an arithmetic error. The contract therefore records the
  convention rather than "fixing" the published number.
- **Assuming one convention for the whole record** (H53) — rejected after measurement: ten distinct
  profiles across nineteen producer tags, including one key (`val_sharpe`) that holds three
  different meanings.
- **Re-deriving the H9 regime block from the published Sharpe alone** (H53) — rejected: the regime
  labels are a function of a VIX series that was never committed, so the block is not a function of
  the record at all. Disclosed as indeterminable rather than approximated.

## Precise next task

**H54 — re-derive the published blocks of the summaries that publish no `metrics` block, and record
the convention each publisher used for every key in them.** The committed record holds **80**
`summary.json` files; §H49 covered the **5** `validation` blocks, §H51 the **48**
`information_ratio` values, §H52 the `avg_trade_cost` values and §H53 the `metrics` block itself
(**37** summaries, **450** values). What has **never** been re-derived is the rest of the record:
the **43** summaries that publish **no** `metrics` block at all, carrying **164** distinct
top-level keys over **7 785** leaf values in **24** distinct shapes — `gates`, `passes`,
`all_pass`, `verdict`, `oos_metrics`, `split_metrics`, `benchmark_comparison`,
`strategy_metrics`, `validation`, `ablations`, `grid`, … — with the published `all_pass` /
`verdict` / `gates` blocks (20 / 15 / 15 summaries) resting on them. **Three** of those summaries
publish no parquet artifact at all.

The work: enumerate the 43 summaries, their shapes and their keys and the artifacts each published
them from; re-derive each published value from that summary's own frozen artifact under the
engine's conventions, using the §H53 method (reconstruct the convention, match to ≤ 1e-09
relative, record it per producer); separate the three classes they fall into — the
**certified-family** blocks (`gates`, `verdict`, `all_pass`), the **exploratory** blocks
(`ablation`, `ablations`, `grid`, `all_results`, `all_combo_results`, `param_grid_summary`) and
the **audit** blocks (`h26_sharpe_scale`, `h27_pnl_level`, `h28_causal_recertification`,
`h29_lookahead_sweep`, `pf_robustness`), which publish a verdict *about* the record rather than
metrics and therefore read other artifacts; publish a per-summary, per-key table of published vs
re-derived vs residual; and pin it with a new contract module carrying a **behavioural negative
control**. Read-only against the frozen artifacts, no grid re-run, no published number may move —
where a value does not re-derive, **disclose** it with the convention that explains it. The full
statement and the constraints are in `NEXT_TASK.md`.

**H53 is complete** (2026-10-21). The record of what was done is in `FINAL_REPORT.md` §H53 and
`HANDOFF_CURRENT.md`.
