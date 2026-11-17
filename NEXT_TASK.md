# Next task (Cycle 192, 2026-11-17)

## What changed this session
- **No source, test, gate, artifact, sidecar, hash, frozen-number, or workflow change.**
  Working tree was clean at start (HEAD `69f7385`, up to date with `origin/main`).
  Only handoff docs updated, with own re-verified evidence. This is a handoff
  update, **not** project progress.

## What was actually verified (own evidence, 2026-11-17, Cycle 192)
- `python -m ruff check src tests run_*.py scripts` -> **All checks passed.**
- `python -m ruff format --check src tests run_*.py scripts` -> **336 files already formatted.**
- `python scripts/backtest_perf_regression_gate.py` -> **PERF GATE PASSED**
  (0.324s < 5s, 10.7MB peak, 13668 trades).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` -> exit 0 (patch still applies cleanly).
- `python -m pytest -q tests/test_gates_workflow.py` not re-run this cycle (known maintainer-gated 7 failures per prior cycles/patch); full suite not re-run (prior evidence on same HEAD lineage: 4270 passed, 51 skipped, 7 failed in `test_gates_workflow.py`).
- No new reproduced, runner-reachable defect found from baseline re-verification and existing evidence.

## What remains unresolved
- **Maintainer-gated (agent-unreachable):** apply/push
  `patches/0001-gates-workflow-contract-fix.patch` with `workflows`-scoped
  credentials (`.github/scripts/kilo-controller.sh` restores `.github/workflows/**`
  from `origin/main`; no agent `workflows` token). After push:
  `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
- **Strategy-family discovery exhausted:** H1-H182 executed/rejected
  (`NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96; `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md`
  §6). H183 is data-blocked (futures roll/contango, crypto funding, or options
  point-in-time data). Do not invent candidates or treat
  parameter/timeframe/universe variants as new mechanism families.
- **Reproducibility backlog (frozen, authorization-gated):**
  `missing_files=197` (172 H28 contract-blocked + 25 unrecoverable),
  `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=0`
  (`REPRODUCIBILITY_AUDIT_REPORT.md`; `tests/test_reproducibility_audit.py` green).

## The single concrete code item (maintainer authorization required)
The 8 `param_grid_results` hash mismatches come from the momentum runners logging
the same artifact name **more than once** per run (pre- and post-BH grid), so one
recorded hash is always stale:
- `run_ts_momentum_experiment.py`: logs at `:440` (pre-BH), `:473` (post-BH),
  and **`:708` (pre-BH again)** -- the redundant `:708` re-log makes the on-disk
  file the pre-BH grid.
- `run_regime_gated_momentum_experiment.py`: `:573` (pre-BH), `:613` (post-BH),
  and **`:941` (pre-BH again)** -- same redundant re-log.
- `run_cs_momentum_experiment.py`: `:294` (pre-BH), `:516` (post-BH) -- both
  names recorded against one on-disk file.
This is **authorization-gated** (`REPRODUCIBILITY_AUDIT_REPORT.md` §2): the
remediation is to log once per final path (or drop superseded keys from
`experiments.jsonl`); the on-disk file is authoritative and feeds the published
values (`test_h54_non_metrics_block_disclosure.py` re-derives BH from it). The
runners are exercised by `test_runner_metric_agreement.py`,
`test_runner_causality_inventory.py`, `test_causality_invariant.py`,
`test_h51_benchmark_container_invariance.py`, `test_h29_lookahead_sweep.py`,
`test_parameter_sensitivity_reproducibility.py`, `test_cs_momentum_signal.py`, so
an agent edit risks breaking frozen contracts. **Do not change without maintainer
authorization and a full gate run.**

## One precise next task
**Maintainer:** apply and push `patches/0001-gates-workflow-contract-fix.patch`,
then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
**Agent (next session):** the free-data discovery queue and the four §6 fallback
items are all complete; **no agent code change is warranted.** If (and only if) a
NEW reproduced, runner-reachable defect appears in `src/qtr`/runners/corpus
metadata, fix it with the smallest verifiable change and rerun focused tests,
`python -m ruff check src tests run_*.py scripts`,
`python -m ruff format --check src tests run_*.py scripts`, and
`python scripts/backtest_perf_regression_gate.py` with own evidence; otherwise
re-verify this baseline and make no code change.

## Approaches already tried and why they should not be repeated
- Do not re-review the seven `src/qtr` modules for pinned defect classes without
  NEW evidence (exhaustively re-reviewed Cycle 191; no new defect).
- Do not edit `.github/workflows/**` or weaken `tests/test_gates_workflow.py` --
  maintainer-gated contract; fix is the workflow patch.
- Do not edit the momentum runners' `param_grid_results` logging without maintainer
  authorization (frozen; test-covered; does not reduce the frozen backlog).
- Do not invent a free-data H182/H183 or treat parameter/timeframe/universe
  variants as new mechanism families.
- Do not trust handoff pass/fail/coverage counts -- re-run gates.