# HANDOFF_CURRENT_SESSION.md — gates workflow fix converted to apply-ready patch; loop stopped

## What changed
- **`patches/0001-gates-workflow-contract-fix.patch`** (new): the previously-recurring
  `.github/workflows/gates.yml` fix as an apply-ready patch with a header explaining why
  an agent cannot land it. Not applied to the workflow in this commit.
- **`AGENTS.md`**: documented that workflow files are maintainer-managed/agent-unreachable,
  that `tests/test_gates_workflow.py` is red on `main` by that design, and where the fix
  lives. Also closed the unclosed ```bash fence in the Lint section (line 15-18).
- **`NEXT_TASK.md`**: rewritten with the structural root cause, the exact maintainer
  command, and this session's evidence.
- No `src/qtr`, test, threshold, verdict, or frozen artifact changed. `.github/workflows`
  restored to HEAD before commit (no workflow edit in this commit).

## Root cause (structural, supersedes "push the commit")
`tests/test_gates_workflow.py` fails 7/7 at `origin/main` (`d542019`). Fixing it in a
commit is impossible for an agent, for two independent reasons:
1. `.github/scripts/kilo-controller.sh:305-317` restores `.github/workflows` from
   `origin/main` after each session and `:323` excludes those paths from staging.
2. The repo GitHub App token has no `workflows` permission
   (`gh api repos/<repo> --jq .permissions` → all `false`), so the fix can never be
   pushed to `main`.

Every "fix" commit since `f86d732` was therefore reverted by an empty-message commit
(`d542019`, `5bcc177`, `8e3e496`, `0efe2af`, ...). This was the 7th cycle.

## Actually verified (this session)
- Full suite: `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`
  → **7 failed, 3746 passed, 48 skipped**; coverage **100.00%** (1211 stmts / 422 branches / 0 miss).
  All 7 failures are `tests/test_gates_workflow.py` (the known workflow block).
- Patch applied in isolation (`/tmp/gates-verify` = patched `gates.yml` + the contract test)
  → `tests/test_gates_workflow.py` **7 passed**.
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → clean.
- `python -m ruff check src tests run_*.py scripts` → All checks passed (327 files with format check).
- `python -m ruff format --check src tests run_*.py scripts` → 327 files already formatted.

## What remains unresolved
- **Maintainer push** of `patches/0001-gates-workflow-contract-fix.patch` (needs `workflow` scope).
- **H182:** authorization-gated (free-data PIT families H1–H181 exhausted/rejected).
- **Artifact restoration apply:** authorization-gated (dry-run no-op).

## Failed approaches / do not repeat
- Do NOT commit the `gates.yml` edit again and report it durable — it is reverted by
  `kilo-controller.sh:305` and cannot be pushed (no `workflows` permission). 7 cycles.
- Do NOT weaken/delete `tests/test_gates_workflow.py` or the maintainer-managed-workflows policy.
- Do NOT trust a handoff's failure list without re-running the suite (this repo has a
  history of stale handoff docs).

## One precise next task
For a human maintainer only: `git apply patches/0001-gates-workflow-contract-fix.patch`,
commit, and push to `origin/main` with `workflow` scope; then confirm
`test_gates_workflow.py` 7/7 and a green full suite. For an agent: the free-data
research queue is exhausted (H182 unassigned), so the next agent should audit
infrastructure or await explicit authorization for a data gap — not invent a family.