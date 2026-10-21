# HANDOFF_NEXT — H49: the published validation blocks re-derive from the frozen artifacts

## What changed (this session)

- `tests/test_h49_validation_block_disclosure.py` — **new**, 11 tests: re-derives each published
  `validation` block from its own frozen `equity_curve.parquet` and asserts the published values,
  so the drift cannot change silently.
- `FINAL_REPORT.md` — new **§H49** section (rewritten from the H48-era draft) and an updated
  "Next task" section.
- `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`, `HANDOFF_NEXT.md`,
  `NEXT_TASK.md` updated.

## The corrected finding

The H48-era handoff claimed the last two artifacts "do not re-derive" and that the two buy-and-hold
blocks were written by *different* code versions on the *same* series. **Both claims were based on
the wrong return convention.** The engine charges costs per bar and compounds them into the equity
curve (`equity = (1 + net_returns).cumprod() * initial_capital`), so the equity curve carries the
full series including the opening bar; `equity.pct_change()` alone drops that bar. Including the
first bar's return — `equity[0] / initial_capital - 1`, the cost of the very first position change
charged on the opening bar — reproduces the published block for **all five** artifacts to float
noise (< 1e-9).

| artifact | sharpe | profit_factor | max_drawdown | total_return | walkforward_stability |
|---|---|---|---|---|---|
| `…17-02-22-080026Z` | matches (4e-16) | matches | matches | matches | matches (4e-16) |
| `…17-03-39-610858Z` | matches (2e-15) | matches | matches | matches | matches (2e-16) |
| `…17-04-21-400695Z` | matches (9e-16) | matches | matches | matches | matches (4e-15) |
| `…17-05-58-697503Z` | matches (8e-16) | matches | matches | matches | matches (5e-15) |
| `…08-26-02-537359Z` | matches (3e-15) | matches | matches | matches | matches (4e-15) |

(published vs re-derived; "matches" = |diff| < 1e-9)

## The `walkforward_stability` basis

Every published `walkforward_stability` is exactly `sharpe(second half) / sharpe(first half)`,
taken **unconditionally** — the pre-guard formula. The published `walkforward_folds` also
re-derive from the frozen equity curve under the same convention.

* Three ma_crossover artifacts: **both halves losing** (`−1.5594 / −0.8479 = 1.8391876…`), so the
  sign-unaware ratio **passed** the `0.7` gate on a strategy that lost money in both halves. The
  current sign-aware code reports `0.0` and would report `walkforward_pass: False`.
* Two buy-and-hold artifacts: **both halves profitable**, so the published value and the current
  sign-aware code agree (`1.0277108` and `0.9334875`).

All five published blocks report `walkforward_pass: True` and `all_pass: false`; the current code
would report `walkforward_pass: False` for the three ma_crossover artifacts. **No verdict moves.**

## Why the two buy-and-hold blocks differ from each other

`exp_2026-10-10T17-05-58-697503Z` and `exp_2026-10-14T08-26-02-537359Z` run the **same** SPY
buy-and-hold series (price series byte-identical, equity curves proportional), but their published
blocks differ because they charged **different costs**, baked into their own frozen equity curves:
`…17-05-58` charged the real cost model (`avg_trade_cost = 0.041105949376283715`) while
`…08-26-02` charged a fixed `0.0002` per trade (`avg_trade_cost = 0.00020009711746988646`).
Each block re-derives exactly from **its own** frozen equity curve; they do not re-derive from each
other's. Disclosed, not reconciled.

## What was actually verified

- `python -m pytest -q -W error tests/test_h49_validation_block_disclosure.py` → **11 passed**.
- `python -m pytest -q -W error` → **1366 passed, 1 skipped** (full suite, up from 1355).
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` → `src/qtr` =
  **1054 statements, 320 branches, 0 missed, 0 partial, 100.00%**; the committed gate reports
  *"Required test coverage of 100.0% reached. Total coverage: 100.00%"*.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **92 files already formatted**.
- The re-derivation is read-only against the frozen artifacts (no pipeline re-execution, no
  network, no grid re-run).
- The published blocks carry **no `param_stability` key** (they pre-date that gate); pinned.
- The published `all_pass` is `false` for all five and stays `false`.

## The published record is unaffected

No published artifact, gate threshold, verdict or certified number was modified; no grid was
re-run; no hypothesis was added. The artifacts are frozen; the published `walkforward_pass` and the
absent `param_stability` key are *history*.

## What a next session inherits

- **No further task is assigned.** The pre-registered free-data hypothesis space (H1–H30) remains
  exhausted; the certified families are frozen.
- The H47 cost-attribution disclosure and the stale `src/qtr.egg-info/` manifest are unchanged;
  **untrack** the manifest (`.gitignore` + `git rm --cached`), do not regenerate it — two sessions
  have now failed the regeneration route.
