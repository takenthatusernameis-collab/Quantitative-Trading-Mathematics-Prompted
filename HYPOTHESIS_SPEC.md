# Hypothesis Specification

## Phase 5: Falsifiable Hypotheses & Experimental Design

Both pre-registered hypotheses below were taken to executable minimum-viable
experiments using the **existing** infrastructure (`qtr.backtest.engine`,
`qtr.data.fetcher`, `qtr.tracking.experiment`, `qtr.strategies`, `qtr.validation`).
Evidence gates are the **stricter** union of PROMPT_V2.md (frozen) and the
HYPOTHESIS_SPEC gates. No gate was weakened.

---

### Hypothesis H1: Time-Series Momentum on 20 Liquid ETFs

**Statement.** Volatility-scaled (12, skip-1) time-series momentum on 20 liquid
ETFs across 5 asset classes generates net pooled out-of-sample (Val+Test) Sharpe
≥ 1.0 with ≥ 200 trades, PF ≥ 1.3, max DD ≤ 15%, stable across regimes
(worst-regime Sharpe ≥ 0.3), robust to ±20% parameter perturbation (OOS Sharpe
≥ 0.5 × optimum), and significant vs an equal-weight benchmark (p < 0.05).

**Mechanism.** Underreaction to earnings/news (Barberis et al. 1998) + speculator
trend-following (Moskowitz, Ooi & Pedersen 2012), amplified by volatility
scaling (Kim, Liew & Moulang 2016).

**Null (H0).** Returns follow a random walk; TSMOM Sharpe ≤ 0. We test H1 by
rejecting H0 on the protected OOS window only.

**Pre-registration.**
- Universe: 20 ETFs (see INEFFICIENCY_RANKING.md); data source Yahoo Finance
  daily, cached; `^VIX` used for regime labels only (not traded).
- Train: 2015-01-01 → 2019-12-31; Val: 2020-01-01 → 2021-12-31; Test: 2022-01-01
  → 2024-12-31 (**protected holdout — used only for gate evaluation, never for
  parameter selection**).
- Selection: 18-combo grid `lookback ∈ {63,126,252} × skip ∈ {1,5,21} ×
  long_only ∈ {T,F}`, scored by **train-only** 4-fold walk-forward Sharpe.
  Selected: `long_only=True, lookback=126, skip=1`.
- Signal: portfolio-level volatility targeting (target 15% annual, 3× over-leverage
  cap, 0% lower bound), monthly rebalance. Cost model: 1+1 bp + 0.1 bp/1% ADV.
- Compute budget: ≤ 2 CPU-h (actual < 3 min). Seed: 42.

**Measured (experiment `exp_2026-10-10T21-08-54-188263Z`):**

| Split | Sharpe |
|-------|--------|
| Train (2015-2019) | 0.589 |
| Val (2020-2021) | 0.245 |
| Test (2022-2024, protected) | -0.039 |
| **OOS Val+Test (gated)** | **0.093** (95% CI [-0.758, 0.962]) |

| Gate (OOS) | Value | Threshold | Result |
|------------|-------|-----------|--------|
| Net Sharpe | 0.093 | ≥ 1.0 | FAIL |
| Trades | 768 | ≥ 200 | PASS |
| Profit factor | 1.017 | ≥ 1.3 | FAIL |
| Max drawdown | -34.8% | ≤ 15% | FAIL |
| Walk-forward stability | 0.158 | ≥ 0.7 | FAIL |
| Param perturbation (±20%) | 0.059 | ≥ 0.046 | PASS |
| Regime stability (worst) | -2.40 | ≥ 0.3 | FAIL |
| Benchmark significance (p) | 0.782 | < 0.05 | FAIL |

Benchmark (equal-weight, vol-scaled buy-and-hold on the 20 ETFs): Sharpe 0.295,
total return 31.1%. Strategy IR vs benchmark = -0.124 (α = -1.5%/yr, p = 0.78 ⇒
**no statistically significant alpha**).

**Verdict: REJECT H1.** 6/8 gates fail. The train period overfit (train Sharpe 0.589,
train walk-forward Sharpe 1.194) but the protected test produced a negative
Sharpe. The dominant failure modes are the 2020 COVID crash and 2022 inflation
shock (bear-regime Sharpe -2.40), i.e. the documented *momentum crash*.

---

### Hypothesis H2: Cross-Sectional Momentum on 10 Equity ETFs

**Statement.** Volatility-scaled rank-based (top-N vs bottom-N) cross-sectional
momentum on 10 equity ETFs generates net OOS Sharpe ≥ 1.0 with ≥ 200 trades,
PF ≥ 1.3, max DD ≤ 15%, significant vs EW benchmark (p < 0.05).

**Mechanism.** Relative-performance persistence from delayed price discovery and
investor attention (Jegadeesh & Titman 1993; Asness et al. 2013).

**Pre-registration.**
- Universe: SPY, QQQ, IWM, EFA, EEM, VWO, EWJ, EWZ, INDA, VNQ.
- Same splits, cost model, vol-targeting, and walk-forward selection protocol as H1.
- Grid: `lookback ∈ {63,126,252} × skip ∈ {1,5,21} × n_top ∈ {1,3,5} ×
  long_only ∈ {T,F}` (54 combos); selection by train-only walk-forward Sharpe.
  Selected: `long_only=True, lookback=252, skip=21`.

**Measured (experiment `exp_2026-10-10T21-09-06-830199Z`):**

| Split | Sharpe |
|-------|--------|
| Train | 0.636 |
| Val | 0.147 |
| Test | 0.092 |
| **OOS** | **0.116** (95% CI [-0.714, 1.024]) |

| Gate (OOS) | Value | Threshold | Result |
|------------|-------|-----------|--------|
| Net Sharpe | 0.116 | ≥ 1.0 | FAIL |
| Trades | 388 | ≥ 200 | PASS |
| Profit factor | 1.024 | ≥ 1.3 | FAIL |
| Max drawdown | -38.7% | ≤ 15% | FAIL |
| Walk-forward stability | 0.183 | ≥ 0.7 | FAIL |
| Param perturbation | 0.036 | ≥ 0.058 | FAIL |
| Regime stability (worst) | -3.03 | ≥ 0.3 | FAIL |
| Benchmark significance (p) | 0.573 | < 0.05 | FAIL |

Benchmark (EW buy-and-hold, 10 equity ETFs): Sharpe 0.365, −50.8% drawdown.
Strategy IR = -0.252, p = 0.57 (no alpha).

**Verdict: REJECT H2.** 7/8 gates fail.

---

### Implementation Plan (executed)
1. ✅ Created `run_ts_momentum_experiment.py` — full H1 pipeline + gates.
2. ✅ Implemented portfolio-level volatility scaling (Kim et al. 2016; see
   implementation note in MATHEMATICAL_DISCOVERY_REPORT.md §4).
3. ✅ Ran with experiment tracking (artifacts in `.experiments/artifacts/`).
4. ✅ Applied evidence gates rigorously — **rejected** (no gate weakening).
5. ✅ Created `run_cs_momentum_experiment.py` for H2.
6. ✅ Fixed the backtest-engine cost-model units bug (essential to make the gates
   meaningful — see EXECUTION_REPORT.md).

### Deliverables
1. `MATHEMATICAL_DISCOVERY_REPORT.md` — literature review + traceability chains.
2. `INEFFICIENCY_RANKING.md` — market ranking + measured net edge.
3. `HYPOTHESIS_SPEC.md` — pre-registered hypotheses + gate outcomes (this file).
4. Experiment artifacts in `.experiments/`:
   - `exp_2026-10-10T21-08-54-188263Z/` (H1) — prices, volumes, vix, signals,
     equity, trades, param-grid (18 combos), summary.json.
   - `exp_2026-10-10T21-09-06-830199Z/` (H2) — same structure (54 combos).
   - All with git commit, seeds, dependency versions (see tracker JSONL).
5. `NEXT_TASK.md` — next bottleneck + experiment for the next agent.
