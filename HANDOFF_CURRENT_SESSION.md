# HANDOFF_CURRENT_SESSION.md — Session summary (2026-11-20, Cycle 233)

> **Superseded banner (2026-11-20, Cycle 238):** this doc's "Next task for next agent —
> Execute H189" instruction (lines 63–68) is **stale by 2 hypotheses**. H189 was
> confirmed **data-blocked** in Cycle 234 (SEC XBRL `companyfacts`: CostOfRevenue
> 28/100 and CostOfGoodsSold 29/100 co-reported with Revenues on the same 10-K end,
> both below the 40-name minimum — no executable gross-profitability test exists on this
> source) and H190 was executed/rejected in Cycle 235 (crypto perpetual funding/basis
> cross-section, REJECT 1/8 on Binance public archives). The free-data point-in-time
> strategy-family queue is now **exhausted (H1–H190)**; no H191 is pre-registered. The
> only remaining actionable item is the maintainer-applied workflow contract fix
> (`patches/0001-gates-workflow-contract-fix.patch`), which is agent-unreachable. The
> H188 execution record below (Cycle 233, REJECT 3/8) is durable and unchanged. Historical
> narrative below is preserved.

## Session objective
Execute H188 (NF-20261120-02: net share issuance / external financing) as pre-registered in
HYPOTHESIS_SPEC.md §Cycle 232, following the completion of H187 in Cycle 231.

## What was done

### 1. Created runner: `run_nf_20261120_02_net_share_issuance.py`
- Implements the pre-registered H188 construction exactly
- Features: `net_issuance = shares_t / shares_{t-1} - 1` (short high issuance) and
  `buyback_intensity = buybacks_t / assets_{t-1}` (long high buyback)
- Universe: 91 names (S&P 100 minus 9 measured share-count gaps: ACN, CMCSA, MA, META,
  RTX, SNDK, UPS, V, XOM; BKNG included)
- PIT timing: max `filed` of shares_t, shares_{t-1}, buybacks, assets_t, assets_{t-1}
  then engine `shift(1)`, monthly refresh
- Grid: 16 combos (2 features × entry_z {0.5, 1.0} × k {10, 20} × vol_target {0.10, 0.15})
- Reuses backtest engine, metrics, gates, benchmark constructors, and cross-sectional/
  hysteresis primitives from H187/H186/H184
- New code: `tag_rows_with_units()` for shares-unit tags, `annual_share_observations()`,
  feature-specific `signal_weights()` with pre-registered orientation

### 2. Created tests: `tests/test_nf_20261120_02_net_share_issuance.py`
- 17 tests covering constants, universe, grid, signal formulas, signal orientations,
  hysteresis, collinearity diagnostics, and artifact verification
- All tests pass

### 3. Executed experiment
- Command: `python run_nf_20261120_02_net_share_issuance.py`
- Runtime: 67.2 seconds
- Artifact: `.experiments/nf_runs/nf_20261120_02_net_share_issuance_20261120_075812/`
- Result: **REJECT (3/8 gates passed)**
  - Selected: feature=net_issuance, entry_z=0.5, exit_z=0.0, k=20, vol_target=0.10
  - WF train Sharpe: 0.765
  - OOS Val+Test: Sharpe 0.698, PF 1.126, maxDD −12.43%, trades 14,743,
    worst-regime rolling-252 Sharpe −0.387, total return 0.389
  - Gates PASS: trades (≥50), maxDD (≤15%), WF stability (≥0.7)
  - Gates FAIL: Sharpe (≥1.0), PF (≥1.3), worst-regime (≥0.3),
    benchmark p≤0.05 with IR≥0 (p=0.178, IR=−0.600), OAT perturbation min ratio≥0.5 (−0.668)
  - Benchmark passive equal-weight long book OOS: Sharpe 1.058, total return 0.714
  - Separation from H187: max |ρ| = 0.29 (net_issuance vs asset_growth) — separation holds

### 4. Updated artifact schema pins
- `tests/test_experiment_artifact_schema.py`: `EXPECTED_TOTAL_DIRS = 115`,
  `EXPECTED_SUMMARY_COUNT = 107`, `EXPECTED_DISTINCT_KEYS = 149`
- New keys: `train_input_collinearity_net_issuance_vs_buyback`,
  `train_input_collinearity_vs_h187`
- All 112 artifact schema tests pass

### 5. Updated documentation
- `NEW_FAMILY_RESEARCH_REGISTER.md`: Added Cycle 233 record (H188 executed/rejected)
- `HYPOTHESIS_SPEC.md`: Added H188 execution result section (Cycle 233)
- `AGENTS.md`: Updated stale H-range claim to H1–H188 exhausted/rejected
- `HANDOFF_NEXT.md`: Updated with current state and next task (H189 or conclude exhaustion)

## Verification
- All new tests pass (17 + 112 + 146 = 275 tests)
- Key contract tests pass (426 passed, 47 skipped)
- Lint: `ruff check` clean
- Format: `ruff format --check` clean (358 files)

## Next task for next agent
Execute H189 (NF-20261120-03: gross profitability) — currently deferred for data thinness
(`CostOfRevenue` only 31/99 names). Requires finding a different measured cost tag and
pre-registering with mechanism-separation argument against H187/H188.

If H189 remains blocked, conclude free-data point-in-time family discovery is exhausted
(H1–H188 all executed/rejected on SEC XBRL) and shift to auditing/infrastructure.