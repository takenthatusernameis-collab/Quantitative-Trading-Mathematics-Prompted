# HANDOFF_NEXT — dependency fix: pyarrow declared in requirements.txt

## What changed (this session)

`requirements.txt` — added the missing core dependency `pyarrow>=14.0.0`.

`pyproject.toml` declares `pyarrow>=14.0.0` as a core dependency and `src/qtr` uses it
(`data/fetcher.py:92`/`111`, `tracking/experiment.py:166`/`336`), but `requirements.txt` — the
documented quick start (`pip install -r requirements.txt` per AGENTS.md) — omitted it. A fresh
environment following the quick start could not read/write parquet, so
`tests/test_h53_published_metrics_disclosure.py` and `tests/test_h55_nested_metrics_disclosure.py`
errored at collection (`ImportError: Unable to find a usable engine`). Added `pyarrow>=14.0.0` after
`loguru>=0.7.0`, mirroring `pyproject.toml`'s core-dependency block.

No code under `src/qtr` or tests was modified; no published artifact, gate threshold, verdict or
certified number was changed; no grid was re-run; no hypothesis was added.

## What was actually verified

- `python -m pytest -q -W error` → **2 057 passed, 16 skipped** (full suite; both previously
  erroring modules collect and pass).
- `python -m pytest -q --cov=qtr --cov-branch` → `src/qtr` = **1 086 statements, 330 branches,
  0 missed, 0 partial, 100.00%**.
- `python -m ruff check src tests run_*.py` → *All checks passed!*; `ruff format --check` →
  **103 files already formatted**.

## What a next session inherits

- **No hypothesis task is assigned.** H47–H61 complete; H1–H30 exhausted; certified families frozen.
- The one precise remaining task is clean-environment verification of the fix: in a fresh venv with
  only `pip install -r requirements.txt` (no pre-installed pyarrow), run
  `python -m pytest -q -W error` and confirm `test_h53_published_metrics_disclosure.py` and
  `test_h55_nested_metrics_disclosure.py` collect and the suite stays green.
- The inherited baseline is green; after any change under `src/qtr`, re-run the pinned contracts
  (see NEXT_TASK.md "Constraints carried forward") and confirm the gates stay green.
