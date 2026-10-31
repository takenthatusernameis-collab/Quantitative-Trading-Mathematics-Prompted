# HANDOFF_CURRENT_SESSION — session complete (H80: `statistical_power_analysis` fail-closed on degenerate inputs)

## State
- Working tree: 2 modified files (`src/qtr/validation/statistics.py`, `tests/test_statistics.py`).
  No commit made (no-commit-without-explicit-request rule).
- HEAD `b170f18` on `main`; `main == origin/main` (up to date).
- `.github/workflows/gates.yml` tracked in HEAD (blob `a8126b8`); CI gates present.
- Package `qtr` not installed (bare clone). `PYTHONPATH=src` works.
- H1–H30 exhausted; hypotheses up to H80 documented.

## What changed
- `src/qtr/validation/statistics.py:761` (`statistical_power_analysis`) — added a
  degenerate-input guard before the closed form. The function now returns `0`
  when any operand is non-positive or non-finite:
  - `effect_size <= 0` or not finite (the denominator; an exact zero makes the
    required sample size infinite, a negative one is a sign error the formula
    squares away);
  - `std <= 0` or not finite (the other numerator factor);
  - `alpha` not in `(0, 1)` (the `norm.ppf(1 - alpha / 2)` argument is only
    finite there; `alpha <= 0` -> ppf(+1) = +inf, `alpha >= 1` -> ppf(<=0.5),
    and past 1 the argument goes negative and ppf returns nan);
  - `power` not in `(0, 1)` (the `norm.ppf(power)` argument is only finite
    there; `power <= 0` -> ppf(0) = -inf, `power >= 1` -> ppf(+1) = +inf).
  The fail-closed value is `0` (no sample size can be justified), matching the
  way `sharpe_ratio` and `compare_to_benchmark` fail closed on the same input
  classes. For every input in the valid domain the arithmetic is
  bit-identical to before: the guard only short-circuits the degenerate cases.
- `tests/test_statistics.py` — added 21 tests to `TestStatisticalPowerAnalysis`
  (was 4, now 25):
  - four parametrised fail-closed suites (effect_size, std, alpha, power), 20
    cases covering zero, negative, above-one, `inf`, `-inf` and `nan`;
  - `test_all_degenerate_inputs_raise_no_warning_or_exception` — a behavioural
    negative control that runs every degenerate input under
    `warnings.simplefilter("error")` and requires `0` with no warning and no
    exception (the pre-fix path emitted `RuntimeWarning: divide by zero` for
    an exact-zero effect size and raised `OverflowError`/`ValueError` for the
    non-finite operands).

## What was actually verified
- Defect reproduced on HEAD `b170f18` before changing anything:
  `statistical_power_analysis(0.0)` raised `OverflowError: cannot convert float
  infinity to integer` (with a `RuntimeWarning: divide by zero`); the same for
  `std=inf`, `alpha=0`, `power=0`; `statistical_power_analysis(0.5, alpha=1.0)`
  returned `6` and `alpha=1.5` returned `1` — finite but nonsense answers; and
  `effect_size=nan` / `std=nan` raised `ValueError: cannot convert float NaN to
  integer`. A pure function that every caller treats as returning an `int` was
  raising out of it on an input the record actually contains (a flat effect, a
  synthetic fixture, a non-finite std reaching a function with no caller to
  filter for it).
- Negative control: with the guard stripped, the 21 new tests fail 18/18 on the
  pre-fix code (the seven that stay green are the valid-domain tests); with the
  guard restored they pass 25/25.
- Valid domain bit-identical: `statistical_power_analysis(0.5, 0.05, 0.8, 1.0)`
  and the four other pinned cases match the closed form exactly.
- `python -m ruff check src tests run_*.py` → **All checks passed!**
- `python -m ruff format --check src tests run_*.py` → **105 files already formatted**
- `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`
  → **2200 passed, 16 skipped** (was 2179; +21 are the new tests); `src/qtr`
  **1181 stmts / 378 branches / 0 missed / 0 partial / 100.00%** (required
  coverage reached; the guard added 2 statements and 2 branches, both covered).
- `git diff --stat` → only the two intended files; no published artifact, gate
  threshold, verdict or certified number touched; no grid re-run.

## What remains unresolved
- The fix is uncommitted; committing requires explicit user approval.
- Items in `FINAL_REPORT.md` §H53–§H61 remain disclosed (not quantified); no gate impact.

## Approaches already failed
- None this session. The defect was a direct extension of the pattern the
  previous sessions established (`sharpe_ratio` §H62, `compare_to_benchmark`
  §H61/§H79): a pure statistic function with no caller-side filtering that
  divides by an operand and had no guard for the degenerate input class. The
  fix reuses the same `np.isfinite(...) and ... > 0` / `0 < x < 1` idiom and
  the same fail-closed value, so it is consistent with the codebase rather
  than a new convention.

## One precise next task
**Maintain baseline health.** No further code change needed now. On any future
change under `src/qtr`, `tests/`, `run_*.py`, `requirements.txt`, or
`pyproject.toml`, run the pinned gates and confirm they stay green:

```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```

Constraints: keep `src/qtr` at 100% statement + branch coverage (`fail_under = 100`);
do not relax `fail_under`, drop `-W error`, or remove the format check; do not
modify published artifacts, gate thresholds, verdicts or certified numbers;
H1–H30 exhausted; keep `qtr` uninstalled unless a test explicitly requires it;
never commit without explicit user request.

(End of file - total 64 lines)