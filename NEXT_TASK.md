# NEXT_TASK.md — Cycle 99: H52 frozen-record pin complete (100/103 logged); 3 contested logs held-open

## Status
Cycle 98 re-verified the baseline and repaired `tests/test_trade_log_cost_reconciliation.py`'s 14 stale-engine-API crashes. The H52 pinning task (extend `TRADE_LOG_RECORD` + `ATTRIBUTION_CHANGES_A_NUMBER` / `ATTRIBUTION_COINCIDES` / `NO_TRADES`) is **complete**: all 18 unambiguous unpinned logs are already pinned (15 aggregate factor 1.0 → `ATTRIBUTION_COINCIDES`; 2 empty → `NO_TRADES`; 1 aggregate factor 2.0 `exp_2026-11-05T12-24-33-350043Z/best_trades.parquet` → `ATTRIBUTION_CHANGES_A_NUMBER`). `git ls-files` shows 103 committed trade logs; 100 are in `TRADE_LOG_RECORD`; the only 3 unpinned are the contested per-trade `exp_2026-11-05` best_trades logs (`T01-17-49-208916Z`, `T01-24-02-934356Z`, `T18-09-06-924039Z`). Full suite 3393 passed / 39 failed / 16 skipped, all 39 pre-existing.

## Verified this session
- `python -m ruff check tests/test_trade_log_cost_reconciliation.py` — All checks passed.
- `python -m ruff format --check tests/test_trade_log_cost_reconciliation.py` — already formatted.
- `PYTHONPATH=src pytest -q tests/test_trade_log_cost_reconciliation.py` — **35 passed, 2 failed**; both failures are the 3 held-open contested per-trade logs:
  - `test_the_committed_trade_logs_are_exactly_the_pinned_record` (3 committed logs not in the record)
  - `test_every_committed_trade_log_records_the_aggregate_attribution` (3 per-trade logs)

## Next task (BLOCKED on explicit authorization)
Resolve the 3 held-open contested per-trade logs in `tests/test_trade_log_cost_reconciliation.py`. They carry per-trade attribution, so no existing classification set fits them, and adding them to the record breaks `test_the_three_pinned_sets_partition_the_record` (no per-trade class exists). Resolving them amends the frozen-record disclosure and requires **explicit authorization**. Without authorization, leave them held-open; do not force the partition or the all-aggregate assertion.

## Deferred (do not select without authorization)
The other 23 pre-existing failures: 11 NF spread-gate `KeyError: 'alpha_p_value'` tests; frozen-number drift in `test_h51`/`test_h53`/`test_h55`/`test_h57`, `test_gate_vacuity_contract`, `test_engine_total_return_consistency`. These involve frozen published numbers/gates and require evidence-based per-contract review — do not mass-edit to force the suite green.

H182 remains unassigned; NF discovery queue exhausted per Cycle 96.
