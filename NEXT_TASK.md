# NEXT_TASK.md — gates.yml contract failing at HEAD; fix applied in working tree (uncommitted)

## Current status (verified this session, 2026-11-13, own evidence)
- HEAD at start: `f5d7c1f` (clean working tree). `python -m pytest -q -W error tests/test_gates_workflow.py` failed **7/7** against `.github/workflows/gates.yml` (missing `scripts/**` path triggers, missing `scripts/` in lint ruff targets, missing editable install steps, missing perf regression gate step in `research_gates`).
- `.github/workflows/gates.yml` re-applied in working tree to satisfy the pinned contract. Verified after fix:
  - `python -m pytest -q -W error tests/test_gates_workflow.py` → **7 passed**.
  - `python -m ruff check src tests run_*.py scripts` → All checks passed.
  - `python -m ruff format --check src tests run_*.py scripts` → 327 files already formatted.
  - `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.284s, limit 5s, 10.7MB peak, 13668 trades).
- `git diff -- .github/workflows/gates.yml` is **not empty** (uncommitted). No commit created this session.

## What changed this session
- `.github/workflows/gates.yml`: reconciled to `tests/test_gates_workflow.py` contract (`scripts/**` path triggers, scripts in ruff targets, `python -m pip install -e . --no-deps` in lint+research_gates, perf gate step before pytest).
- `HANDOFF_CURRENT_SESSION.md` updated. No `src/qtr`, `tests/`, frozen artifacts, gates thresholds, or published numbers changed.

## One precise next task
**Persist the gates.yml fix (commit if explicitly authorized) and reverify full baseline, then hold for H182 authorization.**
- `git show --name-only HEAD` / `git log --oneline -3` confirm fix is **not** in HEAD; `git diff -- .github/workflows/gates.yml` shows the working-tree fix. If commits are explicitly requested/authorized, commit the workflow fix (and handoff/docs as appropriate) and verify `tests/test_gates_workflow.py` passes on committed state. If not authorized, leave a clear handoff noting the uncommitted fix — do **not** claim it persisted.
- Re-run full baseline on the resulting state: `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` (prior claimed: 3753 passed, 48 skipped, 0 failed, 100% `src/qtr`), ruff check/format over `src tests run_*.py scripts`, and `python scripts/backtest_perf_regression_gate.py`.
- H182: per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6 and `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96, H1–H181 exhausted/rejected with no feasible free-data PIT family identified. Do not invent/pre-register/execute H182 without explicit human authorization and an authorized free/PIT data source for a materially new mechanism (or explicit authorization to document discovery exhausted and shift to audit/infra).

## Unresolved / blocked
- **Persistence:** workflow fix uncommitted; prior handoffs report repeated loss/revert of similar fixes when not durably committed.
- **H182 discovery (needs authorization/data):** exhausted at H181; carry/insider/earnings/options/breakeven data-blocked, others adjacency/power-blocked.
- **Artifact restoration apply:** needs explicit human authorization (`--dry-run` → Recoverable 0 / Excluded 172 / Unrecoverable 25). All inventories pinned.

## Failed approaches / do not repeat
- Do not trust handoff/task claims that the fix is committed/persisted without checking `git diff HEAD`, `git show`, and running `tests/test_gates_workflow.py`.
- Do not leave `.github/workflows/gates.yml` fixed only in working tree and report it as durable; prior losses documented (`3434489`, `d2697d2`, reverted `3675656`→`9d00e01`).
- Do not invent/execute H182 from exhausted/adjacent families or blocked data.
- Do not run `scripts/plan_artifact_restoration.py --apply`; do not time perf gate with `tracemalloc` active.
- Do not mass-edit frozen contracts/tests, weaken gates, or modify frozen artifacts/verdicts/thresholds.

## Constraints
- `src/qtr` unchanged unless an evidenced defect requires it. No frozen/certified/published artifact, verdict, threshold, or gate weakening. Free/public data only. No commit/push unless explicitly requested/authorized.