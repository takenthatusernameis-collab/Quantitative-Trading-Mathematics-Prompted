# HANDOFF_CURRENT — session complete (H48)

## State

- **H48 is COMPLETE** as recorded in `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_NEXT.md` and
  `HANDOFF_CURRENT_SESSION.md`: `qtr.validation.statistics.parameter_sensitivity` now takes an
  optional `random_state` and its bootstrap confidence intervals are reproducible instead of
  redrawn from OS entropy on every call, pinned by
  `tests/test_parameter_sensitivity_reproducibility.py` (14 tests: exact reproducibility under a
  fixed seed, seed isolation from the legacy global RNG, different seeds → different bounds,
  seed-free point estimates, row independence, grid-extension stability, cross-process
  reproducibility, a negative control and the published-record disclosure). The default
  (`random_state=None`) path is unchanged and is now *documented* as non-reproducible.
- **H35–H47 are COMPLETE**: every gate defect class that has surfaced is closed by an executable
  invariant, the point-in-time invariant covers every `run_*.py`, the engine's `total_return` spans
  every bar, the package's two Sharpe implementations agree, the lint/format gate is reproducible,
  the coverage gate is measured, declared and complete, both the package's public API and the
  runners' import surface are declared and pinned, and the engine's trade log reconciles with the
  costs it charges.
- No published artifact, gate threshold, verdict or certified number was modified; no grid was
  re-run; no hypothesis was added.

## What changed (this session — H48)

- `src/qtr/validation/statistics.py`
  - `parameter_sensitivity` takes an **optional** `random_state` (default `None`, so **no existing
    caller changes behaviour**);
  - `_bootstrap_seeds` (new) expands an integer seed into **one independent stream per parameter
    row** (`np.random.SeedSequence(seed).spawn(n)`), so the rows are not resampled with a shared
    pattern; a row's seed does not depend on how many rows the grid holds, so extending the grid
    does not perturb the rows already analysed; the unseeded path passes `None` straight through.
- `tests/test_parameter_sensitivity_reproducibility.py` — **new**, 14 tests.
- `FINAL_REPORT.md` — new **§H48** section and an updated "Next task" section.
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`,
  `HANDOFF_NEXT.md` updated.

## The defect this closed

`parameter_sensitivity` is exported in `qtr.validation.__all__` but called
`bootstrap_confidence_interval` **without** a `random_state`, so `np.random.default_rng(None)` drew
from OS entropy and two calls on the same input returned **different** confidence intervals. Its
siblings `sharpe_ratio_ci` and `bootstrap_confidence_interval` both accept `random_state`, and all
three runners that call the bootstrap directly pass `random_state=SEED`; `parameter_sensitivity`
was the only bootstrap caller in the package that could not be seeded. The point estimates were
always deterministic — only the bounds move — so the defect was invisible in every published
number.

With the fix, `src/qtr` contains exactly **two** randomness sites, both in `statistics.py`, and
every stochastic computation reachable from the public API now takes a `random_state`.

## What was actually verified

- `python -m pytest -q -W error tests/test_parameter_sensitivity_reproducibility.py` → **14 passed**.
- `python -m pytest -q -W error` → **1355 passed, 1 skipped** (full suite).
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` → `src/qtr` = **1054
  statements, 320 branches, 0 missed, 0 partial, 100.00%**; the committed gate reports *"Required
  test coverage of 100.0% reached. Total coverage: 100.00%"*.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **91 files already formatted**.
- **Negative control** — the new contract run against the **pre-fix** implementation: **4 of the 14
  tests fail**, every one **behaviourally** (the bounds move; e.g. `-0.5059` against `-0.7423`),
  not with a `TypeError` for a missing keyword.
- **Preconditions verified before the change** — no `run_*.py` calls `parameter_sensitivity` (AST
  scan of all 32 runners) and `validate_strategy` derives its published `param_stability` from the
  walk-forward fold Sharpes (`src/qtr/validation/statistics.py:714`); both are now pinned.

## What remains unresolved

- **The published `validation` blocks are on an older `validate_strategy`** (the next assignment,
  H49). The five committed exploratory summaries carry a `validation` block written by a version
  with **no `param_stability` gate** and a **sign-unaware** walk-forward ratio; re-deriving the
  block from each artifact's own frozen `equity_curve.parquet` reproduces `sharpe`,
  `profit_factor`, `max_drawdown` and `total_return` in three of the five, but
  `walkforward_stability` comes out as the *pre-guard* ratio `sharpe(2nd half) /
  sharpe(1st half)` **with both halves losing** (e.g. `1.8391876…`), which the current sign-aware
  code reports as `0.0`. In the other two artifacts the published block does not re-derive at all.
  No verdict moves (all five are `all_pass: false`), but the drift is undocumented.
- **Disclosure (H47)** — the committed trade logs' `cost` column (H10, H11, H16, H21, H22, H25)
  and the `avg_trade_cost` of the three exploratory 2026-10-10 MA-crossover summaries carry the
  pre-fix aggregate attribution. The artifacts are frozen and were left untouched; no gate,
  threshold, verdict or certified number reads them.
- The committed `src/qtr.egg-info/` manifest is stale; regenerating it with the local setuptools
  would degrade its `PKG-INFO`, so it was left untouched (pre-existing, cosmetic). **Two sessions
  have now hit this** — the next attempt must untrack the manifest, not regenerate it.
- H9's published OOS Sharpe is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict cannot move (REJECT on the profit factor, 55× margin over its 1.0 gate).
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified
  families' numbers and verdicts are frozen.

## Approaches already tried / failed (and why)

- **A negative control that only asserted the new keyword exists** — rejected: it failed against
  the pre-fix implementation with `TypeError` (the parameter was *missing*), not because the
  behaviour was wrong. The contract now goes through the `_seeded()` adapter, so the pre-fix
  implementation is driven down its unseeded path and the control is behavioural — the same lesson
  H47 learned for the engine.
- **One shared seed for every parameter row** — rejected: it would make the rows perfectly
  correlated (two identical rows would report identical intervals). Each row gets its own spawned
  stream instead.
- **Regenerating `src/qtr.egg-info/` with the local setuptools** — rejected: setuptools 68.1.2
  writes `Metadata-Version: 2.1` and drops the core `Requires-Dist` entries, a *regression* in the
  committed metadata.
