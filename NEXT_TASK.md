# Next Task

## State

H35–H62 complete. **No hypothesis work is assigned** — every remaining unresolved item in
`FINAL_REPORT.md` (§H53–§H61) is a value that is not a function of the committed record (missing
inputs, disclosed convention differences, or benchmarks/trade logs/signals never committed). None
can be implemented or verified from this checkout; they stay disclosed, not quantified, and no gate
reads any of them.

## What changed (this session)

`src/qtr/validation/statistics.py` — `sharpe_ratio`'s std guard is now
`np.isfinite(std) and std > 1e-15` instead of `returns.std() <= 1e-15`. A non-finite standard
deviation (the series carries an `inf`, `-inf` or `nan`) compares unordered, so the old guard did
not fire and the function divided an inf/nan mean by a nan std, emitting `nan`, while the engine's
own guard reported `0.0`. The `RuntimeWarning` the reduction raises under `pytest -W error` is
swallowed inside the guard, since the input is the guard's whole job to short-circuit. For every
finite input the arithmetic is bit-identical to before.

`tests/test_statistics.py` — two additions to `TestSharpeRatio`: `test_non_finite_returns_give_zero_sharpe`
(parametrized over `inf`, `-inf`, `nan`) and `test_the_contract_rejects_the_pre_fix_non_finite_guard`
(behavioural negative control).

`tests/test_engine_metric_agreement.py` — two additions: `test_agreement_holds_when_the_returns_carry_a_non_finite_bar`
in `TestSharedMetricAgreement` and `test_the_contract_rejects_a_nan_sharpe_from_a_non_finite_series`
in `TestContractNegativeControl`.

## What was actually verified (this session)

- The 8 new tests fail on the pre-fix code (reverted guard) with the expected errors, then pass
  with the fix restored. The negative controls fire.
- `python -m pytest -q -W error tests/test_statistics.py tests/test_engine_metric_agreement.py`
  → **144 passed**.
- `python -m pytest -q -W error` → **2 065 passed, 16 skipped** (full suite).
- `python -m pytest -q --cov=qtr --cov-branch` → `src/qtr` **1 091 statements, 330 branches,
  0 missed, 0 partial, 100.00%**.
- `python -m ruff check src tests run_*.py` → *All checks passed!*; `ruff format --check` →
  **103 files already formatted**.
- Finite-input bit-identity confirmed.

## One precise next task

**None assigned.** The H47–H62 series is complete. If a session wants work, the only honest
options are (a) wait for newly committed artifacts that make a disclosed value measurable, or
(b) after any change under `src/qtr`, re-run the pinned contracts and confirm the gates stay green.

## Constraints carried forward

- No published artifact, gate threshold, verdict or certified number may be modified.
- No grid may be re-run; the H1–H30 hypothesis space remains exhausted.
- The package's public API (§H45) is pinned by `tests/test_public_api_contract.py`.
- The runners' import surface (§H46) is pinned by `tests/test_runner_import_contract.py`.
- The engine's trade-log reconciliation (§H47) and the frozen record (§H52) are pinned by
  `tests/test_trade_log_cost_reconciliation.py`.
- The seeded reproducibility of `parameter_sensitivity` (§H48) is pinned by
  `tests/test_parameter_sensitivity_reproducibility.py`.
- The published validation blocks (§H49) are pinned by `tests/test_h49_validation_block_disclosure.py`.
- The metadata source of truth (§H50) is pinned by `tests/test_generated_manifest_contract.py`.
- The container-independence of `compare_to_benchmark` (§H51) is pinned by
  `tests/test_h51_benchmark_container_invariance.py`.
- The published `metrics` block (§H53) is pinned by `tests/test_h53_published_metrics_disclosure.py`;
  the nested blocks (§H55) by `tests/test_h55_nested_metrics_disclosure.py`.
- The cross-module agreement (§H60) and the Sharpe convention (§H26) are pinned by
  `tests/test_engine_metric_agreement.py`; the row filter (§H61) by `tests/test_statistics.py`.
- The non-finite Sharpe guard (§H62) is pinned by `tests/test_statistics.py` and
  `tests/test_engine_metric_agreement.py`.
- Re-run `tests/test_runner_causality_inventory.py`, `tests/test_runner_metric_agreement.py` and
  `tests/test_benchmark_gate_contract.py` after any change in a runner or under `src/qtr/validation`.
- The coverage gate (`python -m pytest -q --cov=qtr --cov-branch`) must stay at 100% for `src/qtr`;
  the lint gate (`python -m ruff check src tests run_*.py` and
  `python -m ruff format --check src tests run_*.py`) must stay clean.