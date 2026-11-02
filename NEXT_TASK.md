# Next task — Baseline maintenance (verified on HEAD 91d0840)

## Status (this session)
Baseline verified green on HEAD `91d0840` after the H81 fail-closed guards in
`src/qtr/validation/statistics.py`. `regime_analysis` and `capacity_estimate`
now fail closed on degenerate input; 12 new regression tests added; ruff
check/format green; full gates green (2257 passed, 16 skipped, 100%
coverage). Working tree has 2 uncommitted file modifications.

## What changed
- `src/qtr/validation/statistics.py` and `tests/test_statistics.py` (see
  `HANDOFF.md` for the full diff summary).
- No source, test, runner, artifact, gate threshold, verdict or certified
  number was modified beyond the H81 fixes and their tests.

## What was actually verified (this session, on HEAD 91d0840)
- `git status --short` → 2 modified files (uncommitted); HEAD `91d0840` on
  `main`; `main == origin/main` (up to date).
- `.github/workflows/gates.yml` present and tracked.
- `python -m ruff check src tests run_*.py` → All checks passed.
- `python -m ruff format --check src tests run_*.py` → 106 files already
  formatted.
- `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch
  --cov-report=term-missing` → **2257 passed, 16 skipped**; `src/qtr`
  **1184 stmts / 384 branches / 0 missed / 0 partial / 100.00%**.
- Negative control: with the source reverted, 10 of the 12 new tests fail on
  the pre-fix code; all 154 pass with the fix restored.
- Valid domain bit-identical: `capacity_estimate` and `regime_analysis` match
  pre-fix output to 10 decimal places over finite 400-bar series.

## What remains unresolved
- Items in `FINAL_REPORT.md` §H53–§H61 remain disclosed (not quantified); no
  gate impact.

## Approaches already failed
- None this session. Baseline restored green; the two degenerate-input defects
  were fixed at the source (smallest reversible change).

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
- H1–H30 exhausted; hypotheses up to H81 documented.
- Keep package behavior consistent with src layout; do not commit build
  artifacts/secrets/caches.
- Never commit without explicit user request.

(End of file)