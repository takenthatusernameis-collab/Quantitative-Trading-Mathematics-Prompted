# HANDOFF_CURRENT — session complete (H47)

## State

- **H47 is COMPLETE** as recorded in `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_NEXT.md` and
  `HANDOFF_CURRENT_SESSION.md`: the engine's trade log now records **each trade's own
  transaction cost** and therefore reconciles with the cost the engine charges, pinned by
  `tests/test_trade_log_cost_reconciliation.py` (13 tests: reconciliation for the
  equity/futures/crypto paths, the own-cost identity, the strict-`1/k` share, the unchanged
  charge, a negative control and the frozen-artifact disclosure). The fix is
  **attribution-only**: the net returns, the equity curve, the positions and every metric except
  `avg_trade_cost` are bit-identical to the pre-fix engine.
- **H35, H36, H37, H38, H39, H40, H41, H42, H43, H44, H45 and H46 are COMPLETE**: every gate
  defect class that has surfaced is closed by an executable invariant, the point-in-time invariant
  covers every `run_*.py`, the engine's `total_return` spans every bar, the package's two Sharpe
  implementations agree, the lint/format gate is reproducible, the coverage gate is measured,
  declared and complete, and both the package's public API and the runners' import surface are
  declared and pinned.
- No published artifact, gate threshold, verdict or certified number was modified; no grid was
  re-run; no hypothesis was added.

## What changed (this session — H47)

- `src/qtr/backtest/engine.py` — the cost model now keeps the **per-symbol** breakdown
  (`_calculate_costs_by_symbol`), the per-bar charge is their sum (`_total_costs`), and
  `_extract_trades` attributes each trade its own share. `_calculate_costs` is kept (it is used by
  `run_h27_pnl_level_audit.py:218`) and returns the same series as before.
- `tests/test_trade_log_cost_reconciliation.py` — **new**, 13 tests.
- `FINAL_REPORT.md` — new **§H47** section and an updated "Next task" section.
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`,
  `HANDOFF_NEXT.md` updated.

## What was actually verified

- `python -m pytest -q -W error tests/test_trade_log_cost_reconciliation.py` → **13 passed**.
- `python -m pytest -q -W error` → **1341 passed, 1 skipped**; `src/qtr` =
  **1048 statements, 318 branches, 0 missed, 0 partial, 100.00%**.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **90 files already formatted**.
- **Negative control** — the new contract run against the **pre-fix** engine: **6 of the 13 tests
  fail**, the first with the exact over-count (`log=0.0016` against `charged=0.0008`).
- **Attribution-only** — pre-fix and post-fix engines side by side over nine
  equity/futures/crypto cases: returns, equity, positions and every metric except
  `avg_trade_cost` are bit-identical.

## What remains unresolved

- **Disclosure (H47)** — the committed trade logs' `cost` column (H10, H11, H16, H21, H22, H25)
  and the `avg_trade_cost` of the three exploratory 2026-10-10 MA-crossover summaries carry the
  pre-fix aggregate attribution. The artifacts are frozen and were left untouched; no gate,
  threshold, verdict or certified number reads them.
- The **committed** `src/qtr.egg-info/` manifest is stale. Regenerating it with the local
  setuptools (68.1.2) would *degrade* the committed `PKG-INFO`, so it was left untouched.
  Pre-existing, cosmetic. **Two sessions have now hit this** — use a materially different
  approach next time (untrack the manifest), not another regeneration.
- H9's published OOS Sharpe is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict cannot move (REJECT on the profit factor, 55× margin over its 1.0 gate).
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified
  families' numbers and verdicts are frozen.

## Approaches already tried / failed (and why)

- **Regenerating `src/qtr.egg-info/` with the local setuptools** — rejected as a regression to
  the committed metadata; see above.
- **Fixing the trade log by changing the charge** — rejected: the charge was never wrong (H27's
  `L3` check proves it to ~1e-19); only the attribution inside the log was wrong.
- **A negative control that only asserted the new API exists** — rejected: it failed against the
  pre-fix engine because the method was *missing*, not because the behaviour was wrong.
- **An explicit top-level `__all__` list** — rejected in favour of composing it from the
  subpackages' `__all__`s, so the aggregate cannot drift from what it aggregates.

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
