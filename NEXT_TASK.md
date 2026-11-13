# NEXT_TASK.md — CI workflow contract pinned; full suite green

## Current status (re-verified this session, 2026-11-13T02:55Z)
- `python -m pytest -q -W error` → **3748 passed, 51 skipped, 0 failed** (618s).
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` → **100% coverage** (1211 stmts / 422 branches / 0 miss).
- `python -m ruff check src tests run_*.py scripts` → All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` → 327 files already formatted.
- `python scripts/backtest_perf_regression_gate.py` → PERF GATE PASSED (0.866s, limit 5s).
- `.github/workflows/gates.yml` parses OK.

## What changed this session (CI/CD hardening — contract test → workflow)
The prior session wrote `tests/test_gates_workflow.py` (commit `36148b2`) asserting that
`.github/workflows/gates.yml` lints `scripts/**` and triggers on `scripts/**` edits, but the
committed YAML did **not** yet satisfy those assertions — the test failed 5/5. This session
made the YAML match the contract (the test is the spec; the workflow was stale, not the test):

- `.github/workflows/gates.yml`:
  - `push.paths` and `pull_request.paths` now include `'scripts/**'`.
  - `lint` job: `Ruff check` → `python -m ruff check src tests run_*.py scripts`;
    `Ruff format check` → `python -m ruff format --check src tests run_*.py scripts`.
  - `research_gates` job: added `python scripts/backtest_perf_regression_gate.py` step before
    the pytest step (the perf gate now runs in CI).
- `tests/test_gates_workflow.py` → **5 passed** (was 5 failed). No test code changed.

No source changes to `scripts/`, `src/qtr`, or `tests/` were required — all were already clean.

## Unresolved / blocked
- **Artifact restoration apply (needs explicit human authorization):** `--apply` is a no-op on this checkout; `--dry-run` → Recoverable 0 / Excluded 172 / Unrecoverable 25. Baseline in `tests/test_reproducibility_audit.py`: `missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=140`.
- **H182 discovery (needs data/authorization):** free-data PIT family discovery is exhausted at H181 (Cycle 96, `NEW_FAMILY_RESEARCH_REGISTER.md`, `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6). Carry/insider/earnings/options/breakeven candidates are data-blocked; remaining candidates adjacency- or power-blocked. Do not invent/execute H182 from exhausted/adjacent families or blocked data.
- **All generated inventories are pinned.** Running experiments that change `.experiments/experiments.jsonl` will fail `test_report_reproduces_committed_content` and summary pins until `EXPERIMENT_LINEAGE_REPORT.md` is regenerated deliberately and pins updated.

## One precise next task
**None bounded and safe remaining.** The CI/CD hardening line is complete and verified end-to-end
(the contract test pins the workflow, the workflow satisfies the contract, the perf gate runs and
passes, and the full suite + coverage + lint + format are all green). The only open research item
is H182, which is data-blocked and requires explicit human authorization per
`STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6.

## Failed approaches / do not repeat
- Do not trust committed doc counts without re-running the producing check.
- Do not run `scripts/plan_artifact_restoration.py --apply` (no-op; needs authorization).
- Do not invent/execute H182 from exhausted/adjacent families or blocked data.
- Do not time a performance gate with `tracemalloc` active.
- Do not commit/push unless requested.

## Constraints
- `src/qtr` unchanged unless evidenced defect (then rerun pinned full gates). No frozen/certified/published artifact, verdict, threshold, or gate weakening. No commit/push unless requested. Free/public data only.