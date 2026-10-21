# HANDOFF_CURRENT — session complete (H52)

## State

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

## What was actually verified

- `python -m pytest -q -W error tests/test_trade_log_cost_reconciliation.py` → **37 passed**
  (13 before this session).
- `python -m pytest -q -W error` → **1647 passed, 13 skipped** (full suite, up from 1623 + 13).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **94 files already formatted**.
- **Every H52 number is a read of the frozen artifacts** — no pipeline re-execution, no network,
  no grid re-run — and the negative control is behavioural.

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

- The **22 published `information_ratio` values on the sample (`ddof=1`) convention** no longer
  re-derive from the library, which now enforces the population convention. They are **disclosed**,
  not rewritten; the artifacts are frozen and no gate outcome moves.
- **The H47 cost-attribution disclosure is RESOLVED (§H52).** The record is **82** trade logs,
  all of them carry the pre-fix attribution, and all of them are pinned; the set where the
  attribution changes a number (**70**) is pinned separately from the set where it cannot
  (**7**) and the logs that hold no trade (**5**). The **14** benchmark `avg_trade_cost` entries
  whose benchmark trade log and signals were never committed remain **not quantifiable** from
  the record; they are disclosed, not quantified.
- **H9's published OOS Sharpe** is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict frozen.
- **H53 is assigned** — stated in full in `NEXT_TASK.md`: re-derive the published **`metrics` block**
  of every summary that publishes one from its own frozen artifact, and record the convention each
  publisher used for every key in it. The measurement behind it: **80** committed `summary.json`
  files publish about 190 distinct top-level keys; §H49 covered the **5** `validation` blocks, §H51
  the **48** `information_ratio` values and §H52 the `avg_trade_cost` values — and the rest of the
  `metrics` block (**37** summaries), which carries the *certified* numbers, has never been
  re-derived.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted.