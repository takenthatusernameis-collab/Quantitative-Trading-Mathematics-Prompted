# HANDOFF_CURRENT.md — H90 executed (REJECTED 1/9)

## What changed
- Implemented and executed H90/NF-20261105-08 (FOMC announcement event drift, ex-ante calendar, SPY long/flat). Added/updated `run_nf_20261105_08_fomc_event_drift.py` and `tests/test_nf_20261105_08_fomc_event_drift.py` (causal 1-bar delay; 96 hardcoded Fed statement dates 2015-2026-10-31; VIX gate/hold/vol-target grid). Fixed runner bugs found during execution (sys.path import, finish_experiment arg, NaN vix_gate key). Updated `HYPOTHESIS_SPEC.md` §H90 and `NEW_FAMILY_RESEARCH_REGISTER.md`. src/qtr unchanged.

## What was actually verified
- `pytest -q tests/test_nf_20261105_08_fomc_event_drift.py tests/test_nf_20261105_07_skew_tail_timing.py` -> 19 passed.
- `ruff check` and `ruff format --check` on src/tests/run_*.py -> all checks passed / 117 files formatted.
- H90 experiment `exp_2026-11-05T13-22-09-693533Z` completed (32-combo grid, ~1.8s). Verdict REJECT (1/9): OOS Sharpe -0.633, PF 0.582, maxDD -6.57% (pass), trades 110 (fail), WF stability 0, bench p 1.0, IR -0.859, worst-regime -2.268, perturbation min ratio 0. Train/Val/Test -0.872/-0.886/-0.379.

## What remains unresolved
- New-family discovery required (H1–H90 exhausted/recorded). NF-04/NF-05 remain deferred per prior register; H90 showed negative FOMC event drift under this design.
- No src/qtr changes; coverage/lint gates preserved by checks above.

## Failed/blocked approaches (evidence)
- H90 initial run failed twice: `ModuleNotFoundError: qtr` when run without PYTHONPATH (fixed by sys.path like NF-06); then `KeyError` from NaN vix_gate DataFrame key and `finish_experiment(notes=...)` signature mismatch (fixed). Final run completed with artifact `summary.json`.

## One precise next task
Enter new-family discovery: propose >=3 repository-new mechanism candidates (NF-20261105-09+) across >=3 categories with NF scoring, confirm they are not H1–H90/NF-01..08 variants, resolve NF-04/NF-05 status, and pre-register the highest-information feasible candidate as H91 only when decision-ready; then implement+test+execute bounded.
