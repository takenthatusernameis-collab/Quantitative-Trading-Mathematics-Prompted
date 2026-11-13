# NEXT_TASK.md — stale prose corrections landed; gates workflow patch remains maintainer-gated

## What changed this session (2026-11-13)

Two committed audit reports carried prose figures that contradicted their own
pinned baselines/measurements. Both are corrected in the working tree. No
`src/qtr`, test, gate, threshold, verdict, artifact, or frozen number was
modified; no commit/push was made by the agent (the controller checkpoints the
worktree).

1. **`REPRODUCIBILITY_AUDIT_REPORT.md`** — the missing-artifact arithmetic was
   wrong. Correct values, re-derived from the test baseline, the planner, and the
   committed CSV:
   - `missing_files` = **197** = **172 H28 contract-blocked** + **25
     unrecoverable**; **149** non-H28 hash-exact artifacts were restored on
     2026-11-12 (346 → 197).
   - The old prose said "25 remaining" and "321 were applied … 346 → 25"; both
     were false. The 321 is the number of hash-exact candidates (149 restored +
     172 H28-excluded), not the number applied.
   - The stale example (`exp_2026-10-11T18-36-51-113738Z` "is empty") was
     replaced: that run now has 14/15 artifacts and misses only `summary.json`;
     the current worst non-H28 example is `exp_2026-10-13T21-46-52-446478Z`
     (`h17_vrp`, 12 missing).
   - Verification table's "3641 passed, 51 skipped" was stale; it now records
     **3,743 passed / 51 skipped / 7 failed** (all 7 = maintainer-gated
     `tests/test_gates_workflow.py`).

2. **`BACKTEST_PERF_PROFILE_RESULTS.md`** — conclusions overstated the measured
   matrix:
   - The matrix's largest cell is **200 symbols × 5 years (1,260 bars) =
     21.3s / 93.9MB**, not "500 symbols × 10 years in ~22s / <100MB".
   - Linear extrapolation to 500 × 10 years is **~117s / ~521MB**; the report now
     labels it an extrapolation and says to measure it before claiming it.
   - The "200 symbols × 10 years (93MB)" memory claim was actually the measured
     200 × 5-year cell; corrected.
   - CSV row count corrected 36 → **33**.
   - Fallback-item status updated: engine edge stress
     (`tests/test_engine_edge_stress.py`, 12 passed), lineage report
     (`scripts/generate_experiment_lineage_report.py`), and performance
     regression gate (`scripts/backtest_perf_regression_gate.py`) are all done.

## Actually verified this session (own evidence)

- Full suite `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`
  → **7 failed, 3,743 passed, 51 skipped** (429s). All 7 failures are
  `tests/test_gates_workflow.py` (maintainer-gated workflow contract). Coverage
  **100.00%** (1,211 stmts / 422 branches, 0 miss).
- `python -m ruff check src tests run_*.py scripts` → All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` → 327 files formatted.
- Focused audits — **133 passed**:
  `tests/test_reproducibility_audit.py`, `tests/test_artifact_restoration_plan.py`,
  `tests/test_experiment_artifact_schema.py`,
  `tests/test_experiment_lineage_report.py`,
  `tests/test_performance_regression_gate.py`,
  `tests/test_engine_edge_stress.py`.
- Core suite (engine/config/cost/statistics/data) — **359 passed**.
- `python scripts/plan_artifact_restoration.py` (read-only) → **0 recoverable /
  172 excluded / 25 unrecoverable**; CSV has 197 data rows
  (`excluded=172`, `unrecoverable=25`).
- Independent recount of `.experiments/nf_runs` summaries: **95** summary files,
  **130** distinct keys, **9** keys ≥50%, **3** keys ≥80% (`data`, `gates`,
  `verdict`) — matches `EXPERIMENT_ARTIFACT_AUDIT.md` and its pinned test.

## What remains unresolved

- **gates.yml contract (maintainer-only).** `tests/test_gates_workflow.py` is red
  7/7 on `origin/main` by design of the controller block. The apply-ready fix is
  `patches/0001-gates-workflow-contract-fix.patch`; it applies cleanly and makes
  the contract 7/7 in isolation. Landing it requires a credential with
  `workflow` scope:
  ```bash
  git apply patches/0001-gates-workflow-contract-fix.patch
  git commit -am "fix(ci): satisfy gates workflow contract"
  git push origin main
  ```
  Do **not** edit `.github/workflows/gates.yml` in-tree and expect persistence:
  `.github/scripts/kilo-controller.sh:305-323` restores/excludes it, and the repo
  token has no `workflows` permission. This has failed for 8 cycles.
- **H182** — free-data PIT strategy-family queue exhausted (H1–H181
  executed/rejected; commodity carry data-blocked; insider/earnings/options PIT
  unavailable without paid services). Requires explicit authorization plus an
  authorized data source. Do not pre-register or execute.
- **Artifact restoration apply** — authorization-gated. Current plan: 0
  recoverable / 172 excluded (H28 depth-one path conflict) / 25 unrecoverable
  (no hash-exact source).

## Failed approaches / do not blindly repeat

- **Do not trust prose counts in committed reports.** The two errors fixed this
  session survived multiple cycles because the prose was not derived from the
  pinned baseline/planner/CSV. Re-derive before acting on any "remaining"/
  "restored"/"missing" figure.
- **Do not commit a `gates.yml` edit** expecting persistence (8 cycles reverted).
- **Do not weaken** `tests/test_gates_workflow.py`, the 100% coverage gate, or any
  frozen contract.
- **Do not mass-edit** runners/tests/gates to force the suite green.
- **Do not add contested per-trade logs** to `TRADE_LOG_RECORD`; the partition
  test forbids it.

## One precise next task

**Read-only audit of the 11 hash mismatches** (`REPRODUCIBILITY_BASELINE["hash_mismatches"] = 11`).

Current inventory (re-derived this session with the audit's own hash logic):
- **8 × `param_grid_results`** across 8 experiments: 4 with recorded
  `3c3ca96bf45b5f28` (all on disk as `2cfbb88200656d0d`), 2 with
  `3c5c66cd85442477` (on disk as `c7a1cedb8a4fc5b1`), 2 with
  `5aa48f8683d54d37` (on disk as `b7dddfb0dc0c524d`). These are shared grid
  files overwritten by a later run.
- **3 × `summary.json`** under `.experiments/nf_runs/`:
  `nf_20261105_14_credit_regime`, `nf_20261105_16_usd_macro`,
  `nf_20261105_19_pead` (each recorded vs on-disk hash differs).

For each mismatch, record: `experiment_id`, artifact name, recorded 16-char
SHA-256 prefix, on-disk prefix, likely cause (shared `param_grid_results`
overwritten by a later run vs `summary.json` under `.experiments/nf_runs/`), and
whether any published/frozen number, gate, or test pins that artifact. Append the
table to `REPRODUCIBILITY_AUDIT_REPORT.md` §2 and state whether the on-disk file
is authoritative. If any mismatch feeds a published/frozen value, escalate for
authorization; do not rewrite `experiments.jsonl` or overwrite artifacts.

Verify with `python -m pytest -q tests/test_reproducibility_audit.py` (7 passed)
and the read-only planner; no baseline change is expected. This is bounded,
requires no data download or authorization, and directly informs remediation
item 3.