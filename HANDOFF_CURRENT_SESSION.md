# HANDOFF_CURRENT_SESSION — H48: the package's stochastic surface is seedable

## What changed

- `src/qtr/validation/statistics.py`
  - `parameter_sensitivity` now takes an **optional** `random_state` (default `None`, so **no
    existing caller changes behaviour**);
  - `_bootstrap_seeds` (new) expands an integer seed into **one independent stream per parameter
    row** (`np.random.SeedSequence(seed).spawn(n)`), so the rows are not resampled with a shared
    pattern; a row's seed does not depend on how many rows the grid holds, so extending the grid
    does not perturb the rows already analysed; the unseeded path passes `None` straight through.
- `tests/test_parameter_sensitivity_reproducibility.py` — **new**, 14 tests: exact reproducibility
  under a fixed seed, seed isolation from the legacy global `np.random.seed`, different seeds →
  different bounds, seed-free point estimates, row independence, grid-extension stability,
  **cross-process** reproducibility, a **negative control** (the unseeded path really moves; the
  pre-fix call site is reconstructed and shown to fail the invariant), and the published-record
  disclosure.
- `FINAL_REPORT.md` — new **§H48** section and an updated "Next task" section.
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_NEXT.md` updated.

### The defect and its evidence

`parameter_sensitivity` is exported in `qtr.validation.__all__` but called
`bootstrap_confidence_interval` **without** a `random_state`, so `np.random.default_rng(None)` drew
from OS entropy and two calls on the same input returned **different** confidence intervals
(measured on a fixed input: `ci_lower` = `[-0.7393122, -2.54308907]` then `[-0.93933284,
-3.07895489]`). Its siblings `sharpe_ratio_ci` and `bootstrap_confidence_interval`
both accept `random_state`, and all three runners that call the bootstrap directly pass
`random_state=SEED` (`run_cs_momentum_experiment.py:385`, `run_ts_momentum_experiment.py:563`,
`run_regime_gated_momentum_experiment.py:725`); `parameter_sensitivity` was the only bootstrap
caller in the package that could not be seeded.

The point estimates were always deterministic — only the bounds move — which is why the defect was
invisible in every published number.

With the fix, `src/qtr` contains exactly **two** randomness sites, both in `statistics.py`, and
every stochastic computation reachable from the public API now takes a `random_state`.

## What was actually verified

- `python -m pytest -q -W error tests/test_parameter_sensitivity_reproducibility.py` → **14 passed**.
- `python -m pytest -q -W error` → **1355 passed, 1 skipped**; `src/qtr` =
  **1054 statements, 320 branches, 0 missed, 0 partial, 100.00%**; the committed gate reports
  *"Required test coverage of 100.0% reached. Total coverage: 100.00%"*.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **91 files already formatted**.
- **Negative control** — the new contract run against the **pre-fix** implementation: **4 of the 14
  tests fail**, every one **behaviourally** (the bounds move; e.g. `-0.5059` against `-0.7423`), not
  with a `TypeError` for a missing keyword.
- **Preconditions verified before the change** — no `run_*.py` calls `parameter_sensitivity` (AST
  scan of all 32 runners) and `validate_strategy` derives its published `param_stability` from the
  walk-forward fold Sharpes (`src/qtr/validation/statistics.py:714`); both are now pinned.

## What remains unresolved

- **The published `validation` blocks are on an older `validate_strategy`** — the five committed
  exploratory summaries carry a `validation` block written by a version with **no
  `param_stability` gate** and a **sign-unaware** walk-forward ratio. Re-deriving the block from
  each artifact's own frozen `equity_curve.parquet` shows `sharpe`, `profit_factor`,
  `max_drawdown` and `total_return` reproduce from the frozen data in three of the five, but
  `walkforward_stability` does not: the published value is exactly
  `sharpe(second half) / sharpe(first half)` **with both halves losing** (e.g. `1.8391876…` from
  `−1.5594 / −0.8479`), a figure the current sign-aware code reports as `0.0`. In the other two
  artifacts the published block does not re-derive at all, and the two blocks were written by
  *different* code versions on the *same* series. No verdict moves (all five are
  `all_pass: false`), but the drift is real and is currently undocumented. → **H49**.
- **Disclosure (H47)** — the committed trade logs' `cost` column (H10, H11, H16, H21, H22, H25)
  and the `avg_trade_cost` of the three exploratory 2026-10-10 MA-crossover summaries carry the
  pre-fix aggregate attribution. The artifacts are frozen and were left untouched; no gate,
  threshold, verdict or certified number reads them.
- The committed `src/qtr.egg-info/` manifest is stale; regenerating it with the local setuptools
  would degrade its `PKG-INFO`, so it was left untouched (pre-existing, cosmetic). **Two sessions
  have now hit this** — the next attempt must untrack the manifest, not regenerate it.
- H9's sample-convention Sharpe disclosure, and the exhausted H1–H30 hypothesis space, stand.

## Approaches already tried / failed (and why)

- **A negative control that only asserted the new keyword exists** — rejected: it failed against
  the pre-fix implementation with `TypeError` (the parameter was *missing*), not because the
  behaviour was wrong. The contract now goes through the `_seeded()` adapter, so the pre-fix
  implementation is driven down its unseeded path and the control is behavioural. (This is the same
  lesson H47 learned for the engine.)
- **One shared seed for every parameter row** — rejected: it would make the rows perfectly
  correlated (two identical rows would report identical intervals). Each row gets its own spawned
  stream instead.
- **Regenerating `src/qtr.egg-info/` with the local setuptools** — rejected as a regression to the
  committed metadata.

## Precise next task

**H49 — re-derive the published `validation` blocks from the frozen artifacts, and disclose the
`walkforward_stability` basis they were written on.** The five committed exploratory summaries that
carry a `validation` block (`exp_2026-10-10T17-02-22-080026Z`, `exp_2026-10-10T17-03-39-610858Z`,
`exp_2026-10-10T17-04-21-400695Z`, `exp_2026-10-10T17-05-58-697503Z`,
`exp_2026-10-14T08-26-02-537359Z`) were written by an **earlier** `validate_strategy` — one with
**no `param_stability` gate** and a **sign-unaware** walk-forward ratio. Re-deriving the block from
each artifact's own frozen `equity_curve.parquet` shows `sharpe`, `profit_factor`, `max_drawdown`
and `total_return` reproduce from the frozen data in three of the five, but
`walkforward_stability` does not: the published value is exactly
`sharpe(second half) / sharpe(first half)` **with both halves losing** (e.g. `1.8391876…` from
`−1.5594 / −0.8479`), which *passed* the `0.7` gate on a strategy that lost money in both halves;
the current sign-aware code reports `0.0`. In the other two artifacts the published block does not
re-derive at all, and the two blocks were written by *different* code versions on the *same*
series. Determine the cause (do not assume it), publish the finding as a **disclosure** (the
artifacts are frozen — the published `walkforward_pass` and the absent `param_stability` key are
*history*), and pin it with a test module that re-derives the block from the frozen equity curve
and asserts the published values, so the drift cannot change silently. The **certified** families
are out of scope: they carry no `validation` block, and no gate, threshold, verdict or certified
number may move. Full statement, with the measured table, in `NEXT_TASK.md`.
