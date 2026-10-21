# Next Task

## State

H35–H46 complete (the coverage gate is measured, declared and complete at 100% statement +
branch; the package's public API and the runners' import surface are both declared and pinned).
**H47 is complete**: the engine's trade log now reconciles with the transaction costs the engine
charges, and the reconciliation is pinned by a non-vacuous executable contract.

## What changed (H47)

- `src/qtr/backtest/engine.py` — the cost model now keeps the **per-symbol** breakdown
  (`_calculate_costs_by_symbol`), the per-bar charge is their sum (`_total_costs`), and
  `_extract_trades` attributes each trade **its own** cost instead of the bar's aggregate cost.
  `_calculate_costs` is kept (it is used by `run_h27_pnl_level_audit.py:218`) and returns the same
  series as before.
- `tests/test_trade_log_cost_reconciliation.py` — **new**, 13 tests: the reconciliation invariant
  (per-bar and in total, for the equity/futures/crypto paths), the own-cost identity reproduced by
  an independent formula, the strict-`1/k` share in a multi-trade bar, the unchanged charge, a
  **negative control** (the pre-fix aggregate attribution is reconstructed and shown to fail the
  invariant), and the frozen-artifact disclosure.

## What was actually verified

- `python -m pytest -q -W error tests/test_trade_log_cost_reconciliation.py` → **13 passed**.
- `python -m pytest -q -W error` → **1341 passed, 1 skipped** (full suite).
- `python -m pytest -q -W error --cov=qtr --cov-branch` → `src/qtr` = **1048 statements, 318
  branches, 0 missed, 0 partial, 100.00%**; the committed gate reports *"Required test coverage of
  100.0% reached. Total coverage: 100.00%"*.
- `python -m ruff check src tests run_*.py` → **All checks passed!**.
- `python -m ruff format --check src tests run_*.py` → **90 files already formatted**.
- **Negative control** — the new contract run against the **pre-fix** engine: **6 of the 13 tests
  fail**, the first with the exact over-count (`log=0.0016` against `charged=0.0008`).
- **Attribution-only** — the pre-fix and post-fix engines were run side by side over nine
  equity/futures/crypto cases: the net returns, the equity curve, the positions and every metric
  except `avg_trade_cost` are **bit-identical**.

## What remains unresolved

- The **committed** `src/qtr.egg-info/` manifest is stale (it predates eight test modules added
  since H33). Regenerating it with the setuptools available here (68.1.2) would *degrade* the
  committed `PKG-INFO` (`Metadata-Version: 2.1`, core `Requires-Dist` entries dropped), so it
  was left untouched. Pre-existing, cosmetic: the build regenerates it. The next session that
  wants to close it should use a **materially different** approach — stop tracking the generated
  manifest (add `*.egg-info/` to `.gitignore` and `git rm --cached src/qtr.egg-info`) rather than
  regenerating it with a local setuptools.
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

- **Regenerating `src/qtr.egg-info/` with the local setuptools** — rejected as a regression to
  the committed metadata (see above). Two sessions have now hit this; a materially different
  approach is required (untrack the manifest), not another regeneration.
- **An explicit top-level `__all__` list** — rejected in favour of composing it from the
  subpackages' `__all__`s, so the aggregate cannot drift from what it aggregates.
- **Fixing the H10 trade-log cost by changing the charge** — rejected: the charge was never
  wrong. The H27 `L3` check proves it (the per-bar cost recomputed from the trade log matches the
  engine's per-bar cost to ~1e-19 for all five audited families). Only the *attribution* inside
  the log was wrong, so the fix moves the log, not the charge.

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
- Re-run `tests/test_runner_causality_inventory.py` and `tests/test_runner_metric_agreement.py`
  after any change in a runner.
- The coverage gate (`python -m pytest -q --cov=qtr --cov-branch`) must stay at 100% for
  `src/qtr`; the lint gate (`python -m ruff check src tests run_*.py` and
  `python -m ruff format --check src tests run_*.py`) must stay clean.

## The next task (H48)

> **Make `qtr.validation.statistics.parameter_sensitivity` reproducible.**
>
> The function is part of the public API (`qtr.validation.__all__`) but it calls
> `bootstrap_confidence_interval` **without** a `random_state`, so `np.random.default_rng(None)`
> draws from OS entropy and two calls on the same input return **different** confidence
> intervals. Measured on a fixed input: `ci_lower` = `[-0.866, -0.409, -0.631, -1.040]` on the
> first call and `[-0.801, -0.465, -0.521, -0.972]` on the second (the point estimates,
> `stability_ratio`, `optimal_param` and `metric_std` are deterministic — only the bootstrap
> bounds move).
>
> Its siblings already do the right thing: `sharpe_ratio_ci` and `bootstrap_confidence_interval`
> both accept `random_state`, and all three runners that call the bootstrap directly pass
> `random_state=SEED` (`run_cs_momentum_experiment.py:386`, `run_ts_momentum_experiment.py:564`,
> `run_regime_gated_momentum_experiment.py:726`). `parameter_sensitivity` is the **only**
> bootstrap caller in the package that cannot be seeded.
>
> **The work.** Add an optional `random_state` parameter to `parameter_sensitivity` and thread it
> into its `bootstrap_confidence_interval` call (backwards compatible: the default stays `None`,
> so no existing caller changes behaviour), then pin the contract in a new test module:
> two calls with the same seed agree exactly; the same seed on different data may differ; and the
> default (unseeded) path is explicitly documented as non-reproducible rather than silently
> relied upon. A negative control must show that the unseeded path really does move.
>
> **The published record is unaffected.** No runner calls `parameter_sensitivity`, and
> `validate_strategy` computes its published `param_stability` from the walk-forward fold Sharpes
> (`src/qtr/validation/statistics.py:714`), **not** from `parameter_sensitivity`. So the
> `min_param_stability` gate stays deterministic and no published number moves. Verify that
> claim against the runners before changing anything, and record it as a disclosure.
