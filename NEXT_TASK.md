# Next task (Cycle 202, 2026-11-17)

## What changed this session
- **No source, test, gate, artifact, sidecar, hash, frozen-number, or workflow change.**
  Working tree clean at start (HEAD `e338680`, up to date with `origin/main`).
  Only handoff docs updated with own re-verified evidence. This is a handoff
  update, **not** project progress.

## What was actually verified (own evidence, 2026-11-17, Cycle 201)
- `python -m ruff check src tests run_*.py scripts` -> **All checks passed.**
- `python -m ruff format --check src tests run_*.py scripts` -> **336 files already formatted.**
- `python scripts/backtest_perf_regression_gate.py` -> **PERF GATE PASSED**
  (0.302s < 5s, 10.7MB peak, 13668 trades).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` -> exit 0 (applies cleanly).
- `python -m pytest -q tests/test_gates_workflow.py` -> **7 failed** (unchanged, maintainer-gated: missing editable install, `scripts/**` in lint targets/triggers, and perf-regression-gate step — matches `patches/0001-gates-workflow-contract-fix.patch`). Not a new defect.
- `grep -rn "TODO|FIXME|XXX|HACK" src/qtr` -> no matches.
- No new reproduced, runner-reachable defect found in `src/qtr`/runners/corpus metadata. No code change made.

## What remains unresolved
- **Maintainer-gated (agent-unreachable):** apply/push
  `patches/0001-gates-workflow-contract-fix.patch` with `workflows`-scoped
  credentials (`.github/scripts/kilo-controller.sh` restores `.github/workflows/**`
  from `origin/main`; no agent `workflows` token). After push:
  `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
- **Strategy-family discovery exhausted:** H1–H182 executed/rejected
  (`NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96; `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md`
  §6). H183 is data-blocked (futures roll/contango, crypto funding, or options
  point-in-time data). Do not invent candidates or treat
  parameter/timeframe/universe variants as new mechanism families.
- **Reproducibility backlog (frozen, authorization-gated):**
  `missing_files=197` (172 H28 contract-blocked + 25 unrecoverable),
  `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=0`
  (`REPRODUCIBILITY_AUDIT_REPORT.md`; audit tests green).
- **Single concrete code item (maintainer authorization required):** momentum
  runners log `param_grid_results` more than once per run
  (`run_ts_momentum_experiment.py:440/473/708`,
  `run_regime_gated_momentum_experiment.py:573/613/941`,
  `run_cs_momentum_experiment.py:294/516`), leaving one recorded hash stale.
  Remediation is authorization-gated and test-covered; do not change without
  maintainer authorization and a full gate run.

## One precise next task
**Maintainer:** apply and push `patches/0001-gates-workflow-contract-fix.patch`,
then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
**Agent (next session):** no agent code change is warranted. If (and only if) a
NEW reproduced, runner-reachable defect appears in `src/qtr`/runners/corpus
metadata, fix it with the smallest verifiable change and rerun focused tests,
`python -m ruff check src tests run_*.py scripts`,
`python -m ruff format --check src tests run_*.py scripts`, and
`python scripts/backtest_perf_regression_gate.py` with own evidence; otherwise
re-verify this baseline and make no code change.

## Approaches already tried and why they should not be repeated
- Do not re-review the seven `src/qtr` modules for pinned defect classes without
  NEW evidence (exhaustively re-reviewed through Cycle 195).
- Do not edit `.github/workflows/**` or weaken `tests/test_gates_workflow.py` —
  maintainer-gated contract; fix is the workflow patch.
- Do not edit the momentum runners' `param_grid_results` logging without
  maintainer authorization (frozen; test-covered; does not reduce the frozen backlog).
- Do not invent H183 or treat parameter/timeframe/universe variants as new
  mechanism families.
- Do not trust handoff pass/fail/coverage counts — re-run gates.
