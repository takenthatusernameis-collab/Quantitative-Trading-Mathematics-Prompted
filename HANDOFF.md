# Agent Handoff

## Summary
Executed the assigned task: updated NEXT_TASK.md to correct stale note about H22 files (already committed), verified all tests pass (319/319), and prepared a precise next task for the subsequent agent. All H1-H23 are fully documented; repo is in a clean, verifiable state.

## Incoming state (prior agent)
- H1-H23 consolidated (commit 5f22b61) - FINAL_REPORT.md, INEFFICIENCY_RANKING.md, NEXT_TASK.md updated
- H23 latest run with sideways-regime ablation committed (d1bc12e)
- H22 script and tests committed
- All 319 tests passing
- NEXT_TASK.md incorrectly stated H22 script/tests were uncommitted

## What changed
1. `NEXT_TASK.md` - Corrected stale note: H22 script/tests are committed. Clarified next step is PF-margin-targeted re-selection on H22 basket (not yet pre-registered).

2. `HANDOFF_NEXT.md` (new) - Detailed handoff with precise next task.

## What was actually verified
- `python -m pytest -q` → 319 passed in 6.10s
- Confirmed H22/H23 committed files present in HEAD
- Confirmed latest H23 experiment artifacts committed
- Git state: only NEXT_TASK.md modified (committed as 253010a); pyc/cache files untracked as expected

## What remains unresolved
- PF-margin-targeted re-selection on H22 basket (select by Val PF margin vs Val Sharpe). H13/H14 showed H10 PF margin +0.004 is fragile; H22 basket PF margin +0.034 but remains fragile (CL=F/GC=F indispensable). This hypothesis is not pre-registered.
- Data walls persist: yfinance hourly `=F` capped ~730 days; Coinbase/CCXT hourly crypto capped ~12 days.

## Which approaches have already failed and why
- Selecting by Val Sharpe (H10) yields thin PF margin (+0.004) - bootstrap CI [1.190,1.425] shows fragility (H13/H14)
- H22 closed vol-targeting gap to achieve 9/9 gates with PF 1.334, but fragility not eliminated
- Weakening gates to force pass is disallowed

## One precise next task (for the next agent)
**H24a (PF-margin-targeted re-selection on H22 basket)**: Pre-register in `HYPOTHESIS_SPEC.md` a hypothesis that re-selects on the H22 family/grid using Val profit-factor margin (or PF) as selection metric instead of Val Sharpe. Reuse existing `run_h22_futures_tsmom_voltarget.py`. Freeze pre-registration before running; never select on Test; all gates from PROMPT_V2.md + HYPOTHESIS_SPEC.md apply; no gate weakening; free data only. Run, evaluate, document results (update FINAL_REPORT/INEFFICIENCY_RANKING if warranted). Add tests as appropriate.

Constraints: follow repo commit-per-experiment convention; run full suite after changes; verify artifacts before committing.
