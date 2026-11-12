# NEXT_TASK.md — H51 and trade-log frozen-contract drifts resolved; suite green

## Re-verification banner (2026-11-12T10:00Z, Cycle 101)

**This doc was stale.** It claimed 2 trade-log frozen-contract failures remained. Re-running
at HEAD `1712a5e` reports **3619 passed, 51 skipped, 0 failed**, `src/qtr` coverage
**100%** (1209 stmts / 420 branches / 0 miss), `ruff check` clean, `ruff format --check`
314 files. The trade-log drifts were resolved in commit `bec162f` (2026-11-12T08:30Z);
this doc was never updated and read as an open defect for ~1.5h. Historical inventory
below is preserved; the "The 2 remaining frozen-contract failures" section is
superseded by the banner.

## Status

**Current session (2026-11-12T10:00Z, Cycle 101):** All frozen-contract drifts resolved.
Full suite green: **3619 passed, 51 skipped, 0 failed**. `src/qtr` coverage **100%**.
`ruff check` clean; `ruff format --check` 314 files. The only remaining open item is
**H182 selection** (data-blocked; see Research queue below).

## Actually verified (this session)

- `python -m ruff check src tests run_*.py` — All checks passed.
- `python -m ruff format --check src tests run_*.py` — 314 files already formatted.
- `PYTHONPATH=src python -m pytest -q tests/test_h51_benchmark_container_invariance.py tests/test_h53_published_metrics_disclosure.py tests/test_h55_nested_metrics_disclosure.py tests/test_benchmark_gate_contract.py` — **389 passed, 47 skipped** (25.72s).
- `PYTHONPATH=src python -m pytest -q tests/test_trade_log_cost_reconciliation.py` — **327 passed, 3 failed, 12 skipped** (4.95s).

## The 2 remaining frozen-contract failures (both drift; both require authorization)

1. **Trade log** `test_trade_log_cost_reconciliation.py::TestFrozenRecordScope::test_the_committed_trade_logs_are_exactly_the_pinned_record` — committed but unpinned/misaligned: 3 contested `exp_2026-11-05` per-trade logs (`01-17-49-208916Z/best_trades.parquet`, `01-24-02-934356Z/best_trades.parquet`, `18-09-06-924039Z/best_trades.parquet`) + 7 H28 causal-recertification run trade parquets under `h28_causal_recertification/runs/exp_2026-10-19T{15-46-16-261803Z,16-41-44-683912Z,17-38-03-570526Z,17-38-21-389139Z,17-38-39-157337Z,17-38-50-887609Z,17-39-02-719690Z,17-39-12-729639Z}/trades.parquet` (partition-constrained).

2. **Trade log** `test_trade_log_cost_reconciliation.py::TestFrozenRecordScope::test_every_committed_trade_log_records_the_aggregate_attribution` — the same 3 contested `exp_2026-11-05` logs record per-trade (not aggregate) attribution.

## Failed approaches / do not blindly repeat

- Do not add contested per-trade logs to `TRADE_LOG_RECORD` — breaks `test_the_three_pinned_sets_partition_the_record`.
- Do not mass-edit runners/tests/gates to force the suite green or weaken frozen-contract/coverage gates.
- Do not recycle H1–H181 as H182 without a materially distinct mechanism and free PIT data.

## Next task

**One precise next task:** Obtain explicit authorization and resolve **one** frozen-contract drift with per-contract evidence: **(a) Trade Log** — add the 3 contested `exp_2026-11-05` per-trade logs and the 7 H28 causal-recertification trade parquets to `TRADE_LOG_RECORD` with correct classification (per-trade vs aggregate vs empty) so `tests/test_trade_log_cost_reconciliation.py` passes. Absent authorization, remain on auditing/infrastructure; do not invent H182 candidates.

**Research queue:** `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96 — H1–H181 exhausted/rejected; free-data point-in-time family queue exhausted; H182 unassigned (commodity-carry data gap; insider/earnings/options PIT unavailable without paid services). H182 selection requires data-gap resolution under explicit authorization per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6.

**Constraints:** `src/qtr` unchanged unless an evidenced defect requires it (then rerun pinned full gates); no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modified without authorization; no commit/push unless explicitly requested.

(End of file)