# Next Task

## AUTHORITATIVE STATUS — Cycle 313 (2026-11-25): Baseline restored to green (5026 passed, 51 skipped, `-W error`, excluding 7 agent-unreachable workflow tests). Two deterministic test-quality bugs fixed.

### What changed this session (durable, additive; `src/qtr` unchanged)
- **Fixed `tests/test_probe_sec_13f_holdings.py::test_probe_records_bad_cik_without_crashing`** — was order-dependent on ambient `.cache/13f/institutional_ciks.json` (relative `CACHE_DIR`). Patched `load_cik_name_map` to return the bundled `INSTITUTIONAL_CIKS` universe so the regression guard exercises only the bad-CIK handling under test. Now hermetic (no cache file created).
- **Fixed `tests/test_nf_20261125_01_institutional_flow.py::test_artifact_summary_exists_and_verdict`** — leaked an open file handle via `json.load(open(...))`, which triggered pytest's unraisable-exception plugin under `-W error`. Changed to `with open(...) as handle: json.load(handle)`.
- Both fixes verified in isolation, in-file, and full baseline (5026 passed / 51 skipped, 0 failed). Ruff clean.

### Unresolved (maintainer / next-session)
1. **Workflow contract patch — still unlanded.** `patches/0001-gates-workflow-contract-fix.patch` applies cleanly; `python scripts/verify_gates_workflow_patch.py` → exit 0, "PATCH VERIFIED ... resolves all 7 violation(s)". Agent cannot land: `.github/workflows/**` is controller-restored and the token lacks `workflows` scope. Awaits maintainer: `git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am "fix(ci): satisfy gates workflow contract" && git push origin main`.

### Approaches already failed — do NOT repeat
- Re-running the fast invariants / 750 s baseline as the deliverable; appending another "verified, nothing to do" block; adding another guard test; reconciling a doc — make-work.
- Fabricating H202 or running another equity cross-section / discovery scan on the exhausted universe (directive §2).
- Editing `.github/workflows/**` in a commit — controller-restored; token lacks `workflows` scope.
- Re-declaring SEC 13F / FINRA / FRED / N-CEN "data-blocked" without the named-source probe (all probed; N-CEN now additionally confirmed live to carry no Item-C dollar flow).
- Chasing the `src/qtr` audit candidates as "bugs" — verified documented conventions / frozen numerical core.

### Precise next task (choose ONE, in priority order)
**Option C (program closure) — execute now.** Formally close the free-data equity/fund cross-section program in this file, registering the Cycle 311/Cycle 312 reachability evidence (options CBOE 403; FRED reachable but no free macro-surprise consensus; N-CEN reachable + PIT but no Item-C dollar flow in `primary_doc.xml` for BlackRock or Vanguard; N-PORT holdings-only; SEC 13F/FINRA/FRED all probed). Then **request maintainer authorization for a paid/consensus source** (options chains, analyst revisions, macro consensus) to open a genuinely distinct mechanism family, since the free frontier is evidenced near-exhausted (H187–H201 median OOS Sharpe 0.187; no free source yields a bounded, distinct flow signal).

If deps are missing in a reset env, run `pip install -r requirements.txt` before any verification. Do NOT re-run the 750 s baseline, do NOT add more guards, do NOT re-declare 13F/FINRA/FRED/N-CEN blocked, do NOT fabricate H202.

(End of file - total 29 lines)