# NEXT_TASK.md — 11 hash mismatches audited; on-disk authoritative; orphan audit next

## What changed this session (2026-11-13)

Completed the previous agent's assigned task: a **read-only audit of the 11
hash mismatches** (`REPRODUCIBILITY_BASELINE["hash_mismatches"] = 11`). The
audit table, causes, pinning status, and authority verdict are appended to
`REPRODUCIBILITY_AUDIT_REPORT.md` §2. No `src/qtr`, test, gate, threshold,
verdict, artifact, or frozen number was modified; no commit/push was made.

Findings (all re-derived with the audit's own hash logic):

- **8 × `param_grid_results`** (`ts_momentum_20etf_v1` ×4,
  `cs_momentum_10etf_v1` ×2, `regime_gated_momentum_20etf_v1` ×2): the runner
  calls `log_dataframe("param_grid_results", ...)` more than once on the same
  path with different DataFrame contents (e.g.
  `run_ts_momentum_experiment.py:440/473/708`,
  `run_cs_momentum_experiment.py:294/516`,
  `run_regime_gated_momentum_experiment.py:573/613`). Only one write survives on
  disk; the other recorded name is superseded. The on-disk file matches the
  other recorded name in every case.
- **3 × `summary.json`** under `.experiments/nf_runs/`
  (`nf_20261105_14_credit_regime`, `_16_usd_macro`, `_19_pead`): the runner
  derives `run_dir` from `EXPERIMENT_NAME` alone
  (`run_nf_20261105_14_credit_regime.py:281`, `..._16_usd_macro.py:281`,
  `..._19_pead.py:292`), so a later re-run overwrote `summary.json`. The
  on-disk hash equals the later record in all three cases.

**No mismatch feeds a published/frozen number.** The frozen
`param_grid_summary` values (`n_combos`, `benjamini_hochberg_significant`) are
re-derived from the *on-disk* parquet by
`tests/test_h54_non_metrics_block_disclosure.py::test_the_re_derivable_families_re_derive`;
an independent recount confirms all 8 on-disk grids match their summaries
(18/18, 54/54, 108/108 rows, BH = 0). `HYPOTHESIS_SPEC.md` cites the later
execution ids for `_16_usd_macro` and `_19_pead`. **The on-disk file is
authoritative in all 11 rows.**

## Actually verified this session (own evidence)

- `python -m pytest -q tests/test_reproducibility_audit.py` → **7 passed**.
- `python -m pytest -q tests/test_h54_non_metrics_block_disclosure.py` → **21
  passed** (proves the on-disk grids re-derive the published values).
- `python -m pytest -q tests/test_nf_20261105_1{4,6,9}_*.py` → **34 passed**.
- `python scripts/plan_artifact_restoration.py` (read-only) → **0 recoverable /
  172 excluded / 25 unrecoverable** (unchanged; output files byte-identical).
- Cross-basename hash-exact scan of all **2,155** non-sidecar files under
  `.experiments` (446 MB): **0** hash-exact sources for the 25 unrecoverable
  rows. The 88 cross-basename candidate pairs all belong to H28 contract-blocked
  rows, so they do not reduce the backlog.
- `python -m ruff check src tests run_*.py scripts` → All checks passed.

## What remains unresolved

- **gates.yml contract (maintainer-only).** `tests/test_gates_workflow.py` is red
  7/7 on `origin/main` by design of the controller block. The apply-ready fix is
  `patches/0001-gates-workflow-contract-fix.patch`; landing it requires a
  credential with `workflow` scope. Do **not** edit
  `.github/workflows/gates.yml` in-tree and expect persistence (8 cycles
  reverted).
- **H182** — free-data PIT strategy-family queue exhausted (H1–H181
  executed/rejected; commodity carry data-blocked; insider/earnings/options PIT
  unavailable without paid services). Requires explicit authorization plus an
  authorized data source. Do not pre-register or execute.
- **Artifact restoration apply** — authorization-gated. 172 H28 contract-blocked
  + 25 unrecoverable (no hash-exact source anywhere, now verified).
- **experiments.jsonl dedup** — the 8 superseded duplicate
  `param_grid_results` keys and 3 stale nf hashes could be dropped, but this edits
  the committed record and is authorization-gated. Do not do it without approval.

## Failed approaches / do not blindly repeat

- **Do not re-run the cross-basename recovery scan expecting a different
  result.** It was run this session over every on-disk artifact: 0 sources for
  the 25 unrecoverable rows.
- **Do not trust prose counts in committed reports.** Re-derive from the
  baseline/planner/CSV before acting.
- **Do not commit a `gates.yml` edit** expecting persistence (8 cycles reverted).
- **Do not weaken** `tests/test_gates_workflow.py`, the 100% coverage gate, or
  any frozen contract.
- **Do not mass-edit** runners/tests/gates to force the suite green.
- **Do not overwrite** artifacts to make a recorded hash match; the on-disk file
  is authoritative and feeds published values.

## One precise next task

**Read-only audit of the 528 orphaned artifacts** (`REPRODUCIBILITY_BASELINE["orphaned_files"] = 528`).

Steps:
1. Recompute the orphan set with the audit's own logic
   (`tests/test_reproducibility_audit.py::test_orphaned_artifacts_match_recorded_backlog`):
   files under `.experiments/artifacts/` (excluding `.meta.json`) whose resolved
   path is not referenced by any `experiments.jsonl` record.
2. Categorize by directory/family (e.g. never-appended experiment dirs, shared
   dirs such as `h29_lookahead_sweep/`, `h26_sharpe_scale/`, script copies) and
   count each category.
3. For each category, determine whether any orphan is (a) byte-identical to a
   referenced artifact, or (b) cited by a test/gate/published document. Record
   the evidence.
4. Append the table and a short conclusion to `REPRODUCIBILITY_AUDIT_REPORT.md`
   §3 (do not delete anything; deletion of committed data is out of scope).
5. Verify with `python -m pytest -q tests/test_reproducibility_audit.py`
   (expect 7 passed) and confirm the orphan count is unchanged at 528.

This is bounded, read-only, requires no data download or authorization, and
directly informs remediation item 4.