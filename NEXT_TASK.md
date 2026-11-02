# Next task — Baseline maintenance (verified on HEAD 0e8394c)

## Status (this session)
Baseline verified green on HEAD `0e8394c`. Working tree has 1 uncommitted
documentation-only modification (`FINAL_REPORT.md`: H81 now has its own
standalone section). All gates pass: ruff check/format green; full gates green
(2274 passed, 16 skipped, 100% coverage).

## What changed
- `FINAL_REPORT.md` — added the missing `## H81` section (between H80 and H82)
  so the record's hypothesis index points at H81 rather than describing it only
  inside the H82 section. No source, test, runner, artifact, gate threshold,
  verdict or certified number moved.

## What was actually verified (this session, on HEAD 0e8394c)
- `git status --short` → only `FINAL_REPORT.md` modified.
- `python -m ruff check src tests run_*.py` → All checks passed.
- `python -m ruff format --check src tests run_*.py` → 106 files already formatted.
- `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` → **2274 passed, 16 skipped**; `src/qtr` **1191 stmts / 388 branches / 0 missed / 0 partial / 100.00%**.
- `## H81` is now present exactly once, in numeric order between H80 and H82.
- All 33 `run_*.py` files parse and import; all 2290 tests collect.

## What remains unresolved
- The `FINAL_REPORT.md` edit is uncommitted; committing requires explicit user
  approval.
- Items in `FINAL_REPORT.md` §H53–§H61 remain disclosed (not quantified); no gate impact.

## Approaches already failed
- Two audit candidates (`validate_strategy`, `_calculate_metrics` missing
  degenerate-input guards) were tested and rejected: their `profit_factor ==
  np.inf` on flat/zero/all-NaN series is the pinned boundary convention
  (`test_engine_metric_agreement.py:271`), and the shared-metric contract holds
  across every non-finite input. No source change was made.

## One precise next task
**Maintain baseline health.** On any future change under `src/qtr`, `tests/`,
`run_*.py`, `requirements.txt`, or `pyproject.toml`, run the pinned gates and
confirm they stay green:

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

(End of file)