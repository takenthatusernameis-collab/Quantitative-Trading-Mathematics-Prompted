# HANDOFF — current session (2026-11-15, Cycle 128)

## What changed

**Repaired a coverage-gate regression left by Cycle 127 (no source change).**

The Cycle 127 commit (`cdf13eb`) added the `if not line: continue` guard to
`ExperimentTracker.load_experiment` (and `list_experiments`) and claimed
"100.00% coverage". That claim was wrong at HEAD: the accompanying test
`test_load_and_list_skip_malformed_and_incomplete_lines` never exercises the
blank-line branch on the **load** path. `load_experiment` returns as soon as it
matches a record, so the trailing blank line of the test's log (the only blank
line present) is reached only by `list_experiments`, which scans the whole file.
Result: `src/qtr/tracking/experiment.py` line 287 (`continue` for an empty line
in `load_experiment`) was **uncovered**, and the full suite failed the 100%
coverage gate at **99.90%** (3853 passed, 48 skipped, `Coverage failure`).

- **Fix:** `tests/test_experiment_tracker.py` — added
  `test_load_experiment_skips_blank_lines`: writes a log whose **first** line is
  blank, then asserts `load_experiment("e1")` still finds the valid record and
  `load_experiment("missing")` still returns `None`. This exercises the load
  path's `if not line: continue` guard on both the match and no-match paths.
  No `src/qtr` change: the guard is the documented contract, so it is pinned by
  a test rather than removed.

No gate, artifact, sidecar, hash, frozen number, or workflow change.

## What was actually verified (own evidence)

- **Reproduced the regression first:** focused coverage
  `pytest -q tests/test_experiment_tracker.py tests/test_experiment_tracking.py --cov=qtr --cov-branch --cov-report=term-missing`
  → `src/qtr/tracking/experiment.py 215 1 44 1 99% 287`; full pinned suite
  before the fix → **3853 passed, 48 skipped**, `TOTAL ... 99.90%`,
  `Coverage failure: total of 99 is less than fail-under=100`.
- After the fix: focused coverage → `experiment.py 215 0 44 0 100%`,
  **46 passed** (was 45; +1 = the new test).
- Full pinned suite
  `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py`
  (336.34s) → **3854 passed, 48 skipped, coverage 100.00%**. The 48 skips are
  the pre-existing H51/H29/H28/causality skips.
- `python -m pytest -q tests/test_gates_workflow.py` → **7 failed** (unchanged,
  exclusively the maintainer-gated workflow-contract block; fix is
  `patches/0001-gates-workflow-contract-fix.patch`).
- `python -m ruff check src tests run_*.py scripts` → All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` → 335 files already
  formatted.

## What remains unresolved

1. **Maintainer-only (CI contract):** `.github/workflows/gates.yml` not updated;
   7 `tests/test_gates_workflow.py` tests red until the maintainer applies
   `patches/0001-gates-workflow-contract-fix.patch` with workflow-scoped
   credentials. Agent cannot land `.github/workflows/**`.
2. **Research queue exhausted under free/public PIT data:** H1–H182
   executed/rejected; no honest free-data H183 is pre-registrable without new
   authorized data.
3. **Reproducibility backlog:** `missing_files=197`, `hash_mismatches=11`,
   `orphaned_files=528`, `missing_meta_files=0` unchanged; baseline-frozen where
   contract/citation constraints apply.
4. **Handoff reliability:** Cycle 127's `HANDOFF.md`/`NEXT_TASK.md`/`HANDOFF_CURRENT_SESSION.md`
   asserted 100% coverage that did not hold at HEAD. Treat prior "verified"
   claims as unconfirmed until the gate is actually run; the gate is the source
   of truth, not the prose.

## Approaches already failed / must not be repeated

- Do not trust a handoff's coverage/pass claim without running the gate; Cycle
  127's "100.00%" was false at HEAD (99.90%).
- Do not "fix" a coverage miss by deleting the explicit `if not line: continue`
  guard — the guard is the documented contract; the correct closure is a test
  that exercises the load-path branch (this session's approach).
- Do not re-open closed defect classes without new evidence: duplicate
  index/column guards (Cycles 125/126), `regime_analysis`/`parameter_sensitivity`
  shape guards (Cycle 124), H182 fetch `KeyError` (Cycle 122), malformed/incomplete
  JSONL skip (Cycle 127), non-JSON-serializable metadata writers (`default=str`,
  commit `b3702fd`).
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or
  alter coverage/frozen-contract gates.
- Do not make speculative `src/qtr` changes absent a reproduced, reachable defect.

## One precise next task

**Maintainer (preferred, unblocks CI):** apply and push
`patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then run
`python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on
`origin/main`.

**Agent alternative (only with new evidence):** audit the remaining `qtr.tracking`
/ `qtr.data` persistence paths for a *reproduced* crash on realistically
corrupt/partial state. `Experiment.load_metadata()` already degrades to `{}` on
corrupt JSON and `log_metadata`/`log_params`/`log_results` now use
`json.dump(..., default=str)` (commit `b3702fd`). The still-unguarded serializers
are `Experiment.record_artifact` (`json.dump(data, f)` for a `dict`/`list`/unknown
object) and `ExperimentTracker.log_artifact`'s metadata sidecar
(`json.dump(metadata, f, indent=2)`); both are public API but are **not reached by
any runner** (runners call `log_artifact("summary", path)` with no metadata and do
not use `Experiment.record_artifact`), so a fix there would be speculative — do not
change them without a concrete failing case. Keep 100% `src/qtr` coverage and all
gates/contracts intact.

**Constraints:** no gate weakening; no modification of published/frozen artifacts,
verdicts, thresholds, or frozen numbers except a deliberate authorized
corpus/baseline update; no workflow commit from agent.