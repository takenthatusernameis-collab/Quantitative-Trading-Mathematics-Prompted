# Handoff — Next Session: Free-data program closed at Cycle 322; both open items maintainer-blocked

## Authoritative status (Cycle 322, 2026-11-26, HEAD `277d49d`)

- **Full test suite green:** `python -m pytest -q --ignore=tests/test_gates_workflow.py` → **5029 passed, 51 skipped, 0 failed** (756 s). The 51 skips are legitimate artifact-conditional/container-convention skips; `test_gates_workflow.py` is red by design (maintainer-gated).
- **CI `-W error` gate holds:** `pytest -W error tests/test_runner_import_contract.py tests/test_verify_hypothesis_inventory.py` → **344 passed** (Cycle-278 `google.protobuf` DeprecationWarning escape remains fixed).
- **Fast invariants clean:** `ruff check` + `ruff format --check` clean (407 files); `verify_hypothesis_inventory.py` IN SYNC (H201 == H201); `verify_gates_workflow_patch.py` exit 0 (resolves all 7 violations); `git rev-list --left-right --count origin/main...HEAD` → `0 0`; no TODO/FIXME/XXX/HACK in `src/`/`scripts/`/`run_*.py`.
- **Coverage gate** remains `fail_under = 100` (`pyproject.toml`); not re-measured (frozen numerical core, no change to `src/qtr`).

## Hypothesis inventory

**H1–H201 exhausted/rejected; H189 data-blocked.** Free-data equity/fund cross-section program **CLOSED (Cycle 313)**. Latest executed: H201 short-interest/days-to-cover (FINRA Reg SHO) REJECT 4/8 (Cycle 310). Prior: H200 institutional flow/13F REJECT 2/8 (Cycle 308). Next unused H-ID: **H202** (requires maintainer-authorized paid/consensus data source; see `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 313/319).

## Unresolved (maintainer action required)

1. **Workflow contract patch** — `patches/0001-gates-workflow-contract-fix.patch` applies cleanly; `python scripts/verify_gates_workflow_patch.py` → exit 0, "resolves all 7 violation(s)". Agent cannot land: `.github/workflows/**` is controller-restored; token lacks `workflows` scope. Awaits maintainer: `git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am "fix(ci): satisfy gates workflow contract" && git push origin main`.

2. **Paid/consensus source authorization for H202** — free-data frontier evidenced exhausted (N-CEN multi-exhibit path proven false premise; no remaining free candidate). Opening a genuinely-distinct family requires a paid/consensus source (options chains, analyst revisions, macro consensus).

## Approaches already failed — do NOT repeat

- Re-running the full suite / fast invariants as the deliverable; appending another "verified, nothing to do" block; adding guard tests; reconciling docs — make-work.
- Fabricating H202 or running another equity cross-section / discovery scan on the exhausted universe (directive §2).
- Editing `.github/workflows/**` in a commit — controller-restored; token lacks `workflows` scope.
- Re-declaring SEC 13F / FINRA / FRED / CBOE / N-CEN "data-blocked" without the named-source probe (all probed). **New:** do NOT re-attempt the N-CEN "heavier multi-exhibit parser" — evidenced a false premise (no data exhibit, no flow field).
- Chasing `src/qtr` audit candidates as "bugs" — verified documented conventions / frozen numerical core.

## Next task (if/when maintainer authorization lands)

- **If paid/consensus source authorized:** bump H-ID to H202 in `AGENTS.md` and `HYPOTHESIS_SPEC.md` (together per contract), open the new family per `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 313/319, and execute H202 on the paid source.
- **If not authorized:** the free-data research frontier is evidenced exhausted; no further free-data family search is warranted. Confirm the program remains closed.

## Loop-breaking instruction for the next agent

The "re-verify invariants + re-declare closure" cycle has run through Cycle 322 and is itself the make-work failure mode. **Do NOT repeat it.** The full suite is green (5029 passed) and the `-W error` CI gate passes at `277d49d` — re-running either as the deliverable is explicitly make-work. If no maintainer authorization has landed by the time you run, the correct action is a SHORT handoff that (a) states the program is closed, (b) cites the Cycle 321/322 full-suite evidence rather than re-measuring, and (c) **stops** — do not add guards, do not re-probe, do not fabricate H202.

---

(End of handoff)