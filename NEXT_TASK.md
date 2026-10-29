# Next task — none assigned (baseline hygiene)

## Status (this session)

No prior agent assignment existed; the baseline was already fully green. I inspected the repository and selected one bounded, high-value task: relocate a late module-level import in `src/qtr/validation/statistics.py` to the top of the file with the other stdlib imports. `from itertools import combinations as _combinations` was defined at line 895, after all function definitions (first def at line 11). While it executes correctly (module-level imports run before any function is called) and ruff ignores E402, it is unconventional and the only import-out-of-place in `src/qtr`.

## What changed

`src/qtr/validation/statistics.py` — moved `from itertools import combinations as _combinations` from line 895 (after all function definitions) to line 4 (with the other stdlib imports: `warnings`, `typing`). Removed the now-duplicate late import. Behavior-preserving: no code added, removed, or modified; only an import statement relocated.

-1 file changed, -2 net lines (1 import added at top, 1 import + 1 blank line removed at bottom); working tree contains only this modification (uncommitted).

## What was actually verified

- `python -m ruff check src tests run_*.py` → **All checks passed!**
- `python -m ruff format --check src tests run_*.py` → **105 files already formatted.**
- `python -m pytest -q tests/test_statistics.py tests/test_runner_import_contract.py tests/test_ruff_reproducibility.py tests/test_public_api_contract.py tests/test_config.py -W error` → **203 passed.**
- `git status --short` → only `src/qtr/validation/statistics.py` modified; `qtr` remains **uninstalled** (bare clone).

## What remains unresolved

- No hypothesis work assigned (H1–H30 exhausted; certified families frozen per prior handoffs).
- No published artifact, gate threshold, verdict, or certified number may be modified.
- Full-suite coverage run (`python -m pytest -q --cov=qtr --cov-branch`) could not complete in this session due to environment slowness (some test files take >3min individually), but the change is a pure import relocation with zero behavior impact, so coverage is unaffected. Statistics module coverage was previously 100%.

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
- After changes under `src/qtr` or runners/validation, re-run causality/metric agreement/benchmark gate contracts.

## Failed approaches

- None this session. Full suite (`python -m pytest -q`) times out at ~3min in this environment due to slow test files (not failures); individual fast test files (statistics, config, runner import, public API, ruff reproducibility, baselines, data fetcher) all pass quickly. No defect was found in `src/qtr` after reviewing `fetcher.py`, `engine.py`, `statistics.py`, `__init__.py` files, and subpackage `__all__` lists.
