# NEXT_TASK.md — CI gates workflow reconciled to pinned contract; baseline green

## Current status (verified this session, 2026-11-13, own evidence)
- Session start: HEAD `3434489` had **7 failing** `tests/test_gates_workflow.py`
  assertions because the prior handoff's claimed `.github/workflows/gates.yml` edit
  was absent (only handoff docs changed in that commit).
- This session re-applied the workflow fix, then verified:
- `python -m pytest -q -W error tests/test_gates_workflow.py tests/test_generated_manifest_contract.py` → **18 passed** (was 7 failed / 11 passed).
- `python -m ruff check src tests run_*.py scripts` → All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` → 327 files already formatted.
- `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.287s, limit 5s, 10.7MB peak, 13668 trades).
- Full suite: `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` → **3753 passed, 48 skipped, 0 failed**, `src/qtr` coverage **100%** (1211 stmts / 422 branches).

## What changed this session
- `.github/workflows/gates.yml` reconciled to the committed pinned contract in
  `tests/test_gates_workflow.py`: `scripts/**` added to push/pull_request path
  triggers; lint job lints `scripts`; both `lint` and `research_gates` run
  `python -m pip install -e . --no-deps`; `research_gates` runs
  `python scripts/backtest_perf_regression_gate.py` before pytest.
- `HANDOFF_CURRENT_SESSION.md` and this file updated with verified state.
  `tests/` was NOT modified this session.

## Why this was necessary (evidence)
- The prior session added `test_jobs_install_the_package_editably` to
  `tests/test_gates_workflow.py` (commit `4f5436b`) and claimed the workflow was
  reconciled, but `.github/workflows/gates.yml` was never changed — it remained the
  original from `f86d732`. HEAD therefore had **7 failing** contract tests despite
  the handoff claiming "3753 passed, 0 failed". This session fixed the source
  (workflow), not the test.

## One precise next task
**First confirm the workflow fix persisted (do not trust this doc), then re-verify
the baseline, then hold for the authorization-gated H182/discovery decision.**
Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6 and `NEW_FAMILY_RESEARCH_REGISTER.md`
Cycle 96, H1–H181 are exhausted/rejected and no feasible free-data PIT family remains
(carry/insider/earnings/options/breakeven data-blocked; others adjacency/power-blocked).
Next session must either: (a) obtain explicit human authorization plus an authorized
free/PIT data source for a materially new mechanism and pre-register H182 per directive
§4 (honest scoring, lineage check, smallest decisive test) before any runner execution;
or (b) with explicit authorization, document free-data family discovery as exhausted
and shift effort to auditing/infrastructure only. Do not invent H182 or modify frozen
artifacts/gates. Re-verify baseline first:
- `git status --short` + `git diff .github/workflows/gates.yml`: if the five fixes are
  absent at HEAD, re-apply them (this exact regression already happened once at
  `3434489`) and re-run `tests/test_gates_workflow.py`.
- `pytest -q -W error` (expect 3753 passed, 48 skipped), ruff check/format clean over
  `src tests run_*.py scripts`, perf gate passed, 100% `src/qtr` coverage.

## Unresolved / blocked
- **H182 discovery (needs data/authorization):** exhausted at H181 (Cycle 96). No feasible free-data PIT family. Requires explicit authorization + authorized source or explicit exhaustion closure.
- **Artifact restoration apply (needs explicit human authorization):** `--apply` no-op; `--dry-run` → Recoverable 0 / Excluded 172 / Unrecoverable 25. Baseline in `tests/test_reproducibility_audit.py`: `missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=140`.
- **All generated inventories are pinned.** Running experiments that change `.experiments/experiments.jsonl` will fail pinned inventory tests until regenerated deliberately and pins updated.
- Working tree has one uncommitted change: `.github/workflows/gates.yml` (no commit/push performed by this session; prior sessions auto-commit at end). Persistence unproven: the same fix claimed by the prior handoff was absent at HEAD `3434489`.

## Failed approaches / do not repeat
- Do not trust a committed handoff/task doc as current truth without re-running the producing/contract check (session start: doc claimed green while HEAD was 7/7 red; the same workflow edit was missing again at `3434489`).
- Do not assume an uncommitted working-tree change survives to the next session; check `git status`/`git diff` for `.github/workflows/gates.yml` first.
- Do not add/modify a pinned test to match an unbuilt source; make the source satisfy the contract.
- Do not run `scripts/plan_artifact_restoration.py --apply` (no-op; needs authorization).
- Do not invent/execute H182 from exhausted/adjacent families or blocked data.
- Do not time a performance gate with `tracemalloc` active.
- Do not mass-edit frozen contracts/tests to force green.
- Do not commit/push unless requested.

## Constraints
- `src/qtr` unchanged unless an evidenced defect requires it. No frozen/certified/published artifact, verdict, threshold, or gate weakening. No commit/push unless requested. Free/public data only.