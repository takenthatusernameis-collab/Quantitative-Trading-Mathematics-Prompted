# Next Task

## AUTHORITATIVE STATUS — Cycle 308 (2026-11-25): SEC 13F institutional-flow source REACHABLE (durable "data-blocked" correction); probe defects fixed; H200 unblocked

**Read this block only. It supersedes the prior "loop terminated / no task" consolidation: that
consolidation was itself the repeated-failure loop (reliability rule 2), so this cycle executed a
genuinely deferred, never-run bounded probe instead of re-appending it.**

### What changed this session (durable, additive; `src/qtr` unchanged)
- **First real execution of `scripts/probe_sec_13f_holdings.py` against SEC EDGAR** (it had been
  classified "data-blocked (no free PIT 13F source)" since Cycle 96 but never actually run). Artifact:
  `.experiments/nf_runs/nf_20261125_01_sec13f_availability_20261125_055740/coverage.json`.
- **Durable finding:** SEC Form 13F-HR is **REACHABLE and PIT-parseable for free** — the "no free PIT 13F
  source" blocker is **refuted** (same class as FRED/Binance/Chinese-futures corrections). Verified on two
  independent large filers: **Berkshire (0001067983)** 2718 positions / 40 quarters / 45 d median lag, and
  **MassMutual (0001103653)** 37643 positions / 51 quarters / 40 d median lag; PIT field
  `acceptanceDateTime` (2014-02-13 → 2026-11-16). This unblocks the **institutional-flow / herding family
  (NF-20261110-08)** previously deferred for "PIT parsing complexity".
- **Two defects fixed:** (1) robustness — a single stale CIK (HTTP 404) no longer aborts the whole run;
  `probe()` records it in `missing_submissions` + new `missing_errors` and continues (pinned by
  `tests/test_probe_sec_13f_holdings.py::test_probe_records_bad_cik_without_crashing`, 15 → 16 passed).
  (2) CIK-map data quality — the bundled `INSTITUTIONAL_CIKS` map is **52/57 stale** (only 5/57 CIKs
  return 200); MassMutual's entry corrected to its authoritative SEC CIK. The remaining ~51 stale entries
  were NOT hand-guessed.
- **No new H-ID, no fabricated H200.** Inventory high-water mark stays **H199**. Artifact-schema test
  bumped +1 probe dir (`EXPECTED_TOTAL_DIRS` 128 → 129; new incomplete dir; summary count / key sets /
  cache-only unchanged). No runner, gate, threshold, frozen number, or prior artifact changed.

### What I actually verified (fresh evidence, 2026-11-25)
- `tests/test_probe_sec_13f_holdings.py` → **16 passed**; `test_experiment_artifact_schema` +
  `test_probe_report_schema` + `test_probe_script_coverage` → **146 passed**.
- `scripts/verify_hypothesis_inventory.py` → **IN SYNC** (H199 == H199).
- Coverage artifact: 2/2 filers with positions, 40361 positions, PIT 2014-02-13 → 2026-11-16, 42.5 d median lag.
- CIK-map sweep: **5/57 bundled CIKs valid (200), 52/57 stale (404)** — quantified, not guessed.

### Unresolved (maintainer / next-session)
1. **Rebuild the 13F filer CIK map (precise next task).** The bundled map is 52/57 stale. Rebuild from an
   authoritative SEC source (SEC company search / Form 13F data sets), verify each submissions URL returns
   200, then pre-register and execute **H200** as a genuinely-distinct **institutional-flow (13F
   holdings-change) cross-section/timing** mechanism on the free PIT 13F source (report `reportDate` +
   `acceptanceDateTime` ~45-day lag), standard 8 gates + protected holdout. This is the first repo-new
   family with a now-evidenced free PIT source — NOT a parameter/universe/timeframe variant of any
   exhausted family.
2. **Workflow contract patch — the sole remaining test red (7 `tests/test_gates_workflow.py` failures).**
   `.github/workflows/**` is agent-unreachable (restored by `.github/scripts/kilo-controller.sh`; token
   lacks `workflows` scope). Maintainer runs:
   `git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am "fix(ci): satisfy gates workflow contract" && git push origin main`
   (re-proven this session: applies cleanly; `scripts/verify_gates_workflow_patch.py` → PATCH VERIFIED).
   Do NOT re-edit `gates.yml` in a commit; do NOT weaken the contract test.
3. **Equity cross-section program closure / new universe (unchanged).** H1–H199 exhausted/rejected; the
   reject is genuine mechanism weakness (median strategy OOS Sharpe 0.187 vs passive equal-weight book
   1.075; 11/11 negative IR). A new equity cross-section on the same 98-name / broad universe is ruled out.

### Approaches already failed — do NOT repeat
- Re-running the fast invariants / 750 s baseline **as the deliverable**; appending another "verified,
  nothing to do" block; adding another guard test; reconciling a doc (Cycles ~257–307) — make-work; this
  consolidation + the 13F probe replace that loop.
- Fabricating H200 or running another equity cross-section / discovery scan on the exhausted universe.
- Editing `.github/workflows/**` in a commit — controller restores it; token lacks `workflows` scope.
- **Re-declaring SEC 13F "data-blocked"** — refuted this cycle with a reproducible free artifact.
- Chasing the `src/qtr` audit candidates (cost-attribution timing, negative-equity drawdown, beta ddof,
  market-impact NaN, `QTR_CACHE_DIR` fallback) as "bugs" — verified documented conventions / false
  positives / frozen numerical core.

### Precise next task
Rebuild the 13F filer CIK map from an authoritative SEC source (verify 200 per CIK), then pre-register and
execute **H200** (institutional-flow / 13F holdings-change mechanism) on the now-evidenced free PIT 13F
source, with the standard 8 gates and protected holdout. If deps are missing in a reset env, run
`pip install -r requirements.txt` before any verification. Do NOT re-run the 750 s baseline, do NOT add
more guards, do NOT re-declare 13F blocked.