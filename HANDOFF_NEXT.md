# HANDOFF_NEXT.md — H53 recipe verified; 9 frozen-contract failures are all drift

## What changed (verified this session)

- **H53 recipe correction confirmed**: the 3 H92 (`nf_20261105_10_equity_bond_relmom`)
  artifacts `exp_2026-11-06T02-17-43-039138Z`, `03-36-48-479398Z`, `04-23-47-511988Z`
  are correctly excluded from `BENCH_P_PUBLISHED_DEFAULT_ARTIFACTS`. The
  `test_every_published_value_re_derives` test now **passes** (was failing on those 3
  `benchmark_p_value` mismatches).
- Lint/format on `tests/test_h53_published_metrics_disclosure.py` — clean.
- Full frozen-contract suite run — all 9 failures are pre-existing frozen-number/count
  drifts or contested trade logs. No new code bug found.

## Actually verified (this session)

- `python -m ruff check tests/test_h53_published_metrics_disclosure.py && python -m ruff format --check tests/test_h53_published_metrics_disclosure.py` — clean.
- `PYTHONPATH=src python -m pytest -q tests/test_h53_published_metrics_disclosure.py` — **18 passed, 2 failed** (pinned-count drifts only: 58 vs 54 summaries, 674 vs 630 values).
- `PYTHONPATH=src python -m pytest -q` on all 6 frozen-contract files — **348 passed, 9 failed, 12 skipped**. No new code bugs found.
- **Baseline evidence:** the original commit `82eb68a`'s version of this same test file,
  run against the current working tree, also yields **58 / 674**. So the pins `54` / `630`
  were already stale at commit time — pure frozen-number drift, not a regression.

## Unresolved / pre-existing (require authorization, do not mass-fix)

1. **H51** `test_every_published_information_ratio_is_disclosed` — 21 new IR-publishing experiments not in pinned `PUBLISHED_INFORMATION_RATIOS`.
2. **H53** `test_h53_metrics_summary_count_pinned` (58 vs 54) and `test_h53_published_value_count_pinned` (674 vs 630) — pinned-count drifts.
3. **H55** 4 failures — nested-block set, leaf count 1292 vs 1188, rederivable count 631 vs 627, perturbation gate 40 vs 36.
4. **Trade log reconciliation** 2 failures — 3 contested per-trade `exp_2026-11-05` logs (`exp_2026-11-05T01-17-49-208916Z`, `01-24-02-934356Z`, `18-09-06-924039Z`) + H28 causal-recertification logs; adding them breaks partition.
5. **H182** unassigned — NF discovery queue exhausted per Cycle 96 (commodity-carry data gap: no free PIT term-structure/roll proxy).

## Failed approaches / do not blindly repeat

- Do not update pinned counts in H51/H53/H55 without authorization.
- Do not add the 3 contested per-trade logs to `TRADE_LOG_RECORD` — breaks `test_the_three_pinned_sets_partition_the_record`.
- Do not treat the 3 newer H92 artifacts as published-default; they correctly publish the real `alpha_p_value`.
- The H57 / engine-total-return "code bug" hypothesis is disproven — `test_h57_total_return_audit.py` (66 passed) and `test_engine_total_return_consistency.py` (16 passed) both pass.

## Next task

**One precise next task:** Await authorization to update frozen counts in H51/H53/H55 test files, resolve the 3 contested per-trade logs in `test_trade_log_cost_reconciliation.py`, or select H182 (requires resolving commodity-carry data gap under authorization or concluding free-data family discovery exhausted per Cycle 96).

**Evidence to review before authorization:** Exact failure diffs above; artifact inspection confirms the 3 H92 `benchmark_p_value` mismatches are resolved by the recipe correction already committed; the H57/total-return code-bug hypothesis is disproven.