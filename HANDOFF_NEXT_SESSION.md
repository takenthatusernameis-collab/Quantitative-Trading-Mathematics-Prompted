# HANDOFF — Next Session: Frozen-contract investigation complete; no code bugs found

## What was investigated

Investigated all 10 remaining frozen-contract failures from the prior handoff to determine whether any are code bugs (like the `alpha_p_value`/`p_value` KeyError fixed in 7 NF runners) rather than frozen-number drifts or stale test assertions.

## Findings: NO CODE BUGS FOUND

All 10 failures are either **frozen-number/pin drifts** (new experiments committed, pinned counts not updated) or **stale test-scope assertions** (test logic too broad or based on wrong assumptions). No `src/qtr`, runner, gate, or threshold code changes are needed.

---

## Failure breakdown

### 1. `test_h51_benchmark_container_invariance.py::test_every_published_information_ratio_is_disclosed`
- **Type**: Frozen-number drift
- **Detail**: 21 new NF experiments (2026-11-05/06) publish `information_ratio` but the pinned disclosure table `PUBLISHED_INFORMATION_RATIOS` only contains 48 older artifacts.
- **Action**: Update the pinned set with the 21 new experiment IDs (requires authorization).

### 2. `test_h53_published_metrics_disclosure.py::test_h53_metrics_summary_count_pinned` (58 vs 54)
### 3. `test_h53_published_metrics_disclosure.py::test_h53_published_value_count_pinned` (674 vs 630)
- **Type**: Frozen-number drift
- **Detail**: 4 new NF experiment summaries added; pinned counts not updated.

### 4. `test_h53_published_metrics_disclosure.py::test_every_published_value_re_derives` (3 failures on `benchmark_p_value`)
- **Type**: **Test recipe error** (not a code bug)
- **Detail**: The test recipe for `nf_20261105_10_equity_bond_relmom` (H92) has `bench_p_published_default=True`, which forces the re-derived `benchmark_p_value` to `1.0`. But the runner **correctly** uses `cmp.get("alpha_p_value", 1.0)` (verified in source), so the published value is `0.005822770948177806`. The test recipe assumption is wrong for this runner (and likely for other NF runners with the same flag).
- **Evidence**: All 7 NF runners fixed in the prior session were `run_nf_20261107_*.py`; the H92 runner is `run_nf_20261105_10_equity_bond_relmom.py` and never had the bug.
- **Action**: Fix the test recipe (remove `bench_p_published_default=True` for runners that correctly use `alpha_p_value`); update pinned counts.

### 5. `test_h53_published_metrics_disclosure.py::test_the_nine_undeterminable_values_are_exactly_the_regime_block`
- **Type**: Cascading from #4
- **Detail**: The 3 H92 experiments now appear as extra mismatches because the test recipe forces re-derived `benchmark_p_value = 1.0` while published is `0.0058`.

### 6. `test_h55_nested_metrics_disclosure.py::test_the_summaries_that_publish_a_nested_block_are_pinned` (ablations 48 vs 44, perturbation 28 vs 24)
### 7. `test_h55_published_metrics_disclosure.py::test_the_published_leaf_count_is_pinned` (1292 vs 1188)
### 8. `test_h55_published_metrics_disclosure.py::test_the_rederivable_and_disclosed_counts_are_pinned` (631 vs 627)
### 9. `test_h55_published_metrics_disclosure.py::test_the_perturbation_gate_reads_only_the_ratio` (40 vs 36)
- **Type**: Frozen-number drift
- **Detail**: New NF experiments added nested metrics (ablations, perturbation blocks); pinned counts not updated.

### 10. `test_engine_total_return_consistency.py::test_no_runner_selects_on_the_engines_total_return` (33 "offenders")
- **Type**: Stale test-scope assertion
- **Detail**: The test assumes only H18 computes `total_return`. Actually, 33 NF runners compute a **local** `total_return` (using `eq.iloc[-1] / eq.iloc[0] - 1.0`) for disclosure in their `summary.json`. They do **not** read `metrics["total_return"]` from the engine. The test's string search for `"total_return"` in source is too broad.
- **Evidence**: Verified in `run_nf_20261107_04_amihud_illiq.py:220` and `run_nf_20261104_03_es_spy_basis.py:234` — local computation, not engine metric access.
- **Action**: Narrow the test to check for `metrics["total_return"]` / `metrics['total_return']` access only (already done in the first two asserts); remove the broad `"total_return" not in source` fallback.

---

## Pre-existing failures (unchanged)

- `tests/test_trade_log_cost_reconciliation.py::TestFrozenRecordScope` — 2 failed (3 contested per-trade `exp_2026-11-05` logs, held-open pending explicit authorization). Adding them breaks `test_the_three_pinned_sets_partition_the_record`.

---

## Verified this session

- `python -m ruff check src tests run_*.py` — **All checks passed**
- `python -m ruff format --check src tests run_*.py` — **316 files already formatted**
- `PYTHONPATH=src pytest -q tests/test_h51_benchmark_container_invariance.py tests/test_h53_published_metrics_disclosure.py tests/test_h55_nested_metrics_disclosure.py tests/test_gate_vacuity_contract.py tests/test_engine_total_return_consistency.py` — **10 failed, 308 passed, 12 skipped** (failures documented above)
- `PYTHONPATH=src pytest tests/test_h57_total_return_audit.py::TestTheRecord tests/test_h57_total_return_audit.py::TestTheControl tests/test_h57_total_return_audit.py::TestTheConvention tests/test_h57_total_return_audit.py::TestTheCounterfactual tests/test_h57_total_return_audit.py::TestTheVerdictImpact tests/test_h57_total_return_audit.py::TestTheDisclosure` — **All passed** (TestTheAuditReDerives passes but takes ~90s for deterministic rebuild test)

---

## Next task (BLOCKED on explicit authorization)

Per-contract review of the frozen-contract drifts above:
1. `test_h51_benchmark_container_invariance.py` — update `PUBLISHED_INFORMATION_RATIOS` with 21 new experiment IDs
2. `test_h53_published_metrics_disclosure.py` — fix test recipe for NF runners (remove incorrect `bench_p_published_default=True`), update pinned counts (54→58 summaries, 630→674 values)
3. `test_h55_nested_metrics_disclosure.py` — update all pinned counts (ablations 44→48, perturbation 24→28, leaves 1188→1292, re-derived 627→631, perturbation gates 36→40)
4. `test_engine_total_return_consistency.py` — narrow `test_no_runner_selects_on_the_engines_total_return` to only flag `metrics["total_return"]` access (remove broad string search)

**Do not mass-edit to force the suite green.** Each requires evidence-based per-contract review and authorization.

---

## Deferred (do not select without authorization)

- Resolve the 3 held-open contested per-trade logs in `test_trade_log_cost_reconciliation.py` — amends frozen-record disclosure; requires explicit authorization (breaks `test_the_three_pinned_sets_partition_the_record`).
- Select H182 — blocked on commodity-carry data gap (no free PIT term-structure/roll proxy; yfinance provides only `=F` continuous contracts) or conclusion that free-data family discovery is exhausted per Cycle 96.

---

## Failed approaches / do not blindly repeat

- Do not add the 3 contested per-trade logs to `TRADE_LOG_RECORD` — breaks partition test; requires explicit authorization.
- Do not mass-edit runners/tests/gates to force the suite green.
- New-family discovery queue H85–H181 is exhausted (Cycle 96); H182 unassigned; no feasible H182 candidate without resolving data gap.

(End of file)