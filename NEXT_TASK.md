# Next task — §H83 forward-reference resolved (verified on HEAD 7a7f863)

## Status
The dangling `§H83` forward reference carried by `src/qtr/backtest/engine.py`
and `src/qtr/validation/statistics.py` is now **resolved** by a real §H83 section
in `FINAL_REPORT.md`. Working tree has 1 uncommitted change in
`FINAL_REPORT.md`. Do not commit without explicit user request.

## What changed
- `FINAL_REPORT.md` — new **§H83** section recording the `CostModel`
  degenerate-input guards (`equity_cost_bps`, `future_cost_per_contract`,
  `crypto_cost_bps`, and the `capacity_estimate` scalar guard) as an
  already-delivered hypothesis, so the four citation sites resolve. It is a
  narrative reconciliation of guards already verified under §H81; no source
  line moved and no published number changed.

## What was actually verified
- `grep -n "H83\|§H83" --include="*.py" --include="*.md" .` → all four citation
  sites (engine.py:72-73, engine.py:116-117, engine.py:170-171,
  statistics.py:716) now resolve against the new section.
- `git status --short` → clean before the change; `git diff --stat` →
  `FINAL_REPORT.md` only.
- `python -m ruff check src tests run_*.py` → **All checks passed!**
- `python -m ruff format --check src tests run_*.py` → **105 files already formatted**
- `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch
  --cov-report=term-missing` → **2286 passed, 16 skipped**; `src/qtr`
  **1209 stmts / 404 branches / 0 missed / 0 partial / 100.00%**
  (identical to the pre-change baseline; the report is outside the gate's
  `paths` filter, so CI is unaffected).

## What remains unresolved
- The §H83 section is a narrative reconciliation, not a new measurement; it
  moves no published number. Committing requires explicit user approval.
- Items in `FINAL_REPORT.md` §H53–§H61 remain disclosed (not quantified); no
  gate impact.
- H1–H30 exhausted; hypotheses up to H83 documented.

## Approaches already failed
- **No unhandled defect class found in `src/qtr`.** A systematic probe of the
  public API under `warnings.simplefilter("error")` (statistics, strategies,
  engine, cost model, config, experiment tracker) found every degenerate input
  already fail closed: the only failures were explicit `ValueError`s the
  contract requires (unknown strategy name, non-positive price panel refused
  by the engine's screen). The `benchmark_significance_gate(array p)`
  `TypeError` is unreachable from the library's own callers, which always pass
  a scalar p-value (the gate consumes the scalar `alpha_p_value` from
  `compare_to_benchmark`).

## One precise next task
**Maintain baseline health.** No further code change needed now. On any future
change under `src/qtr`, `tests/`, `run_*.py`, `requirements.txt`, or
`pyproject.toml`, run the pinned gates and confirm they stay green:

```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```

Constraints: keep `src/qtr` at 100% statement + branch coverage; do not relax
`fail_under`, drop `-W error`, or remove the format check; do not modify
published artifacts/gate thresholds/verdicts/certified numbers; never commit
without explicit user request.

(End of file - total 35 lines)