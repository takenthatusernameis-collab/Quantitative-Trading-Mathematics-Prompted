# HANDOFF_CURRENT — session complete (H51)

## State

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

## The corrected finding

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
- The **H47 cost-attribution disclosure** covers less than the record does: all **41** committed
  trade logs carry the pre-fix aggregate attribution, and the disclosure is pinned for one of them
  (H10). The assigned task (H52).
- **H9's published OOS Sharpe** is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict frozen.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted.