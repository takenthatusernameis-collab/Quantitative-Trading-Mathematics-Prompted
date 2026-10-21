# HANDOFF_NEXT — H48: the package's stochastic surface is seedable

## What changed (this session)

- `src/qtr/validation/statistics.py` — the public API's last unseedable bootstrap caller is now
  seedable:
  - `parameter_sensitivity` takes an **optional** `random_state` (default `None`, so **no existing
    caller changes behaviour** — the unseeded path is exactly what it always was, now *documented*
    as non-reproducible);
  - `_bootstrap_seeds` (new) expands an integer seed into **one independent stream per parameter
    row** (`np.random.SeedSequence(seed).spawn(n)`), so the rows are not resampled with a shared
    pattern; a row's seed does not depend on how many rows the grid holds, so extending the grid
    does not perturb the rows already analysed; the unseeded path passes `None` straight through.
- `tests/test_parameter_sensitivity_reproducibility.py` — **new**, 14 tests.
- `FINAL_REPORT.md` — new **§H48** section and an updated "Next task" section.
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md` updated.

## The defect this closed

`parameter_sensitivity` is exported in `qtr.validation.__all__` but called
`bootstrap_confidence_interval` **without** a `random_state`, so `np.random.default_rng(None)` drew
from OS entropy and two calls on the same input returned **different** confidence intervals:

| call | `ci_lower` (2 rows, `n_bootstrap=200`) |
|---|---|
| 1 | `[-0.7393122, -2.54308907]` |
| 2 | `[-0.93933284, -3.07895489]` |

Its siblings `sharpe_ratio_ci` and `bootstrap_confidence_interval` both accept `random_state`, and
all three runners that call the bootstrap directly pass `random_state=SEED`
(`run_cs_momentum_experiment.py:385`, `run_ts_momentum_experiment.py:563`,
`run_regime_gated_momentum_experiment.py:725`). `parameter_sensitivity` was the only bootstrap
caller in the package that could not be seeded.

The point estimates (`metrics`, `optimal_param`, `optimal_metric`, `stability_ratio`,
`metric_std`) were always deterministic — only the bounds move — so the defect was invisible in
every published number.

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
  tests fail**, every one **behaviourally** (the bounds move; e.g. `-0.5059` against `-0.7423`),
  not with a `TypeError` for a missing keyword.
- **Preconditions verified before the change** — no `run_*.py` calls `parameter_sensitivity` (AST
  scan of all 32 runners) and `validate_strategy` derives its published `param_stability` from the
  walk-forward fold Sharpes (`src/qtr/validation/statistics.py:714`); both are now pinned.

## The published record is unaffected

No published artifact, gate threshold, verdict or certified number was modified; no grid was
re-run; no hypothesis was added. The default path is byte-for-byte the behaviour it always had.
`validate_strategy` computes its published `param_stability` from the walk-forward fold Sharpes,
**not** from `parameter_sensitivity`, so the `min_param_stability` gate stays deterministic.

## What a next session inherits

- **H49 is assigned** (stated in full in `NEXT_TASK.md`): re-derive the published `validation`
  blocks from the frozen artifacts and disclose the `walkforward_stability` basis they were written
  on. Measured evidence is in `NEXT_TASK.md`; the key observation is that the published
  `walkforward_stability` in three of the five artifacts is the *pre-guard* ratio
  `sharpe(2nd half) / sharpe(1st half)` **with both halves losing** (e.g. `1.8391876…`), which the
  current sign-aware code reports as `0.0` — and that in the other two artifacts the published
  block does not re-derive at all, so two blocks were written by different code versions on the
  same series. The artifacts are frozen: publish the finding, do not rewrite them.
- **Disclosure (H47)** — the committed trade logs' `cost` column and the exploratory summaries'
  `avg_trade_cost` carry the pre-fix aggregate attribution; frozen, untouched, unread by any gate.
- The committed `src/qtr.egg-info/` manifest is stale; **untrack** it (`.gitignore` +
  `git rm --cached`), do not regenerate it — two sessions have now failed the regeneration route.
- The H1–H30 hypothesis space remains exhausted; the certified families are frozen.
