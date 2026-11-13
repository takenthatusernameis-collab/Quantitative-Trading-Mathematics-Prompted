# NEXT_TASK.md — CI workflow contract pinned; full-suite verification remains

## Current status (re-verified this session)
- `python3 -m pytest -q -W error tests/test_gates_workflow.py` → **5 passed**.
- `python3 -m ruff check src tests run_*.py scripts` → All checks passed.
- `python3 -m ruff format --check src tests run_*.py scripts` → 327 files already formatted.
- `python3 -m pytest -q -W error tests/test_backtest_perf_regression_gate.py` → **5 passed**.
- `python3 scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.806s, limit 5s, 10.7MB peak, 13668 trades).

## What changed this session (CI/CD hardening)
- `.github/workflows/gates.yml`: lint job now runs `python -m ruff check src tests run_*.py scripts` and `python -m ruff format --check src tests run_*.py scripts`; push/pull_request `paths` now include `scripts/**`; `research_gates` job now runs `python scripts/backtest_perf_regression_gate.py`. This makes the previously written `tests/test_gates_workflow.py` contract pass (it previously failed 5/5 against the stale workflow).
- AGENTS.md already documented `scripts` in the lint targets; no change needed there.
- `src/qtr` unchanged. No commit/push performed.

## Unresolved / blocked
- **Artifact restoration apply (needs explicit human authorization):** `--apply` is a no-op on this checkout; `--dry-run` → Recoverable 0 / Excluded 172 / Unrecoverable 25. Baseline in `tests/test_reproducibility_audit.py`: `missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=140`.
- **H182 discovery (needs data/authorization):** free-data PIT family discovery is exhausted at H181 (Cycle 96, `NEW_FAMILY_RESEARCH_REGISTER.md`, `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6). Do not invent/execute H182 from exhausted/adjacent families or blocked data.
- **All generated inventories are pinned.** Running experiments that change `.experiments/experiments.jsonl` will fail `test_report_reproduces_committed_content` and summary pins until `EXPERIMENT_LINEAGE_REPORT.md` is regenerated deliberately and pins updated.

## One precise next task
**Run the full pinned test suite to confirm the CI workflow change didn't regress anything:**
`python3 -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`
Expected: ~3743 passed, 51 skipped, 0 failed, `src/qtr` coverage 100.00%. This is the same command `.github/workflows/gates.yml` now runs in CI, so it validates the workflow end-to-end. If it passes, the session is clean; no code changes expected. Do not commit/push unless requested.

## Failed approaches / do not repeat
- Do not run `scripts/plan_artifact_restoration.py --apply` (no-op; needs authorization).
- Do not invent/execute H182 from exhausted/adjacent families or blocked data.
- Do not time a performance gate with `tracemalloc` active.
- Do not commit/push unless requested.

## Constraints
- `src/qtr` unchanged unless evidenced defect (then rerun pinned full gates). No frozen/certified/published artifact, verdict, threshold, or gate weakening. No commit/push unless requested. Free/public data only.
