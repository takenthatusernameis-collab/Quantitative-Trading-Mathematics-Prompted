# Next task (2026-11-18, Cycle 212)

## What changed this session
- **Added `scripts/verify_gates_workflow_patch.py`** — an executable ratchet for the
  maintainer-gated workflow fix. It parses the live `.github/workflows/gates.yml`,
  reports every contract violation pinned by `tests/test_gates_workflow.py`, applies
  `patches/0001-gates-workflow-contract-fix.patch` to a **throwaway copy** (never the
  working tree), and re-checks the patched document. Exit 0 when the live workflow is
  already fixed **or** the pending patch resolves all violations; 1 when the patch is
  stale/incomplete; 2 when `git`/workflow/patch is missing.
- **Added `tests/test_verify_gates_workflow_patch.py`** — 15 tests covering exactly-7
  violations on a pre-fix fixture, zero on a fixed one, malformed-document reporting,
  throwaway-copy application (working tree unchanged), stale/incomplete patch failure,
  missing inputs, and a live-repository invariant that stays green after the maintainer
  lands the patch.
- No change to `src/qtr`, runners, frozen artifacts, gates, or `.github/workflows/**`.

## What was actually verified (own evidence, 2026-11-18)
- `python scripts/verify_gates_workflow_patch.py` → prints the 7 live violations and
  `PATCH VERIFIED: 0001-gates-workflow-contract-fix.patch applies to the live gates.yml
  and resolves all 7 violation(s)`, exit 0.
- `python -m pytest -q tests/test_verify_gates_workflow_patch.py` → **15 passed**.
- Full pinned suite `python -m pytest -q -W error --cov=qtr --cov-branch
  --cov-report=term-missing --ignore=tests/test_gates_workflow.py` → **4350 passed,
  51 skipped, 0 failed** (642.76s), `src/qtr` coverage **100.00%** (1692 stmts / 642
  branches / 0 miss).
- `python -m ruff check src tests run_*.py scripts` → All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` → **339 files formatted**.
- `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.796s < 5s,
  10.7MB peak, 13668 trades).
- `python -m pytest -q tests/test_gates_workflow.py` → **7 failed** (still red on
  `origin/main`; maintainer-gated).

## What remains unresolved
- **Maintainer-gated (agent-unreachable):** apply/push
  `patches/0001-gates-workflow-contract-fix.patch` with `workflows`-scoped credentials.
  `scripts/verify_gates_workflow_patch.py` proves the patch is still valid and complete;
  after landing, the same script (and its tests) must keep reporting `CONTRACT SATISFIED`.
- **Strategy-family discovery exhausted:** H1–H182 executed/rejected
  (`NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96). H183 data-blocked (futures roll/contango,
  crypto funding, or options PIT data).
- **Reproducibility backlog (frozen, authorization-gated):** missing_files=197,
  hash_mismatches=11, orphaned_files=528, missing_meta_files=0.

## One precise next task
- **Maintainer:** `git apply patches/0001-gates-workflow-contract-fix.patch && git commit
  -am "fix(ci): satisfy gates workflow contract" && git push origin main`, then run
  `python scripts/verify_gates_workflow_patch.py` (expect `CONTRACT SATISFIED`) and
  `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
- **Agent:** run `python scripts/verify_gates_workflow_patch.py` as the first baseline
  check each session; if it exits 1, refresh the patch against the live `gates.yml`
  (workflow-scoped credentials still required to land it). Otherwise only act on NEW
  concrete evidence of a runner-reachable defect, then rerun focused tests, both ruff
  checks, the full pinned coverage suite, and the perf gate. Do not make speculative
  source changes.

## Approaches already tried and why they should not be repeated
- Do not re-audit `src/qtr`/runners for the pinned defect classes without NEW evidence
  (exhaustively reviewed through Cycle 211).
- Do not edit `.github/workflows/**` or weaken `tests/test_gates_workflow.py`
  (maintainer-gated; patch + verification script exist).
- Do not re-verify the patch by hand in `/tmp` — `scripts/verify_gates_workflow_patch.py`
  does it deterministically and covers the already-fixed state.
- Do not edit momentum runners' `param_grid_results` logging without maintainer authorization.
- Do not invent H183 or treat parameter/timeframe/universe variants as new mechanism families.
- Do not trust handoff pass/fail/coverage counts — re-run the gates.

## HEAD
- `b7b526d` at session start (working tree carries the two new files above; the session
  controller checkpoints them, `.github/workflows/**` excluded from staging).
