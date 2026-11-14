# Backtest Engine Performance Profiling Results

**Date:** 2026-11-12
**Session:** Infrastructure Auditing per STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §6 fallback path
**Script:** `run_backtest_perf_profile.py`
**Output:** `.experiments/backtest_perf_profile.csv`

## Summary

Executed comprehensive performance profiling of the vectorized backtest engine across varying universe sizes, time periods, and asset classes. This addresses the fallback audit work item: "Performance profiling of backtest engine on large universes."

## Key Findings

### Scaling Behavior (Equity, Long-Only, 1 Year Daily)

| Symbols | Bars | Time (s) | Peak Memory (MB) | Trades |
|---------|------|----------|------------------|--------|
| 1       | 252  | 0.053    | 0.3              | 193    |
| 5       | 252  | 0.113    | 0.5              | 477    |
| 10      | 252  | 0.225    | 1.0              | 1,172  |
| 20      | 252  | 0.499    | 2.3              | 2,788  |
| 50      | 252  | 1.263    | 5.8              | 7,401  |
| 100     | 252  | 2.536    | 11.5             | 14,788 |
| 200     | 252  | 4.928    | 22.2             | 28,645 |
| 500     | 252  | 11.591   | 52.1             | 67,077 |

**Linear fit:** `time = 0.0232 * symbols + 0.077` (R² ≈ 0.999)
**Memory fit:** Roughly linear at ~0.1 MB per symbol per 252 bars

### Time Scaling (Fixed 50 Symbols)

| Bars (Years) | Time (s) | Peak Memory (MB) |
|--------------|----------|------------------|
| 252 (1yr)    | 1.26     | 5.8              |
| 1,260 (5yr)  | 5.63     | 24.9             |
| 2,520 (10yr) | 10.30    | 45.8             |

Time scales linearly with bars (O(n_bars)). Memory scales linearly with both symbols and bars.

### Asset Class Comparison (50 symbols, 252 bars)

| Asset Class | Allow Short | Max Lev | Time (s) | Memory (MB) |
|-------------|-------------|---------|----------|-------------|
| Equity (long-only) | False | 1.0 | 1.26 | 5.8 |
| Equity (long-short) | True | 2.0 | 2.04 | 9.3 |
| Futures | True | 10.0 | 2.02 | 9.1 |
| Crypto | True | 1.0 | 1.97 | 8.0 |

All asset classes show similar O(n_symbols * n_bars) scaling. Futures and crypto have slightly higher per-symbol overhead due to contract-based cost calculations.

### Configuration Impact

- **Long-short vs Long-only:** ~1.6x slower due to doubled trade count and leverage normalization
- **Higher leverage:** Increases computation via gross-leverage normalization pass
- **Impact cost model:** Adds O(n_symbols * n_bars) participation rate calculation

## Conclusions

1. **Engine is production-ready at measured scales:** the largest measured cell,
   200 symbols × 5 years (1,260 bars), completes in **21.3s** with **93.9MB** peak
   memory. The matrix does not measure 500 symbols × 10 years; linear extrapolation
   from the fitted model is ~117s and ~521MB, so that cell should be measured before
   it is claimed.

2. **Linear scaling confirmed:** Both time and memory scale linearly with symbols × bars. No quadratic bottlenecks detected.

3. **Memory efficient at measured scales:** peak memory stays under 100MB for every
   measured cell up to 200 symbols × 5 years (93.9MB). Memory scales linearly with
   symbols × bars, so extrapolating to 500 symbols × 10 years implies ~521MB; measure
   that cell rather than asserting a bound.

4. **Cost model overhead is minimal:** Equity impact cost model adds ~10-15% overhead vs base cost model.

5. **No regressions in the core suite:** the 359 core tests pass, lint clean, format clean.
*Current full-suite status (re-verified 2026-11-14, Cycle 105):* **3,744 passed, 51 skipped, 7
   failed** — the 7 are exclusively the maintainer-gated `tests/test_gates_workflow.py`
   contract block (documented in `NEXT_TASK.md`).

## Files Created

- `run_backtest_perf_profile.py` - Profiling script (linted, formatted, tested)
- `.experiments/backtest_perf_profile.csv` - Raw benchmark data (33 rows)

## Verification

- ✅ `python -m ruff check src tests run_*.py scripts` — All checks passed (327 files)
- ✅ `python -m ruff format --check src tests run_*.py scripts` — 327 files already formatted
- ✅ `python -m pytest tests/test_backtest_engine.py tests/test_config.py tests/test_cost_model.py tests/test_statistics.py tests/test_data_fetcher.py -q` — 359 passed

## Fallback Items Status

1. **Stress-test engine/gate edge cases** — done: `tests/test_engine_edge_stress.py`
   (12 passed) pins NaN prices, zero/extreme leverage, zero-volume/degenerate
   futures, and the bar-0 look-ahead boundary.
2. **Document experiment lineage** — done: `scripts/generate_experiment_lineage_report.py`, `EXPERIMENT_LINEAGE_REPORT.md`.
3. **CI/CD hardening** — done: `scripts/backtest_perf_regression_gate.py` (performance regression gate).

---
*Generated as part of infrastructure auditing per STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §6 fallback path.*
