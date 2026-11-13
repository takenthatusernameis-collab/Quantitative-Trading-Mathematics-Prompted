# NEXT_TASK.md — CI workflow contract repaired; full suite green

## Current status (verified this session, 2026-11-13)
- `python -m pytest -q -W error tests/test_gates_workflow.py tests/test_performance_regression_gate.py tests/test_backtest_perf_regression_gate.py` → **11 passed**.
- Full suite: `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` → **3748 passed, 51 skipped, 0 failed** (324s); `src/qtr` coverage **100%** (1211 stmts / 422 branches / 0 miss).
- With `pip install -e . --no-deps`: full suite → **3751 passed, 48 skipped, 0 failed** (3 manifest skips become passes); `tests/test_generated_manifest_contract.py` → **11 passed**.
- `python -m ruff check src tests run_*.py scripts` → All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` → 327 files already formatted.
- `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.282s, limit 5s, 10.7MB peak, 13668 trades).

## What changed this session
- `.github/workflows/gates.yml`: added `scripts/**` to `push`/`pull_request` path triggers; lint steps now include `scripts`; `research_gates` now runs `python scripts/backtest_perf_regression_gate.py` before pytest. This makes the existing `tests/test_gates_workflow.py` contract pass (it failed 5/5 at HEAD `f86d732`).
- `HANDOFF_CURRENT_SESSION.md` updated with verified state and the concrete next task.

## One precise next task
**Close the packaging-contract CI gap.** `gates.yml` installs only `requirements.txt`, so
the installed-distribution checks in `tests/test_generated_manifest_contract.py` skip in CI.
Add `python -m pip install -e . --no-deps` to the CI job(s) after the requirements install,
then verify:
1. `pip install -e . --no-deps && python -m pytest -q -W error tests/test_generated_manifest_contract.py` → 11 passed, 0 skipped.
2. `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` → 3751 passed, 48 skipped, 0 failed; 100% coverage.
3. `python -m ruff check src tests run_*.py scripts` and `python -m ruff format --check src tests run_*.py scripts` → clean.
Optionally pin the CI install step in `tests/test_gates_workflow.py` so it cannot silently regress.

## Unresolved / blocked
- **H182 discovery (needs data/authorization):** free-data PIT family discovery is exhausted at H181 (Cycle 96, `NEW_FAMILY_RESEARCH_REGISTER.md`, `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6). Carry/insider/earnings/options/breakeven candidates are data-blocked; the remaining candidates are adjacency- or power-blocked. Do not invent/execute H182 from exhausted/adjacent families or blocked data.
- **Artifact restoration apply (needs explicit human authorization):** `--apply` is a no-op on this checkout; `--dry-run` → Recoverable 0 / Excluded 172 / Unrecoverable 25. Baseline in `tests/test_reproducibility_audit.py`: `missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=140`.
- **All generated inventories are pinned.** Running experiments that change `.experiments/experiments.jsonl` will fail pinned inventory tests until regenerated deliberately and pins updated.

## Failed approaches / do not repeat
- Do not trust committed handoff/task docs as current defect or "next task" truth without re-running the producing/contract checks. This session's baseline had `tests/test_gates_workflow.py` failing 5/5 even though the prior handoff claimed a committed workflow fix; that fix was not present at HEAD `f86d732`.
- Do not run `scripts/plan_artifact_restoration.py --apply` (no-op; needs authorization).
- Do not invent/execute H182 from exhausted/adjacent families or blocked data.
- Do not time a performance gate with `tracemalloc` active.
- Do not mass-edit frozen contracts/tests to force green.
- Do not commit/push unless requested.

## Constraints
- `src/qtr` unchanged unless an evidenced defect requires it (then rerun the full pinned gates). No frozen/certified/published artifact, verdict, threshold, or gate weakening. No commit/push unless requested. Free/public data only.
- Working tree currently has three modified files: `.github/workflows/gates.yml`, `HANDOFF_CURRENT_SESSION.md`, and `NEXT_TASK.md`; none are committed.