# Next Task

## State

H35–H63 complete. **No hypothesis work is assigned** — every remaining unresolved item in
`FINAL_REPORT.md` (§H53–§H61) is a value that is not a function of the committed record (missing
inputs, disclosed convention differences, or benchmarks/trade logs/signals never committed). None
can be implemented or verified from this checkout; they stay disclosed, not quantified, and no gate
reads any of them.

## What changed (this session — clean-environment verification, H63)

The one precise task carried forward from `HANDOFF_NEXT.md` was run end-to-end in a fresh venv with
only `pip install -r requirements.txt` (no pre-installed pyarrow or setuptools). It confirmed the
pyarrow fix and found a second dependency of the same class.

- `requirements.txt` — added `setuptools>=68` ahead of `numpy>=1.24.0`, mirroring
  `pyproject.toml`'s `[build-system] requires`. `pyproject.toml:2` declares it as the build backend
  and `tests/test_public_api_contract.py:147`/`:157` exercise `setuptools.find_packages`, but both
  use `pytest.importorskip("setuptools")`, so a clean environment following the documented quick start
  skipped those two pinned contract tests instead of running them. The system runner had setuptools
  68.1.2 apt-installed, which is why the inherited baseline showed only 16 skipped.

No code under `src/qtr` or tests was modified; no published artifact, gate threshold, verdict or
certified number was changed; no grid was re-run; no hypothesis was added.

## What was actually verified (this session)

- Fresh venv, `pip install -r requirements.txt` only: `setuptools-84.2.1` and `pyarrow-26.0.0` both
  install.
- `python -m pytest -q -W error tests/test_public_api_contract.py` → **33 passed, 0 skipped**
  (was 31 passed, 2 skipped before the fix).
- `python -m pytest -q -W error` → **2 072 passed, 16 skipped** (full suite). The remaining 16 skips
  are all intentional and self-declaring.
- `python -m pytest -q --cov=qtr --cov-branch` → `src/qtr` **1 091 statements, 330 branches,
  0 missed, 0 partial, 100.00%** (unchanged: no source or test code moved).
- `python -m ruff check src tests run_*.py` → *All checks passed!*; `ruff format --check` →
  **103 files already formatted**.
- The two previously-erroring modules from the pyarrow fix still collect and pass:
  `tests/test_h53_published_metrics_disclosure.py` and `tests/test_h55_nested_metrics_disclosure.py`
  → 45 passed.

## One precise next task

**None assigned.** The H47–H63 series is complete. If a session wants work, the only honest options
are (a) wait for newly committed artifacts that make a disclosed value measurable, or (b) after any
change under `src/qtr`, re-run the pinned contracts and confirm the gates stay green.

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
- The quick-start dependency surface (§H63) is pinned by running the suite from a fresh venv with
  only `pip install -r requirements.txt`; `requirements.txt` must declare every dependency a pinned
  contract test imports (currently `setuptools>=68` and `pyarrow>=14.0.0`).
- Re-run `tests/test_runner_causality_inventory.py`, `tests/test_runner_metric_agreement.py` and
  `tests/test_benchmark_gate_contract.py` after any change in a runner or under `src/qtr/validation`.
- The coverage gate (`python -m pytest -q --cov=qtr --cov-branch`) must stay at 100% for `src/qtr`;
  the lint gate (`python -m ruff check src tests run_*.py` and
  `python -m ruff format --check src tests run_*.py`) must stay clean.
