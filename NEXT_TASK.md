# Next task — coverage gate restored (verified on HEAD f5e047d)

## Status
The pinned `fail_under = 100` coverage gate was **broken** by commit `f5e047d` (the `equity_cost_bps` element-wise rewrite). It is now **restored** by reverting that function's body to the original implementation. Working tree has 1 uncommitted change in `src/qtr/backtest/engine.py`. Do not commit without explicit user request.

## What changed
- `src/qtr/backtest/engine.py` — `equity_cost_bps` body reverted to the commit-`49f9898` version (the simple scalar/Series guard). The `f5e047d` rewrite added 10 uncovered statements + 5 uncovered branches for an unreachable symmetric Series/scalar mix; coverage fell to 99.09% and tripped the CI `research_gates` job.

## What was actually verified
- `git log --oneline -1` → `f5e047d`
- `python -m ruff check src tests run_*.py` → **All checks passed!**
- `python -m ruff format --check src tests run_*.py` → **105 files already formatted**
- `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` → **2278 passed, 16 skipped**; `src/qtr` **1207 stmts / 402 branches / 0 missed / 0 partial / 100.00%**.
- `crypto_cost_bps` and `future_cost_per_contract` are byte-identical to HEAD; only `equity_cost_bps` differs.

## What remains unresolved
- The revert is uncommitted; next step is to commit (user must request).
- Items in `FINAL_REPORT.md` §H53–§H61 remain disclosed (not quantified); no gate impact.
- `engine.py` docstrings cite `§H83` (a forward reference to a not-yet-written hypothesis); cosmetic, pre-existing.

## Approaches already failed
- **The `f5e047d` element-wise dispatch approach.** It attempted to handle a symmetric Series/scalar operand mix that no caller produces (the engine always passes scalar `spread_bps` + Series `adv_pct`; external callers pass scalars for both). The added branches were unreachable and broke the 100% coverage invariant. The original guard already handles the real engine path element-wise and fails closed on degenerate Series input, so reverting was the correct fix.

## One precise next task
**Commit the coverage-gate fix** (`src/qtr/backtest/engine.py`) only on explicit user request, then maintain baseline health: on any future change under `src/qtr`, `tests/`, `run_*.py`, `requirements.txt`, or `pyproject.toml`, run:

```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```

Constraints: keep `src/qtr` at 100% statement + branch coverage; do not relax `fail_under`, drop `-W error`, or remove the format check; do not modify published artifacts/gate thresholds/verdicts/certified numbers; never commit without explicit user request.

(End of file - total 33 lines)