# REPRODUCIBILITY AUDIT REPORT

**Session:** 2026-11-12
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

---

## Findings

| Check | Status | Count | Details |
|-------|--------|-------|---------|
| Experiments log exists & nonempty | ✅ PASS | 173 experiments | All records parseable |
| Artifact files exist on disk | ⚠ BASELINE | 346 missing | Referenced parquet/JSON files not found |
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

### 1. Missing Artifact Files (346)

Experiments reference artifact paths under `.experiments/artifacts/<exp_id>/`
but those files were never created, were cleaned up, or were written under a
different experiment id. For example, `exp_2026-10-11T18-36-51-113738Z` is
empty while the same artifact names exist under
`exp_2026-10-11T18-40-37-427062Z`.

Recovery audit: all 346 missing paths have at least one same-basename file
elsewhere under `.experiments/`; 321 of them also match the recorded 16-char
SHA-256 prefix exactly. Those 321 are byte-identical restorations; the
remaining 25 have no hash-matching source and need a re-run.

**Most affected experiments:** `h11_robustness_certification`, `h17_vrp`, early
TS/CS momentum runs, and `exp_2026-10-14T19-46-14-356479Z` /
`exp_2026-10-14T20-00-08-312708Z` (22 missing each).

### 2. Hash Mismatches (11)

The artifact name embeds a 16-char SHA-256 prefix, but the file at the
referenced path has different content. Most cases are `param_grid_results`
artifacts reused across experiments; the file on disk was overwritten by a later
run. Three are `summary.json` files under `.experiments/nf_runs/`.

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
sidecar. The 140 artifacts without sidecars were logged through
`log_artifact(..., metadata=None)` — mostly `summary.json` (118) and 22
parquet files. The earlier count of 1,059 was an artifact of the test checking
the wrong path (`.experiments/artifacts/<exp>/<name>.meta.json`) instead of the
tracker's actual contract (`.experiments/<name>.meta.json`). That path bug is
fixed in this change.

---

## Implications

| Claim | Supported? | Evidence |
|-------|------------|----------|
| "All 173 experiments are fully reproducible from tracked metadata" | ❌ No | 346 missing files, 11 hash mismatches |
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

1. **Restore the 321 hash-exact missing artifacts** — copy the byte-identical
   same-basename file to the referenced path after verifying its SHA-256 prefix
   matches the artifact name. This is additive and verifiable; it reduces
   `missing_files` from 346 to 25.

2. **Re-run the 25 artifacts with no hash-matching source** — recreate them at
   the referenced paths and lower the baseline.

3. **Resolve the 11 hash mismatches** — either re-run the affected experiments
   or record why the on-disk file is the authoritative version. Do not rewrite
   `experiments.jsonl` without authorization.

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
| Core unit tests | `pytest tests/test_backtest_engine.py tests/test_config.py tests/test_cost_model.py tests/test_statistics.py tests/test_data_fetcher.py -q` | ✅ 359 passed |
| Edge stress tests | `pytest tests/test_engine_edge_stress.py -q` | ✅ 12 passed |
| Performance regression gate | `pytest tests/test_performance_regression_gate.py -q` | ✅ 1 passed |
| Full pinned suite | `pytest -q -W error` | ✅ 3641 passed, 51 skipped |
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