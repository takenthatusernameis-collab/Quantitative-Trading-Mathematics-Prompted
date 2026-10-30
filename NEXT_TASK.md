# Next task — H77: CI gate workflow was deleted from HEAD

## Status (this session)
Discovered by inspection, not by assignment: **HEAD `876a15f` deleted
`.github/workflows/gates.yml`** (the H76 artifact), while every handoff in the
tree still records H76 as complete and the file as present. On disk the research
gates had **no CI enforcement** — the exact gap H76 closed. Restored the file
byte-identical to the verified version (`a9e9fe1:.github/workflows/gates.yml`).
No `src/qtr` change, no published artifact, gate threshold, verdict or certified
number modified, no grid re-run. H1–H30 exhausted.

## What changed
- `.github/workflows/gates.yml` — **restored**, byte-identical to the version
  verified in the H76 session (diff confirmed empty). Two jobs on `push` to
  `main`, `pull_request`, `workflow_dispatch`, path-filtered to `src/`,
  `tests/`, `run_*.py`, `requirements.txt`, `pyproject.toml` and the workflow
  itself:
  - `lint` — `python -m ruff check src tests run_*.py` and
    `python -m ruff format --check src tests run_*.py`.
  - `research_gates` — `python -m pytest -q -W error --cov=qtr --cov-branch
    --cov-report=term-missing` (enforces `fail_under = 100` with branch
    coverage).
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`,
  `HANDOFF_NEXT.md`, `HANDOFF_NEXT_SESSION.md`, `HANDOFF_SESSION.md`,
  `HANDOFF_SESSION_END.md` — corrected to record H77 and the true on-disk state.

## What was actually verified
- `diff <(git show a9e9fe1:.github/workflows/gates.yml) .github/workflows/gates.yml`
  → empty; **byte-identical to the verified artifact**.
- `python -c "import yaml; yaml.safe_load(open('.github/workflows/gates.yml'))"`
  → parses OK; triggers are `push`/`pull_request`/`workflow_dispatch`.
- `git log --oneline -- .github/workflows/gates.yml` → `876a15f` (delete),
  `a9e9fe1` (add), `d080a1e` (delete), `d878dad` (add) — the file has been
  added and deleted repeatedly; this session restores it and the tree now
  matches the documented H76 state.
- `PYTHONPATH=src python -m ruff check src tests run_*.py` → All checks passed!
- `PYTHONPATH=src python -m ruff format --check src tests run_*.py` →
  105 files already formatted.
- The file is **untracked** (not committed) per the no-commit-without-
  explicit-request rule; it is present on disk and restores CI enforcement.

## What remains unresolved
- H53–H61 remain disclosed, not quantified (no inputs). No gates affected.
- Whether the deletion at `876a15f` was intentional (e.g. a deliberate rollback)
  is not recorded anywhere in the tree; the handoffs all describe the file as
  present, so the deletion is treated as an unintended regression.

## Precise next task
**None assigned.** If a future session touches CI or the gates it enforces:
1. Keep the two jobs' commands identical to the documented gates in `AGENTS.md`
   and `pyproject.toml`; do not relax `fail_under`, drop `-W error` or remove the
   format check.
2. After any change that could move the gate surface, re-run
   `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`
   and the ruff commands and confirm `src/qtr` stays at 100% (statement+branch).
3. Do not `pip install -e .` unless a test requires it; restore the bare-clone
   state (qtr uninstalled) afterwards.

## Constraints carried forward
- No published artifact, gate threshold, verdict, or certified number may be
  modified. H1–H30 exhausted.
- `src/qtr` must remain at 100% coverage (statement + branch).
- Ruff lint/format must remain clean.
- qtr remains uninstalled (bare clone).
- Preserve existing automation/permissions/safety controls.

## Failed approaches
- None for this session. The fix was a direct restoration from git history;
  the only subtlety was the missing trailing newline, which was added to match
  the verified artifact byte-for-byte.

(End of file - total 65 lines)