# HANDOFF_SESSION_END — H68 complete (zero-volatility was booked as a SHORT)

## What changed

- `src/qtr/strategies/baselines.py` — `mean_reversion_signals`'s long/short leg
  booked a constant price series as a SHORT. Both legs now require
  `rolling_std > 0`; the long-only branch gained the same guard for symmetry.
  Bit-identical on every panel with positive realized volatility (measured:
  max abs diff 0.0, both branches, 400-bar random panels).
- `tests/test_baselines.py` — **4 tests added** (26, was 22):
  `TestZeroVolatilityIsNotAShort`.

No published artifact, gate threshold, verdict or certified number was changed;
no grid was re-run; no hypothesis was added.

## What was actually verified

- The new tests **fail on the pre-fix code** (reverted source: 3 of 4 fail; the
  long-only one passes because that branch was already correct), then pass with
  the fix.
- `python -m pytest -q -W error` → **2101 passed, 16 skipped** (was 2097; +4).
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` →
  `src/qtr` **1112 statements, 342 branches, 0 missed, 0 partial, 100.00%**
  (unchanged).
- `python -m ruff check src tests run_*.py` → *All checks passed!*;
  `python -m ruff format --check src tests run_*.py` → **103 files already
  formatted**.
- Pinned contracts re-run: **970 passed, 1 skipped** across
  `test_engine_metric_agreement`, `test_h53_published_metrics_disclosure`,
  `test_h54_non_metrics_block_disclosure`, `test_h55_nested_metrics_disclosure`,
  `test_h56_stats_json_echoes`, `test_h57_total_return_audit`,
  `test_h58_price_pathology_contamination`,
  `test_h59_contamination_gate_blast_radius`,
  `test_runner_causality_inventory`, `test_runner_metric_agreement`,
  `test_benchmark_gate_contract`, `test_public_api_contract`,
  `test_ruff_reproducibility`, `test_trade_log_cost_reconciliation`,
  `test_tsmom_signal`, `test_causality_invariant`.

## What remains unresolved

- All remaining items in `FINAL_REPORT.md` §H53–§H61 are **disclosed, not
  quantified** (missing committed inputs/convention differences/benchmarks/trade
  logs/signals). No gates read them; cannot quantify from committed record.
  H1–H30 exhausted; H35–H68 complete.
- Thirteen H58/H59 gate booleans remain as published (all REJECT families). No
  published artifact, gate threshold, verdict, or certified number may be
  modified.

## Which approaches have already failed and why

- Scanning only the pinned contract tests first would have reported everything
  green and missed the gap: `mean_reversion_signals` is only exercised by
  `test_baselines.py`/`test_baselines_extra.py` with random-walk and
  short-history panels whose rolling std is always strictly positive, and the
  one long/short test only asserts the bounds `[-1, 1]`, which a full short
  satisfies. The gap was found by feeding a perfectly flat price panel to each
  strategy function in turn and observing which one produced a non-zero
  position on a zero-information input.
- A mixed-panel test with a monotone trend as the trading symbol first failed
  (`TREND` produced no trades): a trend never crosses its own 2-sigma band, so
  it is not a valid mean-reversion fixture. The trading symbol was replaced with
  a high-volatility random walk, which does cross its band.

## One precise next task

**None assigned.** If work is desired: wait for newly committed artifacts that
make any disclosed §H53–§H61 value measurable. If any change is made under
`src/qtr/` or affecting runners/validation, re-run pinned contracts
(`test_engine_metric_agreement`, `test_h53_published_metrics_disclosure`,
`test_h54_non_metrics_block_disclosure`, `test_h55_nested_metrics_disclosure`,
`test_h56_stats_json_echoes`, `test_h57_total_return_audit`,
`test_h58_price_pathology_contamination`,
`test_h59_contamination_gate_blast_radius`,
`test_runner_causality_inventory`, `test_runner_metric_agreement`,
`test_benchmark_gate_contract`, `test_public_api_contract`,
`test_ruff_reproducibility`, `test_trade_log_cost_reconciliation`,
`test_tsmom_signal`, `test_causality_invariant`) plus full suite with
`-W error`, keep `src/qtr` coverage at 100% (statement+branch), keep ruff
lint/format clean. Preserve published artifacts/gates/thresholds/verdicts/
certified numbers; do not re-run grids; respect API contract in
`tests/test_public_api_contract.py`.

(End of file - total 29 lines)