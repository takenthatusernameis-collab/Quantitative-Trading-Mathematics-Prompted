# Next Task

## Status: COMPLETE (this session)

The parquet-helper task from the prior handoff was already implemented by the
previous agent. Verified this session:

1. `tests/_utils_parquet.py` exists with `read_parquet_safe(path, **kwargs)` that
   tries engine="pyarrow", then engine="fastparquet", then default, catching
   ImportError/OSError/ValueError/AttributeError per strategy.
2. All 15 test files that read parquet artifacts import and use the helper.
3. No direct `pd.read_parquet` calls remain on artifact paths in tests.
4. Full suite: 521 passed (re-confirmed this session). Lint/format clean.

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

## Next task (beyond free-data scope)

No bounded task remains within the free-data constraint. Per FINAL_REPORT.md §Next
Task, the precise next task requires **paid hourly futures data** to widen the OOS
window enough for the PF and Sharpe bootstrap CIs to clear their gates with margin
(H10/H22/H25 are PASS but PF-margin is CI-fragile: H13 CI [1.190, 1.425], H25 Robustness
CI [1.2049, 1.4425], P(PF≥1.3)≈0.5–0.62). Do not run further hypotheses on free data
— that repeats the H1–H9/H19–H23 pattern (OOS Sharpe 0.2–0.8, PF-CI-fragile).