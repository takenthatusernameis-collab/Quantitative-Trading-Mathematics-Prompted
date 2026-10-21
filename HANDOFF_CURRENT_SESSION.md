# HANDOFF_CURRENT_SESSION — H43: the coverage gate is measured, declared and complete

## What changed

**`src/qtr/strategies/baselines.py`** — the inline `if vol > 0:` guard in
`time_series_momentum_signals` was **provably unreachable**: the realized-volatility series is
sanitized strictly positive by construction
(`returns.rolling(63).std() * sqrt(252)` then `.replace(0, np.nan).ffill().fillna(0.15)`), so
the false arm could never be taken. A 200-trial property check over random and constant price
series found a minimum of 0.15. The guard was moved into a module-level helper:

```python
def _vol_scale(vol: float, target_vol: float) -> float:
    if vol <= 0:
        return 1.0
    return min(target_vol / vol, 2.0)
```

The behavior is **identical** — the old code simply skipped the scaling, which is exactly what a
multiplier of 1.0 does — but the defensive path is now reachable and is covered by a test.
`time_series_momentum_signals` is called by no `run_*.py` (only `vol_scaled_tsmom_signals` is),
so no published artifact, gate, threshold, verdict or certified number can be affected. (+2
statements: 1014 → 1016.)

**`pyproject.toml`** — the coverage gate, which the record quoted but never declared:

```toml
[tool.coverage.run]
branch = true
source = ["src/qtr"]

[tool.coverage.report]
fail_under = 100
show_missing = true
```

**`tests/test_coverage_gate_contract.py`** — **new**, 18 tests: 6 gate pins + 12 branch-closure
tests. The 12 branch-closure tests close the 11 partial branches found by the first branch
measurement (two of them close one arc, one closes two):

- `test_fetch_futures_caches_every_symbol_it_downloads`
- `test_fetch_futures_with_the_cache_disabled_leaves_the_cache_untouched`
- `test_fetch_ccxt_paginates_until_the_window_is_exhausted`
- `test_momentum_without_negative_symbols_leaves_the_short_leg_empty`
- `test_vol_scale_leaves_a_position_unscaled_when_the_volatility_is_not_positive`
- `test_start_experiment_uses_the_caller_supplied_seeds`
- `test_log_artifact_without_metadata_writes_no_sidecar`
- `test_experiment_constructor_preserves_existing_metadata`
- `test_walk_forward_drops_a_fold_with_an_empty_test_side`
- `test_walk_forward_drops_a_fold_with_an_empty_train_side`
- `test_purged_kfold_drops_a_fold_with_no_training_data`
- `test_combinatorial_purged_cv_drops_a_fold_with_no_training_data`

No `run_*.py` was touched; no published artifact, gate threshold, verdict, certified number or
published row was modified; no grid was re-run; no hypothesis was added.

## What was actually verified

- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` → **1230 passed,
  1 skipped**; `src/qtr` = **1016 statements, 316 branches, 0 missed, 0 partial, 100.00%**; the
  committed gate reports *"Required test coverage of 100.0% reached. Total coverage: 100.00%"*.
- `python -m pytest -q -W error` → **1230 passed, 1 skipped** in 271.26 s (the bare-clone path:
  no install step, no coverage plugin, no network).
- `python -m pytest -q -W error tests/test_coverage_gate_contract.py` → **18 passed**.
- Bare-clone path with the coverage tool **absent** → **17 passed, 1 skipped**.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **86 files already formatted**.

## What remains unresolved (disclosures, not rewrites)

- H9's published OOS Sharpe is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict cannot move (REJECT on the profit factor, 55× margin over its 1.0 gate).
- **No further task is assigned.** All tasks (H35–H43) are complete: gate defects (§H35),
  point-in-time causality (§H36–H37), metric agreement (§H39–H41), reproducible lint/format
  (§H42) and the coverage gate (§H43).

## Approaches already tried / failed (this session)

- **The gate bit.** The first run with `fail_under = 100` committed failed the suite
  ("Coverage failure: total of 99 is less than fail-under=100") with one arc still open
  (`fetcher.py:215->173`). That arc turned out to be the `use_cache=False` path, not the
  cache-write path: no test had ever downloaded futures successfully with the cache disabled.
  It was closed by a test that also asserts the cache is left untouched.
- **Suppressing the unreachable branch with `pragma: no cover` was rejected** in favour of
  resolving it — a suppression hides the fact, the helper makes the defensive path observable.
- **Relaxing `fail_under` was rejected**: the threshold was kept at 100 and the gap was closed.
- **Carrying the coverage claim forward a fifth time was rejected**: H39/H40/H41/H42 each
  recorded that the coverage tool was not installed. H43 installed it, measured (the recorded
  number was confirmed exactly) and closed what the measurement found.

## Precise next task

None. All assigned tasks (H35–H43) are complete.

(End of file - total 95 lines)
