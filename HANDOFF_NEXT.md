# HANDOFF_NEXT — H43: the coverage gate is measured, declared and complete

## What changed (this session)

- `src/qtr/strategies/baselines.py` — the provably unreachable inline `if vol > 0:` guard in
  `time_series_momentum_signals` moved into a module-level `_vol_scale(vol, target_vol)` helper
  (returns `1.0` for a non-positive volatility, `min(target_vol / vol, 2.0)` otherwise).
  Behavior-identical: the old code simply skipped the scaling, which is what a multiplier of 1.0
  does. The realized-volatility series is sanitized strictly positive by construction
  (`.replace(0, np.nan).ffill().fillna(0.15)`), which is why the guard could never fire — a
  200-trial property check over random and constant price series found a minimum of 0.15.
  `time_series_momentum_signals` is called by no `run_*.py`, so no published artifact can be
  affected. (+2 statements.)
- `pyproject.toml` — the coverage gate:
  `[tool.coverage.run] branch = true`, `source = ["src/qtr"]`;
  `[tool.coverage.report] fail_under = 100`, `show_missing = true`.
- `tests/test_coverage_gate_contract.py` — **new**, 18 tests: 6 gate pins (the configuration is
  committed, branch coverage is required, the scope is the package, the gate fails below 100%,
  `pytest-cov` is declared, and the configuration is read back through the coverage API) and 12
  branch-closure tests.
- `FINAL_REPORT.md` — new §H43 section, updated `Summary statistics` (test-suite tally, coverage
  bullet) and `Next Task`; `NEXT_TASK.md`; the `HANDOFF*` files.

## What was actually verified

- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` → **1230 passed,
  1 skipped**; `src/qtr` = **1016 statements, 316 branches, 0 missed, 0 partial, 100.00%**; the
  committed gate reports *"Required test coverage of 100.0% reached. Total coverage: 100.00%"*.
- `python -m pytest -q -W error` → **1230 passed, 1 skipped** in 271.26 s (bare clone, no install
  step, no coverage plugin, no network).
- `python -m pytest -q -W error tests/test_coverage_gate_contract.py` → **18 passed**.
- Bare-clone path with the coverage tool **absent** (shim raising `ModuleNotFoundError` on
  `import coverage`) → **17 passed, 1 skipped** — the tool-dependent pin skips cleanly.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **86 files already formatted** (85 + the new
  test module).

## The 11 partial branches that were closed

| Arc | The untested guard |
|---|---|
| `fetcher.py:215->173` | `fetch_futures` with `use_cache=False` — a successful download with the cache disabled was never exercised |
| `fetcher.py:284->293` | the CCXT pagination loop never ended on its `while` condition (only on an empty/short page) |
| `fetcher.py:290->284` | a full 1000-row page never continued the pagination loop |
| `baselines.py:155->131` | `momentum_signals` never saw a bar with no negative momentum |
| `baselines.py:267->272` | `time_series_momentum_signals`'s `if vol > 0` — provably unreachable; moved to `_vol_scale` |
| `experiment.py:89->95` | `start_experiment` never received explicit seeds |
| `experiment.py:150->155` | `log_artifact` was never called without metadata |
| `experiment.py:326->exit` | `Experiment.__init__` never met an existing `metadata.json` |
| `statistics.py:172->161` | `walk_forward_splits` never dropped a fold |
| `statistics.py:779->766` | `purged_kfold_splits` never dropped a fold |
| `statistics.py:816->803` | `combinatorial_purged_cv` never dropped a fold |

## What remains unresolved (disclosures, not rewrites)

- H9's published OOS Sharpe is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict cannot move (REJECT on the profit factor, 55× margin over its 1.0 gate).
- The record's "100% coverage" was a **statement**-coverage figure; the recorded number
  (1014 statements, 0 missed) was confirmed exactly by the first real measurement, but the
  statement-only scope is what hid the 11 branches. The gate now measures branches explicitly.

## Precise next task

None. All assigned tasks (H35–H43) are complete. All metric-agreement sites — library-side
(§H39), runner-local helpers (§H40) and runner-inline sites (§H41) — are classified and pinned;
every gate defect class that has surfaced (§H35) is closed by an executable invariant; the
point-in-time contract covers every `run_*.py` (§H36–H37); the engine's `total_return` spans
every bar (§H38); the package's two Sharpe implementations agree (§H39); the lint/format
gate is reproducible (§H42); and the coverage gate is measured, declared and complete (§H43).
No further work is assigned.

(End of file - total 72 lines)
