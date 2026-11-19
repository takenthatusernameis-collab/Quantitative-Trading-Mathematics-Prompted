# Next task (2026-11-19, Cycle 225)

## State at the start of this session (what the previous session left)
- HEAD `1a7c83a` == origin/main. The **H28 path remediation is already committed** (commit
  message empty — cosmetic defect only): 172 obsolete depth-one paths in
  `.experiments/experiments.jsonl` were rewritten to
  `.experiments/artifacts/h28_causal_recertification/runs/<exp_id>/` (each verified hash-exact),
  and 8 additive `.meta.json` sidecars were added.
- Backlog moved **(missing 197→25, orphaned 528→356)**; hash mismatches (11) and missing sidecars
  (0) unchanged. Identity digests for both count-only backlogs are pinned in
  `tests/test_reproducibility_audit.py`.
- `HANDOFF.md` / `NEXT_TASK.md` / `HANDOFF_CURRENT_SESSION.md` still described the pre-remediation
  Cycle 222 state (197 / 528, HEAD `6773007`) — stale and misleading.

## What changed this session
- `REPRODUCIBILITY_AUDIT_REPORT.md`: removed two dangling references to files that never existed
  (`patches/0002-h28-jsonl-path-remediation.patch`, `scripts/verify_h28_path_remediation_patch.py`)
  and replaced them with the real provenance (applied directly in commit `1a7c83a`); refreshed the
  Implications table (25 missing / 356 orphaned; sidecar row now ✅ at 0) and the remediation item.
- `tests/test_reproducibility_audit.py`: docstring provenance corrected the same way (comment-only;
  pins untouched).
- `HANDOFF.md` banner, `NEXT_TASK.md`, `HANDOFF_CURRENT_SESSION.md`: rewritten for the
  post-remediation state.
- No change to `src/qtr`, other tests, `run_*.py`, gates, artifacts, sidecars, hashes, frozen
  numbers, or `.github/workflows/**`.

## What was actually verified (own evidence, 2026-11-19)
- Independent recount of `.experiments/experiments.jsonl` (174 records) → **missing 25,
  hash_mismatches 11, orphaned 356, missing_meta 0**; recomputed digests equal the pins
  (`a5024443…` / `c6611f77…`).
- `python -m pytest -q tests/test_reproducibility_audit.py tests/test_artifact_restoration_plan.py
  tests/test_h28_causal_recertification.py` → **63 passed**.
- `python -m ruff check src tests run_*.py scripts` → All checks passed;
  `python -m ruff format --check …` → 352 files already formatted.
- `python scripts/backtest_perf_regression_gate.py` → PERF GATE PASSED (0.424 s, 10.7 MB, 13668
  trades). `python scripts/verify_gates_workflow_patch.py` → PATCH VERIFIED (7 live violations,
  maintainer-gated).
- Full pinned suite with coverage → see `HANDOFF_CURRENT_SESSION.md` for the recorded run.

## What remains unresolved
- **Maintainer-gated workflow patch:** apply/push `patches/0001-gates-workflow-contract-fix.patch`,
  then `python scripts/verify_gates_workflow_patch.py` (expect `CONTRACT SATISFIED`) and
  `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed). Live state: 7 failed.
- **25 unrecoverable missing artifacts** (no hash-matching source anywhere in the store) require a
  re-run with the original configs; that is a research/data task and is authorization-gated.
- **11 hash mismatches** are superseded duplicate log entries; remediation means editing
  `experiments.jsonl` (drop the stale keys), which is authorization-gated and must not overwrite
  artifacts.
- **H1–H186 exhausted/rejected; H187 unassigned with no free-data source.** Free-data family
  discovery is concluded per directive §6; any new research cycle needs a newly authorized source.

## One precise next task
**Maintainer:** apply/push `patches/0001-gates-workflow-contract-fix.patch`, then verify
`CONTRACT SATISFIED` and 7 passing contract tests.

**Agent:** re-verify the post-remediation baseline with own evidence (recount the four backlog
numbers + digests, `tests/test_reproducibility_audit.py`, `tests/test_artifact_restoration_plan.py`,
`tests/test_h28_causal_recertification.py`, ruff check/format, full pinned suite with 100%
`src/qtr` coverage, perf gate, `scripts/verify_gates_workflow_patch.py`) and leave the handoff. Do
not re-open the H28 remediation or re-add the removed patch reference; if the corpus genuinely
changes, update `REPRODUCIBILITY_BASELINE`, the two digests, and
`REPRODUCIBILITY_AUDIT_REPORT.md` together in one deliberate commit.

## Approaches already tried and why they should not be repeated
- Do not restore H28 artifacts by copying them to depth-one paths — that breaks the H28 depth-one
  invariant in `tests/test_h28_causal_recertification.py`; the logged paths were corrected instead
  (Cycle 224).
- Do not invent a `patches/0002-*` rehearsal patch now that the remediation is committed; the
  provenance is the commit diff.
- Do not rebuild the corpus guard on `json.loads`; use `object_pairs_hook` (Cycle 217).
- Do not re-run H184/H185/H186 or parameter/universe/window variants; do not re-probe
  CHRIS/CME/Yahoo/stooq/LME/DCE; do not re-declare FRED/binance/Chinese-exchange/CFTC-Socrata data
  as blocked.
- Do not edit `.github/workflows/**` or weaken any gate or contract test.
- Do not trust "working tree clean" or handoff counts as proof tests are green — re-run them.
