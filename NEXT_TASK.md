# Next task — Baseline maintenance (verified on HEAD 38723d6)

## Status
Baseline restored green on HEAD `38723d6`. Working tree has UNCOMMITTED changes in `src/qtr/backtest/engine.py` and `tests/test_cost_model.py` (fix for 5 failing cost-model tests). Do not commit without explicit user request.

## What changed
- `src/qtr/backtest/engine.py` — `equity_cost_bps`/`crypto_cost_bps` guards made element-wise so per-bar Series ADV input no longer raises "truth value of a Series is ambiguous".
- `tests/test_cost_model.py` — added `TestCostModelDegenerateInput` (4 tests).

## What was actually verified
- `git log --oneline -1` → `38723d6`
- `python -m ruff check src tests run_*.py` → **All checks passed!**
- `python -m ruff format --check src tests run_*.py` → **105 files already formatted**
- `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` → **2278 passed, 16 skipped**; `src/qtr` **1203 stmts / 398 branches / 0 missed / 0 partial / 100.00%**.
- `pytest --collect-only -q` → **2294 tests collected**.

## What remains unresolved
- Changes are uncommitted; next step is to commit (user must request).
- Items in `FINAL_REPORT.md` §H53–§H61 remain disclosed (not quantified); no gate impact.

## Approaches already failed
- None this session. Baseline was broken by a reproducible bug (5 failures, one root cause at `engine.py:82`); fixed.

## One precise next task
**Commit the baseline fix** (`src/qtr/backtest/engine.py`, `tests/test_cost_model.py`) only on explicit user request, then maintain baseline health: on any future change under `src/qtr`, `tests/`, `run_*.py`, `requirements.txt`, or `pyproject.toml`, run:

```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```

Constraints: keep `src/qtr` at 100% statement + branch coverage; do not relax `fail_under`, drop `-W error`, or remove the format check; do not modify published artifacts/gate thresholds/verdicts/certified numbers; never commit without explicit user request.
