# NEXT_TASK.md — gates.yml contract fixed in working tree, uncommitted; needs persistence + full re-verify

## Current status (verified this session, 2026-11-13)
- HEAD: `b6538cc` (docs-only); committed `.github/workflows/gates.yml` at HEAD fails `tests/test_gates_workflow.py` **7/7** (missing `scripts/**` triggers, scripts in ruff targets, editable installs, perf regression gate step).
- Working tree: `.github/workflows/gates.yml` fixed to satisfy contract (uncommitted). `HANDOFF_CURRENT_SESSION.md` updated.
- Verified now: `python -m pytest -q -W error tests/test_gates_workflow.py` → **7 passed**; `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.283s, 5s limit, 10.7MB, 13668 trades); `python -m ruff check src tests run_*.py scripts` and `ruff format --check ...` → clean/327 files formatted.
- `git diff -- .github/workflows/gates.yml` non-empty → fix **not durable/persisted**.

## One precise next task
**If explicitly authorized, commit the workflow fix and verify persistence; then re-run full baseline and hold for H182 authorization.**
1. Persistence: `git show HEAD:.github/workflows/gates.yml` lacks contract elements while working tree has them. If commit/push is explicitly requested, commit `.github/workflows/gates.yml` (+ handoff docs) and verify `tests/test_gates_workflow.py` passes on committed HEAD and `git diff HEAD -- .github/workflows/gates.yml` is empty. Do not claim persisted without this evidence.
2. Baseline: `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`, ruff check/format over `src tests run_*.py scripts`, `python scripts/backtest_perf_regression_gate.py`. Report actual results.
3. H182: discovery exhausted at H181 per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6 / `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96. Do not invent/pre-register/execute without explicit human authorization and an authorized free/PIT source for a materially new mechanism (or explicit decision to close free-data discovery).

## Unresolved / blocked
- **Persistence:** fix uncommitted; prior fix commits (`3675656`,`09d4701`) did not survive later history and working-tree-only fixes were lost before.
- **H182:** authorization + data-gated.
- **Artifact restoration apply:** authorization-gated, dry-run no-op (Recoverable 0 / Excluded 172 / Unrecoverable 25).

## Failed approaches / do not repeat
- Do not trust handoff claims that fix is committed/persisted without `git show`/`git diff` and running `tests/test_gates_workflow.py` on HEAD.
- Do not leave working-tree-only fix and report durable.
- Do not invent/execute H182 from exhausted/adjacent/blocked families or data.
- Do not run artifact restoration `--apply`; do not time perf gate with `tracemalloc`; do not weaken gates or modify frozen artifacts/verdicts/thresholds.

## Constraints
- `src/qtr` unchanged unless evidenced defect requires it. No frozen/certified/published artifact, verdict, threshold, or gate weakening. No commit/push unless explicitly requested/authorized.
