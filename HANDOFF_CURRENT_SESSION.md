# HANDOFF_CURRENT_SESSION — H38: the engine's `total_return` measured the wrong horizon

## What changed

1. **`src/qtr/backtest/engine.py:312-320`** — `_calculate_metrics` now measures the total
   return **from the initial capital**:
   `total_return = equity.iloc[-1] / self.config.initial_capital - 1.0`
   (was `equity.iloc[-1] / equity.iloc[0] - 1`, which dropped the first bar).
2. **`tests/test_engine_total_return_consistency.py`** (new: 13 tests) — the executable
   contract for the corrected metric:
   - the metric equals the equity curve's total return from the initial capital and the
     full return product `(1 + returns).prod() - 1`;
   - it equals `qtr.validation.statistics.validate_strategy`'s `total_return` on the same
     series (the two functions of the package can no longer disagree);
   - `annualized_return` is the `n`-period annualization of an `n`-period total return
     (the pair is invertible);
   - **negative controls**: the pre-fix range is *detected* (the test fails if the engine
     reports it), and a zero-first-bar signal is *not* flagged (the invariant is not
     over-strict);
   - **published-artifact audit**: the pre-fix convention, the corrected convention and the
     gap between them are pinned against the five committed artifacts;
   - **the blind-spot pin**: the 2026-10-10 and 2026-10-14 buy-and-hold artifacts publish
     the *same* `total_return`/`annualized_return` across a 205× change in the per-trade
     cost, while the corrected metric separates them by 11.77 pp;
   - **the selection guard**: no runner reads `metrics["total_return"]`, so no selection,
     row or verdict can move.
3. **`FINAL_REPORT.md`** — new §H38 (the defect, the evidence tables, the fix, the bounded
   impact, the remaining disclosure) and a rewritten `## Next Task` section; the
   `Summary statistics` test count is re-baselined (959 → 1115).
4. **`NEXT_TASK.md`**, **`HANDOFF_NEXT.md`**, this file.

No published artifact, gate threshold, verdict, certified number or published row was
touched. No grid was re-run. No hypothesis was added. `run_*.py` was not touched at all.

## What was actually verified

- Baseline before this session: `python -m pytest -q -W error` → **1102 passed, 1 skipped**.
- After: `python -m pytest -q -W error` → **1115 passed, 1 skipped** in 203 s (1102 + the 13
  new tests; the skip is the pre-existing `buy_and_hold` skip inside H36's module).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → the only deviations are on
  pre-existing lines of `tests/test_runner_causality_inventory.py` that this session did
  not touch (ruff 0.17.1 style drift); every line this session added is format-clean.
- `src/qtr` coverage **100%** (the change is one expression; no new branch).
- **Injected negative control**: re-injecting the pre-fix formula into the engine makes
  **4 of the 13 new tests fail**; the file is restored afterwards and `git diff` shows only
  the intended change.
- Every number in §H38 is read out of the **committed artifacts** (summary.json +
  equity parquet); nothing was recomputed by re-running a grid.

## The finding

- **F1 — the metric measured the wrong quantity.** The equity curve is
  `cumprod(1 + net_returns) * initial_capital`, so `equity.iloc[0]` is already one bar
  into the sample, and the first bar is the only bar that carries the *initial entry cost*
  (`position_changes = signals.diff().fillna(signals.iloc[0])`). The pre-fix range covered
  `n - 1` compounding periods while `annualized_return` divided by `n_periods = len(returns)`:
  the two metrics of one equity curve described two different horizons.
- **F2 — the same artifact published two different values for one run.**
  `exp_2026-10-10T17-05-58-697503Z` publishes `strategy_metrics.total_return =
  1.863359741396068` (the engine) **and** `validation.total_return = 1.7456586208201519`
  (`validate_strategy`) — 11.77 pp apart, the difference being the first bar's 4.11%
  entry cost. The `benchmark_metrics` block of the MA-crossover artifacts carries the same
  error (4.47 pp) with no `validation` counterpart to expose it.
- **F3 — the metric was blind to the dominant term of the cost model.** The buy-and-hold
  run was re-executed on 2026-10-14 after the cost-model fix cut the per-trade cost from
  4.11% to 0.02% of capital; both artifacts publish `total_return = 1.86335974139…` and
  `annualized_return = 0.11116466309…` — **identical to 13 significant digits** — because
  the whole cost difference lands on the first bar. The corrected metric separates them:
  1.7457 vs 1.8628 (11.77 pp).
- **The fix is bounded by the published record**: the corrected value is *already* in every
  affected artifact under its `validation` block, so the engine now agrees with the
  published record rather than contradicting it. The pre-fix `strategy_metrics` /
  `benchmark_metrics` values stay as the historical record of the runs as executed, and are
  now pinned by tests.

## What remains unresolved (disclosures, not rewrites)

- **H18's runner-local `total_return` copy** (`run_h18_overnight_intraday_experiment.py:526`
  and `:637`) still uses the pre-fix range. The H18 artifacts are frozen, so the copy stays.
  Bounded: the published full-period `total_return` of the selected row is **6.34 bps**
  above the from-capital value (2.169671442460739 vs 2.169037508172247); H18's *OOS*
  `total_return` is unaffected (it matches its own OOS return series and the committed
  equity curve bit-for-bit: OOS Sharpe 0.4424368131799029, max DD −0.22230414028780243,
  PF 1.0890543891778597); and H18's nine gates do not use `total_return`.
- **The engine's Sharpe and `statistics.sharpe_ratio` still use different conventions**
  (sample std, ddof=1, vs population std, ddof=0). This session found it while verifying
  the H38 fix; it is the next task (see below), not a rewrite.
- The pre-fix `strategy_metrics` / `benchmark_metrics` values of the five affected
  artifacts are history and are now pinned.

## Approaches already tried / failed (and why)

- **Re-running a grid to quantify the impact was not attempted and is forbidden.** Every
  number in §H38 is read from the committed artifacts and their committed equity curves,
  which is both cheaper and stronger (the artifacts *are* the published record).
- **Reading the impact off the "few bps" wording in the old handoff was wrong**: the
  within-artifact gap is 11.77 pp for the 2026-10-10 buy-and-hold artifact, because that
  artifact was produced *before* the cost-model fix (4.11% entry cost). The handoff's
  "~a few bps" described the current cost model only.
- **The first attempt to compare H18's OOS block against its committed equity curve
  appeared to fail** (Sharpe 0.193 vs the published 0.442). The cause was an indexing
  mistake in the *audit script* (the OOS window is Val **+** Test, i.e. `index > train_end`,
  not `index > val_end`). With the correct masks every published OOS number reproduces
  bit-for-bit from the committed equity curve; the H18 artifact is consistent.

## Precise next task (one task), with evidence and constraints

**Make the package's two Sharpe implementations agree, and extend the H38 cross-module
agreement contract to every metric that the package computes twice.**

*Evidence.* H38 had to compare the engine's `metrics` with `validate_strategy`'s output to
prove the `total_return` fix; that comparison exposed the next discrepancy: the engine
computes the Sharpe with the **sample** standard deviation (pandas `Series.std()`, ddof=1)
while `qtr.validation.statistics.sharpe_ratio` uses the **population** standard deviation
(`np.std`, ddof=0). The two differ by exactly `sqrt(n / (n - 1))` — measured as
`strategy_metrics.sharpe / validation.sharpe = 0.999801173` in **all five** artifacts with
engine metrics (n = 2,515 bars) — so every one of those artifacts also publishes two
different Sharpes for one run. The engine's Sharpe is *not* the record's convention: the
certified H10–H14 numbers come from the runners' `sharpe_ratio` calls (ddof=0), and the
gates are evaluated on those, so the only admissible direction is the **engine → ddof=0**
(a 0.02% change to reported Sharpes; no certified number moves). Note that 11 runners read
`result.metrics["sharpe"]`, two of them (`run_alternatives.py`, `run_param_sweep.py`) for a
"beats benchmark" comparison — both sides of that comparison come from the engine, so a
uniform convention change cannot flip it, but the *cross-module* comparison (engine Sharpe
vs `validate_strategy` Sharpe) can and must be pinned.

*Deliverable.* An executable contract (in the style of
`tests/test_engine_total_return_consistency.py`) that, for every metric the package
computes twice — Sharpe, Sortino, profit factor, max drawdown, annualized return and
volatility, total return — asserts either exact agreement between the engine and
`validate_strategy`, or pins the *documented* difference with its exact formula and its
bounded effect on the published artifacts; plus the decision (and its justification) on
which Sharpe convention the package uses, applied in the direction that changes no
certified number.

*Also open.* H18's runner-local `total_return` copy (disclosure only — the artifact is
frozen) and the stale pre-fix `strategy_metrics` / `benchmark_metrics` values of the five
affected artifacts (history, pinned).

*Constraints.* Do not re-run any grid; do not modify a published artifact, gate threshold,
verdict or certified number; do not add a hypothesis; keep `src/qtr` at 100% coverage;
`python -m pytest -q -W error` and `ruff check` / `ruff format --check` must pass from a
bare clone (no install step); re-run `tests/test_causality_invariant.py` after any change
under `src/qtr` and `tests/test_runner_causality_inventory.py` after any change in a
`run_*.py`.
