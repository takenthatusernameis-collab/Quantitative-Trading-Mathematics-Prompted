# REPRODUCIBILITY AUDIT REPORT

**Session:** 2026-11-12
**Re-verified:** 2026-11-13 — `missing_files` is **197** (172 H28 contract-blocked +
25 unrecoverable), the planner reports 0 recoverable / 172 excluded / 25
unrecoverable, and `missing_meta_files` is **140**. The earlier prose that said
"25 remaining" / "321 restored" was wrong and is corrected in §1 and
§Recommended Remediation below.
**Task:** Verify all experiment artifacts can be re-derived from tracked metadata (STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §6 fallback path)

---

## Summary

`tests/test_reproducibility_audit.py` audits the experiment tracking system
against `.experiments/experiments.jsonl` (173 experiments).

The committed corpus predates the current tracking contract, so it carries a
known historical backlog. The audit now records that backlog in an explicit
baseline and fails if the backlog changes in either direction. This makes the
gate green at the current state while preventing silent regression or a stale
baseline.

**Audit Status:** **GREEN WITH RECORDED BACKLOG** — 3 invariant checks pass; 4
backlog checks are locked to the counts below.

**2026-11-12 remediation:** 149 non-H28 hash-exact artifacts were restored into
place, so `missing_files` fell 346 → 197. The other 172 hash-exact rows are H28
causal-recertification artifacts: the committed `experiments.jsonl` records their
old depth-one paths, but H28 runs must live under
`.experiments/artifacts/h28_causal_recertification/runs/`, so copying them to
depth-one would satisfy the audit while breaking the H28 depth-one invariant
(`tests/test_h28_causal_recertification.py`). They are reported as
**contract-blocked** in `REPRODUCIBILITY_RESTORATION_PLAN.{md,csv}` and are not
restored. Sidecar count is unchanged at 140. The baselines below reflect this
state; all deltas are additive and verified.

---

## Findings

| Check | Status | Count | Details |
|-------|--------|-------|---------|
| Experiments log exists & nonempty | ✅ PASS | 173 experiments | All records parseable |
| Artifact files exist on disk | ⚠ BASELINE | 197 missing | Referenced parquet/JSON files not found (was 346; 149 restored) |
| Artifact hashes match recorded values | ⚠ BASELINE | 11 mismatches | SHA-256 prefix differs from artifact name |
| No orphaned files in artifacts dir | ⚠ BASELINE | 528 orphaned | Files on disk not referenced by any experiment |
| Experiment metadata completeness | ✅ PASS | 173/173 complete | All required fields present |
| Git commit consistency | ✅ PASS | 173/173 valid | No "unknown" commits |
| Artifact `.meta.json` sidecars exist | ⚠ BASELINE | 140 missing | Sidecars absent for artifacts logged without metadata |

---

## How the Gate Works

`REPRODUCIBILITY_BASELINE` in `tests/test_reproducibility_audit.py` records the
four backlog counts above. Each backlog test asserts:

```
current_count == REPRODUCIBILITY_BASELINE[check]
```

- If a count **increases**, the test fails: a new reproducibility regression.
- If a count **decreases**, the test fails: the baseline is stale and must be
  lowered deliberately, together with this report.
- If a count is unchanged, the test passes.

This is the same pattern as
`tests/test_experiment_artifact_schema.py::test_incomplete_runs_match_audit_inventory`.
The desired end state is a zero backlog; the baseline is the bridge from the
historical corpus to that end state.

---

## Root Cause Analysis

### 1. Missing Artifact Files (197 remaining, was 346)

Experiments reference artifact paths under `.experiments/artifacts/<exp_id>/`
but those files were never created, were cleaned up, or were written under a
different experiment id. For example, `exp_2026-10-13T21-46-52-446478Z`
(`h17_vrp`) is missing 12 referenced artifacts, and
`exp_2026-10-11T18-36-51-113738Z` is missing only its `summary.json` after the
2026-11-12 restore (it is no longer empty).

Recovery audit: of the 346 originally-missing paths, 321 had a same-basename
candidate whose recorded 16-char SHA-256 prefix matched. Of those 321,
**149 non-H28 rows were applied (copied) on 2026-11-12**, reducing
`missing_files` from 346 to 197. The remaining 197 rows are **172 H28
contract-blocked** (their hash-exact sources live under
`.experiments/artifacts/h28_causal_recertification/runs/`; restoring depth-one
copies would break `tests/test_h28_causal_recertification.py`) plus **25 with no
hash-matching source** that need a re-run. The planner reports 0 recoverable /
172 excluded / 25 unrecoverable (`REPRODUCIBILITY_RESTORATION_PLAN.{md,csv}`).

**Most affected experiments (before apply):** `h11_robustness_certification`,
`h17_vrp`, early TS/CS momentum runs, and
`exp_2026-10-14T19-46-14-356479Z` / `exp_2026-10-14T20-00-08-312708Z`
(22 missing each).

### 2. Hash Mismatches (11)

The artifact name embeds a 16-char SHA-256 prefix, but the file at the
referenced path has different content. The 11 rows fall into two distinct
mechanisms, re-derived 2026-11-13 with the audit's own hash logic.

**8 × `param_grid_results` — duplicate same-path log entries within one run.**
The momentum runners call `log_dataframe("param_grid_results", ...)` more than
once on the same output path, with different DataFrame contents (e.g.
`run_ts_momentum_experiment.py:440` pre-correction, `:473` post-correction,
`:708` pre-correction again; `run_cs_momentum_experiment.py:294` then `:516`;
`run_regime_gated_momentum_experiment.py:573` then `:613`). Only one write
survives on disk, so the superseded recorded name can never match the file. The
on-disk file matches the *other* recorded name in every case.

**3 × `summary.json` under `.experiments/nf_runs/` — fixed `run_dir` re-run.**
These runners derive `run_dir` from `EXPERIMENT_NAME` alone
(`run_nf_20261105_14_credit_regime.py:281`, `..._16_usd_macro.py:281`,
`..._19_pead.py:292`), so re-running an experiment overwrites `summary.json`
while the earlier experiment record keeps its original hash.

| Experiment id | Artifact (recorded name) | Recorded | On disk | Likely cause | Test/gate pins it? | On disk authoritative? |
|---|---|---|---|---|---|---|
| exp_2026-10-10T20-56-30-507309Z | param_grid_results_3c3ca96bf45b5f28 | 3c3ca96bf45b5f28 | 2cfbb88200656d0d | duplicate same-path write (ts_momentum_20etf_v1) | No (stale duplicate); published counts re-derived from disk | Yes |
| exp_2026-10-10T20-57-26-136503Z | param_grid_results_3c3ca96bf45b5f28 | 3c3ca96bf45b5f28 | 2cfbb88200656d0d | duplicate same-path write (ts_momentum_20etf_v1) | No (stale duplicate); published counts re-derived from disk | Yes |
| exp_2026-10-10T20-59-28-306148Z | param_grid_results_3c5c66cd85442477 | 3c5c66cd85442477 | c7a1cedb8a4fc5b1 | duplicate same-path write (cs_momentum_10etf_v1) | No (stale duplicate); published counts re-derived from disk | Yes |
| exp_2026-10-10T21-08-54-188263Z | param_grid_results_3c3ca96bf45b5f28 | 3c3ca96bf45b5f28 | 2cfbb88200656d0d | duplicate same-path write (ts_momentum_20etf_v1) | No (stale duplicate); published counts re-derived from disk | Yes |
| exp_2026-10-10T21-09-06-830199Z | param_grid_results_3c5c66cd85442477 | 3c5c66cd85442477 | c7a1cedb8a4fc5b1 | duplicate same-path write (cs_momentum_10etf_v1) | No (stale duplicate); published counts re-derived from disk | Yes |
| exp_2026-10-10T21-27-13-928282Z | param_grid_results_5aa48f8683d54d37 | 5aa48f8683d54d37 | b7dddfb0dc0c524d | duplicate same-path write (regime_gated_momentum_20etf_v1) | No (stale duplicate); published counts re-derived from disk | Yes |
| exp_2026-10-10T21-28-20-920399Z | param_grid_results_5aa48f8683d54d37 | 5aa48f8683d54d37 | b7dddfb0dc0c524d | duplicate same-path write (regime_gated_momentum_20etf_v1) | No (stale duplicate); published counts re-derived from disk | Yes |
| exp_2026-10-14T08-26-18-385545Z | param_grid_results_3c3ca96bf45b5f28 | 3c3ca96bf45b5f28 | 2cfbb88200656d0d | duplicate same-path write (ts_momentum_20etf_v1) | No (stale duplicate); published counts re-derived from disk | Yes |
| exp_2026-11-05T18-20-38-363385Z | summary_b8cf0dae88579c7a | b8cf0dae88579c7a | 63139e710dc45c09 | fixed `run_dir` re-run overwrote summary.json (later run exp_2026-11-10T17-24-06-550812Z) | No; later record is the on-disk hash | Yes (later run) |
| exp_2026-11-05T19-06-45-864432Z | summary_361a5942ebe194a6 | 361a5942ebe194a6 | 7ec56dd201670d5a | fixed `run_dir` re-run overwrote summary.json (later run exp_2026-11-05T19-09-07-377344Z) | No; register cites later run | Yes (later run) |
| exp_2026-11-06T01-28-49-517869Z | summary_4eff6682192c3e69 | 4eff6682192c3e69 | da9da6784d5a7d8d | fixed `run_dir` re-run overwrote summary.json (later run exp_2026-11-06T01-30-29-259047Z) | No; register cites later run | Yes (later run) |

**No mismatch feeds a published/frozen number.** The frozen published
`param_grid_summary` values (`n_combos`, `benjamini_hochberg_significant`) are
re-derived from the *on-disk* parquet by
`tests/test_h54_non_metrics_block_disclosure.py::test_the_re_derivable_families_re_derive`;
an independent recount confirms all 8 on-disk grids match their summaries
(18/18, 54/54, 108/108 rows and BH = 0 in each case). The three `nf_runs`
summaries are re-run products; the later record carries the on-disk hash and
`HYPOTHESIS_SPEC.md` cites the later execution ids for `_16_usd_macro` and
`_19_pead`. **The on-disk file is authoritative in all 11 rows; the flagged
recorded name is a superseded duplicate/stale entry.** Remediation should correct
`experiments.jsonl` (drop superseded duplicate keys) or the runner (log once per
final path), not overwrite the artifacts. This is authorization-gated because it
edits the committed record; no baseline change is needed.

**Verified 2026-11-13:** `tests/test_reproducibility_audit.py` — 7 passed;
`tests/test_h54_non_metrics_block_disclosure.py` — 21 passed; the three
`tests/test_nf_20261105_1{4,6,9}_*.py` — 34 passed; read-only planner unchanged
(0 recoverable / 172 excluded / 25 unrecoverable).

### 3. Orphaned Artifact Files (528)

Files exist under `.experiments/artifacts/` but are not referenced by any
record in `experiments.jsonl`. Includes:

- Experiment directories whose records were never appended (e.g.
  `exp_2026-10-14T08-20-16-720432Z/`).
- Shared directories (`h29_lookahead_sweep/`, `h26_sharpe_scale/`).
- Script copies (`run_h9_intraday_tsmom_experiment.py`).

These are not deleted: deleting committed artifacts would destroy user data.
They are catalogued here and locked by the baseline.

### 4. Missing `.meta.json` Sidecars (140)

`ExperimentTracker.log_artifact()` writes a sidecar only when a non-empty
`metadata` dict is passed:

```python
if metadata:
    meta_path = self.log_dir / f"{artifact_name}.meta.json"
```

`log_dataframe()` always passes a metadata dict and therefore always writes a
sidecar. The sidecar-less artifacts were logged through
`log_artifact(..., metadata=None)` — mostly `summary.json`. None of them had a
sidecar in the source corpus either. The earlier count of 1,059 was an artifact
of the test checking the wrong path
(`.experiments/artifacts/<exp>/<name>.meta.json`) instead of the tracker's actual
contract (`.experiments/<name>.meta.json`). That path bug is fixed in this change.

**Re-verified 2026-11-13:** the 8-restore delta (140 → 148) recorded in the
prior session's prose never materialized. Independent recount against the
committed corpus yields **140** missing sidecars (1,068 present), matching
`REPRODUCIBILITY_BASELINE["missing_meta_files"]` exactly. The prose figure is
stale and is corrected here; the baseline and the gate are unchanged.

---

## Implications

| Claim | Supported? | Evidence |
|-------|------------|----------|
| "All 173 experiments are fully reproducible from tracked metadata" | ❌ No | 197 missing files (172 H28 contract-blocked + 25 unrecoverable), 11 hash mismatches |
| "Artifact hashes in experiment records match on-disk content" | ❌ No | 11 mismatches prove divergence |
| "Every file in `.experiments/artifacts/` is accounted for" | ❌ No | 528 orphaned files |
| "Every artifact has per-artifact metadata" | ❌ No | 140 missing sidecars |
| "No *new* reproducibility drift is introduced" | ✅ Yes | Baseline ratchet fails on any count change |

**However:** Experiment-level metadata (git commit, dependencies, seeds, config)
is **complete and valid** for all 173 experiments. The code version and
configuration for every run are recoverable.

---

## Recommended Remediation

Ordered by value and risk:

1. **✅ Restore the 149 non-H28 hash-exact missing artifacts** — done 2026-11-12.
   Each byte-identical same-basename file was copied to the referenced path after
   re-verifying its SHA-256 prefix; `missing_files` fell 346 → 197. The remaining
   197 are 172 H28 contract-blocked rows plus 25 with no hash-exact source; the
   planner now reports 0 recoverable / 172 excluded / 25 unrecoverable and refuses
   to overwrite existing targets.

2. **Re-run the 25 artifacts with no hash-matching source** — recreate them at
   the referenced paths and lower the baseline to 0.

3. **✅ Audit the 11 hash mismatches** — done 2026-11-13 (§2). All 11 are
   superseded duplicate/stale entries: 8 are duplicate same-path
   `param_grid_results` log entries and 3 are fixed-`run_dir` re-runs. The
   on-disk file is authoritative and feeds the published values (the frozen h54
   re-derivation reads it). The only remediation is to drop the superseded keys
   from `experiments.jsonl` (or log once per final path); it is
   authorization-gated and must not overwrite artifacts. A cross-basename
   hash-exact scan of all 2,155 on-disk artifacts found **0** sources for the 25
   unrecoverable rows, so the missing backlog cannot be reduced this way.

4. **Catalog or archive the 528 orphaned files** — add references if they are
   valid artifacts, or move them to an explicit archive directory. Do not
   delete committed data.

5. **Backfill the 140 missing sidecars** — derive shape/columns/dtypes for
   parquet and top-level keys for JSON, or change `log_artifact` to always write
   a sidecar (requires the full `src/qtr` gates: `pytest -q -W error`, ruff,
   100% branch coverage).

6. **Keep the baseline ratchet in CI** — it prevents new drift while remediation
   proceeds.

---

## Verification Evidence

| Check | Command | Result |
|-------|---------|--------|
| Reproducibility audit | `pytest tests/test_reproducibility_audit.py -q` | ✅ 7 passed |
| Hash-mismatch re-derivation | `pytest tests/test_h54_non_metrics_block_disclosure.py -q` | ✅ 21 passed (8 on-disk grids match published `param_grid_summary`) |
| NF runner tests | `pytest tests/test_nf_20261105_1{4,6,9}_*.py -q` | ✅ 34 passed |
| Core unit tests | `pytest tests/test_backtest_engine.py tests/test_config.py tests/test_cost_model.py tests/test_statistics.py tests/test_data_fetcher.py -q` | ✅ 359 passed |
| Edge stress tests | `pytest tests/test_engine_edge_stress.py -q` | ✅ 12 passed |
| Performance regression gate | `pytest tests/test_performance_regression_gate.py -q` | ✅ 1 passed |
| Full pinned suite | `pytest -q -W error --cov=qtr --cov-branch` | ⚠ 3,743 passed, 51 skipped, 7 failed (all 7 = maintainer-gated `tests/test_gates_workflow.py`; re-verified 2026-11-13) |
| Lint (ruff) | `ruff check src tests run_*.py` | ✅ Clean |
| Format (ruff) | `ruff format --check src tests run_*.py` | ✅ Clean |

---

## Artifacts

- `tests/test_reproducibility_audit.py` — re-runnable audit + baseline ratchet
- This report: `REPRODUCIBILITY_AUDIT_REPORT.md`

---

## Next Steps

The audit is now a green, non-regressing gate. The remaining work is data
remediation, in the order above. Per
STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §6, this completes the
"Reproducibility audit" fallback item. All four fallback items are executed:

1. ✅ Performance profiling of backtest engine
2. ✅ Experiment lineage documentation
3. ✅ CI/CD hardening (performance regression gate)
4. ✅ Reproducibility audit (baseline ratchet in place, gaps documented)

**Strategy family discovery remains exhausted at H181 pending data authorization.**
