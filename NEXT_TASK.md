# NEXT_TASK.md — H52 frozen-record pin complete (100/103 logged); 3 contested logs held-open
## Status

H52 pinning task complete: `TRADE_LOG_RECORD` covers 100 of 103 committed trade logs; three classification sets partition the 100 pinned logs exactly. The only 3 unpinned are the contested per-trade `exp_2026-11-05` best_trades logs (`T01-17-49-208916Z`, `T01-24-02-934356Z`, `T18-09-06-924039Z`). Test file: 35 passed, 2 failed (contested-only); partition test passes.

**This session:** Fixed `KeyError: 'alpha_p_value'` code bug in 7 NF experiment runners (files `run_nf_20261107_{04,07,08,10,13,15,28}_*.py`). Each runner's `evaluate_gates` accessed `bench["alpha_p_value"]` but the bench dict carries the p-value under key `"p_value"`. Changed `bench["alpha_p_value"]` → `bench["p_value"]` (10 lines, 7 files). No `src/qtr`, test, gate, or frozen-number changes.

- `python -m ruff check` on fixed runners — clean
- `python -m ruff format --check` on fixed runners — clean
- `PYTHONPATH=src pytest -q tests/test_nf_20261107_{03,04,07,08,10,13,15,28}_*.py` — **87 passed** (was 10 failing with KeyError)

Full core suite 282 passed; benchmark gates 26 passed; NF regressions 30 passed. Ruff clean on 316 files.

## Verified this session
- `python -m ruff check src tests run_*.py` — All checks passed.
- `python -m ruff format --check src tests run_*.py` — already formatted.
- `PYTHONPATH=src pytest -q tests/test_trade_log_cost_reconciliation.py` — **35 passed, 2 failed**; both failures are the 3 held-open contested per-trade logs.
- `test_the_three_pinned_sets_partition_the_record` — **passed**.

## Investigation completed this session — frozen-contract failures are not code bugs

Inspected all 7 pre-existing frozen-contract failures for code bugs analogous to the fixed `alpha_p_value`/`p_value` KeyError:

- `tests/test_h57_total_return_audit.py` — **all pass** (no failure currently).
- `tests/test_engine_total_return_consistency.py` — engine contract (`TestEngineTotalReturnContract`) and artifact audit pass; the single failure is `TestRemainingDisclosures::test_no_runner_selects_on_the_engines_total_return`: 33 committed NF runners mention `total_return` only in disclosure `_metrics` dicts written to `summary.json` (6 read the engine's now-corrected `res.metrics["total_return"]` solely to publish it); **none use it in gates/selection/verdict**. Mirrors the H18 runner disclosure the test already carves out. **Not a key-mismatch bug; not a number change — a stale test-scope assertion.**
- `tests/test_h51_benchmark_container_invariance.py` — 1 failure: set-mismatch of published/disclosed information-ratio experiment IDs (frozen-number drift).
- `tests/test_gate_vacuity_contract.py` — **all pass**.
- `tests/test_h55_nested_metrics_disclosure.py` — 4 failures: pinned count drifts (e.g. 1292 vs 1188 leaves, 631 vs 627 re-derivable counts, 40 vs 36 perturbation gates).
- `tests/test_h53_published_metrics_disclosure.py` — 4 failures: pinned count drifts (58 metrics, 674 values) plus re-derivation mismatches on `benchmark_p_value`.

**No code bug found in any of the 7.** All are frozen-number/pin drifts (or one stale test-scope assertion) requiring evidence-based per-contract review. **No `src/qtr`, runner, test, gate, or frozen-number changes were made.** Working tree clean.

## Next task (BLOCKED on explicit authorization)

Per-contract review of the frozen-contract drifts above (`test_h51_benchmark_container_invariance.py`, `test_h53_published_metrics_disclosure.py`, `test_h55_nested_metrics_disclosure.py`, and the stale scope assertion in `test_engine_total_return_consistency.py`) — each requires authorization before any edit; do not mass-edit to force the suite green.

## Deferred (do not select without authorization)

- Resolve the 3 held-open contested per-trade logs in `tests/test_trade_log_cost_reconciliation.py` — amends the frozen-record disclosure; requires explicit authorization (adding them breaks `test_the_three_pinned_sets_partition_the_record`).
- Select H182 — blocked on the commodity-carry data gap (no free PIT term-structure/roll proxy; yfinance provides only `=F` continuous contracts) or a conclusion that free-data family discovery is exhausted per Cycle 96.

H182 remains unassigned; NF discovery queue exhausted per Cycle 96.