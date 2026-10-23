# Next Task

## State

H35–H61 complete. **No hypothesis work is assigned** — every remaining unresolved item in
`FINAL_REPORT.md` (§H53–§H61) is a value that is not a function of the committed record (missing
inputs, disclosed convention differences, or benchmarks/trade logs/signals never committed). None
can be implemented or verified from this checkout; they stay disclosed, not quantified, and no gate
reads any of them.

## What changed (this session)

`requirements.txt` — added the missing core dependency `pyarrow>=14.0.0`.

`pyproject.toml` declares `pyarrow>=14.0.0` as a core dependency, and `src/qtr` uses it
(`data/fetcher.py:92` `pd.read_parquet`, `data/fetcher.py:111` `df.to_parquet`,
`tracking/experiment.py:166`/`336` `df.to_parquet`), but `requirements.txt` — the documented quick
start (`pip install -r requirements.txt` per AGENTS.md) — omitted it. A fresh environment following
the quick start could not read/write parquet, so `tests/test_h53_published_metrics_disclosure.py`
and `tests/test_h55_nested_metrics_disclosure.py` errored at collection (`ImportError: Unable to
find a usable engine`). Added `pyarrow>=14.0.0` after `loguru>=0.7.0`, mirroring `pyproject.toml`'s
core-dependency block.

No code under `src/qtr` or tests was modified; no published artifact, gate threshold, verdict or
certified number was changed; no grid was re-run; no hypothesis was added.

## What was actually verified (this session)

- `pip install -r requirements.txt` now installs pyarrow (previously it did not).
- `python -m pytest -q -W error` → **2 057 passed, 16 skipped** (full suite; both previously
  erroring modules collect and pass). The 16 skips are environment-related (qtr not installed as a
  distribution, no generated manifest, H51 convention splits) and pre-exist this change.
- `python -m pytest -q --cov=qtr --cov-branch` → `src/qtr` 100.00% (unchanged; no source touched).
- `python -m ruff check src tests run_*.py` → **All checks passed!**; `ruff format --check` →
  **103 files already formatted**.

## One precise next task

Verify the fix end-to-end from a clean state: in a fresh venv with only `pip install -r
requirements.txt` (no pre-installed pyarrow), run `python -m pytest -q -W error` and confirm
`tests/test_h53_published_metrics_disclosure.py` and `tests/test_h55_nested_metrics_disclosure.py`
collect and the suite stays green. If green, this session's work is durable; the only remaining
honest options after that are (a) wait for newly committed artifacts that make a disclosed value
measurable, or (b) after any change under `src/qtr`, re-run the pinned contracts and confirm the
gates stay green.

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
- The cross-module agreement (§H60) is pinned by `tests/test_engine_metric_agreement.py`.
- The non-finite row filter of `compare_to_benchmark` (§H61) is pinned by `tests/test_statistics.py`.
- Re-run `tests/test_runner_causality_inventory.py`, `tests/test_runner_metric_agreement.py` and
  `tests/test_benchmark_gate_contract.py` after any change in a runner or under `src/qtr/validation`.
- The coverage gate (`python -m pytest -q --cov=qtr --cov-branch`) must stay at 100% for `src/qtr`;
  the lint gate (`python -m ruff check src tests run_*.py` and
  `python -m ruff format --check src tests run_*.py`) must stay clean.
