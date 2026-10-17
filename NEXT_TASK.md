# NEXT TASK

No bounded task remains under current constraints. The ruff lint sweep is
complete and `ruff format` has been applied to all `run_*.py` files:

- `ruff check src tests` -> All checks passed.
- `ruff check run_*.py` -> All checks passed (was 4 errors; fixed as `57b9a4f`).
  - SIM102 (run_h10:208, run_h23:211): `elif` had no `else` clause, so
    collapsing the nested `if can_trade` into the `elif` condition is
    behavior-preserving; the `can_trade` gate is retained.
  - PERF102 (run_h11:223, run_h11:403): loop variable `sym` was unused in
    both bodies; `.items()` -> `.values()` is safe.
- `ruff format --check run_*.py` -> All 28 files formatted (26 reformatted
  this session, 2 already formatted).
- `pytest -q` -> 359 passed.

Working tree: 26 `run_*.py` files modified but uncommitted. Branch ahead of
`origin/main` by 2 commits, not yet pushed.

Constraints:
- Do not touch `src/` or `tests/` — clean and must stay clean.
  (`ruff format` debt remains: 8 `src/` files and 53 `tests/` files, but the
  hands-off constraint blocks formatting them.)
- The free-data hypothesis space (H1–H25) is exhausted; no bounded
  free-data experiment remains. Paid hourly futures data work is out of
  free-data scope.

If the next agent has new evidence (e.g. paid data access, a new ruff class,
or a reproducible bug), re-open scope. Otherwise declare the free-data phase
complete. Candidate next actions: (1) commit + push the 26 formatted
`run_*.py` files to make progress durable, (2) lift the `src/`/`tests/`
constraint and run `ruff format` there too.

(End of file - total 21 lines)