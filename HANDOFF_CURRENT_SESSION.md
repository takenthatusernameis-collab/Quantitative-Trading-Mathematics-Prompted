# HANDOFF (current session)

## What changed

`tests/test_runner_import_contract.py` — `test_runner_is_importable` now restores `sys.modules` (the runner module and any `mod_name.*` submodules) to their pre-test objects in a `finally` block after exec'ing a fresh copy to verify importability.

Root cause: the test removed `run_h8_rolladjusted_tsmom_experiment` from `sys.modules` and re-executed it into a *new* module object, leaving that new object registered. The causality probe's `_apply_patch` patches `LOOKBACK` via `importlib.import_module(...)` → the new object, but `_chained_build_tsmom_signals` calls `run_h8_rolladjusted_tsmom_experiment.build_tsmom_signals` via the *old* module object bound at test-module import. With `LOOKBACK` still 252 on the old object and only 80 dense bars, momentum was all-NaN → signal all zeros → `test_dense_sweep[h8_roll_adjusted_tsmom.build_tsmom_signals]` reported "did not react to the perturbation, so the probe is vacuous" whenever `test_runner_import_contract.py` ran first.

No code under `src/qtr`, no published artifact, gate threshold, verdict or certified number was modified; no grid was re-run; no hypothesis was added. The probe is now stricter (it actually exercises the patched `LOOKBACK=20`), not weakened.

## What was actually verified

- Reproduced the failure: `test_runner_import_contract.py` + `test_dense_sweep[h8_roll_adjusted_tsmom.build_tsmom_signals]` → failed ("probe is vacuous") before the fix; passes after.
- `python -m pytest -q -W error tests/test_runner_causality_inventory.py` → **321 passed** (dense + sparse sweeps + all classes).
- Pinned contract group: `test_public_api_contract`, `test_runner_import_contract`, `test_runner_metric_agreement`, `test_runner_causality_inventory`, `test_engine_metric_agreement`, `test_h53_*`, `test_h54_*`, `test_h55_*`, `test_h56_*`, `test_h57_*`, `test_h58_*`, `test_h59_*`, `test_statistics`, `test_generated_manifest_contract`, `test_h51_benchmark_container_invariance`, `test_h49_validation_block_disclosure`, `test_trade_log_cost_reconciliation`, `test_coverage_gate_contract`, `test_gate_vacuity_contract` → **1 321 passed, 15 skipped** (all skips intentional/self-declaring).
- `python -m ruff check src tests run_*.py` → **All checks passed!**; `ruff format --check` → **103 files already formatted**.
- Working tree contains only the intended one-file test change; `git status` clean otherwise.

## What remains unresolved

All remaining items in `FINAL_REPORT.md` (§H53–§H61) are **disclosed, not quantified** — each depends on an input the committed record does not hold. None can be implemented or verified from this checkout; they remain disclosed. Thirteen H58/H59 gate booleans stay as published (all REJECT families). H1–H30 exhausted; certified families frozen.

## Which approaches have already failed and why

- Treating the causality probe's "vacuous" result as a real look-ahead in `build_tsmom_signals` — rejected: the signal is clean when run in isolation; the failure is test pollution from `sys.modules` clobbering by `test_runner_is_importable`.
- No source change was considered: coverage is already 100% and the frozen-record constraints forbid it.

## One precise next task

**None assigned.** H35–H63 complete; H1–H30 exhausted; certified families frozen. Baseline is now green and stable. If work is desired: (a) wait for newly committed artifacts that make a disclosed §H53–§H61 value measurable, then re-run the pinned contracts and confirm gates stay green at 100% coverage; or (b) maintain baseline hygiene — re-verify lint/format/tests after any change under `src/qtr`, and confirm quick-start from a fresh venv with only `pip install -r requirements.txt` (must keep `setuptools>=68` and `pyarrow>=14.0.0`).

Constraints: no published artifact/gate/threshold/verdict/certified number changes; no grid re-runs; 100% coverage on `src/qtr` and clean lint/format required; preserve pinned contracts.
