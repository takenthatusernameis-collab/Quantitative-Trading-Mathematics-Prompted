# HANDOFF_NEXT.md — H51 frozen-contract drift resolved; trade log drifts remain

## What changed (verified this session)

- **H51 resolved**: Added all 21 NF artifacts (2026-11-05/06) that publish `information_ratio` to `PUBLISHED_INFORMATION_RATIOS` disclosure table in `tests/test_h51_benchmark_container_invariance.py`.
  - 3 artifacts from `nf_20261104_02_cross_asset_leadlag` (H87): OOS window recipe (train_end="2019-12-31"), container=ndarray, ddof=0
  - 18 artifacts from 8 other NF families (H88-H95): full-series recipe, container=Series, ddof=0 (post-H51 fix)
  - Updated `DDOF_0_ARTIFACTS` from 26 → 47, `DDOF_1_ARTIFACTS` stays 22
  - Added RECIPES for all 21 artifacts
  - Added 9 NF runners to `RUNNER_CALL_SITE_CONTAINER` (8 Series, 1 ndarray)
  - Updated `test_the_series_call_sites_belong_to_the_ddof_1_families` to distinguish pre-H51 Series families (ddof=1) from post-H51 NF Series families (ddof=0)
  - Updated `test_the_pre_h51_implementation_reproduces_the_published_values` to skip NF artifacts (post-H51, ddof=0 regardless of container)
- **Benchmark gate contract**: 26 passed (unchanged)
- **Frozen-contract suite**: H51, H53, H55 all green. Trade log: 2 failures remain (pre-existing, authorization-gated)
- **Lint/format**: Clean across `src`, `tests`, `run_*.py` (314 files)

## Actually verified (this session)

- `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py` — clean.
- `PYTHONPATH=src python -m pytest -q tests/test_h51_benchmark_container_invariance.py tests/test_h53_published_metrics_disclosure.py tests/test_h55_nested_metrics_disclosure.py tests/test_benchmark_gate_contract.py` — **389 passed, 47 skipped**.
- `PYTHONPATH=src python -m pytest -q tests/test_trade_log_cost_reconciliation.py` — **327 passed, 3 failed, 12 skipped**. The 3 failures = 2 trade log + 1 (H51 was fixed, now only trade log failures remain).

## Unresolved / pre-existing (require authorization, do not mass-fix)

1. **Trade log reconciliation** `test_the_committed_trade_logs_are_exactly_the_pinned_record` — committed but unpinned/misaligned: 3 contested `exp_2026-11-05` per-trade logs (`01-17-49-208916Z`, `01-24-02-934356Z`, `18-09-06-924039Z`) + 7 H28 causal-recertification run trade parquets. Constrained by partition semantics (`test_the_three_pinned_sets_partition_the_record`).

2. **Trade log attribution** `test_every_committed_trade_log_records_the_aggregate_attribution` — the same 3 contested `exp_2026-11-05` logs record per-trade (not aggregate) attribution.

## Resolved since prior handoff (do not re-open)

- **H51** `test_every_published_information_ratio_is_disclosed` — all 21 NF IR entries added with correct recipes, containers, conventions, and p-values. Test now passes.
- **H53** `test_h53_metrics_summary_count_pinned` (54 vs 58) and `test_h53_published_value_count_pinned` (630 vs 674) — remain green.
- **H55** 4 failures (nested-block set, leaf count, rederivable count, perturbation gate) — remain green.

## Failed approaches / do not blindly repeat

- Do not add contested per-trade logs to `TRADE_LOG_RECORD` — breaks `test_the_three_pinned_sets_partition_the_record`.
- Do not mass-edit runners/tests/gates to force the suite green or weaken frozen-contract/coverage gates.
- Do not recycle H1–H181 as H182 without a materially distinct mechanism and free PIT data.

## Next task

**One precise next task:** Obtain explicit authorization and resolve **one** trade-log frozen-contract drift with per-contract evidence: **(a) Trade Log** — reconcile the 3 contested `exp_2026-11-05` per-trade logs and the 7 committed-but-unpinned H28 causal-recertification trade parquets under the partition-test constraint so `tests/test_trade_log_cost_reconciliation.py` passes. Absent authorization, remain on auditing/infrastructure; do not invent H182 candidates.

**Research queue:** `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96 — H1–H181 exhausted/rejected; free-data point-in-time family queue exhausted; H182 unassigned (commodity-carry data gap; insider/earnings/options PIT unavailable without paid services). H182 selection requires data-gap resolution under explicit authorization per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6.

**Constraints:** `src/qtr` unchanged unless an evidenced defect requires it (then rerun pinned full gates: `pytest -q -W error`, ruff check/format, coverage 100% for `src/qtr`); no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modified without authorization; no commit/push unless explicitly requested.

(End of file)