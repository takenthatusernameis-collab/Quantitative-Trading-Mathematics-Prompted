# NEXT TASK

Status: COMPLETE — free-data phase declared complete.

## Current state

- HEAD `ddd49c5` on `main`, in sync with `origin/main`; working tree clean.
- The 27 `ruff format`-reformatted `src/`/`tests/` files are committed in
  `d6eed70` and pushed (Session 18 task complete).
- `ruff format --check src tests run_*.py` -> 61 files formatted.
- `ruff check src tests run_*.py` -> All checks passed.
- `pytest -q` -> 359 passed (semantics preserved).

## Precise next task

None. No bounded task remains under current constraints:
- The free-data hypothesis space (H1–H25) is exhausted.
- Paid hourly futures data (required to widen the OOS window for the certified
  intraday futures TSMOM family H10/H22/H25) is out of free-data scope.

Resume only when paid hourly futures data becomes available. Evidence and
constraints: FINAL_REPORT.md §Conclusion; INEFFICIENCY_RANKING.md §17.

## Constraints

- Do not re-open any ruff lint rule (sweep finished).
- `src/`/`tests/` changes are formatting-only; no semantic changes.
- Paid data work is out of scope under current constraints.

(End of file)
