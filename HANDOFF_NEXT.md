# HANDOFF_NEXT — H38: the engine's `total_return` is fixed; the metric surface is next

## What changed (this session)

1. **`src/qtr/backtest/engine.py:312-320`** — `_calculate_metrics` now measures the total
   return from the **initial capital** (`equity.iloc[-1] / initial_capital - 1`) instead of
   from `equity.iloc[0]`, which dropped the first bar — the only bar that carries the
   initial entry cost. The metric now spans every bar of the return series, agrees with
   `qtr.validation.statistics.validate_strategy` (which computes the same quantity), and
   makes `annualized_return` the `n`-period annualization of an `n`-period total return.

2. **`tests/test_engine_total_return_consistency.py`** (new, 13 tests) — the executable
   contract: the metric against the equity curve and the full return product, the
   cross-module agreement with `validate_strategy`, the invertibility of the
   `(total_return, annualized_return)` pair, a negative control that *detects* the pre-fix
   range, a control that shows the invariant is not over-strict, the published-artifact
   audit (pre-fix convention, corrected convention and gap, pinned against the five
   affected artifacts), the "blind to a 205× cost change" pin, and the guard that **no
   runner reads `metrics["total_return"]`**.

3. **`FINAL_REPORT.md`** — new §H38 and a rewritten `## Next Task` section; the
   `Summary statistics` test count is re-baselined (959 → 1115).

4. **`NEXT_TASK.md`**, **`HANDOFF_CURRENT_SESSION.md`**, this file.

No published artifact, gate threshold, verdict, certified number or published row was
modified; no grid was re-run; no hypothesis was added; `run_*.py` was not touched.

## What was actually verified

- `python -m pytest -q -W error` → **1115 passed, 1 skipped** (baseline before: 1102
  passed, 1 skipped).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → deviations only on pre-existing
  lines of `tests/test_runner_causality_inventory.py` that this session did not touch.
- `src/qtr` coverage **100%**.
- **Injected negative control**: re-injecting the pre-fix formula into the engine fails 4
  of the 13 new tests; the file is restored afterwards.
- Every number quoted in §H38 is read from the committed artifacts and their committed
  equity curves — nothing was recomputed by re-running anything.

## The finding in one paragraph

The engine's `total_return` dropped the first bar, i.e. the only bar on which the initial
entry cost is charged, so it measured `n - 1` compounding periods while
`annualized_return` divided by `n`. The consequence was not cosmetic: one published
artifact (`exp_2026-10-10T17-05-58-697503Z`) publishes **two different `total_return`
values for the same run** (1.863359741396068 in `strategy_metrics`, 1.7456586208201519 in
`validation` — 11.77 pp apart), and the metric was **blind to a 205× change in the cost
model**: the 2026-10-10 and 2026-10-14 buy-and-hold artifacts publish the *same*
`total_return` and `annualized_return` to 13 significant digits although the per-trade
cost fell from 4.11% to 0.02% of capital. The fix aligns the engine with the value the
artifacts already publish under `validation`; the pre-fix values stay as history and are
now pinned.

## What remains unresolved (disclosures, not rewrites)

- **H18's runner-local `total_return` copy** (`run_h18_overnight_intraday_experiment.py:526`,
  `:637`) still uses the pre-fix range; the H18 artifacts are frozen, so it stays.
  Bounded: 6.34 bps on the published full-period `total_return` of the selected row;
  H18's OOS `total_return` is consistent with its own OOS return series and with the
  committed equity curve; H18's nine gates do not use `total_return`.
- **The engine's Sharpe and `statistics.sharpe_ratio` use different conventions**
  (ddof=1 vs ddof=0) — the next task.
- The pre-fix `strategy_metrics` / `benchmark_metrics` values of the five affected
  artifacts are history and are now pinned by tests.

## Approaches already tried / failed (this session)

- **Quantifying the impact by re-running a grid** was not attempted (forbidden, and
  unnecessary: the committed artifacts *are* the published record).
- **The "few bps" figure in the previous handoff understated the defect**: the gap is
  11.77 pp in the pre-cost-fix artifact and 5.73 bps in the current one.
- **An audit script initially appeared to show H18's OOS block inconsistent with its
  committed equity curve**; the cause was a slicing mistake in the script (the OOS window
  is Val **+** Test). With the correct masks every published H18 OOS number reproduces
  bit-for-bit.

## Precise next task (one task)

**Make the package's two Sharpe implementations agree, and extend the H38 cross-module
agreement contract to every metric the package computes twice.**

*Evidence.* Comparing the engine's `metrics` with `validate_strategy`'s output (which the
H38 fix required) exposed the next discrepancy: the engine computes the Sharpe with the
**sample** std (pandas, ddof=1) and `qtr.validation.statistics.sharpe_ratio` with the
**population** std (numpy, ddof=0). The two differ by exactly `sqrt(n / (n - 1))` —
measured as `strategy_metrics.sharpe / validation.sharpe = 0.999801173` in all five
artifacts with engine metrics (n = 2,515) — so those artifacts also publish two different
Sharpes for one run. The record's convention is ddof=0 (the certified H10–H14 numbers come
from the runners' `sharpe_ratio` calls, and the gates are evaluated on those), so the only
admissible direction is **engine → ddof=0**: a 0.02% change to reported Sharpes, with no
certified number moving. Note that 11 runners read `result.metrics["sharpe"]`, two of them
for a "beats benchmark" comparison — both sides of that comparison come from the engine,
so a uniform convention change cannot flip it, but the cross-module comparison can and
must be pinned.

*Deliverable.* An executable contract that, for every metric the package computes twice
(Sharpe, Sortino, profit factor, max drawdown, annualized return and volatility, total
return), asserts either exact agreement between the engine and `validate_strategy`, or
pins the documented difference with its exact formula and its bounded effect on the
published artifacts; plus the decision on which Sharpe convention the package uses, applied
in the direction that changes no certified number.
