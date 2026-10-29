# Next task — none assigned (baseline hygiene)

## Status (this session)

No prior agent assignment existed; the baseline was already fully green. I inspected the repository and selected one bounded, high-value task: pin the `run_*.py` experiment runners' formatting as a test, since they are committed experiment artifacts but only had a manual lint/format gate (AGENTS.md) and no test-based check.

## What changed

`tests/test_runner_import_contract.py` — added `TestRunnerFormatContract.test_all_runners_are_ruff_formatted`, which runs `python -m ruff format --check` over every `run_*.py` in the repo root and fails if any runner is unformatted. Complements `test_runner_import_contract.py`'s importability/import-classification pins and `test_ruff_reproducibility.py`'s pyproject pin. No source under `src/qtr` was modified.

+35 insertions, 1 file changed; working tree otherwise clean.

## What was actually verified

- New test passes: `tests/test_runner_import_contract.py` → 68 passed (includes the new formatting test).
- Full suite `python -m pytest -q -W error` → **2164 passed, 16 skipped** (all 16 skips intentional/self-declaring; was 2163 before the new test).
- Coverage `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` → **TOTAL 1154 stmts / 368 branches / 0 missed / 0 partial / 100.00%**.
- `python -m ruff check src tests run_*.py` → **All checks passed!**
- `python -m ruff format --check src tests run_*.py` → **104 files already formatted.**

## What remains unresolved

- No hypothesis work assigned (H1–H30 exhausted; certified families frozen per prior handoffs).
- No published artifact, gate threshold, verdict, or certified number may be modified.

## Precise next task

Baseline hygiene only after any change under `src/qtr` or affecting runners/validation:

1. Re-run pinned contracts and confirm `python -m pytest -q --cov=qtr --cov-branch` stays at 100% (statement+branch).
2. Keep `python -m ruff check src tests run_*.py` and `python -m ruff format --check src tests run_*.py` clean.
3. `qtr` is left **uninstalled** (bare clone) — do not `pip install -e .` unless a test requires it, and restore that state if you do.
4. `requirements.txt` must declare every dependency a pinned contract test imports (`setuptools>=68`, `pyarrow>=14.0.0`, `ruff>=0.6.0`).

## Constraints carried forward

- No published artifact, gate threshold, verdict, or certified number may be modified. H1–H30 hypothesis space remains exhausted.
- `src/qtr` coverage gate must stay at 100% (statement + branch).
- Ruff lint and format gates must stay clean.

## Failed approaches

- None this session; the repository had no defect to fix (baseline was already green: 2163 passed / 16 skipped, 100% coverage, ruff clean, all runner imports valid). The only uncommitted improvement available was the missing run-script formatting test, now added.
