# Next Task

## Goal
Make parquet reading in tests robust across environments by extracting a reusable safe reader and applying it where experiment artifacts are read.

## Requirements
1. Create `tests/_utils_parquet.py` with `def read_parquet_safe(path, **kwargs)` that:
   - Tries engine="pyarrow" if available/importable; falls back to engine="fastparquet" if available; otherwise uses default.
   - Catches specific exceptions (ImportError, OSError, ValueError, AttributeError) and retries with next strategy.
2. Update `tests/test_h18_overnight_intraday.py` to use the helper.
3. Search for other direct `pd.read_parquet` calls on artifact paths (under .experiments or in tests that load artifacts) and update them to use the helper where appropriate.
4. Run `python -m ruff check src tests run_*.py` and `python -m ruff format --check` (format if needed).
5. Run full suite `python -m pytest -q` and ensure all pass.

## Constraints
- Minimal changes, no production code modifications.
- Preserve existing test behavior.
- No network, no data downloads.

## Success criteria
- Helper exists and is used in at least the H18 test.
- Lint/format clean.
- Full suite: 521 passed (no regressions).
