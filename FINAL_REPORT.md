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
- **Rejected:** H1 and H2 as *profitable* on 2015-2024 ETFs (both fail gates).
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

## Next Task
See `NEXT_TASK.md`: build a **regime-aware / crisis-resilient** momentum variant
(VIX-gated, volatility-scaled, tail-risk hedged) with a proper futures/contango
data layer, and re-test against the same gates. This directly targets the
*identified* failure mode rather than re-running raw momentum.
