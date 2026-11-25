# Handoff for Next Agent — Cycle 317 (2026-11-25)

## Authoritative Status
**Free-data equity/fund cross-section program formally CLOSED** (Cycle 313). Baseline confirmed green:
- `test_runner_import_contract.py`: 316 passed (`-W error`)
- `test_verify_hypothesis_inventory.py`: 28 passed (`-W error`)
- `test_nf_20261122_04_size_premium.py` + `test_nf_20261125_01/02`: 39 passed (`-W error`)
- `ruff check src tests run_*.py scripts`: **All checks passed**
- `ruff format --check src tests run_*.py scripts`: **407 files already formatted**
- Working tree clean, `src/qtr` unchanged

## Executed Record
- **H1–H201 exhausted/rejected**; H189 data-blocked (gross profitability share overlap < 40 names)
- H187–H201 median OOS Sharpe: **0.187**
- Free-data sources probed and exhausted: SEC 13F, FINRA Reg SHO, FRED, SEC N-CEN (no Item C dollar flow), SEC N-PORT (holdings only), CBOE options (403)
- Evidence in `.cache/remaining_family_sources.json` (gitignored)

## Two Blocked Items Awaiting Maintainer Action

### 1. Workflow Contract Patch (agent-unreachable)
- **Patch:** `patches/0001-gates-workflow-contract-fix.patch` — applies cleanly, resolves all 7 contract violations
- **Verification:** `python scripts/verify_gates_workflow_patch.py` → "PATCH VERIFIED"
- **Maintainer action required:**
  ```bash
  git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am "fix(ci): satisfy gates workflow contract" && git push origin main
  ```
- Agent cannot land: `.github/workflows/**` is controller-restored; GitHub token lacks `workflows` scope

### 2. Paid/Consensus Source Authorization for H202
- Next H-ID is **H202** (requires maintainer-authorized paid/consensus data source per `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 313)
- Free frontier evidenced near-exhausted: no free source yields a bounded, distinct flow signal
- Agent cannot authorize or purchase data

## Approaches Already Failed — Do NOT Repeat
- Re-running the 750 s baseline as deliverable
- Adding more guards or reconciling docs (make-work)
- Fabricating H202 or running another equity cross-section on exhausted universe (directive §2)
- Editing `.github/workflows/**` in a commit (controller-restored)
- Re-declaring 13F/FINRA/FRED/N-CEN "data-blocked" without named-source probe
- Chasing `src/qtr` audit candidates as "bugs" (verified documented conventions)

## Next Agent Task (Priority Order)

**Wait for maintainer action on the two blocked items above, then:**

1. **If paid/consensus source authorized:**
   - Bump H-ID to **H202** in `AGENTS.md` and `HYPOTHESIS_SPEC.md` (bump together per AGENTS.md contract)
   - Open the new family per `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 313
   - Execute H202 on the paid source

2. **If not authorized:**
   - Confirm the free-data equity/fund cross-section program remains closed
   - No further free-data cross-sections (directive §2 forbids H187–H198 re-tests and universe/parameter variants)

**Do NOT:** re-run the 750 s baseline, add more guards, re-declare 13F/FINRA/FRED/N-CEN blocked, fabricate H202.

---

*All verification evidence captured above. Working tree clean. `src/qtr` unchanged.*