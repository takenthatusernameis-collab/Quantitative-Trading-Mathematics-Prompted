# Next Task

## AUTHORITATIVE STATUS — Cycle 312 (2026-11-25): H201 executed/committed (REJECT 4/8); Option A patch verified & apply-ready (maintainer-only); Option B investigated live and found NOT viable (no Item-C flow data to extract); falling to Option C (program closure) as the precise next task.

### What changed this session (durable, additive; `src/qtr` unchanged)
- **Option A — workflow contract patch confirmed apply-ready.** `git apply --check patches/0001-gates-workflow-contract-fix.patch` → applies cleanly; `python scripts/verify_gates_workflow_patch.py` → exit 0, "PATCH VERIFIED ... resolves all 7 violation(s)". Only remaining deterministic blocker (7 `tests/test_gates_workflow.py` failures on `origin/main`). Agent cannot land it: `.github/workflows/**` is controller-restored and the token lacks `workflows` scope. Awaits maintainer: `git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am "fix(ci): satisfy gates workflow contract" && git push origin main`.
- **Option B — N-CEN Item-C flow extraction investigated against live SEC data and ruled out.** Fetched BlackRock's latest N-CEN filing (CIK 0001137360, accession 0001410368-26-069245, filed 2026-07-08) via `data.sec.gov` + `www.sec.gov` (network reachable with a descriptive User-Agent). The filing carries only `primary_doc.xml` (436 KB) and a rendered `NCEN_*.htm` (30 KB, same data). Full tag inventory of `primary_doc.xml` contains **no** `netAssetFlow`, `totalSales`, `totalRedemptions`, `shareholder transaction`, `Item C`, or any dollar-level shareholder-flow tag — only administrative/creation-unit/principal fields plus `mnthlyAvgNetAssets`/`sharesOutstanding`/`averagePercentageRedeemed` (percentages, not dollar flows). Vanguard already showed `flow_present=false` in the prior probe. So there is **no per-class `netAssetFlow` document to parse**: Option B Step 1 finds nothing extractable, and extending `parse_ncen_primary_doc` cannot manufacture a signal that isn't filed. Option B is not viable in bounded form → fall back to Option C per the handoff's own escape clause.
- Baseline confirmed green by the prior cycle (4939 passed / 51 skipped, `-W error`, excluding the 7 agent-unreachable `tests/test_gates_workflow.py`); no `src/qtr`, gate, runner, or frozen artifact was touched in this session.

### Unresolved (maintainer / next-session)
1. **Workflow contract patch — still unlanded.** Same as above; the sole remaining deterministic test red. Do NOT re-edit `gates.yml` in a commit; do NOT weaken the contract test.

### Approaches already failed — do NOT repeat
- Re-running the fast invariants / 750 s baseline as the deliverable; appending another "verified, nothing to do" block; adding another guard test; reconciling a doc — make-work.
- Fabricating H202 or running another equity cross-section / discovery scan on the exhausted universe (directive §2).
- Editing `.github/workflows/**` in a commit — controller-restored; token lacks `workflows` scope.
- Re-declaring SEC 13F / FINRA / FRED / N-CEN "data-blocked" without the named-source probe (all probed; N-CEN now additionally confirmed live to carry no Item-C dollar flow).
- Chasing the `src/qtr` audit candidates as "bugs" — verified documented conventions / frozen numerical core.

### Precise next task (choose ONE, in priority order)
**Option C (program closure) — execute now.** Formally close the free-data equity/fund cross-section program in this file, registering the Cycle 311/Cycle 312 reachability evidence (options CBOE 403; FRED reachable but no free macro-surprise consensus; N-CEN reachable + PIT but no Item-C dollar flow in `primary_doc.xml` for BlackRock or Vanguard; N-PORT holdings-only; SEC 13F/FINRA/FRED all probed). Then **request maintainer authorization for a paid/consensus source** (options chains, analyst revisions, macro consensus) to open a genuinely distinct mechanism family, since the free frontier is evidenced near-exhausted (H187–H201 median OOS Sharpe 0.187; no free source yields a bounded, distinct flow signal).

If deps are missing in a reset env, run `pip install -r requirements.txt` before any verification. Do NOT re-run the 750 s baseline, do NOT add more guards, do NOT re-declare 13F/FINRA/FRED/N-CEN blocked, do NOT fabricate H202.