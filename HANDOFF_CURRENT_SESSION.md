# HANDOFF_CURRENT_SESSION.md — CI gates workflow reconciled to pinned contract (2026-11-13)

## What changed
- `.github/workflows/gates.yml` reconciled to the committed, pinned contract in
  `tests/test_gates_workflow.py`:
  - added `scripts/**` to both the `push` and `pull_request` path triggers;
  - lint job now runs `python -m ruff check src tests run_*.py scripts` and
    `python -m ruff format --check src tests run_*.py scripts`;
  - both `lint` and `research_gates` install the package with
    `python -m pip install -e . --no-deps` after `pip install -r requirements.txt`;
  - `research_gates` runs `python scripts/backtest_perf_regression_gate.py`
    before pytest.
- `HANDOFF_CURRENT_SESSION.md` and `NEXT_TASK.md` updated with the verified state.
- No `src/qtr`, runner, gate threshold, verdict, frozen artifact, or published
  number changed. `tests/` was NOT modified this session.

## Root cause of the prior false handoff (do not repeat)
- The previous session added a new pinned assertion to
  `tests/test_gates_workflow.py` (`test_jobs_install_the_package_editably`,
  commit `4f5436b`) and claimed the workflow had been reconciled, but
  **`.github/workflows/gates.yml` was never modified** — it remained the original
  committed at `f86d732`.
- At the start of this session HEAD therefore had **7 failing** contract tests
  (5 workflow-shape assertions + 2 editable-install assertions), not the
  "3753 passed / 0 failed" the handoff claimed. The committed handoff was false.
- This session made the source (workflow) match the pinned test instead of
  trusting the doc.

## Actually verified (this session, own evidence)
- Focused contracts:
  `python -m pytest -q -W error tests/test_gates_workflow.py tests/test_generated_manifest_contract.py`
  → **18 passed**, 0 skipped, 0 failed (was 7 failed / 11 passed before the fix).
- Lint/format: `python -m ruff check src tests run_*.py scripts` → All checks
  passed; `python -m ruff format --check src tests run_*.py scripts` → 327 files
  already formatted.
- Performance gate: `python scripts/backtest_perf_regression_gate.py` →
  `PERF GATE PASSED` (100 symbols x 252 bars, 0.305s vs 5s limit, 10.7MB peak,
  13668 trades).
- Full suite: `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`
  → **3753 passed, 48 skipped, 0 failed** (327.81s), `src/qtr` coverage **100%**
  (1211 stmts / 422 branches, 0 miss).

## What remains unresolved
- **H182 discovery:** free-data PIT strategy-family discovery is exhausted at H181
  (Cycle 96, `NEW_FAMILY_RESEARCH_REGISTER.md`,
  `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6). Carry/insider/earnings/options/
  breakeven candidates are data-blocked; the rest are adjacency- or power-blocked.
  Requires explicit human authorization and an authorized free/PIT source for a
  materially new mechanism. Do not invent/execute H182.
- **Artifact restoration apply:** blocked on explicit human authorization and a
  no-op on this checkout (`--dry-run` → Recoverable 0 / Excluded 172 /
  Unrecoverable 25; baseline in `tests/test_reproducibility_audit.py`).
- **Generated inventories/pins remain frozen;** mutating `.experiments/experiments.jsonl`
  will fail pinned inventory tests until deliberately regenerated.
- Working tree has one uncommitted change: `.github/workflows/gates.yml`
  (no commit/push performed by this session; prior sessions auto-commit at end).

## Failed approaches / do not repeat
- Do not trust a committed handoff/task doc as current truth without re-running the
  producing/contract check. This is the exact failure that produced the false
  "green" claim: the doc said 3753 passed but HEAD was 7/7 red.
- Do not add/modify a pinned test to match an unbuilt source. Make the source
  (workflow) satisfy the committed contract, or update both in one change.
- Do not invent/execute H182 from exhausted/adjacent families or blocked data.
- Do not run `scripts/plan_artifact_restoration.py --apply` (no-op; needs authorization).
- Do not time performance gates with `tracemalloc` active.
- Do not commit/push unless explicitly requested.

## One precise next task
**Confirm the workflow fix persisted and the baseline is green, then hold for the
authorization-gated H182/discovery decision.**

Concretely, the next session should:
1. Inspect `git log`/`git show` to confirm `.github/workflows/gates.yml` now contains
   `scripts/**`, the `scripts` ruff targets, `python -m pip install -e . --no-deps`,
   and `python scripts/backtest_perf_regression_gate.py` (this session's fix must be
   committed by the harness/auto-commit, not left as drift).
2. Re-verify the baseline with `python -m pytest -q -W error --cov=qtr --cov-branch`
   (expect **3753 passed, 48 skipped, 0 failed**, `src/qtr` 100%), ruff check/format
   clean over `src tests run_*.py scripts`, and `python scripts/backtest_perf_regression_gate.py`
   → `PERF GATE PASSED`.
3. If green, the only remaining open item is **H182 selection**, which requires
   explicit human authorization plus an authorized free/PIT data source (or an
   explicit decision to close free-data family discovery as exhausted and shift to
   auditing/infrastructure only). Do not invent H182 or modify frozen
   artifacts/gates/thresholds.