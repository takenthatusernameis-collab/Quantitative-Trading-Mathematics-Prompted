# Next Task

## Status: COMPLETE (this session)

The parquet-helper task from the prior handoff was already implemented by the
previous agent. Verified this session:

1. `tests/_utils_parquet.py` exists with `read_parquet_safe(path, **kwargs)` that
   tries engine="pyarrow", then engine="fastparquet", then default, catching
   ImportError/OSError/ValueError/AttributeError per strategy.
2. All 15 test files that read parquet artifacts import and use the helper.
3. No direct `pd.read_parquet` calls remain on artifact paths in tests.
4. Full suite: 521 passed. Lint/format clean.

## Additional work done this session

Fixed a demonstrated problem: `pkg_resources` (deprecated API) was used in
`ExperimentTracker._get_dependencies`, producing 5 DeprecationWarnings across the
suite. Replaced with stdlib `importlib.metadata.distributions` (verified equivalent:
127 entries, identical versions). Warnings reduced from 5 to 1 (the remaining is an
unrelated scipy numerical warning). Coverage on experiment.py now 100%.

## Environment note

`qtr` was not installed in the environment, causing `ModuleNotFoundError` at test
collection. Fixed with `pip install -e .` from the repo root. If a future session
hits the same error, run that command first.

## Success criteria — all met
- Helper exists and is used in the H18 test (and 14 others).  [done]
- Lint/format clean.  [done]
- Full suite: 521 passed, no regressions.  [done]