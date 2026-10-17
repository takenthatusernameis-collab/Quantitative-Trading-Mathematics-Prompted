# NEXT TASK

No bounded task remains. The RUF046 cleanup (4 `int(round(...))` sites) is
already committed as `679eee5` and verified:

- `ruff check run_*.py` -> 4 errors (2 SIM102, 2 PERF102), all deliberate,
  left as-is per prior constraints.
- `ruff check src tests` -> All checks passed.
- `pytest -q` -> 359 passed.

Constraints:
- Do not touch `src/` or `tests/` — clean and must stay clean.
- Do not auto-fix SIM102 (run_h10:208, run_h23:211) or PERF102
  (run_h11:223, run_h11:403) — unsafe fixes would change runtime behavior.
- The free-data hypothesis space (H1–H25) is exhausted; no bounded
  free-data experiment remains. Paid hourly futures data work is out of
  free-data scope.

If the next agent has new evidence (e.g. paid data access, a new ruff class,
or a reproducible bug), re-open scope. Otherwise declare the free-data phase
complete.
