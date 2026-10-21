# HANDOFF — H47 complete (session handoff)

## What changed

**H47:** the engine's trade log now reconciles with the transaction costs the engine charges.

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
- `FINAL_REPORT.md` — new **§H47** section and an updated "Next task" section.
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`,
  `HANDOFF_NEXT.md` updated.

### The defect

`_extract_trades` wrote the trade log's `cost` column from the **per-bar portfolio cost** series,
so every trade in a bar carried the **whole bar's** cost. A bar with `k` simultaneous trades
reported `k` times the cost that was actually deducted from the returns: the trade log no longer
reconciled with the P&L it exists to audit, and `metrics["avg_trade_cost"]` was an average *per
trade-bar* rather than per trade. The defect is invisible in a single-symbol backtest, which is
why it survived.

### The evidence

The certified H10 artifact (3,701 trades, 2,975 bars, up to 5 simultaneous trades per bar):
every trade in a bar records the same number (0 of 2,975 bars disagree); the per-bar totals sum
to the engine's charge, **0.034907**; the published `cost` column sums to **0.062352** — an
over-count of **1.786×**. The charge itself was never wrong: the repository's own H27 `L3` check
recomputes the per-bar cost from the trade log and matches the engine's per-bar cost to ~1e-19
for all five audited families.

## What was actually verified

- `python -m pytest -q -W error tests/test_trade_log_cost_reconciliation.py` → **13 passed**.
- `python -m pytest -q -W error` → **1341 passed, 1 skipped**; `src/qtr` =
  **1048 statements, 318 branches, 0 missed, 0 partial, 100.00%**; the committed gate reports
  *"Required test coverage of 100.0% reached. Total coverage: 100.00%"*.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **90 files already formatted**.
- **Negative control** — the new contract run against the **pre-fix** engine: **6 of the 13 tests
  fail**, the first with the exact over-count (`log=0.0016` against `charged=0.0008`).
- **Attribution-only** — the pre-fix and post-fix engines were run side by side over nine
  equity/futures/crypto cases: the net returns, the equity curve, the positions and every metric
  except `avg_trade_cost` are **bit-identical**.

## What remains unresolved

- **Disclosure (H47)** — the `cost` column of the **committed** trade logs (H10, H11, H16, H21,
  H22, H25) and the `avg_trade_cost` of the three exploratory 2026-10-10 MA-crossover summaries
  carry the pre-fix aggregate attribution. The artifact files are frozen and were left untouched.
  No gate, threshold, verdict or certified number reads them.
- The **committed** `src/qtr.egg-info/` manifest is stale (it predates eight test modules added
  since H33). Regenerating it with the setuptools available here (68.1.2) would *degrade* the
  committed `PKG-INFO` (`Metadata-Version: 2.1`, core `Requires-Dist` entries dropped), so it
  was left untouched. Pre-existing, cosmetic: the build regenerates it. **Two sessions have now
  hit this** — the next attempt must use a materially different approach (untrack the manifest:
  `*.egg-info/` in `.gitignore` + `git rm --cached src/qtr.egg-info`), not another regeneration.
- H9's published OOS Sharpe is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict cannot move (REJECT on the profit factor, 55× margin over its 1.0 gate).
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified
  families' numbers and verdicts are frozen.

## Approaches already tried / failed (and why)

- **Regenerating `src/qtr.egg-info/` with the local setuptools** — rejected: setuptools 68.1.2
  writes `Metadata-Version: 2.1` and drops the core `Requires-Dist` entries, which is a
  *regression* in the committed metadata. The stale manifest is pre-existing and cosmetic.
- **Fixing the trade log by changing the charge** — rejected: the charge was never wrong (H27's
  `L3` check proves it to ~1e-19). Only the attribution inside the log was wrong, so the fix moves
  the log, not the charge.
- **A negative control that only asserted the new API exists** — rejected: the first version
  failed against the pre-fix engine because the method was *missing*, not because the behaviour
  was wrong. The spy now hooks both `_total_costs` and `_calculate_costs`, so the control is
  behavioural.

## Precise next task

**H48 — make `qtr.validation.statistics.parameter_sensitivity` reproducible.** It is exported in
`qtr.validation.__all__` but calls `bootstrap_confidence_interval` **without** a `random_state`,
so its confidence intervals change on every call (measured: `ci_lower` = `[-0.866, -0.409,
-0.631, -1.040]` then `[-0.801, -0.465, -0.521, -0.972]` on the same input). Its siblings
`sharpe_ratio_ci` and `bootstrap_confidence_interval` both accept `random_state`, and all three
runners that call the bootstrap directly pass `random_state=SEED`; `parameter_sensitivity` is the
only bootstrap caller in the package that cannot be seeded. Add an optional `random_state`
parameter, thread it through, and pin the contract with a negative control. **The published record
is unaffected**: no runner calls `parameter_sensitivity`, and `validate_strategy` derives its
published `param_stability` from the walk-forward fold Sharpes
(`src/qtr/validation/statistics.py:714`), not from `parameter_sensitivity` — verify that claim
before changing anything.
