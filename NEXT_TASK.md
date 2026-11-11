# NEXT_TASK.md — H53 recipe verified in dep-enabled env; remaining failures are frozen-count drifts

## Status

The prior session's H53 recipe correction (removal of 3 stale H92 `benchmark_p_value`
artifact IDs from `BENCH_P_PUBLISHED_DEFAULT_ARTIFACTS`) is **verified in an
environment with project deps**. The 3 H92 `benchmark_p_value` re-derivation
mismatches are gone.

- `python -m ruff check tests/test_h53_published_metrics_disclosure.py` — All checks passed.
- `python -m ruff format --check tests/test_h53_published_metrics_disclosure.py` — 1 file already formatted.
- `PYTHONPATH=src python -m pytest -q tests/test_h53_published_metrics_disclosure.py` — **18 passed, 2 failed** (down from 16 passed / 4 failed). The 2 remaining failures are pinned-count drifts only.

## Verified this session

- H53 focused suite: 18 passed / 2 failed. Failures are exactly:
  - `test_h53_metrics_summary_count_pinned` — `58 == 54`
  - `test_h53_published_value_count_pinned` — `674 == 630`
- **Baseline evidence (important):** the original commit `82eb68a`'s version of this
  same test file, run against the current working tree, also yields **58 / 674**.
  So the pins `54` and `630` were already stale at commit time; this is pure
  frozen-number drift, not a code bug and not a regression introduced by the recipe fix.
- Full frozen-contract suite (`tests/test_h51_benchmark_container_invariance.py
  tests/test_h53_published_metrics_disclosure.py tests/test_h55_nested_metrics_disclosure.py
  tests/test_gate_vacuity_contract.py tests/test_engine_total_return_consistency.py
  tests/test_trade_log_cost_reconciliation.py`) — **348 passed, 9 failed, 12 skipped**.
  All 9 failures match the previously documented drift list; no new code bug found.
- `tests/test_h57_total_return_audit.py` — **66 passed** (was flagged as a possible
  code-bug candidate: "runners selecting on engine total-return column"). No bug.
- `tests/test_engine_total_return_consistency.py` — **16 passed**. No bug.

## The 9 remaining frozen-contract failures (all drift; all require authorization)

1. `test_h51_benchmark_container_invariance.py::test_every_published_information_ratio_is_disclosed` — 21 new IR-publishing experiments not in pinned `PUBLISHED_INFORMATION_RATIOS`.
2. `test_h53_published_metrics_disclosure.py::test_h53_metrics_summary_count_pinned` — 58 vs 54.
3. `test_h53_published_metrics_disclosure.py::test_h53_published_value_count_pinned` — 674 vs 630.
4. `test_h55_nested_metrics_disclosure.py::test_the_summaries_that_publish_a_nested_block_are_pinned` — nested-block set drifted.
5. `test_h55_nested_metrics_disclosure.py::test_the_published_leaf_count_is_pinned` — 1292 vs 1188.
6. `test_h55_nested_metrics_disclosure.py::test_the_rederivable_and_disclosed_counts_are_pinned` — 631 vs 627.
7. `test_h55_nested_metrics_disclosure.py::test_the_perturbation_gate_reads_only_the_ratio` — 40 vs 36.
8. `test_trade_log_cost_reconciliation.py::TestFrozenRecordScope::test_the_committed_trade_logs_are_exactly_the_pinned_record` — 3 contested `exp_2026-11-05` per-trade logs (`exp_2026-11-05T01-17-49-208916Z`, `01-24-02-934356Z`, `18-09-06-924039Z`) + H28 causal-recertification logs.
9. `test_trade_log_cost_reconciliation.py::TestFrozenRecordScope::test_every_committed_trade_log_records_the_aggregate_attribution` — the 3 contested logs no longer carry the pre-fix attribution.

## Failed approaches / do not blindly repeat

- Do not update pinned counts in H51/H53/H55 without authorization — frozen-number drifts.
- Do not add the 3 contested per-trade logs to `TRADE_LOG_RECORD` — breaks
  `test_the_three_pinned_sets_partition_the_record`; authorization required.
- Do not treat the 3 newer H92 artifacts as published-default p-values; artifacts show
  the real `0.005822770948177806` (runner uses `cmp.get("alpha_p_value", 1.0)`).
- Do not mass-edit runners/tests/gates to force the suite green.

## Next task

**One precise next task:** Await authorization to (a) resolve the 9 frozen-contract drifts via per-contract evidence review (exact failures listed above), or (b) resolve a free-data gap under explicit authorization (commodity carry roll/contango; PIT insider/earnings/options data) and select H182. Per `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 96) and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6, H1–H181 are all executed and rejected and the free-data family queue is exhausted; absent a data-gap resolution, conclude free-data family discovery is exhausted and shift to auditing/infrastructure. This session verified that one of the previously-reported failures (`test_benchmark_gate_contract.py::test_every_call_site_reads_only_keys_the_library_returns`) was a real code bug and fixed it (parameter rename in `run_nf_20261107_{03,04,07,08}_*.py`; `ruff`/contract test clean; full suite 3425 passed / 9 failed / 16 skipped, the 9 all documented drift). Constraints: `src/qtr` unchanged unless an evidenced defect requires it (then rerun pinned full gates); no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modified; no commit/push unless explicitly requested.

## Deferred (do not select without authorization)

- Update pinned counts in `test_h51_benchmark_container_invariance.py`,
  `test_h53_published_metrics_disclosure.py`, `test_h55_nested_metrics_disclosure.py` —
  frozen-number/count drifts.
- Resolve 3 contested per-trade logs in `test_trade_log_cost_reconciliation.py`
  (`exp_2026-11-05T01-17-49-208916Z`, `01-24-02-934356Z`, `18-09-06-924039Z`) —
  breaks partition; authorization required.
- Select H182 — commodity-carry data gap / no feasible free-data family per Cycle 96
  (discovery queue exhausted unless data gap resolved under authorization).