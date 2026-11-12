# NEXT_TASK.md — Baseline verified (clean lint/format); 3 frozen-contract drifts remain authorization-gated

## Status

**Current session (read-only re-verification, no authorization needed):** No source, test, gate, artifact, or frozen-number changes. Working tree clean at start. Ruff check/format clean (314 files). Frozen-contract modules re-run: **327 passed, 3 failed, 12 skipped** — the 3 failures are exactly the documented authorization-gated drifts below (H53/H55 green), no new failure, no regression.

## Actually verified (this session)

- `git status --short --branch` (start) — `## main...origin/main` (clean).
- `python -m ruff check src tests run_*.py` — All checks passed.
- `python -m ruff format --check src tests run_*.py` — 314 files already formatted.
- `python -m pytest -q tests/test_h51_benchmark_container_invariance.py tests/test_h53_published_metrics_disclosure.py tests/test_h55_nested_metrics_disclosure.py tests/test_trade_log_cost_reconciliation.py` — **327 passed, 3 failed, 12 skipped**.

## The 3 remaining frozen-contract failures (all drift; all require authorization)

1. **H51** `test_h51_benchmark_container_invariance.py::test_every_published_information_ratio_is_disclosed` — 21 NF artifacts (2026-11-05/06) publish IR but are not in pinned `PUBLISHED_INFORMATION_RATIOS`; 18/21 re-derive cleanly under ddof=0, 3 (`nf_20261104-02`) need per-artifact recipe investigation.
2. **Trade log** `test_trade_log_cost_reconciliation.py::TestFrozenRecordScope::test_the_committed_trade_logs_are_exactly_the_pinned_record` — 3 contested `exp_2026-11-05` per-trade logs (`01-17-49-208916Z`, `01-24-02-934356Z`, `18-09-06-924039Z`) + 7 committed H28 causal-recertification trade parquets (`exp_2026-10-19T15-46-16-261803Z`, `16-41-44-683912Z`, `17-38-03-570526Z`, `17-38-21-389139Z`, `17-38-39-157337Z`, `17-39-02-719690Z`, `17-39-12-729639Z`) committed but not aligned with `TRADE_LOG_RECORD` (partition-constrained).
3. **Trade log** `test_trade_log_cost_reconciliation.py::TestFrozenRecordScope::test_every_committed_trade_log_records_the_aggregate_attribution` — the 3 contested `exp_2026-11-05` logs record per-trade (not aggregate) attribution.

## Failed approaches / do not blindly repeat

- Do not update pinned counts in H51/H53/H55 or add NF IR entries without per-artifact recipe verification and authorization — 3 `nf_20261104-02` H51 artifacts do not re-derive under a naive full-series recipe.
- Do not add the 3 contested per-trade logs to `TRADE_LOG_RECORD` — breaks `test_the_three_pinned_sets_partition_the_record`; authorization required.
- Do not mass-edit runners/tests/gates to force the suite green or weaken gates.
- Do not recycle H1–H181 as H182 without a materially distinct mechanism and free PIT data.

## Next task

**One precise next task:** Obtain explicit authorization and resolve **one** frozen-contract drift with per-contract evidence: **(a) H51** — add the 18 clean NF IR entries (and required recipes/prefix/DDOF updates) and separately investigate/fix recipes for the 3 `nf_20261104-02` mismatches so `tests/test_h51_benchmark_container_invariance.py` passes, **or (b) Trade Log** — reconcile the 3 contested `exp_2026-11-05` per-trade logs and the 7 committed-but-unpinned H28 causal-recertification trade parquets under the partition-test constraint so `tests/test_trade_log_cost_reconciliation.py` passes. Absent authorization, remain on auditing/infrastructure; do not invent H182 candidates.

**Research queue:** `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96 — H1–H181 exhausted/rejected; free-data point-in-time family queue exhausted; H182 unassigned (commodity-carry data gap; insider/earnings/options PIT unavailable without paid services). Network access available but H182 requires data-gap resolution under explicit authorization (`STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6).

**Constraints:** `src/qtr` unchanged unless an evidenced defect requires it (then rerun pinned full gates); no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modified without authorization; no commit/push unless explicitly requested.
