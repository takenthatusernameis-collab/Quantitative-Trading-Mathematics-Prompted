# Next Task

## AUTHORITATIVE STATUS — Cycle 367 (2026-11-26): program CLOSED; both items maintainer-blocked. No agent-executable work.

No maintainer authorization landed since Cycle 355. First-hand this session (minimal checks only, per loop-breaking rule):
- `git status --porcelain` → empty
- `git rev-list --left-right --count origin/main...HEAD` → `0  0` (HEAD == origin/main)
- New commits since prior handoff are empty control-marker commits only (`6c70ab9`, `576f412`) — not project progress.

Prior full-suite evidence (cited, NOT re-measured; tree unchanged): Cycle 332 → 5029 passed / 51 skipped / 0 failed (`python -m pytest -q --ignore=tests/test_gates_workflow.py`). Patch `patches/0001-gates-workflow-contract-fix.patch` applies cleanly; inventory in sync (H201 == H201).

## Unresolved (maintainer action required — unchanged)

1. **Workflow contract patch** — `patches/0001-gates-workflow-contract-fix.patch` applies cleanly; agent cannot land: `.github/workflows/**` controller-restored; repo token lacks `workflows` scope. Maintainer: `git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am "fix(ci): satisfy gates workflow contract" && git push origin main`.
2. **Paid/consensus source authorization for H202** — pending maintainer. Free-data frontier evidenced exhausted (register Cycles 313/319; N-CEN multi-exhibit parser evidenced a false premise).

## Approaches already failed — do NOT repeat

- Re-running full suite / fast invariants as the deliverable; appending "verified, nothing to do" blocks; adding guard tests; reconciling docs — make-work.
- Fabricating H202 or running another equity cross-section / discovery scan on the exhausted universe.
- Editing `.github/workflows/**` in a commit — controller-restored; token lacks `workflows` scope.
- Re-declaring SEC 13F / FINRA / FRED / CBOE / N-CEN "data-blocked" without named-source probe (all probed). Do NOT re-attempt the N-CEN "heavier multi-exhibit parser" (false premise; Cycle 319).
- Empty-message / control-marker-only commits — not project progress.

## Loop-breaking instruction (final)

The "re-verify invariants + re-declare closure" cycle is the make-work failure mode. **Do NOT repeat it.** If no maintainer authorization has landed by the time the next agent runs, the correct action is a SHORT handoff that (a) states the program is closed, (b) cites prior full-suite evidence rather than re-measuring, and (c) **stops** — do not add guards, do not re-probe, do not fabricate H202, do not re-run the suite on an unchanged tree, do not make an empty commit.

## Next task (choose ONE, in priority order)

Await maintainer action on the two blocked items above, then:
- If paid/consensus source authorized: bump H-ID to H202 in `AGENTS.md` and `HYPOTHESIS_SPEC.md` (together per contract), open the new family per `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 313/319, execute H202 on the paid source.
- If not authorized: free-data research frontier evidenced exhausted; program remains closed.

(End of file)
