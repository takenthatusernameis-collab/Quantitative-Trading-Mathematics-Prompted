# NEXT TASK

No bounded task remains. The ruff sweep is complete:

- `ruff check src tests` -> All checks passed.
- `ruff check run_*.py` -> All checks passed (was 4 errors; fixed as `57b9a4f`).
  - SIM102 (run_h10:208, run_h23:211): `elif` had no `else` clause, so
    collapsing the nested `if can_trade` into the `elif` condition is
    behavior-preserving; the `can_trade` gate is retained.
  - PERF102 (run_h11:223, run_h11:403): loop variable `sym` was unused in
    both bodies; `.items()` -> `.values()` is safe.
- `pytest -q` -> 359 passed.

Constraints:
- Do not touch `src/` or `tests/` — clean and must stay clean.
- The free-data hypothesis space (H1–H25) is exhausted; no bounded
  free-data experiment remains. Paid hourly futures data work is out of
  free-data scope.

If the next agent has new evidence (e.g. paid data access, a new ruff class,
or a reproducible bug), re-open scope. Otherwise declare the free-data phase
complete.

(End of file - total 21 lines)