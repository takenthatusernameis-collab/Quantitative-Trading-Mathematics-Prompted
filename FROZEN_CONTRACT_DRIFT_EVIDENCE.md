# Frozen-Contract Drift Evidence Package

**Generated:** 2026-11-11
**Repository state:** HEAD, `src/qtr` unchanged, no commits/pushes this session
**Purpose:** Evidence for per-contract authorization to resolve 9 frozen-number drifts

---

## Summary

All 9 failures are **pre-existing frozen-number drifts** caused by new NF experiment artifacts (H85–H181) committed after the pinned counts were established. No new code bugs, no gate regressions, no `src/qtr` changes.

| Contract | Test | Expected | Actual | Drift Cause |
|---|---|---|---|---|
| H51 | `test_every_published_information_ratio_is_disclosed` | 48 pinned | 69 found (+21) | 21 new NF IR-publishing artifacts (2026-11-05/06) |
| H53 | `test_h53_metrics_summary_count_pinned` | 54 | 58 (+4) | 4 new NF summaries with metrics blocks |
| H53 | `test_h53_published_value_count_pinned` | 630 | 674 (+44) | 44 new metric values from NF artifacts |
| H55 | `test_summaries_publish_nested_block_pinned` | ablations 44, perturbation 24 | ablations 48, perturbation 28 | NF artifacts add nested blocks |
| H55 | `test_published_leaf_count_pinned` | 1188 | 1292 (+104) | NF nested block leaves |
| H55 | `test_rederivable_disclosed_counts_pinned` | 627 | 631 (+4) | NF re-derivable leaves |
| H55 | `test_perturbation_gate_reads_only_ratio` | 36 | 40 (+4) | NF perturbation gates |
| TradeLog | `test_committed_trade_logs_pinned` | pinned set | +3 contested + H28 logs | 3 `exp_2026-11-05` + H28 causal-recert |
| TradeLog | `test_aggregate_attribution_recorded` | 0 missing | 3 missing | 3 `exp_2026-11-05` logs lost pre-fix attribution |

**Total drift:** 21 + 4 + 44 + 4 + 4 + 104 + 4 + 4 + 3 = **192** new data points from NF H85–H181 artifacts.

---

## H51: `test_every_published_information_ratio_is_disclosed`

**Failure:** 21 new IR-publishing experiments not in pinned `PUBLISHED_INFORMATION_RATIOS` set.

**Extra artifact IDs (all NF, 2026-11-05/06):**
```
exp_2026-11-05T01-17-49-208916Z   nf_20261105_01_opening_gap
exp_2026-11-05T01-22-22-092087Z   nf_20261105_01_opening_gap
exp_2026-11-05T01-24-02-934356Z   nf_20261105_01_opening_gap
exp_2026-11-05T01-43-20-575295Z   nf_20261104_01_vix_termstructure
exp_2026-11-05T02-51-06-343400Z   nf_20261105_01_opening_gap
exp_2026-11-05T04-44-31-638354Z   nf_20261105_01_opening_gap
exp_2026-11-05T12-24-33-350043Z   nf_20261105_06_gold_oil_rv
exp_2026-11-05T12-36-06-158635Z   nf_20261105_07_skew_tail_timing
exp_2026-11-05T13-22-09-693533Z   nf_20261105_08_fomc_event_drift
exp_2026-11-05T13-32-16-258120Z   nf_20261105_09_turn_of_month
exp_2026-11-05T13-32-55-648939Z   nf_20261105_09_turn_of_month
exp_2026-11-05T15-24-22-849461Z   nf_20261105_10_equity_bond_relmom
exp_2026-11-05T15-40-24-218763Z   nf_20261105_10_equity_bond_relmom
exp_2026-11-05T18-05-46-174209Z   nf_20261105_10_equity_bond_relmom
exp_2026-11-05T18-09-06-924039Z   nf_20261105_13_idiosyncratic_vol
exp_2026-11-05T18-11-49-464520Z   nf_20261105_10_equity_bond_relmom
exp_2026-11-05T18-12-36-229696Z   nf_20261105_10_equity_bond_relmom
exp_2026-11-06T02-00-06-752931Z   nf_20261105_10_equity_bond_relmom
exp_2026-11-06T02-17-43-039138Z   nf_20261105_10_equity_bond_relmom
exp_2026-11-06T03-36-48-479398Z   nf_20261105_10_equity_bond_relmom
exp_2026-11-06T04-23-47-511988Z   nf_20261105_10_equity_bond_relmom
```

**Producers:** `nf_20261104_01_vix_termstructure` (H86), `nf_20261105_01_opening_gap` (H87), `nf_20261105_06_gold_oil_rv` (H88), `nf_20261105_07_skew_tail_timing` (H89), `nf_20261105_08_fomc_event_drift` (H90), `nf_20261105_09_turn_of_month` (H91), `nf_20261105_10_equity_bond_relmom` (H92), `nf_20261105_13_idiosyncratic_vol` (H93).

**Resolution required:** Add these 21 artifact IDs to `PUBLISHED_INFORMATION_RATIOS` in `tests/test_h51_benchmark_container_invariance.py`.

---

## H53: `test_h53_metrics_summary_count_pinned`

**Failure:** 58 summaries vs pinned 54 (+4).

**New summaries (all NF, 2026-11-05/06):**
- The 4 new NF producers that publish metrics blocks beyond the original 54.

**Resolution required:** Update pinned count from 54 → 58 in `tests/test_h53_published_metrics_disclosure.py:1052`.

---

## H53: `test_h53_published_value_count_pinned`

**Failure:** 674 published metric values vs pinned 630 (+44).

**Breakdown:** 4 new summaries × 11 metric keys each ≈ 44 new values (some summaries may not publish all 13 keys).

**Resolution required:** Update pinned count from 630 → 674 in `tests/test_h53_published_metrics_disclosure.py:1084`.

---

## H53: `test_every_published_value_re_derives`

**Status: PASSED** — All published values re-derive from their frozen artifacts (except the 9 undeterminable regime values from H9 family). The H92 `benchmark_p_value` recipe fix is confirmed working.

---

## H55: `test_the_summaries_that_publish_a_nested_block_are_pinned`

**Failure:** Nested block counts drifted.
- `ablations`: 44 → 48 (+4)
- `perturbation`: 24 → 28 (+4)
- `perturbation_min_ratio`: 7 (unchanged)
- `cross_validation`: 2 (unchanged)
- `top_level_perturbation`: 5 (unchanged)

**Resolution required:** Update pinned dict in `tests/test_h55_nested_metrics_disclosure.py`.

---

## H55: `test_the_published_leaf_count_is_pinned`

**Failure:** 1292 leaves vs pinned 1188 (+104).

**Resolution required:** Update pinned count from 1188 → 1292.

---

## H55: `test_the_rederivable_and_disclosed_counts_are_pinned`

**Failure:** 631 re-derivable vs pinned 627 (+4).

**Resolution required:** Update pinned count from 627 → 631.

---

## H55: `test_the_perturbation_gate_reads_only_the_ratio`

**Failure:** 40 gates vs pinned 36 (+4).

**Resolution required:** Update pinned count from 36 → 40.

---

## Trade Log Reconciliation: `test_the_committed_trade_logs_are_exactly_the_pinned_record`

**Failure:** Committed trade logs differ from pinned `TRADE_LOG_RECORD`.

**Extra logs in committed artifacts (not in pinned record):**
1. `exp_2026-11-05T01-17-49-208916Z/best_trades.parquet`
2. `exp_2026-11-05T01-24-02-934356Z/best_trades.parquet`
3. `exp_2026-11-05T18-09-06-924039Z/best_trades.parquet`
4. H28 causal-recertification logs (7 runs from `exp_2026-10-19T15-46-16Z` through `exp_2026-10-19T17-39-12Z`)

**Note:** The 3 `exp_2026-11-05` logs are the **same 3 contested logs** documented in handoffs — they no longer carry the pre-fix attribution. Adding them to `TRADE_LOG_RECORD` breaks `test_the_three_pinned_sets_partition_the_record`.

**Resolution required:** Per-contract decision on (a) adding H28 logs to pinned record, (b) handling the 3 contested logs (authorization required).

---

## Trade Log Reconciliation: `test_every_committed_trade_log_records_the_aggregate_attribution`

**Failure:** 3 committed trade logs missing the pre-fix aggregate attribution.
- `exp_2026-11-05T01-17-49-208916Z/best_trades.parquet`
- `exp_2026-11-05T01-24-02-934356Z/best_trades.parquet`
- `exp_2026-11-05T18-09-06-924039Z/best_trades.parquet`

**Resolution required:** Same 3 contested logs — explicit authorization needed per handoff.

---

## Verification Checklist (All Confirmed)

- [x] `python -m ruff check src tests run_*.py` — clean
- [x] `python -m ruff format --check src tests run_*.py` — clean (316 files)
- [x] `PYTHONPATH=src python -m pytest tests/test_benchmark_gate_contract.py` — 26 passed (prior fix confirmed)
- [x] `PYTHONPATH=src python -m pytest tests/test_engine_total_return_consistency.py` — 16 passed (test-logic bug fix confirmed)
- [x] Frozen-contract suite: **348 passed, 9 failed, 12 skipped** (matches prior session)
- [x] H92 `benchmark_p_value` recipe fix verified — `test_every_published_value_re_derives` passes
- [x] H57/total-return code-bug hypothesis disproven — both audit tests pass
- [x] `src/qtr` unchanged throughout
- [x] No published/certified artifact, verdict, threshold, or frozen number modified
- [x] No commit/push

---

## Authorization Request

Per handoff constraints and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md`, the following require explicit per-contract authorization:

1. **H51:** Add 21 NF artifact IDs to `PUBLISHED_INFORMATION_RATIOS`
2. **H53:** Update pinned counts (54→58 summaries, 630→674 values)
3. **H55:** Update 4 pinned counts (ablations 44→48, perturbation 24→28, leaves 1188→1292, rederivable 627→631, gates 36→40)
4. **Trade Log:** Resolve 3 contested `exp_2026-11-05` logs + 7 H28 causal-recertification logs (partition test constraint)

**Alternative (Cycle 96 conclusion):** Conclude free-data family discovery exhausted; shift to auditing/infrastructure; leave frozen drifts as documented evidence of NF H85–H181 execution.

---

## Next Session Task

Upon authorization:
1. Apply minimal pinned-count updates to test files only (no `src/qtr`, no runner, no gate, no artifact changes)
2. Re-run focused frozen-contract modules to verify green
3. Re-run full pinned suite to confirm no new regressions
4. Document resolution in handoff

If no authorization: proceed with auditing/infrastructure tasks per Cycle 96 directive.