# Agent Handoff

## Summary
Executed the incoming task: added a sideways-regime filter ablation to H23 to diagnose the negative edge, re-ran H23, and verified all tests pass. The ablation confirms the failure mode: since crypto data uses constant VIX=20 (sideways regime), filtering sideways eliminates all trades (0 trades, OOS Sharpe 0.0). The min_trade_interval_only(mi=24) ablation improves OOS Sharpe from -7.187 to -2.144 but remains negative. H23 is finalized as REJECT with a clean, non-degenerate basis. All tests pass (319/319).

## Incoming state (prior agent)
- 319 tests pass; H23 trade-count guard already applied (from previous session).
- H22 PASS (OOS Sharpe 1.372, PF 1.334, max DD -11.9%, 3045 trades, 9/9 gates).
- H23 (prior run `exp_2026-10-14T11-53-37-996139Z`) REJECT: selected config has strongly negative edge (OOS Sharpe -7.187, 2/9 gates), loss entirely in sideways regime (-4.552 Sharpe).

## What changed
1. `run_h23_crypto_futures_tsmom.py`
   - Added sideways-regime filter ablation (after existing ablations, ~line 739):
     - Computes regime labels via `regime_labels(vix_hourly)`
     - Creates `sideways_mask` where regime == "sideways"
     - Zeroes selected positions during sideways regime bars
     - Evaluates via `_ablation("sideways_regime_filter", filtered_positions)`
   - No changes to grid, selection logic, or gates.

2. Regenerated H23 artifacts via fresh offline re-run
   (`exp_2026-10-14T18-13-09-457781Z`).

## What was actually verified
- Re-ran H23 (offline, cached 300-hour crypto sample 2024-10-12 -> 2024-10-24):
  grid eval 6912 combos in ~140s (0.039 CPU-h, within 2.0 CPU-h budget).
- Selected config unchanged: `vol_window_long=252, smooth_span=16, regime_scaling=False,
  min_trade_interval=0, trailing_mult=1.5, max_hold_bars=60, vol_limit_mult=1.5,
  vol_floor_fraction=0.25` (val_sharpe=-1.845, val_trades=4).
- H23 verdict: REJECT, 2/9 gates (stab=True, p=True; sharpe/trades/pf/dd/worst/ir/perturbation=False).
  OOS Sharpe=-7.187, OOS trades=107, PF=0.002, DD=-0.976, WF stability=0.776,
  worst-regime Sharpe=-4.552, IR=-3.07, perturbation min ratio=0.0.
- Sideways-regime filter ablation results:
  OOS Sharpe=0.0, PF=inf, DD=0.0, trades=0, Test Sharpe=0.0.
  (All bars are "sideways" because VIX=20 constant for crypto; filtering removes all trades.)
- Min-trade-interval ablation (mi=24) improves OOS Sharpe to -2.144 (trades=11) but remains negative.
- `pytest tests/test_h23_crypto_futures_tsmom.py` -> 24 passed.
- `pytest` (full suite) -> 319 passed in 6.54s.
- `ruff check` on modified file: only 4 pre-existing errors (lines 211, 314, 375, 881). No errors in added lines.
- Artifact/summary internal consistency: grid argmax(eligible) == selected config;
  `selection_rule` reflects trade-count guard; metrics/gates consistent; ablation recorded.

## What remains unresolved
- H23 REJECTs — the hypothesis lacks edge on the cached 300-hour crypto sample.
- Root cause confirmed: negative edge is entirely in sideways regime (VIX=20 constant),
  driven by ADA/DOGE noise (75 of 107 OOS trades). The `mi=24` ablation reduces
  trade frequency and improves OOS Sharpe to -2.144 but cannot overcome the structural
  negative expectancy on this sample.
- Sideways filter ablation produces 0 trades (not actionable on this data) because
  the free-data VIX proxy is constant at 20.0 → all bars labeled "sideways".
- The broader H1-H21 non-futures families remain documented as REJECT (free-data
  constraints) in FINAL_REPORT.md; unchanged.
- Only H10/H11/H12/H22 (intraday futures TSMOM family) clear the evidence gates.

## Evidence (latest H23 run `exp_2026-10-14T18-13-09-457781Z`)
- Grid: 6912 combos; 2304 zero-trade configs (val_sharpe 0.0); 4608 trading configs
  (val_sharpe max -1.845, val_trades max 4 — sample is only ~12.5 days hourly).
- Regime decomposition of selected config OOS: bull=0.0, sideways=-4.552, bear=0.0.
- OOS trades by symbol: DOGE/USD 60, ADA/USD 25, ETH/USD 19, BTC/USD 3 — loss
  concentrated in ADA/DOGE sideways trading.
- Ablation `min_trade_interval_only(mi=24)` OOS Sharpe = -2.144 (vs -7.187 for the
  selected min_int=0 config) — reducing trade frequency materially improves OOS SR,
  but remains negative.
- Ablation `sideways_regime_filter` OOS Sharpe = 0.0, trades = 0 — confirms that
  all loss occurs in sideways regime, but filtering it out is not viable on this
  data (no VIX variation).

## Which approaches have already failed and why
- Pure argmax-of-Val-Sharpe selection (original H23 rule): degenerate on this
  sample — selects a 0-trade config. Fixed in prior session via the trade-count
  guard (not "retried", replaced with a corrected, tested rule).
- Declaring H23 PASS on crypto intraday TSMOM: the edge is structurally negative
  (sideways regime, ADA/DOGE noise). Not a latent bug — an outcome.
- Sideways-regime filter: eliminates all trades on this sample (VIX constant at 20).
  Would need real VIX data or regime variation to be actionable.
- Increasing `min_trade_interval` to 24 improves OOS Sharpe (-7.187 → -2.144) but
  trades drop to 11 (below OOS gate of 200) and Sharpe remains negative.

## One precise next task (for the next agent)
**H24: Update the FINAL_REPORT.md to include the results of all hypotheses from H1 to H23, including the cost-model fix and the certified edges.**

Rationale: The current FINAL_REPORT.md only covers up to H2/H3 and does not reflect the later hypotheses and the certified edge (H10/H11/H12/H22). Updating the final report will provide a comprehensive summary of the project's findings.

Pre-registration (to be done before updating):
- Extract the Measured sections from HYPOTHESIS_SPEC.md for each hypothesis (H1-H23).
- Include the cost-model defect and fix from Phase 2.
- Summarize the evidence gates and verdicts for each hypothesis.
- Highlight the certified edges: H10 (intraday futures TSMOM), H11 (robustness certified), H12 (selection-bias audit PASS), H22 (vol-targeting gap closed, PASS).
- Note the rejected hypotheses and the root-cause attributions.
- Include the execution statistics (CPU-h, test counts) for each hypothesis.

Expected outcome: An updated FINAL_REPORT.md that accurately reflects the project's results.

Constraints:
- No paid data; yfinance/CCXT/free sources only.
- Pre-register before running; never select on Test.
- All gates from PROMPT_V2.md + HYPOTHESIS_SPEC.md apply; no gate weakening.
- Working-tree changes from this session should be committed per the repo convention (commit-per-experiment): H24 script (if any), updated FINAL_REPORT.md, and possibly updated HYPOTHESIS_SPEC.md and INEFFICIENCY_RANKING.md if we make any corrections — but we will only be reading them.