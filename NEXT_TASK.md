# Next Task

## State

H35–H70 complete. **No hypothesis work is assigned** — every remaining
unresolved item in `FINAL_REPORT.md` (§H53–§H61) is a value that is not a
function of the committed record (missing inputs, disclosed convention
differences, or benchmarks/trade logs/signals never committed). None can be
implemented or verified from this checkout; they stay disclosed, not
quantified, and no gate reads any of them.

## What changed (this session — H70: momentum_signals guards n_top<=0)

- `src/qtr/strategies/baselines.py` — `momentum_signals` now skips when
  `n_top <= 0` (avoiding division by zero in both long-only and long/short
  branches). No published artifact, gate threshold, verdict or certified number
  depends on this; no runner in the committed record passes `n_top <= 0`.

- `python -m pytest -q -W error` → **2103 passed, 16 skipped**.
- `python -m pytest -q --cov=qtr --cov-branch` → `src/qtr` **1112 statements,
  342 branches, 0 missed, 0 partial, 100.00%**.
- `python -m ruff check src tests run_*.py` → *All checks passed!*;
  `python -m ruff format --check src tests run_*.py` → **103 files already
  formatted**.
- Pinned contracts re-run: 609 passed, 1 skipped across the full pinned set.

## One precise next task

**None assigned.** Options if further work is desired:
(a) wait for newly committed artifacts that make any disclosed §H53–§H61
value measurable; or
(b) baseline hygiene — after any change under `src/qtr` or affecting
runners/validation, re-run the pinned contracts and confirm `src/qtr` stays
at 100% coverage with gates green; keep ruff clean.

## Constraints carried forward

- No published artifact, gate threshold, verdict or certified number may be
  modified. No grid may be re-run; the H1–H30 hypothesis space remains exhausted.
- `src/qtr` coverage gate must stay at 100% (statement + branch).
- Ruff lint and format gates must stay clean.
- Re-run causality/metric agreement/benchmark gate contracts after changes in
  runners or under `src/qtr/validation`.
