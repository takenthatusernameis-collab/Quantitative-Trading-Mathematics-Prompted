# Handoff — Next Session (2026-11-20, Cycle 236 — audit/infrastructure: doc sync)

## State

H1–H190 exhausted/rejected or data-blocked (unchanged; see `AGENTS.md` and
`NEW_FAMILY_RESEARCH_REGISTER.md` Cycles 215–235). Free-data point-in-time family
discovery remains exhausted; do not re-declare any H-ID data-blocked without
naming the probed source, and do not treat parameter/timeframe/universe/market
variants of H1–H190 as new families.

## What changed (this session)

**EXPERIMENT_ARTIFACT_AUDIT.md** updated to reflect the current corpus state
(Cycle 236, post H183–H190). The doc previously stated Cycle-115 pins
(108 dirs / 100 summaries / 131 keys); the live corpus and
`tests/test_experiment_artifact_schema.py` pins are **116 / 108 / 150**.
Added a new re-verification banner (Cycle 236) documenting the 8 additional
summary.json artifacts from Cycles 213, 215, 219, 230, 232, 235. The ≥50% and
≥80% key sets are unchanged. No test pins were modified (they were already
correct); only the audit doc prose was refreshed.

Scope: documentation only. No `src/qtr`, runner, artifact, sidecar, hash, gate,
frozen number, test, or workflow was modified.

## Verified evidence (this session)

- `python -m pytest -q tests/test_experiment_artifact_schema.py` → **113 passed**.
- `python -m pytest -q tests/test_nf_20261120_01_equity_accruals.py tests/test_nf_20261120_02_net_share_issuance.py -W error` → **32 passed** (hermetic, no `.cache/` dependency).
- `python -m ruff check src tests run_*.py scripts` → clean.
- `python -m ruff format --check src tests run_*.py scripts` → 360 files formatted.
- `python scripts/backtest_perf_regression_gate.py` → PERF GATE PASSED (0.416s, limit 5s).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → applies cleanly.
- Corpus counts verified: 116 dirs, 108 summaries, 150 distinct keys, 9 keys ≥50%,
  3 keys ≥80%, 11 cache-only, 8 incomplete — all match test pins.

## One precise next task (for next session)

**None blocking.** The only remaining actionable item is still the
maintainer-applied workflow contract fix (`patches/0001-gates-workflow-contract-fix.patch`)
to make `tests/test_gates_workflow.py` green; it is agent-unreachable
(`.github/workflows/**` is maintainer-managed, restored from `origin/main` after
every session, and the repo-scoped GitHub App token has no `workflows` permission).

Optional low-risk follow-up (authorization-gated, do not overwrite artifacts):
- Drop 8 superseded duplicate `param_grid_results` keys + 3 stale `summary`
  keys from `experiments.jsonl` per `REPRODUCIBILITY_AUDIT_REPORT.md` §2.

## Approaches already tried / do not repeat

- Do not re-declare any H-ID family as data-blocked without naming the probed source.
- Do not treat parameter/timeframe/universe/market variants of H1–H190 as new families.
- Do not modify `.github/workflows/**` (maintainer-managed; agent-unreachable).
- Do not re-run H190 as a variant; the full-window pre-registered run is the record.
- Do not reintroduce a hard dependency on `.cache/xbrl/**` in tests: that cache is
  git-ignored and absent on fresh checkouts/CI. Tests must be hermetic (synthetic
  fixtures), as H187/H188 now are.
- Do not mass-edit runners/tests/gates to force the suite green; frozen-contract
  drifts need per-contract evidence and authorization.
- Do not add the 3 contested per-trade logs to `TRADE_LOG_RECORD` without
  authorization (breaks `test_the_three_pinned_sets_partition_the_record`).
- Do not treat the 3 newer H92 artifacts as published-default p-values; artifacts
  show real `0.005822770948177806`.
- The H57 / engine-total-return "code bug" hypothesis is disproven — both tests pass.

(End of file - total 77 lines)