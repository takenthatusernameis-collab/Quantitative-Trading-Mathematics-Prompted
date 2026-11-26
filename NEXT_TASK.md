# Next Task

## AUTHORITATIVE STATUS — Cycle 333 (2026-11-26): program CLOSED; both items maintainer-blocked. No agent-executable work.

State unchanged from Cycle 332 (no re-measurement):
- `git status` clean; `origin/main...HEAD` → `0 0`; `patches/` holds only `0001-gates-workflow-contract-fix.patch` (applies cleanly).
- Cycle 332 first-hand full-suite evidence: 5029 passed / 51 skipped / 0 failed (`python -m pytest -q --ignore=tests/test_gates_workflow.py`).
- `verify_hypothesis_inventory.py` → IN SYNC (H201 == H201; 101 documented H-IDs).
- `verify_gates_workflow_patch.py` → exit 0: patch resolves all 7 violations; maintainer-gated (workflows-scoped credentials).

## Unresolved (maintainer action required)
1. **Workflow contract patch** — `patches/0001-gates-workflow-contract-fix.patch` applies cleanly; agent cannot land (`.github/workflows/**` controller-restored; token lacks `workflows` scope). Maintainer: `git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am "fix(ci): satisfy gates workflow contract" && git push origin main`.
2. **Paid/consensus source authorization for H202** — pending maintainer. Free-data frontier evidenced exhausted (N-CEN false premise; register Cycle 319).

## Approaches already failed — do NOT repeat
- Re-running full suite / fast invariants as deliverable; appending "verified, nothing to do" blocks; adding guard tests; reconciling docs — make-work.
- Fabricating H202 or running another equity cross-section / discovery scan on the exhausted universe (directive §2).
- Editing `.github/workflows/**` in a commit — controller-restored; token lacks `workflows` scope.
- Re-declaring SEC 13F / FINRA / FRED / CBOE / N-CEN "data-blocked" without named-source probe (all probed). Do NOT re-attempt the N-CEN "heavier multi-exhibit parser" (false premise; register Cycle 319).

## Next task (choose ONE, in priority order)
Await maintainer action on the two blocked items above, then:
- If paid/consensus source authorized: bump H-ID to H202 in `AGENTS.md` and `HYPOTHESIS_SPEC.md` (together per contract), open the new family per `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 313/319, execute H202 on the paid source.
- If not authorized: free-data research frontier evidenced exhausted; confirm program remains closed.

## Loop-breaking instruction
The "re-verify invariants + re-declare closure" cycle has run through Cycle 332 and is the make-work failure mode. Do NOT repeat it. If no maintainer authorization has landed, the correct action is a SHORT handoff that (a) states the program is closed, (b) cites Cycle 332 full-suite evidence rather than re-measuring, and (c) stops — do not add guards, do not re-probe, do not fabricate H202.

(End of file)
