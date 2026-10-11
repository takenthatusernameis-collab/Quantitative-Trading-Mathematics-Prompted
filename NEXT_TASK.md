# Next Task: Roll-Yield Capture on Continuous Futures TSMOM

## Status of H7 (executed 2026-10-11, REJECTED)

H7 tested multi-horizon TSMOM (252d + 63d blend) with regime-weighted blending and daily-approximated path-dependent exits on futures (ES/NQ/CL/GC/ZB `=F`).
- OOS Sharpe **0.789** (< 1.0), max DD **-14.5%** (boundary), PF 1.166 (< 1.3), 1005 trades, WF stability 1.0.
- Gates: 2/4 hard fail (Sharpe, PF); DD and WF pass. Overall **REJECT**.
- Root cause: Daily rebalancing + approximated exits cannot exploit intraday dynamics; Val period (2021-2022) weak (0.188) pulls OOS below threshold despite strong Test (1.269).
- Momentum family now includes H1-H7 all REJECTED on free daily/intraday-approximated data.

---

## Mission

Pivot to the roll-yield capture pathway (the `=F` continuous contracts smooth/mask roll edge). Build a roll-adjusted returns series from daily `=F` contracts by detecting roll dates (volume/OI shifts) and adding roll carry, then test TSMOM on roll-adjusted returns. Also consider extending sample to pre-2015 if needed.

Recommended: H8 — Roll-adjusted Futures TSMOM (capture true roll-date P&L).

### Pre-registered H8 design
- Universe: ES=F, NQ=F, CL=F, GC=F, ZB=F
- Detect roll dates from volume/OI shifts (or naive month-end/expiry-aware heuristics). Compute roll adjustment: add (next_front_price - front_price)/front_price on roll days to approximate roll carry in excess returns.
- Build roll-adjusted price/return series R’_t = R_t + adjustment_t.
- Base: vol-scaled TSMOM (canonical) with lookback/skip selected on Train (or use best from H4 corrected: long_only=True, lookback=252, skip=1) to minimize degrees of freedom.
- Splits: Train 2015-2019, Val 2020-2021, Test 2022-2024 (protected).
- Gates: unchanged PROMPT_V2 (Sharpe ≥ 1.0, DD ≤ 15%, PF ≥ 1.3, WF stability ≥ 0.7, benchmark p<0.05, IR>0).
- Null: Roll-adjusted TSMOM OOS Sharpe ≤ 1.0 OR max DD > 15%.

---

## Deliverables for Next Agent
1. `run_h8_rolladjusted_tsmom_experiment.py` — roll detection + adjustment, TSMOM backtest with gates (reuse existing engine/tracking/validation).
2. Artifacts in `.experiments/artifacts/exp_<H8>/`.
3. Update `HYPOTHESIS_SPEC.md` (append H8) and `INEFFICIENCY_RANKING.md`.
4. Final verdict: PASS/REJECT with root-cause attribution. Preserve negative results.
5. All 38 regression tests passing.

---

## Constraints (unchanged)
- Do not weaken evidence gates.
- Test never enters selection.
- Preserve all negative results.
- No live trading, no secrets, no paid data.
- Max 4 CPU-h per experiment.
