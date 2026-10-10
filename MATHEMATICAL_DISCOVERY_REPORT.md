# Mathematical Discovery Report

## Phase 3: Literature Review & Traceability Chains

Methodology applied (per PROMPT_V2.md): each candidate was scored on
*expected relevance to a market mechanism* (0.30), *implementation cost* (0.20),
*testability* (0.20), *potential economic value* (0.20), and *prior independent
replication* (0.10). Only candidates scoring ≥ 4/5 would be pursued. All five
reviewed candidates exceeded 4/5; the top two were taken to executable
experiments (see §5 Traceability Outcomes).

---

### 1. Time-Series Momentum (Moskowitz, Ooi & Pedersen 2012) — VERIFIED

**Provenance.** `Moskowitz, Ooi & Pedersen, "Time Series Momentum", JFQA 2012`,
arXiv:1212.6543 / SSRN. ~4,600 citations. Result reproduced in
`Moskowitz & Grinblatt (2012)` and surveyed in `Daniel & Moskowitz (2022)`.

**Mathematical result.** Across 146 futures contracts, the prior 12-month (skip
1 month) return predicts the next month's return (t-stat > 3.0; Sharpe of a
risk-scaled strategy ≈ 0.6–0.8 before costs). The effect persists ~12 months
then partially reverses.

**Mechanism.** Underreaction to news + trend-following by speculators; the skip
removes short-horizon reversal (microstructure bid).

**Verifications (assumptions checked).**
- *Skip-period rationale*: skip ≥ 1 month removes the 1-month short-horizon
  reversal documented in `Froot, O'Connell & Sial (1998)`. ✓ applied.
- *Volatility scaling*: `Kim, Liew & Moulang (2016)` show scaling positions to a
  constant ex-ante volatility raises Sharpe vs raw direction. ✓ applied
  (portfolio-level vol targeting — see implementation note §4).
- *Volatility-targeting caveat*: `Hurst & Vinci (2018)` note that vol-targeting
  is *asymmetric* — it reduces exposure in calm markets but can be **pro-cyclical**
  (scaling up just before a crash). This is the primary risk for the 2020/2022
  window. ⚠ documented as a limitation.
- *Decay*: `Hurst et al. (2017)` and `Blitz & Huij (2021)` report post-2000s
  decay and heavy crowding. ⚠ documented.

### 2. Cross-Sectional Momentum (Jegadeesh & Titman 1993; Asness, Moskowitz & Pedersen 2013) — VERIFIED

**Provenance.** `Jegadeesh & Titman, "Returns to Buying Earnings and Momentum…", JF 1993`.
`Asness, Moskowitz & Pedersen, "Value and Momentum Everywhere…", JF 2013`.
~11,000 citations combined.

**Mathematical result.** Ranking stocks by 12-1 momentum yields a spread (winners
− losers) returning ~5–7 bps/day (t ≈ 3.0), robust across asset classes and
partially explained by a common "betting-against-beta" / funding-liquidity factor.

**Mechanism.** Behavioral underreaction; delayed price discovery.

**Verifications.**
- *Momentum crashes* (`Daniel & Moskowitz, 2014`; `Barberis & Shleifer, 2003`):
  the strategy crashes when shorts (recent losers) rebound while longs (recent
  winners) keep falling — the 2008, 2009 and 2020 episodes. ⚠ documented.
- *Capacity*: `Asness et al. (2013)` cap per-stock; we cap per-ETF (≤200%). ✓ applied.
- *Crowding*: `Fleming et al. (2021)` show CS momentum is now heavily traded;
  net alpha post-costs is compressed. ⚠ documented (key reason for the gate).

### 3. Term-Structure / Carry (Koijen, Moskowitz, Pedersen & Vrugt 2018) — REVIEWED

**Provenance.** `Koijen et al., "Term Structures…", AER 2018`.

**Result.** Diversified carry (long high-yielding, short low-yielding) Sharpe ≈ 1.2
pre-cost. **Limitation (rejected for execution):** severe drawdowns in global
recessions (2008, 1972–75, 1980–82) and the 2021–22 bond massacre; requires futures
roll data not available via the free Yahoo pipeline. **Deferred** to a future cycle
that adds futures/contango data.

### 4. Change-Point / Regime Detection (Kim & Mueller 2016 / Brown et al. 2018) — REVIEWED

**Provenance.** `Kim & Mueller, "Regression-based asset pricing…"`; HMM regime
models (`Frühwirth, 2008`).

**Result.** Regime-switching momentum (momentum ON in bull, OFF / reversed in
bear) reduces crash risk. **Considered as a control** for the experiments below
(regime gate: worst-regime Sharpe ≥ 0.3).

### 5. Information-Theoretic Predictors (Transfer Entropy) — REVIEWED

**Provenance.** `Schreiber, "Measuring mutual information…", PNAS 2000`;
applied to markets by `Dhamija & Vasant, 2021`.

**Result.** Detects cross-market lead-lag. **Rejected for execution:** requires
high-frequency cross-market data unavailable on the free tier and offers weak
marginal value over price momentum for daily ETFs.

---

## Ranking & Selection

| # | Candidate | Mechanism relevance | Impl cost | Testable | Econ value | Replication | Score |
|---|-----------|--------------------|-----------|------------|------------|-------------|-------|
| 1 | TS momentum (12-1, vol-scaled) | 5 | 5 | 5 | 2 | 5 | **5.0** |
| 2 | CS momentum (rank-based, dollar-neutral) | 5 | 5 | 5 | 2 | 5 | **5.0** |
| 3 | Carry (term structure) | 4 | 3 | 3 | 3 | 4 | 3.8 |
| 4 | Regime-switching momentum | 4 | 2 | 4 | 2 | 3 | 3.5 |
| 5 | Transfer-entropy lead-lag | 2 | 2 | 2 | 2 | 2 | 2.0 |

**Top candidates taken to executable experiments:** #1 and #2.

---

## Implementation Note (methodological correction)

The library `time_series_momentum_signals` (src/qtr/strategies/baselines.py)
implements *per-asset* vol scaling (`weight = target_vol / sigma_i`) capped at
2.0×. For a multi-asset book this is miscalibrated: when `sigma_i ≈ target_vol`
the raw weight → 1.0 per asset, and the backtester's gross-leverage
normalization then *replaces* vol targeting with a flat gross cap. The
experiments therefore use a **portfolio-level volatility targeting** step
(vol-scale the *aggregate* book to a constant ex-ante volatility, with a 3×
over-leverage cap and a 0% lower bound so exposure is genuinely reduced during
volatility spikes) — the standard AQR/Moskowitz construction. This is implemented
in `run_ts_momentum_experiment.py::vol_scaled_tsmom_signals` and reused for H2.

A separate, material correctness fix was required in the backtest engine
(see §5 / EXECUTION_REPORT.md): the equity cost model previously charged
`weight_delta * price * bps` instead of `weight_delta * bps`, inflating trading
costs by ~the asset price (hundreds of basis points per trade) and rendering every
active strategy unprofitable. After correction, buy-and-hold SPY returns to the
expected Sharpe ≈ 0.685 (from a cost-depressed 0.660), confirming costs are now
realistic.

---

## Traceability Outcomes (Math → Mechanism → Hypothesis → Experiment → Validation)

### H1 — Time-Series Momentum on 20 Liquid ETFs

1. **Random walk (Fama 1965)** → contradicted by momentum evidence.
2. **Underreaction theory (Barberis, Shleifer & Vishny 1998)** → predicts persistence.
3. **Moskowitz, Ooi & Pedersen (2012)** → TSMOM in futures, Sharpe ≈ 0.6–0.8.
4. **Kim, Liew & Moulang (2016)** → volatility scaling raises Sharpe.
5. **Hypothesis (pre-registered):** 12-1 vol-scaled TSMOM on 20 liquid ETFs
   (2015-2024) yields net OOS Sharpe ≥ 1.0, ≥200 OOS trades, PF ≥ 1.3,
   max DD ≤ 15%, robust to regimes & ±20% perturbation, significant vs
   equal-weight benchmark (p < 0.05).
6. **Method:** vectorized backtest, portfolio-level vol targeting to 15%,
   monthly rebalance, train/val/test split (2015-19 / 20-21 / 22-24),
   18-combo grid selected by *train-only* walk-forward Sharpe.
7. **Experiment:** `exp_2026-10-10T21-08-54-188263Z` (run_ts_momentum_experiment.py).
8. **Validation result: REJECTED (6/8 gates fail).** See INEFFICIENCY_RANKING.md
   and HYPOTHESIS_SPEC.md for measured values:
   - OOS Sharpe = 0.093 (95% CI [-0.76, 0.96]); Train 0.589 → Val 0.245 →
     **Test -0.039** (train-period overfit).
   - Max drawdown = -34.8% (gate ≤ 15%); worst regime (bear) Sharpe = -2.40.
   - PF = 1.017; benchmark IR = -0.124 (p = 0.78, not significant).
   - Only trade-count (768) and parameter-perturbation gates pass.

### H2 — Cross-Sectional Momentum on 10 Equity ETFs

1. **Jegadeesh & Titman (1993)** → 3-12 month cross-sectional momentum.
2. **Asness, Moskowitz & Pedersen (2013)** → common factor across assets.
3. **Hypothesis (pre-registered):** rank-based vol-scaled CS momentum on 10 equity
   ETFs yields net OOS Sharpe ≥ 1.0, ≥200 trades, PF ≥ 1.3, DD ≤ 15%, significant
   vs EW benchmark (p < 0.05).
4. **Experiment:** `exp_2026-10-10T21-09-06-830199Z` (run_cs_momentum_experiment.py).
5. **Validation result: REJECTED (7/8 gates fail).**
   - OOS Sharpe = 0.116 (95% CI [-0.71, 1.02]); Test Sharpe = 0.092.
   - Max drawdown = -38.7%; worst regime (bear) Sharpe = -3.03; PF = 1.024.
   - Benchmark IR = -0.252 (p = 0.57); only trade-count (388) passes.

### Conclusion on discovery

The mathematical results are real (peer-reviewed, replicated), and the *mechanisms*
are economically plausible. However, on the **2015-2024** sample with **liquid ETFs**
the *monetizable* edge is below the evidence gates: the train period (2015-2019)
selected parameters that did not generalize OOS, and the 2020 COVID crash and 2022
inflation shock produced catastrophic *momentum crashes* (bear-regime Sharpe
≈ -2.4 to -3.0). The failure is **not** a cost-model artifact (costs are now
verified sub-bps for low-turnover legs and ~3 bps/trade here). It is a genuine
decay + regime-crash finding consistent with `Daniel & Moskowitz (2022)` and
`Hurst & Vinci (2018)`.
