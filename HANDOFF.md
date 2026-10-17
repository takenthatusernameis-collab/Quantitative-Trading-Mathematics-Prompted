# HANDOFF — Session 13 (Kilo)

## What changed

Committed `68fdf8d`: ruff cleanup sweep across the `run_*.py` experiment
scripts. Tree is clean; `src/` and `tests/` were already clean at HEAD
`7b456ac` (prior session's sweep).

- Removed 37 unused-variable sites (F841/RUF059) across 16 scripts.
  One was a genuine dropped computation: `run_h11_robustness_experiment.py`
  computed `fresh_bh` (a buy-and-hold benchmark on the fresh-OOS slice) and
  never compared it against the strategy. Removed; the fresh-OOS block now
  only evaluates the frozen config.
- Annotated 26 intentional blind-except sites with `# noqa: BLE001`
  (top-level experiment harnesses and advisory-metric blocks where
  catch-and-continue is the design).
- Fixed one genuine bug: `run_h7_intraday_tsmom_experiment.py:389` used a
  double-quote character inside a double-quoted f-string — invalid on
  Python < 3.12 (ruff flagged it; the project's ruff config targets 3.10).
- Removed a no-op self-assignment (`INITIAL_CAPITAL = INITIAL_CAPITAL`) in
  `run_h10_intraday_tsmom_pfopt_experiment.py` and added the missing
  `# noqa: F401` re-export annotation (h21/h22/h25 import it for test
  pinning).
- Converted 11 `%`-format prints to f-strings (UP031) and 3 `dict.keys()`
  to `dict` (SIM118) in `run_ddcv_experiment.py`, `run_h6_vix_ddcv_experiment.py`,
  `run_h13_oos_deflation_pf_audit.py`.

## What was verified

- `ruff check src tests` — clean.
- `ruff check run_*.py --select F` (F401/F841/F821/F811) — clean.
- `pytest -q` — 359 passed (210 s).
- All edited files byte-compile.

## What remains unresolved

`ruff check run_*.py` still reports 26 style-only errors, deliberately
left untouched:
- 18 × `EXE001` (shebang present but file not executable) — repo convention;
  scripts are invoked via `python run_*.py`.
- 4 × `RUF046` (unnecessary `int()` cast on already-int values).
- 2 × `SIM102` (collapsible `if`) — intentional trade guards in
  `run_h10`/`run_h23` exit logic.
- 2 × `PERF102` (dict iteration) — the loop variable is used inside the
  body, so the auto-fix is unsafe.

## Approaches already tried and why

- `ruff --fix` on the full rule set: unsafe for `PERF102`/`SIM102` (would
  change runtime behavior) and for `UP031` (needs manual f-string
  conversion). Used only for the safe `I001` import sort.
- Line-number-based bulk edits: caused two real bugs (deleted an `else`
  branch in `run_regime_gated_momentum_experiment.py`; dropped the `skew`/
  `kurt` computation in `run_h14`). Fixed immediately by re-reading and
  restoring. Lesson: content-based edits with verification beats blind
  line-based edits.

## Next task (precise)

**Extend the ruff sweep to the remaining style rules in `run_*.py` —
specifically the 18 `EXE001` sites.**

The `EXE001` errors are the largest remaining class and are a one-line,
zero-risk fix: `chmod +x` the 18 `run_*.py` scripts that carry a shebang.
Verify with `ruff check run_*.py` (expect 8 errors: 4 RUF046, 2 SIM102,
2 PERF102) and confirm the scripts still run (`python run_baseline.py --help`
or equivalent) before committing.

Constraints:
- Do not touch `src/` or `tests/` — they are clean and must stay clean.
- Do not change the `EXE001` fix to anything other than making the file
  executable; the shebangs are intentional (`#!/usr/bin/env python3`).
- After the chmod, re-run `pytest -q` (359/359) and
  `ruff check src tests` to confirm nothing regressed.
- Commit with a message matching the repo style (one-line summary, body
  with verification).