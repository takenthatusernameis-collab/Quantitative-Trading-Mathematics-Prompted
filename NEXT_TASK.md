# NEXT_TASK.md — H53 H92 benchmark_p_value recipe corrected; verify with deps

## Status

Corrected one **test-recipe** defect in `tests/test_h53_published_metrics_disclosure.py` (no `src/qtr`, runner, gate, threshold, or frozen-number change).

- The 3 newer H92 (`nf_20261105_10_equity_bond_relmom`) artifacts `exp_2026-11-06T02-17-43-039138Z`, `03-36-48-479398Z`, `04-23-47-511988Z` were pinned in `BENCH_P_PUBLISHED_DEFAULT_ARTIFACTS` but publish the real `benchmark_p_value = 0.005822770948177806` (post-runner-fix; runner uses `cmp.get("alpha_p_value", 1.0)`).
- Removed those 3 IDs from the set (14 IDs remain) and documented the mid-production split in the H92 recipe comment. The 6 older H92 artifacts correctly remain pinned as published-default (`1.0`).

## Verified this session

- Artifact inspection: 6 older H92 artifacts publish `1.0`; 3 newer publish `0.005822770948177806`.
- `python3 -m py_compile tests/test_h53_published_metrics_disclosure.py` — OK.
- `python3 -m compileall -q tests/test_h53_published_metrics_disclosure.py` — OK.
- Structural checks: 3 newer IDs absent from set literal; 14 ID entries present; `len == 14` assertion retained.
- **Not run:** `pytest`/`ruff` unavailable in this environment.

## Next task

In an environment with project deps, run:
- `python -m ruff check tests/test_h53_published_metrics_disclosure.py && python -m ruff format --check tests/test_h53_published_metrics_disclosure.py`
- `PYTHONPATH=src python -m pytest -q tests/test_h53_published_metrics_disclosure.py`
- frozen-contract set: `tests/test_h51_benchmark_container_invariance.py tests/test_h53_published_metrics_disclosure.py tests/test_h55_nested_metrics_disclosure.py tests/test_gate_vacuity_contract.py tests/test_engine_total_return_consistency.py tests/test_trade_log_cost_reconciliation.py`

Confirm the 3 H92 `benchmark_p_value` re-derivation mismatches are gone. If H53 still fails only on pinned-count drifts (previously 54→58 summaries, 630→674 values), record exact failures/evidence and stop for authorization before updating frozen counts.

## Deferred (do not select without authorization)

- Update pinned counts in `test_h51_benchmark_container_invariance.py`, `test_h53_published_metrics_disclosure.py`, `test_h55_nested_metrics_disclosure.py` — frozen-number/count drifts.
- Resolve 3 contested per-trade logs in `test_trade_log_cost_reconciliation.py` (`exp_2026-11-05T01-17-49-208916Z`, `01-24-02-934356Z`, `18-09-06-924039Z`) — breaks partition; authorization required.
- Select H182 — commodity-carry data gap/no feasible free-data family per Cycle 96 (discovery queue exhausted unless data gap resolved under authorization).