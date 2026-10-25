# Next Task

## State

H35–H68 complete. **No hypothesis work is assigned** — every remaining
unresolved item in `FINAL_REPORT.md` (§H53–§H61) is a value that is not a
function of the committed record (missing inputs, disclosed convention
differences, or benchmarks/trade logs/signals never committed). None can be
implemented or verified from this checkout; they stay disclosed, not
quantified, and no gate reads any of them.

## What changed (this session — H68: zero volatility booked as a SHORT)

- `src/qtr/strategies/baselines.py` — `mean_reversion_signals`'s long/short leg
  was `signal[price >= upper] = -1.0` with no guard on the realized
  volatility. When the rolling std is zero the bands collapse to the mean and
  every bar is simultaneously at, below and above them, so a constant price
  series was booked as a SHORT and held through the forward fill -- a
  zero-volatility symbol in a long/short book carried a full `-1.0` short
  weight. Both legs now require `rolling_std > 0`. The long-only branch was
  already self-cancelling on this input but gained the same guard for
  symmetry. On any panel with positive realized volatility the masks are
  bit-identical to the old ones (measured: max abs diff 0.0, both branches,
  400-bar random panels).
- `tests/test_baselines.py` — **4 tests added** (26, was 22): a
  `TestZeroVolatilityIsNotAShort` class with a perfectly-flat fixture
  (rolling std exactly zero after warmup), pinning zero-volatility => zero
  weight in long/short and long-only, a mixed-panel test that a flat symbol
  stays flat alongside a trading one, and a behavioural negative control
  reconstructing the pre-fix `price >= upper => -1` mapping.

- `python -m pytest -q -W error` → **2101 passed, 16 skipped** (was 2097; +4).
- `python -m pytest -q --cov=qtr --cov-branch` → `src/qtr` **1112 statements,
  342 branches, 0 missed, 0 partial, 100.00%** (unchanged).
- `python -m ruff check src tests run_*.py` → *All checks passed!*;
  `python -m ruff format --check src tests run_*.py` → **103 files already
  formatted**.
- Pinned contracts re-run: 970 passed across `test_engine_metric_agreement`,
  `test_h53_*`, `test_h54_*`, `test_h55_*`, `test_h56_*`, `test_h57_*`,
  `test_h58_*`, `test_h59_*`, `test_runner_causality_inventory`,
  `test_runner_metric_agreement`, `test_benchmark_gate_contract`,
  `test_public_api_contract`, `test_ruff_reproducibility`,
  `test_trade_log_cost_reconciliation`, `test_tsmom_signal`,
  `test_causality_invariant`.

## One precise next task

**None assigned.** The quick-start surface verification from a fresh venv
(`pip install -r requirements.txt` only) is complete and green in prior
sessions. Options if further work is desired:
(a) wait for newly committed artifacts that make any disclosed §H53–§H61
value measurable; or
(b) baseline hygiene — after any change under `src/qtr` or affecting
runners/validation, re-run the pinned contracts
(`test_engine_metric_agreement.py`, `test_h53_published_metrics_disclosure`,
`test_h54_non_metrics_block_disclosure`, `test_h55_nested_metrics_disclosure`,
`test_h56_stats_json_echoes`, `test_h57_total_return_audit`,
`test_h58_price_pathology_contamination`,
`test_h59_containment_gate_blast_radius`,
`test_runner_causality_inventory`, `test_runner_metric_agreement`,
`test_benchmark_gate_contract`, `test_public_api_contract`,
`test_ruff_reproducibility`, `test_trade_log_cost_reconciliation`,
`test_tsmom_signal`, `test_causality_invariant`) and confirm
`python -m pytest -q --cov=qtr --cov-branch` keeps `src/qtr` at 100% with
gates green; keep the ruff lint/format gates clean.

## Constraints carried forward

- No published artifact, gate threshold, verdict or certified number may be
  modified. No grid may be re-run; the H1–H30 hypothesis space remains
  exhausted.
- `src/qtr` coverage gate must stay at 100% (statement + branch).
- Ruff lint (`python -m ruff check src tests run_*.py`) and format
  (`python -m ruff format --check src tests run_*.py`) gates must stay clean.
- Re-run `tests/test_runner_causality_inventory.py`,
  `tests/test_runner_metric_agreement.py` and `tests/test_benchmark_gate_contract.py`
  after any change in a runner or under `src/qtr/validation`.

(End of file - total 77 lines)