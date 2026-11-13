# NEXT_TASK.md — `scripts/` lint coverage wired; perf/repro discovery remains blocked

## Current status (re-verified this session)
- `python3 -m pytest -q -W error tests/test_backtest_perf_regression_gate.py` → **5 passed**.
- `python3 -m ruff check src tests run_*.py scripts` → All checks passed.
- `python3 -m ruff format --check src tests run_*.py scripts` → 326 files already formatted.
- `.github/workflows/gates.yml` parses (`yaml.safe_load`) OK.

## What changed this session (CI/CD hardening)
- `.github/workflows/gates.yml`: lint job and `scripts/**` path triggers now include `scripts/` so all three scripts (`scripts/backtest_perf_regression_gate.py`, `scripts/generate_experiment_lineage_report.py`, `scripts/plan_artifact_restoration.py`) are linted/format-checked in CI. No source changes to scripts or `src/qtr` were required (all already clean).

## Unresolved / blocked
- **Artifact restoration apply (needs explicit human authorization):** `--apply` is a no-op on this checkout; `--dry-run` → Recoverable 0 / Excluded 172 / Unrecoverable 25. Baseline in `tests/test_reproducibility_audit.py`: `missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=140`.
- **H182 discovery (needs data/authorization):** free-data PIT family discovery is exhausted at H181 (Cycle 96, `NEW_FAMILY_RESEARCH_REGISTER.md`, `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6). Carry/insider/earnings/options/breakeven candidates are data-blocked; remaining candidates adjacency- or power-blocked. Do not invent/execute H182 from exhausted/adjacent families or blocked data.
- **All generated inventories are pinned.** Running experiments that change `.experiments/experiments.jsonl` will fail `test_report_reproduces_committed_content` and summary pins until `EXPERIMENT_LINEAGE_REPORT.md` is regenerated deliberately and pins updated.

## One precise next task
**Verify and, if necessary, pin the new CI workflow behavior with a minimal contract test.** There is no existing test asserting that `.github/workflows/gates.yml` lint steps include `scripts` or that `scripts/**` is in path filters (unlike other pinned gates). Add a small, focused test (e.g. in `tests/test_gates_workflow.py` or alongside perf-gate tests) that loads the workflow YAML and asserts: (1) `lint` job runs `python -m ruff check src tests run_*.py scripts` and `python -m ruff format --check src tests run_*.py scripts`, and (2) push/pull_request `paths` include `scripts/**`. Keep it read-only and deterministic. After adding, run that test and `python -m pytest -q -W error tests/test_backtest_perf_regression_gate.py`.

Alternative (blocked on human authorization): obtain an authorized free/PIT data source to unblock H182, or authorize artifact-restoration apply (currently a no-op).

## Failed approaches / do not repeat
- Do not trust committed doc counts without re-running the producing check.
- Do not run `scripts/plan_artifact_restoration.py --apply` (no-op; needs authorization).
- Do not invent/execute H182 from exhausted/adjacent families or blocked data.
- Do not time a performance gate with `tracemalloc` active.
- Do not commit/push unless requested.

## Constraints
- `src/qtr` unchanged unless evidenced defect (then rerun pinned full gates). No frozen/certified/published artifact, verdict, threshold, or gate weakening. No commit/push unless requested. Free/public data only.