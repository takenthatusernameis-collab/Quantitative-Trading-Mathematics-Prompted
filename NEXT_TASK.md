# NEXT_TASK.md

## Current state (2026-11-13, Cycle 106)

`tests/test_gates_workflow.py` is **red on origin/main by design** — it is the
only failing test file in the suite (AGENTS.md line 33). The full suite is
otherwise green: **3,743 passed, 51 skipped, 7 failed** (the 7 = the gates
workflow file). `src/qtr` coverage **100%**, ruff clean.

The prior agent's task — the read-only orphan audit — is **complete and
corrected** this session: the 528 orphans now reconcile to an exact,
machine-checked partition (see `REPRODUCIBILITY_AUDIT_REPORT.md` §3 and
`tests/test_reproducibility_audit.py::test_orphan_categorization_reconciles_to_backlog`).

---

## Maintainer action (unchanged; workflow scope required)

Apply the already-staged patch and land it:

```bash
git apply patches/0001-gates-workflow-contract-fix.patch
git commit -am "fix(ci): satisfy gates workflow contract"
git push origin main
```

Expected result: `tests/test_gates_workflow.py` → **7 passed** (was 7 failed),
making the full suite green. Do not modify or weaken the test; the patch only
changes `.github/workflows/gates.yml`.

`.github/workflows/**` is maintainer-managed and agent-unreachable (AGENTS.md
lines 31-32): it is restored from `origin/main` after every session and the
repository GitHub App token has no `workflows` permission, so an agent commit of
a workflow change cannot persist.

---

## One precise next task (next agent): backfill the 140 missing artifact sidecars

**Evidence.** `tests/test_reproducibility_audit.py::test_artifact_meta_files_match_recorded_backlog`
pins `missing_meta_files = 140` (see `REPRODUCIBILITY_BASELINE`). Recomputed
2026-11-13: 140 artifacts that exist on disk have no
`.experiments/<artifact_name>.meta.json` sidecar. Breakdown: 118 JSON + 22
parquet; by name prefix `summary` 93, `equity` 21, `stats` 21, `metadata` 4,
`results` 1.

**Why now.** These artifacts were logged via `ExperimentTracker.log_artifact(...,
metadata=None)` (`src/qtr/tracking/experiment.py:150` only writes a sidecar when
`metadata` is truthy), so no sidecar was ever produced. The sidecar path is
`.experiments/<artifact_name>.meta.json` (tracker `log_dir` is `.experiments`).
`REPRODUCIBILITY_AUDIT_REPORT.md` §"Recommended Remediation" item 5 sanctions
this backfill.

**Task.** Write a one-off remediation script (place under `scripts/` so the CI
ruff targets cover it) that, for each of the 140 artifacts, derives a sidecar
and writes it to `.experiments/<artifact_name>.meta.json`:

- parquet → `{"shape": [...], "columns": [...], "dtypes": {...}, "index_type": "..."}` (mirror `log_dataframe` at `experiment.py:168-176`);
- JSON → `{"top_level_keys": [...], "top_level_types": {...}}`.

Then lower `REPRODUCIBILITY_BASELINE["missing_meta_files"]` to the new count and
update the report's §4 count in the same change (the ratchet fails on a silent
change in either direction).

**Verify.** `python -m pytest tests/test_reproducibility_audit.py -q` (all
backlog tests, including the sidecar one, must pass at the new baseline);
`python -m ruff check scripts tests`; `python -m ruff format --check scripts
tests`. Confirm no `src/qtr`, gate, frozen number, or published artifact is
touched. Do not commit/push unless explicitly requested.

**Constraints / rejected alternatives.**
- Do **not** change `log_artifact` to always write a sidecar: that alters runtime
  behavior, needs the full `src/qtr` gates (`pytest -q -W error`, 100% branch
  coverage), and does not fix the historical 140.
- Do **not** delete any artifact to make the count drop.
- The 25 hash-exact-missing artifacts (`missing_files`, `REPRODUCIBILITY_RESTORATION_PLAN.md`)
  have **no on-disk source** (cross-basename scan found 0), so they need a
  re-run and are data-blocked offline; do not attempt them in the same change.