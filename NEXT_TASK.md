# NEXT_TASK.md

## Latest session (2026-11-14T04:50Z, Cycle 106) — sidecar-schema repair committed; full suite re-verified

The previous "backfill the 140 missing sidecars" task is **complete** (done 2026-11-13,
committed as `62df672` together with the schema-repair follow-up). This file's
remaining numbered steps below are historical; the live next task is at the bottom.

### What was verified this session (Cycle 106, own evidence)

- Full suite at HEAD `62df672` (the sidecar-schema repair commit): **3,745 passed,
  51 skipped, 7 failed** (430s). The 7 are exclusively
  `tests/test_gates_workflow.py`, unchanged from Cycle 105. The +1 vs Cycle 105's
  3,744 is `test_sidecar_schema_contract.py`, added in `62df672` — the suite had
  never been re-run after that commit until now.
- `src/qtr` coverage — **100%** (1211 stmts / 422 branches / 0 miss).
- `tests/test_sidecar_schema_contract.py` — 1 passed. Re-derived all **528**
  committed `.meta.json` sidecars: 424 parquet-schema + 104 json-keys; **0** other
  shapes, **0** unparseable.
- `tests/test_reproducibility_audit.py` — 7 passed (backlog 197 / 11 / 528 / 0 unchanged).
- `scripts/backtest_perf_regression_gate.py` — green on this host (0.406s, limit 5s).
- `ruff check`/`format --check` over `src tests run_*.py scripts` — clean, 327 files.
- **Maintainer patch re-verified** in a clean checkout: `git apply --check` succeeds,
  patched `gates.yml` satisfies all 7 contract assertions, `pytest
  tests/test_gates_workflow.py` -> 7 passed. With it applied the full suite would be
  **3,752 passed / 51 skipped / 0 failed**. Agent cannot land it (no `workflows`
  token; `.github/scripts/kilo-controller.sh` restores `.github/workflows/**` from
  `origin/main` after every session).

### What changed (annotation only, no source/test/artifact change)

- `patches/0001-gates-workflow-contract-fix.patch` — corrected the stale
  "HEAD d542019" evidence line. That object does not exist in this repository
  (full history is 6 empty-message commits). Patch content is byte-identical;
  only the prose header was refreshed with the Cycle 106 re-verification.
- `HANDOFF.md` — added the Cycle 106 re-verification banner and updated the
  "one precise next task" section.

## Prior session (2026-11-13T22:5xZ) — fixed caller-dict mutation in `log_dataframe`

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

**Maintainer-only: apply `patches/0001-gates-workflow-contract-fix.patch` to
turn the 7 red `tests/test_gates_workflow.py` failures green.** Re-verified
this cycle (Cycle 106) in a clean checkout: the patch applies, the patched
`gates.yml` satisfies all 7 contract assertions, and the new CI step
`scripts/backtest_perf_regression_gate.py` passes on this host (0.406s, limit
5s). Agent cannot land it (no `workflows` token permission;
`.github/scripts/kilo-controller.sh` restores `.github/workflows/**` from
`origin/main` after every session, and the staging filter excludes those
paths).

If the maintainer applies it, the full suite goes green at **3,752 passed /
51 skipped / 0 failed** and the CI `scripts/**` path filter, editable install,
and perf-gate step become live. No agent-side follow-up is needed.

**Otherwise (agent path):** the only remaining open item is **H182 selection**:
per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6 and
`NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96, the free-data point-in-time
strategy-family queue is exhausted (H1–H181 executed/rejected; commodity carry
data-blocked; insider/earnings/options PIT unavailable without paid services).
Selecting H182 requires resolving a data gap under explicit authorization.
Absent that, conclude free-data family discovery is exhausted and shift to
auditing/infrastructure rather than inventing candidates.

**Constraints:** additive sidecars only; do not delete/move artifacts; do not
touch published/frozen numbers, gates, or `src/qtr` unless an evidenced defect
requires it; no commit/push of `.github/workflows/**`.