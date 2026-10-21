# HANDOFF_CURRENT_SESSION — H47: the engine's trade log reconciles with the costs it charges

## What changed

- `src/qtr/backtest/engine.py` — the trade log now records **each trade's own transaction cost**
  instead of the bar's aggregate cost:
  - `_calculate_costs_by_symbol` (new) computes the per-symbol cost of each bar;
  - `_total_costs` (new) sums that breakdown into the per-bar charge, in the same column order
    and with the same float arithmetic as before, so the charge is **bit-identical**;
  - `_calculate_costs` is kept as the wrapper `run_h27_pnl_level_audit.py:218` uses and returns
    the same series as before;
  - `_extract_trades` now takes the per-symbol breakdown and writes
    `cost = symbol_cost_series.at[idx]`.
- `tests/test_trade_log_cost_reconciliation.py` — **new**, 13 tests: the reconciliation invariant
  (per-bar and in total, for the equity/futures/crypto paths), the own-cost identity reproduced by
  an independent formula, the strict-`1/k` share in a multi-trade bar, the unchanged charge, a
  **negative control** (the pre-fix aggregate attribution is reconstructed and shown to fail the
  invariant), and the frozen-artifact disclosure.
- `FINAL_REPORT.md` — new **§H47** section and an updated "Next task" section.
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_NEXT.md` updated.

### The defect and its evidence

`_extract_trades` wrote the trade log's `cost` column from the **per-bar portfolio cost** series,
so every trade in a bar carried the whole bar's cost: a bar with `k` simultaneous trades reported
`k` times the cost actually deducted from the returns, the log no longer reconciled with the P&L,
and `avg_trade_cost` was an average per trade-*bar*. It is invisible in a single-symbol backtest,
which is why it survived.

On the certified H10 artifact (3,701 trades, 2,975 bars, up to 5 simultaneous trades per bar):
every trade in a bar records the same number (0 of 2,975 bars disagree), the per-bar totals sum to
the engine's charge **0.034907**, and the published `cost` column sums to **0.062352** — an
over-count of **1.786×**. The charge was never wrong: H27's own `L3` check recomputes the per-bar
cost from the trade log and matches the engine's per-bar cost to ~1e-19 for all five audited
families.

## What was actually verified

- `python -m pytest -q -W error tests/test_trade_log_cost_reconciliation.py` → **13 passed**.
- `python -m pytest -q -W error` → **1341 passed, 1 skipped**; `src/qtr` =
  **1048 statements, 318 branches, 0 missed, 0 partial, 100.00%**; the committed gate reports
  *"Required test coverage of 100.0% reached. Total coverage: 100.00%"*.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **90 files already formatted**.
- **Negative control** — the new contract run against the **pre-fix** engine: **6 of the 13 tests
  fail**, the first with the exact over-count (`log=0.0016` against `charged=0.0008`).
- **Attribution-only** — pre-fix and post-fix engines side by side over nine
  equity/futures/crypto cases: the net returns, the equity curve, the positions and every metric
  except `avg_trade_cost` are bit-identical.

## What remains unresolved

- **Disclosure (H47)** — the committed trade logs' `cost` column (H10, H11, H16, H21, H22, H25)
  and the `avg_trade_cost` of the three exploratory 2026-10-10 MA-crossover summaries carry the
  pre-fix aggregate attribution. The artifacts are frozen and were left untouched; no gate,
  threshold, verdict or certified number reads them.
- The committed `src/qtr.egg-info/` manifest is stale; regenerating it with the local setuptools
  would degrade its `PKG-INFO`, so it was left untouched (pre-existing, cosmetic). **Two sessions
  have now hit this** — the next attempt must untrack the manifest, not regenerate it.
- H9's sample-convention Sharpe disclosure, and the exhausted H1–H30 hypothesis space, stand.

## Approaches already tried / failed (and why)

- **Regenerating `src/qtr.egg-info/` with the local setuptools** — rejected as a regression to the
  committed metadata.
- **Fixing the trade log by changing the charge** — rejected: the charge was never wrong (H27's
  `L3` check proves it to ~1e-19); only the attribution inside the log was wrong.
- **A negative control that only asserted the new API exists** — rejected: it failed against the
  pre-fix engine because the method was *missing*, not because the behaviour was wrong; the spy
  now hooks both `_total_costs` and `_calculate_costs` so the control is behavioural.

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
