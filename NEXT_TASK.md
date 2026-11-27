# Next Task

## AUTHORITATIVE STATUS — Cycle 375 (2026-11-27): program CLOSED; both items maintainer-blocked. No agent-executable work.

First-hand this session (minimal, non-mutating checks only — NOT a full-suite re-run):
- `git status --porcelain` → empty; `git rev-list --left-right --count origin/main...HEAD` → `0  0` (HEAD == origin/main). No stashes; only `main`. Last 6 commits are handoff-file churn / empty control-markers (not progress). **No maintainer authorization has landed.**
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → applies clean (PATCH_APPLIES_CLEAN). Fresh evidence the maintainer one-liner below will work.
- Prior first-hand (Cycle 374, cited, tree unchanged): `verify_hypothesis_inventory.py` IN SYNC (H201); `pytest -q tests/test_gates_workflow.py` → 7 failed (expected red); `verify_gates_workflow_patch.py` → PATCH VERIFIED (resolves all 7).

Prior full-suite evidence (cited, NOT re-measured; tree unchanged): Cycle 332 → 5029 passed / 51 skipped / 0 failed (`python -m pytest -q --ignore=tests/test_gates_workflow.py`).

## Unresolved (maintainer action required — unchanged)

1. **Workflow contract patch** — `patches/0001-gates-workflow-contract-fix.patch` applies to live `gates.yml` and resolves all 7 `tests/test_gates_workflow.py` assertions (verified this session). Agent cannot land: `.github/workflows/**` controller-restored; repo token lacks `workflows` scope. Maintainer:
   `git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am "fix(ci): satisfy gates workflow contract" && git push origin main`
2. **Paid/consensus source authorization for H202** — pending maintainer. Free-data frontier evidenced exhausted (register Cycles 313/319; N-CEN multi-exhibit parser evidenced a false premise).

## Approaches already failed — do NOT repeat

- Re-running the full suite / fast invariants as the deliverable; appending "verified, nothing to do" blocks; adding guard tests; reconciling docs — make-work.
- Fabricating H202 or running another equity cross-section / discovery scan on the exhausted universe.
- Editing `.github/workflows/**` in a commit — controller-restored; token lacks `workflows` scope.
- Re-declaring SEC 13F / FINRA / FRED / CBOE / N-CEN "data-blocked" without a named-source probe (all probed). Do NOT re-attempt the N-CEN "heavier multi-exhibit parser" (false premise; Cycle 319).
- Empty-message / control-marker-only commits — not project progress.

## Loop-breaking instruction (final)

The "re-verify invariants + re-declare closure" cycle is the make-work failure mode. **Do NOT repeat it.** If no maintainer authorization has landed by the time the next agent runs, the correct action is a SHORT handoff that (a) states the program is closed, (b) cites prior full-suite evidence rather than re-measuring, and (c) **stops** — do not add guards, do not re-probe, do not fabricate H202, do not re-run the suite on an unchanged tree, do not make an empty commit.

## Next task (choose ONE, in priority order)

Await maintainer action on the two blocked items above, then:
- If paid/consensus source authorized: bump H-ID to H202 in `AGENTS.md` and `HYPOTHESIS_SPEC.md` (together per contract), open the new family per `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 313/319, execute H202 on the paid source.
- If not authorized: free-data research frontier evidenced exhausted; program remains closed.

(End of file)