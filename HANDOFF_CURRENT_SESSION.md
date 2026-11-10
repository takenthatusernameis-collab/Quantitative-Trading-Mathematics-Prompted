# HANDOFF — Current Session: NF runner KeyError bug fixed (7 runners, 10 lines)

## What changed

Fixed a `KeyError: 'alpha_p_value'` code bug in 7 NF experiment runners. Each runner's `evaluate_gates` accessed `bench["alpha_p_value"]`, but the `bench` dict (built by `compare_to_benchmark` → stored as `"p_value"` in `bench_out`, or by custom `benchmark_cmp` → returned as `"p_value"`) carries the p-value under key `"p_value"`, not `"alpha_p_value"`. The `benchmark_significance_gate()` function in `src/qtr/validation/statistics.py:799` takes `p_value` as its parameter name.

Files fixed (one key per file; 2 keys in 3 files):
- `run_nf_20261107_04_amihud_illiq.py` — line 348 (`evaluate_gates`) + line 507 (artifact output `bench_out["alpha_p_value"]` → `bench_out["p_value"]`)
- `run_nf_20261107_07_realized_semivariance.py` — line 356 + line 515
- `run_nf_20261107_08_vix9d_fear_spread.py` — line 342 + line 501
- `run_nf_20261107_10_vix_move_spread.py` — line 336
- `run_nf_20261107_13_gvz_vix_spread.py` — line 368
- `run_nf_20261107_15_gld_tlt_corr.py` — line 356
- `run_nf_20261107_28_realized_skewness_stress.py` — line 354

No `src/qtr` changes. No test changes. No frozen-number/gate/threshold changes.

## Actually verified (this session)

- `python -m ruff check <7 runners>` — clean
- `python -m ruff format --check <7 runners>` — clean (already formatted)
- `PYTHONPATH=src pytest -q tests/test_nf_20261107_{03,04,07,08,10,13,15,28}_*.py` — **87 passed** (was 10 failing with KeyError across files 04/07/08/10/13; files 03/15/28 already passed their unit tests but had the same latent crash-on-execution bug)
- `grep -rn 'bench["alpha_p_value"]' run_nf_*.py` — no matches (bug fully eradicated)

## Unresolved / pre-existing failures (do not mass-fix)

Per `HANDOFF_CURRENT_SESSION.md` prior state, the following remain:
1. `tests/test_trade_log_cost_reconciliation.py::TestFrozenRecordScope` — 2 failed (3 contested per-trade `exp_2026-11-05` logs, held-open pending explicit authorization)
2. `tests/test_h57_total_return_audit.py` — 1 failed (runners selecting on engine total-return column)
3. `tests/test_h55_nested_metrics_disclosure.py` — 4 failed (pinned counts drifted)
4. `tests/test_h53_published_metrics_disclosure.py` — 4 failed (pinned counts 58/674)
5. `tests/test_h51_benchmark_container_invariance.py` — 1 failed (published information-ratio disclosure set mismatch)
6. `tests/test_gate_vacuity_contract.py` — 1 failed (non-evaluating gates set mismatch)
7. `tests/test_engine_total_return_consistency.py` — 1 failed (runners selecting on engine total return)

All involve frozen published numbers/gates/pins; per AGENTS.md they require evidence-based per-contract review. Do not mass-edit.

## Failed approaches / do not blindly repeat

- Do not add the 3 contested per-trade logs to `TRADE_LOG_RECORD` — breaks `test_the_three_pinned_sets_partition_the_record`; requires explicit authorization.
- Do not mass-edit runners/tests/gates to force the suite green.
- New-family discovery queue H85–H181 is exhausted (Cycle 96); H182 unassigned; no feasible H182 candidate without resolving a data gap (commodity carry blocked: no free PIT term-structure/roll proxy — verified yfinance provides only `=F` continuous contracts, no individual contract months).

## Next task

**One precise next task:** Investigate whether any of the remaining 7 frozen-contract failures (items 2–7 above) are actually code bugs like the `KeyError` just fixed, rather than frozen-number drifts. Start with `test_h57_total_return_audit.py` and `test_engine_total_return_consistency.py` (both mention "runners selecting on engine total-return column") — inspect whether runners access a wrong/missing column key, analogous to the `alpha_p_value`/`p_value` key mismatch fixed here. If a code bug is found, fix it with the same minimal approach (key-name correction, no number/gate changes). If no code bug is found, document it as a genuine frozen-number drift requiring per-contract review authorization.

**Blocked alternative:** Resolve the 3 contested per-trade logs in `test_trade_log_cost_reconciliation.py` — requires explicit authorization to amend the frozen-record disclosure.

**Blocked alternative:** Select H182 — requires resolving a data gap (commodity carry term-structure/roll data) under explicit authorization, or concluding free-data family discovery is exhausted per Cycle 96.