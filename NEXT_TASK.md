# NEXT_TASK.md — Suite green (Cycle 104); lineage-report reproducibility pinned

## Current status (re-verified from scratch this session)
- `PYTHONPATH=src python3 -m pytest -q` → **3738 passed, 51 skipped, 0 failed** (620s).
- `python3 -m ruff check src tests run_*.py` → All checks passed.
- `python3 -m ruff format --check src tests run_*.py` → 322 files already formatted.
- `tests/test_experiment_lineage_report.py` → 5 passed (0.06s).
- `src/qtr` unchanged this session; prior verified coverage 100.00% (1211 stmts / 422 branches).

## What changed this session (test only; no src/qtr, runner, gate, or frozen artifact)
- `tests/test_experiment_lineage_report.py` (new): pins `EXPERIMENT_LINEAGE_REPORT.md`
  reproducibility by regenerating the report **in memory** (to a temp file) and
  asserting the non-timestamp content equals the committed report. Five guards:
  `test_committed_report_exists`, `test_generator_is_importable`,
  `test_report_reproduces_committed_content`, `test_report_total_experiment_count`
  (173), `test_report_category_summary_matches_pinned_inventory` (10 rows).
  Negative control verified: mutating a category row fails the test; the
  committed report is restored byte-identical (md5 `f2aaa00c…`) after.

## Unresolved / blocked
- **Artifact restoration apply (needs explicit human authorization):** planner reports
  Recoverable 0 / Excluded 172 / Unrecoverable 25, matching the committed
  `REPRODUCIBILITY_RESTORATION_PLAN.md/csv` and `tests/test_artifact_restoration_plan.py`.
  `--apply` is a **no-op** and must not be run. Baseline in
  `tests/test_reproducibility_audit.py`: `missing_files=197`, `hash_mismatches=11`,
  `orphaned_files=528`, `missing_meta_files=140`.
- **H182 discovery (needs data/authorization):** free-data PIT family discovery is
  exhausted at H181 (Cycle 96); carry/insider/earnings/options/breakeven candidates are
  data-blocked; remaining candidates are adjacency- or power-blocked.
- **New pins are an intentional ratchet:** running experiments that change
  `.experiments/experiments.jsonl` (adding/removing records, flipping a verdict)
  will fail `test_report_reproduces_committed_content` and the summary pins until
  `EXPERIMENT_LINEAGE_REPORT.md` is regenerated deliberately and the pins updated
  (same pattern as `test_experiment_artifact_schema.py`).

## One precise next task
**All unpinned generated inventories are now pinned.** The remaining authorized
progress paths are:
1. **Stress-test frozen-contract gates** against edge cases (NaN prices, extreme
   leverage, zero-volume, look-ahead boundaries) — listed as remaining audit work
   in `HANDOFF_SESSION_END.md` §"What Remains Unresolved".
2. **CI/CD hardening** — performance regression gate (e.g., fail if 100-symbol
   backtest > 5s), per `HANDOFF_SESSION_END.md`.
3. **Artifact restoration authorization** or an authorized PIT/free data source for
   a materially new mechanism (H182).

If no further doc-pinning work is authorized, the only remaining progress requires
restoration authorization or an authorized PIT/free data source for a materially new
mechanism.

## Failed approaches / do not repeat
- Do not trust committed doc counts without re-running the producing check.
- Do not run `scripts/plan_artifact_restoration.py --apply` (no-op; needs authorization).
- Do not invent/execute H182 from exhausted/adjacent families or blocked data.
- Do not commit/push unless requested.

## Constraints
- `src/qtr` unchanged unless evidenced defect (then rerun pinned full gates). No
  frozen/certified/published artifact, verdict, threshold, or gate weakening. No
  commit/push unless requested. Free/public data only.

(End of file - total 55 lines)