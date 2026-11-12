# NEXT_TASK.md — Apply Path Implemented and Verified; Apply Awaits Authorization

## Session Summary (2026-11-12)

**Assigned task (from previous handoff):** Apply the 321 hash-exact artifact
restorations, then lower the baselines — **only with explicit authorization**.

**Status: BLOCKED on explicit authorization (not granted this session).** The
apply path was implemented and verified behind an off-by-default `--apply` flag,
and the plan report was made truly byte-reproducible. **No artifact was copied.**

### What Changed This Session
- `scripts/plan_artifact_restoration.py`
  - Added `apply_plan()` and `--apply` / `--dry-run` flags. The default remains
    read-only. `--apply` re-hashes each source immediately before copying and
    refuses to overwrite an existing target; `--dry-run` reports without writing.
  - Fixed CSV determinism: `csv.DictWriter(..., lineterminator="\n")`. The
    committed plan previously had mixed CRLF/LF endings the tool could not
    reproduce; it now emits clean LF.
  - Plan header now states that applying requires the explicit `--apply` flag.
- `tests/test_artifact_restoration_plan.py`
  - Added 4 tests: apply copies byte-for-byte; dry-run writes nothing; apply
    refuses to overwrite an existing target; apply refuses on source-hash drift.
    All run against `tmp_path`, never the real artifact store.
- `REPRODUCIBILITY_RESTORATION_PLAN.{md,csv}`
  - Regenerated in place. CSV line endings normalized to LF; row content is
    unchanged (321 recoverable, 25 unrecoverable).

### Files Not Changed
- `src/qtr/` — unchanged; coverage remains 100%.
- `.experiments/` — no artifacts, records, metadata, or `experiments.jsonl`
  were modified, copied, or deleted. **No artifact was restored.**
- `tests/test_reproducibility_audit.py` — unchanged; baseline ratchet intact.
- Frozen contracts, gates, thresholds, published artifacts — unchanged.
- `.github/workflows/` — unchanged.

---

## What Was Verified

| Check | Command | Result |
|-------|---------|--------|
| Full pinned suite | `PYTHONPATH=src python -m pytest -q -W error` | ✅ **3649 passed, 51 skipped** (3645 + 4 apply tests) |
| Coverage gate | `PYTHONPATH=src python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` | ✅ **100.00%** (1209 stmts, 420 branches, 0 missed) |
| Lint | `python -m ruff check scripts tests` | ✅ Clean |
| Format | `python -m ruff format --check scripts tests` | ✅ Clean (168 files) |
| Focused planner+audit | `PYTHONPATH=src python -m pytest tests/test_artifact_restoration_plan.py tests/test_reproducibility_audit.py -q -W error` | ✅ 15 passed |
| Determinism | run planner twice to `/tmp`, `diff` | ✅ byte-identical (MD and CSV) |
| Apply isolation | new apply tests run on `tmp_path` only | ✅ no real artifact touched |

---

## Remaining Unresolved

### Apply is not executed (needs authorization)
The plan is ready; copying 321 files into `.experiments/artifacts/` is a write
that requires explicit human authorization. It has not been run.

| Backlog | Count | Notes |
|---------|-------|-------|
| Missing referenced files | 346 | 321 hash-exact recoverable (plan exists); 25 unrecoverable |
| Hash mismatches | 11 | Overwritten `param_grid_results`; 3 `summary.json` under `nf_runs` |
| Orphaned files | 528 | Unreferenced files/dirs; deletion would destroy committed data |
| Missing `.meta.json` sidecars | 140 | 118 are `summary.json`; 22 parquet |

Full analysis: `REPRODUCIBILITY_AUDIT_REPORT.md`.

### Strategy family discovery
**Queue exhausted at H181.** H182 unassigned. Cycle 96 blockers remain:
commodity carry, insider transactions, earnings revisions, options dealer GEX,
breakeven inflation, and statistical power for annual events. No free-data
candidate clears the directive bar.

---

## Failed Approaches / Do Not Blindly Repeat

- Do not run `--apply` without explicit human authorization.
- Do not restore the audit to a zero-backlog assertion — it makes the suite and
  CI red with no signal.
- Do not "fix" the sidecar count by rewriting history; the real count is 140.
- Do not delete orphaned artifacts to make the orphan check pass.
- Do not edit `experiments.jsonl` paths or hashes without authorization.
- Do not modify `src/qtr` for a test-only path mismatch.
- Do not trust a handoff doc's green claim — re-run the suite.
- Do not commit the plan with absolute paths (already fixed: repo-relative).

---

## One Precise Next Task

**Run the apply only after a human explicitly authorizes it.**

Concretely, after authorization:
1. Preview: `python scripts/plan_artifact_restoration.py --apply --dry-run`
   (prints every target; writes nothing).
2. Apply: `python scripts/plan_artifact_restoration.py --apply`
   (copies 321 files; refuses to overwrite).
3. Re-run `PYTHONPATH=src python -m pytest tests/test_reproducibility_audit.py -q`
   and confirm `missing_files` drops 346 → 25.
4. Lower, together and deliberately:
   - `tests/test_reproducibility_audit.py::REPRODUCIBILITY_BASELINE["missing_files"]` 346 → 25
   - `tests/test_artifact_restoration_plan.py::RECOVERABLE_BASELINE` 321 → 0
     (unrecoverable stays 25)
5. Regenerate `REPRODUCIBILITY_RESTORATION_PLAN.{md,csv}` (the tool now writes
   LF and is byte-reproducible) and update `REPRODUCIBILITY_AUDIT_REPORT.md`.
6. Re-run `pytest -q -W error`, ruff check/format, and the coverage gate.

If authorization is **not** granted, close out the reproducibility fallback item
and return to strategy-family discovery at H182, documenting that discovery
remains blocked on the same six data constraints.

**Evidence to start from:**
- `REPRODUCIBILITY_RESTORATION_PLAN.csv` — 321 rows, every `source_hash ==
  recorded_hash`, LF endings.
- `scripts/plan_artifact_restoration.py` — `apply_plan()` is the apply source of
  truth; `--apply` is off by default.
- `tests/test_artifact_restoration_plan.py` — baseline ratchet + apply tests.
- `tests/test_reproducibility_audit.py` — audit baseline to lower after apply.

**Constraints:**
- `src/qtr` unchanged unless an evidenced defect requires the full gates.
- No artifact deletion, no `experiments.jsonl` rewrite, no gate weakening.
- No commit/push unless requested.
- Do not run `--apply` without explicit authorization.

---
*Updated 2026-11-12: opt-in `--apply` implemented and verified behind a
default-off flag; CSV made byte-reproducible (LF); full pinned suite 3649 passed
/ 51 skipped; coverage 100%; lint and format clean. No artifact copied. Next:
human-authorized apply of the 321 hash-exact rows.*