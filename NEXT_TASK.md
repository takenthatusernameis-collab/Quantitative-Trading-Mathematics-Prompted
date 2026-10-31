# Next task — Baseline maintenance (no pending code change)

## Status (this session)
Executed baseline verification in current HEAD. No code changes made.

Verified actual state:
- HEAD `e98860b` on `main`; `main == origin/main` (up to date).
- Working tree clean (`git status --short` empty).
- `.github/workflows/gates.yml` tracked in HEAD.
- `python -m ruff check src tests run_*.py` → All checks passed.
- `python -m ruff format --check src tests run_*.py` → 105 files already formatted.
- `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` → 2176 passed, 13 skipped; `src/qtr` 1170 stmts / 376 branches / 100.00% (required coverage reached).
- Package `qtr` not installed (bare clone state confirmed).

## What changed
None to source/tests/runners/artifacts/gates/thresholds/verdicts/certified numbers.

## What was actually verified
- Git state clean and up to date.
- All three pinned gates green with evidence above.

## What remains unresolved
- Older handoff files reference different HEADs; treat as historical narrative.

## Approaches already failed
None this session.

## One precise next task
**Maintain baseline health.** No code change needed now. On any future change under `src/qtr`, `tests/`, `run_*.py`, `requirements.txt`, or `pyproject.toml`, run the pinned gates and confirm they stay green:

```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```

Constraints:
- Preserve `src/qtr` at 100% statement + branch coverage (`fail_under = 100`).
- Do not relax `fail_under`, drop `-W error`, or remove the format check.
- Do not modify published artifacts, gate thresholds, verdicts, or certified numbers.
- H1–H30 exhausted; hypotheses up to H78 documented.
- Keep package behavior consistent with src layout; editable install is fine locally but do not commit build artifacts/secrets/caches.
- Never commit without explicit user request.
