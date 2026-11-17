# Next task (Cycle 190, 2026-11-17)

## What changed this session
- No source, test, gate, artifact, sidecar, hash, frozen-number, or workflow change. Working tree clean at start (HEAD `eb88fca`); only handoff docs updated with own verification.

## What was actually verified (own evidence, 2026-11-17)
- `python -m ruff check src tests run_*.py scripts` → All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` → **336 files already formatted**.
- `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.299s < 5s, 10.7MB, 13668 trades).
- `python -m pytest -q tests/test_gates_workflow.py` → **7 failed** (unchanged, maintainer-gated; covered by `patches/0001-gates-workflow-contract-fix.patch`).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → exit 0 (applies cleanly).
- `grep -rn "TODO|FIXME|XXX|HACK" src/qtr` → no matches.
- No new reproduced defect found in `src/qtr`/runners/scripts this session.

## What remains unresolved
- **Maintainer-gated (agent-unreachable):** apply/push `patches/0001-gates-workflow-contract-fix.patch` with `workflows`-scoped credentials (`.github/scripts/kilo-controller.sh` restores `.github/workflows/**` from `origin/main`; no agent `workflows` token). After push: `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
- **H182 selection blocked:** free-data point-in-time strategy-family queue exhausted (H1–H181 rejected/recorded, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96). No honest pre-registrable candidate without new authorized data. Do not invent candidates or treat parameter/timeframe/universe variations as new mechanism families.
- **Reproducibility backlog (frozen):** missing_files=197, hash_mismatches=11, orphaned_files=528, missing_meta_files=0.

## One precise next task
**Maintainer:** apply and push `patches/0001-gates-workflow-contract-fix.patch`, then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
**Agent (next session):** no agent-assigned code change. Only if a NEW reproduced, runner-reachable defect appears in `src/qtr`/runners/corpus metadata — fix with the smallest verifiable change and rerun focused tests, `python -m ruff check src tests run_*.py scripts`, `python -m ruff format --check src tests run_*.py scripts`, and `python scripts/backtest_perf_regression_gate.py` with own evidence; otherwise re-verify baseline and make no code change.

## Approaches already tried and why they should not be repeated
- Do not re-review the seven `src/qtr` modules for pinned defect classes without NEW evidence (exhaustively reviewed through Cycle 186; no new defect).
- Do not edit `.github/workflows/**` or weaken `tests/test_gates_workflow.py` — maintainer-gated contract; fix is the workflow patch.
- Do not invent a free-data H182 or treat parameter/timeframe/universe variants as new mechanism families.
- Do not trust handoff pass/fail/coverage counts — re-run gates.
