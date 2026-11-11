# HANDOFF — Current Session: NF static-contract code bug fixed (4 runners)

## What changed

Fixed a code bug surfaced by `tests/test_benchmark_gate_contract.py::test_every_call_site_reads_only_keys_the_library_returns` in 4 NF experiment runners. Each runner's `evaluate_gates` has a parameter named `bench` that reads `bench["p_value"]`/`bench["information_ratio"]`, while the same module also contains `bench = compare_to_benchmark(...)`. The library key set pinned by that test (compare_to_benchmark returns `alpha_p_value`, not `p_value`) means `p_value` is not a key the library returns — the flow-insensitive AST contract check conflated the gate parameter with the library-result assignment and flagged it as a vacuous-gate class defect (H4/H7/H18).

Files fixed (signature + gate reads; runtime behavior unchanged — callers pass `bench_out`, a runner-owned dict that carries `p_value`):
- `run_nf_20261107_03_spy_ts_reversal.py` (`evaluate_gates`)
- `run_nf_20261107_04_amihud_illiq.py` (`evaluate_gates`)
- `run_nf_20261107_07_realized_semivariance.py` (`evaluate_gates`)
- `run_nf_20261107_08_vix9d_fear_spread.py` (`evaluate_gates`)

No `src/qtr` changes. No test changes. No frozen-number/gate/threshold changes. No commit/push.

## Actually verified (this session)

- `python -m ruff check <4 runners>` — clean; `python -m ruff format --check <4 runners>` — clean (4 over-length signatures reformatted by ruff).
- `PYTHONPATH=src python -m pytest tests/test_benchmark_gate_contract.py` — **26 passed**; `test_every_call_site_reads_only_keys_the_library_returns` now passes.
- Full suite — **3425 passed, 9 failed, 16 skipped** (was 10 failed / 3424 passed before the fix).

## Unresolved / pre-existing (require authorization, do not mass-fix)

1. `test_h51_benchmark_container_invariance.py::test_every_published_information_ratio_is_disclosed` — IR disclosure set drifted.
2-3. `test_h53_published_metrics_disclosure.py` — pinned counts: 58 vs 54 summaries; 674 vs 630 values.
4-7. `test_h55_nested_metrics_disclosure.py` — nested-block set drifted; leaf count 1292 vs 1188; rederivable count 631 vs 627; perturbation gate 40 vs 36.
8-9. `test_trade_log_cost_reconciliation.py::TestFrozenRecordScope` — 3 contested `exp_2026-11-05` per-trade logs (`exp_2026-11-05T01-17-49-208916Z`, `01-24-02-934356Z`, `18-09-06-924039Z`) + H28 causal-recertification logs; adding them breaks the pinned-record partition.

All involve frozen published numbers/gates/pins; per AGENTS.md they require evidence-based per-contract review. Do not mass-edit.

## Approaches that failed / do not blindly repeat

- Do not update frozen counts in h51/h53/h55 without authorization — frozen-number drifts.
- Do not add the 3 contested per-trade logs to `TRADE_LOG_RECORD` — breaks `test_the_three_pinned_sets_partition_the_record`.
- Do not change runner keys (`p_value` vs `alpha_p_value`) to silence the static contract — the reads are correct on the objects actually passed; the fix was the parameter-name collision, not a key change.
- Do not mass-edit runners/tests/gates to force the suite green.

## Next task

**One precise next task:** Await authorization to (a) resolve the 9 frozen-contract drifts above via per-contract evidence review, or (b) resolve a free-data gap under explicit authorization (commodity carry roll/contango; PIT insider/earnings/options data) and select H182. Per `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 96) and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6, H1–H181 are all executed and rejected and the free-data point-in-time family queue is exhausted; absent a data-gap resolution, conclude free-data family discovery is exhausted and shift to auditing/infrastructure rather than inventing candidates. Constraints: `src/qtr` unchanged unless an evidenced defect requires it (then rerun pinned full gates); no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modified; no commit/push unless explicitly requested.
