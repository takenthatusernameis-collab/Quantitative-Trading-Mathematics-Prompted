# Next task — Baseline maintenance (verified on HEAD fce1143)

## Status (this session)
Restored baseline health on HEAD `fce1143`: the `stressed_cost_test`
fail-closed defect in `src/qtr/validation/statistics.py` was fixed at the
source (10 previously-failing tests now all pass); ruff check/format green;
full gates green (2234 passed, 16 skipped, 100% coverage); working tree has
2 uncommitted file modifications.

## What changed
- `src/qtr/validation/statistics.py` and `tests/test_statistics.py` (see
  `HANDOFF_CURRENT_SESSION.md` for the full diff summary).
- No source, test, runner, artifact, gate threshold, verdict or certified
  number was modified beyond the `stressed_cost_test` fix and its test.

## What was actually verified (this session, on HEAD fce1143)
- `git status --short` → 2 modified files (uncommitted); HEAD `fce1143` on
  `main`; `main == origin/main` (up to date).
- `.github/workflows/gates.yml` present and tracked.
- `python -m ruff check src tests run_*.py` → All checks passed.
- `python -m ruff format --check src tests run_*.py` → 106 files already
  formatted.
- `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch
  --cov-report=term-missing` → **2234 passed, 16 skipped**; `src/qtr`
  **1172 stmts / 376 branches / 0 missed / 0 partial / 100.00%**.

## What remains unresolved
- Items in `FINAL_REPORT.md` §H53–§H61 remain disclosed (not quantified); no
  gate impact.

## Approaches already failed
- None this session. Baseline restored green; no defect remains.

## One precise next task
**Maintain baseline health.** No code change needed now. On any future change
under `src/qtr`, `tests/`, `run_*.py`, `requirements.txt`, or
`pyproject.toml`, run the pinned gates and confirm they stay green:

```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```

Constraints:
- Preserve `src/qtr` at 100% statement + branch coverage (`fail_under = 100`).
- Do not relax `fail_under`, drop `-W error`, or remove the format check.
- Do not modify published artifacts, gate thresholds, verdicts, or certified
  numbers.
- H1–H30 exhausted; hypotheses up to H61 documented.
- Keep package behavior consistent with src layout; do not commit build
  artifacts/secrets/caches.
- Never commit without explicit user request.
