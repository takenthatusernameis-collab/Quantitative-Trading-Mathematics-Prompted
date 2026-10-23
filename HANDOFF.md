# HANDOFF — H63 complete (clean-environment verification)

## What changed (H63)

The one precise task carried forward from `HANDOFF_NEXT.md` was run end-to-end: a fresh venv with
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

## What was actually verified

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

## What remains unresolved

All remaining items are **disclosed, not quantified** -- each depends on an input the record does
not hold (the H9 VIX series, pre-fix fold/beta conventions, the H16 train+val `val_sharpe`,
the 22 sample-convention information ratios, the 14 benchmark `avg_trade_cost` entries, the 40
`stats.json` echoes, the SVXY split) and none can be resolved without new committed inputs. The
thirteen H58/H59 gate booleans stay as published (all in REJECT families; no certified verdict
moves). H1–H30 exhausted; certified families frozen.

## Precise next task

**None assigned.** The H47–H63 series is complete. If a session wants work, the only honest
options are (a) wait for newly committed artifacts that make a disclosed value measurable, or
(b) after any change under `src/qtr`, re-run the pinned contracts -- including
`test_engine_metric_agreement.py`, `test_h53_published_metrics_disclosure`,
`test_h54_non_metrics_block_disclosure`, `test_h55_nested_metrics_disclosure`,
`test_h56_stats_json_echoes`, `test_h57_total_return_audit`, `test_h58_price_pathology_contamination`
and `test_h59_contamination_gate_blast_radius` -- and confirm the gates stay green. In addition,
verify the quick-start surface by running the suite from a fresh venv with only
`pip install -r requirements.txt`, since `requirements.txt` is now the contract that must declare
every dependency a pinned contract test imports.

---

## What changed (this session — dependency fix)

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

## What was actually verified (this session)

- `python -m pytest -q -W error` → **2 057 passed, 16 skipped** (full suite; both previously
  erroring modules collect and pass).
- `python -m pytest -q --cov=qtr --cov-branch` → `src/qtr` = **1 086 statements, 330 branches,
  0 missed, 0 partial, 100.00%**.
- `python -m ruff check src tests run_*.py` → *All checks passed!*; `ruff format --check` →
  **103 files already formatted**.

## What remains unresolved

- Clean-environment verification of the requirements.txt fix (fresh venv, install only
  requirements.txt, full suite green) remains; see NEXT_TASK.md.
- All remaining items in FINAL_REPORT.md §H53–§H61 are disclosed, not quantified, and depend on
  inputs the record does not hold.
