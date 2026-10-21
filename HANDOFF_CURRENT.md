# HANDOFF_CURRENT — session complete (H49)

## State

- **H49 is COMPLETE** as recorded in `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_NEXT.md` and
  `HANDOFF_CURRENT_SESSION.md`: the published `validation` blocks in all five exploratory
  summaries re-derive from their own frozen `equity_curve.parquet` under the engine's full return
  convention (including the opening bar), and the `walkforward_stability` basis — the sign-unaware
  `sharpe(2nd half) / sharpe(1st half)` — is disclosed and pinned by
  `tests/test_h49_validation_block_disclosure.py` (11 tests). The two buy-and-hold blocks differ
  from each other because they charged different costs baked into their own frozen equity curves.
- **H35–H48 are COMPLETE**: every gate defect class that has surfaced is closed by an executable
  invariant, the point-in-time invariant covers every `run_*.py`, the engine's `total_return` spans
  every bar, the package's two Sharpe implementations agree, the lint/format gate is reproducible,
  the coverage gate is measured, declared and complete, both the package's public API and the
  runners' import surface are declared and pinned, the engine's trade log reconciles with the
  costs it charges, the package's stochastic surface is seedable, and the published validation
  blocks re-derive from the frozen artifacts.
- No published artifact, gate threshold, verdict or certified number was modified; no grid was
  re-run; no hypothesis was added.

## What changed (this session — H49)

- `tests/test_h49_validation_block_disclosure.py` — **new**, 11 tests: re-derives each published
  `validation` block from its own frozen `equity_curve.parquet` and asserts the published values,
  including the pre-guard `walkforward_stability` ratio, the `walkforward_folds`, the absence of
  the `param_stability` key, the fact that the two buy-and-hold blocks differ by cost model, and
  that `all_pass` stays `false`.
- `FINAL_REPORT.md` — new **§H49** section (rewritten from the H48-era draft) and an updated
  "Next task" section.
- `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`, `HANDOFF_NEXT.md`,
  `NEXT_TASK.md` updated.

## The corrected finding

The H48-era handoff claimed the last two artifacts "do not re-derive" and that the two buy-and-hold
blocks were written by *different* code versions on the *same* series. **Both claims were based on
the wrong return convention.** The engine charges costs per bar and compounds them into the equity
curve, so the equity curve carries the full series including the opening bar; `equity.pct_change()`
alone drops that bar. Including the first bar's return — `equity[0] / initial_capital - 1` —
reproduces the published block for **all five** artifacts to float noise (< 1e-9).

The published `walkforward_stability` is exactly `sharpe(second half) / sharpe(first half)`,
taken **unconditionally** (the pre-guard formula). In three ma_crossover artifacts both halves are
losing, so the sign-unaware ratio **passed** the `0.7` gate on a strategy that lost money in both
halves; the current sign-aware code reports `0.0`. In the two buy-and-hold artifacts both halves
are profitable, so the published value and the current code agree. All five published blocks report
`walkforward_pass: True` and `all_pass: false`; the current code would report
`walkforward_pass: False` for the three ma_crossover artifacts. **No verdict moves.**

The two buy-and-hold blocks differ because they charged **different costs** baked into their own
frozen equity curves (real cost model, `avg_trade_cost = 0.041106`, vs a fixed `0.0002` per trade),
on the **same** SPY price series. Each block re-derives exactly from **its own** frozen equity
curve; they do not re-derive from each other's. Disclosed, not reconciled.

## What was actually verified

- `python -m pytest -q -W error tests/test_h49_validation_block_disclosure.py` → **11 passed**.
- `python -m pytest -q -W error` → **1366 passed, 1 skipped** (full suite).
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` → `src/qtr` =
  **1054 statements, 320 branches, 0 missed, 0 partial, 100.00%**.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **92 files already formatted**.
- The re-derivation is read-only against the frozen artifacts.

## What remains unresolved

- The **certified** families are out of scope: they carry no `validation` block, and no gate,
  threshold, verdict or certified number may move.
- The H47 cost-attribution disclosure and the stale `src/qtr.egg-info/` manifest are unchanged.
