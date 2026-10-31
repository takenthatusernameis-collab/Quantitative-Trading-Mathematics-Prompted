# HANDOFF — session complete (H80: `statistical_power_analysis` fail-closed on degenerate inputs)

## State
- Repository at HEAD `b170f18`. Working tree contains two modified files,
  `src/qtr/validation/statistics.py` and `tests/test_statistics.py` (the H80 fix
  and its 21 tests). No commit made (no-commit-without-explicit-request rule).
- HEAD `b170f18` on `main`; `main == origin/main` (up to date).
- `.github/workflows/gates.yml` tracked in HEAD (blob `a8126b8`); CI gates present.
- Package `qtr` not installed (bare clone). `PYTHONPATH=src` works.
- H1–H30 exhausted; hypotheses up to H80 documented.

## What changed (this session)
- `src/qtr/validation/statistics.py:761` (`statistical_power_analysis`) — added a
  degenerate-input guard before the closed form. The function now returns `0`
  when `effect_size`, `std`, `alpha` or `power` is non-positive or non-finite:
  zero, negative, above-one, `inf`, `-inf` or `nan`. The guard uses the same
  `np.isfinite(...) and ... > 0` / `0 < x < 1` idiom and the same fail-closed
  value (`0`) as `sharpe_ratio` (§H62) and `compare_to_benchmark` (§H61/§H79),
  so it is consistent with the codebase rather than a new convention. For every
  input in the valid domain the arithmetic is bit-identical to before.
- `tests/test_statistics.py` — added 21 tests to `TestStatisticalPowerAnalysis`
  (4 → 25): four parametrised fail-closed suites over effect_size/std/alpha/
  power (20 cases) plus a behavioural negative control that runs every
  degenerate input under `warnings.simplefilter("error")`.

## The defect
`statistical_power_analysis` is a pure function with no caller-side filtering,
and its closed form divides by `effect_size` and takes `norm.ppf(1 - alpha / 2)`
and `norm.ppf(power)`. Reproduced on HEAD `b170f18` before the change:
- `statistical_power_analysis(0.0)` → `RuntimeWarning: divide by zero` then
  `OverflowError: cannot convert float infinity to integer`;
- `std=inf`, `alpha=0`, `power=0` → the same `OverflowError`;
- `effect_size=nan`, `std=nan` → `ValueError: cannot convert float NaN to integer`;
- `alpha=1.0` → returned `6`; `alpha=1.5` → returned `1` (finite but nonsense:
  `norm.ppf(0.5) == 0.0`, so the z-score vanished and the answer was meaningless).

A function every caller treats as returning an `int` was raising out of it on an
input the record actually contains (a flat effect, a synthetic fixture, a
non-finite std reaching a function with no caller to filter for it). It is the
same class of defect §H60–§H62 and §H79 closed in the validation core.

## What was actually verified
- Defect reproduced on HEAD before changing anything (evidence above).
- Negative control: with the guard stripped, the 21 new tests fail 18/18 on the
  pre-fix code (the seven valid-domain tests stay green); all 25 pass with the
  guard restored.
- Valid domain bit-identical: `statistical_power_analysis(0.5, 0.05, 0.8, 1.0)`
  and the four other pinned cases match the closed form exactly.
- `python -m ruff check src tests run_*.py` → **All checks passed!**
- `python -m ruff format --check src tests run_*.py` → **105 files already formatted**
- `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`
  → **2200 passed, 16 skipped**; `src/qtr` **1181 stmts / 378 branches / 0
  missed / 0 partial / 100.00%** (required coverage reached).
- `git diff --stat` → only the two intended files; no published artifact, gate
  threshold, verdict or certified number touched; no grid re-run.

## What remains unresolved
- The fix is uncommitted. Committing requires explicit user approval.
- Items in `FINAL_REPORT.md` §H53–§H61 remain disclosed (not quantified); no gate impact.

## Approaches already tried / failed (and why)
- None this session. The defect was a direct extension of the pattern the
  previous sessions established (§H62 `sharpe_ratio`, §H61/§H79
  `compare_to_benchmark`): a pure statistic function with no caller-side
  filtering that divides by an operand and had no guard for the degenerate
  input class. The fix reuses the existing idiom and fail-closed value rather
  than introducing a new convention.

## One precise next task (with evidence and constraints)
**Maintain baseline health.** No further code change needed now. On any future
change under `src/qtr`, `tests/`, `run_*.py`, `requirements.txt`, or
`pyproject.toml`, run the pinned gates and confirm they stay green:

```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```

- **Requires explicit user approval to commit** (no-commit-without-explicit-
  request rule). Do not commit without it.
- If approved: `git add src/qtr/validation/statistics.py tests/test_statistics.py &&
  git commit -m "H80: statistical_power_analysis fails closed on degenerate
  operands"`, then verify `git status` is clean and re-run the ruff + pytest
  coverage gates once more.
- Do not modify any gate command, `fail_under`, `-W error`, or the format
  check. Keep commands identical to `AGENTS.md`/`pyproject.toml`. No published
  artifact/gate threshold/verdict/certified number may change; H1–H30 exhausted;
  `src/qtr` coverage stays 100% (stmt+branch); qtr left uninstalled unless a
  test requires install (then restore bare-clone state after).

## Constraints carried forward
- No published artifact, gate threshold, verdict or certified number may be
  modified. No grid may be re-run. H1–H30 exhausted.
- `src/qtr` coverage gate stays 100% (statement + branch).
- Ruff lint and format gates stay clean.
- qtr left uninstalled (bare clone); do not `pip install -e .` unless a test
  requires it, restore bare-clone state afterwards.
- Never commit without explicit user request.

(End of file - total 83 lines)