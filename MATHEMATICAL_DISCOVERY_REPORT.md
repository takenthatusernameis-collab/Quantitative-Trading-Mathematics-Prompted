# Mathematical Discovery Report

## Phase 3: Literature Review & Traceability Chains

### 1. Time-Series Momentum (Moskowitz, Ooi, Pedersen 2012)

**Mathematical Result**: For 58 futures contracts across equity indices, currencies, commodities, and bonds, past 12-month returns predict next-month returns with t-statistics > 3.0. The effect persists ~12 months then partially reverses.

**Mechanism**: Speculators take positions with the trend, profiting at the expense of hedgers. Underreaction to news and trend-following behavior.

**Market Hypothesis**: Time-series momentum exists in liquid futures markets due to delayed price discovery and hedging pressure.

**Falsifiable Test**: Long-short 12-month momentum strategy on 20 liquid futures/ETFs; test if out-of-sample Sharpe > 0.9 with >100 trades.

**Limitations**: Kim et al. (2016) show volatility scaling drives much of the effect. Hurst et al. (2017) find decay after 2000s.

### 2. Cross-Sectional Momentum (Jegadeesh, Titman 1993)

**Mathematical Result**: Buying past 3-12 month winners and selling losers yields ~1% monthly excess returns (t-stat 3.07), not explained by Fama-French factors.

**Mechanism**: Underreaction to earnings news, delayed price discovery.

**Market Hypothesis**: Cross-sectional momentum persists across liquid assets.

**Falsifiable Test**: Top-3 momentum deciles vs bottom-3; test significance vs benchmark.

**Limitations**: Momentum crashes (2009, 2000). Decay over time. Capacity constraints.

### 3. Value and Momentum Everywhere (Asness, Moskowitz, Pedersen 2013)

**Mathematical Result**: Value and momentum premia exist across 8 asset classes with common factor structure. Three-factor model (market, value, momentum) explains returns.

**Mechanism**: Funding liquidity risk links value and momentum across markets.

**Market Hypothesis**: Diversified value-momentum portfolio captures persistent risk premium.

**Falsifiable Test**: Long-short value + momentum across asset classes; test alpha vs 3-factor model.

### 4. Carry (Koijen, Moskowitz, Pedersen, Vrugt 2018)

**Mathematical Result**: Carry predicts returns in equities, bonds, commodities, currencies, credit, options. Diversified carry Sharpe = 1.2.

**Mechanism**: Time-varying risk premia; carry = expected return decomposition.

**Market Hypothesis**: High-carry assets outperform low-carry assets.

**Falsifiable Test**: Long high-carry, short low-carry across asset classes.

**Limitations**: Severe drawdowns during global recessions (2008, 1972-75, 1980-82).

### 5. Change-Point Detection / Regime Identification

**Mathematical Result**: Market regimes (bull/bear/sideways) are detectable via structural breaks in return series.

**Mechanism**: Regime-dependent strategy performance; momentum works in bull, fails in bear.

**Market Hypothesis**: Regime-aware momentum outperforms static momentum.

**Falsifiable Test**: Regime-switching model with walk-forward validation.

### 6. Information-Theoretic Predictors

**Mathematical Result**: Transfer entropy and mutual information detect information flow between markets.

**Mechanism**: Lead-lag relationships across markets.

**Market Hypothesis**: Information flow predicts returns.

**Falsifiable Test**: Entropy-based signals with bootstrap significance testing.

## Ranking & Selection

**Top Candidate: Time-Series Momentum on Liquid Futures/ETFs**
- Strongest academic provenance (Moskowitz et al. 2012, 4000+ citations)
- Testable with existing infrastructure (yfinance data, vectorized backtest)
- Mechanism: underreaction + speculator positioning
- Limitations: volatility scaling, decay, capacity

**Runner-Up: Cross-Sectional Momentum on Equity ETFs**
- Jegadeesh & Titman (1993), most replicated anomaly
- Works with ETF data (existing infrastructure)
- Limitations: momentum crashes, capacity

## Traceability Chain (Selected)

1. Random walk hypothesis (Fama 1965) → contradicted by momentum evidence
2. Underreaction theory (Barberis, Shleifer, Vishny 1998) → predicts momentum
3. Moskowitz et al. (2012) → time-series momentum in futures
4. Hypothesis: 12-month momentum on liquid ETFs persists net of costs
5. Method: Vectorized backtest with realistic cost model
6. Validation: Train/val/test split, walk-forward, bootstrap CIs
7. Experiment: run_ts_momentum_experiment.py