# HANDOFF_CURRENT_SESSION.md — gates.yml revert ROOT-CAUSED (controller, not "not committed")

## What changed
- **No `src/qtr`, test, threshold, verdict, frozen artifact, or committed file changed.**
- `gates.yml` was temporarily corrected in the worktree to verify the fix, then restored to
  HEAD (`git status` clean; `git diff -- .github/workflows/gates.yml` empty).
- `NEXT_TASK.md` rewritten with the definitive root cause, exact fix, and next task.

## Root cause (new, evidence-based — supersedes "fix not persisted")
`gates.yml` is **actively reverted by the autonomous controller**, by design:
- `.github/scripts/kilo-controller.sh:230` — `WORKFLOW_BASE_SHA="$(git rev-parse HEAD)"`
  captured **once at activation start**.
- `.github/scripts/kilo-controller.sh:305` — after every session:
  `git restore --source="$WORKFLOW_BASE_SHA" --staged --worktree -- .github/workflows`
  reverts `gates.yml` (and all workflows) to the activation-start revision.
- `.github/scripts/kilo-controller.sh:323` excludes `.github/workflows/**` from `git add`,
  but the `--staged` restore already staged the old content, so
  `kilo-controller.sh:396` (`git commit --allow-empty-message -m ""`) records the revert —
  the recurring empty-message revert commits (`0efe2af`, `9d00e01`, `f5d7c1f`, …).
- This activation is **stale-based**: `GITHUB_SHA=f86d73282a4123961f5ab92d693f9084f7609539`
  = `WORKFLOW_BASE_SHA`, 18 commits behind HEAD, with the **broken** `gates.yml`. So every
  fix (`3675656`, `09d4701`, `6c2078d`, `2f88722`) is reverted to `f86d732`'s broken version.

## Actually verified (this session, own evidence)
- At HEAD `0efe2af`: `python -m pytest -q -W error tests/test_gates_workflow.py` → **7 failed**
  (all contract assertions).
- With corrected `gates.yml` in worktree: same test → **7 passed**.
- Full baseline with corrected `gates.yml`:
  `pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` →
  **3753 passed, 48 skipped, 100% coverage (1211 stmts / 422 branches, 0 miss)**.
- `ruff check` / `ruff format --check` over `src tests run_*.py scripts` → clean (327 files).
- `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.289s / 5s, 10.7MB).
- `git status` clean after restoring `gates.yml` to HEAD.

## What remains unresolved
- **gates.yml:** maintainer-owned and reverted by the controller to the stale base. Agent
  edits cannot persist; a maintainer commit on `main` (or a controller restore fix) is required.
- **H182:** authorization-gated (free-data PIT families H1–H181 exhausted/rejected).
- **Artifact restoration apply:** authorization-gated (dry-run no-op).

## Failed approaches / do not repeat
- Do NOT re-apply the `gates.yml` edit and report it durable — it is reverted by
  `kilo-controller.sh:305` (stale `WORKFLOW_BASE_SHA`). This is the 6th cycle of the same trap.
- Do NOT trust handoff claims of "persisted" without `git show HEAD:.github/workflows/gates.yml`
  + running `tests/test_gates_workflow.py`.
- Do NOT weaken the "maintainer-managed workflows" policy or the contract test.

## One precise next task
See `NEXT_TASK.md` §"One precise next task". Short form: **stop re-editing `gates.yml`;**
either (1) have a maintainer land the corrected `gates.yml` directly on `main`, or
(2) fix `kilo-controller.sh` to restore workflows relative to the latest `origin/main`
(fetch-first, fall back to `WORKFLOW_BASE_SHA`), preserving the "agents cannot change
workflows" intent. Then re-verify: `test_gates_workflow.py` 7/7, full suite 100% coverage,
ruff clean, perf gate passed.