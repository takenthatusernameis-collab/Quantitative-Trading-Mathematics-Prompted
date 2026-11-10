# NEXT_TASK.md — H52 frozen-record pin complete (100/103 logged); 3 contested logs held-open

## Status
H52 pinning task complete: `TRADE_LOG_RECORD` covers 100 of 103 committed trade logs; three classification sets partition the 100 pinned logs exactly. The only 3 unpinned are the contested per-trade `exp_2026-11-05` best_trades logs (`T01-17-49-208916Z`, `T01-24-02-934356Z`, `T18-09-06-924039Z`). Test file: 35 passed, 2 failed (contested-only); partition test passes. Full core suite 282 passed; benchmark gates 26 passed; NF regressions 30 passed. Ruff clean on 316 files.

## Verified this session
- `python -m ruff check src tests run_*.py` — All checks passed.
- `python -m ruff format --check src tests run_*.py` — already formatted.
- `PYTHONPATH=src pytest -q tests/test_trade_log_cost_reconciliation.py` — **35 passed, 2 failed**; both failures are the 3 held-open contested per-trade logs.
- `test_the_three_pinned_sets_partition_the_record` — **passed**.

## Next task (BLOCKED on explicit authorization)
Resolve the 3 held-open contested per-trade logs in `tests/test_trade_log_cost_reconciliation.py`. They carry per-trade attribution, so no existing classification set fits them, and adding them to the record breaks `test_the_three_pinned_sets_partition_the_record` (no per-trade class exists). Resolving them amends the frozen-record disclosure and requires **explicit authorization**. Without authorization, leave them held-open; do not force the partition or the all-aggregate assertion.

## Deferred (do not select without authorization)
The other 23 pre-existing failures: 11 NF spread-gate `KeyError: 'alpha_p_value'` tests; frozen-number drift in `test_h51`/`test_h53`/`test_h55`/`test_h57`, `test_gate_vacuity_contract`, `test_engine_total_return_consistency`. These involve frozen published numbers/gates and require evidence-based per-contract review — do not mass-edit to force the suite green.

H182 remains unassigned; NF discovery queue exhausted per Cycle 96.