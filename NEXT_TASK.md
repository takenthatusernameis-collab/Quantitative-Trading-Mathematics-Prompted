# Next task — Baseline maintenance (no pending code change)

## Status (this session)
No prior agent assignment existed in this clone; the handoff files describe a
phantom state (HEAD `830dfd3`, `gates.yml` untracked/missing, byte-identity to
commits `a9e9fe1`/`137b8a6`/… that are not present in this repo's single-commit
history). I inspected the tree instead of waiting.

Verified actual state:
- HEAD `5af36cc` on `main`; `main == origin/main` (fully synced after fetch).
- Working tree clean (`git status --short` empty).
- `.github/workflows/gates.yml` IS tracked in HEAD (CI gates already durable;
  no commit needed, and none may be made without explicit user approval).
- `python -m ruff check src tests run_*.py` → All checks passed.
- `python -m ruff format --check src tests run_*.py` → 105 files formatted.
- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`
  → 2168 passed, 16 skipped; `src/qtr` 1168 stmts / 374 branches / 100.00%
  (required coverage reached).
- `qtr` not installed (bare clone state; `PYTHONPATH=src` works).

## What changed
None. This was a verification + doc-reconciliation session; no source, test,
runner, artifact, gate threshold, verdict, or certified number was modified.

## What was actually verified
- `git rev-parse main origin/main` → identical (`5af36cc`).
- `git ls-files .github/workflows/gates.yml` → tracked.
- All three gates above green (evidence in this session's tool output).

## What remains unresolved
- Older handoff files (`HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_NEXT.md`,
  `HANDOFF_SESSION.md`, `HANDOFF_SESSION_END.md`, parts of
  `HANDOFF_CURRENT_SESSION.md`/`HANDOFF_NEXT_SESSION.md`) still reference the
  phantom HEAD `830dfd3` and an untracked/missing `gates.yml`. They are
  superseded by this file; their byte-identity claims cannot be re-verified
  locally because the referenced commits do not exist in this clone. Treat them
  as historical narrative, not actionable state.
- Workflow real-world execution on GitHub Actions is unverified (no runner in
  this sandbox); verified by each gate command being green in-tree.

## Approaches already failed
- None this session. (Earlier sessions' "commit gates.yml" approach is moot:
  the file is already tracked in HEAD; committing again would be a no-op and is
  barred without explicit user approval.)

## One precise next task
**Maintain baseline health.** No code change is needed now. On any future
change under `src/qtr`, `tests/`, `run_*.py`, `requirements.txt`, or
`pyproject.toml`, run the pinned gates and confirm they stay green:

```
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```

Constraints:
- Preserve `src/qtr` at 100% statement + branch coverage (`fail_under = 100`).
- Do not relax `fail_under`, drop `-W error`, or remove the format check.
- Do not modify published artifacts, gate thresholds, verdicts, or certified
  numbers; H1–H30 hypothesis space remains exhausted; no grid re-runs.
- Keep `qtr` uninstalled (bare clone) unless a test explicitly requires
  installation; restore bare-clone state afterwards.
- Never commit without an explicit user request.
