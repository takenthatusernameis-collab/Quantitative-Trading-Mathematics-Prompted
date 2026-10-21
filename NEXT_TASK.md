# Next Task — H42 done: the lint/format gate is reproducible

## State

**H35, H36, H37, the remaining-runner extension, H38, H39, H40, H41 and H42 are COMPLETE.**

- The engine and `qtr.validation.statistics.validate_strategy` now agree **exactly** on all six
  metrics the package computes twice (`total_return`, `annualized_return`,
  `annualized_volatility`, `sharpe`, `max_drawdown`, `profit_factor`), and the engine-only
  metrics (Sortino, Calmar, max-drawdown duration, average trade cost) are pinned by their exact
  formula (`tests/test_engine_metric_agreement.py`, 55 tests).
- The **Sharpe convention is settled**: the package uses the **population** standard deviation
  (ddof=0), which is what `qtr.validation.statistics.sharpe_ratio` already used and what every
  audited family's published Sharpe uses (H26's own per-family classification, pinned). The
  engine was the only outlier; it now matches.
- The engine's **degenerate-series guard** now carries the record's 1e-15 tolerance, so a constant
  return series yields 0.0 in both implementations instead of 7.3e16 in the engine.
- The five artifacts that carry engine metrics published **two different Sharpes for one run**
  (ratio exactly `sqrt((n-1)/n) = 0.9998011730768697`, n = 2,515). They are frozen history; both
  conventions are pinned against each artifact's own equity curve.
- **H9 is the one family in the record published on the other convention** (sample std, ddof=1);
  the gap is 1.026e-04 against a margin of 5.6e-02 above its 1.0 Sharpe gate, and its published
  row is a REJECT on the profit factor in any case. Disclosed and pinned.
- **The lint/format gate is now reproducible from a bare clone.** `pyproject.toml` already
  declared ruff (`[project.optional-dependencies] lint = ["ruff>=0.6.0"]`) and a `[tool.ruff]`
  block with `target-version`, `line-length`, a lint `select`/`ignore` set and a format
  `quote-style`/`indent-style`; ruff 0.17.1 is installed in this environment. The only residual
  gap was one format deviation on pre-existing lines of
  `tests/test_runner_causality_inventory.py` (introduced in H38, commit 944cdc3, not touched by
  H39/H40/H41). `python -m ruff format` closed it; both commands are now clean on
  `src tests run_*.py` (85 files already formatted).

## What changed this session (H42)

- `tests/test_runner_causality_inventory.py` — reformatted by `python -m ruff format`
  (`1 file reformatted`, 61 insertions / 22 deletions across 8 hunks). Pure whitespace: no
  `run_*.py`, no `src/qtr`, no published artifact, gate, threshold, verdict or certified number
  was touched; no grid was re-run; no hypothesis was added.
- `FINAL_REPORT.md` — new §H42 section, updated `Summary statistics` (test-suite tally) and
  `Next Task`; this file; the `HANDOFF*` files.

## What was actually verified (this session — H42)

- `python -m ruff check src tests run_*.py` → *All checks passed!* (unchanged).
- `python -m ruff format --check src tests run_*.py` → **85 files already formatted** (was
  `1 file would be reformatted, 84 files already formatted`; the deviation is gone).
- `python -m pytest -q -W error tests/test_runner_causality_inventory.py` → **321 passed**
  (the module that owns the formatted file; unchanged — formatting cannot change semantics).
- `python -m pytest -q -W error` → **1212 passed, 1 skipped** in 275.34 s (identical to the H41
  baseline of 1212 passed, 1 skipped in 276.17 s; the change is whitespace-only).
- `src/qtr` coverage is unchanged at 100%: the change is confined to a test file, so no branch is
  added or removed. (The coverage tool, `pytest-cov`, is still not installed in this
  environment — `python -m pytest --cov=qtr` → "unrecognized arguments"; the H39/H40/H41 branch
  argument applies unchanged.)

## Constraints carried forward

- No published artifact, gate threshold, verdict or certified number may be modified; no grid
  may be re-run; no new hypothesis (the H1–H30 space is exhausted; the certified families
  H10/H11/H12/H22/H25 are frozen).
- `python -m pytest -q -W error` and `ruff check src tests run_*.py` must pass from a bare
  clone (no install step); `ruff format --check src tests run_*.py` must now also pass — it is
  the reproducible gate that H42 closed. Keep `src/qtr` at 100% coverage.
- Re-run `tests/test_runner_causality_inventory.py` after any change in a `run_*.py`,
  `tests/test_causality_invariant.py` after any change under `src/qtr`,
  `tests/test_engine_metric_agreement.py` after any change to `_calculate_metrics` or to
  `qtr.validation.statistics`, and `tests/test_runner_metric_agreement.py` after any change to
  a runner's local metric helper or inline metric site.

## Next task

None. All assigned tasks (H35–H42) are complete. All metric-agreement sites — library-side
(§H39), runner-local helpers (§H40) and runner-inline sites (§H41) — are classified and pinned;
every gate defect class that has surfaced (§H35) is closed by an executable invariant; the
point-in-time contract covers every `run_*.py` (§H36–H37); the engine's `total_return` spans
every bar (§H38); the package's two Sharpe implementations agree (§H39); and the lint/format
gate is reproducible (§H42). No further work is assigned.