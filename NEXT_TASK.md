# Next task — Baseline maintenance (verified on HEAD c17c06c)

## Status (this session)
Baseline verified green on HEAD `c17c06c`. H82 fail-closed guard committed in previous
session (`tests/test_statistics.py` indentation fix); working tree clean.
All gates pass: ruff check/format green; full gates green (2274 passed, 16 skipped,
100% coverage).

## What changed
- Restored `tests/test_statistics.py` to a collectable state (H82).

## What was actually verified (this session, on HEAD c17c06c)
- `git status --short` → clean after handoff edits; HEAD `c17c06c` on `main`.
- `.github/workflows/gates.yml` present and tracked.
- `python -m ruff check src tests run_*.py` → All checks passed.
- `python -m ruff format --check src tests run_*.py` → 106 files already formatted.
- `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` → **2274 passed, 16 skipped**; `src/qtr` **1191 stmts / 388 branches / 0 missed / 0 partial / 100.00%**.

## What remains unresolved
- Items in `FINAL_REPORT.md` §H53–§H61 remain disclosed (not quantified); no gate impact.

## Approaches already failed
- None this session.

## One precise next task
**Maintain baseline health.** No code change needed now. On any future change
under `src/qtr`, `tests/`, `run_*.py`, `requirements.txt`, or `pyproject.toml`,
run the pinned gates and confirm they stay green:

```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```

Constraints:
- Preserve `src/qtr` at 100% statement + branch coverage (`fail_under = 100`).
- Do not relax `fail_under`, drop `-W error`, or remove the format check.
- Do not modify published artifacts, gate thresholds, verdicts, or certified numbers.
- H1–H30 exhausted; hypotheses up to H82 documented.
- Keep package behavior consistent with src layout; do not commit build artifacts/secrets/caches.
- Never commit without explicit user request.