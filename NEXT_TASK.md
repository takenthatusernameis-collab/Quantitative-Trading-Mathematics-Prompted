# Next Task: H6 — VIX-Gated + DDCV Combo on Futures TSMOM

## Status of H5 (executed 2026-10-11, REJECTED)

H5 (DDCV) was executed and **rejected** (7/8 gates fail). The DDCV mechanism
reduced max drawdown from −38.5% (base H4) to −35.3% (best DDCV combo:
dd_trigger=0.30, dd_factor=0.75, OOS Sharpe 0.509), but this was insufficient
to clear the ≤15% DD gate. The full results are in
`HYPOTHESIS_SPEC.md` (H5 section) and artifact
`exp_2026-10-11T00-34-05-381535Z`.

**Key H5 finding:** The VIX-gate ablation (ablation c) was the **best
performer** across all variants: OOS Sharpe **0.711**, max DD **−20.0%**,
PF 1.186, 164 trades, IR 0.39. This is the highest Sharpe achieved in the
entire momentum family on 2015-2024 free daily data. DDCV added no Sharpe
benefit over a blunt 50% vol cut; the DD gate is a **risk-scaling problem**,
not a drawdown-timing problem.

## Mission

The momentum family has been tested across 5 hypotheses (H1-H5), all
**REJECTED**. The corrected futures TSMOM produces genuine positive OOS alpha
(IR 0.33-0.39) but cannot certify the PROMPT_V2 gates (Sharpe ≥ 1.0, DD ≤ 15%)
on free daily data. The strongest single result is the **VIX-gated vol target**
from the H5 ablation: Sharpe 0.711, DD −20.0% — both dimensions close to
passing but neither clears the gates.

The logical next step is to **combine the two most effective vol-management
mechanisms** — VIX-regime exposure cuts (which raised Sharpe from 0.495 to 0.711)
and DDCV drawdown conditioning (which cut DD from 38.5% to 35.3%) — and test
whether the combination pushes both metrics into passing territory.

## Hypothesis H6: VIX-Gated + DDCV Combo on Futures TSMOM

**H6**: Apply both a VIX-regime exposure gate AND a drawdown-conditioned vol
target to the corrected futures TSMOM (long-only, lookback 252, skip 1) so that:
- In bull regime (VIX < 20): full target vol (15%), DDCV active.
- In sideways regime (VIX 20-30): 25% exposure, DDCV active.
- In bear regime (VIX > 30): 10% exposure, DDCV active (aggressive cutting).
- DDCV further reduces vol target when portfolio is in drawdown from rolling peak.

This combines the Sharpe-lifting power of VIX-gating with the drawdown-reducing
power of DDCV. The VIX gate alone achieved Sharpe 0.711 but DD −20.0%; adding
DDC could bring DD below the 15% gate while preserving the Sharpe lift.

**Null (H0):** VIX+DDCV futures TSMOM OOS Sharpe ≤ 1.0 OR max DD > 15%.

### Pre-registered design

- **Universe**: ES=F, NQ=F, CL=F, GC=F, ZB=F (all 5 available).
- **Splits**: Train 2015-2019, Val 2020-2021, Test 2022-24 (protected).
- **Base signal**: `vol_scaled_tsmom_signals` from
  `src/qtr/strategies/baselines.py` (long_only=True, lookback=252, skip=1,
  target_vol=0.15) — the corrected H4 best combo.
- **VIX gate**: same as H5 ablation (c):
  - VIX < 20 → scale = 1.0 (full)
  - VIX 20-30 → scale = 0.25
  - VIX > 30 → scale = 0.10
  - `^VIX` used for regime labels only (not traded).
- **DDCV layer**: applied *after* VIX gate, before engine:
  ```
  dd = equity / equity.rolling(252).max() - 1.0   # ≤ 0
  dd_scale = 1.0 - dd_factor * max(0, -dd).clip(0, dd_trigger)
  total_scale = vix_scale * dd_scale
  ```
  Grid over `dd_trigger` ∈ {0.10, 0.15, 0.20} and `dd_factor` ∈ {0.5, 0.75}.
  The combined scale (VIX × DDCV) is applied to the whole book.
- **Selection**: single pre-registered combo (no grid search on Test); Val
  used for gate evaluation only.
- **Gates** (unchanged PROMPT_V2): Sharpe ≥ 1.0, ≥ 200 trades, PF ≥ 1.3,
  DD ≤ 15%, WF stability ≥ 0.7, ±20% perturbation, worst-regime Sharpe
  ≥ 0.3, benchmark p < 0.05 **and IR > 0**.
- **Compute budget**: ≤ 2 CPU-h. Seed 42.

### Deliverables

1. `run_h6_vix_ddcv_experiment.py` — H6 pipeline + gates (reuses
   `vol_scaled_tsmom_signals`, `run_backtest`, `compare_to_benchmark`).
2. Artifacts in `.experiments/artifacts/exp_<H6>/`.
3. Updated `HYPOTHESIS_SPEC.md` (append H6) and `INEFFICIENCY_RANKING.md`.
4. Final verdict: PASS all gates, or REJECT with root-cause attribution
   (preserve all negative results).

### Fallback / Ablation plan

If the combined VIX+DDCV still cannot clear both Sharpe ≥ 1.0 and DD ≤ 15%,
run the ablation to isolate which component drives the remaining failure:
- (a) VIX-gate only (already known: Sharpe 0.711, DD −20.0%)
- (b) DDCV only (already known: Sharpe 0.509, DD −35.3%)
- (c) VIX+DDCV combo (H6)
- (d) VIX-gate with more aggressive sideways/bear factors
  (e.g. sid_factor ∈ {0.10, 0.15}, bear_factor ∈ {0.05, 0.10})

This isolates whether the remaining Sharpe gap (0.711 → need 1.0) comes from
insufficient crash-mitigation (need more aggressive VIX cuts) or from a
fundamental signal-strength ceiling on free daily data.

### Constraints (unchanged)

- Do **not** weaken evidence gates; they survived H1-H5 intact.
- Do not optimize against Test; Val/Test used only for gate evaluation.
- Test never enters selection.
- Preserve all negative results.
- No live trading, no secrets, no paid data.
- Max 2 CPU-h per experiment.
- Regression tests must pass before finishing
  (`python3 -m pytest tests/ -q` — currently 38 passing).

## Context for the Next Agent

### What H1-H4 proved (before H5)

| Exp | Strategy | OOS Sharpe | Max DD | IR | Status |
|-----|----------|-----------|--------|----|--------|
| H1 | TSMOM (20 ETFs) | 0.093 | −34.8% | −0.124 | REJECTED |
| H2 | CS Momentum (10 ETFs) | 0.116 | −38.7% | −0.252 | REJECTED |
| H3 | VIX-gated + VXX hedge | −0.868 | −48.3% | −0.893 | REJECTED |
| H4 | Futures TSMOM (ensemble) | 0.376 | −47.4% | +0.332 | REJECTED |

### What H5 proved

| Variant | OOS Sharpe | Max DD | PF | Trades | IR |
|---------|-----------|--------|----|--------|----|
| Base (H4 combo) | 0.495 | −38.5% | 1.139 | 138 | — |
| DDCV (best) | 0.509 | −35.3% | 1.108 | 188 | — |
| Fixed 50% cut | 0.495 | −19.2% | 1.139 | 138 | — |
| **VIX-gate** | **0.711** | **−20.0%** | 1.186 | 164 | 0.39 |

### Key architectural notes

- The canonical TSMOM signal is in `src/qtr/strategies/baselines.py::vol_scaled_tsmom_signals`
  (sign invariant pinned by `tests/test_tsmom_signal.py`).
- The backtest engine's cost model is corrected (equity costs in bps of
  portfolio value, not multiplied by price; futures costs per-contract with
  multiplier/tick_value).
- Data is cached at `.cache/data/` (Yahoo `=F` continuous futures, `^VIX`).
- Experiment tracking is via `src/qtr/tracking/experiment.py` (JSONL +
  Parquet artifacts, full reproducibility metadata).
- Start the experiment script from the repo root — it adds `src/` to the
  Python path internally.

### The central research question for H6

The VIX-gate ablation (H5c) is the **single best result in the entire
momentum family on free daily data** — Sharpe 0.711, DD −20.0%. It clears
neither gate but is within striking distance on both. The question H6 tests is
whether **combining** VIX-gating (Sharpe lift) with DDCV (DD reduction) can
bridge the gap: if VIX+DDCV achieves Sharpe ≥ 1.0 AND DD ≤ 15%, the gates
pass and the momentum family is no longer "exhausted." If not, the negative
result further establishes the floor for any future regime-aware variant.
