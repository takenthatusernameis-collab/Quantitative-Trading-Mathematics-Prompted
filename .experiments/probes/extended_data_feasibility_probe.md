# Extended Data Feasibility Probe for H10-Family PF-Margin Robustness

**Experiment ID:** `probe_2026-10-13T19-45-00Z`
**Related Hypotheses:** H10, H11, H12, H13, H14
**Date:** 2026-10-13
**Status:** COMPLETE (read-only assessment; no network fetches, no artifact modifications)

---

## 1. Executive Summary

This probe assesses whether extending the evaluation window beyond the current ~730-day hourly `=F` futures horizon (2024-10-13 → 2026-10-09) via an alternate data adapter/path could plausibly:
- Move the OOS Profit Factor (PF) bootstrap 95% CI lower bound from **1.190 → ≥ 1.300**
- Achieve full symbol dispensability (currently CL=F and GC=F are indispensable)

**Verdict:** **UNLIKELY** without paid data. Free `yfinance` hourly `=F` futures are hard-capped at ~730 days. No local alternate hourly data exists. Paid data (CQG, Rithmic, IQFeed, Polygon.io, Databento) would be required. Even with extended data, statistical power analysis suggests the PF margin (+0.004 over 1.3) is smaller than bootstrap noise; CI width reduction scales as 1/√N, requiring ~3-4× more bars to shrink the CI enough for the lower bound to clear 1.3 reliably, assuming the point estimate holds.

---

## 2. Current Data Horizon & Constraints

| Property | Value |
|----------|-------|
| **Data Source** | Yahoo Finance (`yfinance`) continuous futures `=F` tickers |
| **Symbols** | ES=F, NQ=F, CL=F, GC=F, ZB=F (+ VIX) |
| **Interval** | 1-hour |
| **Start** | 2024-10-13 18:00 UTC-4 |
| **End** | 2026-10-09 16:00 UTC-4 |
| **Total Bars (per symbol)** | ~11,300–11,400 |
| **OOS Bars (H10 split)** | 5,148 (selected config) |
| **Free Tier Limit** | ~730 calendar days for hourly `=F` (yfinance hard cap) |

**Evidence:** Cached artifacts in `.cache/data/` confirm hourly futures end at 2026-10-09. No bars exist beyond this date in the local cache. The `yfinance` library enforces this limit for continuous futures contracts.

---

## 3. Candidate Alternate Data Sources (Read-Only Assessment)

| Source | Hourly `=F` Futures | History Depth | Access Type | Local Availability | Notes |
|--------|---------------------|---------------|-------------|-------------------|-------|
| **Yahoo Finance (current)** | ✅ | ~730 days | Free, public API | ✅ Cached | Hard cap; no extension possible |
| **Polygon.io** | ✅ (via `@polygon` tickers) | 5+ years | Paid (Developer $29/mo+) | ❌ Not present | Requires API key; REST + WebSocket |
| **Databento** | ✅ (GLBX.MDP3, etc.) | 10+ years | Paid (pay-per-GB) | ❌ Not present | High-quality normalized data; Python SDK |
| **IQFeed / DTN** | ✅ | 20+ years | Paid (enterprise) | ❌ Not present | Requires proprietary client |
| **CQG / Rithmic** | ✅ | 10+ years | Paid (broker-integrated) | ❌ Not present | Professional futures data feeds |
| **Quandl / Nasdaq Data Link** | ⚠️ Limited | Varies | Paid/Free tiers | ❌ Not present | Mostly daily; limited hourly futures |
| **Local CSV/Parquet (user-provided)** | ❓ | ❓ | Manual | ❌ Not present | Would need schema validation |

**No alternate hourly futures data found in local environment.** All cache entries are `yfinance`-sourced.

---

## 4. Statistical Power & CI Width Impact Analysis

### 4.1 Current Bootstrap CI (H13)
- **Point estimate (PF):** 1.3042
- **Bootstrap 95% CI:** [1.190, 1.425]
- **CI Width:** 0.235
- **Margin over gate (1.3):** +0.0042
- **P(PF ≥ 1.3):** 51.7% (2,000 resamples, seed=42)
- **OOS Bars (n):** 5,148

### 4.2 CI Width Scaling
Bootstrap CI width for a statistic scales approximately as `σ / √n_eff`, where `n_eff` is the effective sample size accounting for autocorrelation. For hourly futures returns, autocorrelation is low but non-zero (|ρ₁| ~ 0.02–0.05). A conservative `n_eff ≈ n / (1 + 2∑ρₖ) ≈ 0.8n`.

| Scenario | OOS Bars (n) | n_eff (est.) | CI Width (est.) | CI Lower Bound (est.) | Pass PF Gate? |
|----------|--------------|--------------|-----------------|----------------------|---------------|
| **Current (H13)** | 5,148 | ~4,100 | 0.235 | 1.190 | ❌ FAIL |
| **2× extension** | ~10,300 | ~8,200 | 0.166 | 1.238 | ❌ FAIL |
| **3× extension** | ~15,450 | ~12,350 | 0.136 | 1.268 | ❌ FAIL (marginal) |
| **4× extension** | ~20,600 | ~16,500 | 0.118 | 1.286 | ⚠️ BORDERLINE |
| **5× extension** | ~25,750 | ~20,600 | 0.105 | 1.299 | ✅ LIKELY PASS |

**Key Assumption:** Point estimate (PF ≈ 1.304) remains stable with more data. If the true PF is actually 1.304, ~5× current OOS bars (~25k bars, ~3 years of hourly data) would be needed for the 95% CI lower bound to reliably exceed 1.3. If the true PF is lower (e.g., 1.28), no feasible extension helps.

### 4.3 Symbol Dispensability
H13 per-symbol net PFs:
- ES=F: 1.218 | NQ=F: 1.237 | **CL=F: 1.358** | **GC=F: 1.224** | ZB=F: 1.118

Leave-one-out pooled PFs (removing each symbol):
- Without CL=F: 1.249 (< 1.3) → **INDISPENSABLE**
- Without GC=F: 1.282 (< 1.3) → **INDISPENSABLE**

Extended data would need to either:
(a) Improve CL=F and GC=F standalone PFs so their removal doesn't drag pooled PF below 1.3, OR
(b) Improve other symbols enough to compensate.

No evidence from current data suggests structural improvement in CL=F/GC=F with more samples; their indispensability appears to be a feature of the signal's interaction with energy/metals volatility regimes.

---

## 5. Split Feasibility (Extended Window)

Current splits (H11/H13):
- 50/25/25: Train 10,296 / Val 5,148 / OOS 5,148 bars
- 60/20/20: Train 12,355 / Val 4,118 / OOS 4,118 bars
- 45/30/25: Train 9,266 / Val 6,178 / OOS 5,148 bars

With 3–5× more data (15k–25k OOS bars):
- All split ratios remain feasible
- Walk-forward validation gains statistical power
- Regime coverage improves (more bear/sideways regimes captured)
- **Risk:** Non-stationarity increases with longer horizons (regime changes, market structure shifts, roll methodology changes)

---

## 6. Required Fields (per NEXT_TASK.md)

| Field | Value |
|-------|-------|
| **data_source** | No viable free hourly `=F` futures source beyond yfinance's ~730-day cap. Paid sources (Polygon.io, Databento, IQFeed, CQG) required for extension. |
| **available_bars** | Current: ~11.3k hourly bars/symbol (2024-10-13 → 2026-10-09). Extended (paid): 50k–200k+ bars/symbol (5–20 years) depending on vendor. |
| **split_feasibility** | Feasible with extended data. Current 3-split design (50/25/25, 60/20/20, 45/30/25) scales directly. Minimum OOS ≥ 5k bars maintained. |
| **estimated_power_ci_impact** | CI width ∝ 1/√n. Need ~4–5× current OOS bars (~20k–25k) for CI LB to plausibly clear 1.3 *if point estimate holds at 1.304*. At 2× extension, CI LB ≈ 1.24 (still FAIL). Symbol dispensability unlikely to resolve without regime-specific signal improvements. |
| **assumptions** | 1. PF point estimate (1.304) is unbiased and stable out-of-sample.<br>2. Return autocorrelation structure doesn't change materially.<br>3. Paid data quality ≥ yfinance (no look-ahead bias, correct roll adjustments).<br>4. Signal logic (H10 frozen config) remains valid over extended horizon.<br>5. Transaction cost model (H11/H13) remains accurate. |
| **risks** | 1. **Non-stationarity:** 5+ year horizons span multiple macro regimes; TSMOM edge may decay.<br>2. **Roll-adjustment bias:** Continuous `=F` contracts from different vendors use different roll algorithms; splicing introduces drift.<br>3. **Cost model mismatch:** Historical bid-ask spreads, commissions, slippage differ from current model.<br>4. **Selection bias amplification:** Re-running selection on extended window invalidates frozen-pipeline guarantees (H11/H12).<br>5. **Data cost:** $500–$5,000+/year for quality hourly futures; not recoverable in this research context.<br>6. **False precision:** Narrower CI on a biased estimate is worse than wide CI on unbiased estimate. |

---

## 7. Recommendation

**Do not pursue extended data acquisition for this hypothesis family.** The PF-margin fragility is a structural property of the H10-selected config on the available window. The margin (+0.004 over 1.3) is smaller than bootstrap noise and depends critically on CL=F and GC=F loss-offsetting.

**Alternative paths (out of scope for this probe):**
1. **Signal redesign** — incorporate regime-aware exits or symbol-specific parameters (would require new hypothesis H15+).
2. **Ensemble/diversification** — combine with uncorrelated strategies to raise portfolio PF (H10 was single-config).
3. **Cost reduction** — tighter execution (not a data problem).

**If paid data becomes available**, the minimal validation step would be:
1. Fetch 5+ years of hourly futures from vendor (read-only).
2. Validate schema, coverage, roll adjustment methodology.
3. Re-run H13 gates *with frozen H10 config only* (no re-selection) on extended OOS.
4. Report whether CI LB ≥ 1.3 and all symbols dispensable.

---

## 8. Artifact Invariants Verified

- ✅ No frozen pipeline logic modified.
- ✅ No committed H10/H11/H12/H13/H14 artifacts overwritten.
- ✅ No external network fetches performed.
- ✅ Runtime < 0.01 CPU-h (pure analysis of cached metadata).
- ✅ Report written to `.experiments/probes/extended_data_feasibility_probe.md`.

---

*End of probe report.*