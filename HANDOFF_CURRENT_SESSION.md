# Handoff — Current Session (Cycle 151, 2026-11-16)

## What changed
- **`src/qtr/tracking/experiment.py`** — `Experiment.record_artifact` now resolves the caller-supplied `filename` against the resolved `artifact_dir` and rejects names that escape it (`../evil.txt`, absolute paths) with `ValueError` ("pass a plain filename, not a path"). Plain in-directory filenames and existing behavior (DataFrame dedup/serialization) unchanged. Reproduced before fix: traversal wrote outside `artifact_dir`.
- **`tests/test_experiment_tracking.py`** — added `test_record_artifact_rejects_path_traversal` and `test_record_artifact_path_traversal_pre_fix_wrote_outside` (+2). Total 30 tests in file.
- **`NEXT_TASK.md`** — updated to Cycle 151 handoff, verification evidence, and next precise task.

## What was actually verified (own evidence)
- Repro before fix: `Experiment(...).record_artifact('../evil.txt','hi')` wrote `/.../<base>/x/evil.txt` outside `artifact_dir` (path escaped). After fix: raises `ValueError`; in-directory `ok.txt` and existing cases unchanged.
- `python -m pytest -q tests/test_experiment_tracking.py -W error` → **30 passed**.
- `python -m ruff check src tests run_*.py scripts` → clean. `python -m ruff format --check src tests run_*.py scripts` → **336 files already formatted**.
- `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.308s < 5s, 13668 trades).
- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py` (345.56s) → **3952 passed, 48 skipped, 0 failed**, `src/qtr` coverage **100.00%** (1550 stmts / 558 branches / 0 miss; `tracking/experiment.py` 225/52).
- `python -m pytest -q tests/test_gates_workflow.py` → **7 failed** (unchanged, maintainer-gated; fix `patches/0001-gates-workflow-contract-fix.patch`).

## What remains unresolved
- Maintainer-only: apply/push `patches/0001-gates-workflow-contract-fix.patch` to fix `.github/workflows/gates.yml` and make `tests/test_gates_workflow.py` pass on `origin/main`.
- Research: H1–H182 exhausted under free/public PIT data; no honest H183 without new authorized data.
- Reproducibility backlog baseline-frozen: `missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=0`.

## Approaches already failed / do not repeat
- Do not re-audit pinned defects (cache index/column normalization+dedup, `max_leverage`/`initial_capital` boundaries, engine/fetcher/tracker duplicate handling, `record_artifact` DataFrame dedupe, `load_metadata` non-dict, `record_artifact` path traversal).
- Do not edit `.github/workflows/**`, weaken tests/gates/frozen contracts, or invent H183 / parameter-only "new families".

## One precise next task
- **Maintainer:** apply/push `patches/0001-gates-workflow-contract-fix.patch`; run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
- **Agent (new evidence only):** hunt a reproduced, runner-reachable `src/qtr` defect on public paths not yet closed (fuzz/boundary probes: n=0/1/2, empty, duplicate labels, non-finite, corrupt/partial state, untrusted names). If code changes, verify full pinned suite (excluding maintainer-gated workflow tests), ruff check/format, and perf gate.
