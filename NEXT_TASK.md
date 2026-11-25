# Next Task

## AUTHORITATIVE STATUS — Cycle 309 (2026-11-25): H200 institutional-flow / 13F holdings-change EXECUTED → REJECT 2/8

### What changed this session (durable, additive; `src/qtr` unchanged)
- **H200 executed** (Cycle 308): institutional-flow / 13F holdings-change cross-section on the free PIT 13F source (Berkshire, UBS, MassMutual). **REJECT 2/8**, OOS Sharpe -1.167 (train 0.000), passive equal-weight benchmark +0.625; 235 tradeable tickers. Artifact: `.experiments/nf_runs/nf_20261125_01_institutional_flow_20261125_071915/`.
- **13F probe cache populated**: 378,329 holding rows across 3 institutions, 18,169 unique CUSIPs, 235 mapped to tickers with price data.
- **Inverse signal direction confirmed**: anti-flow (short net-buying / long net-selling) shows OOS Sharpe +1.117 but still fails Sharpe >= 1.0 gate on the selected params; the mechanism is empirically inverted but not strong enough to pass all gates.
- **Tests passing**: `tests/test_probe_sec_13f_holdings.py` → 16 passed; `scripts/verify_hypothesis_inventory.py` → IN SYNC (H200 == H200).

### Unresolved (maintainer / next-session)
1. **Workflow contract patch — the sole remaining test red (7 `tests/test_gates_workflow.py` failures).**
   `.github/workflows/**` is agent-unreachable (restored by `.github/scripts/kilo-controller.sh`; token
   lacks `workflows` scope). Maintainer runs:
   `git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am "fix(ci): satisfy gates workflow contract" && git push origin main`
   (re-proven: applies cleanly; `scripts/verify_gates_workflow_patch.py` → PATCH VERIFIED).
   Do NOT re-edit `gates.yml` in a commit; do NOT weaken the contract test.

2. **Equity cross-section program closure / new universe (unchanged).** H1–H200 exhausted/rejected; the
   reject is genuine mechanism weakness (median strategy OOS Sharpe 0.187 vs passive equal-weight book
   1.075; 11/11 negative IR across H187-H200). A new equity cross-section on the same 98-name / broad universe is ruled out.

3. **Next mechanism family search (H201+).** The only genuinely-distinct, repo-new, free-data-feasible-in-principle mechanisms not yet executed would require new data sources (e.g., options flow, short interest, ETF flow, macro surprises) or a different asset class (futures, crypto, FX). Per directive §2, parameter/universe/timeframe variants of exhausted families (H187-H200) are not new families.

### Approaches already failed — do NOT repeat
- Re-running the fast invariants / 750 s baseline **as the deliverable**; appending another "verified, nothing to do" block; adding another guard test; reconciling a doc (Cycles ~257–307) — make-work.
- Fabricating H201 or running another equity cross-section / discovery scan on the exhausted universe.
- Editing `.github/workflows/**` in a commit — controller restores it; token lacks `workflows` scope.
- **Re-declaring SEC 13F "data-blocked"** — refuted with a reproducible free artifact.
- Chasing the `src/qtr` audit candidates (cost-attribution timing, negative-equity drawdown, beta ddof, market-impact NaN, `QTR_CACHE_DIR` fallback) as "bugs" — verified documented conventions / false positives / frozen numerical core.

### Precise next task
**Option A (maintainer action required):** Apply the workflow contract patch (`patches/0001-gates-workflow-contract-fix.patch`) to unblock CI. This is the only remaining deterministic blocker.

**Option B (research direction):** Identify and pre-register **H201** as a genuinely-distinct mechanism family (not a parameter/universe/timeframe variant of H1–H200) with a free PIT source. Candidates: (1) options-market flow / put-call skew cross-section (CBOE data), (2) short-interest / days-to-cover cross-section (FINRA/SEC data), (3) ETF creation/redemption flow cross-section (SEC N-CEN), (4) macro surprise / nowcast revision cross-section (FRED/Bloomberg), (5) futures basis / term-structure carry on new asset class (e.g., crypto futures, FX forwards). Each requires a bounded availability probe before pre-registration.

If deps are missing in a reset env, run `pip install -r requirements.txt` before any verification. Do NOT re-run the 750 s baseline, do NOT add more guards, do NOT re-declare 13F blocked.