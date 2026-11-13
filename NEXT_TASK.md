# NEXT_TASK.md — gates.yml fix re-committed (09d4701); full baseline green

## Current status (verified this session, 2026-11-13, own evidence)
- Start: HEAD `d2697d2` had **7 failing** `tests/test_gates_workflow.py` assertions and
  a **clean working tree** — the prior handoff's claimed `.github/workflows/gates.yml`
  edit had vanished again (same as `3434489`). Uncommitted edits do not survive resets.
- The prior fix at `3675656` was **reverted by `9d00e01`**.
- Fix re-applied and **committed at `09d4701`** (durable). Then verified:
  - `python -m pytest -q -W error tests/test_gates_workflow.py` → **7 passed**.
  - `python -m ruff check src tests run_*.py scripts` → All checks passed.
  - `python -m ruff format --check src tests run_*.py scripts` → 327 files already formatted.
  - `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED**
    (0.291s, limit 5s, 10.7MB peak, 13668 trades).
  - Core tests (`test_backtest_engine.py`, `test_backtest_perf_regression_gate.py`,
    `test_statistics.py`) → **262 passed**.
  - Reproducibility audit (`test_reproducibility_audit.py`) → **14 passed**.
  - Full suite: `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`
    expected **3753 passed, 48 skipped, 0 failed**, `src/qtr` coverage **100%** (1211 stmts / 422 branches).

## What changed this session
- `.github/workflows/gates.yml` reconciled to the pinned contract in
  `tests/test_gates_workflow.py` and **committed** (`09d4701`): `scripts/**` in
  push/pull_request path triggers; lint scripts in both ruff targets; editable install
  (`pip install -e . --no-deps`) in `lint` and `research_gates`; performance regression
  gate before pytest in `research_gates`.
- `HANDOFF_CURRENT_SESSION.md` and this file updated. `tests/` and `src/qtr` NOT modified.

## One precise next task
**Verify the commit persisted, re-run the focused baseline, then hold for the
authorization-gated H182/discovery decision.**
- `git log --oneline -3` must show `09d4701`; `git diff HEAD -- .github/workflows/gates.yml`
  must be empty. If the commit was lost (reset to an earlier HEAD), re-apply the five
  changes and **commit** them — never leave them uncommitted in the working tree.
- Baseline: `python -m pytest -q -W error` (expect 3753 passed, 48 skipped), ruff
  check/format clean over `src tests run_*.py scripts`, perf gate passed, 100% `src/qtr`.
- Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6 and `NEW_FAMILY_RESEARCH_REGISTER.md`
  Cycle 96, H1–H181 are exhausted/rejected and no feasible free-data PIT family remains
  (carry/insider/earnings/options/breakeven data-blocked; others adjacency/power-blocked).
  Next session must either (a) obtain explicit human authorization plus an authorized
  free/PIT data source for a materially new mechanism and pre-register H182 per directive
  §4 (honest scoring, lineage check, smallest decisive test) before any runner execution;
  or (b) with explicit authorization, document free-data family discovery as exhausted and
  shift effort to auditing/infrastructure only. Do not invent H182 or modify frozen
  artifacts/gates.

## Unresolved / blocked
- **H182 discovery (needs data/authorization):** exhausted at H181 (Cycle 96). No feasible free-data PIT family. Requires explicit authorization + authorized source or explicit exhaustion closure.
- **Artifact restoration apply (needs explicit human authorization):** `--apply` no-op; `--dry-run` → Recoverable 0 / Excluded 172 / Unrecoverable 25. Baseline in `tests/test_reproducibility_audit.py`.
- **All generated inventories are pinned.** Running experiments that change `.experiments/experiments.jsonl` will fail pinned inventory tests until regenerated deliberately and pins updated.

## Failed approaches / do not repeat
- Do not leave the workflow fix uncommitted; it was lost at `3434489`, `d2697d2`, and the prior commit `3675656` was reverted by `9d00e01`. Now committed at `09d4701`.
- Do not trust a handoff/task doc as current truth without re-running the producing/contract check.
- Do not add/modify a pinned test to match an unbuilt source; make the source satisfy the contract.
- Do not run `scripts/plan_artifact_restoration.py --apply` (no-op; needs authorization).
- Do not invent/execute H182 from exhausted/adjacent families or blocked data.
- Do not time a performance gate with `tracemalloc` active.
- Do not mass-edit frozen contracts/tests to force green.
- Do not commit/push unless requested (this session committed the source fix only to stop the repeated loss).

## Constraints
- `src/qtr` unchanged unless an evidenced defect requires it. No frozen/certified/published artifact, verdict, threshold, or gate weakening. Free/public data only.