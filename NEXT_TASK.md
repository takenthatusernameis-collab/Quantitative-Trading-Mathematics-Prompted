# NEXT_TASK.md — maintainer action: land the gates workflow contract fix

## Current state (2026-11-13)

`tests/test_gates_workflow.py` is **red on origin/main by design** — it is the only failing test file in the suite (AGENTS.md line 33). It pins the committed `.github/workflows/gates.yml` against required contract behavior:

- lint job ruff targets include `scripts/` (both `ruff check` and `ruff format --check`)
- push/pull_request path triggers include `scripts/**`
- `research_gates` job runs `python scripts/backtest_perf_regression_gate.py`
- both jobs install the package editably: `python -m pip install -e . --no-deps`

The committed `gates.yml` lacks all four, so the test reports **7 failed**.

## What was verified this session

- `python -m pytest tests/test_gates_workflow.py -q` → **7 failed** on committed `gates.yml` (contract mismatch enumerated above).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → **applies cleanly** to HEAD `a7957c4`.
- Temporarily applied the patch, re-ran the contract test → **7 passed**. Restored `gates.yml` via `git checkout`; working tree clean, no `src/qtr`, test, gate, or artifact touched; no commit/push.

## What remains unresolved

The fix cannot be landed by the autonomous agent:

- `.github/workflows/**` is **maintainer-managed and agent-unreachable** (AGENTS.md line 31-32). It is restored from `origin/main` after every session by `.github/scripts/kilo-controller.sh` and excluded from staging; the repository-scoped GitHub App token has no `workflows` permission, so `git push` of a workflow change is rejected.
- Committing the change in-tree does not persist; `origin/main` keeps the failing `gates.yml`.

## One precise next task (maintainer, with workflow scope)

Apply the already-staged patch and land it:

```bash
git apply patches/0001-gates-workflow-contract-fix.patch
git commit -am "fix(ci): satisfy gates workflow contract"
git push origin main
```

Expected result: `tests/test_gates_workflow.py` → **7 passed** (was 7 failed), making the full suite green. `tests/test_gates_workflow.py` itself must not be modified or weakened; the patch only changes `.github/workflows/gates.yml` per the diff in `patches/0001-gates-workflow-contract-fix.patch`.

Constraint from AGENTS.md: do not commit workflow changes from an agent session; capture as apply-ready patch under `patches/` (done) and record the maintainer action here (done).
