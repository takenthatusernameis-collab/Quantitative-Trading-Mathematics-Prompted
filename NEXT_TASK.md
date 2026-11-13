# NEXT_TASK.md

## Latest session (2026-11-13T22:5xZ) — fixed caller-dict mutation in `log_dataframe`

### What changed (this session)

- `src/qtr/tracking/experiment.py` — `ExperimentTracker.log_dataframe` no longer
  mutates the caller's `metadata` dict. It now copies it (`dict(metadata) if
  metadata else {}`) before adding the frame schema keys
  (`shape`/`columns`/`dtypes`/`index_type`). The sidecar written to disk is
  **byte-for-byte identical** to before; only the in-place side effect on the
  caller's dict is removed.
- `tests/test_experiment_tracker.py` — added
  `test_log_dataframe_does_not_mutate_caller_metadata` (regression test; calls
  `log_dataframe` twice with the same caller dict and asserts it is unchanged).

Reproduced before the fix: after `log_dataframe("a", df, metadata=caller)`,
`caller` gained `shape`/`columns`/`dtypes`/`index_type`; a second call overwrote
them. A caller that reuses one metadata dict across logs (e.g. then passes it to
`log_artifact`) would leak a DataFrame's schema into a non-DataFrame artifact's
sidecar.

### What was actually verified (this session, own evidence)

- `python -m pytest tests/test_experiment_tracker.py -q` → **24 passed**.
- Focused reproducibility/tracker suites
  (`test_experiment_tracker`, `test_experiment_tracking`,
  `test_reproducibility_audit`, `test_experiment_artifact_schema`,
  `test_gate_vacuity_contract`, `test_h56_stats_json_echoes`) → **342 passed**.
- Full suite `python -m pytest -q` → **3744 passed, 51 skipped, 7 failed**
  (the 7 = `tests/test_gates_workflow.py` only; unchanged maintainer-gated
  contract). Baseline before this change was 3743 passed; +1 is the new test.
- `src/qtr/tracking/experiment.py` coverage via
  `pytest tests/test_experiment_tracker.py --cov=qtr --cov-branch` → **100%**
  (181 stmts / 38 branch / 0 miss), so the new `dict(metadata)` branch and the
  `{}` branch are both exercised.
- `python -m ruff check src tests run_*.py scripts` → clean;
  `python -m ruff format --check ...` → 327 files already formatted.
- `git diff --stat` → only the two files above changed. No published/frozen
  artifact, verdict, threshold, sidecar, or experiment record modified.

### What remains unresolved

1. **Maintainer-only (unchanged, still blocked).** `tests/test_gates_workflow.py`
   is red on `origin/main` by design. The fix is
   `patches/0001-gates-workflow-contract-fix.patch`; `.github/workflows/**` is
   agent-unreachable (restored from `origin/main` each session, excluded from
   staging, no `workflows` token permission). Landing it requires a maintainer
   with workflow scope:
   ```bash
   git apply patches/0001-gates-workflow-contract-fix.patch
   git commit -am "fix(ci): satisfy gates workflow contract"
   git push origin main
   ```
2. **Full coverage gate not run end-to-end this session.** The targeted module
   is 100%, but the whole-suite `--cov=qtr --cov-branch` run (the documented
   gate) was not re-executed; run it before relying on the 100% claim.
3. **Root cause of the 11 hash mismatches is not fixed.** Audit
   `REPRODUCIBILITY_AUDIT_REPORT.md` §2: 8 rows are duplicate same-path
   `param_grid_results` writes inside one run (`log_dataframe` called twice with
   the same `name` → second overwrites the first on disk, both stay recorded).
   Fixing this changes record semantics and touches the frozen
   `REPRODUCIBILITY_BASELINE["hash_mismatches"]`; it is authorization-gated.

### Approaches already tried and why they failed (do not repeat blindly)

- The prior session's `NEXT_TASK` was the maintainer workflow patch; an agent
  cannot land it (see above). Do not re-attempt a workflow commit from an agent
  session.
- Do not mass-edit runners/tests/gates to force the suite green; frozen-contract
  drifts need per-contract evidence and authorization.
- Do not delete or move committed artifacts to reduce the 528-orphan backlog
  (committed user data; the shared-dir orphans are actively cited by tests).

## One precise next task

**Backfill the 140 missing artifact `.meta.json` sidecars, then lower the
ratchet.** This is remediation item 5 in `REPRODUCIBILITY_AUDIT_REPORT.md` and
is additive (no artifact or published number is overwritten).

Evidence (recomputed this session): `missing_meta_files = 140`
(118 `.json`, 22 `.parquet`; by basename: `summary.json` 93, `equity.parquet`
21, `stats.json` 21, `metadata.json` 4, `h14_results.parquet` 1).

Steps:
1. For each referenced artifact that exists on disk but lacks
   `.experiments/<artifact_name>.meta.json`, write a sidecar: JSON artifacts →
   `{"keys": [<top-level keys>]}` (or the existing metadata if the runner
   logged it); parquet artifacts → `{"shape": [...], "columns": [...],
   "dtypes": {...}, "index_type": "..."}` matching `log_dataframe`'s schema.
   Do **not** overwrite an existing sidecar.
2. Re-run `pytest tests/test_reproducibility_audit.py -q`. It will fail with
   `missing_meta_files backlog changed: <new> (recorded baseline 140)`.
3. Lower `REPRODUCIBILITY_BASELINE["missing_meta_files"]` in
   `tests/test_reproducibility_audit.py` to the new count and update
   `REPRODUCIBILITY_AUDIT_REPORT.md` §4 + the summary table in the same change
   (the ratchet requires the baseline and report to move together).
4. Verify: `pytest tests/test_reproducibility_audit.py -q` green, focused
   artifact suites green, `ruff check`/`format --check` clean, and the full
   `pytest -q -W error --cov=qtr --cov-branch` gate (expect 3744 passed, 51
   skipped, 7 failed = maintainer-gated `test_gates_workflow.py`).

**Constraints:** additive sidecars only; do not delete/move artifacts; do not
touch published/frozen numbers, gates, or `src/qtr` unless an evidenced defect
requires it; no commit/push of `.github/workflows/**`.