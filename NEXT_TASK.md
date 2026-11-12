# NEXT_TASK.md — Coverage gate fixed (100% src/qtr); remaining failures are frozen-count drifts

## Status

**Cycle 101 (2026-11-12) — dead probe/stub cleanup + baseline re-verification (no authorization needed; no gated artifact/test touched).**

Removed 2 committed, unreferenced probe/stub files (`_probe_h51.py`, `run_h148_probe.py`; verified unreferenced by grep before deletion). Baseline re-verified green: ruff check/format clean (314 files); runner-touching suites 764 passed/0 failed; full suite 3530 passed/3 failed/16 skipped (the 3 = documented authorization-gated frozen-contract drifts; no new failure, no regression); `src/qtr` coverage unchanged at 100%. Two working-tree deletions left unstaged (no commit/push — not explicitly requested).

**No `src/qtr` change. No gated artifact, test, threshold, or frozen number touched. No commit/push.**

## Verified this session

- **Stale-audit re-verification:** `tests/test_benchmark_gate_contract.py` — **26 passed**,
  including `test_no_runner_compares_a_p_value_against_max_p_value_directly` (0 offenders
  vs. the 38 the audit doc claimed) and `test_every_runner_with_a_benchmark_gate_uses_the_direction_aware_helper`.
- **Runner-touching suites after stub deletion:** `test_runner_import_contract`,
  `test_benchmark_gate_contract`, `test_gate_vacuity_contract`,
  `test_engine_metric_agreement`, `test_engine_total_return_consistency`,
  `test_parameter_sensitivity_reproducibility`, `test_runner_causality_inventory`,
  `test_probe_report_schema`, `test_config` — **773 passed, 0 failed**.
- **Full suite:** **3429 passed, 9 failed, 16 skipped** (was 3433 passed; the −4 is the
  deletion of `_chunk_test.py`/`_t8.py`/`_t11.py`, which were never collected by pytest
  because `testpaths = ["tests"]`). The 9 failures are **unchanged and are exactly the
  documented frozen-contract drifts** — no new failure, no regression.
- `python -m ruff check src tests run_*.py` — All checks passed.
- `python -m ruff format --check src tests run_*.py` — 314 files already formatted.
- `src/qtr` coverage — **100%** (1209 stmts / 420 branches, 0 miss), unchanged.

## Prior session's verified work (kept for lineage)

The prior session's H53 recipe correction (removal of 3 stale H92 `benchmark_p_value`
artifact IDs from `BENCH_P_PUBLISHED_DEFAULT_ARTIFACTS`) is **verified in an
environment with project deps**. The 3 H92 `benchmark_p_value` re-derivation
mismatches are gone.

**Prior session's fix:** the `src/qtr` coverage gate (`fail_under = 100` in
`pyproject.toml`) was a real defect — measured coverage was **99%** (5 uncovered
defensive branches in `src/qtr/backtest/engine.py`: 146, 198, 230, 246, 401).
Added 9 focused tests in `tests/test_backtest_engine.py`
(`TestFailClosedCostGuards`) pinning each fail-closed guard with the exact input
that takes its branch. Coverage is now **100%** (1209 stmts / 420 branches, 0
miss). `src/qtr` source unchanged; only tests added.

## The 3 remaining frozen-contract failures (all drift; all require authorization)

H53/H55 drifts are now green (resolved in prior session; do not re-open). Remaining:

1. `test_h51_benchmark_container_invariance.py::test_every_published_information_ratio_is_disclosed` — 21 NF artifacts (2026-11-05/06) publish IR but are not in pinned `PUBLISHED_INFORMATION_RATIOS`; 18/21 re-derive cleanly under ddof=0, 3 (`nf_20261104-02` OOS window mismatches) need per-artifact recipe investigation.
2. `test_trade_log_cost_reconciliation.py::TestFrozenRecordScope::test_the_committed_trade_logs_are_exactly_the_pinned_record` — 3 contested `exp_2026-11-05` per-trade logs (`exp_2026-11-05T01-17-49-208916Z`, `01-24-02-934356Z`, `18-09-06-924039Z`) + 8 H28 causal-recertification trade parquets committed but not in `TRADE_LOG_RECORD`.
3. `test_trade_log_cost_reconciliation.py::TestFrozenRecordScope::test_every_committed_trade_log_records_the_aggregate_attribution` — the 3 contested logs record per-trade (not aggregate) attribution.

## Failed approaches / do not blindly repeat

- Do not update pinned counts in H51/H53/H55 without authorization — frozen-number/count drifts.
- Do not add the 3 contested per-trade logs to `TRADE_LOG_RECORD` — breaks
  `test_the_three_pinned_sets_partition_the_record`; authorization required.
- Do not treat the 3 newer H92 artifacts as published-default p-values; artifacts show
  the real `0.005822770948177806` (runner uses `cmp.get("alpha_p_value", 1.0)`).
- Do not mass-edit runners/tests/gates to force the suite green.

## Next task

**One precise next task:** When explicit authorization is available, do exactly one of: (a) resolve one of the 9 frozen-contract drifts via per-contract evidence review (exact failures listed in §"The 9 remaining frozen-contract failures"), or (b) resolve a free-data gap under explicit authorization (futures roll/contango data for carry; PIT insider/earnings/options data) and select H182. Network access IS available (yfinance returns real SPY data, verified 2026-11-11T18:30Z), so the data-gap path is no longer network-blocked — but still authorization-blocked per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6. Per `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 96), H1–H181 are all executed and rejected and the free-data family queue is exhausted; absent a data-gap resolution under authorization, conclude free-data family discovery is exhausted and shift to auditing/infrastructure rather than inventing candidates.

**Status verified this session (2026-11-11T18:30Z, own evidence):** `src/qtr` unchanged; working tree clean; `ruff check/format` clean (314 files); coverage **100%** (TOTAL 1209/0/420/0); full suite **3429 passed, 9 failed, 16 skipped** — the 9 failures are exactly the documented frozen-contract drifts below, no new code bug, no regression. **Network access IS available** (yfinance SPY download OK), correcting the prior session's "no network access" note. **H160 is already executed** (Cycle 74, NF-20261109-01 IVOL dispersion, REJECT 4/8, recorded in `HYPOTHESIS_SPEC.md` §H160); do not re-implement H160.

## Deferred (do not select without authorization)

- Update pinned counts in `test_h51_benchmark_container_invariance.py`,
  `test_h53_published_metrics_disclosure.py`, `test_h55_nested_metrics_disclosure.py` —
  frozen-number/count drifts.
- Resolve 3 contested per-trade logs in `test_trade_log_cost_reconciliation.py`
  (`exp_2026-11-05T01-17-49-208916Z`, `01-24-02-934356Z`, `18-09-06-924039Z`) —
  breaks partition; authorization required.
- Select H182 — commodity-carry data gap / no feasible free-data family per Cycle 96
  (discovery queue exhausted unless data gap resolved under authorization).

**Constraints:** `src/qtr` unchanged unless an evidenced defect requires it (then rerun pinned full gates); no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modified; no commit/push unless explicitly requested.

## Session 2026-11-11T21:11Z — read-only re-verification (no changes)

No source, test, gate, frozen-number, or artifact change. Working tree clean; no commit/push.

**Actually verified (this session, own evidence):**
- Re-ran the four frozen-drift test files — **all 9 failures still present, unchanged** (no new failure, no regression).
- Full suite `pytest -q --cov=qtr --cov-branch` — **3526 passed, 9 failed, 16 skipped** (all 9 = documented frozen drifts; no code bug, no regression).
- `src/qtr` coverage — **100%** (1209 stmts / 420 branches, 0 miss).
- `python -m ruff check src tests run_*.py` — all checks passed.
- `python -m ruff format --check src tests run_*.py` — 315 files already formatted.