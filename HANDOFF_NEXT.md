# HANDOFF_NEXT — H63: setuptools declared in requirements.txt

## What changed (this session)

`requirements.txt` — added the missing build dependency `setuptools>=68`.

`pyproject.toml:2` declares `setuptools>=68` as the build-system requirement and
`tests/test_public_api_contract.py:147`/`:157` exercise `setuptools.find_packages(where="src")`
to pin the package's discovery surface (the `qtr.utils` namespace-package hole, §H45). Both use
`pytest.importorskip("setuptools")`, so a clean environment following the documented quick start
skipped those two pinned contract tests instead of running them. The system runner had setuptools
68.1.2 apt-installed, which is why the inherited baseline showed only 16 skipped and this only
surfaced in a venv created from `requirements.txt` alone. Added `setuptools>=68` ahead of
`numpy>=1.24.0`, mirroring `pyproject.toml`'s `[build-system] requires`, with a comment recording
that it is required by the build backend and by `test_public_api_contract.py`.

This is the same defect class already fixed for `pyarrow` (see prior handoff): `requirements.txt` is
the documented quick start (`pip install -r requirements.txt` per `AGENTS.md`), and it must pull in
everything the pinned contract tests need to run, not just what `src/qtr` imports at runtime.

No code under `src/qtr` or tests was modified; no published artifact, gate threshold, verdict or
certified number was changed; no grid was re-run; no hypothesis was added.

## What was actually verified

- Fresh venv, `pip install -r requirements.txt` only (no pre-installed pyarrow or setuptools):
  `setuptools-84.2.1` and `pyarrow-26.0.0` both install.
- `python -m pytest -q -W error tests/test_public_api_contract.py` → **33 passed, 0 skipped**
  (was 31 passed, 2 skipped before the fix).
- `python -m pytest -q -W error` → **2 072 passed, 16 skipped** (full suite; the two setuptools-driven
  skips are gone). The remaining 16 skips are all intentional and self-declaring.
- `python -m pytest -q --cov=qtr --cov-branch` → `src/qtr` = **1 091 statements, 330 branches,
  0 missed, 0 partial, 100.00%** (unchanged: no source or test code moved).
- `python -m ruff check src tests run_*.py` → *All checks passed!*; `ruff format --check` →
  **103 files already formatted**.
- The two previously-erroring modules from the pyarrow fix still collect and pass:
  `tests/test_h53_published_metrics_disclosure.py` and `tests/test_h55_nested_metrics_disclosure.py`
  → 45 passed.

## What a next session inherits

- **No hypothesis task is assigned.** H47–H63 complete; H1–H30 exhausted; certified families frozen.
- The quick-start dependency surface is now verified from a clean state. `requirements.txt` is the
  contract that must declare every dependency a pinned contract test imports (currently
  `setuptools>=68` and `pyarrow>=14.0.0`); if a new contract test is added that imports a third
  package, that package must land in `requirements.txt` too.
- The inherited baseline is green; after any change under `src/qtr`, re-run the pinned contracts
  (see NEXT_TASK.md "Constraints carried forward") and confirm the gates stay green.
