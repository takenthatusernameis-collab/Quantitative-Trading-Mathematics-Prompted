# Next task — Baseline maintenance (verified on HEAD 38723d6)

## Status
Baseline verified green on HEAD `38723d6`. Working tree clean.

## What changed
- None this session.

## What was actually verified
- `git log --oneline -1` → `38723d6`
- `git status --short` → empty
- `python -m ruff check src tests run_*.py` → **All checks passed!**
- `python -m ruff format --check src tests run_*.py` → **105 files already formatted**
- `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` → **2274 passed, 16 skipped**; `src/qtr` **1191 stmts / 388 branches / 0 missed / 0 partial / 100.00%**.
- `pytest --collect-only -q` → **2290 tests collected**.

## What remains unresolved
- Items in `FINAL_REPORT.md` §H53–§H61 remain disclosed (not quantified); no gate impact. H1–H30 exhausted; hypotheses up to H82 documented.

## Approaches already failed
- None this session.

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
- H1–H30 exhausted; hypotheses up to H82 documented.
- Keep package behavior consistent with src layout; do not commit build artifacts/secrets/caches.
- Never commit without explicit user request.
