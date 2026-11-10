# NEXT_TASK.md — test-logic bug fixed; next: H92 benchmark_p_value recipe investigation

## Status

One **test-logic bug** fixed this session (not a frozen-number drift):
`tests/test_engine_total_return_consistency.py::TestRemainingDisclosures::test_no_runner_selects_on_the_engines_total_return`
was flagging 33 NF runners as false positives because its broad fallback
(`"total_return" not in source`) caught runners that publish a runner-local
`total_return` scalar without reading the engine's metric. Removed the broad
fallback, added a negative control so the scan is not vacuous. Module now
**16 passed** (was 1 failed). `ruff check/format` clean. No `src/qtr`, runner,
gate, threshold, or frozen-number change.

## Verified this session

- `python -m ruff check tests/test_engine_total_return_consistency.py` — clean.
- `python -m ruff format --check tests/test_engine_total_return_consistency.py` — clean.
- `PYTHONPATH=src pytest -q tests/test_engine_total_return_consistency.py` — **16 passed**.
- Frozen-contract modules re-run: **11 failed, 345 passed, 12 skipped** (was 12 failed; the engine module's failure is gone, no new failure introduced).

## Next task

Investigate the 3 H92 `benchmark_p_value` mismatches in
`tests/test_h53_published_metrics_disclosure.py` — the only remaining
*test-recipe* failures rather than frozen-number drifts:

- Artifacts: `exp_2026-11-06T02-17-43-039138Z`, `exp_2026-11-06T03-36-48-479398Z`, `exp_2026-11-06T04-23-47-511988Z` (all `nf_20261105_10_equity_bond_relmom` / H92).
- Published `benchmark_p_value = 0.005822770948177806`; recipe re-derives `1.0` because `FAMILY_RECIPES["nf_20261105_10_equity_bond_relmom"]` still carries `bench_p_published_default=True`.
- Runner source (`run_nf_20261105_10_equity_bond_relmom.py:234`) uses `cmp.get("alpha_p_value", 1.0)` — the correct key, so the published 0.0058 is the real value and the recipe flag is stale for these 3 artifacts.
- Same producer has 6 older artifacts where published == re-derived == 1.0 (the flag is harmless there).

Determine whether the flag should be removed entirely or narrowed to the older
artifacts only. If evidenced, apply the minimal fix (flag correction only —
no number/gate/threshold changes) and re-run the focused module. If no fix is
evidenced, document as a genuine frozen-record item requiring authorization.

## Deferred (do not select without authorization)

- Resolve the 3 contested per-trade logs in `test_trade_log_cost_reconciliation.py` — amends frozen-record disclosure; requires explicit authorization (breaks `test_the_three_pinned_sets_partition_the_record`).
- Update pinned counts in `test_h51_benchmark_container_invariance.py` (21 new IR experiments), `test_h53_published_metrics_disclosure.py` (54→58 summaries, 630→674 values), `test_h55_nested_metrics_disclosure.py` (ablations 44→48, perturbation 24→28, leaves 1188→1292, re-derived 627→631, perturbation gates 36→40) — all frozen-number drifts, require authorization.
- Select H182 — blocked on commodity-carry data gap (no free PIT term-structure/roll proxy; yfinance provides only `=F` continuous contracts) or conclusion that free-data family discovery is exhausted per Cycle 96.

H182 remains unassigned; NF discovery queue exhausted per Cycle 96.