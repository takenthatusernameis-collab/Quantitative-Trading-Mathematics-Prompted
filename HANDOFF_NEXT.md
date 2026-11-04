# HANDOFF_NEXT — session complete (H84 defect fix; gates green on uncommitted tree)

## State
- Working tree has **uncommitted changes** to `src/qtr/backtest/engine.py` and
  `tests/test_cost_model.py` (the H84 fix; not committed — committing requires
  explicit user approval). HEAD `c2d7250` on `main`; `main == origin/main`.
- `.github/workflows/gates.yml` tracked in HEAD; CI gates present.
- `PYTHONPATH=src` works. H1–H30 exhausted; hypotheses up to H84 documented.

## What changed
- `src/qtr/backtest/engine.py` — `get_future_contract_multiplier` now guards its
  operand the same way its three CostModel siblings already did under §H83. It
  was the only CostModel cost method with no guard, and the only one whose
  return value is divided into a published number (engine.py:483).
- `tests/test_cost_model.py` — six additions to `TestCostModelDegenerateInput`,
  including a behavioural negative control that reconstructs the pre-guard
  method.
- `FINAL_REPORT.md` — new **§H84** section.

## What was actually verified
- `git status --short` → `src/qtr/backtest/engine.py`, `tests/test_cost_model.py`,
  `FINAL_REPORT.md` modified; everything else clean.
- The six new tests **fail on the pre-fix code** (reverted guard) with the
  expected errors, then pass with the fix restored.
- `python -m ruff check src tests run_*.py` → **All checks passed!**
- `python -m ruff format --check src tests run_*.py` → **105 files already formatted**
- `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch
  --cov-report=term-missing` → **2295 passed, 16 skipped**; `src/qtr`
  **1215 stmts / 406 branches / 0 missed / 0 partial / 100.00%**.

## What remains unresolved
- The H84 fix is uncommitted; committing requires explicit user approval.
- Items in `FINAL_REPORT.md` §H53–§H61 remain disclosed (not quantified); no gate
  impact.
- H1–H30 exhausted; hypotheses up to H84 documented.

## Approaches already failed
- None this session. The defect was found by direct inspection of the fourth
  CostModel cost method against the guard its three siblings already carried.

## One precise next task
**Commit or roll back the H84 change.** The working tree carries an uncommitted
defect fix that all pinned gates pass. If the user approves, commit only
`src/qtr/backtest/engine.py`, `tests/test_cost_model.py` and `FINAL_REPORT.md`
with a message matching the repo style, then re-run the pinned gates to confirm
they stay green on the committed tree:

```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```

Constraints: keep `src/qtr` at 100% statement + branch coverage (`fail_under =
100`); do not relax `fail_under`, drop `-W error`, or remove the format check;
do not modify published artifacts, gate thresholds, verdicts or certified
numbers; H1–H30 exhausted; hypotheses up to H84 documented; never commit without
explicit user request. CI gates workflow is present in `.github/workflows/gates.yml`.

(End of file)