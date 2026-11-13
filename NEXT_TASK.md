# NEXT_TASK.md — gates.yml fix committed locally; requires maintainer push to origin/main

## Current status (this session, 2026-11-13)

**HEAD = `818abe2`, working tree clean:**
- `M .github/workflows/gates.yml` — contract fix applied and **committed locally** (matches `2f88722` verbatim).
- `.github/scripts/kilo-controller.sh` — controller restore already reconciles `.github/workflows` to latest `origin/main` (fetch-first, fall back to `WORKFLOW_BASE_SHA`). This file is NOT under `.github/workflows`, so it is not reverted by the controller.

**Verification (all in this session's worktree):**
- `tests/test_gates_workflow.py` → **7/7 passed** (was 7/7 failed at previous HEAD).
- `python -m ruff check src tests run_*.py scripts` → **All checks passed** (327 files).
- `python -m ruff format --check src tests run_*.py scripts` → **327 files already formatted**.
- `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.302s / 5s limit, 10.7MB, 13668 trades).
- `bash -n .github/scripts/kilo-controller.sh` → OK; shellcheck reports only pre-existing warnings.

## Exact fix applied to `.github/workflows/gates.yml` (verbatim matches commit `2f88722`)
- `push`/`pull_request` paths: added `'scripts/**'`.
- `lint` job: added `python -m pip install -e . --no-deps` step; ruff check/format now target `src tests run_*.py scripts`.
- `research_gates` job: added editable-install step and `python scripts/backtest_perf_regression_gate.py` step before "Run gates".

## What remains unresolved
- **Durability:** the `gates.yml` fix is **committed locally at `818abe2`** but **cannot be pushed** because the GitHub App token lacks `workflows` permission. A maintainer must push `818abe2` (or an equivalent commit) to `origin/main`. Until then, a fresh activation whose `WORKFLOW_BASE_SHA` is stale would still revert any in-session `gates.yml` edit — the controller fix stops reversion *to a stale snapshot*, but it reconciles to `origin/main`, which still carries the broken `gates.yml` until the fix lands on `main`.
- **H182:** authorization-gated (H1–H181 exhausted/rejected per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6 / `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96). Do not invent/pre-register/execute without explicit human authorization + an authorized free/PIT source for a materially new mechanism.
- **Artifact restoration apply:** authorization-gated (dry-run no-op: Recoverable 0 / Excluded 172 / Unrecoverable 25).

## One precise next task (for the next agent — do NOT repeat the failed approach)
**Push the local commit `818abe2` to `origin/main`** (requires maintainer credentials with `workflows` permission, or a PAT with `workflow` scope). After that:
1. Confirm `git show origin/main:.github/workflows/gates.yml` contains the fix (scripts/** paths, editable install, perf gate, scripts in ruff targets).
2. On a fresh checkout at `origin/main`: `tests/test_gates_workflow.py` → 7/7 and full baseline green (3753 passed, 100% coverage, ruff clean, perf gate passed).
3. The controller fix (already applied) then prevents future activations from reverting `gates.yml` to a stale snapshot, because restores reconcile to `origin/main` (fixed) rather than the stale `WORKFLOW_BASE_SHA`.

Do NOT re-apply only the `gates.yml` edit and expect persistence without the controller fix or without landing on `main`. Do NOT weaken the "maintainer-managed workflows" policy or delete/weaken the contract test. Do NOT run `scripts/plan_artifact_restoration.py --apply`; do not modify frozen artifacts/verdicts/thresholds. `src/qtr` must remain unchanged.

## Constraints
- `src/qtr` unchanged (no evidenced code defect; baseline green at 100% coverage).
- No frozen/certified/published artifact, verdict, threshold, or gate weakened.
- Local commit `818abe2` ready; push to `origin/main` required for durability (the controller fix protects it afterward).