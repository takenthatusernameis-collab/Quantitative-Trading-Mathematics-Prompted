# Next task — Baseline maintenance (verified on HEAD b170f18; H80 applied)

## Status (this session)
Executed H80: `statistical_power_analysis` now fails closed on every degenerate
operand. Gates re-run and green.

Verified actual state:
- HEAD `b170f18` on `main`; `main == origin/main` (up to date).
- Working tree: `M src/qtr/validation/statistics.py`, `M tests/test_statistics.py` (uncommitted).
- `.github/workflows/gates.yml` tracked in HEAD (blob `a8126b8`).
- `python -m ruff check src tests run_*.py` → All checks passed.
- `python -m ruff format --check src tests run_*.py` → 105 files already formatted.
- `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` → 2200 passed, 16 skipped; `src/qtr` 1181 stmts / 378 branches / 100.00%.
- Package `qtr` not installed (bare clone state confirmed).

## What changed
- `src/qtr/validation/statistics.py:761` — `statistical_power_analysis` gained a
  degenerate-input guard. It now returns `0` when `effect_size`, `std`, `alpha`
  or `power` is non-positive or non-finite (zero, negative, above-one, `inf`,
  `-inf`, `nan`). The pre-fix closed form divided by `effect_size` and took
  `norm.ppf` of `1 - alpha / 2` and of `power`, so an exact-zero effect size
  emitted `RuntimeWarning: divide by zero` and `OverflowError`, a non-finite
  operand raised `OverflowError`/`ValueError`, and `alpha >= 1` returned a
  finite but nonsense answer (6 for `alpha=1.0`, 1 for `alpha=1.5`).
- `tests/test_statistics.py` — added 21 tests to `TestStatisticalPowerAnalysis`
  (4 → 25): four parametrised fail-closed suites over effect_size/std/alpha/
  power (20 cases) plus a behavioural negative control that runs every
  degenerate input under `warnings.simplefilter("error")`.

## What was actually verified
- Defect reproduced on HEAD before the change: `statistical_power_analysis(0.0)`
  raised `OverflowError` (with a `divide by zero` warning); `std=inf`,
  `alpha=0`, `power=0` raised likewise; `effect_size=nan`/`std=nan` raised
  `ValueError`; `alpha=1.0` returned `6`, `alpha=1.5` returned `1`.
- Negative control: the 21 new tests fail 18/21 on the pre-fix code (the seven
  valid-domain tests stay green); all 25 pass with the guard restored.
- Valid domain bit-identical: the five pinned cases match the closed form
  exactly.
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
- H1–H30 exhausted; hypotheses up to H80 documented.
- Keep package behavior consistent with src layout; editable install is fine locally
  but do not commit build artifacts/secrets/caches.
- Never commit without explicit user request.

(End of file - total 56 lines)