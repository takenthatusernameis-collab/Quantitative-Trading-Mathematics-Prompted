# Handoff — Current Session: test-logic bug fixed (1 file, 1 test method)

## What changed

Fixed one **test-logic bug** (not a frozen-number drift) in
`tests/test_engine_total_return_consistency.py:344`.

`TestRemainingDisclosures::test_no_runner_selects_on_the_engines_total_return`
used a broad fallback — flagging every runner whose source contained the
string `"total_return"` — as the tripwire for "no runner reads the engine's
`metrics["total_return"]`. The two explicit assertions above it
(`'metrics["total_return"]' not in source` / `"metrics['total_return']"`
not in source) already covered the contract exactly, so the broad fallback
was a **false positive**: 33 NF runners publish a runner-local `total_return`
scalar (computed from their own equity curve, e.g.
`eq.iloc[-1] / eq.iloc[0] - 1` or `eq.iloc[-1] - 1`) for disclosure, and **none
of them reads the engine's metric**. The metric is therefore not load-bearing
for any published number.

- Removed the broad `"total_return" not in source` fallback and the
  `offenders` list it populated.
- Added `test_negative_control_the_metric_read_is_detected` so the source scan
  is not vacuous (a runner that *does* read `metrics["total_return"]` must be
  flagged; a runner that only mentions `total_return` as a local variable is
  not).
- Documented the 33-runner local-total_return disclosure in the module
  docstring (§H53 re-derives each published value from its frozen artifact,
  so the local value is pinned there, not here).

No `src/qtr`, runner, gate, threshold, or frozen-number change.

## Actually verified (this session)

- `python -m ruff check tests/test_engine_total_return_consistency.py` — clean.
- `python -m ruff format --check tests/test_engine_total_return_consistency.py` — 1 file reformatted, then clean.
- `PYTHONPATH=src pytest -q tests/test_engine_total_return_consistency.py` — **16 passed** (was 1 failed / 15 passed).
- Evidence that the 33 flagged runners are false positives: `grep -rn 'metrics\[.total_return\|metrics\[.total_return.' run_*.py` → no matches; every one of the 33 computes a local `total_return` (verified in 3 samples; AST scan confirms no runner both imports `qtr.backtest` and references `total_return` except the two exempted ones).
- Frozen-contract modules re-run (unchanged set of pre-existing failures):
  `tests/test_h51_benchmark_container_invariance.py tests/test_h53_published_metrics_disclosure.py tests/test_h55_nested_metrics_disclosure.py tests/test_gate_vacuity_contract.py tests/test_engine_total_return_consistency.py tests/test_trade_log_cost_reconciliation.py` — **11 failed, 345 passed, 12 skipped** (was 12 failed before this fix; the engine module's 1 failure is gone and no new failure appeared).

## Unresolved / pre-existing failures (do not mass-fix)

All remaining failures are frozen-number drifts, stale test recipes, or held-open
disclosure items requiring explicit authorization per-contract:

1. `test_h51_benchmark_container_invariance.py::test_every_published_information_ratio_is_disclosed` — 21 new IR-publishing experiments not in the pinned `PUBLISHED_INFORMATION_RATIOS` set.
2. `test_h53_published_metrics_disclosure.py` — 4 failures: pinned counts drifted (58 vs 54 summaries; 674 vs 630 values); `test_every_published_value_re_derives` flags 3 H92 artifacts (`exp_2026-11-06T02-17-43-039138Z`, `03-36-48-479398Z`, `04-23-47-511988Z`) whose published `benchmark_p_value = 0.005822770948177806` is re-derived as `1.0` because the recipe still carries `bench_p_published_default=True` for `nf_20261105_10_equity_bond_relmom`.
3. `test_h55_nested_metrics_disclosure.py` — 4 failures: pinned counts drifted (ablations 48 vs 44, perturbation 28 vs 24, leaves 1292 vs 1188, re-derived 631 vs 627, perturbation gates 40 vs 36).
4. `test_trade_log_cost_reconciliation.py::TestFrozenRecordScope` — 2 failed: 3 contested per-trade `exp_2026-11-05` logs (`exp_2026-11-05T01-17-49-208916Z`, `01-24-02-934356Z`, `18-09-06-924039Z`) no longer carry the pre-fix attribution; adding them to `TRADE_LOG_RECORD` breaks `test_the_three_pinned_sets_partition_the_record`. Held-open pending explicit authorization.

## Failed approaches / do not blindly repeat

- Do not mass-edit runners/tests/gates to force the suite green. Each frozen-contract failure requires evidence-based per-contract review and authorization.
- Do not add the 3 contested per-trade logs to `TRADE_LOG_RECORD` — breaks the partition test; requires explicit authorization.
- Do not weaken the engine total-return contract; the 33-runner local-total_return disclosure is pinned in §H53, not in this module.

## Next task

**One precise next task:** the 3 H92 `benchmark_p_value` mismatches in
`test_h53_published_metrics_disclosure.py` are the only remaining
*test-recipe* failures rather than frozen-number drifts. Investigate whether
the H92 runner's `bench_p_published_default=True` recipe flag is genuinely
stale for the 3 newer artifacts (published 0.0058 vs re-derived 1.0) — i.e.
whether the runner's `cmp.get("alpha_p_value", 1.0)` path is the correct one
and the recipe flag should be removed or narrowed to the older artifacts only.
If a recipe fix is evidenced, apply it with the same minimal approach
(flag correction only — no number/gate/threshold changes) and re-run the
focused module. If no fix is evidenced, document it as a genuine frozen-record
item requiring authorization.

**Blocked alternatives:** resolve the 3 contested per-trade logs (authorization);
update pinned counts in H51/H53/H55 (authorization); select H182 (commodity-carry
data gap, or conclude free-data family discovery is exhausted per Cycle 96).