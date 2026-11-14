# NEXT_TASK.md

## Latest session (2026-11-14, Cycle 110) — full pinned gate re-verification; fix integrated, no further agent action needed

### What was verified this session (own evidence)

- Full pinned gate `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` (431s) — **3,746 passed / 51 skipped / 7 failed**. The count matches the Cycle 109 expectation exactly: Cycle 108's 3,745 + 1 for the new `test_log_dataframe_requires_experiment` test. The 7 failures are *exclusively* `tests/test_gates_workflow.py`, the known maintainer-gated contract block — unchanged from Cycle 108, no regression, no new failure.
- `src/qtr` coverage — **100%** (1213 stmts / 424 branches / 0 miss); coverage gate "Required test coverage of 100.0% reached."
- `python -m ruff check src tests run_*.py scripts` — all checks passed.
- `python -m ruff format --check src tests run_*.py scripts` — 329 files already formatted.
- `git status` — clean. No source/test/artifact/frozen-number change this session; the Cycle 109 fix (`src/qtr/tracking/experiment.py` guard + `tests/test_experiment_tracker.py` regression test) was already committed in prior cycle and is now confirmed integrated.

### Conclusion

The Cycle 109 `log_dataframe` no-experiment guard fix is integrated and green across the full pinned gate. **No further agent action is needed on the code.**

### One precise next task (unchanged, maintainer-only)

**Apply `patches/0001-gates-workflow-contract-fix.patch`** to turn the 7 red `tests/test_gates_workflow.py` failures green (re-verified applicable in Cycles 106–108; patched `gates.yml` satisfies all 7 assertions; `scripts/backtest_perf_regression_gate.py` passes on this host). Agent cannot land it (no `workflows` token; `.github/scripts/kilo-controller.sh` restores `.github/workflows/**` from `origin/main` each session). If applied, full suite goes green at **3,753 passed / 51 skipped / 0 failed**.

**Agent path (blocked unless authorized):** resolve the H182 data gap (free PIT commodity roll/contango for carry, or PIT insider/earnings/options data) and select H182 per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4/§6 and `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96. Absent authorization, conclude free-data family discovery is exhausted — do not invent an H182 candidate.

**Constraints:** `src/qtr` unchanged unless an evidenced defect requires it; no gate weakening; no published/frozen artifact, verdict, threshold, or frozen number modified; no commit/push of `.github/workflows/**`.

---

## Latest session (2026-11-14, Cycle 109) — real defect fix: `log_dataframe` no-experiment guard

The prior four cycles (105–108) were re-verification-only and produced no source change.
This cycle found and fixed an evidenced, bounded defect in `src/qtr`.

### The defect (reproduced before the fix)

`ExperimentTracker.log_dataframe` built the artifact directory with
`self.log_dir / "artifacts" / self.current_experiment.experiment_id` **before** any
"active experiment" guard. Calling it with no active experiment raised
`AttributeError: 'NoneType' object has no attribute 'experiment_id'` instead of the
`RuntimeError("No active experiment. Call start_experiment() first.")` that its sibling
methods (`log_metric`, `log_artifact`, `finish_experiment`) raise. `log_metric` and
`finish_experiment` already had requires-experiment tests; `log_dataframe` had none.

### What changed (minimal, additive)

- `src/qtr/tracking/experiment.py` — `log_dataframe` now raises the documented
  `RuntimeError` when `self.current_experiment is None`, before dereferencing it.
- `tests/test_experiment_tracker.py` — added
  `test_log_dataframe_requires_experiment` (mirrors `test_log_metric_requires_experiment`).

### What was actually verified (this session, own evidence)

- Reproduced before the fix: `log_dataframe` -> `AttributeError`; after the fix ->
  `RuntimeError: No active experiment. Call start_experiment() first.`
- `python -m pytest tests/test_experiment_tracker.py -q` -> **25 passed** (was 24; +1 new test).
- `src/qtr/tracking/experiment.py` coverage -> **100%** (183 stmts / 40 branch / 0 miss);
  both guard branches (experiment present / absent) exercised.
- Tracking-adjacent suites
  (`test_experiment_tracker`, `test_experiment_tracking`,
  `test_experiment_artifact_schema`, `test_reproducibility_audit`,
  `test_h56_stats_json_echoes`) -> **332 passed**.
- `python -m ruff check src/qtr/tracking/experiment.py tests/test_experiment_tracker.py`
  -> all checks passed; `ruff format --check` -> 2 files already formatted.
- `git diff` -> only the two files above; no published/frozen artifact, verdict,
  threshold, sidecar, or experiment record modified.

### What remains unresolved

1. **Maintainer-only (unchanged).** `tests/test_gates_workflow.py` is red on
   `origin/main` by design; the fix is
   `patches/0001-gates-workflow-contract-fix.patch` (re-verified applicable and correct
   in Cycle 108). `.github/workflows/**` is agent-unreachable.
2. **Full-suite end-to-end re-run not repeated this session.** The changed method is
   100% covered at module level and the focused suites are green; the full
   `--cov=qtr --cov-branch` gate was last green at Cycle 108 (3,745 passed / 51 skipped
   / 7 failed; 7 = `test_gates_workflow.py` only) and this change cannot regress other
   modules, but the next session should re-run the full gate after this lands.
3. **H182 selection** — free-data point-in-time strategy-family queue exhausted
   (H1–H181 all rejected/recorded, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96);
   selecting H182 requires resolving a data gap under explicit authorization.

### Approaches already tried and why they should not be repeated

- Do not repeat re-verification-only cycles (105–108): the suite is green and stable;
  re-running it does not constitute progress. Look for real, evidenced defects instead.
- Do not edit `.github/workflows/**` to chase the 7 failures (restored from
  `origin/main`, excluded from staging, no `workflows` token).
- Do not invent/select H182 without a resolved data gap and authorization.

## One precise next task

**Re-run the full pinned gate to confirm this Cycle 109 fix integrates cleanly:**

```bash
python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing
python -m ruff check src tests run_*.py scripts
python -m ruff format --check src tests run_*.py scripts
```

Expected: **3,746 passed / 51 skipped / 7 failed** (the +1 vs Cycle 108 is the new
`test_log_dataframe_requires_experiment`; the 7 remain the maintainer-gated
`tests/test_gates_workflow.py`). `src/qtr` coverage stays **100%**. If the count is
exactly that, the fix is integrated and no further agent action is needed.

**Maintainer-only (still blocked):** apply
`patches/0001-gates-workflow-contract-fix.patch` to turn the 7 red
`tests/test_gates_workflow.py` failures green (full suite -> 3,753 / 51 / 0).

**Agent path (blocked unless authorized):** resolve the H182 data gap (free PIT
commodity roll/contango for carry, or PIT insider/earnings/options data) and select H182
per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4/§6 and
`NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96. Absent authorization, conclude free-data
family discovery is exhausted — do not invent an H182 candidate.

**Constraints:** additive sidecars only; do not delete/move artifacts; do not touch
published/frozen numbers, gates, or `src/qtr` beyond evidenced defects; no commit/push of
`.github/workflows/**`.

---

## Prior session (2026-11-14T05:52Z, Cycle 108) — full-suite re-verification; green baseline confirmed, no agent-actionable work

The previous "agent-path review" session (Cycle 107) confirmed no agent-actionable change exists. This session independently re-ran the full suite to verify the baseline.

### What was verified this session (Cycle 108, own evidence)

- `python -m ruff check src tests run_*.py scripts` — all checks passed.
- `python -m ruff format --check src tests run_*.py scripts` — 329 files already formatted.
- Full suite `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` (423s) — **3,745 passed, 51 skipped, 7 failed**. The 7 are exclusively `tests/test_gates_workflow.py`, unchanged from Cycle 107.
- `src/qtr` coverage — **100%** (1211 stmts / 422 branches / 0 miss).
- `scripts/backtest_perf_regression_gate.py` — green on this host (0.408s, limit 5s).
- **Maintainer patch re-verified**: `git apply --check patches/0001-gates-workflow-contract-fix.patch` succeeds; patched `gates.yml` satisfies all 7 contract assertions; with it applied the full suite would be **3,752 passed / 51 skipped / 0 failed**. Agent cannot land it (no `workflows` token; `.github/scripts/kilo-controller.sh` restores `.github/workflows/**` from `origin/main` after every session).
- `git status` — clean. No commit/push.

### What changed (annotation only, no source/test/artifact change)

- `HANDOFF.md` — added the Cycle 108 re-verification banner.
- `NEXT_TASK.md` — this entry.

## Prior session (2026-11-14T04:50Z, Cycle 106) — sidecar-schema repair committed; full suite re-verified

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

**Agent path (blocked unless authorized):** resolve the H182 data gap
(e.g. free point-in-time commodity roll/contango data for carry, or PIT
insider/earnings/options data) and select H182 per
`STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4/§6 and
`NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96. The free-data point-in-time
strategy-family queue is exhausted (H1–H181 all rejected/recorded; H182
unassigned). Absent authorization, conclude free-data family discovery is
exhausted — do not invent an H182 candidate.

**Session 2026-11-14T05:09Z (Cycle 107):** inspected the repository; confirmed
no agent-actionable change exists. `src/qtr` has no evidenced defect (suite
green except the 7 maintainer-gated `test_gates_workflow.py` failures, 100%
`src/qtr` coverage, ruff clean over 329 files). Verified `ruff check`/`format
--check` over `src tests run_*.py scripts` — all passed, 329 files formatted.
HEAD `08e551f` is annotation-only (HANDOFF.md, NEXT_TASK.md, patch prose
header) atop `62df672`; no source/test/gate/artifact/frozen-number change.
Per directive §6, did not default to maintenance-only work (no concrete
defect) and did not invent/select H182 (queue exhausted, authorization-gated).

**Constraints:** additive sidecars only; do not delete/move artifacts; do not
touch published/frozen numbers, gates, or `src/qtr` unless an evidenced defect
requires it; no commit/push of `.github/workflows/**`.