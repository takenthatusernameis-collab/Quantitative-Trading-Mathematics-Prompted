# Final Report: Quantitative Trading Mathematics Research

## Executive Summary

Executed Phases 3–5 of the PROMPT_V2.md research spec: a mathematical
discovery → market inefficiency → hypothesis test pipeline, applied to
**volatility-scaled time-series and cross-sectional momentum on liquid ETFs
(2015-2024)**. The two pre-registered hypotheses were **rejected** by the strict
evidence gates (Sharpe ≥ 1.0, ≥200 OOS trades, PF ≥ 1.3, max DD ≤ 15%,
walk-forward stability, ±20% perturbation, regime stability, benchmark
significance). The dominant failure is a **train→OOS collapse** driven by the
2020 COVID crash and 2022 inflation shock (bear-regime Sharpe ≈ -2.4 to -3.0) —
the well-documented *momentum crash*.

A separate, material infrastructure defect was found and fixed: the backtest
engine's equity cost model inflated trading costs ~400× (by the asset price),
which was the **actual bottleneck** making every active strategy appear
catastrophically unprofitable while buy-and-hold survived. After correction,
costs are verified realistic, and the momentum underperformance is genuine
signal weakness (OOS Sharpe ≈ 0.1), not a cost artifact.

---

## Phase 1 — Prompt Refinement
Frozen at PROMPT_V2.md (2 cycles; all criteria ≥ 4/5). Not changed during this
cycle (no new evidence requiring prompt revision — the gates held and correctly
rejected the candidate).

## Phase 2 — Infrastructure (prior agent) → Bottleneck Found
The prior agent built the engine, fetcher, tracker, strategies and stats suite
and established the SPY buy-and-hold baseline (Sharpe ≈ 0.66). **Bottleneck
identified during Phase 3-5 execution:** the cost model. Details below.

### Cost-model defect (the real bottleneck)
`src/qtr/backtest/engine.py::_calculate_costs` computed equity cost as
`weight_delta * price * bps/10000` and subtracted it from *fractional* portfolio
returns. The correct cost-as-fraction-of-capital is
`weight_delta * bps/10000`. The extra `* price` injects the per-share dollar
price (e.g. ~$400 for SPY), inflating each trade's cost by ~400×.
Consequences (verified):
- Buy-and-hold SPY (1 trade): day-0 cost ≈ 12% of capital (now ≈ 3 bps).
- MA 30/200 (9 trades): reported Sharpe **0.249** (buggy) → **0.655** (fixed).
- Momentum (768–1500 trades): every trade carried a ~0.6–6% haircut, destroying
  the signal.

**Fix:** `symbol_costs = changes * (cost_bps / 10000)` for equity and crypto
(Futures path was already correct). Re-validated: buy-and-hold SPY → 0.685,
costs sub-bps for low-turnover legs. The prior "MA crossover fails catastrophically"
conclusion was an artifact; the corrected conclusion is "MA crossover ≈ buy-and-hold,
still not an edge."

---

## Phase 3 — Mathematical Discoveries Investigated
Literature review with provenance, assumptions, limitations, and replication
status for: TS momentum (Moskowitz et al. 2012), CS momentum (Jegadeesh &
Titman 1993; Asness et al. 2013), carry (Koijen et al. 2018), regime-switching
(Kim & Mueller 2016), and information-theoretic predictors (Schreiber 2000).
Full traceability chains in `MATHEMATICAL_DISCOVERY_REPORT.md`.

Top candidates scored 5.0/5.0 and were taken to experiments: TS momentum (H1)
and CS momentum (H2). Carry was deferred (futures-roll data gap); transfer
entropy rejected (no high-freq cross-market data).

## Phase 4 — Inefficiency Ranking
Six-factor market ranking; updated with measured (post-cost-fix) net edge.
TS momentum ranked #1 on theory but **2/10 on realized edge** — the sample
itself (2020/2022) is the invalidating evidence. See `INEFFICIENCY_RANKING.md`.

## Phase 5 — Hypothesis Generation & Testing

| Hypothesis | Universe | Selected params | OOS Sharpe (CI) | Trades | PF | Max DD | Gates passed | Verdict |
|------------|----------|-----------------|-----------------|--------|----|--------|--------------|---------|
| H1 TS momentum | 20 ETFs | LO, lb=126, sk=1 | 0.093 ([-0.76, 0.96]) | 768 | 1.017 | -34.8% | 2/8 | **REJECTED** |
| H2 CS momentum | 10 eq ETFs | LO, lb=252, sk=21 | 0.116 ([-0.71, 1.02]) | 388 | 1.024 | -38.7% | 1/8 | **REJECTED** |

**Why rejected (root causes, not artifacts):**
1. **Train→OOS decay:** train Sharpe 0.59–0.64 but protected-test Sharpe
   -0.039 / 0.092. The 2015-2019 window was a favorable bull regime; parameters
   selected by train-only walk-forward did not generalize.
2. **Momentum crashes:** 2020-03 and 2022 bear regimes produced Sharpe ≈ -2.4
   (H1) / -3.0 (H2), the documented crash episodes (Barberis & Shleifer 2003;
   Daniel & Moskowitz 2014).
3. **No alpha vs benchmark:** IR = -0.12 (H1) / -0.25 (H2), p = 0.78 / 0.57
   ⇒ the signal is indistinguishable from the equal-weight benchmark.

Evidence of genuine *information gain* (not noise): the experiment moved the
research question from "momentum might work" to "TS/CS momentum on 2015-2024
liquid ETFs, as constructed, fails the gates — primarily via regime crash risk,
not cost or implementation error."

---

## Phase 6 — Evidence Gates (applied, all real)
Both hypotheses evaluated against the full PROMPT_V2 + HYPOTHESIS_SPEC gate set
on pooled Val+Test OOS. Neither passed. Negative results preserved with full
reproducibility metadata (git commit, seeds, dependency versions, data hashes).

## Phase 6 (continued) — H1–H12 research arc (later agents)
The H1/H2 rejection motivated the H3–H12 hypothesis family (documented in
`HYPOTHESIS_SPEC.md` and `INEFFICIENCY_RANKING.md`):

| Hyp | Construction | OOS Sharpe | PF | Verdict |
|-----|--------------|-----------|-----|---------|
| H3 | Regime-gated vol-scaled momentum | — | — | REJECTED |
| H4 | Futures TSMOM + ensemble selection | — | — | REJECTED (cost-model bug found & fixed) |
| H5 | Drawdown-conditioned vol targeting | — | — | REJECTED |
| H6 | VIX-gated + DDCV combo | — | — | REJECTED |
| H7 | Multi-horizon regime-weighted TSMOM | — | — | REJECTED |
| H8 | Roll-adjusted futures TSMOM | — | — | REJECTED |
| H9 | Intraday futures TSMOM + CT exits | — | — | REJECTED |
| **H10** | **Intraday TSMOM PF-optimization (13,824-combo grid, Val-selected)** | **1.276** | **1.304** | **PASS (first to clear all 8 gates)** |
| H11 | Robustness certification of H10 | 1.276 | 1.304 | **PASS** (seeds, ±20% perturbation, ±50% costs, shifted splits, concentration) |
| **H12** | **Selection-bias audit of H10** | — | — | **PASS** (DSR-adj Sharpe 1.409, p=0.0028; PBO=0.055; family-corrected p=6.9e-06) |
| H13 | OOS deflation & PF-margin fragility audit | **1.275** (worst-case DSR-adj OOS) | 1.304, 95% CI [1.190, 1.425] | **REJECT on the fragility axes** (Sharpe survives the worst-case N=13,824 deflation, p=0.001; PF CI LB 1.190 < 1.3; CL=F and GC=F indispensable — leave-one-out PF 1.249 / 1.282) |

H12 confirms the H10 result is not a best-of-13,824 selection artifact: the
observed Val Sharpe (1.413) is 2.3× the expected maximum of 13,824 null
trials (0.621), CSCV finds no backtest overfitting (PBO 0.055 < 0.3), and the
OOS benchmark alpha (p 4.79e-10) survives Bonferroni/BH/Šidák correction at
the pooled family trial count (14,389). The fragile margin remains the profit
factor: OOS PF 1.304 clears the 1.3 gate by only +0.004, and only 0.32% of
grid configs clear PF ≥ 1.3 OOS.

H13 (executed 2026-10-13, < 0.1 CPU-h, artifact-reuse-only) shows the
certification is **Sharpe-robust but PF-fragile**: the OOS Sharpe survives
even the worst-case "OOS-as-selection-metric" deflation (DSR-adj 1.2745,
p = 0.001; single-peek DSR 1.2758), but the PF margin is statistically
indistinguishable from the 1.3 gate (bootstrap 95% CI [1.190, 1.425],
P(PF ≥ 1.3) = 51.7%) and single-symbol-dependent — CL=F (net PF 1.358,
the only symbol above the pooled PF) and GC=F are indispensable
(leave-one-out pooled PF 1.249 / 1.282). The shifted-split PF shortfalls
(1.281 / 1.292) are driven by CL=F and the bull regime. Cost break-even
verified at 1.542× (H11: 1.5418×) — costs are not the driver.

## Phase 7 — Process Improvement
- **Bottleneck:** cost-model units bug (fixed). Secondary: single-sample period
  (2015-2024 incl. two crisis episodes) is harsh on momentum; a regime-aware or
  longer-horizon (including pre-2015 TSMOM-strong decades) evaluation is needed.
- **Assumption that mattered most:** that buy-and-hold-style active strategies
  would beat a 10-year equity rally. They did not on ETFs; the opportunity is
  in *crisis-resilient* constructions, not raw direction-following.
- **Process change:** always sanity-check cost units against a 1-trade baseline
  before trusting active-strategy P&L.

## Phase 8 — Operational (all honored)
No secrets, no live trading, no paid data, no test-set feedback, all work
reproducible from `.experiments/` artifacts.

## Phase 9 — Verification
- Cost fix verified: buy-and-hold SPY Sharpe 0.685 (matches expectation).
- Artifacts re-loaded from parquet and match reported metrics.
- No existing tests exist (`.experiments/` has no `tests/` dir despite pyproject).

---

## Conclusion
- **Supported:** the cost-model bug is real and fixed; volatility-scaled
  momentum *implementation* is correct; the infra runs end-to-end.
- **Rejected:** H1 and H2 as *profitable* on 2015-2024 ETFs (both fail gates);
  H3–H9 across regime-gating, DDCV, multi-horizon, roll-adjustment and
  intraday-CT-exit variants (all fail gates — see HYPOTHESIS_SPEC.md).
- **Certified:** H10 (intraday futures TSMOM, PF-optimized) passes all 8
  gates; H11 certifies robustness; H12 certifies the result against
  selection bias (DSR, PBO, family-wide multiple testing).
- **Qualified (H13):** the certification is Sharpe-robust (worst-case
  OOS DSR 1.2745, p = 0.001) but the PF margin is fragile — bootstrap
  95% CI [1.190, 1.425] and single-symbol-dependent (CL=F, GC=F
  indispensable). Production use requires a longer OOS window (paid
  data) or PF-margin-targeted re-optimization.
- **Uncertain → actionable:** regime-aware / crisis-resilient momentum is the
  highest-value next step (see `NEXT_TASK.md`).

| Finding | Confidence | Evidence |
|---------|-----------|----------|
| Cost-model units bug | HIGH | pre/post fix: MA 30/200 0.249→0.655; B&H 0.660→0.685 |
| TS momentum fails gates on 2015-2024 | HIGH | exp_…20-57-26, 6/8 gates fail, Test Sharpe -0.039 |
| CS momentum fails gates | HIGH | exp_…20-59-28, 7/8 gates fail |
| Train→OOS decay is the failure driver | HIGH | train 0.59 vs test -0.04 |
| Momentum crashes (2020/2022) dominate | HIGH | bear-regime Sharpe -2.4/-3.0 |
| No significant alpha vs EW benchmark | HIGH | p = 0.78 / 0.57 |
| H10 intraday TSMOM clears all 8 gates | HIGH | OOS Sharpe 1.276, PF 1.304, DD -5.8%, 2,416 trades |
| H10 result is not a selection artifact | HIGH (H12) | DSR p=0.0028; PBO=0.055; Bonferroni p=6.9e-06 @ N=14,389 |
| Profit factor is the fragile gate | HIGH | OOS PF margin +0.004; only 0.32% of combos pass PF OOS |
| OOS Sharpe is deflation-robust | HIGH (H13) | worst-case DSR-adj OOS Sharpe 1.2745, p=0.001 (N=13,824 peeking bound) |
| PF margin is statistically fragile | HIGH (H13) | bootstrap 95% CI [1.190, 1.425]; P(PF ≥ 1.3) = 51.7% |
| PF margin is single-symbol-dependent | HIGH (H13) | CL=F and GC=F indispensable: leave-one-out PF 1.249 / 1.282; CL drives shifted-split shortfalls (−0.076 / −0.084) |

## Next Task
See `NEXT_TASK.md`: the H10/H11/H12 chain is certified on the
available (~2-year hourly) window, and H13 qualified the
certification — the OOS Sharpe is deflation-robust but the PF
margin is statistically fragile and single-symbol-dependent. The
binding constraints are data-horizon (free yfinance caps hourly
`=F` at ~730 days) and the thin PF margin. Next steps: (a) extend
to a paid data source for a longer OOS window, and/or (b) a
PF-margin-targeted re-optimization (select on PF margin, not
Val Sharpe) of the certified config family.


## H14 Summary (2026-10-13)

H14: PF-margin-targeted selection audit (top-K=50 by Val PF margin, K=50, excluding H10). Gates: PF bootstrap CI LB≥1.3, worst-case DSR-adj OOS Sharpe≥1.0 at N=K, all symbols dispensable. No config satisfied all three (CI LB max 1.199, all 0/50 dispensable despite all DSR≥1.0). Verdict: REJECT — PF-margin fragility is a family property on this window; H10 line closed.
Artifacts: `.experiments/artifacts/exp_2026-10-13T19-01-59-371405Z/`
