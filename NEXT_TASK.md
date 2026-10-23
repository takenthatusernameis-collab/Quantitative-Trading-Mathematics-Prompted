# Next Task

## State

H35–H64 complete. **No hypothesis work is assigned** — every remaining unresolved item in
`FINAL_REPORT.md` (§H53–§H61) is a value that is not a function of the committed record (missing
inputs, disclosed convention differences, or benchmarks/trade logs/signals never committed). None
can be implemented or verified from this checkout; they stay disclosed, not quantified, and no gate
reads any of them.

## What changed (this session — clean-environment verification, H64)

The carried-forward task from `HANDOFF_CURRENT.md` was run end-to-end in a fresh venv with only
`pip install -r requirements.txt` (no pre-installed pyarrow, setuptools or ruff). It confirmed
the two prior fixes and **found a third dependency of the same class**: `ruff` was missing from
`requirements.txt`, so the two documented lint/format gates in `AGENTS.md` were not runnable from
the documented quick start.

- `requirements.txt` — added `ruff>=0.6.0` after `pytest-cov>=4.1.0`, with a comment naming the
  two documented gates it unblocks.

`AGENTS.md:16-17` documents the lint/format gates as the canonical commands:

```
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
```

`ruff` is declared in `pyproject.toml:25` only as the optional `lint` extra
(`lint = ["ruff>=0.6.0"]`), and `pip install -r requirements.txt` does **not** install optional
extras. So a fresh environment following the documented quick start could not run the documented
lint/format gates at all (`python: No module named ruff`). The declaration and the committed
`[tool.ruff]*` configuration were already pinned by `tests/test_ruff_reproducibility.py:31`, but
the pinned *gate* itself was unreachable from the quick start: the declaration test could pass
while the gates it exists to make reproducible could not be executed. Same defect class as the two
prior instances — `requirements.txt` is the documented quick start and must pull in everything the
pinned contract surface needs to run, not just what `src/qtr` imports at runtime.

No code under `src/qtr` or tests was modified; no published artifact, gate threshold, verdict or
certified number was changed; no grid was re-run; no hypothesis was added.

## What was actually verified (this session)

- Fresh venv, `pip install -r requirements.txt` only: `ruff-0.17.2`, `setuptools-84.2.1` and
  `pyarrow-26.0.0` all install.
- From that same clean venv:
  - `python -m ruff check src tests run_*.py` → *All checks passed!*
  - `python -m ruff format --check src tests run_*.py` → **103 files already formatted**
  - `python -m pytest -q -W error` → **2 072 passed, 16 skipped** (full suite; the 16 skips are
    all intentional and self-declaring, unchanged).
  - `python -m pytest -q --cov=qtr --cov-branch` → `src/qtr` **1 091 statements, 330 branches,
    0 missed, 0 partial, 100.00%**.
- System environment re-check after the edit: `ruff check` → *All checks passed!*;
  `ruff format --check` → **103 files already formatted**; `tests/test_ruff_reproducibility.py`
  and `tests/test_public_api_contract.py` → **35 passed**.

## One precise next task

**None assigned.** The H47–H64 series is complete. If a session wants work, the only honest
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
- The quick-start dependency surface (§H63, §H64) is pinned by running the suite, the coverage
  gate and the two ruff gates from a fresh venv with only `pip install -r requirements.txt`;
  `requirements.txt` must declare every dependency a pinned contract test or a documented gate
  imports (currently `setuptools>=68`, `pyarrow>=14.0.0` and `ruff>=0.6.0`).
- Re-run `tests/test_runner_causality_inventory.py`, `tests/test_runner_metric_agreement.py` and
  `tests/test_benchmark_gate_contract.py` after any change in a runner or under `src/qtr/validation`.
- The coverage gate (`python -m pytest -q --cov=qtr --cov-branch`) must stay at 100% for `src/qtr`;
  the lint gate (`python -m ruff check src tests run_*.py` and
  `python -m ruff format --check src tests run_*.py`) must stay clean.