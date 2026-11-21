# Session complete (2026-11-21, Cycle 240 — code hardening: `bars_per_year` non-timestamp index)

## State

H1–H190 exhausted/rejected or data-blocked (unchanged; see `AGENTS.md` and
`NEW_FAMILY_RESEARCH_REGISTER.md` Cycles 215–235). Free-data point-in-time family
discovery remains exhausted; do not re-declare any H-ID data-blocked without
naming the probed source, and do not treat parameter/timeframe/universe/market
variants of H1–H190 as new families.

This cycle made a **real code fix + tests** (not a doc-sync): it closed a
fail-closed gap in `qtr.validation.statistics.bars_per_year` that was reachable
from the public API. No strategy family was added; H1–H190 exhaustion is
unchanged.

## What changed (Cycle 240)

`src/qtr/validation/statistics.py::bars_per_year` documents that it returns
**NaN** when the index "is not a timestamp axis", and already refused a
numeric/positional axis (a `RangeIndex`, `pd.Index([1,2,3])`) because
`pd.DatetimeIndex` coerces integers to 1970 nanoseconds and manufactures a
~4.7e16 bars-per-year factor. But the implementation only screened the
**numeric** case; every other non-datetime-convertible axis fell through to
`pd.DatetimeIndex(raw)` and **raised** out of a function every caller treats as
returning a float:

- a categorical / object string index -> `DateParseError` (a `ValueError`);
- a `MultiIndex`, `PeriodIndex`, `TimedeltaIndex`, `IntervalIndex` -> `TypeError`.

`annualized_sharpe` calls this helper directly, so the crash propagated there
too (`annualized_sharpe(rets, multiindex)` raised instead of returning `0.0`).

Fix: wrap the `pd.DatetimeIndex(raw)` conversion in
`try/except (TypeError, ValueError)` and return `float("nan")` on failure — the
same fail-closed value the numeric, single-bar and zero-span paths already
return, and the value `annualized_sharpe` already maps to `0.0`. A
datetime-like index (date strings, `date`/`datetime` objects, `Timestamp`s,
`DatetimeIndex`) converts unchanged, so every valid input is **bit-identical**
to before (verified: `bars_per_year(["2020-01-01","2020-01-02","2020-01-03"])`
and `bars_per_year(pd.date_range(...))` both return `547.875`, exactly as
before).

Tests (`tests/test_statistics.py::TestBarsPerYearNonTimestampIndex`): 9 new
tests — 7 parametrized non-timestamp axes (categorical, object-string, object,
`MultiIndex`, `PeriodIndex`, `TimedeltaIndex`, `IntervalIndex`) each asserting
`bars_per_year` is NaN; one asserting `annualized_sharpe` returns `0.0` for a
`MultiIndex` and a `TimedeltaIndex`; and one pinning that a datetime-like list
still converts. No existing test passed a non-timestamp axis (it previously
crashed), so no frozen number/contract moved.

Scope: `src/qtr/validation/statistics.py` + `tests/test_statistics.py` only. No
runner, artifact, sidecar, hash, gate, frozen number, or workflow was modified.
No `NEW_FAMILY_RESEARCH_REGISTER.md` / `HYPOTHESIS_SPEC.md` / `AGENTS.md`
H-range claim was touched (this is a hardening fix, not a new family).

## Verified evidence (this session)

- `python -m pytest -q` → **4554 passed / 51 skipped / 7 failed** (baseline this
  session was 4545/51/7; +9 = the new tests). All 7 failures are
  `tests/test_gates_workflow.py`, unchanged and maintainer-gated by design
  (patch `patches/0001-gates-workflow-contract-fix.patch`).
- `PYTHONPATH=src python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing`
  → **100.00% coverage** (`src/qtr/validation/statistics.py` 381 stmts / 158
  branches / 0 miss; TOTAL 1702 stmts / 648 branches / 0 miss). The new
  `except` branch is fully covered by the new tests.
- `python -m pytest -q -W error tests/test_statistics.py` → **365 passed**
  (no warnings-as-errors regressions).
- `python -m ruff check src tests run_*.py scripts` → clean;
  `python -m ruff format --check src tests run_*.py scripts` → 360 files already
  formatted.
- Direct probe under `-W error`: categorical/object-string/object/`MultiIndex`/
  `PeriodIndex`/`TimedeltaIndex`/`IntervalIndex` all return `nan` from
  `bars_per_year` and `0.0` from `annualized_sharpe`; date-string and
  `DatetimeIndex` inputs unchanged.
- `git diff --check` → clean (no trailing whitespace / EOF issues).

## One precise next task (for next session)

**None blocking.** The only remaining actionable items are unchanged from prior
cycles:

1. Maintainer-applied workflow contract fix
   (`patches/0001-gates-workflow-contract-fix.patch`) to make
   `tests/test_gates_workflow.py` green — **agent-unreachable** (`.github/workflows/**`
   is maintainer-managed, excluded from staging by
   `.github/scripts/kilo-controller.sh`, restored from `origin/main` after every
   session, and the repo-scoped GitHub App token has no `workflows` permission).
   Patch verified to `git apply --check` cleanly in prior cycles; capture as
   apply-ready and record the maintainer action here.

2. Optional, authorization-gated artifact cleanup from
   `REPRODUCIBILITY_AUDIT_REPORT.md` §2: drop 8 superseded duplicate
   `param_grid_results` keys + 3 stale `summary` keys from `experiments.jsonl`.
   **Do not overwrite artifacts** without authorization.

Optional further hardening (same evidence-first pattern as this cycle). The
following degenerate-input classes are **reproduced but NOT fixed** this cycle
(they are outside the bounded `bars_per_year` scope); each is a candidate for
the next session — reproduce under `-W error`, then fix with a minimal
fail-closed/reduction guard + a test that keeps `src/qtr` at 100% branch
coverage:

- `validate_strategy(returns, trades, config)` with a plain Python **list** or
  **tuple** `returns` raises `AttributeError: 'list' object has no attribute
  'to_numpy'`. The function's first line converts `np.ndarray` -> `pd.Series`
  but not other array-likes; every sibling (`compare_to_benchmark`,
  `regime_analysis`, ...) accepts array-likes via `np.asarray`. A 1-D array-like
  should be accepted (normalise with `np.asarray(..., dtype=float)`), and a
  **non-1-D** `returns` (2-D ndarray/DataFrame) — which currently raises
  `ValueError: Data must be 1-dimensional` or an ambiguous-truth error — should
  fail closed to the same all-fail tuple the empty/non-finite paths return,
  matching `regime_analysis` (non-1-D) and `parameter_sensitivity` (non-2-D).
- `validate_strategy(returns, None, {})` raises `TypeError: object of type
  'NoneType' has no len()`; `validate_strategy(returns, trades, None)` raises
  `TypeError: 'NoneType' object is not a mapping`. Both are caller type
  violations; decide whether to fail closed or keep raising (lower priority than
  the list/2-D `returns` case).

## Approaches already tried / do not repeat

- Do not re-declare any H-ID family as data-blocked without naming the probed source.
- Do not treat parameter/timeframe/universe/market variants of H1–H190 as new families.
- Do not modify `.github/workflows/**` (maintainer-managed; agent-unreachable).
- Do not re-run H190 or any exhausted family as a variant; the full-window
  pre-registered runs are the record.
- Do not reintroduce a hard dependency on `.cache/xbrl/**` in tests: that cache is
  git-ignored and absent on fresh checkouts/CI. Tests must be hermetic (synthetic
  fixtures), as H187/H188 now are.
- Do not mass-edit runners/tests/gates to force the suite green; frozen-contract
  drifts need per-contract evidence and authorization.
- Do not manufacture a hardening guard without first reproducing a concrete failure
  under `-W error`; this cycle's fix was driven by a reproduced
  `TypeError`/`DateParseError` from a non-timestamp `bars_per_year` index, not by
  speculation.
- **Coverage command note:** `--cov=qtr.validation.statistics` triggers a numpy
  `ImportError: cannot load module more than once per process` during collection
  in this environment (Python 3.14 / numpy 2.x). Use `--cov=qtr` (the form the
  handoff/CI uses); it works and reports per-module coverage.
- `_probe.txt` (repo root) is a tracked leftover probe script from a prior
  session (not a `.py` file, so ruff ignores it). It is harmless; removing it is
  out of scope for a hardening cycle — leave it unless a cleanup task is
  authorized.

(End of file - total 118 lines)