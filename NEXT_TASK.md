# NEXT_TASK.md — Cycle 98 (post-audit): inventory benchmark-gate contract offenders

## Status
Cycle 97 infrastructure fixes for engine-Sharpe contract remain verified (`tests/test_engine_metric_agreement.py` 72/72). Free-data point-in-time strategy-family queue exhausted (H1–H181 rejected, H182 unassigned). `src/qtr` unchanged.

## Verified baseline (Cycle 97 audit)
- `ruff check/format --check src tests run_*.py`: clean.
- `PYTHONPATH=src pytest -q tests/test_engine_metric_agreement.py`: **72 passed**.
- `PYTHONPATH=src pytest -q tests/test_config.py tests/test_public_api_contract.py tests/test_coverage_gate_contract.py tests/test_backtest_engine.py tests/test_data_fetcher.py tests/test_cost_model.py`: **210 passed**.
- `PYTHONPATH=src pytest -q tests/test_benchmark_gate_contract.py`: **25 passed, 1 failed** — `test_no_runner_compares_a_p_value_against_max_p_value_directly` (38 NF runner offenders; pre-existing).
- Full suite: collection **3448 tests**; not completed this session after first failure in benchmark gate contract (stopped at 136 passed in that run).

## Precise next task (bounded, no behavior change)
Create `INFRASTRUCTURE_AUDIT_BENCHMARK_GATE.md` inventorying the 38 offenders reported by `test_no_runner_compares_a_p_value_against_max_p_value_directly`:

**Status: COMPLETE.** `INFRASTRUCTURE_AUDIT_BENCHMARK_GATE.md` written with the full offender table (runner path, line, NF ID, offending comparison snippet, linked `.experiments/nf_runs/*` artifact dirs), summary counts by NF family/date bucket, and artifact presence (31/38 with artifacts, 7 without). Pointers added to `HANDOFF_NEXT.md` and `HANDOFF_CURRENT_SESSION.md`.

- For each: runner path, line(s), offending comparison snippet, NF/H identifier (from filename/header/comments when available), and linked `.experiments/nf_runs/*` artifact dirs if present.
- Add short summary counts by NF family/date bucket.
- Update `HANDOFF_NEXT.md` and `HANDOFF_CURRENT_SESSION.md` pointers to this audit file.

Constraints:
- Do **not** edit `src/qtr`, runner logic, tests, gates, thresholds, or any published/frozen artifacts/results.
- No commit/push. No speculative fixes to make suite green.
- Re-run and report: `ruff check/format`, `tests/test_engine_metric_agreement.py`, focused core tests, `tests/test_benchmark_gate_contract.py` (expect same 1 failure unless environment changes).

## Blocked alternatives (do not select without authorization)
- H182 pre-registration/execution remains blocked until a data-gap blocker is resolved under explicit authorization (futures roll/contango; PIT insider/earnings-revisions/options-chain). Do not pick from blocked/deferred pool.
