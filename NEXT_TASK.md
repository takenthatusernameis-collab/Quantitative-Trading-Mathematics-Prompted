# NEXT_TASK.md — Cycle 99: absorb committed-record drift into the H52 frozen-record pin

## Status
Cycle 98 re-verified the baseline and repaired `tests/test_trade_log_cost_reconciliation.py`'s 14 stale-engine-API crashes (`VectorizedBacktester.run`/`_calculate_costs` -> module-level `run_backtest`). That file is now 35 passed / 2 failed; full suite 3393 passed / 39 failed / 16 skipped, all 39 pre-existing.

## Precise next task (bounded, no behavior change)
In `tests/test_trade_log_cost_reconciliation.py`, extend `TRADE_LOG_RECORD` and the three attribution classification sets (`ATTRIBUTION_CHANGES_A_NUMBER`, `ATTRIBUTION_COINCIDES`, `NO_TRADES`) to cover the 18 unambiguous unpinned committed logs reported by `git ls-files -z -- '.experiments/artifacts/*trades*.parquet'` (103 committed vs 82 pinned):

- 15 aggregate, repetition factor 1.0 -> `ATTRIBUTION_COINCIDES`
- 2 empty -> `NO_TRADES`
- 1 aggregate, factor 2.0: `.experiments/artifacts/exp_2026-11-05T12-24-33-350043Z/best_trades.parquet` (3374 trades, 1687 bars, 1687 multi-trade bars) -> `ATTRIBUTION_CHANGES_A_NUMBER`

For each, re-measure `(n_trades, n_bars, n_multi)` via `_load_trade_log` and classify with `_attribution`/`_repetition_factor`. Keep the partition assertions (`test_the_three_pinned_sets_partition_the_record`, etc.) intact.

Expectation: `test_the_committed_trade_logs_are_exactly_the_pinned_record` and `test_every_committed_trade_log_records_the_aggregate_attribution` still fail on the 3 contested `exp_2026-11-05` best_trades logs (factors 28.26, 28.23, 6.04) that carry per-trade attribution — no existing classification set or the all-aggregate assertion accommodates them. Adding them to the record would break `test_the_three_pinned_sets_partition_the_record`; resolving them amends the frozen-record disclosure and requires **explicit authorization**. Without authorization, pin the 18 and leave the 3 as a held-open decision.

## Constraints
- Do not touch `src/qtr`, artifact bytes, or published/frozen numbers.
- Do not change the all-aggregate assertion or the partition semantics without authorization.
- `ruff check src tests run_*.py` and `ruff format --check src tests run_*.py` must stay clean.
- Verify by running `pytest tests/test_trade_log_cost_reconciliation.py` (18 newly pinned logs; same 2 frozen-disclosure failures remain).

## Deferred (do not select without authorization)
The other 23 pre-existing failures: 11 NF spread-gate `KeyError: 'alpha_p_value'` tests; frozen-number drift in `test_h51`/`test_h53`/`test_h55`/`test_h57`, `test_gate_vacuity_contract`, `test_engine_total_return_consistency`. These involve frozen published numbers/gates and require evidence-based per-contract review — do not mass-edit to force the suite green.

H182 remains unassigned; NF discovery queue exhausted per Cycle 96.
