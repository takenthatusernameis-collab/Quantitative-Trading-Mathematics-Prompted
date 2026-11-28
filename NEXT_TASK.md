# Next Task

## AUTHORITATIVE STATUS — Cycle 424 (2026-11-28T03:58Z): program CLOSED; both items maintainer-blocked. No agent-executable work.

Single sanctioned bounded check this session (re-verified, not re-measured): `git fetch origin main`
→ exit 0 (network reachable); `git rev-list --left-right --count origin/main...HEAD` → `0  0`
(**no maintainer commit landed**; no maintainer commit ahead of or behind HEAD). Tree clean
(`git status --short` empty). No other verification performed — no suite re-run, no data re-probe,
no guard added, no H202 fabricated (per loop-breaking instruction below).

Prior full-suite evidence (cited, NOT re-measured; tree unchanged since Cycle 332):
`python -m pytest -q --ignore=tests/test_gates_workflow.py` → **5029 passed / 51 skipped / 0 failed**.
`tests/test_gates_workflow.py` red by design (7 failed) until the patch lands.

## Unresolved (maintainer action required — unchanged)

1. **Workflow contract patch** — `patches/0001-gates-workflow-contract-fix.patch` applies clean and
   resolves all 7 `tests/test_gates_workflow.py` assertions. Agent cannot land: `.github/workflows/**`
   controller-restored; repo token lacks `workflows` scope.
   Maintainer: `git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am "fix(ci): satisfy gates workflow contract" && git push origin main`
2. **Paid/consensus source authorization for H202** — pending maintainer. Free-data frontier
   evidenced exhausted (Cycles 313/319; N-CEN multi-exhibit parser false premise).

## Approaches already failed — do NOT repeat

- Re-running the full suite / fast invariants as the deliverable; appending "verified, nothing to do"
  blocks; adding guard tests; reconciling docs; churning handoff docs — make-work / control-marker commits.
- Fabricating H202 or running another equity cross-section / discovery scan on the exhausted universe.
- Editing `.github/workflows/**` in a commit — controller-restored; token lacks `workflows` scope.
- Re-declaring SEC 13F / FINRA / FRED / CBOE / N-CEN "data-blocked" without a named-source probe
  (all probed). Do NOT re-attempt the N-CEN "heavier multi-exhibit parser" (false premise; Cycle 319).
- Empty-message / control-marker-only commits — not project progress.

## Loop-breaking instruction (final)

Do NOT repeat the "re-verify invariants + re-declare closure" cycle, and do NOT churn handoff docs.
If no maintainer authorization has landed by the time the next agent runs, the correct action is a
SHORT handoff that (a) states the program is closed, (b) cites prior full-suite evidence rather than
re-measuring, and (c) **stops** — do not add guards, do not re-probe data sources, do not fabricate
H202, do not re-run the suite on an unchanged tree, do not make an empty/control-marker commit. A
single bounded `git fetch` to check for maintainer authorization is the only sanctioned verification.

## Next task (choose ONE, in priority order)

Await maintainer action on the two blocked items above, then:
- If paid/consensus source authorized: bump H-ID to H202 in `AGENTS.md` and `HYPOTHESIS_SPEC.md`
  (together per contract), open the new family per `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 313/319,
  execute H202 on the paid source.
- If not authorized: free-data research frontier evidenced exhausted; program remains closed.

(End of file)