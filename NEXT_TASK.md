# Next Task — H43 done: the coverage gate is measured, declared and complete

## State

**H35, H36, H37, the remaining-runner extension, H38, H39, H40, H41, H42 and H43 are COMPLETE.**

- The engine and `qtr.validation.statistics.validate_strategy` now agree **exactly** on all six
  metrics the package computes twice (`total_return`, `annualized_return`,
  `annualized_volatility`, `sharpe`, `max_drawdown`, `profit_factor`), and the engine-only
  metrics (Sortino, Calmar, max-drawdown duration, average trade cost) are pinned by their exact
  formula (`tests/test_engine_metric_agreement.py`, 55 tests).
- The **Sharpe convention is settled**: the package uses the **population** standard deviation
  (ddof=0), which is what `qtr.validation.statistics.sharpe_ratio` already used and what every
  audited family's published Sharpe uses (H26's own per-family classification, pinned). The
  engine was the only outlier; it now matches.
- The engine's **degenerate-series guard** now carries the record's 1e-15 tolerance, so a constant
  return series yields 0.0 in both implementations instead of 7.3e16 in the engine.
- The five artifacts that carry engine metrics published **two different Sharpes for one run**
  (ratio exactly `sqrt((n-1)/n) = 0.9998011730768697`, n = 2,515). They are frozen history; both
  conventions are pinned against each artifact's own equity curve.
- **H9 is the one family in the record published on the other convention** (sample std, ddof=1);
  the gap is 1.026e-04 against a margin of 5.6e-02 above its 1.0 Sharpe gate, and its published
  row is a REJECT on the profit factor in any case. Disclosed and pinned.
- **The lint/format gate is reproducible from a bare clone** (§H42).
- **The coverage gate is now measured, declared and complete** (§H43). The record's "100%
  coverage" was a *statement*-coverage figure that four consecutive sessions re-asserted without
  re-measuring, because `pytest-cov` was not installed in those environments. The first real
  measurement confirmed the figure (1014 statements, 0 missed) **and** found 11 partial branches
  behind it. All 11 are now closed by named tests, and `pyproject.toml` declares the gate
  (`branch = true`, `source = ["src/qtr"]`, `fail_under = 100`) so the quoted command
  **fails closed** below full coverage.

## What changed this session (H43)

- `src/qtr/strategies/baselines.py` — the provably unreachable inline `if vol > 0:` guard in
  `time_series_momentum_signals` moved into a module-level `_vol_scale(vol, target_vol)` helper
  (returns `1.0` for a non-positive volatility, `min(target_vol / vol, 2.0)` otherwise).
  **Behavior-identical** — the old code simply skipped the scaling — but the defensive path is now
  reachable and covered. `time_series_momentum_signals` is called by no `run_*.py`, so no published
  artifact can be affected. (+2 statements.)
- `pyproject.toml` — the `[tool.coverage.run]` / `[tool.coverage.report]` gate.
- `tests/test_coverage_gate_contract.py` — **new**, 18 tests (6 gate pins + 12 branch-closure
  tests).
- `FINAL_REPORT.md` — new §H43 section, updated `Summary statistics` and `Next Task`; this file;
  the `HANDOFF*` files.

## What was actually verified (this session — H43)

- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` → **1230 passed,
  1 skipped**; `src/qtr` = **1016 statements, 316 branches, 0 missed, 0 partial, 100.00%**; the
  committed gate reports *"Required test coverage of 100.0% reached. Total coverage: 100.00%"*.
- `python -m pytest -q -W error` → **1230 passed, 1 skipped** in 271.26 s (the bare-clone path: no
  install step, no coverage plugin, no network).
- `python -m pytest -q -W error tests/test_coverage_gate_contract.py` → **18 passed**.
- Bare-clone path with the coverage tool **absent** (shim raising `ModuleNotFoundError` on
  `import coverage`): **17 passed, 1 skipped** — the tool-dependent pin skips cleanly.
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

## Constraints carried forward

- No published artifact, gate threshold, verdict or certified number may be modified; no grid
  may be re-run; no new hypothesis (the H1–H30 space is exhausted; the certified families
  H10/H11/H12/H22/H25 are frozen).
- `python -m pytest -q -W error` and `ruff check src tests run_*.py` must pass from a bare
  clone (no install step); `ruff format --check src tests run_*.py` must pass (§H42). The
  **coverage gate is now a fourth enforced gate**:
  `python -m pytest -q --cov=qtr --cov-branch` must exit 0 (it fails below 100%). `pytest-cov` is
  declared under `[project.optional-dependencies] test`; it is *not* required for the bare-clone
  suite run, and the one tool-dependent pin skips cleanly when it is absent.
- Keep `src/qtr` at **100% statement *and* branch** coverage.
- Re-run `tests/test_runner_causality_inventory.py` after any change in a `run_*.py`,
  `tests/test_causality_invariant.py` after any change under `src/qtr`,
  `tests/test_engine_metric_agreement.py` after any change to `_calculate_metrics` or to
  `qtr.validation.statistics`, and `tests/test_runner_metric_agreement.py` after any change to
  a runner's local metric helper or inline metric site.

## Next task

None. All assigned tasks (H35–H43) are complete. All metric-agreement sites — library-side
(§H39), runner-local helpers (§H40) and runner-inline sites (§H41) — are classified and pinned;
every gate defect class that has surfaced (§H35) is closed by an executable invariant; the
point-in-time contract covers every `run_*.py` (§H36–H37); the engine's `total_return` spans
every bar (§H38); the package's two Sharpe implementations agree (§H39); the lint/format
gate is reproducible (§H42); and the coverage gate is measured, declared and complete (§H43).
No further work is assigned.
