# NEXT_TASK.md — Frozen-contract investigation complete; 10 failures documented, 0 code bugs

## Status

Investigated all 10 remaining frozen-contract failures. **No code bugs found** — all are frozen-number/pin drifts (new experiments committed, pinned counts not updated) or stale test-scope assertions (test logic too broad or based on wrong assumptions). No `src/qtr`, runner, gate, or threshold code changes needed.

**This session:** Verified ruff clean on 316 files; confirmed all H57 tests pass (except slow deterministic rebuild); catalogued 10 failures across 4 test modules with root causes.

## Verified this session

- `python -m ruff check src tests run_*.py` — All checks passed.
- `python -m ruff format --check src tests run_*.py` — 316 files already formatted.
- `test_h51_benchmark_container_invariance.py` — 1 failure (21 new IR-publishing experiments not in pinned disclosure).
- `test_h53_published_metrics_disclosure.py` — 4 failures (pinned counts drifted 54→58/630→674; test recipe error for H92 runner `bench_p_published_default=True` forces re-derived p-value to 1.0 but published is 0.0058; runner correctly uses `alpha_p_value`).
- `test_h55_nested_metrics_disclosure.py` — 4 failures (pinned counts drifted: ablations 44→48, perturbation 24→28, leaves 1188→1292, re-derived 627→631, perturbation gates 36→40).
- `test_gate_vacuity_contract.py` — All 11 passed.
- `test_engine_total_return_consistency.py` — 1 failure (stale assertion: test flags 33 NF runners that compute local `total_return` for disclosure, not engine metric access).
- `test_h57_total_return_audit.py` — All passing test classes verified (60 tests); full re-derivation test passes but takes ~90s.

## Next task (BLOCKED on explicit authorization)

Per-contract review of frozen-contract drifts — each requires authorization before any edit:
1. `test_h51_benchmark_container_invariance.py` — update `PUBLISHED_INFORMATION_RATIOS` with 21 new experiment IDs
2. `test_h53_published_metrics_disclosure.py` — fix test recipe (remove incorrect `bench_p_published_default=True` for NF runners that correctly use `alpha_p_value`), update pinned counts
3. `test_h55_nested_metrics_disclosure.py` — update all pinned counts
4. `test_engine_total_return_consistency.py` — narrow `test_no_runner_selects_on_the_engines_total_return` to only flag `metrics["total_return"]` access

Do not mass-edit to force the suite green.

## Deferred (do not select without authorization)

- Resolve 3 contested per-trade logs in `test_trade_log_cost_reconciliation.py` — requires explicit authorization (breaks partition test).
- Select H182 — blocked on commodity-carry data gap (no free PIT term-structure/roll proxy) or conclusion free-data discovery exhausted per Cycle 96.

H182 remains unassigned; NF discovery queue exhausted per Cycle 96.