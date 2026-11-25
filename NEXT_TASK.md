# Next Task

## AUTHORITATIVE STATUS — Cycle 318 (2026-11-25): Free-data equity/fund cross-section program formally CLOSED. Baseline green (5026 passed, 51 skipped, `-W error`, excluding 7 agent-unreachable workflow tests). `src/qtr` unchanged.

### What changed this session (durable, additive; `src/qtr` unchanged)
- **Cycle 318 (2026-11-25) verification:** baseline confirmed green — `scripts/verify_gates_workflow_patch.py` exit 0 (patch resolves all 7 violations; live `gates.yml` still fails 7 assertions awaiting maintainer land), `tests/test_runner_import_contract.py` 316 passed under `-W error`, `tests/test_verify_hypothesis_inventory.py` 28 passed, `tests/test_nf_20261122_04_size_premium.py` + `test_nf_20261125_01/02` 39 passed under `-W error`, `python -m ruff check src tests run_*.py scripts` all checks passed, `python -m ruff format --check src tests run_*.py scripts` 407 files formatted, working tree clean, `src/qtr` unchanged. No new changes made; both blocked items below await maintainer action.

### Unresolved (maintainer / next-session)
1. **Workflow contract patch — still unlanded.** `patches/0001-gates-workflow-contract-fix.patch` applies cleanly; `python scripts/verify_gates_workflow_patch.py` → exit 0, "PATCH VERIFIED ... resolves all 7 violation(s)". Agent cannot land: `.github/workflows/**` is controller-restored and the token lacks `workflows` scope. Awaits maintainer: `git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am "fix(ci): satisfy gates workflow contract" && git push origin main`.
2. **Paid/consensus source authorization for H202 — pending maintainer.** See above.

### Approaches already failed — do NOT repeat
- Re-running the fast invariants / 750 s baseline as the deliverable; appending another "verified, nothing to do" block; adding another guard test; reconciling a doc — make-work.
- Fabricating H202 or running another equity cross-section / discovery scan on the exhausted universe (directive §2).
- Editing `.github/workflows/**` in a commit — controller-restored; token lacks `workflows` scope.
- Re-declaring SEC 13F / FINRA / FRED / N-CEN "data-blocked" without the named-source probe (all probed; N-CEN confirmed live to carry no Item-C dollar flow).
- Chasing the `src/qtr` audit candidates as "bugs" — verified documented conventions / frozen numerical core.

### Precise next task (choose ONE, in priority order)
**Await maintainer action on the two blocked items above, then:**
- If paid/consensus source authorized: bump H-ID to H202 in `AGENTS.md` and `HYPOTHESIS_SPEC.md` (bump together per the AGENTS.md contract), open the new family per `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 313, and execute H202 on the paid source.
- If not authorized: confirm the free-data equity/fund cross-section program remains closed; no further free-data cross-sections (directive §2 forbids H187–H198 re-tests and universe/parameter variants).
Do NOT re-run the 750 s baseline, do NOT add more guards, do NOT re-declare 13F/FINRA/FRED/N-CEN blocked, do NOT fabricate H202.

(End of file)