# NEXT_TASK.md — gates.yml contract fix is maintainer-gated; do NOT commit it again

## Structural finding (2026-11-13, verified this session)

`tests/test_gates_workflow.py` fails 7/7 at `origin/main` (`d542019`) because
`.github/workflows/gates.yml` on `main` lacks the contract's required content.
Every attempt to fix it *in a commit* has been reverted, 7 cycles in a row:

- The controller restores `.github/workflows` from `origin/main` after each session
  (`.github/scripts/kilo-controller.sh:305-317`) and excludes those paths from staging
  (`.github/scripts/kilo-controller.sh:323`).
- `origin/main` holds the broken file, and the repo-scoped GitHub App token (`ghs_*`)
  has no `workflows` permission (`gh api repos/<repo> --jq .permissions` →
  `{"admin":false,"maintain":false,"pull":false,"push":false,"triage":false}`), so the
  fix can never reach `main` from an agent.
- Consequence: committing the workflow edit produces a revert commit with an empty
  message (`d542019`, `5bcc177`, `8e3e496`, `0efe2af`, ...) and no progress.

**Do not repeat:** editing `gates.yml` in-tree and expecting persistence is a proven
dead end. Do not weaken/delete the contract test, and do not weaken the
maintainer-managed-workflows policy.

## Apply-ready fix (committed here, not applied to the workflow)

`patches/0001-gates-workflow-contract-fix.patch` — header explains the block; the diff:

- `push`/`pull_request` `paths`: add `'scripts/**'`.
- `lint` job: add `python -m pip install -e . --no-deps`; ruff check/format target
  `src tests run_*.py scripts`.
- `research_gates` job: add the editable install and
  `python scripts/backtest_perf_regression_gate.py` before "Run gates".

## Exact maintainer action (only remaining unblock)

```bash
git apply patches/0001-gates-workflow-contract-fix.patch
git commit -am "fix(ci): satisfy gates workflow contract"
git push origin main        # needs a credential with `workflow` scope
```

Then confirm `git show origin/main:.github/workflows/gates.yml | grep -c 'scripts/\*\*'`.

## Evidence (this session, HEAD `d542019`)

- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`
  → **7 failed, 3743 passed, 51 skipped** (429s); coverage **100.00%** (1211 stmts / 422 branches,
  0 miss). All 7 failures are `tests/test_gates_workflow.py`.
- `python -m pytest -q -W error tests/test_gates_workflow.py` → **7 failed** (contract).
- Patch verified in isolation (`/tmp/gates-verify`, patched `gates.yml` + the contract test):
  → **7 passed**.
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → clean.
- `python -m ruff check src tests run_*.py scripts` → All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` → 327 files already formatted.

## Sidecar-count correction (2026-11-13)

`REPRODUCIBILITY_AUDIT_REPORT.md` §4 prose claimed the missing-`.meta.json`-sidecar
backlog was **148** (an 8-restore delta from a prior session that never materialized).
Independent recount against the committed corpus yields **140** missing (1,068 present),
exactly matching `REPRODUCIBILITY_BASELINE["missing_meta_files"]`. Prose corrected;
baseline and gate unchanged. `tests/test_reproducibility_audit.py` — **7 passed**.

## Remaining open items (unchanged, authorization-gated)

- **H182:** free-data PIT strategy-family queue exhausted (H1–H181 executed/rejected,
  H182 unassigned; commodity carry data-blocked) per `NEW_FAMILY_RESEARCH_REGISTER.md`
  Cycle 96 / `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6. Do not pre-register or execute
  without explicit human authorization plus an authorized free/PIT data source.
- **Artifact restoration apply:** authorization-gated (dry-run no-op:
  Recoverable 0 / Excluded 172 / Unrecoverable 25).