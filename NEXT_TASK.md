# Next task (2026-11-18, Cycle 207)

## What changed this session
- **Fixed a reproduced runner-reachable defect in the two runner-local `vol_scaled_tsmom_signals` copies** (`run_ts_momentum_experiment.py`, `run_regime_gated_momentum_experiment.py`): the `long_only` branch had been rewritten (commit `a645a48`) to `direction = np.sign(mom)`, which emits `-1` for negative momentum. In a *long-only* book that (a) booked up to `-MAX_POSITION_SIZE = -2.0` (a phantom short) on every negative-momentum asset and (b) fed those phantom shorts into `port_ret = (w_raw.shift(1) * pct).sum(axis=1)`, corrupting `port_vol` and therefore the vol-targeting scale applied to every *long* position. Restored `direction = (mom > 0).astype(float)`, which is bit-identical to `qtr.strategies.baselines.vol_scaled_tsmom_signals(long_only=True)`. The `long_only=False` branch (`np.sign(mom)` + `.where(mom.notna(), 0.0)`, the H67 zero-momentum-not-a-short fix) is unchanged. Added `tests/test_tsmom_runner_long_only.py` (parametrized over both runners). No `src/qtr`, gate, artifact, sidecar, hash, frozen-number, or workflow change.

## What was actually verified (own evidence, 2026-11-18)
- Pre-fix repro (inline, 400-bar trending panel, lookback=63/skip=1): runner `long_only=True` gave the down-trending asset min weight **-2.0** and UP weight sum **85.7** vs canonical library **298.5**.
- Post-fix: both runners' `long_only` have **no negative weights**, equal the library via `np.allclose(..., atol=1e-12)` → **True**, UP sum **298.465**.
- `python -m pytest -q tests/test_tsmom_runner_long_only.py tests/test_tsmom_signal.py tests/test_runner_causality_inventory.py -W error` → **341 passed**.
- `python -m ruff check src tests run_*.py scripts` → All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` → **337 files already formatted**.
- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py` → **4337 passed, 48 skipped, 0 failed**, `src/qtr` coverage **100.00%** (1686 stmts / 640 branches / 0 miss).
- `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.812s < 5s, 10.7MB peak, 13668 trades).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → exit 0.
- `python -m pytest -q tests/test_gates_workflow.py` → **7 failed** (unchanged maintainer-gated contract; expected until patch applied).

## Blast radius / scope notes
- Other runners that use TSMOM (`run_futures_tsmom_experiment.py`, `run_ddcv_experiment.py`, `run_h6_vix_ddcv_experiment.py`, `run_h8_rolladjusted_tsmom_experiment.py`, `run_h21/h22/h25_*`) import `vol_scaled_tsmom_signals` from the canonical `qtr.strategies.baselines` and were never affected; only these two runners carried a divergent local copy.
- No committed per-experiment artifacts exist for `ts_momentum_20etf_v1` / `regime_gated_momentum_20etf_v1`; restoring `(mom > 0)` realigns the code with the pre-`a645a48` (and pre-existing published) behaviour.

## What remains unresolved
- **Maintainer-gated (agent-unreachable):** apply/push `patches/0001-gates-workflow-contract-fix.patch` with `workflows`-scoped credentials, then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
- **Strategy-family discovery exhausted:** H1–H182 executed/rejected (`NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96). H183 data-blocked (futures roll/contango, crypto funding, or options PIT data).
- **Reproducibility backlog (frozen, authorization-gated):** missing_files=197, hash_mismatches=11, orphaned_files=528, missing_meta_files=0.
- **Maintainer authorization required:** repeated momentum-runner `param_grid_results` logging leaves one recorded hash stale; frozen/test-covered.

## One precise next task
- **Maintainer:** apply and push `patches/0001-gates-workflow-contract-fix.patch`, then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
- **Agent:** perform a bounded, evidence-first search for a NEW reproduced, runner-reachable defect in `src/qtr` or runners/corpus metadata (not previously pinned scalar/degenerate/duplicate-column/duplicate-index/long-only-sign audits). If found, implement the smallest fix + focused regression, then rerun focused tests, `python -m ruff check src tests run_*.py scripts`, `python -m ruff format --check src tests run_*.py scripts`, full pinned coverage (`--ignore=tests/test_gates_workflow.py`), and `python scripts/backtest_perf_regression_gate.py`. If none found after concrete repro attempts, make no source change and re-verify the baseline with own evidence.

## Approaches already tried and why they should not be repeated
- Do not re-audit `src/qtr`/runners for previously pinned scalar/degenerate-input, duplicate-price-column builder/E2E, duplicate-index builder, or long-only-sign defect classes without NEW evidence (Cycles 203–207).
- Do not edit the runner-local `vol_scaled_tsmom_signals` `long_only` branch again without NEW evidence — it is now pinned by `tests/test_tsmom_runner_long_only.py`.
- Do not edit `.github/workflows/**` or weaken `tests/test_gates_workflow.py` — maintainer-gated; fix is the workflow patch.
- Do not edit momentum runners' `param_grid_results` logging without maintainer authorization (frozen; test-covered).
- Do not invent H183 or treat parameter/timeframe/universe variants as new mechanism families.
- Do not trust handoff pass/fail/coverage counts — re-run gates.