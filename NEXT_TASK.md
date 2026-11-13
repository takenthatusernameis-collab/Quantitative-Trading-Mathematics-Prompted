# NEXT_TASK.md — CI packaging/manifest contract wired; suite green

## Current status (verified this session, 2026-11-13)
- `python -m pytest -q -W error tests/test_gates_workflow.py tests/test_generated_manifest_contract.py` → **18 passed** (0 skipped).
- `python -m pytest -q -W error tests/test_performance_regression_gate.py tests/test_backtest_perf_regression_gate.py` → **6 passed**.
- Full suite: `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` → **3751 passed, 48 skipped, 0 failed**; `src/qtr` coverage **100%** (1211 stmts / 422 branches / 0 miss).
- `python -m ruff check src tests run_*.py scripts` → All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` → 327 files already formatted.
- `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.288s, limit 5s, 10.7MB peak, 13668 trades).

## What changed this session
- `.github/workflows/gates.yml`: added `scripts/**` to push/pull_request path triggers; lint now runs ruff on `scripts`; both `lint` and `research_gates` run `python -m pip install -e . --no-deps` after deps install; `research_gates` runs `python scripts/backtest_perf_regression_gate.py` before pytest.
- `tests/test_gates_workflow.py`: added parametrized `test_jobs_install_the_package_editably` for `lint` and `research_gates`.
- `HANDOFF_CURRENT_SESSION.md` and this file updated with verified state.

## One precise next task
**Resolve the H182 discovery blocker or formally close discovery (authorization-gated).**
Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6 and `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96,
H1–H181 are exhausted/rejected and no feasible free-data PIT family remains (carry/insider/earnings/
options/breakeven data-blocked; others adjacency/power-blocked). Next session must either:
(a) obtain explicit human authorization plus an authorized free/PIT data source for a materially
new mechanism and pre-register H182 per directive §4 (honest scoring, lineage check, smallest
decisive test) before any runner execution; or (b) with explicit authorization, document
free-data family discovery as exhausted and shift effort to auditing/infrastructure only.
Do not invent H182 or modify frozen artifacts/gates. Re-verify baseline first:
`pytest -q -W error` (expect 3751 passed, 48 skipped), ruff check/format clean, perf gate passed,
100% `src/qtr` coverage.

## Unresolved / blocked
- **H182 discovery (needs data/authorization):** exhausted at H181 (Cycle 96). No feasible free-data PIT family. Requires explicit authorization + authorized source or explicit exhaustion closure.
- **Artifact restoration apply (needs explicit human authorization):** `--apply` no-op; `--dry-run` → Recoverable 0 / Excluded 172 / Unrecoverable 25. Baseline in `tests/test_reproducibility_audit.py`: `missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=140`.
- **All generated inventories are pinned.** Running experiments that change `.experiments/experiments.jsonl` will fail pinned inventory tests until regenerated deliberately and pins updated.

## Failed approaches / do not repeat
- Do not trust committed handoff/task docs as current defect or "next task" truth without re-running the producing/contract checks (session start: workflow/manifest contract state did not match prior handoff claims).
- Do not run `scripts/plan_artifact_restoration.py --apply` (no-op; needs authorization).
- Do not invent/execute H182 from exhausted/adjacent families or blocked data.
- Do not time a performance gate with `tracemalloc` active.
- Do not mass-edit frozen contracts/tests to force green.
- Do not commit/push unless requested.

## Constraints
- `src/qtr` unchanged unless an evidenced defect requires it. No frozen/certified/published artifact, verdict, threshold, or gate weakening. No commit/push unless requested. Free/public data only.
- Working tree has uncommitted changes to `.github/workflows/gates.yml`, `tests/test_gates_workflow.py`, `HANDOFF_CURRENT_SESSION.md`, and `NEXT_TASK.md`.