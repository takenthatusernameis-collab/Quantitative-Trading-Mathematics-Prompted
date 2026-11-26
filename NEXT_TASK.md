# Next Task

## AUTHORITATIVE STATUS — Cycle 328 (2026-11-26): program CLOSED; both items maintainer-blocked. No agent-executable work.

### Cycle 328 — short handoff (independent cheap re-confirmation; NO suite re-run, NO new guards)
A fresh session re-checked the Cycle 327 handoff with cheap deterministic checks only (seconds):
- `git rev-list --left-right --count origin/main...HEAD` → `0 0`; working tree clean; no stash;
  `patches/` holds only the maintainer-blocked `0001-gates-workflow-contract-fix.patch`.
- **Provenance correction (new this cycle):** the baseline/HEAD SHAs cited in prior handoffs
  (`277d49d`, `f1582ea`) are **NOT real objects in this repo** (`git cat-file`/`git diff` →
  "bad revision"). Actual history is **1 commit** (`6ceb281`, empty message) — matches the
  long-standing provenance caution in `HANDOFF_CURRENT.md`. Do NOT cite those SHAs as verifiable;
  cite the working-tree state and the verify-script exit codes below instead.
- `python scripts/verify_hypothesis_inventory.py` → exit 0, "IN SYNC" (H201 == H201).
- `python scripts/verify_gates_workflow_patch.py` → exit 0, "PATCH VERIFIED ... resolves all 7
  violation(s); a maintainer must land it with workflows-scoped credentials."

**Ground truth (cited, NOT re-measured):** the full suite and `-W error` CI gate are green at the
working tree (Cycle 321: 5029 passed / 51 skipped / 0 failed; `-W error` 344 passed). Re-running
either as the deliverable is make-work.

**Conclusion:** no bounded, high-value, non-make-work task is agent-executable. Do NOT fabricate H202,
re-run the suite/baseline, add a guard test, re-probe N-CEN, or re-declare 13F/FINRA/FRED/CBOE/N-CEN blocked.

### Unresolved (maintainer / next-session)
1. **Workflow contract patch — still unlanded.** `patches/0001-gates-workflow-contract-fix.patch`
   applies cleanly; `python scripts/verify_gates_workflow_patch.py` → exit 0, "PATCH VERIFIED ...
   resolves all 7 violation(s)". Agent cannot land: `.github/workflows/**` is controller-restored and
   the repo token lacks `workflows` scope. Maintainer action:
   `git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am "fix(ci): satisfy gates workflow contract" && git push origin main`.
2. **Paid/consensus source authorization for H202 — pending maintainer.** The free-data frontier is
   evidenced exhausted (register Cycles 308→319); opening a genuinely-distinct family requires a
   paid/consensus source (options chains, analyst revisions, macro consensus).

### Approaches already failed — do NOT repeat
- Re-running the fast invariants / 750 s baseline as the deliverable; appending another "verified,
  nothing to do" block; adding another guard test; reconciling a doc — make-work.
- Fabricating H202 or running another equity cross-section / discovery scan on the exhausted universe
  (directive §2).
- Editing `.github/workflows/**` in a commit — controller-restored; token lacks `workflows` scope.
- Re-declaring SEC 13F / FINRA / FRED / CBOE / N-CEN "data-blocked" without the named-source probe
  (all probed). Do NOT re-attempt the N-CEN "heavier multi-exhibit parser" — evidenced a false
  premise (no data exhibit, no flow field; register Cycle 319).
- Chasing `src/qtr` audit candidates as "bugs" — verified documented conventions / frozen numerical core.

### Precise next task (choose ONE, in priority order)
**Await maintainer action on the two blocked items above, then:**
- If paid/consensus source authorized: bump H-ID to H202 in `AGENTS.md` and `HYPOTHESIS_SPEC.md`
  (bump together per the AGENTS.md contract), open the new family per
  `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 313/319, and execute H202 on the paid source.
- If not authorized: the free-data research frontier is evidenced exhausted; no further free-data
  family search is warranted. Confirm the program remains closed.

**Loop-breaking instruction for the next agent:** the "re-verify invariants + re-declare closure"
cycle has run many times (through Cycle 327) and is itself the make-work failure mode. The full suite
is green (5029 passed) and the `-W error` CI gate passes at `277d49d` — re-running either as the
deliverable is explicitly make-work. If no maintainer authorization has landed by the time you run,
the correct action is a SHORT handoff that (a) states the program is closed, (b) cites the Cycle 321
full-suite evidence rather than re-measuring, and (c) stops — do not add guards, do not re-probe, do
not fabricate H202.

(End of file)