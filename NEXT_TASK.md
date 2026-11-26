# Next Task

## AUTHORITATIVE STATUS — Cycle 334 (2026-11-26): program CLOSED; both items maintainer-blocked. No agent-executable work.

State unchanged from Cycle 333 (no re-measurement; full-suite re-runs are make-work per prior handoff):
- First-hand verified this session: `git status` clean; `origin/main...HEAD` → `0 0`; `patches/` holds only `0001-gates-workflow-contract-fix.patch` and `git apply --check` → PATCH_APPLIES_CLEAN.
- No maintainer authorization landed: last 20 commit bodies contain no `authoriz|H202|paid|consensus|maintainer|workflow` signal; recent commits are empty control-markers (not project progress).
- Prior full-suite evidence (Cycle 332, cited not re-measured): 5029 passed / 51 skipped / 0 failed (`python -m pytest -q --ignore=tests/test_gates_workflow.py`).
- `verify_hypothesis_inventory.py` → IN SYNC (H201 == H201) per Cycle 333.

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
The "re-verify invariants + re-declare closure" cycle has run through Cycle 333 and is the make-work failure mode. Do NOT repeat it. If no maintainer authorization has landed, the correct action is a SHORT handoff that (a) states the program is closed, (b) cites prior full-suite evidence rather than re-measuring, and (c) stops — do not add guards, do not re-probe, do not fabricate H202.

(End of file)