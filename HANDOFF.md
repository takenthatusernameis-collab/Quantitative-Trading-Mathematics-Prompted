# Agent Handoff

## Summary
Executed the incoming task: added an in-sample trade-count guard to H23's
Val Sharpe selection to eliminate the degenerate zero-trade config selection,
re-ran H23, and updated tests to match the intentionally-modified selection rule.
All tests pass (319/319).

## Incoming state (prior agent)
- 318 tests pass; no source code modifications (only `__pycache__` artifacts).
- H22 PASS (OOS Sharpe 1.372, PF 1.334, max DD -11.9%, 3045 trades, 9/9 gates).
- H23 (prior run `exp_2026-10-14T10-04-52`) REJECT: selected a zero-trade config
  (val_sharpe 0.0, OOS Sharpe 0.0, 0 trades) because the pure argmax of Val Sharpe
  fell on the 2304 degenerate zero-trade configs (Val Sharpe 0.0), which beat every
  live-trading config (Val Sharpe max ~ -1.85).

## What changed
1. `run_h23_crypto_futures_tsmom.py`
   - Added `MIN_VAL_TRADES_FOR_SELECTION = 1` (after `GATES`), with a comment
     documenting the post-mortem rationale.
   - Guarded the `best_by_sharpe` update so a config is only a Sharpe candidate
     when `vm["trades"] >= MIN_VAL_TRADES_FOR_SELECTION` (i.e. it actually traded
     in-sample).
   - Updated the logged `selection_rule` string to:
     `"best Val Sharpe among configs with >= 1 Val trade(s); Test protected ...;
     gates on OOS Val+Test"`.
   - `best_by_pf` logic left unchanged (already excludes `inf` PF = zero-trade).
2. `tests/test_h23_crypto_futures_tsmom.py`
   - Updated `test_select_on_val_only` to take the argmax of `val_sharpe` only over
     in-sample-trading configs (`val_trades >= MIN_VAL_TRADES_FOR_SELECTION`),
     matching the modified, intentionally-tuned rule.
   - Added `test_selection_excludes_zero_trade_configs`: locks the robustness fix —
     the selected config's grid row must have `val_trades >= threshold`, and the
     pure (unfiltered) argmax must not be selected when it is a zero-trade config.
3. Regenerated H23 artifacts via a fresh offline re-run
   (`exp_2026-10-14T11-53-37-996139Z`).

## What was actually verified
- Re-ran H23 (offline, cached 300-row crypto sample 2024-10-12 -> 2024-10-24):
  grid eval 6912 combos in ~128s (0.038 CPU-h, within the 2.0 CPU-h budget).
- New selected config: `vol_window_long=252, smooth_span=16, regime_scaling=False,
  min_trade_interval=0, trailing_mult=1.5, max_hold_bars=60, vol_limit_mult=1.5,
  vol_floor_fraction=0.25` — the best *trading* config (val_sharpe=-1.845,
  val_trades=4). No longer the degenerate zero-trade argmax.
- New H23 verdict: REJECT, 2/9 gates (stab=True, p=True; sharpe/trades/pf/dd/
  worst/ir/perturbation=False). OOS Sharpe=-7.187, OOS trades=107, PF=0.002,
  DD=-0.976, WF stability=0.776, worst-regime Sharpe=-4.552, IR fails, pert=0.0.
- `pytest tests/test_h23_crypto_futures_tsmom.py` -> 24 passed.
- `pytest` (full suite) -> 319 passed in 5.97s (was 318; +1 new robustness test).
- `ruff check` on modified files: only 5 errors, ALL pre-existing (lines 211, 314,
  375, 873 of run_h23 and line 64 of the test file). No errors in any added line.
  No mypy config present; project is untyped.
- Artifact/summary internal consistency: grid argmax(eligible) == selected config;
  `selection_rule` reflects the new rule; metrics/gates consistent.

## What remains unresolved
- H23 still REJECTs — and now for a *real* reason rather than a degenerate artifact.
  The selected trading config has a strongly negative edge on this sample.
- Root cause of the negative edge is clear and localized (see evidence below); it
  is not a bug in the selection logic. The liveness guard has done its job of
  steering selection away from the zero-trade trap; the hypothesis itself lacks
  edge on the cached 300-hour crypto sample.
- The broader H1-H21 non-futures families remain documented as REJECT (free-data
  constraints) in FINAL_REPORT.md; unchanged.

## Evidence (latest H23 run `exp_2026-10-14T11-53-37-996139Z`)
- Grid: 6912 combos; 2304 zero-trade configs (val_sharpe 0.0); 4608 trading configs
  (val_sharpe max -1.845, val_trades max 4 — sample is only ~12.5 days hourly).
- Regime decomposition of selected config OOS: bull=0.0, sideways=-4.552, bear=0.0.
- OOS trades by symbol: DOGE/USD 60, ADA/USD 25, ETH/USD 19, BTC/USD 3 — loss
  concentrated in ADA/DOGE sideways trading.
- Ablation `min_trade_interval_only(mi=24)` OOS Sharpe = -2.144 (vs -7.187 for the
  selected min_int=0 config) — reducing trade frequency materially improves OOS SR,
  but remains negative.

## Which approaches have already failed and why
- Pure argmax-of-Val-Sharfe selection (original H23 rule): degenerate on this
  sample — selects a 0-trade config. Fixed in this session via the trade-count
  guard (not "retried", replaced with a corrected, tested rule).
- Declaring H23 PASS on crypto intraday TSMOM: the edge is structurally negative
  (sideways regime, ADA/DOGE noise). Not a latent bug — an outcome.
- A `val_trades >= GATES["min_trades"]/2` (=100) threshold was considered but is
  infeasible on this sample (max val_trades=4) and would select nothing; `>= 1`
  was chosen as the minimal viability guard that excludes exactly the degenerate
  configs.

## One precise next task (for the next agent)
**Diagnose and gate the sideways-regime exposure of the selected H23 config.**
Evidence: the selected config's OOS loss (-7.187 Sharpe) is
*entirely* in the sideways VIX regime (-4.552; bull/bear are flat at 0.0), and is
driven by ADA/USD and DOGE/USD noise (75 of 107 OOS trades). The `mi=24`
ablation already lifts OOS Sharpe to -2.144, indicating trade-frequency/noise is a
key driver.

Bounded scope (single session, ~2-3 min):
1. In `run_h23_crypto_futures_tsmom.py`, add a "sideways-regime filter" ablation
   variant of the selected config that zeroes the position when regime == "sideways"
   (reuse `regime_labels`/`regime_factor_hourly`; set the sideways regime factor to
   0.0), then re-evaluate OOS/Test gates.
2. Record OOS Sharpe, trades, PF, DD, worst-regime Sharpe, and the 9-gate
   pass/fail for (a) current selected config and (b) sideways-filtered variant.
3. If the sideways-filtered variant passes all gates (esp. sharpness and worst-
   regime), promote the regime factor / min_trade_interval change and re-run the
   full grid (the `MIN_TRADE_INTERVALS` grid already contains `mi=24`).
4. If still negative, record the failure mode (likely signal noise on low-mcap
   alts) and finalize H23 as REJECT with a clean, non-degenerate basis — and stop
   (do not keep chasing).

Constraints: preserve determinism (SEED=42, offline cached data); keep changes
reversible; run only H23; validate with
`pytest tests/test_h23_crypto_futures_tsmom.py`. Do NOT regress H22 or other
hypotheses. If a regime filter flips the verdict to PASS, also add a test pinning
the regime factor value used.
