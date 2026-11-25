# Next Task

## AUTHORITATIVE STATUS — Cycle 311 (2026-11-25): H201 executed/committed (REJECT 4/8); remaining repo-new candidate sources probed (no new H-ID; frontier evidence recorded)

### What changed this session (durable, additive; `src/qtr` unchanged)
- **Prior assignment COMPLETE + verified.** H201 (short-interest / days-to-cover cross-section) was executed
  and committed in Cycle 310: **REJECT 4/8**, OOS Sharpe +0.813 (train 0.308), passive benchmark +0.558,
  1499 tradeable names; artifact `.experiments/nf_runs/nf_20261125_02_short_interest_20261125_091617/`,
  runner `run_nf_20261125_02_short_interest.py`. `scripts/verify_hypothesis_inventory.py` → IN SYNC (H201 ==
  H201 == README H1–H201); marker H201, next unused H-ID **H202**.
- **Bounded reachability probe of the remaining candidate sources** (directive §6 — probe the named source
  before any "blocked" claim): new `scripts/probe_remaining_family_sources.py` +
  `tests/test_probe_remaining_family_sources.py` (23 offline tests). Reproducible artifact
  `.cache/remaining_family_sources.json` (git-ignored). Findings:
  - **CBOE options** (per-symbol delayed chains / put-call): **NOT reachable — HTTP 403** to non-browser clients.
  - **FRED macro** (T10YIE, DFII10): **reachable** (T10YIE 2003-01-02 → 2026-11-23), but macro-regime timing is
    already **H175** and a macro-*surprise* cross-section still needs consensus data FRED does not give free.
  - **SEC N-CEN** (fund share flows): **reachable + PIT-dated** (BlackRock 71 series/$188.7B; Vanguard 12
    series/$1.41T) but **`flow_present=false`** — the Item C shareholder net-asset-flow signal is **absent
    from the bounded `primary_doc.xml`** (0 flow/redemption/sales tags); extraction needs heavier multi-exhibit parse.
  - **SEC N-PORT** (monthly holdings): **reachable** but holdings, not flows.
- **Already-executed adjacent families (do NOT re-run as new):** insider Form 4/13F = **H182**; institutional
  13F holdings-change = **H200**; ETF NAV arb / leveraged-ETF rebalancing (H170) / index-rebalance flow (H168);
  macro regime = **H175**; short interest = H179/H201.
- **Verification:** `tests/test_probe_remaining_family_sources.py` 23 passed; probe/script coverage guards pass;
  `tests/test_experiment_artifact_schema.py` + `test_verify_hypothesis_inventory.py` = 170 passed (probe writes
  to `.cache`, so committed artifact inventory untouched); `ruff check` + `ruff format --check` clean.

### Unresolved (maintainer / next-session)
1. **Workflow contract patch — the sole remaining deterministic test red (7 `tests/test_gates_workflow.py`
   failures).** `.github/workflows/**` is agent-unreachable (controller-restored; token lacks `workflows` scope).
   Maintainer runs:
   `git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am "fix(ci): satisfy gates workflow contract" && git push origin main`
   (`scripts/verify_gates_workflow_patch.py` → PATCH VERIFIED). Do NOT re-edit `gates.yml` in a commit; do NOT
   weaken the contract test.

2. **Free-data frontier for a genuinely-distinct repo-new family is evidenced near-exhausted.** Options 403;
   insider/13F/ETF-NAV/leveraged-ETF/macro-regime/short-interest done; N-CEN reachable but flow not bounded;
   N-PORT holdings-only; a new equity cross-section on the same broad universe is ruled out (directive §2).

### Approaches already failed — do NOT repeat
- Re-running the fast invariants / 750 s baseline as the deliverable; appending another "verified, nothing to
  do" block; adding another guard test; reconciling a doc (Cycles ~257–311) — make-work.
- Fabricating H202 or running another equity cross-section / discovery scan on the exhausted universe.
- Editing `.github/workflows/**` in a commit — controller restores it; token lacks `workflows` scope.
- Re-declaring SEC 13F / FINRA / FRED / N-CEN "data-blocked" without the named-source probe (all probed).
- Chasing the `src/qtr` audit candidates as "bugs" — verified documented conventions / frozen numerical core.

### Precise next task (choose ONE, in priority order)
**Option A (maintainer action required — still unlanded):** Apply the workflow contract patch
(`patches/0001-gates-workflow-contract-fix.patch`) to unblock CI. Only remaining deterministic blocker.
`scripts/verify_gates_workflow_patch.py` → PATCH VERIFIED. (Agent cannot land: `.github/workflows/**` is
controller-restored and the token lacks `workflows` scope.)

**Option B (research, next-agent — the one remaining free candidate with a reachable PIT source):** Build a
bounded **N-CEN Item-C net-asset-flow extractor** (the flow signal is NOT in `primary_doc.xml`; locate and
parse the additional exhibit / rendered `.htm` that carries Item C shareholder sales/redemptions). Step 1:
extend `scripts/probe_sec_ncen`-style parsing to extract per-class `netAssetFlow` and measure the broad-universe
coverage fraction. Step 2: **only if** coverage clears the documented feasibility bar, pre-register **H202**
(fund-flow demand-pressure cross-section) in `HYPOTHESIS_SPEC.md`, bump the AGENTS.md marker H201→H202 and the
README H-range, and re-run `scripts/verify_hypothesis_inventory.py`. Step 3: execute with the standard 8 gates
and protected holdout, produce a frozen artifact, record the verdict. Expected: likely REJECT (H187–H201 median
OOS Sharpe 0.187) — a valid falsification, not a failure. If N-CEN flow extraction proves infeasible in bounded
form, record the evidence and fall back to Option C.

**Option C (program closure):** If neither A nor B is viable, formally close the free-data equity/fund
cross-section program in `NEXT_TASK.md` + register with the Cycle 311 reachability evidence, and request
maintainer authorization for a paid/consensus source (options chains, analyst revisions, macro consensus).

If deps are missing in a reset env, run `pip install -r requirements.txt` before any verification. Do NOT re-run
the 750 s baseline, do NOT add more guards, do NOT re-declare 13F/FINRA/FRED/N-CEN blocked, do NOT fabricate H202.