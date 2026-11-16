# Handoff — Current Session (Cycle 152, 2026-11-16)

## What changed
- **`src/qtr/backtest/engine.py`** — `run_backtest` now normalizes a negative or non-finite `BacktestConfig.max_position_size` to `0.0` before the position-size `clip`. Reproduced before fix: a `max_position_size` of `-1.0`, `NaN`, `+inf` or `-inf` silently *disabled* the cap — pandas `clip(lower=-max_pos, upper=max_pos)` is a no-op for `NaN`/infinite bounds and inverts for a negative bound — so an oversized signal (e.g. a vol-scaled TSMOM weight of `3.0`) reached the book at full size with `max_leverage=5.0`. After fix the book is flat (no exposure, no trades, zero returns). Every finite non-negative value is unchanged, so the clean path is bit-identical. This mirrors the accepted `max_leverage` (Cycle 147) and `initial_capital` (Cycle 148) fail-closed boundaries; `max_position_size` was the last unguarded numeric `BacktestConfig` field.
- **`tests/test_engine_edge_stress.py`** — added `TestInvalidPositionSize` (+6): parametrized `-1.0 / -inf / NaN / +inf` fail-closed, a finite-positive `0.5` control (still caps), and a behavioural negative control reconstructing the pre-fix NaN `clip` no-op.
- **`src/qtr/tracking/experiment.py`, `tests/test_experiment_tracker.py`** — `ruff format` only (line-wrap of the two Cycle-151 `log_artifact`/`log_dataframe` path-guard conditions + one blank line). These two files were left unformatted by the previous session's commit, so the required `ruff format --check` gate was red on `origin/main`; no semantic change.

## What was actually verified (own evidence)
- Repro before fix: `run_backtest` with `max_position_size=nan` (or `inf`) and a `3.0` signal returned positions `3.0` (cap disabled); `-1.0` returned `1.0` (negated bound). After fix all four invalid values return all-zero positions/returns and no trades; `max_position_size=0.5` still caps to `0.5`.
- Negative control: `git stash push -- src/qtr/backtest/engine.py` → `TestInvalidPositionSize` gives **4 failed, 2 passed** (the 4 parametrized invalid sizes fail; the 2 controls pass); `git stash pop` → all pass.
- `python -m pytest -q tests/test_engine_edge_stress.py tests/test_backtest_engine.py tests/test_engine_metric_agreement.py tests/test_engine_total_return_consistency.py tests/test_cost_model.py -W error` → **230 passed**.
- `python -m ruff check src tests run_*.py scripts` → clean. `python -m ruff format --check src tests run_*.py scripts` → **336 files already formatted**.
- `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.291s < 5s, 10.7MB, 13668 trades).
- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py` (346.26s) → **3960 passed, 48 skipped, 0 failed**, `src/qtr` coverage **100.00%** (1562 stmts / 564 branches / 0 miss; `backtest/engine.py` 247/90).
- `python -m pytest -q tests/test_gates_workflow.py` → **7 failed** (unchanged, maintainer-gated; fix `patches/0001-gates-workflow-contract-fix.patch`, `git apply --check` still clean).

## What remains unresolved
- Maintainer-only: apply/push `patches/0001-gates-workflow-contract-fix.patch` to fix `.github/workflows/gates.yml` and make `tests/test_gates_workflow.py` pass on `origin/main`.
- Research: H1–H182 exhausted under free/public PIT data; no honest H183 without new authorized data.
- Reproducibility backlog baseline-frozen: `missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=0`.

## Approaches already failed / do not repeat
- Do not re-audit pinned defects (cache index/column normalization+dedup, `max_leverage`/`initial_capital`/`max_position_size` boundaries, engine/fetcher/tracker duplicate handling, `record_artifact` DataFrame dedupe, `load_metadata` non-dict, `record_artifact`/`log_artifact` path traversal).
- Do not edit `.github/workflows/**`, weaken tests/gates/frozen contracts, or invent H183 / parameter-only "new families".
- Do not trust handoff counts without re-running the gate; this session re-ran the full pinned suite with own evidence.

## One precise next task
- **Maintainer:** apply/push `patches/0001-gates-workflow-contract-fix.patch`; run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
- **Agent (new evidence only):** hunt a reproduced, runner-reachable `src/qtr` defect on public paths not yet closed (fuzz/boundary probes: n=0/1/2, empty, duplicate labels, non-finite, corrupt/partial state, untrusted names, type-mismatched operands). If code changes, verify full pinned suite (excluding maintainer-gated workflow tests), ruff check/format, and perf gate.