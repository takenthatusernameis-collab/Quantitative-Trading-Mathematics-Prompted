# NEXT_TASK.md — CI workflow contract satisfied; full suite green

## Current status (re-verified this session, 2026-11-13T03:29Z)
- `python -m pytest -q -W error tests/test_gates_workflow.py tests/test_backtest_perf_regression_gate.py` → **10 passed**.
- `python -m ruff check src tests run_*.py scripts` → All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` → 327 files already formatted.
- `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.875s, limit 5s, 10.7MB peak, 13668 trades).
- Prior session baseline (re-stated, not fully rerun this session): `python -m pytest -q -W error` → **3748 passed, 51 skipped, 0 failed**; `--cov=qtr --cov-branch` → **100% coverage** (1211 stmts / 422 branches / 0 miss). This session changed only `.github/workflows/gates.yml` (no `src/qtr`, no tests, no scripts logic).

## What changed this session
- `.github/workflows/gates.yml` updated to satisfy the existing contract in `tests/test_gates_workflow.py` (commit `36148b2` added the test but the committed workflow was stale): `push`/`pull_request` paths now include `scripts/**`; lint steps now run `python -m ruff check src tests run_*.py scripts` and `python -m ruff format --check src tests run_*.py scripts`; `research_gates` now runs `python scripts/backtest_perf_regression_gate.py` before pytest.

## Unresolved / blocked
- **H182 discovery (needs data/authorization):** free-data PIT family discovery is exhausted at H181 (Cycle 96, `NEW_FAMILY_RESEARCH_REGISTER.md`, `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6). Carry/insider/earnings/options/breakeven candidates are data-blocked; remaining candidates adjacency- or power-blocked. Do not invent/execute H182 from exhausted/adjacent families or blocked data.
- **Artifact restoration apply (needs explicit human authorization):** `--apply` is a no-op on this checkout; `--dry-run` → Recoverable 0 / Excluded 172 / Unrecoverable 25. Baseline in `tests/test_reproducibility_audit.py`: `missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=140`.
- **All generated inventories are pinned.** Running experiments that change `.experiments/experiments.jsonl` will fail pinned inventory tests until regenerated deliberately and pins updated.

## One precise next task
**None bounded and safe remaining in-repo without authorization.** CI/CD hardening contract is satisfied and verified. The only research task is H182, which is data-blocked and requires explicit human authorization/data resolution per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6. If authorization is granted, pre-register a materially new mechanism with an authorized free/PIT data source, rank it per §4, and only then assign/execute H182 as the smallest decisive test.

## Failed approaches / do not repeat
- Do not trust committed handoff/task docs as current defect or "next task" truth without re-running the producing/contract checks (this session: docs claimed workflow stale/missing but the committed workflow was the stale artifact; `tests/test_gates_workflow.py` failed 5/5 at HEAD and now passes after workflow fix).
- Do not run `scripts/plan_artifact_restoration.py --apply` (no-op; needs authorization).
- Do not invent/execute H182 from exhausted/adjacent families or blocked data.
- Do not time a performance gate with `tracemalloc` active.
- Do not commit/push unless requested.

## Constraints
- `src/qtr` unchanged unless evidenced defect (then rerun pinned full gates). No frozen/certified/published artifact, verdict, threshold, or gate weakening. No commit/push unless requested. Free/public data only.