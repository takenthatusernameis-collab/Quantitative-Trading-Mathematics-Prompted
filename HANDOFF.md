# Agent Handoff

## State
- Full suite: 538 passed, 0 warnings, ~207s. All lint/format clean. Coverage on src/ = 99% (919/919 stmts, one uncovered branch at statistics.py:114 — `walk_forward_splits` empty-window guard, unreachable under real inputs).
- Working tree has uncommitted changes (not committed per session policy):
  - `src/qtr/tracking/experiment.py` — `ExperimentTracker._get_git_info` now probes `git status --porcelain` instead of `git diff --quiet`, so **untracked** files (new experiment artifacts) register as `git_dirty=True`. The old probe only inspected tracked working-tree changes, so an experiment that wrote a fresh artifact into an untracked directory (e.g. `.experiments/artifacts/<exp_id>/`) would be stamped `git_dirty=False` — the exact reproducibility failure the flag exists to warn about.
  - `tests/test_experiment_tracker.py` — new `test_git_dirty_detects_untracked_artifacts` pins the corrected probe against a real, clean git repo, then writes an untracked file and asserts `git_dirty` flips to True (and a modified tracked file still registers dirty).

## What this session did
- No prior agent assignment remained (the H17/H19/H20 prose fix from the previous session was already committed and verified; the working tree was clean). Inspected the repo independently and selected one bounded, high-value task:
  **`ExperimentTracker._get_git_info` `git_dirty` blind spot for untracked files.** The tracker stamps every experiment record with `git_commit` + `git_dirty` as its reproducibility marker (logged verbatim into `.experiments/experiments.jsonl` — 1,236 tracked records). The probe was `subprocess.call(["git", "diff", "--quiet"])`, which only inspects **tracked** working-tree changes. `git diff` does not report untracked files at all, so any experiment that wrote a new artifact into an untracked directory would be recorded with `git_dirty=False` even though the artifact was never committed — a false "clean, reproducible" stamp on an actually unreproducible state. Reproduced deterministically in a throwaway git repo: clean tree → `git diff --quiet` exit 0 → write untracked `experiments.jsonl` → `git diff --quiet` **still exit 0**, while `git status --porcelain` reports `?? experiments.jsonl`. The fix is a two-line probe swap (`git status --porcelain`, dirty iff non-empty output); it does not touch orchestration, permissions, experiment runners, grids, selection, gates, or any certified number.

## Verified
- `python -m pytest -q` → 538 passed (was 537), ~207s.
- `python -m pytest -W error -q` → 538 passed, 0 warnings.
- `python -m pytest --cov=qtr --cov-report=term-missing` → 99% on src (919 stmts; single miss is the unreachable `walk_forward_splits` empty-window guard at statistics.py:114).
- `python -m ruff check src tests run_*.py` → clean.
- `python -m ruff format --check src tests run_*.py` → 69 files already formatted.
- `bash -n .github/scripts/*.sh` → OK; `bash .github/scripts/test_kilo_progress.sh` → OK.
- The new regression test **fails under the reverted buggy probe** (restored `git diff --quiet`, reproduced `assert dirty2 is True` → `False is True`) and **passes with the fix**.
- `test_tracker_git_and_deps_exception` was updated to drive the failure path through `subprocess.check_output` (the new probe's shell-out); it still asserts the `("unknown", False)` degrade.
- Existing tracker tests (19) still pass; no experiment-runner or artifact regression tests were affected.

## Unresolved
- None blocking. The `walkforward_stability` metric remains a *simplified* proxy (first-half vs second-half ratio), not the literal "5 walk-forward folds" measure used by the H9/H10/H11 runners. `validate_strategy` receives returns + trades only, not the full price/vix context the runners have, so it cannot compute the fold-based metric. The H9–H25 gate is unaffected — it computes `wf_stability` independently in the runner, not via `validate_strategy`.
- `walk_forward_splits` — the documented "drops trailing samples" latent issue is **already fixed in HEAD**: the last window absorbs the trailing tail (`statistics.py:108-110`), so `walk_forward_splits(77, 3)` covers all 77 samples and `walk_forward_splits(252, 5)` covers all 252. Verified empirically. No certified number changes; H10's 5148 bars are divisible by 5 anyway. Nothing to fix here.

## Failed approaches
- None this session. The fix was a two-line probe swap plus one regression test.

## This session (independent re-verification)
- `python -m pytest -q` → 538 passed, ~207s
- `python -m pytest -W error -q` → 538 passed, 0 warnings
- `python -m pytest --cov=qtr --cov-report=term-missing` → 99% on src (919 stmts)
- `python -m ruff check` + `ruff format --check` → clean
- `bash -n .github/scripts/*.sh` → OK
- `bash .github/scripts/test_kilo_progress.sh` → OK
- No TODOs/FIXMEs in `src/` or `tests/`
- Reproduced the defect in a throwaway repo: `git diff --quiet` exit 0 before AND after writing an untracked file; `git status --porcelain` reports `?? experiments.jsonl` after the write.

## Next task (precise)
No bounded task remains within the free-data constraint; the free-data hypothesis space is exhausted (see FINAL_REPORT.md §Next Task). The precise next task requires **paid hourly futures data** to widen the OOS window enough for the PF and Sharpe bootstrap CIs to clear their gates with margin. Do not run further hypotheses on free data. If assigned, verify with the commands above plus `pip install -e .` if `qtr` is not importable.

(End of file)