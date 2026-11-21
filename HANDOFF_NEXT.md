# Handoff for Next Session (2026-11-21, Cycle 245 — H191 recorded + companion tests added)

## Summary
H191 (NF-20261121-01, equity value / book-to-price & cash-flow-yield) was executed and committed
at 14:42 (`3a8fba9`) but left undocumented. This session completed the record: added a hermetic
companion test (22 tests), updated the experiment-artifact inventory pins, and wrote the H191
(Cycle 245) section of `NEW_FAMILY_RESEARCH_REGISTER.md`. Working tree has exactly three changes.

## H191 verdict (REAL REJECT, 4/8)
Selected `book_to_price, entry_z=0.5, exit_z=0.0, k=10, vol_target=0.15` (train WF 0.354).
OOS Val+Test: Sharpe 0.853, PF 1.159, maxDD −13.11%, worst-regime −0.683, trades 1430.
PASS: trades, maxDD, WF stability (2.612), OAT perturbation (1.129). FAIL: Sharpe, PF, worst-regime,
benchmark (p 0.756 two-sided, IR −0.138). Passive equal-weight long book OOS Sharpe 1.075 dominates;
excess return −2.21%/yr. Artifact:
`.experiments/nf_runs/nf_20261121_01_equity_value_20261121_144056/`.

## Current State (HEAD `3a8fba9` + this session's uncommitted changes)
- **New**: `tests/test_nf_20261121_01_equity_value.py` (22 passed) — hermetic synthetic fixtures;
  includes a regression guard that `build_value_panel` is not all-NaN (the transpose bug fixed in
  `3a8fba9`).
- **Modified**: `tests/test_experiment_artifact_schema.py` — inventory pins `EXPECTED_TOTAL_DIRS
  116→117`, `EXPECTED_SUMMARY_COUNT 108→109`, `EXPECTED_DISTINCT_KEYS 150→151` (new key
  `train_input_collinearity_bp_vs_cfy`); GE50/GE80/cache-only unchanged. → 114 passed.
- **Modified**: `NEW_FAMILY_RESEARCH_REGISTER.md` — Cycle 245 H191 section (lineage map, mechanism
  separation from H187/H188/H189, data availability 96/98 usable, execution outcome, durable
  family-status consequence).
- **Modified**: `NEXT_TASK.md` / `HANDOFF_NEXT.md` — this handoff.
- **Lint/format clean**: `ruff check` clean; `ruff format --check` 363 files formatted.
- **Focused regression set**: 588 passed.
- **Full suite (measured, `python -m pytest -q`)**: 4600 passed / 48 skipped / 7 failed — the 7 are
  the pre-existing maintainer-gated `tests/test_gates_workflow.py`; zero new failures. (Prev.
  baseline 4572/51/7 at `4b1df88`; +28/−3 = the new 22 H191 tests + artifact-present tests that
  previously skipped.)
- **`src/qtr` unchanged** → coverage unaffected at 100%.

## What Was Verified (this session)
- `pytest tests/test_nf_20261121_01_equity_value.py` → 22 passed.
- `pytest tests/test_experiment_artifact_schema.py` → 114 passed.
- Sibling NF tests `test_nf_20261120_01/02/04` → pass.
- Focused regression set (incl. reproducibility, momentum-runner, artifact-schema, H191) → 588 passed.
- Project-wide `ruff check` clean; `ruff format --check` → 363 files already formatted.

## Remaining Work (Non-blocking)
1. **Maintainer action required (agent-unreachable)**: Apply
   `patches/0001-gates-workflow-contract-fix.patch` to fix `test_gates_workflow.py` (7 failures).
   `.github/workflows/**` is maintainer-managed; repo token has no `workflows` permission;
   `.github/scripts/kilo-controller.sh` restores workflows from `origin/main` and excludes them
   from staging.
   - Command: `git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am "fix(ci): satisfy gates workflow contract" && git push origin main`
   - Expected: `test_gates_workflow.py` → 7 passed; full suite → 4579 passed / 51 skipped / 0 failed.

2. **Authorization-gated artifact cleanup** (unchanged): Drop 8 superseded `param_grid_results`
   keys + 3 stale `summary` keys from `.experiments/experiments.jsonl`, update
   `REPRODUCIBILITY_BASELINE` (hash_mismatches 11 → 3), `PINNED_HASH_MISMATCHES`, and
   `REPRODUCIBILITY_AUDIT_REPORT.md` together. Re-run `tests/test_reproducibility_audit.py` after
   (gate fails on undocumented count changes).

## Approaches Already Tried / Do Not Repeat
- Do not re-declare any H-ID family as data-blocked without naming the probed source.
- Do not treat parameter/timeframe/universe/market variants of H1–H191 as new families.
- Do not modify `.github/workflows/**` (maintainer-managed; agent-unreachable).
- Do not re-run H190, H191, or any exhausted family as a variant; the full-window pre-registered
  runs are the record.
- Do not reintroduce a hard dependency on `.cache/xbrl/**` in tests: that cache is git-ignored and
  absent on fresh checkouts/CI. Tests must be hermetic (synthetic fixtures).
- Do not mass-edit runners/tests/gates to force the suite green; frozen-contract drifts need
  per-contract evidence and authorization.
- Do not manufacture a hardening guard without first reproducing a concrete failure under
  `-W error`, and do not add a guard to one function when the same input class already behaves
  identically across all sibling functions.

## Evidence Files
- `NEXT_TASK.md` — full verification evidence and constraints (updated Cycle 245).
- `patches/0001-gates-workflow-contract-fix.patch` — maintainer-ready fix (applies cleanly).
- `tests/test_nf_20261121_01_equity_value.py` — new hermetic H191 tests (22 passed).
- `.experiments/nf_runs/nf_20261121_01_equity_value_20261121_144056/summary.json` — H191 verdict.
- `run_nf_20261121_01_equity_value.py:336` — non-transposed `build_value_panel` return (the fix).
- `NEW_FAMILY_RESEARCH_REGISTER.md` — Cycle 245 H191 section.
- `REPRODUCIBILITY_AUDIT_REPORT.md` §2 — 11 hash mismatches (8 runner-side fixed, 3 summary.json re-run).

## Next Session Guidance
- **No blocking code task exists.** H191 is fully executed, tested and recorded. The single next
  task is the maintainer workflow patch application.
- If that lands and artifact-cleanup authorization arrives, perform item 2 above.
- If further hardening is desired later: first reproduce a concrete crash under `-W error` from a
  public-API path, then fix with minimal fail-closed guard + test keeping `src/qtr` at 100% branch
  coverage.

(End of file - total 92 lines)