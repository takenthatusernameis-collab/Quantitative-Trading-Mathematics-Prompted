# HANDOFF_CURRENT — session complete (H55)

## State

- **H55 is COMPLETE** as recorded in `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_NEXT.md` and
  `HANDOFF_CURRENT_SESSION.md`: the four **nested** `metrics` blocks — and the top-level
  `perturbation` block that no earlier pass covered — re-derive from the frozen record. Of the
  **736** published leaf values across **27** summaries, **610** re-derive (worst residual
  **2.5e-12**, median **0**, **321** exact) and the **126** that do not are named with the reason
  the record cannot carry each one: **86** ablation trade counts whose trade log was never
  committed, **32** H20 values whose OHLC panel was never committed, and the **8**
  cross-validation Sharpes whose QQQ/IWM closes were never committed. **Six** conventions the
  record hides are measured and pinned — including a monthly-rebalance anchor that changed *inside*
  the H16 family and a perturbation ratio that is a fallback rather than a measurement — and four
  behavioural negative controls prove the checks fire. The contract is
  `tests/test_h55_nested_metrics_disclosure.py` (26 tests) with the re-derivation helper
  `tests/h55_rederivation.py`.
- **H56 is COMPLETE** as recorded in `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_NEXT.md` and
  `HANDOFF_CURRENT_SESSION.md`: the `stats.json` text echoes (**40** files) and the **14**
  benchmark `avg_trade_cost` entries are measured to the extent the record allows and disclosed
  where it does not. All 40 `returns` texts re-derive byte-for-byte from the committed
  `equity.parquet` under the engine's convention (first bar `equity[0] / 100 000 - 1`, then
  bar-over-bar returns) rendered as `series.to_string(max_rows=10) + "\nLength: {n}, dtype:
  float64"`; the H18 family's **100 000** capital anchor is pinned and a behavioural negative
  control (the **1 000 000** convention every other producer uses) fails all 40. All 40 publish
  the identical `trades` dummy head and no trade log was ever committed beside any `stats.json`,
  so that text is disclosed as unrecoverable. The tracker's **23** `benchmark_avg_trade_cost`
  entries split **9 measurable** (6 × **20.0×** against committed `benchmark_trades.parquet`,
  3 × **5×** against committed `signals_buy_and_hold.parquet`) and **14 not measurable**; each of
  the 14 commits only `benchmark_equity.parquet` for its benchmark, so its over-count factor is
  not measurable — disclosed, not quantified. The contract is
  `tests/test_h56_stats_json_echoes.py` (187 tests). The H47–H56 disclosure series is complete.
- **The one pre-existing suite failure is FIXED.** The attribution-fix commit `3fbef17` is not in
  this squashed clone, so `git show -s --format=%cI 3fbef17` died. Its recorded UTC time
  (**2026-10-21 11:33:35Z**, already in `FINAL_REPORT.md`) is now pinned in the test and
  **cross-checked against `git` whenever the commit is present** — a stronger check than the
  shell-out it replaces.
- **H53 is COMPLETE** as recorded in `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_NEXT.md` and
  `HANDOFF_CURRENT_SESSION.md`: every published value in the **37** `metrics` blocks re-derives
  from the artifact that published it — **441** of **450** values re-derive exactly (residuals
  0 … 5.2e-14) and the remaining **9** are the H9 family's regime block, whose VIX input was never
  committed. The **ten** convention profiles the **nineteen** producer tags used are recorded and
  pinned, and four behavioural negative controls prove the checks fire. The contract is
  `tests/test_h53_published_metrics_disclosure.py` (19 tests, up from 3).
- **H52 is COMPLETE** as recorded in `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_NEXT.md` and
  `HANDOFF_CURRENT_SESSION.md`: §H47's cost-attribution disclosure now covers **the whole
  committed record** — **82** trade logs, not the 41 the §H47-era pathspec saw — and every one of
  them is named, classified and pinned by `tests/test_trade_log_cost_reconciliation.py`
  (37 tests). The set where the pre-fix attribution actually changes a number (**70**) is pinned
  separately from the set where it cannot (**7**) and the logs that hold no trade (**5**). The
  published numbers that read the column are disclosed too: 5 summaries publish the strategy's
  `avg_trade_cost` (3 over-stated) and 23 tracker-metadata entries publish the benchmark's
  (9 verified at 20x or 5x).
- **H51 is COMPLETE** as recorded in `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_NEXT.md` and
  `HANDOFF_CURRENT_SESSION.md`: `compare_to_benchmark` is **container-independent** — both sides are
  reduced to float numpy arrays before any statistic is computed, every standard deviation carries
  an explicit `ddof`, and the excess volatility (and the information ratio) is taken on the
  **population** standard deviation (`ddof=0`). The choice is pinned by
  `tests/test_h51_benchmark_container_invariance.py` (246 tests, 12 skipped for documented reasons).
  The published convention split is disclosed in full: of the **48** committed artifacts that publish
  an `information_ratio`, **26** are on `ddof=0` and **22** on `ddof=1`.
- **H50 is COMPLETE**: the setuptools-generated metadata directory `src/qtr.egg-info/` is
  **untracked** and ignored, `pyproject.toml` is the only declared source of the package's metadata,
  and the arrangement is pinned by `tests/test_generated_manifest_contract.py` (11 tests). The
  "regenerate and commit" route is closed by measurement: the generated metadata's serialisation
  depends on which setuptools built it.
- **H35–H50 are COMPLETE**: every gate defect class that has surfaced is closed by an executable
  invariant, the point-in-time invariant covers every `run_*.py`, the engine's `total_return` spans
  every bar, the package's two Sharpe implementations agree, the lint/format gate is reproducible,
  the coverage gate is measured, declared and complete, both the package's public API and the
  runners' import surface are declared and pinned, the engine's trade log reconciles with the
  costs it charges, the package's stochastic surface is seedable, and the published validation
  blocks re-derive from the frozen artifacts.
- No published artifact, gate threshold, verdict or certified number was modified; no grid was
  re-run; no hypothesis was added.

## What changed (this session — H55)

- `tests/test_h55_nested_metrics_disclosure.py` — **new**, the H55 contract: **26 tests**. Every
  published leaf the reconstruction reaches must agree with it; every published leaf it does not
  reach must be *named* with the reason the artifact cannot carry it; and the record's own shape
  must not move.
- `tests/h55_rederivation.py` — **new**, the re-derivation helper: the two monthly-rebalance
  anchors, the per-family-abloration convention of the first H16 run, and the per-family
  re-derivation of H16, H17, H19, H22 and H25. Every re-execution is gated on a **bit-for-bit**
  match against the committed equity artifact.
- `FINAL_REPORT.md` — new **§H55** section.
- `tests/test_trade_log_cost_reconciliation.py` — the pre-existing failure fixed (the pinned
  attribution-fix timestamp, cross-checked against `git`).
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`,
  `HANDOFF_NEXT.md` updated.
- **Nothing under `src/qtr` changed.** No artifact, gate threshold, verdict or certified number was
  modified; no grid was re-run; no hypothesis was added.

## What changed (this session — H56)

- `tests/test_h56_stats_json_echoes.py` — **new**, the H56 contract: **187 tests**. All 40 `returns`
  texts re-derive byte-for-byte from the committed `equity.parquet`; the **100 000** capital anchor
  is pinned with a behavioural negative control (the **1 000 000** convention fails all 40); all 40
  publish the identical `trades` dummy head and no trade log was ever committed beside any
  `stats.json`; the tracker's **23** `benchmark_avg_trade_cost` entries split **9 measurable** /
  **14 not measurable**, each of the 14 committing only `benchmark_equity.parquet` for its
  benchmark.
- `FINAL_REPORT.md` — new **§H56** section.
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`,
  `HANDOFF_NEXT.md` updated.
- **Nothing under `src/qtr` changed.** No artifact, gate threshold, verdict or certified number was
  modified; no grid was re-run; no hypothesis was added.

## What changed (this session — H53)

- `tests/test_h53_published_metrics_disclosure.py` — the module that previously only enumerated the
  `metrics` summaries is replaced by the full re-derivation contract: **19 tests** (3 → 19). It
  re-derives every published value from the artifact that published it, pins the convention each
  producer used for each key, and carries four behavioural negative controls.
- `FINAL_REPORT.md` — new **§H53** section (with the full 450-row measured table), and the
  "Next task" section updated.
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`,
  `HANDOFF_NEXT.md` updated.
- **Nothing under `src/qtr` changed.** No artifact, gate threshold, verdict or certified number
  was modified; no grid was re-run; no hypothesis was added.

## What changed (this session — H52)

- `tests/test_trade_log_cost_reconciliation.py` — the frozen-record section is extended from one
  artifact to the whole record: **24 new tests** (13 → 37).
- `FINAL_REPORT.md` — new **§H52** section (with the full 82-row measured table), §H47's two
  disclosure bullets **corrected**, and the "Next task" and "What remains unresolved" sections
  updated.
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`,
  `HANDOFF_NEXT.md` updated.
- **Nothing under `src/qtr` changed.** No artifact, gate threshold, verdict or certified number
  was modified; no grid was re-run; no hypothesis was added.

## What changed (this session — H50)

- `.gitignore` — `*.egg-info/` added.
- `src/qtr.egg-info/` — **untracked** (`git rm -r --cached`); the files stay on disk (the editable
  install resolves to them) but they are no longer part of the repository.
- `tests/test_generated_manifest_contract.py` — **new**, 11 tests.
- `FINAL_REPORT.md` — new **§H50** section and an updated "Next task" section.
- `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`, `HANDOFF_NEXT.md`,
  `NEXT_TASK.md` updated.

## What changed (this session — H51)

- `src/qtr/validation/statistics.py` — `compare_to_benchmark` reduces both sides to plain float
  numpy arrays once, up front; every standard deviation carries an explicit `ddof`; the excess
  volatility (and the information ratio) is taken with `ddof=0`. The docstring states the
  convention and the container-independence contract.
- `tests/test_h51_benchmark_container_invariance.py` — **new**, 246 tests (12 skipped for documented
  reasons).
- `FINAL_REPORT.md` — new **§H51** section, an updated "Next task" section and an updated "What
  remains unresolved".
- `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`, `HANDOFF_NEXT.md`,
  `NEXT_TASK.md` updated.

## The corrected finding (H52)

§H47's disclosure was narrower than the record on **three** counts. The pathspec
`".experiments/artifacts/*/trades.parquet"` sees only the logs literally named `trades.parquet`
(**41** of **82**); the family list named six where the record spans **eleven** plus 44
exploratory trade logs; and the published numbers were under-counted — **five** summaries publish
`avg_trade_cost` (not three) and **23** tracker-metadata entries publish the benchmark's (not
mentioned at all).

All **82** committed trade logs record the **aggregate** attribution. **70** have bars with more
than one trade, so the attribution changes a number there (repetition factor 1.229953x …
20.677528x); **7** have only single-trade bars, where the two attributions coincide by
construction; **5** hold no trade. "Uniform per bar" is the *pre-fix* attribution here on three
legs: **provenance** (every committed log's run stamp, taken from the artifact id, precedes the
fix's commit `3fbef17`), the **H27 `L3` charge anchor** (the per-bar charge recomputed from
`weight_change`/`price`, never from the `cost` column, matches to ~1e-19 for five families), and
the **engine's own definition**. Uniformity alone is not proof — a per-trade log whose trades
share a cost looks the same — which is why the provenance leg carries the claim and the negative
control shows the classifier recognises a per-trade log.

## The corrected finding (H51)

Three container dependencies were in `compare_to_benchmark`, not one: `excess.std()` (`ddof=1` for
a Series, `ddof=0` for an ndarray), `strat.mean()` / `bench.mean()` (bottleneck's `nansum` is not
numpy's pairwise sum), and the excess series itself (`Series - Series` aligns on the **index**,
`ndarray - ndarray` subtracts **positionally**, while the function aligns the two sides by *length*).
All three are closed by reducing both sides to numpy arrays once, up front.

The enforced convention is **`ddof=0`**, on four measured grounds: it keeps the larger set of
published numbers unchanged (**26** of **48**), it is this package's own convention
(`sharpe_ratio` uses `ddof=0`), it preserves the existing `tests/test_runner_metric_agreement.py`
pin, and it is numpy's default. The **22** published values on the other convention move by
**+4.371e-05** (n = 11441) and **+1.671e-03** (H23, n = 300) — **disclosed, not rewritten**; no sign
changes, so no gate outcome moves. No artifact publishes an `excess_vol_annual`.

Two facts worth recording for the next session: an equity curve must be inverted against the
initial capital (`equity[0] / capital - 1`), because the engine's `equity = (1 + r).cumprod() *
capital` already carries the first bar's return — `pct_change()` alone loses it; and three families
published `round(information_ratio, 4)`, whose convention is therefore pinned by the runner's
**call site** (an expression reaching `.values` hands the library an array) rather than by the data.

## The findings (H53)

Six findings, all measured:

1. **The walk-forward stability gate was published on the PRE-FIX fold convention.** The library's
   `walk_forward_splits` used to end its last window at `n_splits * window_size`, silently dropping
   the tail of the return series; it was later changed so the last window absorbs it. **29** of the
   **37** published `wf_stability` values are pre-fix and **8** are post-fix. The split follows the
   production date: every post-fix summary is an H28 causal re-certification run of
   **2026-10-19**. All **8** post-fix summaries and **21** of the pre-fix ones are *discriminated* by
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

The **9** values that cannot be re-derived are exactly the H9 regime block (`regime_sharpes` ×4,
`worst_regime_sharpe` ×5): the producer fetched its VIX series from Yahoo at run time and never
committed it, so the regime labels are a function of an input the record does not hold.

The `metrics` block also publishes four nested keys the contract pins but does not re-derive:
`ablations` (**35** summaries — **28** re-derivable from their committed equity files, **7** not),
`perturbation` / `perturbation_min_ratio` (**14**, none re-derivable) and `cross_validation`
(**2**, none re-derivable).

## What was actually verified (H53)

- `python -m pytest -q -W error tests/test_h53_published_metrics_disclosure.py` → **19 passed**
  (3 before this session).
- `python -m pytest -q -W error` → **1666 passed, 13 skipped** (full suite, up from 1650 + 13).
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` → `src/qtr` =
  **1055 statements, 318 branches, 0 missed, 0 partial, 100.00%**.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **95 files already formatted**.
- **Every H53 number is a read of the frozen artifacts** — no pipeline re-execution, no network,
  no grid re-run.
- **The conventions were measured, not assumed** — each was identified by reconstructing it and
  matching the published value to ≤ 1e-09 relative, and the reconstruction is now part of the
  contract.
- **Four behavioural negative controls** — the *current* library fold convention breaks the
  re-derivation of all **21** discriminable pre-fix summaries; the *current* library beta breaks all
  **7** published alphas; the val-only window breaks the three H16 summaries; and a published value
  nudged by one part in a thousand fails the residual check.
- **The blast radius is empty** — no published `passes` block reads `train_sharpe` or
  `val_sharpe`, and every gate key is computed from values that do re-derive.

## What was actually verified (H52)

## What was actually verified (H51)

- `python -m pytest -q -W error tests/test_h51_benchmark_container_invariance.py` → **246 passed,
  12 skipped**.
- `python -m pytest -q -W error` → **1623 passed, 13 skipped** (full suite, up from 1377 + 1).
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` → `src/qtr` =
  **1055 statements, 318 branches, 0 missed, 0 partial, 100.00%**.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **94 files already formatted**.
- **The re-derivation is exact** — residual 0.0e+00 for H21/H22/H25, 4.4e-16 for H23, ~1e-15 …
  ~1e-14 elsewhere; the published `alpha_p_value` re-derives with the same residual.
- **Negative control** — the reconstructed pre-H51 implementation is container-dependent and
  reproduces each artifact's published IR *only* under the container its runner passed.

## What remains unresolved

- **The 9 H9 regime values** cannot be re-derived: the producer's VIX series was never committed.
  Disclosed, not quantified.
- **The 29 pre-fix `wf_stability` values** no longer re-derive from the library's current
  `walk_forward_splits`; published on the convention in force when they were produced, disclosed,
  not rewritten. The certified families (H10, H22, H25) are among them.
- **The 7 published `benchmark_alpha_annual` values** are on the pre-H51 mixed-ddof beta;
  disclosed, not rewritten; no gate reads the key.
- **Three of the four H16 `val_sharpe` values** publish the train+val window under a key named for
  the val window and disagree with their own grid artifact; disclosed, not rewritten.
- **The four nested `metrics` keys are RESOLVED (§H55).** `ablations` (27 summaries, 661 leaves),
  `perturbation` (7, 35), `perturbation_min_ratio` (7, 7), `cross_validation` (2, 8) and the
  top-level `perturbation` block (5, 25) re-derive from the frozen record: **610** of **736** leaves
  re-derive, the **126** that do not are named with the reason the record cannot carry them, and no
  gate reads any of them.
- The **22 published `information_ratio` values on the sample (`ddof=1`) convention** no longer
  re-derive from the library, which now enforces the population convention. They are **disclosed**,
  not rewritten; the artifacts are frozen and no gate outcome moves. H53 extends that disclosure to
  the **8** H28 runs §H51 did not cover.
- **The H47 cost-attribution disclosure is RESOLVED (§H52).** The record is **82** trade logs,
  all of them carry the pre-fix attribution, and all of them are pinned; the set where the
  attribution changes a number (**70**) is pinned separately from the set where it cannot
  (**7**) and the logs that hold no trade (**5**). The **14** benchmark `avg_trade_cost` entries
  whose benchmark trade log and signals were never committed remain **not quantifiable** from
  the record; they are disclosed, not quantified.
- **H9's published OOS Sharpe** is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict frozen.
- **H56 is COMPLETE** (§H56 of `FINAL_REPORT.md`): the `stats.json` echoes and the 14 benchmark
  `avg_trade_cost` entries are measured to the extent the record allows and disclosed where it does
  not; no further disclosure task remains assigned.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted.

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
