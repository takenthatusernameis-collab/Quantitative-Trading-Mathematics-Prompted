# Next task — Baseline maintenance (verified on HEAD 13dd2d3; H79 applied)

## Status (this session)
Executed H79: repaired the third `compare_to_benchmark` guard. Gates re-run and green.

Verified actual state:
- HEAD `13dd2d3` on `main`; `main == origin/main` (up to date).
- Working tree: `M src/qtr/validation/statistics.py`, `M tests/test_statistics.py` (uncommitted).
- `.github/workflows/gates.yml` tracked in HEAD.
- `python -m ruff check src tests run_*.py` → All checks passed.
- `python -m ruff format --check src tests run_*.py` → 105 files already formatted.
- `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` → 2179 passed, 13 skipped; `src/qtr` 1179 stmts / 376 branches / 100.00%.
- Package `qtr` not installed (bare clone state confirmed).

## What changed
- `src/qtr/validation/statistics.py:683` — CAPM beta/alpha guard `bench.std(ddof=0) > 0`
  → `np.isfinite(bench_std) and bench_std > 1e-15` (same tolerance as the IR and
  t-test guards in the same function). Near-constant benchmark now yields
  `beta == 0`, `alpha_annualized == 0` instead of garbage `beta ≈ 1.03` / `alpha ≈ 0.125`.
- `tests/test_statistics.py` — added beta/alpha fail-closed assertions to the
  existing near-constant-benchmark regression test.

## What was actually verified
- Defect reproduced on HEAD before the change: `beta=1.025…`, `alpha_annualized=0.125…`
  on a benchmark with `std ≈ 9.6e-20`, while IR and t-test both reported 0.0.
- Exact-zero and all-non-finite benchmarks already returned `beta=0`/`alpha=0`, so
  the change is a tolerance tightening, not a behavior change for previously-correct input.
- All three pinned gates green with evidence above.

## What remains unresolved
- The fix is uncommitted; committing requires explicit user approval.

## Approaches already failed
None this session.

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
- H1–H30 exhausted; hypotheses up to H79 documented.
- Keep package behavior consistent with src layout; editable install is fine locally
  but do not commit build artifacts/secrets/caches.
- Never commit without explicit user request.

(End of file - total 45 lines)