# Next Agent Task: Mathematical Discovery & Validated Hypothesis Testing

## Mission
Execute Phases 3-5 of the research prompt to discover and validate a genuine trading edge.

## Context
- Prompt refinement complete (2 cycles, all scores ≥ 4/5)
- 10 experiments run, all baselines failed evidence gates
- Best candidate (momentum 252/21) was a 1-trade delayed buy-and-hold, not a real strategy
- Infrastructure ready: backtesting engine, experiment tracking, data fetching, cost model

## Task Definition

### Phase 3: Investigate Mathematical Discoveries
1. **Search academic literature** for mathematically grounded market anomalies with:
   - Proven theoretical mechanism (not just empirical pattern)
   - Peer-reviewed provenance
   - Known limitations and decay estimates
2. **Priority areas** (from PROMPT.MD):
   - Time-series momentum / trend following (Moskowitz, Ooi, Pedersen 2012)
   - Cross-sectional momentum (Jegadeesh, Titman 1993; Asness, Moskowitz, Pedersen 2013)
   - Term structure / carry (Koijen, Moskowitz, Pedersen, Vrugt 2018)
   - Change-point detection / regime identification
   - Information-theoretic predictors (transfer entropy, mutual information)
3. **Output**: Ranked list with traceable chain: Mathematical Result → Mechanism → Market Hypothesis → Falsifiable Test

### Phase 4: Identify Promising Automatable Inefficiencies
1. **Rank candidate markets** by net opportunity (after costs, capacity, competition)
2. **Required**: Evidence of persistent inefficiency, data availability, execution feasibility
3. **Reject**: Markets where costs exceed gross edge, or capacity < $1M
4. **Output**: Ranked market/inefficiency pairs with invalidation criteria

### Phase 5: Generate & Test Hypotheses
For the top 1-2 candidates:
1. **Formulate hypothesis** with:
   - Specific mechanism (e.g., "12-month momentum persists due to investor underreaction to earnings news")
   - Null hypothesis (e.g., "returns follow random walk with drift")
   - Rejection conditions (e.g., "out-of-sample Sharpe < 0.5 OR trades < 100 OR p-value > 0.05 vs benchmark")
2. **Design minimum viable experiment**:
   - Universe: 10-20 liquid futures/ETFs across asset classes
   - Train: 2015-2019, Val: 2020-2021, Test: 2022-2024 (protected)
   - Walk-forward re-optimization monthly/quarterly
   - Realistic cost model (commission, spread, impact)
3. **Implement and run** with experiment tracking
4. **Apply evidence gates**:
   - Net out-of-sample Sharpe ≥ 0.9
   - ≥ 100 pooled out-of-sample trades
   - Statistically significant vs benchmark (p < 0.05, bootstrap)
   - Stable across regimes (bull/bear/sideways)
   - Robust to parameter perturbation (±20%)

## Deliverables
1. `MATHEMATICAL_DISCOVERY_REPORT.md` - Literature review with traceability chains
2. `INEFFICIENCY_RANKING.md` - Market ranking with net opportunity estimates
3. `HYPOTHESIS_SPEC.md` - Falsifiable hypotheses with rejection conditions
4. Experiment artifacts in `.experiments/` with full reproducibility
5. `NEXT_TASK.md` - Next bottleneck and experiment for subsequent agent

## Constraints
- Do not weaken evidence gates
- Do not optimize against test set
- Preserve all failed experiments
- No live trading, no API keys in code
- Max 2 CPU hours per experiment
- Use existing infrastructure (qtr.backtest, qtr.tracking, qtr.strategies)

## Success Criteria
At least one hypothesis passes ALL evidence gates with independent out-of-sample validation.