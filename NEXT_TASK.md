# Next Task

## AUTHORITATIVE STATUS — Cycle 319 (2026-11-26): Free-data research frontier EVIDENCED exhausted. Baseline green. `src/qtr` unchanged.

### What changed this session (durable, additive; `src/qtr` unchanged)
- **Cycle 319 — resolved the last free-data candidate (N-CEN "heavier multi-exhibit parser").** Extended `scripts/probe_remaining_family_sources.py::probe_sec_ncen` to enumerate **every** document in the N-CEN filing directory (new `list_filing_documents` helper via the filing `index.json`) and scan **all** `.xml` exhibits — not just `primary_doc.xml` — for shareholder-flow fields. Added `tests/test_probe_remaining_family_sources.py` cases (18 → 21). Live probe (free, read-only) confirms: BlackRock Funds and Vanguard World Fund N-CEN filings each carry **exactly one XML document (`primary_doc.xml`)**, **no additional data exhibit**, and **no shareholder sales/redemptions flow field** (the only purchase/sale-like tags are ETF creation/redemption *units* and broker-dealer *principal* securities-lending transactions). **The "heavier multi-exhibit parser" path (handoff option (a)) is a false premise; the fund-flow family is not free-sourceable from N-CEN.** No H202 fabricated; high-water mark stays H201.
- **Verification (this session):** `tests/test_probe_remaining_family_sources.py` 21 passed; `test_probe_script_coverage` + `test_script_test_coverage` 5 passed; `test_experiment_artifact_schema` 124 passed (committed artifact inventory untouched — probe writes to git-ignored `.cache/`); combined probe/inventory/schema sweep 184 passed under `-W error`; `scripts/verify_hypothesis_inventory.py` IN SYNC (H201 == H201); `ruff check` + `ruff format --check` clean on both changed files; `git status --short` shows only the two intended files modified.

### Unresolved (maintainer / next-session)
1. **Workflow contract patch — still unlanded.** `patches/0001-gates-workflow-contract-fix.patch` applies cleanly; `python scripts/verify_gates_workflow_patch.py` → exit 0, "PATCH VERIFIED ... resolves all 7 violation(s)". Agent cannot land: `.github/workflows/**` is controller-restored and the token lacks `workflows` scope. Awaits maintainer: `git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am "fix(ci): satisfy gates workflow contract" && git push origin main`.
2. **Paid/consensus source authorization for H202 — pending maintainer.** The free-data frontier is now evidenced exhausted (see above); opening a genuinely-distinct family requires a paid/consensus source (options chains, analyst revisions, macro consensus).

### Approaches already failed — do NOT repeat
- Re-running the fast invariants / 750 s baseline as the deliverable; appending another "verified, nothing to do" block; adding another guard test; reconciling a doc — make-work.
- Fabricating H202 or running another equity cross-section / discovery scan on the exhausted universe (directive §2).
- Editing `.github/workflows/**` in a commit — controller-restored; token lacks `workflows` scope.
- Re-declaring SEC 13F / FINRA / FRED / CBOE / N-CEN "data-blocked" without the named-source probe (all probed). **New:** do NOT re-attempt the N-CEN "heavier multi-exhibit parser" — evidenced a false premise (no data exhibit, no flow field).
- Chasing the `src/qtr` audit candidates as "bugs" — verified documented conventions / frozen numerical core.

### Precise next task (choose ONE, in priority order)
**Await maintainer action on the two blocked items above, then:**
- If paid/consensus source authorized: bump H-ID to H202 in `AGENTS.md` and `HYPOTHESIS_SPEC.md` (bump together per the AGENTS.md contract), open the new family per `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 313/319, and execute H202 on the paid source.
- If not authorized: the free-data research frontier is evidenced exhausted; no further free-data family search is warranted. Confirm the program remains closed.
Do NOT re-run the 750 s baseline, do NOT add more guards, do NOT re-declare 13F/FINRA/FRED/CBOE/N-CEN blocked, do NOT re-probe N-CEN, do NOT fabricate H202.

(End of file)