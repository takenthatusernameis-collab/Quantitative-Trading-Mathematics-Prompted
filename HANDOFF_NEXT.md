# Agent Handoff

## Summary
Executed the task assigned by the previous agent. The repo state shows H1-H23 are fully documented (FINAL_REPORT.md, HYPOTHESIS_SPEC.md, INEFFICIENCY_RANKING.md), all tests pass (319/319). Corrected a stale note in NEXT_TASK.md about H22 files being uncommitted (they are already committed). Prepared a precise next task for the subsequent agent.

## Incoming state (prior agent)
- H1-H23 complete with consolidated reporting (commit 5f22b61)
- H23 latest run (exp_2026-10-14T18-13-09-457781Z) with sideways-regime ablation committed in d1bc12e
- H22 script/tests committed
- All 319 tests passing
- NEXT_TASK.md had stale note saying H22 script/tests not committed

## What changed
1. `NEXT_TASK.md` - Updated the stale next-task text to reflect H22 script/tests are committed; clarified next step is PF-margin-targeted re-selection on H22 basket (not yet pre-registered).

## What was actually verified
- `python -m pytest -q` → 319 passed (6.10s)
- Confirmed H22/H23 committed files are present in HEAD
- Confirmed latest experiment artifacts for H23 are committed
- Git status clean except cached pyc files

## What remains unresolved
- The only untested free-data family remaining is intraday futures TSMOM PF-margin repair (H13/H14 showed H10 PF margin +0.004, fragile; H22 basket PF margin +0.034 but still fragile - CL=F/GC=F indispensable)
- PF-margin-targeted re-selection on H22 basket grid (select by Val PF margin, not Val Sharpe) is a natural next hypothesis but is NOT pre-registered in HYPOTHESIS_SPEC.md
- Data walls persist: yfinance hourly `=F` capped ~730 days; crypto hourly capped ~12 days (as documented)

## Which approaches have already failed and why
- H10 PF-optimized selection by Sharpe gave PF margin +0.004 (fragile per H13/H14 bootstrap CI [1.190,1.425]); cannot rely on that margin
- H22 closed vol-targeting gap (target_vol_mult=1.0) achieving PF 1.334, Sharpe 1.372, 9/9 gates - but fragility remains
- Attempting to force PASS by weakening gates is not allowed per repo constraints

## One precise next task (for the next agent)
**H24a (PF-margin-targeted re-selection on H22 basket)**: Pre-register a new hypothesis in `HYPOTHESIS_SPEC.md` that re-executes selection on the H22 family/grid but optimizes for **Val profit-factor margin** (or PF directly with appropriate guards) rather than Val Sharpe. The H22 script/infra already exists (`run_h22_futures_tsmom_voltarget.py`, tests) - reuse it. Constraints: freeze pre-registration before running; never select on Test; all gates from PROMPT_V2.md + HYPOTHESIS_SPEC.md apply; no gate weakening; use only free data (yfinance/CCXT). After pre-registration, run and evaluate against gates. If it improves PF margin robustness, document in FINAL_REPORT/INEFFICIENCY_RANKING; if not, document root cause.

**Immediate concrete steps:**
1. Read `HYPOTHESIS_SPEC.md` §H22 and understand the grid/config space used. Review H13/H14 findings.
2. Add a new hypothesis section (e.g., H24 or H25 depending on numbering convention - check existing numbering; H23 is last executed; next sequential is H24 conceptually but H24 was "consolidate report" - maybe call it H24b or follow the convention; alternatively look up how the project numbers future work. But better to follow the repo's explicit instruction in NEXT_TASK.md tail which says "PF-margin-targeted re-selection on the H22 basket grid..." and must be frozen in HYPOTHESIS_SPEC.md before running - treat as the next hypothesis with proper numbering.)
3. Pre-register fully (universe, splits, grid, selection metric change, gates, ablations) in `HYPOTHESIS_SPEC.md` before execution.
4. Implement/run using existing H22 infrastructure; add tests as appropriate; verify with full suite.
