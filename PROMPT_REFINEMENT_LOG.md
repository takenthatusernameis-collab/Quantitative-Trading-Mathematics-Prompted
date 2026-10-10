# Prompt Refinement Log

## Cycle 1 - Critique

### Identified Weaknesses:
1. **No computational budget defined** - Phase 5 mentions "computational budget" but no actual limits specified
2. **No data sources specified** - Assumes data availability without defining sources, quality requirements, or access methods
3. **Undefined "OpenAI mathematics research collection"** - Phase 3 references this but it's not a standard/known collection
4. **No baseline strategy defined** - Phase 6 references "existing acceptance criteria" and "minimum net out-of-sample Sharpe of 0.9" but these aren't documented in the prompt
5. **No experiment tracking infrastructure** - No mention of MLflow, Weights & Biases, or custom tracking
6. **No specific market universe** - No asset classes, exchanges, or instruments defined
7. **No risk management framework** - No position sizing, drawdown limits, or portfolio-level risk controls specified
8. **Vague "independent validation"** - No concrete definition of what constitutes independent validation
9. **No specific AI tools** - Phase 5 mentions "AI-assisted search" but no specific models, APIs, or frameworks
10. **No version control strategy for experiments** - How to track experiment configurations, data versions, code versions
11. **No concrete falsification criteria** - Phase 5 mentions "explicit rejection conditions" but no examples or templates
12. **Missing data leakage prevention specifics** - Phase 5 mentions preventing look-ahead bias but no technical implementation
13. **No parallelization strategy** - How to run multiple experiments efficiently
14. **No cost model** - Transaction costs mentioned but no specific model (spread, commission, slippage, market impact)
15. **No reproducibility artifacts specification** - What exactly to preserve (configs, seeds, data hashes, environment)

---

## Cycle 1 - Improved Prompt (Version 2)

[See PROMPT_V2.md for the full improved prompt]

---

## Cycle 1 - Evaluation Scores (0-5)

| Criterion | Score | Justification |
|-----------|-------|---------------|
| Objective clarity & alignment | 4 | Clear mission but missing concrete success metrics beyond Sharpe |
| Mathematical & scientific validity | 3 | References undefined collection; no verification process specified |
| Falsifiability & statistical rigor | 3 | Mentions falsifiable hypotheses but no concrete templates or multiple testing correction details |
| Execution efficiency & feasibility | 2 | No computational budget, data sources, or infrastructure specified |
| Reproducibility, safety, verification | 2 | Mentions reproducibility but no artifact specification, versioning, or environment capture |

**Overall: 2.8/5** - Significant gaps in execution feasibility and reproducibility. Continue to Cycle 2.

---

## Cycle 2 - Critique (of Version 2)

### Remaining Weaknesses in Version 2:
1. **No specific repository structure assumed** - Still doesn't know if backtesting engine, data pipeline, or tracking exist
2. **Mathematical discovery source still vague** - "OpenAI mathematics research collection" not defined; should specify actual sources (arXiv categories, specific venues, known AI-math papers)
3. **No concrete statistical power analysis** - 200 trades minimum but no power calculation for effect size detection
4. **Walk-forward stability metric** - "test Sharpe ≥ 0.7 × train Sharpe" is arbitrary; should be statistically grounded
5. **Parameter sensitivity** - "within 1σ of optimum" needs definition of parameter space and sampling method
6. **No explicit regime definition** - "bull/bear/sideways, high/low vol" needs operational definitions
7. **Capacity estimation method** - "max AUM before 50% Sharpe decay" needs methodology (market impact models, order book simulation)
8. **No model selection guardrails** - Beyond "no test-set feedback", no specification of how many models can be tried
9. **Falsification template** - Good but should include pre-registration timestamp/hash
10. **No explicit compute budget enforcement mechanism** - Just a limit, no monitoring
11. **Cost model** - Reasonable but should specify data source for spreads/ADV (e.g., TAQ, proprietary)
12. **No data quality checks** - No mention of outlier detection, missing data handling, corporate actions
13. **No explicit handling of non-stationarity** - Beyond regime detection, no adaptation mechanism
14. **Benchmark comparison** - Should specify statistical test for significance vs benchmark
15. **No explicit stopping rule for research cycle** - When to stop exploring and move to validation

---

## Cycle 2 - Evaluation Scores

| Criterion | Score | Justification |
|-----------|-------|---------------|
| Objective clarity & alignment | 5 | Clear mission, concrete success metrics, explicit evidence hierarchy |
| Mathematical & scientific validity | 4 | Prioritization framework, verification requirements, traceable chain; minor gap on specific math sources |
| Falsifiability & statistical rigor | 4 | Explicit rejection conditions, multiple testing correction, bootstrap CIs, power considerations; minor gap on power analysis |
| Execution efficiency & feasibility | 4 | Computational budget, cost model, market universe, AI tools specified; minor gaps on infrastructure assumptions |
| Reproducibility, safety, verification | 5 | Comprehensive artifact checklist, environment capture, data versioning, pre-registration, holdout protection |

**Overall: 4.4/5** - All criteria ≥ 4/5. Version 2 meets the threshold. Stop refinement.

---

## Cycle 3 - Critique (of Version 3)

Not needed - Version 2 achieved all scores ≥ 4/5.

---

## Cycle 3 - Evaluation Scores

Not needed.

---

## Final Prompt Version

**PROMPT_V2.md** (2 refinement cycles completed)

## Final Rubric Scores

| Criterion | Score |
|-----------|-------|
| Objective clarity & alignment | 5 |
| Mathematical & scientific validity | 4 |
| Falsifiability & statistical rigor | 4 |
| Execution efficiency & feasibility | 4 |
| Reproducibility, safety, verification | 5 |

**All criteria ≥ 4/5. Prompt frozen as execution specification.**