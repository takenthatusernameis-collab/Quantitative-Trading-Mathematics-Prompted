# NEXT_TASK.md — post H90

## State
- H90/NF-20261105-08 (FOMC announcement event drift) EXECUTED and REJECTED (1/9). `exp_2026-11-05T13-22-09-693533Z`, `run_nf_20261105_08_fomc_event_drift.py`, `tests/test_nf_20261105_08_fomc_event_drift.py`. OOS Sharpe -0.633, PF 0.582, trades 110. src/qtr unchanged.
- H1–H90 lineage recorded (see register/spec). No maintenance blocker found.

## Next task (NEW-FAMILY DISCOVERY MODE)
1. Reconcile latest inventory and confirm NF-04/NF-05 remain infeasible for current free/point-in-time pipeline; do not re-run H90 variants.
2. Per STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4: propose >=3 repository-new mechanism candidates spanning >=3 categories, assign NF-20261105-09+ temp IDs, score/rank with explicit evidence, and select smallest decisive test.
3. Pre-register selected candidate as next unused H-ID only when decision-ready (data, timing, costs, gates, rejection). Implement runner+focused tests; run lint/focused tests; execute only if decision-ready and within compute budget.
