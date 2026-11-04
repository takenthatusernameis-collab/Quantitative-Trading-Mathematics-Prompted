# NEXT_TASK.md — mandatory new strategy-family discovery

## Assignment

This task supersedes the previous maintenance-only next task. The repository has recorded H1–H30 as exhausted and hypotheses through H84 as documented. The next research cycle must now investigate genuinely new strategy families rather than defaulting to baseline maintenance, additional audits, or more parameter variations of known ideas.

## Mandatory reading

1. AGENTS.md
2. PROMPT_V2.md
3. STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md
4. HYPOTHESIS_SPEC.md, FINAL_REPORT.md, MATHEMATICAL_DISCOVERY_REPORT.md, INEFFICIENCY_RANKING.md, and the latest handoffs

## Precise next task

Enter NEW-FAMILY DISCOVERY MODE.

1. Reconcile the full current hypothesis inventory, including any IDs added after H84. Cluster H-IDs by their actual return-generating mechanism; explicitly distinguish root families from variants, extensions, audits, replications, and engineering repairs.
2. Produce a repository-relative family-lineage map documenting each root mechanism, tested markets/data, verdict, known failure mode, and any genuinely untested discriminating experiment.
3. Research at least three materially distinct new candidate mechanisms from at least three broad mechanism categories. Each candidate must be demonstrably different from existing families and include a causal explanation, falsifiable hypothesis, free/public point-in-time data path, realistic net-of-cost implementation, and explicit rejection conditions.
4. Rank candidates using the weighted score in STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md. Do not manufacture novelty or force a candidate to pass.
5. Select the smallest high-information experiment for the strongest credible candidate. Pre-register it before examining validation or protected-test results. If decision-ready, assign the next unused H-ID and implement it in an isolated, testable change.
6. Preserve the candidate inventory, citations, scores, and outcomes in NEW_FAMILY_RESEARCH_REGISTER.md so later sessions continue exploring new mechanisms rather than restarting the same search.

## Guardrails

- Do not stop after confirming that H1–H30 are exhausted; the documented history through H84 must also be mapped.
- A changed lookback, indicator, market, timeframe, universe, parameter grid, or conventional overlay is not a new family on its own.
- Do not modify published artifacts, prior results, existing gates, certified metrics, or verdicts.
- Preserve the protected holdout and all existing PROMPT_V2 statistical and cost standards.
- Keep src/qtr at 100% statement and branch coverage. For source/test/runner changes, retain these checks: Ruff lint, Ruff format, and warning-as-error pytest with coverage.
- Use free/public data and existing infrastructure. No paid resources, live trades, or live-system modifications without explicit authorization.
- Do not claim an experiment, result, or validation passed without evidence.
- Keep the established commit/authorization conventions; the directive does not authorize unrelated commits or changes.

## Required closeout

Report the family map, the three or more candidate mechanisms (or a specific evidence-based explanation if that number is infeasible), sources, novelty comparison, ranking, selected experiment, pre-registration status, actual checks, unresolved blockers, and one precise next research task.

Baseline maintenance remains a guardrail, not the sole research objective.
