# HANDOFF — current session (2026-11-14)

## What changed
- No repository code, test, artifact, gate, frozen number, or workflow file modified. Working tree clean at HEAD `3c083db`; no commit/push performed.

## What was actually verified
- `python -m pytest -q tests/test_gates_workflow.py` → **7 failed** (expected; contract drift vs committed `.github/workflows/gates.yml`, maintainer-gated).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → **applies cleanly**.
- `python -m pytest -q tests/test_reproducibility_audit.py tests/test_experiment_lineage_report.py` → **12 passed** (0.25s). Baseline unchanged: `missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=0`; lineage total pinned at 173.
- `python -m ruff check src tests run_*.py scripts` → **All checks passed**.
- `python -m ruff format --check src tests run_*.py scripts` → **335 files already formatted**.
- `python scripts/backtest_perf_regression_gate.py` → **PASSED** (0.413s, limit 5s).
- `grep -rn "TODO\|FIXME\|XXX" src/qtr` → no matches. No evidenced `src/qtr` defect identified.

## What remains unresolved
1. **Maintainer-only:** apply `patches/0001-gates-workflow-contract-fix.patch` to `.github/workflows/gates.yml` and push with workflow-scoped credentials to clear the 7 workflow-contract tests. Agent cannot modify/persist `.github/workflows/**`.
2. **Research queue (free/public PIT data) exhausted:** H1–H182 executed/rejected (NEW_FAMILY_RESEARCH_REGISTER / directive §6); remaining repo-new mechanisms are data-blocked/underpowered or mechanism-adjacent. No honest free-data H183 pre-registrable.
3. **H182 lineage gap:** NF-20261110-08 (insider net-buy, REJECTED) not recorded in `experiments.jsonl` / `EXPERIMENT_LINEAGE_REPORT.md`; requires authorized corpus+baseline update (sidecars, pinned counts 173→174, audit baseline) or audit-scope extension to `.experiments/nf_runs/`.

## Approaches already failed / must not be repeated
- Re-running exhaustion-only discovery without new data authorization or directive §6 shift.
- Editing `.github/workflows/**` from agent, weakening `tests/test_gates_workflow.py`, or relaxing coverage/frozen-contract gates.
- Using delisted/spliced/unavailable free series as PIT-valid data (OVX, VIX9D, ^RVX; spliced `=F` carry; no free crypto funding history).
- Mass edits to runners/tests/gates/frozen artifacts to force green; reproducibility backlog (528 orphans, 197 missing, 11 mismatches) is baseline-frozen where constrained.
- Appending H182 to lineage without sidecars and coordinated baseline/pinned-test updates.
- Speculative `src/qtr` changes without an evidenced defect.

## One precise next task
**Maintainer (preferred):** apply/push `patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then verify `python -m pytest -q tests/test_gates_workflow.py` → 7 passed. **Authorized research alternative:** secure one paid/PIT data gap (commodity per-contract roll/contango, crypto perpetual funding, or historical options chain/GEX) and run the smallest decisive pre-registered test for that mechanism (no invented free-data H183). **Authorized bookkeeping alternative:** close the H182 lineage gap by adding NF-20261110-08 to `experiments.jsonl` with `.meta.json` sidecars and re-deriving lineage/audit baselines and pinned tests.

**Constraints:** preserve gates/contracts/100% `src/qtr` coverage; do not alter published/frozen artifacts or thresholds except deliberate authorized corpus/baseline update; no workflow commit from agent.
