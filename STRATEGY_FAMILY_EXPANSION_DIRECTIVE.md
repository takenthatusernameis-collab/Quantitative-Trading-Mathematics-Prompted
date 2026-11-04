# Strategy-Family Expansion Directive

**Version:** 1.0  
**Effective:** 2026-11-04  
**Status:** Mandatory additive directive to PROMPT_V2.md

## 1. Mission and mandatory transition

The research program must keep looking for genuinely new systematic-trading strategy families after the repository's existing idea families have been exhausted. Exhausting a family is not permission to stop research, declare the strategy space empty, or spend the next cycle endlessly re-optimizing the same family.

The latest handoff records H1–H30 as exhausted and hypotheses through H84 as documented. Treat that as a trigger to enter **NEW-FAMILY DISCOVERY MODE** now. Before proposing a candidate, verify the complete current inventory, including any hypotheses added after H84. Do not assume that every H-number represents a distinct strategy family.

This directive is repository-relative: it requires ideas that are genuinely new relative to this repository's prior research. It does not claim that any idea is globally unprecedented.

## 2. What counts as a new strategy family

A new family must have a materially different, explicit return-generating economic mechanism and a testable causal path from observable information or market structure to expected returns.

The following, by themselves, do **not** create a new family:
- Changing lookbacks, thresholds, parameter grids, holding periods, bar frequencies, or rebalance schedules.
- Moving an existing signal to another asset, exchange, contract, or universe.
- Replacing one indicator with a close substitute.
- Adding or removing a conventional volatility, trend, regime, stop, or sizing overlay.
- Re-running a rejected grid, changing its presentation, or combining familiar signals without a distinct interaction mechanism.
- Audits, bug fixes, robustness checks, replications, and implementation work on an existing idea.

A hybrid may qualify only where the interaction between its components creates a distinct economic mechanism, with a falsifiable prediction that cannot be reduced to a routine combination or parameter variation of prior families.

## 3. Exhaust the repository map before searching

Build a family-lineage inventory from the latest versions of:
- HYPOTHESIS_SPEC.md and FINAL_REPORT.md.
- MATHEMATICAL_DISCOVERY_REPORT.md and INEFFICIENCY_RANKING.md.
- Every experiment runner, relevant tests, committed result summaries, and experiment metadata.
- README.md, AGENTS.md, PROMPT_V2.md, NEXT_TASK.md, and current handoffs.

For every H-ID found, classify it as one of:
1. Root strategy family.
2. Parameter, instrument, universe, or timeframe variant.
3. Extension or hybrid of an existing family.
4. Robustness, selection-bias, causality, or other audit.
5. Engineering, data-quality, or infrastructure repair.
6. Replication or post-hoc disclosure.

Record each root family's mechanism, observable inputs, markets, data frequency, principal result/verdict, known failure modes, and whether a genuinely discriminating experiment remains. Group related hypotheses under the same family root. Extend the inventory to the actual latest ID; never overwrite, recycle, or relabel historical IDs.

Do not mistake an unfinished implementation or an unavailable dataset for proof that an entire economic mechanism has been exhausted. First determine whether a feasible free-data test or a materially different observable can test the mechanism.

## 4. Required new-family discovery cycle

For each new-family cycle:

1. **Search across mechanisms, not indicators.** Investigate at least three materially distinct candidate mechanisms spanning at least three broad mechanism categories. Search mathematical and statistical research, market-structure and exchange documentation, empirical finance literature, and observable participant or institutional constraints. Illustrative search axes include information transmission and lead-lag, relative value and convergence, carry and term structure, volatility and convexity premia, liquidity provision and order-flow effects, event or auction mechanisms, and supply/flow constraints. These are search prompts only; audit each against the repository before calling it new.

2. **Propose at least three repository-new family candidates.** Assign temporary IDs NF-YYYYMMDD-01, NF-YYYYMMDD-02, and so on. Each proposal must state:
   - The economic mechanism and why it could persist.
   - What observable variables measure the mechanism and when they become available.
   - The causal chain from mechanism to expected return.
   - A precise long/short or portfolio construction concept, including timing and holding horizon.
   - The null hypothesis and an explicit result that would reject the idea.
   - A realistic data source, point-in-time coverage, and whether the needed history is obtainable without paid services.
   - Expected turnover, fees, spread, slippage, capacity, capital, and operational constraints.
   - The closest prior repository family and the specific reason this candidate is not merely its variant.
   - Key confounders, alternative explanations, leakage risks, and what evidence would falsify the mechanism.

3. **Rank candidates before implementation.** Score each from 1–5 on:
   - Repository-relative mechanism novelty and separation from prior families: 25%.
   - Economic plausibility and likely persistence: 25%.
   - Data availability and point-in-time feasibility: 20%.
   - Falsifiability and quality of the smallest decisive test: 15%.
   - Net-of-cost execution feasibility and capacity: 10%.
   - Independent empirical support: 5%.

   Explain each score. Do not inflate novelty or economic plausibility to force a candidate through. If fewer than three credible candidates can be found, document the search domains and the actual blocker rather than inventing candidates.

4. **Select the highest expected-information experiment.** Prefer the smallest experiment that could reject the proposed mechanism. Pre-register the hypothesis, data, timestamp rules, universe, splits, baseline, costs, metrics, multiple-testing treatment, compute budget, and rejection conditions before examining validation or protected-test outcomes.

5. **Implement only after the hypothesis is decision-ready.** Reuse the existing engine and data pipeline. Isolate the new family, preserve experiment lineage, and add focused tests. Assign the next unused H-ID only when the hypothesis is formally registered in HYPOTHESIS_SPEC.md. Preserve the temporary NF-ID as its family-level lineage key.

6. **Close the loop.** Record all candidates, including rejected and infeasible ones, sources, decision scores, experiment IDs, artifacts, results, and the next discriminating question in a durable NEW_FAMILY_RESEARCH_REGISTER.md. A failed test is useful information; it must update the family map and guide the next distinct mechanism search.

## 5. Evidence, data, and repository guardrails

This directive does not change or relax PROMPT_V2.md acceptance gates, statistical standards, cost assumptions, or multiple-testing controls.

- Preserve the protected holdout. Discovery, ranking, parameter selection, and iterative debugging must never use protected-test feedback.
- Do not change published results, prior experiment artifacts, verdicts, certified metrics, or frozen thresholds to make a new candidate pass.
- Keep the existing 100% statement and branch coverage requirement for src/qtr. Preserve Ruff, warning-as-error, and coverage gates.
- Use free/public data and existing infrastructure by default. No paid data, subscriptions, or paid compute without explicit authorization.
- No live trading, deployment, or changes to live systems.
- Account for fees, spreads, slippage, market impact, funding, borrow, roll, and other instrument-specific frictions before claiming economic value.
- Cite external mathematical and empirical claims and distinguish peer-reviewed evidence, preprints, vendor documentation, and unverified claims.
- Do not claim a strategy is novel, profitable, robust, or independently validated merely because it is mathematically interesting or a backtest runs.

## 6. Stopping and continuation rules

Do not stop at the first attractive idea or at the first unsuccessful family. Complete the repository novelty check and the three-candidate, multi-mechanism search before choosing the next experiment.

If all candidates are infeasible, identify whether the blocker is data, execution, capital, statistical power, or weak mechanism evidence. Search one materially different set of sources or mechanism categories before concluding that no candidate is currently testable. Then leave a precise handoff with the untested families and the reason each was deferred.

A family is exhausted only when its evidence and feasible next experiments have been mapped. A family queue is not globally exhausted merely because one grid failed, one dataset is short, or the current strategy implementation is complete.

**Governing rule:** when the known strategy-family queue is exhausted, the next research task must discover and assess new mechanisms. Do not default to maintenance-only work, repeated parameter optimization, or another audit unless a concrete defect or safety issue genuinely takes priority.
