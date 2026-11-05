# NEXT_TASK.md — post H91

## State
- H90/NF-20261105-08 (FOMC announcement event drift) EXECUTED and REJECTED (1/9). `exp_2026-11-05T13-22-09-693533Z`. OOS Sharpe -0.633, PF 0.582, trades 110. src/qtr unchanged.
- H91/NF-20261105-09 (turn-of-month equity seasonality on SPY) EXECUTED and REJECTED (3/9). `exp_2026-11-05T13-32-55-648939Z`, `run_nf_20261105_09_turn_of_month.py`, `tests/test_nf_20261105_09_turn_of_month.py`. OOS Sharpe 0.784 (<1.0), PF 1.296 (<1.3), max DD -9.4% (pass), trades 190 (<200), WF stability 1.144 (pass), worst-regime -1.73 (fail), bench p=1.0 (fail), IR -0.639 (fail), perturbation min ratio 0.941 (pass). src/qtr unchanged (two runner-internal bugs fixed during execution: turn-of-month month-end mask compared periods instead of timestamps → all-True mask; walk_forward_splits called with a Series + invalid `expanding=` kwarg → degenerate all-zero selection).
- H1–H91 lineage recorded (see register/spec). No maintenance blocker found. H85–H91 all rejected; NF-20261105-04 (commodity carry roll proxy) and NF-20261105-05 (short-term CS reversal) remain deferred with decisive risks documented.

## Next task (NEW-FAMILY DISCOVERY MODE)
1. Per STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4/§6: H85–H91 rejected; NF-04/NF-05 remain infeasible (decisive risks unresolved). Propose >=3 repository-new mechanism candidates spanning >=3 categories, assign NF-20261105-10+ temp IDs, score/rank with explicit evidence, and select smallest decisive test.
2. Pre-register selected candidate as next unused H-ID only when decision-ready (data, timing, costs, gates, rejection). Implement runner+focused tests; run lint/focused tests; execute only if decision-ready and within compute budget. Do not re-run rejected families without a materially different, pre-registered mechanism.
3. When executing a new runner, run full pinned gates: `python -m ruff check src tests run_*.py`, `python -m ruff format --check src tests run_*.py`, `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` (100% coverage enforced for src/qtr).
