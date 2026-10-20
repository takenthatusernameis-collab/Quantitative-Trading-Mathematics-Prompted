# Next Task — H38 done: the engine's `total_return` is fixed; the metric surface is next

## State

**H35, H36, H37, the remaining-runner extension and H38 are COMPLETE.**

- The point-in-time invariant covers **every** `run_*.py` in the repository (32 files) and
  every module-level function in them is classified and pinned
  (`tests/test_runner_causality_inventory.py`).
- Every predictor of the H29-CAUSAL families is probed clean; the H37/P3 class (a predictor
  that reads its own bar's close while trading that bar's return) has **no** further
  instance.
- The engine's `metrics["total_return"]` — the last open item of the H37 handoff — is
  **fixed** (§H38 of `FINAL_REPORT.md`): it now spans every bar of the return series and
  agrees with `qtr.validation.statistics.validate_strategy`. The 13 new tests in
  `tests/test_engine_total_return_consistency.py` pin the contract, the published-artifact
  audit and the negative control.
- `DataFetcher.fetch_sp500_constituents(date=...)` raises `ValueError` for a historical
  date (the survivorship footgun is closed) and the branch is tested.

## The next task (one task)

**Make the package's two Sharpe implementations agree, and extend the H38 cross-module
agreement contract to every metric the package computes twice.**

*Evidence (measured, not assumed).* The engine computes the Sharpe with the **sample**
standard deviation (pandas `Series.std()`, ddof=1); `qtr.validation.statistics.sharpe_ratio`
computes it with the **population** standard deviation (`np.std`, ddof=0). The two differ by
exactly `sqrt(n / (n - 1))`; in the five artifacts that carry engine metrics
(`exp_2026-10-10T17-02-22-080026Z`, `…17-03-39-610858Z`, `…17-04-21-400695Z`,
`…17-05-58-697503Z`, `exp_2026-10-14T08-26-02-537359Z`) the ratio
`strategy_metrics.sharpe / validation.sharpe` is **0.999801173** in every one of them
(n = 2,515 bars) — so each of those artifacts publishes **two different Sharpes for one
run**, exactly as it published two different `total_return` values before H38.

*Which direction.* The record's convention is ddof=0: the certified H10–H14 numbers come
from the runners' `sharpe_ratio` calls and the gates are evaluated on those, so the only
admissible direction is **engine → ddof=0** (a 0.02% change to *reported* Sharpes; no
certified number, threshold, verdict or published row moves). 11 runners read
`result.metrics["sharpe"]`; two of them (`run_alternatives.py:178,277`,
`run_param_sweep.py:174,301`) use it for a "beats benchmark" comparison whose two sides
both come from the engine — a uniform convention change cannot flip it, but the
cross-module comparison (engine Sharpe vs `validate_strategy` Sharpe) can and must be
pinned.

*Deliverable.* An executable contract in the style of
`tests/test_engine_total_return_consistency.py` that, for every metric the package computes
twice — Sharpe, Sortino, profit factor, max drawdown, annualized return and volatility,
total return — asserts either exact agreement between the engine and `validate_strategy`,
or pins the *documented* difference with its exact formula and its bounded effect on the
published artifacts; plus the decision (and its justification) on the Sharpe convention,
applied in the direction that changes no certified number.

## What was actually verified (this session)

- `python -m pytest -q -W error` → **1115 passed, 1 skipped** (baseline 1102 + the 13 new
  H38 tests; the skip is the pre-existing `buy_and_hold` skip in H36's module).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → deviations only on pre-existing
  lines of `tests/test_runner_causality_inventory.py` that this session did not touch
  (ruff 0.17.1 style drift); every line this session added is format-clean.
- `src/qtr` coverage **100%**.
- **Injected negative control**: re-injecting the pre-fix `total_return` formula into the
  engine fails 4 of the 13 new tests; the file is restored afterwards.
- No published artifact, gate threshold, verdict, certified number or published row was
  modified; no grid was re-run; no hypothesis was added; `run_*.py` was not touched.

## Remaining items (disclosures, not rewrites)

- `run_h18_overnight_intraday_experiment.py:526,637` — the runner-local `total_return` copy
  still uses the pre-fix range; the H18 artifacts are frozen, so it stays. Bounded: 6.34 bps
  on the published full-period `total_return` of the selected row; H18's OOS `total_return`
  is consistent with its own OOS return series and with the committed equity curve; H18's
  nine gates do not use `total_return`.
- The pre-fix `strategy_metrics` / `benchmark_metrics` values of the five affected artifacts
  are the historical record of the runs as executed; they are now pinned by tests.

## Constraints carried forward

- No published artifact, gate threshold, verdict or certified number may be modified; no grid
  may be re-run; no new hypothesis (the H1–H30 space is exhausted; the certified families
  H10/H11/H12/H22/H25 are frozen).
- `python -m pytest -q -W error` and `ruff check src tests run_*.py` must pass from a bare
  clone (no install step); keep `src/qtr` at 100% coverage; re-run
  `tests/test_runner_causality_inventory.py` after any change in a `run_*.py` and
  `tests/test_causality_invariant.py` after any change under `src/qtr`.
