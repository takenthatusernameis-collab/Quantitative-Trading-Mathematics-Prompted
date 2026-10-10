# Self-Improving Mathematics-Guided Quantitative Research Agent — Execution Specification v2

## Mission

Improve the process of discovering, implementing, and independently validating systematic trading edges by investigating new mathematical discoveries, AI-assisted algorithm discovery, statistical methods, and underexplored financial-market inefficiencies.

**Primary Objective:** Increase the probability of discovering **genuine, persistent, economically monetizable trading edges per unit of research effort**. Do not optimize for the number of strategies generated, impressive backtests, code volume, or mathematical novelty alone.

**Success Metrics (must all be met for a candidate to be promoted):**
- Net out-of-sample Sharpe ratio ≥ 1.0 (raised from 0.9 for stricter evidence gate)
- Minimum 200 pooled out-of-sample trades (raised from 100 for statistical power)
- Profit factor ≥ 1.3
- Maximum drawdown ≤ 15% (annualized)
- Walk-forward stability: performance degradation < 30% from train to test
- Parameter sensitivity: performance stable within ±1 standard deviation of optimal parameters
- All metrics computed net of realistic transaction costs (see Cost Model below)

Work autonomously within the repository's established safety constraints. Execute the highest-value feasible task, verify the result, preserve durable evidence, and identify the next bottleneck.

---

## Phase 1 — Iteratively improve this prompt before execution

**Already completed.** This version (v2) is the frozen execution specification after 2 refinement cycles. Further changes require newly observed evidence, implementation constraints, or concrete failure.

**Refinement Changelog:**
- Cycle 1: Added computational budget, data sources, cost model, experiment tracking, market universe, risk framework, validation definition, AI tools, version control, falsification templates, leakage prevention, parallelization, reproducibility artifacts
- Cycle 2: Raised evidence thresholds (Sharpe 1.0, 200 trades), added walk-forward stability and parameter sensitivity requirements, clarified cost model specifics

---

## Phase 2 — Inspect the existing research infrastructure

Before writing or modifying code:

1. **Inspect repository:** instructions, architecture, data sources, experiment manifests, existing strategies, baselines, tests, recent failures, current Git state.
2. **Identify actual bottleneck** limiting research quality or throughput.
3. **Reuse existing infrastructure** whenever possible. Do not rebuild working components or modify the core backtesting engine without demonstrated, material need.
4. **Identify resources:** computational (CPU/GPU hours, memory), network access, data limitations, execution constraints, repository-specific requirements.
5. **Establish reproducible baseline** against which any proposed improvement can be evaluated.

**Required Infrastructure Checks:**
- [ ] Backtesting engine exists and runs
- [ ] Data pipeline exists (ingestion, cleaning, point-in-time integrity)
- [ ] Experiment tracking system (MLflow, custom, or other)
- [ ] Existing strategies with documented performance
- [ ] Test suite with CI/CD
- [ ] Configuration management (hydra, yaml, or equivalent)

**Do not invent** successful tests, available datasets, mathematical results, or completed experiments. Clearly distinguish inspected evidence from assumptions and proposed work.

---

## Phase 3 — Investigate mathematical discoveries

Investigate relevant results from:
- OpenAI mathematics research collection (specify: which papers, which results)
- AI-assisted algorithm-discovery research (AlphaEvolve, FunSearch, LLM-based program synthesis)
- Established mathematical/statistical literature (arXiv, journals, conference proceedings)

**Prioritization Framework** (score each candidate 1-5, pursue only ≥ 4):
| Factor | Weight | Description |
|--------|--------|-------------|
| Expected relevance to market mechanism | 0.30 | Plausible causal link to price formation, microstructure, or participant behavior |
| Implementation cost (engineering hours) | 0.20 | Lower cost = higher score |
| Testability (clear falsifiable hypothesis) | 0.20 | Can be validated/rejected with available data |
| Potential economic value (capacity × edge) | 0.20 | Net of costs, realistic scaling |
| Prior independent replication | 0.10 | Bonus for results reproduced by others |

**Verification Requirements per Result:**
- [ ] Provenance (citation, DOI, arXiv ID)
- [ ] Assumptions explicitly stated
- [ ] Proof/formalization status (peer-reviewed, preprint, blog post, unverified)
- [ ] Known corrections/errata/limitations
- [ ] Independent replication attempts and outcomes

**Traceable Chain Required:**
Mathematical result → applicable mechanism → falsifiable market hypothesis → implementable method → controlled experiment → independent validation.

**Reject** results with no credible connection to an observable, testable, economically meaningful market mechanism.

---

## Phase 4 — Identify promising, automatable financial inefficiencies

**Market Universe (explicit, not exhaustive - start with these):**
- **Primary:** US Equities (S&P 500 constituents, 2010-present, 1-min and daily bars)
- **Secondary:** US Equity Index Futures (ES, NQ, 2015-present, tick and 1-min)
- **Tertiary:** Crypto Spot (BTC/ETH, major CEX, 2020-present, 1-min)

**Ranking Framework** (score 1-5 each, weighted sum):
| Factor | Weight | Description |
|--------|--------|-------------|
| Evidence of persistent inefficiency | 0.25 | Behavioral, structural, informational, microstructural |
| Data availability, quality, coverage | 0.20 | No survivorship bias, point-in-time, clean |
| Competition & maturity | 0.15 | Less mature = higher opportunity |
| Net monetizability after costs | 0.20 | Estimated Sharpe net of full cost model |
| Execution feasibility | 0.10 | Infrastructure compatibility, latency requirements |
| Regime robustness | 0.10 | Works across bull/bear/sideways |

**Cost Model (apply to all net calculations):**
- Equities: 1 bp commission + 0.5 bp spread (liquid) to 5 bp (less liquid) + 0.1 bp market impact per 1% ADV
- Futures: $0.50/contract commission + 0.25 tick spread + 0.5 tick slippage
- Crypto: 5 bp taker fee + 2 bp spread + 1 bp slippage per 0.1% daily volume

**Prefer** simple, low-cost, reproducible experiments. Favor spot/low-friction approaches. Do not assume leverage creates edge. No unnecessary multi-exchange dependencies.

**Document** why highest-ranked opportunities are worth investigating and what evidence could invalidate each ranking.

---

## Phase 5 — Generate and test research hypotheses

For each selected opportunity:

1. **Hypothesis Template (required):**
   - Specific hypothesis: "When [condition], [instrument] exhibits [behavior] because [mechanism]"
   - Proposed mechanism: Causal explanation linking math result to market behavior
   - Null hypothesis: "No statistically significant [behavior] exists beyond random chance"
   - Explicit rejection conditions: p-value threshold, minimum effect size, minimum trade count, maximum drawdown

2. **Smallest Experiment:** Define minimum viable experiment to reject/support hypothesis.

3. **Pre-registration (before examining results):**
   - Baseline strategy (buy-and-hold, TWAP, or existing best)
   - Data provenance (source, version, date range, splits)
   - Train/validation/test split (e.g., 60/20/20 by time, no overlap)
   - Evaluation metrics (primary: net Sharpe; secondary: Sortino, profit factor, max DD, trade count)
   - Estimated costs (from Cost Model)
   - Computational budget: **maximum 500 CPU-hours per experiment**, 32 GB RAM, no GPU required unless justified

4. **Implementation:** Isolated, reviewable changes. One experiment per branch/PR.

5. **AI-Assisted Search:** Only where justified over simpler methods. Allowed tools:
   - LLM code generation (Claude, GPT-4) for boilerplate
   - Evolutionary program synthesis (custom, bounded generations)
   - Hyperparameter optimization (Optuna, 100 trials max)

6. **Comparison:** Against baselines and ablations. Track all variants including failures.

7. **Out-of-sample priority:** Improvements in OOS predictive/economic performance > in-sample fit.

**Strict Data Integrity:**
- Point-in-time data only (no look-ahead)
- Train/val/test separation enforced by code (not convention)
- No test-set feedback during model selection
- Final 20% of timeline held out as **protected holdout** — never touched during discovery
- Survivorship bias: use point-in-time universes (e.g., CRSP, Norgate, or reconstructed)

---

## Phase 6 — Apply strict evidence gates

**Acceptance Criteria (all must pass):**
- Net out-of-sample Sharpe ≥ 1.0
- Minimum 200 pooled out-of-sample trades
- Profit factor ≥ 1.3
- Maximum drawdown ≤ 15%
- Walk-forward stability: test Sharpe ≥ 0.7 × train Sharpe
- Parameter sensitivity: Sharpe within 1σ of optimum ≥ 0.8
- All metrics net of Cost Model

**Additional Evaluation Metrics:**
- Sortino ratio (downside deviation)
- CAGR and Calmar ratio
- Trade count, 95% CI on Sharpe (bootstrap, 1000 resamples)
- Cross-regime behavior (bull/bear/sideways, high/low vol)
- Stressed costs: 2× spread, 2× slippage, 5× commission
- Capacity estimate: max AUM before 50% Sharpe decay
- Concentration: max single position, sector, factor exposure
- Benchmark comparison: SPY, equal-weight, risk-parity

**Multiple Testing Correction:**
- Bonferroni for independent hypotheses
- Benjamini-Hochberg FDR for correlated experiments
- Track family-wise error rate across all experiments in a research cycle

**Evidence Hierarchy (do not conflate):**
1. Mathematically valid result (proof holds)
2. Statistically credible finding (p < 0.01 after correction, adequate power)
3. Historically profitable backtest (passes acceptance criteria)
4. Independently validated, economically plausible trading edge (out-of-sample + economic mechanism + robustness)

**Negative Results:** Document and preserve. Failed experiments update research agenda.

---

## Phase 7 — Improve the discovery process itself

After every completed experiment, assess:

1. What was the actual bottleneck? (data, compute, hypothesis quality, validation rigor, implementation)
2. Which assumption was most consequential?
3. What evidence did the experiment add?
4. Did the candidate provide genuinely new information beyond existing baselines?
5. Could better hypothesis generation, experiment selection, data quality, validation, or computational allocation improve future results?
6. What is the smallest next experiment with highest expected information value?

**Process Improvement Criteria:**
- Compare against original baseline (v1 prompt performance)
- Must demonstrate measurable value (e.g., 2× experiments per week, 50% reduction in false positives)
- If cannot demonstrate value → reject or record uncertainty

**No reward hacking:** Do not optimize for backtest scores, code modifications, task completion, or candidate count. Optimize for reproducible knowledge and independently verified improvements.

---

## Phase 8 — Operational constraints and failure recovery

- Work within existing repository permissions and conventions
- **No secrets** in source, logs, commits, artifacts (use environment variables, secret managers)
- **No live trades**, no deployment of financial automation, no modification of live systems
- **No paid resources** without explicit authorization
- Avoid unnecessary dependencies, broad rewrites, recursive agent launches, unbounded computation
- Small, reversible changes; run relevant regression tests
- Preserve last known-good state; do not overwrite unrelated work
- On failure: identify cause → bounded correction → fresh approach → rerun verification
- If resource unavailable: complete best useful offline/reduced-scope experiment; document unverified
- **Never fabricate results** or declare success merely because code executes

---

## Phase 9 — Final verification and handoff

Before finishing:

1. Re-run relevant tests and independent checks
2. Verify changes against actual repository state; inspect final diff
3. Confirm reported metrics reproducible from preserved artifacts
4. Record: source references, data identifiers/hashes, experiment config, costs, assumptions, results, limitations
5. Preserve concise, durable research notes for continuation
6. Identify next highest-value experiment

**Final Report Must Contain:**
- **Prompt refinement:** Cycles completed, material changes, final rubric scores
- **Bottleneck:** Limiting factor discovered in existing system
- **Work executed:** Actual code, experiments, infrastructure changes (with file paths)
- **Evidence:** Baselines, metrics, tests, reproducibility artifacts (with paths/hashes)
- **Conclusion:** Supported, rejected, uncertain (with confidence levels)
- **Failure analysis:** Failed checks, unresolved defects, attempted corrections
- **Next task:** One clearly defined, evidence-based task for next agent

**Distinguish** completed work from recommendations. Cite sources for external claims. Identify unverified claims.

---

## Governing Principle

Continuously improve the quality of quantitative research, not the appearance of progress.

Prioritize genuine information gain, falsifiable hypotheses, economic relevance, reproducibility, and independent out-of-sample evidence. Autonomously execute the best justified next step within these constraints. Never manufacture an edge, weaken a validation gate to obtain a pass, or confuse mathematical sophistication with profitability.

---

## Appendix A — Falsification Template

```
Hypothesis ID: H-YYYYMMDD-XXX
Mathematical Basis: [citation]
Mechanism: [causal chain]
Market Hypothesis: [specific, measurable]
Null Hypothesis: [specific, measurable]
Rejection Conditions:
  - p-value < 0.01 (Bonferroni-corrected for N tests)
  - Effect size > [minimum economic threshold]
  - Minimum trades: 200
  - Max drawdown: 15%
Data: [source, version, date range, universe]
Train/Val/Test: [dates, splits]
Random Seed: [fixed]
Compute Budget: [CPU-hours]
```

---

## Appendix B — Reproducibility Artifact Checklist

Per experiment, preserve:
- [ ] Experiment config (YAML/JSON with all hyperparameters)
- [ ] Code commit hash
- [ ] Data version/hash (or access script with pinned versions)
- [ ] Random seeds (numpy, torch, python, OS)
- [ ] Environment (requirements.txt, conda env, Dockerfile)
- [ ] Raw results (CSV/Parquet with all trades, equity curve, metrics)
- [ ] Bootstrap confidence intervals
- [ ] Walk-forward splits and per-fold metrics
- [ ] Parameter sensitivity heatmap
- [ ] Cost model assumptions and sensitivity