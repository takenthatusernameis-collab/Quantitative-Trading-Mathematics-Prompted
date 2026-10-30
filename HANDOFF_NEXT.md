# HANDOFF_NEXT — next agent task (H80: none assigned; H79 complete)

## Context
- H78 (commit `e646dd0`): `.github/workflows/gates.yml` **created and
  committed** from the documented spec. CI enforcement durable.
- H79 (commit `64ced09`): eight handoff/markdown files rewritten to correct
  false provenance claims. Working tree clean.
- Baseline gates green: ruff check passed, 105 files formatted, pytest `-W
  error` coverage 2168 passed / 16 skipped, `src/qtr` 1168 stmts / 374 branches
  / 100.00%. qtr uninstalled (bare clone).

## Precise next task (one task), with evidence and constraints
**None assigned.** If a future session touches CI or the gates it enforces:
1. Keep the two jobs' commands identical to the documented gates in
   `AGENTS.md`/`pyproject.toml`; do not relax `fail_under`, drop `-W error`, or
   remove the format check.
2. After any change that could move the gate surface, re-run
   `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`
   and the ruff commands and confirm `src/qtr` stays at 100% (statement+branch).
3. Do not `pip install -e .` unless a test requires it; restore the bare-clone
   state (qtr uninstalled) afterwards.
4. Before asserting any provenance fact in a handoff, verify it against the
   committed tree (`git log --oneline --all`, `git show HEAD:<path>`,
   `git status --short`). Two consecutive sessions have now written handoff
   prose that was not true of the repo; the check is cheap and the failure
   mode is recurring.

## State at handoff
- HEAD `64ced09`. Working tree clean. `gates.yml` committed and byte-identical
  to disk. qtr uninstalled. All gates green. No false provenance claims remain
  in the handoff files.

## Constraints carried forward
- No published artifact, gate threshold, verdict or certified number may be
  modified; H1–H30 exhausted; `src/qtr` coverage must stay 100%
  (statement+branch); ruff lint and format gates must stay clean; qtr left
  uninstalled.

(End of file)