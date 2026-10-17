# NEXT TASK

**Extend the ruff sweep to the remaining style rules in `run_*.py` —
specifically the 18 `EXE001` sites.**

The `EXE001` errors are the largest remaining class and are a one-line,
zero-risk fix: `chmod +x` the 18 `run_*.py` scripts that carry a shebang.
Verify with `ruff check run_*.py` (expect 8 errors: 4 RUF046, 2 SIM102,
2 PERF102) and confirm the scripts still run before committing.

Constraints:
- Do not touch `src/` or `tests/` — they are clean and must stay clean.
- Do not change the `EXE001` fix to anything other than making the file
  executable; the shebangs are intentional (`#!/usr/bin/env python3`).
- After the chmod, re-run `pytest -q` (359/359) and
  `ruff check src tests` to confirm nothing regressed.
- Commit with a message matching the repo style.

## Context

Session 13 (commit `68fdf8d`) cleaned up the F-rule ruff debt in
`run_*.py` (37 unused variables, 26 intentional blind-except annotations,
one genuine f-string bug, one no-op self-assignment). The remaining 26
ruff errors are all style-only and were deliberately left untouched; this
task addresses the largest of those classes.

See `HANDOFF.md` for the full session record, including approaches that
already failed (line-number-based bulk edits caused two real bugs; use
content-based edits with verification instead).