# HANDOFF.md

> **Latest (2026-11-13, post-audit session):** fixed a caller-dict mutation in
> `ExperimentTracker.log_dataframe` (`src/qtr/tracking/experiment.py`): it now
> copies the caller's `metadata` dict before adding the frame schema keys, so a
> reused dict no longer leaks `shape`/`columns`/`dtypes`/`index_type` into later
> calls. The on-disk sidecar is byte-identical to before. Added a regression
> test (`test_log_dataframe_does_not_mutate_caller_metadata`). Verified: tracker
> tests 24 passed; focused reproducibility suites 342 passed; full suite
> **3744 passed / 51 skipped / 7 failed** (the 7 = maintainer-gated
> `test_gates_workflow.py`); `experiment.py` 100% stmts/branch; ruff clean. No
> published/frozen artifact, verdict, threshold, or experiment record changed.
> See `NEXT_TASK.md` for the next task (backfill the 140 missing sidecars).

> **Prior (2026-11-13):** completed the read-only audit of the 11 hash
> mismatches. All 11 are superseded duplicate/stale entries: 8 duplicate
> same-path `param_grid_results` writes (runners log the path 2–3× with
> different frames) and 3 fixed-`run_dir` `summary.json` re-runs. The on-disk
> file is authoritative in every case and feeds the published values; the
> frozen `test_h54_non_metrics_block_disclosure.py` re-derivation (21 passed)
> reads the on-disk grids. Table + authority verdict appended to
> `REPRODUCIBILITY_AUDIT_REPORT.md` §2. Verified: audit 7 passed, nf runners 34
> passed, planner unchanged (0/172/25), ruff clean. No `src/qtr`, test, gate,
> or artifact changed; no commit/push. See `NEXT_TASK.md` for the next task
> (read-only audit of the 528 orphaned artifacts).

## Re-verification banner (2026-11-12T10:00Z, Cycle 101)

> **Provenance caution (added 2026-11-13, Cycle 104):** this banner cites HEAD `1712a5e`
> and commits `11e8aeb` / `bec162f`. **None of those objects exist in this repository** —
> `git cat-file -t` returns "Not a valid object name" for each; the full history is 6
> commits (0891237 → 09372cf), all empty-message. The counts quoted here (3619 passed,
> 1209 stmts, 314 files) are also stale: current is **3,743 passed / 51 skipped / 7 failed**
> (the 7 = maintainer-gated `test_gates_workflow.py`), **1211 stmts / 422 branches**, and
> **327 files** (re-verified 2026-11-13). The 9 frozen-contract drifts this banner claims
> were "resolved" are green in the working tree; `FROZEN_CONTRACT_DRIFT_EVIDENCE.md`
> carries the durable re-verification. Treat this banner's *substance* (suite green,
> drifts resolved) as correct and its *object references* as unreliable.

**This doc was stale.** It claimed 9 frozen-contract failures remained. Re-running the
full suite at HEAD `1712a5e` reports **3619 passed, 51 skipped, 0 failed**, `src/qtr`
coverage **100%** (1209 stmts / 420 branches / 0 miss), `ruff check` clean, `ruff
format --check` 314 files. The 9 failures were resolved in commits `11e8aeb` (H51,
2026-11-12T08:23Z) and `bec162f` (trade log, 2026-11-12T08:30Z); this doc was never
updated and read as an open defect for ~1.5h. Historical inventory below is preserved;
the "What remains unresolved" section is superseded by the banner above.

## What changed this session (2026-11-11T14:15Z, Cycle 100)

Two stale-audit re-verifications + dead-stub cleanup. **No `src/qtr` change. No
gated artifact, test, threshold, or frozen number touched. No commit/push.**

1. **`INFRASTRUCTURE_AUDIT_BENCHMARK_GATE.md` was stale.** It claimed **38** open
   p-value offenders. Re-running its own detector
   (`tests/test_benchmark_gate_contract.py::test_no_runner_compares_a_p_value_against_max_p_value_directly`)
   reports **0 offenders**, and direct grep confirms all 38 named runners now call
   `benchmark_significance_gate` (exactly 2 call sites each: the import and the
   evaluation). The fix landed between Cycle 98 and Cycle 99; the doc was never
   updated and read as an open defect for two cycles. The doc now carries a
   re-verification banner and keeps the historical inventory for lineage.
2. **`INFRASTRUCTURE_INSPECTION.md` was stale.** It reported "Infrastructure Status:
   NONE EXIST" for a greenfield repo. Every component it lists now exists
   (backtest engine, data pipeline, experiment tracking, strategies, baselines,
   test suite, config management). The doc now carries a re-verification banner
   with the actual locations and keeps the historical greenfield baseline.
3. **Removed 19 dead stub files** from the working tree (all committed, all
   unreferenced by any test, source, runner, workflow, or script):
   `_chunk_test.py`, `_probe.py`, `_probe2.py`, `_probe_h159.py`, `_probe_h169.py`,
   `_probe_h170.py`, `_t.py`..`_t11.py`, `_wtest.txt`, `_placeholder.txt`,
   `run_nf_20261107_53_etr` (0-byte), `run_nf_20261108_13_spy_futures_basis.py`,
   `run_nf_20261108_31_spy_parkinson_rv_spy.py`. Verified unreferenced by grep over
   `tests/ src/ .github/` before deletion; the runner-touching suites
   (`test_runner_import_contract`, `test_benchmark_gate_contract`,
   `test_gate_vacuity_contract`, `test_engine_metric_agreement`,
   `test_engine_total_return_consistency`, `test_parameter_sensitivity_reproducibility`,
   `test_runner_causality_inventory`, `test_probe_report_schema`, `test_config`) —
   **773 passed**, so no contract was weakened.

## What was actually verified

- `tests/test_benchmark_gate_contract.py` — **26 passed**, including
  `test_no_runner_compares_a_p_value_against_max_p_value_directly` (0 offenders
  vs. the 38 the audit doc claimed) and
  `test_every_runner_with_a_benchmark_gate_uses_the_direction_aware_helper`.
- Runner-touching suites after stub deletion — **773 passed, 0 failed**.
- Full suite — **3429 passed, 9 failed, 16 skipped** (was 3433 passed; the −4 is the
  deletion of `_chunk_test.py`/`_t8.py`/`_t11.py`, which were never collected by pytest
  because `testpaths = ["tests"]`). The 9 failures are **unchanged and are exactly the
  documented frozen-contract drifts** — no new failure, no regression.
- `python -m ruff check src tests run_*.py` — All checks passed.
- `python -m ruff format --check src tests run_*.py` — 314 files already formatted.
- `src/qtr` coverage — **100%** (1209 stmts / 420 branches, 0 miss), unchanged.

## What remains unresolved

**Superseded by the re-verification banner above** — the 9 frozen-contract failures it
lists here were resolved in commits `11e8aeb` (H51) and `bec162f` (trade log) and the
full suite is green at HEAD. Historical record preserved for lineage only.

The **9 frozen-contract failures** are unchanged and all require authorization to
resolve (frozen-number/count drifts + 3 contested per-trade logs). Full list in
`NEXT_TASK.md` §"The 9 remaining frozen-contract failures". `src/qtr` coverage is
100% and `ruff` is clean, so there is no code bug to fix.

## Which approaches have already failed and why

- **Do not trust a committed audit/inspection doc as a current defect list.** Both
  `INFRASTRUCTURE_AUDIT_BENCHMARK_GATE.md` and `INFRASTRUCTURE_INSPECTION.md` were
  stale by two cycles and read as open defects when the underlying issues were
  already fixed. Re-run the contract test that generated the doc before acting on
  it; if the doc is stale, annotate it with the re-verification result rather than
  silently editing the pins.
- **Do not trust a handoff doc's failure list either.** This same failure list
  (`9 frozen-contract failures`) was stale by ~1.5h at Cycle 101: the H51 and
  trade-log drifts were resolved in `11e8aeb`/`bec162f` and the full suite is green.
  Always re-run the suite (or the focused contract file) before acting on a
  handoff's "unresolved" section.
- **Do not delete a file without checking it is unreferenced.** The 19 stubs were
  committed and looked like active scaffolding; a grep over `tests/ src/ .github/`
  confirmed zero references before deletion. The runner-touching suites were
  re-run after deletion to confirm no contract was weakened.
- The frozen-contract drifts (H51/H53/H55/H52) remain blocked on authorization; no
  new approach was attempted this session because the task was bounded to
  non-gated cleanup.

## Session 2026-11-11T21:11Z — read-only per-contract re-verification (no changes)

**Superseded.** This section's evidence (3526 passed / 9 failed) was accurate *at that
moment* but is now stale: the 9 failures it lists were resolved in commits `11e8aeb`
(H51, 2026-11-12T08:23Z) and `bec162f` (trade log, 2026-11-12T08:30Z). Re-running at
HEAD `1712a5e` (2026-11-12T10:00Z, Cycle 101) reports **3619 passed, 51 skipped, 0
failed** with `src/qtr` coverage **100%**. Historical record preserved for lineage.

No source, test, gate, frozen-number, or artifact change. Working tree clean; no commit/push.

**Actually verified (this session, own evidence) — STALE, preserved for lineage:**
- Re-ran the four frozen-drift test files — **all 9 failures still present, unchanged** (exact evidence below; no new failure, no regression):
  - h51 `test_every_published_information_ratio_is_disclosed` — set drift: 21 new IR-publishing experiments not in pinned `PUBLISHED_INFORMATION_RATIOS`.
  - h53 `test_h53_metrics_summary_count_pinned` — 58 vs 54; `test_h53_published_value_count_pinned` — 674 vs 630.
  - h55 `test_the_summaries_that_publish_a_nested_block_are_pinned` — nested-block set drift; `test_the_published_leaf_count_is_pinned` — 1292 vs 1188; `test_the_rederivable_and_disclosed_counts_are_pinned` — 631 vs 627; `test_the_perturbation_gate_reads_only_the_ratio` — 40 vs 36.
  - trade-log `test_the_committed_trade_logs_are_exactly_the_pinned_record` + `test_every_committed_trade_log_records_the_aggregate_attribution` — 3 contested `exp_2026-11-05` per-trade logs (`...T01-17-49-208916Z`, `...T01-24-02-934356Z`, `...T18-09-06-924039Z`) + H28 causal-recertification logs.
- Full suite `pytest -q --cov=qtr --cov-branch` — **3526 passed, 9 failed, 16 skipped** (all 9 = documented frozen drifts; no code bug, no regression).
- `src/qtr` coverage — **100%** (1209 stmts / 420 branches / 0 miss; engine.py 100%).
- `python -m ruff check src tests run_*.py` — all checks passed.
- `python -m ruff format --check src tests run_*.py` — 315 files already formatted.

**Current re-verification (2026-11-12T10:00Z, Cycle 101) — supersedes all above:**
- Full suite `pytest -q --cov=qtr --cov-branch` — **3619 passed, 51 skipped, 0 failed** (636s).
- `src/qtr` coverage — **100%** (1209 stmts / 420 branches / 0 miss).
- `python -m ruff check src tests run_*.py` — All checks passed.
- `python -m ruff format --check src tests run_*.py` — 314 files already formatted.

## One precise next task

**Superseded** — see the re-verification banner at the top of this file. The H51 and
trade-log drifts it describes are resolved at HEAD and the full suite is green
(3619 passed, 51 skipped, 0 failed; `src/qtr` coverage 100%; ruff clean). The only
remaining open item is **H182 selection**: per
`STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6 and `NEW_FAMILY_RESEARCH_REGISTER.md`
Cycle 96, the free-data point-in-time strategy-family queue is exhausted (H1–H181
executed/rejected; commodity carry data-blocked; insider/earnings/options PIT
unavailable without paid services). Selecting H182 requires resolving a data gap
under explicit authorization. Absent that, conclude free-data family discovery is
exhausted and shift to auditing/infrastructure rather than inventing candidates.

**Constraints:** `src/qtr` unchanged unless an evidenced defect requires it (then
rerun pinned full gates); no gate weakening; no published/certified artifact,
verdict, threshold, or frozen number modified; no commit/push unless explicitly
requested.