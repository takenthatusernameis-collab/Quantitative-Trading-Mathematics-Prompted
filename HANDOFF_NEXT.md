# HANDOFF_NEXT — H47: the engine's trade log reconciles with the transaction costs it charges

## What changed (this session)

- `src/qtr/backtest/engine.py` — the trade log now records **each trade's own cost** instead of
  the bar's aggregate cost:
  - `_calculate_costs_by_symbol` (new) computes the per-symbol cost of each bar;
  - `_total_costs` (new) sums that breakdown into the per-bar charge, in the same column order
    and with the same float arithmetic as before, so the charge is **bit-identical**;
  - `_calculate_costs` is kept as the wrapper the H27 runner uses
    (`run_h27_pnl_level_audit.py:218`) and returns the same series as before;
  - `_extract_trades` now takes the per-symbol breakdown and writes
    `cost = symbol_cost_series.at[idx]`.
- `tests/test_trade_log_cost_reconciliation.py` — **new**, 13 tests.
- `FINAL_REPORT.md` — new **§H47** section and an updated "Next task" section.
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md` updated.

## The defect this closed

`_extract_trades` wrote the `cost` column of the trade log from the **per-bar portfolio cost**
series:

```python
"cost": costs[idx] if idx in costs.index else 0,     # `costs` is the per-BAR TOTAL
```

Every trade in a bar therefore carried the **whole bar's** transaction cost. A bar with `k`
simultaneous trades reported `k` times the cost that was actually deducted from the returns, so
the trade log no longer reconciled with the P&L it exists to audit, and `metrics["avg_trade_cost"]`
was an average *per trade-bar* rather than per trade.

The defect is invisible in a single-symbol backtest (there the bar total **is** the trade's own
cost), which is why it survived: the runners that exercise the multi-contract path are the
intraday futures family.

### Evidence (frozen artifacts, read-only)

The certified H10 artifact (`exp_2026-10-11T17-41-18-169363Z`) holds **3,701** trades over
**2,975** bars with up to **5** simultaneous trades per bar:

| Quantity | Value |
|---|---|
| bars whose trades do **not** all record the same number | **0 of 2,975** |
| the per-bar totals (= the engine's charge) | **0.034907** |
| the published `cost` column, summed over all trades | **0.062352** |
| **over-count factor** | **1.786×** |

The charge itself is confirmed correct by the repository's own **H27 `L3` check**, which
recomputes the per-bar cost *from the trade log* (each trade's own cost, summed per bar) and
matches the engine's per-bar cost to **~1e-19** for all five audited families (H9, H10, H21, H22,
H25). The engine already computed the correct per-trade cost; the log simply did not carry it.

## The contract

`tests/test_trade_log_cost_reconciliation.py` pins the reconciliation in six layers:

1. **Reconciliation** — the per-trade costs sum to the charged cost, bar by bar and in total, for
   the equity, futures and crypto cost paths.
2. **Own-cost identity** — a trade's cost is reproduced by an *independent* formula from the trade
   log and the cost model (`|Δw| · bps / 10⁴` for equity, `|Δw| · C / (p · m)` for futures), so
   the attribution is checked, not merely re-derived from the engine's internals.
3. **Strict share** — in a bar with `k > 1` trades each trade accounts for exactly `1/k` of the
   bar's charge.
4. **The charge is unchanged** — the engine's net returns are still exactly the gross returns minus
   the charged series (taken from the *final* positions, because the engine normalises the
   leverage before it prices the trades).
5. **Negative control** — the pre-fix (aggregate) attribution is reconstructed from the fixed log
   and is shown to **fail** the reconciliation; the single-symbol case is shown to be unable to
   reveal the defect.
6. **Frozen-record disclosure** — the committed H10 trade log still shows the pre-fix aggregate
   attribution (0 of 2,975 bars disagree; over-count 1.786×), and the H27 `L3` result is pinned as
   the proof that the bar total is the charge.

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

## What remains unresolved (disclosures, not rewrites)

- The `cost` column of the **committed** trade logs (H10, H11, H16, H21, H22, H25) and the
  `avg_trade_cost` of the three **exploratory** 2026-10-10 MA-crossover summaries carry the
  pre-fix aggregate attribution. The artifact files are frozen and were left untouched. No gate,
  threshold, verdict or certified number reads them.
- The **committed** `src/qtr.egg-info/` manifest is stale. Regenerating it with setuptools 68.1.2
  would *degrade* the committed `PKG-INFO`; left untouched (pre-existing, cosmetic). Two sessions
  have now hit this — a materially different approach is required (untrack the manifest), not
  another regeneration.
- H9's published OOS Sharpe is on the sample convention (gap 1.026e-04); disclosed and pinned.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified
  families' numbers and verdicts are frozen.

## Approaches already tried / failed (and why)

- **Regenerating `src/qtr.egg-info/` with the local setuptools** — rejected as a regression to the
  committed metadata; the stale manifest is cosmetic (the build regenerates it).
- **Fixing the trade log by changing the charge** — rejected: the charge was never wrong (H27's
  `L3` check proves it). Only the attribution inside the log was wrong, so the fix moves the log,
  not the charge.
- **A negative control that only asserted the new API exists** — rejected: the first version of
  the control failed because the pre-fix engine *lacked* `_total_costs`, not because the
  behaviour was wrong. The spy now hooks both `_total_costs` and `_calculate_costs`, so the
  control is behavioural.

## Precise next task

**H48 — make `qtr.validation.statistics.parameter_sensitivity` reproducible.** It is exported in
`qtr.validation.__all__` but calls `bootstrap_confidence_interval` **without** a `random_state`,
so its confidence intervals change on every call (measured: `ci_lower` = `[-0.866, -0.409,
-0.631, -1.040]` then `[-0.801, -0.465, -0.521, -0.972]` on the same input). Its siblings
`sharpe_ratio_ci` and `bootstrap_confidence_interval` both accept `random_state`, and all three
runners that call the bootstrap directly pass `random_state=SEED`; `parameter_sensitivity` is the
only bootstrap caller in the package that cannot be seeded. Add an optional `random_state`
parameter, thread it through, and pin the contract with a negative control. **The published
record is unaffected**: no runner calls `parameter_sensitivity`, and `validate_strategy` derives
its published `param_stability` from the walk-forward fold Sharpes
(`src/qtr/validation/statistics.py:714`), not from `parameter_sensitivity` — verify that claim
before changing anything.

## State a next session inherits

- The pre-registered free-data hypothesis space (H1–H30) remains **exhausted**; no new
  hypothesis is warranted and no grid may be re-run.
- Every published artifact, threshold, verdict and certified number is frozen.
- The shared library, the engine **and every `run_*.py`** remain pinned as **point-in-time**;
  re-run `tests/test_causality_invariant.py` after any change under `src/qtr`,
  `tests/test_runner_causality_inventory.py` after any change in a runner,
  `tests/test_public_api_contract.py` after any change under `src/qtr`,
  `tests/test_runner_import_contract.py` after any change in a runner or under `src/qtr`, and
  `tests/test_trade_log_cost_reconciliation.py` after any change under `src/qtr/backtest`.
