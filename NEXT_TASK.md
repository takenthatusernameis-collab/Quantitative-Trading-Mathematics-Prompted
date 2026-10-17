# NEXT TASK

Ruff format has now been applied to the entire repo:
- `ruff check src tests run_*.py` -> All checks passed.
- `ruff format --check src tests run_*.py` -> All 61 files formatted.
- `pytest -q` -> 359 passed (semantics preserved).

Working tree: 27 `src/`/`tests/` files modified but uncommitted
(formatting only). Branch HEAD `8cead58` up to date with `origin/main`.

Precise next task:
1. Commit the 27 formatted files (`git add src tests && git commit`) and
   push to `origin/main`.
2. Verify persistence (`git status` clean, remote in sync).
3. Declare the free-data phase complete — no bounded task remains under
   current constraints; paid hourly futures data work is out of scope.

Constraints:
- Do not re-open any ruff lint rule (sweep finished).
- `src/`/`tests/` changes are formatting-only; no semantic changes.
- Free-data hypothesis space (H1–H25) exhausted; paid data out of scope.

(End of file)
