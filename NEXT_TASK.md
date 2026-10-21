# Next Task

## State

H35–H48 complete (the coverage gate is measured, declared and complete at 100% statement +
branch; the package's public API and the runners' import surface are both declared and pinned; the
engine's trade log reconciles with the costs it charges; the package's stochastic surface is
seedable).
**H49 is complete**: the published `validation` blocks in all five exploratory summaries re-derive
from their own frozen `equity_curve.parquet` under the engine's full return convention, and the
`walkforward_stability` basis — the sign-unaware `sharpe(2nd half) / sharpe(1st half)` — is
disclosed and pinned by `tests/test_h49_validation_block_disclosure.py` (11 tests).

## What changed (H48)

- `src/qtr/validation/statistics.py`
  - `parameter_sensitivity` takes an **optional** `random_state` (default `None`, so **no existing
    caller changes behaviour**).
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

## What was actually verified

- `python -m pytest -q -W error tests/test_parameter_sensitivity_reproducibility.py` → **14 passed**.
- `python -m pytest -q -W error` → **1355 passed, 1 skipped** (full suite).
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` → `src/qtr` = **1054
  statements, 320 branches, 0 missed, 0 partial, 100.00%**; the committed gate reports *"Required
  test coverage of 100.0% reached. Total coverage: 100.00%"*.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **91 files already formatted**.
- **Negative control** — the new contract run against the **pre-fix** implementation: **4 of the 14
  tests fail**, and every failure is **behavioural** (the bounds move; e.g. `-0.5059` against
  `-0.7423`), not a `TypeError` for a missing keyword. An earlier draft of the contract failed
  only with `TypeError: parameter_sensitivity() got an unexpected keyword argument
  'random_state'`; that measures the *API* rather than the behaviour and was replaced by the
  `_seeded()` adapter, which drives the pre-fix function down its unseeded path.
- **Preconditions verified before the change** — no `run_*.py` calls `parameter_sensitivity`
  (AST scan of all 32 runners), and `validate_strategy` derives its published `param_stability`
  from the walk-forward fold Sharpes (`src/qtr/validation/statistics.py:714`), **not** from
  `parameter_sensitivity`; both facts are now pinned by the new contract.

## What remains unresolved

- **The published `validation` blocks are on an older `validate_strategy`** (the new assignment,
  H49). The five committed exploratory summaries (2026-10-10 / 2026-10-14 MA-crossover runs) carry
  a `validation` block written by a version with **no `param_stability` gate** and with a
  **sign-unaware** walk-forward ratio. Re-deriving the block from each artifact's own frozen
  `equity_curve.parquet` shows `sharpe`, `profit_factor`, `max_drawdown` and `total_return` **do**
  reproduce from the frozen data (three of the five match to float noise / exactly), but
  `walkforward_stability` does not: in three of the five the published value is exactly
  `sharpe(second half) / sharpe(first half)` **with both halves losing** (e.g. `1.8391876…` from
  `−1.5594 / −0.8479`), a figure the current sign-aware code reports as `0.0`. The published
  `walkforward_pass` is therefore on the pre-guard basis. No verdict moves (all five are
  `all_pass: false`), but the drift is real and is currently undocumented.
- The **committed** `src/qtr.egg-info/` manifest is stale (it predates the test modules added since
  H33). Regenerating it with the setuptools available here (68.1.2) would *degrade* the committed
  `PKG-INFO` (`Metadata-Version: 2.1`, core `Requires-Dist` entries dropped), so it was left
  untouched. Pre-existing, cosmetic: the build regenerates it. A session that wants to close it
  should use a **materially different** approach — stop tracking the generated manifest (add
  `*.egg-info/` to `.gitignore` and `git rm --cached src/qtr.egg-info`) rather than regenerating it
  with a local setuptools. **Two sessions have now hit this.**
- **Disclosure (H47)** — the `cost` column of the **committed** trade logs (H10, H11, H16, H21,
  H22, H25) and the `avg_trade_cost` of the three exploratory 2026-10-10 MA-crossover summaries
  carry the **pre-fix** aggregate attribution. The artifact files are frozen and were left
  untouched. No gate, threshold, verdict or certified number reads them; the H11 reproduction
  check compares Sharpe, profit factor, drawdown, the trade *count*, walk-forward stability and
  worst-regime Sharpe — all unaffected.
- H9's published OOS Sharpe is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict cannot move (REJECT on the profit factor, 55× margin over its 1.0 gate).
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified
  families' numbers and verdicts are frozen.

## Approaches already tried / failed (and why)

- **A negative control that only asserted the new keyword exists** — rejected: it failed against
  the pre-fix implementation with `TypeError` (the parameter was *missing*), not because the
  behaviour was wrong. The contract now goes through the `_seeded()` adapter, so the pre-fix
  implementation is driven down its unseeded path and the control is **behavioural**.
- **Regenerating `src/qtr.egg-info/` with the local setuptools** — rejected as a regression to the
  committed metadata. Two sessions have now hit this; a materially different approach is required
  (untrack the manifest), not another regeneration.
- **An explicit top-level `__all__` list** — rejected in favour of composing it from the
  subpackages' `__all__`s, so the aggregate cannot drift from what it aggregates.
- **Fixing the H10 trade-log cost by changing the charge** — rejected: the charge was never
  wrong. The H27 `L3` check proves it (the per-bar cost recomputed from the trade log matches the
  engine's per-bar cost to ~1e-19 for all five audited families). Only the *attribution* inside the
  log was wrong, so the fix moves the log, not the charge.

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
- Re-run `tests/test_runner_causality_inventory.py` and `tests/test_runner_metric_agreement.py`
  after any change in a runner.
- The coverage gate (`python -m pytest -q --cov=qtr --cov-branch`) must stay at 100% for
  `src/qtr`; the lint gate (`python -m ruff check src tests run_*.py` and
  `python -m ruff format --check src tests run_*.py`) must stay clean.

## The next task (H49) — COMPLETE (2026-10-21)

> **Re-derive the published `validation` blocks from the frozen artifacts, and disclose the
> `walkforward_stability` basis they were written on.**

**The corrected finding.** The H48-era handoff claimed the last two artifacts "do not re-derive"
and that the two buy-and-hold blocks were written by *different* code versions on the *same* series.
**Both claims were based on the wrong return convention.** The engine charges costs per bar and
compounds them into the equity curve (`equity = (1 + net_returns).cumprod() * initial_capital`), so
the equity curve carries the full series including the opening bar; `equity.pct_change()` alone
drops that bar. Including the first bar's return — `equity[0] / initial_capital - 1`, the cost of
the very first position change charged on the opening bar — reproduces the published block for
**all five** artifacts to float noise (< 1e-9).

| artifact | `sharpe` | `profit_factor` | `max_drawdown` | `total_return` | `walkforward_stability` |
|---|---|---|---|---|---|
| `…17-02-22-080026Z` | matches (4e-16) | matches | matches | matches | matches (4e-16) |
| `…17-03-39-610858Z` | matches (2e-15) | matches | matches | matches | matches (2e-16) |
| `…17-04-21-400695Z` | matches (9e-16) | matches | matches | matches | matches (4e-15) |
| `…17-05-58-697503Z` | matches (8e-16) | matches | matches | matches | matches (5e-15) |
| `…08-26-02-537359Z` | matches (3e-15) | matches | matches | matches | matches (4e-15) |

(published vs re-derived; "matches" = |diff| < 1e-9)

**The `walkforward_stability` basis.** Every published `walkforward_stability` is exactly
`sharpe(second half) / sharpe(first half)`, taken **unconditionally** — the pre-guard formula. The
published `walkforward_folds` also re-derive from the frozen equity curve under the same convention.

* Three ma_crossover artifacts: **both halves losing** (`−1.5594 / −0.8479 = 1.8391876…`), so the
  sign-unaware ratio **passed** the `0.7` gate on a strategy that lost money in both halves. The
  current sign-aware code reports `0.0` and would report `walkforward_pass: False`.
* Two buy-and-hold artifacts: **both halves profitable**, so the published value and the current
  sign-aware code agree (`1.0277108` and `0.9334875`).

All five published blocks report `walkforward_pass: True` and `all_pass: false`; the current code
would report `walkforward_pass: False` for the three ma_crossover artifacts. **No verdict moves.**

**Why the two buy-and-hold blocks differ from each other.** `exp_2026-10-10T17-05-58-697503Z`
and `exp_2026-10-14T08-26-02-537359Z` run the **same** SPY buy-and-hold series (price series
byte-identical, equity curves proportional), but their published blocks differ because they charged
**different costs**, baked into their own frozen equity curves: `…17-05-58` charged the real cost
model (`avg_trade_cost = 0.041105949376283715`) while `…08-26-02` charged a fixed `0.0002` per
trade (`avg_trade_cost = 0.00020009711746988646`). Each block re-derives exactly from **its own**
frozen equity curve; they do not re-derive from each other's. Disclosed, not reconciled.

**The work.** (a) Determine the return convention from the engine's source and the artifacts'
`config` block (done — the opening bar is included); (b) publish the finding as a **disclosure** in
`FINAL_REPORT.md` §H49 (the artifacts are frozen — the published `walkforward_pass` and the absent
`param_stability` key are *history*); (c) pin it with `tests/test_h49_validation_block_disclosure.py`
(11 tests) that re-derives the block from the frozen equity curve and asserts the published values
— including the pre-guard ratio — so the drift cannot change silently.

**What was verified.** `python -m pytest -q -W error` → **1366 passed, 1 skipped** (up from 1355);
`python -m pytest -q --cov=qtr --cov-branch` → `src/qtr` **1054 statements, 320 branches, 0 missed,
0 partial, 100.00%**; `python -m ruff check src tests run_*.py` → *All checks passed!*; `python -m
ruff format --check src tests run_*.py` → **92 files already formatted**. The re-derivation is
read-only against the frozen artifacts; no pipeline re-execution, no network, no grid re-run; the
five artifacts' `all_pass` is `false` and stays `false`.
