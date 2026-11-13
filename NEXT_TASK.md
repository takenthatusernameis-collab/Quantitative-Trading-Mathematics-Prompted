# NEXT_TASK.md — gates.yml contract fixed and persisted at HEAD; full baseline re-verified; hold for H182

## Current status (verified this session, 2026-11-13)
- HEAD: `6c2078d`; committed `.github/workflows/gates.yml` at HEAD passes `tests/test_gates_workflow.py` **7/7**.
- Working tree: clean (`git status` clean, `git diff HEAD -- .github/workflows/gates.yml` empty).
- Verified now: `python -m pytest -q -W error tests/test_gates_workflow.py` → **7 passed**; `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.294s, 5s limit, 10.7MB, 13668 trades); `python -m ruff check src tests run_*.py scripts` and `ruff format --check ...` → clean/327 files formatted; `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` → **3753 passed, 48 skipped, 100% coverage** (1211 statements, 422 branches).
- `git show HEAD:.github/workflows/gates.yml` contains all contract elements.

## One precise next task
**Re-verify full baseline on any fresh checkout and hold for H182 authorization.**
1. On fresh checkout: `python -m pytest -q -W error tests/test_gates_workflow.py` (must pass 7/7) and `git show HEAD:.github/workflows/gates.yml` (must contain all contract elements).
2. Full baseline: `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`, ruff check/format over `src tests run_*.py scripts`, `python scripts/backtest_perf_regression_gate.py`. Record actual counts/evidence.
3. H182 remains authorization-gated: per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6 / `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96, H1–H181 exhausted/rejected. Do not invent/pre-register/execute without explicit human authorization and an authorized free/PIT source for a materially new mechanism (or explicit decision to close free-data discovery).

## Unresolved / blocked
- **H182:** authorization + data-gated.
- **Artifact restoration apply:** authorization-gated, dry-run no-op (Recoverable 0 / Excluded 172 / Unrecoverable 25).

## Failed approaches / do not repeat
- Do not trust handoff claims that fix is committed/persisted without `git show`/`git diff` and running `tests/test_gates_workflow.py` on HEAD.
- Do not leave working-tree-only fix and report durable.
- Do not invent/execute H182 from exhausted/adjacent/blocked families or data.
- Do not run artifact restoration `--apply`; do not time perf gate with `tracemalloc`; do not weaken gates or modify frozen artifacts/verdicts/thresholds.

## Constraints
- `src/qtr` unchanged unless evidenced defect requires it. No frozen/certified/published artifact, verdict, threshold, or gate weakening. No commit/push unless explicitly requested/authorized.