# NEXT_TASK.md

## Latest session (2026-11-14, Cycle 118) — Re-verification of maintenance state; no actionable agent fix (free-data queue exhausted, workflow maintainer-gated)

### What changed

- Documentation/handoff only: refreshed `NEXT_TASK.md` and `HANDOFF_CURRENT_SESSION.md` with this session's own verification evidence/timestamps. No `src/qtr`, runner, test, artifact, workflow, or frozen number modified.

### What was actually verified (own evidence)

- `python -m pytest -q tests/test_reproducibility_audit.py` — **7 passed** (0.24s). Reproducibility backlog remains locked at baseline (`missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=0`); the 528-orphan read-only audit is recorded in `REPRODUCIBILITY_AUDIT_REPORT.md` §3 (Cycle 105) with no safe merge/delete path.
- `python -m pytest -q tests/test_gates_workflow.py` — **7 failed** (expected, unchanged). Contract requires `scripts/**` path triggers, editable install, `ruff ... scripts`, and perf-gate step in `.github/workflows/gates.yml`; fix remains `patches/0001-gates-workflow-contract-fix.patch` (agent-unreachable: `.github/workflows/**` maintainer-managed/restored, no workflow-scoped token).
- `python -m ruff check src tests run_*.py scripts` — **All checks passed**.
- `python -m ruff format --check src tests run_*.py scripts` — **335 files already formatted**.
- `python scripts/backtest_perf_regression_gate.py` — **PASSED** (`100 symbols x 252 bars -> 0.426s`, limit 5s).
- Prior-cycle suite evidence (not re-run here): Cycle 116 recorded `pytest -q --ignore=tests/test_gates_workflow.py` **3,795 passed / 51 skipped / 0 failed** and `tests/test_experiment_artifact_schema.py` **105 passed**; no source/test/artifact changes were made this session.

### What remains unresolved

1. **Maintainer-only:** apply `patches/0001-gates-workflow-contract-fix.patch` to `.github/workflows/gates.yml` and push with workflow scope (per patch header / AGENTS.md). Do not attempt to land workflow edits from the agent.
2. **Free-data strategy-family queue exhausted:** per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6 and `NEW_FAMILY_RESEARCH_REGISTER.md` Cycles 96/116, H1–H182 are executed/rejected and remaining repo-new mechanisms are data-blocked, underpowered, or mechanism/calendar-adjacent under free/public PIT data. No H183 can be honestly pre-registered without a data-gap resolution.

### Approaches already tried and why they should not be repeated

- Do not run another discovery-only cycle that re-confirms exhaustion without new data authorization or a §6 shift (Cycles 96 and 116).
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or alter coverage/frozen-contract gates.
- Do not treat delisted/spliced-continuous/unavailable free series as valid PIT data (OVX, VIX9D, ^RVX; spliced `=F` carry proxy; no free crypto funding history).
- Do not mass-edit runners/tests/gates or frozen artifacts to chase green; the 528 orphans and other reproducibility backlog items are intentionally baseline-frozen where contract/citation/authority constraints apply (`REPRODUCIBILITY_AUDIT_REPORT.md`).

### One precise next task

**Maintainer action (preferred, unblocks CI contract):** apply and push `patches/0001-gates-workflow-contract-fix.patch` with workflow-scoped credentials, then re-run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) and the full pinned gate if desired. **If/when authorized to resume research:** obtain explicit authorization for one paid/PIT data gap (commodity futures per-contract roll/contango term structure, crypto perpetual funding rates, or historical options chain/GEX) and run the smallest decisive pre-registered test for that single mechanism. Do **not** invent a free-data H183 or run another exhaustion-only discovery cycle.

**Constraints:** no gate weakening; no published/frozen artifact, verdict, threshold, or frozen number modified; no commit/push of `.github/workflows/**`; `src/qtr` changes require 100% coverage.
