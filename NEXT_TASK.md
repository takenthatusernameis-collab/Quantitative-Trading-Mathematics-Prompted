# Next Task: H10 complete — PASS

## H10 executed 2026-10-11 — **PASS (8/8 gates)**

Full 13,824-combo turnover-aware signal + exit grid, Val-selected, Test-protected.
Evaluated in 0.48 CPU-h (29 min). Artifacts: `.experiments/artifacts/exp_2026-10-11T17-41-18-169363Z/`.

| Gate | Threshold | H10 OOS | Result |
|------|-----------|---------|--------|
| Sharpe | ≥ 1.0 | **1.276** | PASS |
| Trades | ≥ 200 | **2,416** | PASS |
| Profit Factor | ≥ 1.3 | **1.304** | PASS |
| Max DD | ≤ 15% | **-5.8%** | PASS |
| WF Stability | ≥ 0.7 | **0.781** | PASS |
| Worst-regime SR | ≥ 0.3 | **1.046** (bull) | PASS |
| Benchmark p | < 0.05 | **4.8e-10** | PASS |
| Information Ratio | > 0 | **0.925** | PASS |

**Selected config**: vol_window_long=1008 (4-week vol window), smooth_span=none,
regime_scaling=False, min_trade_interval=0, trailing_mult=2.0, max_hold_bars=60,
vol_limit_mult=1.5, vol_floor_fraction=0.25.

**Root-cause of the PF fix (from ablations):**
- Longer vol window only (vw=1008): OOS Sharpe 1.142, PF 1.273 — recovers most of the gain.
- Exit grid best (selected config): OOS Sharpe 1.276, PF 1.304 — delivers the final push.
- Signal smoothing and regime scaling were **not** selected.

**Infrastructure defect fixed during H10:** the script did not normalize the tz-aware
(America/New_York) yfinance futures index to tz-naive before reindexing against the
tz-naive hourly VIX index (TypeError). Fixed with `tz_convert(None)`; also removed a
duplicated `pos[i] = cur_pos` block in `apply_exits_hourly`.

**Verification:** 50/50 regression tests passing.

---

## Next Task (for next agent): H11 — Robustness / Certification

H10 is the first hypothesis in the H1–H10 family to clear all 8 evidence gates, but it runs
on a **small, single-sample hourly window (~730 days, 2024-10-13 → 2026-10-09)** from free
yfinance data. Before treating this as a certified strategy, the following must be tested:

1. **Seed / perturbation robustness**: re-run H10's selected config with different numpy
   seeds and ±20% parameter perturbations (already a gate: `min_perturbed_sharpe_ratio: 0.5`
   is in the gate set but was not evaluated in H10 — the H10 `_full_gate_eval` does not
   compute perturbation sharpes). Add the perturbation gate and confirm it holds.
2. **Walk-forward re-run on a shifted window**: the 55/25/20 split is fixed to the available
   ~730-day window. If a longer intraday history becomes available (paid data or an
   alternative free source), re-run the full grid on the extended window and confirm the
   vol_window_long=1008 / exit-parameter ranking is stable.
3. **Cost-model sensitivity**: H10 turns over ~2,400 trades in ~2 years. Stress-test the
   cost model (commission/spread/slippage) at ±50% and confirm PF stays ≥ 1.3.
4. **Out-of-sample time extension**: the Test window (2026-08-09 → 2026-10-09) is only ~60
   days. Continue collecting fresh hourly `=F` bars and re-evaluate the selected config on
   new data as it arrives — the true OOS test is ongoing.
5. **Per-symbol concentration**: H10 reports pooled metrics. Check whether the edge is
   concentrated in 1–2 symbols (e.g., ES) or genuinely diversified across ES/NQ/CL/GC/ZB.

**Pre-registration for H11** (to be written by the next agent before execution):
- Null (H0): the H10 selected config, re-run on a perturbed seed/window/cost model,
  fails any of the 8 gates (Sharpe < 1.0, PF < 1.3, DD > 15%, WF stability < 0.7,
  worst-regime SR < 0.3, p ≥ 0.05, IR ≤ 0, or perturbed Sharpe < 0.5).
- Deliverables: `run_h11_robustness_experiment.py`, artifacts in
  `.experiments/artifacts/exp_<H11>/`, updated `HYPOTHESIS_SPEC.md` and
  `INEFFICIENCY_RANKING.md`, final PASS/REJECT verdict with root-cause attribution.

**Constraints (unchanged):** no live trading, no secrets, no paid data, Test never enters
selection, preserve negative results, ≤ 4 CPU-h per experiment, reuse existing engine /
tracking / validation infrastructure, all regression tests passing.