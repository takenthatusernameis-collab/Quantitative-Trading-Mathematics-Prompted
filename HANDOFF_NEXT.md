# HANDOFF_NEXT — next agent task (H79: handoff/claim audit against committed tree)

## Context
H78 is complete: `.github/workflows/gates.yml` was **created and committed**
at HEAD `e646dd0` (working tree clean). Baseline gates green: ruff check passed,
105 files formatted, pytest `-W error` coverage 2168 passed / 16 skipped,
`src/qtr` 1168 stmts / 374 branches / 100.00%. qtr uninstalled (bare clone).

The H78 session exposed a systemic problem: **handoff documents asserted
facts that were not true of the committed tree.** Prior handoffs repeatedly
claimed `gates.yml` was "restored byte-identical to `a9e9fe1`", but that commit
does not exist in this repo (HEAD history is only `d462ff9` and `9e4df99`), and
the file was absent from disk. Each session "restored" it untracked; each
subsequent checkout/reset lost it. The file was only made durable by committing
it.

## Precise next task (one task), with evidence and constraints
**Audit every handoff/claim file in the working tree against the committed
tree, and rewrite any claim that is not true of HEAD.**

Evidence this task is needed: `HANDOFF.md`, `HANDOFF_NEXT.md`,
`HANDOFF_CURRENT_SESSION.md`, `HANDOFF_NEXT_SESSION.md`, `HANDOFF_SESSION.md`,
`HANDOFF_SESSION_END.md`, and `NEXT_TASK.md` all reference commits
(`a9e9fe1`, `830dfd3`, `137b8a6`, `b37e93b`, `0b31804`, `876a15f`, `d080a1e`,
`d878dad`) that `git log --oneline --all` shows **do not exist** in this repo.
They also describe `gates.yml` as "byte-identical to the verified artifact"
when no such artifact exists. This is the second consecutive session whose
handoff contained a false provenance claim.

Constraints:
- Do NOT modify `src/qtr`, tests, runners, any published artifact, gate
  threshold, verdict, or certified number. No grid re-run. H1–H30 exhausted.
- Do NOT delete or rewrite history. Only correct the *prose* claims in the
  handoff/markdown files.
- For each claim, check it against the real state (`git log --oneline --all`,
  `git show HEAD:<path>` for existence, `git status --short`, the actual gate
  outputs) and rewrite it to match reality — or remove it if unverifiable.
- After editing, re-run `python -m ruff check src tests run_*.py`,
  `python -m ruff format --check src tests run_*.py`, and
  `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`
  to confirm `src/qtr` stays at 100% (statement+branch). Do not `pip install -e .`
  unless a test requires it; restore the bare-clone state (qtr uninstalled)
  afterwards.
- Leave the tree clean except for the corrected markdown files, and commit
  only those markdown corrections with a message that states what was corrected
  and why (requires explicit user approval to commit — do not commit without it).

## State at handoff
- HEAD `e646dd0`. Working tree clean. `gates.yml` committed and byte-identical
  to disk. qtr uninstalled. All gates green.

## Constraints carried forward
- No published artifact, gate threshold, verdict or certified number may be
  modified; H1–H30 exhausted; `src/qtr` coverage must stay 100%
  (statement+branch); ruff lint and format gates must stay clean; qtr left
  uninstalled.

(End of file)