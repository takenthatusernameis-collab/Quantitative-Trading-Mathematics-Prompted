# Next task — Baseline maintenance (verified on HEAD 1d4f411)

## Status (this session)
Executed the standing "maintain baseline health" task on HEAD `1d4f411`:
ruff check/format green; full gates green (2200 passed, 16 skipped, 100% coverage); working tree clean.

## What changed
- None to source/tests/runners/artifacts/gates/thresholds/verdicts/certified numbers.
- Updated `NEXT_TASK.md` to reflect current HEAD.

## What was actually verified
- HEAD `1d4f411` on `main`; clean working tree.
- `.github/workflows/gates.yml` present and tracked.
- `python -m ruff check src tests run_*.py` → All checks passed.
- `python -m ruff format --check src tests run_*.py` → 106 files already formatted.
- `PYTHONPATH=src timeout 2400 python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` → **2200 passed, 16 skipped**; `src/qtr` **1181 stmts / 378 branches / 0 missed / 0 partial / 100.00%**

## What remains unresolved
- Items in `FINAL_REPORT.md` §H53–§H61 remain disclosed (not quantified); no gate impact.
- Older handoff files reference stale HEADs; treat as historical narrative.

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
- H1–H30 exhausted; hypotheses up to H80 documented.
- Keep package behavior consistent with src layout; do not commit build artifacts/secrets/caches.
- Never commit without explicit user request.
