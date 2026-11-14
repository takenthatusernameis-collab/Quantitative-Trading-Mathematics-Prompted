# NEXT_TASK.md

## Latest session (2026-11-14, this session) — baseline re-verification; no actionable agent fix

### What changed
- No code, test, artifact, gate, frozen number, or workflow change. Working tree clean at HEAD `3c083db`. No commit/push.

### What was actually verified (own evidence)
- `python -m pytest -q tests/test_gates_workflow.py` — **7 failed** (expected maintainer-gated contract drift vs committed `.github/workflows/gates.yml`).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` — **applies cleanly**; patch asserts (per `tests/test_gates_workflow.py`) match the patched workflow (scripts path triggers, scripts in ruff targets, editable install in both jobs, perf regression gate step in `research_gates`).
- `python -m pytest -q tests/test_reproducibility_audit.py tests/test_experiment_lineage_report.py` — **12 passed** (0.25s). Reproducibility baseline unchanged (`missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=0`); lineage pinned at 173 experiments.
- `python -m ruff check src tests run_*.py scripts` — **All checks passed**.
- `python -m ruff format --check src tests run_*.py scripts` — **335 files already formatted**.
- `python scripts/backtest_perf_regression_gate.py` — **PASSED** (100 symbols x 252 bars -> 0.413s, limit 5s, 10.7MB peak, 13668 trades).
- `grep -rn "TODO\|FIXME\|XXX" src/qtr` — none; `src/qtr` clean (no evidenced defect surfaced). Prior documented state: `src/qtr` 100% covered, full suite otherwise green except maintainer-gated workflow block.

### What remains unresolved
1. **Maintainer-only (CI contract):** `.github/workflows/gates.yml` not yet updated; `tests/test_gates_workflow.py` red until maintainer applies patch with workflow-scoped credentials. Agent cannot land `.github/workflows/**` (restored from `origin/main` each session; token lacks `workflows` scope).
2. **Research queue exhausted under free/public PIT data:** per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6 and `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycles 96/116), H1–H182 executed/rejected; no repo-new mechanism pre-registerable without a data-gap resolution. Do not invent a free-data H183.
3. **H182 lineage gap:** NF-20261110-08 (insider net-buy, REJECTED, Cycle 115) absent from `experiments.jsonl` / `EXPERIMENT_LINEAGE_REPORT.md`. Closing it requires authorization to append record + `.meta.json` sidecars and re-derive audit/lineage baselines (pinned counts: total 173→174, category summary, reproducibility baseline) or to extend audit corpus scope to `.experiments/nf_runs/`.

### Approaches already tried and why they should not be repeated
- Do not re-run exhaustion-only discovery without new data authorization or a §6 shift (Cycles 96/116/120 pattern).
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or alter coverage/frozen-contract gates.
- Do not treat delisted/spliced-continuous/unavailable free series as valid PIT data (OVX, VIX9D, ^RVX; spliced `=F` carry proxy; no free crypto funding history).
- Do not mass-edit runners/tests/gates/frozen artifacts to chase green; 528 orphans and reproducibility backlog items are baseline-frozen where constrained.
- Do not append H182 to `experiments.jsonl` without sidecars + coordinated baseline/pinned-test updates (ratchet will fail).
- Do not make speculative `src/qtr` changes absent an evidenced defect (100% coverage, ruff clean).

### One precise next task
**Maintainer action (preferred, unblocks CI):** apply and push `patches/0001-gates-workflow-contract-fix.patch` with workflow-scoped credentials, then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on `origin/main`. **If research is explicitly authorized:** obtain authorization for one paid/PIT data gap (commodity futures per-contract roll/contango term structure, crypto perpetual funding rates, or historical options chain/GEX) and run the smallest decisive pre-registered test for that single mechanism. **Alternative (authorized bookkeeping):** close the H182 lineage gap by appending NF-20261110-08 to `experiments.jsonl` with `.meta.json` sidecars and re-deriving `REPRODUCIBILITY_AUDIT_REPORT` baseline plus pinned expectations in `tests/test_experiment_lineage_report.py` and `tests/test_reproducibility_audit.py`.

**Constraints:** no gate weakening; no modification of published/frozen artifacts, verdicts, thresholds, or frozen numbers except deliberate, authorized corpus/baseline update above; no commit/push of `.github/workflows/**`; any `src/qtr` change must preserve 100% coverage and pass ruff/suite.
