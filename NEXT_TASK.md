# Session complete (2026-11-21, Cycle 243 — runner-side reproducibility fix)

## State

H1–H190 exhausted/rejected or data-blocked (unchanged; see `AGENTS.md` and
`NEW_FAMILY_RESEARCH_REGISTER.md` Cycles 215–235). Free-data point-in-time family
discovery remains exhausted; do not re-declare any H-ID data-blocked without
naming the probed source, and do not treat parameter/timeframe/universe/market
variants of H1–H190 as new families.

**This session made a real source change (the first in several cycles):** the three
momentum runners no longer write `param_grid_results` twice per run. This is the
root cause of 8 of the 11 `hash_mismatches` in `REPRODUCIBILITY_AUDIT_REPORT.md`
§2. `src/qtr` is unchanged; the committed `.experiments/experiments.jsonl` is
**not** edited (that remains authorization-gated).

## What changed (Cycle 243)

- `run_ts_momentum_experiment.py`, `run_cs_momentum_experiment.py`,
  `run_regime_gated_momentum_experiment.py`: removed the superseded first
  `tracker.log_dataframe("param_grid_results", ...)` call; the single remaining
  call is the final-path write that produced the current on-disk artifact, so a
  re-run is byte-identical for the grid.
- New `tests/test_momentum_runner_single_grid_write.py` (5 tests): AST-counts
  `log_dataframe("param_grid_results", <literal>)` per runner (== 1), with a
  negative control that reconstructs the pre-fix double write (detector reports 2)
  and a specificity control (other artifact names / non-literal first argument are
  not counted).
- Docs: `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 243 entry;
  `REPRODUCIBILITY_AUDIT_REPORT.md` §2 runner-side note.

## Verified evidence (this session, 2026-11-21)

- `python -m pytest -q` → **4572 passed / 51 skipped / 7 failed** (was 4567/51/7;
  +5 from the new test file). All 7 failures are `tests/test_gates_workflow.py`,
  unchanged and maintainer-gated by design (patch
  `patches/0001-gates-workflow-contract-fix.patch`).
- Focused regression set (`test_tsmom_runner_long_only`,
  `test_runner_causality_inventory`, `test_runner_metric_agreement`,
  `test_h29_lookahead_sweep`, `test_h54_non_metrics_block_disclosure`,
  `test_reproducibility_audit`, `test_experiments_jsonl_no_duplicate_artifact_names`)
  → **447 passed**.
- `python -m ruff check src tests run_*.py scripts` → clean;
  `python -m ruff format --check src tests run_*.py scripts` → 361 files formatted.
- `src/qtr` coverage unchanged at 100% (no source change).
- Working tree: 4 files changed (3 runners + 1 new test) plus 3 doc files; no
  artifacts or frozen contracts touched.

## Session verification (2026-11-21, Cycle 243 — verification only; no code change)

No source, runner, test, or artifact change was made this session. The only remaining
actionable item (the workflow contract fix) is agent-unreachable, and artifact cleanup
is authorization-gated, so this session's durable contribution is fresh verification
evidence for the next agent / maintainer.

- `tests/test_gates_workflow.py` → **7 failed** (re-confirmed). The 7 failures are
  exactly the contract gaps the patch closes:
  - `test_lint_job_includes_scripts_in_ruff_targets[ruff check]` and `[ruff format]`:
    committed `gates.yml` lint step is `python -m ruff check src tests run_*.py` /
    `python -m ruff format --check src tests run_*.py` (missing `scripts`).
  - `test_path_triggers_include_scripts[push]` and `[pull_request]`: path filters
    lack `scripts/**`.
  - `test_research_gates_job_runs_performance_regression_gate`: research_gates job
    lacks `python scripts/backtest_perf_regression_gate.py`.
  - `test_jobs_install_the_package_editably[lint]` and `[research_gates]`: neither job
    installs the package editably (`python -m pip install -e . --no-deps`).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → **applies
  cleanly** on the live tree.
- `scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED**
  (100 symbols x 252 bars -> 0.942s, limit 5s, 10.7MB peak, 13668 trades).
- Focused regression set
  (`test_tsmom_runner_long_only`, `test_runner_causality_inventory`,
  `test_runner_metric_agreement`, `test_h29_lookahead_sweep`,
  `test_h54_non_metrics_block_disclosure`, `test_reproducibility_audit`,
  `test_experiments_jsonl_no_duplicate_artifact_names`) → **447 passed**.
- `python -m ruff check src tests run_*.py scripts` → **clean**.
- `python -m ruff format --check src tests run_*.py scripts` → **361 files already
  formatted**.
- `src/qtr` coverage unchanged at 100% (no source change).

## Remaining reproducible-but-NOT-changed (deliberate, evidence-based)

- The committed `experiments.jsonl` still carries the 11 `hash_mismatches` (8
  `param_grid_results` + 3 `summary.json`). The runner fix prevents *future*
  stale hashes but does not rewrite history; the log remediation (drop superseded
  duplicate keys) is **authorization-gated** (audit §2) and was not performed.
- `validate_strategy` still raises on a **generator** argument and on a
  **non-numeric string array**. Left raising deliberately: every sibling function
  (`sharpe_ratio`, `parameter_sensitivity`, ...) uses the same bare
  `np.asarray(x, dtype=float)`, so this is a module-wide caller-type convention,
  not a `validate_strategy` divergence (see prior handoffs).

## Remaining actionable items

1. **Maintainer-applied workflow contract fix**
   (`patches/0001-gates-workflow-contract-fix.patch`) to make
   `tests/test_gates_workflow.py` green — **agent-unreachable** (`.github/workflows/**`
   is maintainer-managed, excluded from staging by
   `.github/scripts/kilo-controller.sh`, restored from `origin/main` after every
   session, and the repo-scoped GitHub App token has no `workflows` permission).
   Capture as apply-ready and record the maintainer action here.

2. **Authorization-gated artifact cleanup** from
   `REPRODUCIBILITY_AUDIT_REPORT.md` §2: drop 8 superseded duplicate
   `param_grid_results` keys + 3 stale `summary` keys from `experiments.jsonl`
   (and move the audit baseline + pins in the same commit). The runner-side root
   cause is now fixed, so this is the remaining half. **Do not overwrite
   artifacts** without authorization.

## One precise next task (for next session)

**None blocking.** The single next task is the maintainer action above: apply
`patches/0001-gates-workflow-contract-fix.patch` to `.github/workflows/**` so
`tests/test_gates_workflow.py` goes green, then record the action in this file.

Command (maintainer, with workflow scope):
  git apply patches/0001-gates-workflow-contract-fix.patch
  git commit -am "fix(ci): satisfy gates workflow contract"
  git push origin main

Expected result: `tests/test_gates_workflow.py` -> 7 passed (was 7 failed), bringing
the full suite from 4572 passed / 51 skipped / 7 failed to 4579 passed / 51 skipped /
0 failed.

If that lands and artifact-cleanup authorization arrives, perform item 2: in one
commit, drop the 8 superseded `param_grid_results` keys + 3 stale `summary` keys
from `.experiments/experiments.jsonl`, update `REPRODUCIBILITY_BASELINE`
(`hash_mismatches` 11 → 3), `PINNED_HASH_MISMATCHES`, and
`REPRODUCIBILITY_AUDIT_REPORT.md` together, then re-run
`tests/test_reproducibility_audit.py` (the gate fails on any count change that is
not a deliberate, documented baseline move).

If further hardening is desired later, follow the same evidence-first pattern:
first reproduce a concrete crash under `-W error` from a public-API path, then
fix with a minimal fail-closed guard + a test that keeps `src/qtr` at 100%
branch coverage. Do not manufacture guards for inputs that already behave
consistently with the rest of the module.

## Approaches already tried / do not repeat

- Do not re-declare any H-ID family as data-blocked without naming the probed source.
- Do not treat parameter/timeframe/universe/market variants of H1–H190 as new families.
- Do not modify `.github/workflows/**` (maintainer-managed; agent-unreachable).
- Do not re-run H190 or any exhausted family as a variant; the full-window
  pre-registered runs are the record.
- Do not reintroduce a hard dependency on `.cache/xbrl/**` in tests: that cache is
  git-ignored and absent on fresh checkouts/CI. Tests must be hermetic (synthetic
  fixtures), as H187/H188 now are.
- Do not mass-edit runners/tests/gates to force the suite green; frozen-contract
  drifts need per-contract evidence and authorization.
- Do not manufacture a hardening guard without first reproducing a concrete
  failure under `-W error`, and do not add a guard to one function when the same
  input class already behaves identically across all sibling functions.
- **Coverage command note:** `--cov=qtr.validation.statistics` triggers a numpy
  `ImportError: cannot load module more than once per process` during collection
  in this environment (Python 3.14 / numpy 2.x). Use `--cov=qtr` (the form the
  handoff/CI uses); it works and reports per-module coverage.
- `_probe.txt` (repo root) is a tracked leftover probe script from a prior
  session (not a `.py` file, so ruff ignores it). It is harmless; leave it unless
  a cleanup task is authorized.

## Session re-verification (2026-11-21, Cycle 244) — verification only; no code change

This session (2026-11-21) independently re-verified the assigned task remains
agent-unreachable; no in-tree change was made and the working tree is clean.

- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → **applies cleanly** on the live tree (re-confirmed).
- `tests/test_gates_workflow.py` → **7 failed** (re-confirmed), all contract gaps the patch closes (scripts in ruff targets + path triggers, editable install in both jobs, backtest perf gate in research_gates).

Why the task cannot be landed by this agent:
- `.github/scripts/kilo-controller.sh` restores `.github/workflows/**` from origin/main at session end and excludes those paths from staging.
- The repo-scoped GitHub App token has no `workflows` permission, so `git push` of a workflow change is rejected.

Precise next task (maintainer, with workflow scope):
  git apply patches/0001-gates-workflow-contract-fix.patch
  git commit -am "fix(ci): satisfy gates workflow contract"
  git push origin main
  Expected result: `tests/test_gates_workflow.py` -> 7 passed (was 7 failed),
  bringing the full suite from 4572 passed / 51 skipped / 7 failed to
  4579 passed / 51 skipped / 0 failed.

- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → **applies
  cleanly** on the live tree (re-confirmed).
- `tests/test_gates_workflow.py` → **7 failed** (re-confirmed), all contract gaps
  the patch closes (scripts in ruff targets + path triggers, editable install in
  both jobs, backtest perf gate in research_gates).
- Throwaway checkout with the patch applied → `tests/test_gates_workflow.py`
  **7 passed** (re-confirmed), matching Cycle 121 evidence.
- `python -m ruff check src tests run_*.py scripts` → **clean**.
- `python -m ruff format --check src tests run_*.py scripts` → **361 files
  formatted**.

Why the task cannot be landed by this agent:
- `.github/scripts/kilo-controller.sh` restores `.github/workflows/**` from
  `origin/main` at session end and excludes those paths from staging
  (`git add -A -- . ':(exclude).github/workflows/**'` ... `git clean -fd --
  .github/workflows`), so an in-tree workflow edit does not persist.
- The repo-scoped GitHub App token has no `workflows` permission, so `git push`
  of a workflow change is rejected.

Precise next task (maintainer, with workflow scope):
  git apply patches/0001-gates-workflow-contract-fix.patch
  git commit -am "fix(ci): satisfy gates workflow contract"
  git push origin main
  Expected result: `tests/test_gates_workflow.py` -> 7 passed (was 7 failed),
  bringing the full suite from 4572 passed / 51 skipped / 7 failed to
  4579 passed / 51 skipped / 0 failed.