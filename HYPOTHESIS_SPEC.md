# Hypothesis Specification

## Phase 5: Falsifiable Hypotheses & Experimental Design

### Hypothesis H1: Time-Series Momentum on Liquid ETFs

**Statement**: A 12-month time-series momentum strategy on 20 liquid ETFs across 5 asset classes generates net out-of-sample Sharpe >= 0.9 with >= 100 pooled trades, statistically significant vs buy-and-hold benchmark (p < 0.05), stable across regimes, and robust to parameter perturbation (±20%).

**Mechanism**: Investor underreaction to news causes trends to persist for 3-12 months. Speculators profit by taking positions with the trend.

**Null Hypothesis (H0)**: Returns follow random walk with drift; momentum strategy Sharpe <= 0.5 OR trades < 100 OR p-value > 0.05 vs benchmark.

**Rejection Conditions** (any one fails):
- Net out-of-sample Sharpe < 0.9
- Pooled out-of-sample trades < 100
- p-value > 0.05 vs benchmark (bootstrap test)
- Instability across regimes (bull/bear/sideways): Sharpe ratio in worst regime < 0.3
- Parameter perturbation (±20%): Sharpe drops > 50% from optimum

### Hypothesis H2: Cross-Sectional Momentum on Equity ETFs

**Statement**: A cross-sectional momentum strategy (top-3 vs bottom-3) on 10 equity ETFs generates net out-of-sample Sharpe >= 0.6 with >= 100 pooled trades.

**Mechanism**: Relative performance persists due to delayed price discovery and investor attention.

**Null Hypothesis (H0)**: Cross-sectional momentum does not generate significant risk-adjusted returns.

**Rejection Conditions**:
- Net out-of-sample Sharpe < 0.6
- Pooled trades < 100
- p-value > 0.05 vs equal-weight benchmark

### Experimental Design

#### Universe
20 liquid ETFs/futures across 5 asset classes:
- Equities: SPY, QQQ, IWM, EFA, EEM, VWO
- Bonds: TLT, AGG, HYG
- Commodities: GLD, USO, PDBC
- Currencies: UUP, FXE, JPY
- Futures: ES, NQ, CL, GC, ZB

#### Data Splits
- **Train**: 2015-01-01 to 2019-12-31 (5 years)
- **Validation**: 2020-01-01 to 2021-12-31 (2 years)
- **Test**: 2022-01-01 to 2024-12-31 (3 years, protected)

#### Walk-Forward Re-optimization
- Monthly re-optimization on trailing 24-month window
- Out-of-sample test on next 1-month window
- Parameters: lookback ∈ {63, 126, 252}, skip ∈ {1, 5, 21}, n_top ∈ {1, 3, 5}

#### Cost Model
- ETFs: 1 bp commission + 1 bp spread + 0.1 bp impact per 1% ADV
- Futures: $0.50/contract + 0.25 tick spread + 0.5 tick slippage
- Crypto: 5 bp taker fee + 2 bp spread + 1 bp slippage

#### Evidence Gates
1. Net out-of-sample Sharpe >= 0.9
2. >= 100 pooled out-of-sample trades
3. Statistically significant vs benchmark (p < 0.05, bootstrap)
4. Stable across regimes (bull/bear/sideways): worst regime Sharpe >= 0.3
5. Robust to parameter perturbation (±20%): Sharpe drops <= 50% from optimum

#### Validation Protocol
- Bootstrap 1000 samples for Sharpe CI
- Walk-forward 5-fold for stability
- Regime analysis: bull (VIX < 20), bear (VIX > 30), sideways (VIX 20-30)
- Parameter sensitivity: ±20% perturbation test
- Multiple testing correction: Benjamini-Hochberg

### Implementation Plan

1. Create `run_ts_momentum_experiment.py` with full pipeline
2. Implement volatility-scaled time-series momentum (per Kim et al. 2016)
3. Run with experiment tracking
4. Apply evidence gates rigorously
5. Generate MATHEMATICAL_DISCOVERY_REPORT.md, INEFFICIENCY_RANKING.md, HYPOTHESIS_SPEC.md

### Deliverables
1. `MATHEMATICAL_DISCOVERY_REPORT.md` - Literature review with traceability chains
2. `INEFFICIENCY_RANKING.md` - Market ranking with net opportunity estimates
3. `HYPOTHESIS_SPEC.md` - Falsifiable hypotheses with rejection conditions
4. Experiment artifacts in `.experiments/` with full reproducibility
5. `NEXT_TASK.md` - Next bottleneck and experiment for subsequent agent