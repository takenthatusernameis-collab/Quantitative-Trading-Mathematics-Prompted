# Inefficiency Ranking

## Phase 4: Market Ranking & Net Opportunity Estimates

### Ranking Methodology

Net Opportunity = (Gross Edge - Transaction Costs) * Capacity * (1 - Competition Decay)

### Ranked Candidates

#### 1. Time-Series Momentum on Equity Index Futures/ETFs
- **Gross Edge**: Sharpe 0.8-1.2 (Moskowitz et al. 2012)
- **Transaction Costs**: ~2-5 bps per trade (ETFs), ~$5-10/futures contract
- **Net Edge**: Estimated Sharpe 0.5-0.9 after costs
- **Capacity**: $1B+ (ETFs), $10B+ (futures)
- **Competition**: High (managed futures funds, retail)
- **Data Availability**: Excellent (yfinance, free)
- **Execution Feasibility**: High (ETFs), Medium (futures require clearing)
- **Net Opportunity Score**: 7/10

#### 2. Cross-Sectional Momentum on Equity ETFs
- **Gross Edge**: Sharpe 0.6-0.9 (Jegadeesh & Titman 1993)
- **Transaction Costs**: ~3-8 bps per trade
- **Net Edge**: Estimated Sharpe 0.3-0.6 after costs
- **Capacity**: $500M+ (liquid ETFs)
- **Competition**: Very High (quant funds, factor ETFs)
- **Data Availability**: Excellent
- **Execution Feasibility**: High
- **Net Opportunity Score**: 5/10

#### 3. Carry on Multiple Asset Classes
- **Gross Edge**: Sharpe 0.8-1.2 (Koijen et al. 2018)
- **Transaction Costs**: Varies by asset class
- **Net Edge**: Sharpe 0.5-0.8 after costs
- **Capacity**: $500M+ (diversified)
- **Competition**: Medium-High
- **Data Availability**: Good (futures), Limited (credit, options)
- **Execution Feasibility**: Medium (multi-asset)
- **Net Opportunity Score**: 6/10

#### 4. Mean Reversion on High-Frequency Data
- **Gross Edge**: Sharpe 0.5-1.0 (intraday)
- **Transaction Costs**: ~1-3 bps per trade (high frequency)
- **Net Edge**: Sharpe 0.2-0.5 after costs
- **Capacity**: $100M+ (high freq)
- **Competition**: Very High (HFT firms)
- **Data Availability**: Requires tick data
- **Execution Feasibility**: Low (requires low-latency infra)
- **Net Opportunity Score**: 3/10

#### 5. Regime-Switching Strategies
- **Gross Edge**: Sharpe 0.4-0.8
- **Transaction Costs**: ~2-5 bps
- **Net Edge**: Sharpe 0.2-0.5
- **Capacity**: $500M+
- **Competition**: Medium
- **Data Availability**: Good
- **Execution Feasibility**: High
- **Net Opportunity Score**: 4/10

### Invalidation Criteria

**Time-Series Momentum** invalidated if:
- Out-of-sample Sharpe < 0.5 for 2+ consecutive years
- Maximum drawdown > 30% in any 12-month period
- Strategy fails during 2008-style crisis (correlation > 0.7 with market)

**Cross-Sectional Momentum** invalidated if:
- Out-of-sample Sharpe < 0.3
- Momentum crash frequency > 20% of years
- Capacity < $100M

### Selected Strategy for Testing

**Time-Series Momentum on 20 liquid ETFs/futures** is the top-ranked candidate because:
1. Strongest academic provenance with testable mechanism
2. Works with existing infrastructure (yfinance + vectorized backtest)
3. Highest capacity among testable strategies
4. Clear falsification criteria

### Universe Selection

**ETFs (15 symbols)**:
- Equities: SPY, QQQ, IWM, EFA, EEM, VWO
- Bonds: TLT, AGG, HYG
- Commodities: GLD, USO, PDBC
- Currencies: UUP, FXE, JPY

**Futures (5 symbols)**:
- ES (S&P 500), NQ (Nasdaq), CL (Crude Oil), GC (Gold), ZB (30Y Bond)

**Total**: 20 symbols across 5 asset classes

### Cost Model Assumptions
- ETFs: 1 bp commission + 1 bp spread + 0.1 bp impact per 1% ADV
- Futures: $0.50/contract + 0.25 tick spread + 0.5 tick slippage
- Crypto: 5 bp taker fee + 2 bp spread + 1 bp slippage

### Capacity Estimates
- ETFs: $1B+ (based on $100M ADV assumption)
- Futures: $10B+ (based on open interest)
- Total estimated capacity: $5B+