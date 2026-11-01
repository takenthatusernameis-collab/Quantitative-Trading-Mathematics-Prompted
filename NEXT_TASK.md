# Next task — Baseline maintenance (verified on HEAD 501b4d0)

## Status (this session)
Executed the standing "maintain baseline health" task on HEAD `501b4d0`:
ruff check/format green; no code change needed.

Verified actual state:
- HEAD `501b4d0` on `main`; `main == origin/main` (up to date). Working tree
  clean; H80 fix is in `9ba00a8`. Latest commit is a handoff commit.
- `.github/workflows/gates.yml` tracked in HEAD.
- `python -m ruff check src tests run_*.py` → All checks passed.
- `python -m ruff format --check src tests run_*.py` → 105 files already formatted.
- Prior full gates on `9ba00a8`: 2200 passed, 16 skipped; `src/qtr` 1181 stmts / 378 branches / 100.00%.
- Package `qtr` not installed (bare clone state confirmed).

## What changed
- None. No source, test, runner, artifact, gate threshold, verdict or certified
  number modified.

## What was actually verified
- Lint/format gates green on current HEAD; `git status --short` empty. Full test+coverage gates were verified green on `9ba00a8`.

## What remains unresolved
- Items in `FINAL_REPORT.md` §H53–§H61 remain disclosed (not quantified); no gate impact.
- Older handoff files reference stale HEADs; treat as historical narrative.

## Approaches already failed
- None this session.

## One precise next task
**Maintain baseline health.** No code change needed now. On any future change under
`src/qtr`, `tests/`, `run_*.py`, `requirements.txt`, or `pyproject.toml`, run the
pinned gates and confirm they stay green:

```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```

Constraints:
- Preserve `src/qtr` at 100% statement + branch coverage (`fail_under = 100`).
- Do not relax `fail_under`, drop `-W error`, or remove the format check.
- Do not modify published artifacts, gate thresholds, verdicts, or certified numbers.
- H1–H30 exhausted; hypotheses up to H80 documented.
- Keep package behavior consistent with src layout; do not commit build artifacts/secrets/caches.
- Never commit without explicit user request.

(End of file)
