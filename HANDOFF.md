# HANDOFF.md — H92 rejected; new-family discovery is the next research task

**State timestamp (UTC):** 2026-11-05T15:40:54Z  
**Branch:** `main`  
**Latest inspected experiment:** H92 / NF-20261105-10, experiment `exp_2026-11-05T15-40-24-218763Z`  
**Research mode:** NEW-FAMILY DISCOVERY MODE; research-only.

## Current verified research state

- The repository's mandatory `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` is present and referenced by `AGENTS.md`. It requires mechanism-level discovery after existing families are exhausted; parameter, timeframe, instrument and indicator variations do not count as new families.
- The research register contains the reconciled H1–H84 lineage and new-family candidates. H92 (NF-20261105-10, equity/bond relative-momentum timing) has now been executed and **REJECTED (3/9 gates)**.
- H92 selected `lookback=63`, `vol_target=0.10`, `allow_short=False`; OOS Sharpe **0.447**, profit factor **1.089**, maximum drawdown **-16.9%**, 313 trades. The SPY buy-and-hold benchmark Sharpe was **0.727**. A random-direction ablation matched the strategy's Sharpe, drawdown and profit factor, indicating no measured directional contribution from the proposed signal. Shorting on negative relative momentum worsened the result. Preserve the rejection; do not retune H92.
- NF-20261105-11 (Treasury term-spread regime timing) and NF-20261105-12 (cross-sectional equity dispersion regime) are documented as deferred candidates, not validated strategies.
- The most recent recorded full core-suite verification in the prior handoff was **2,295 passed, 16 skipped, 100% statement and branch coverage** for `src/qtr` at HEAD `1c3fd75`. This is historical verification, not a fresh full-suite result for the current HEAD. H92's focused runner tests were recorded as 10 passing.
- Frozen historical artifacts, protected-test rules, published verdicts and statistical gates remain unchanged. No live or paper trading is authorized.

## What changed since the obsolete H84 handoff

- The hypothesis inventory advanced beyond H84. The H92 experiment and its rejection are recorded in `NEW_FAMILY_RESEARCH_REGISTER.md` and `HYPOTHESIS_SPEC.md`.
- The prior handoff's H84-only state and maintenance-only next task are stale. They must not cause future agents to stop research or repeat completed maintenance.
- No claim is made here that H92 is profitable or that any new family is independently validated.

## Precise next task

**Continue NEW-FAMILY DISCOVERY MODE under `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md`.**

1. Reconcile the complete latest H-ID and root-family inventory, including H92, against `HYPOTHESIS_SPEC.md`, `FINAL_REPORT.md`, `MATHEMATICAL_DISCOVERY_REPORT.md`, `INEFFICIENCY_RANKING.md`, experiment runners and the research register.
2. Reassess NF-11 and NF-12 without treating their deferred status as a reason to stop. Search at least three materially distinct mechanism categories and propose at least three repository-new candidate families.
3. Explain each candidate's causal mechanism, closest prior family, free-data and point-in-time feasibility, costs, null hypothesis, falsifier and smallest decisive test. Rank using the mandatory directive's weights.
4. Select at most one highest-information experiment, preregister it before examining validation/protected-test outcomes, and assign the next unused H-ID only when formally registered. Keep all discovery and implementation changes isolated from `src/qtr` unless a concrete engine defect is demonstrated.
5. Preserve the existing acceptance thresholds, multiple-testing treatment, protected holdout, and 100% source statement/branch coverage. Do not weaken `-W error`, Ruff, formatting or coverage gates.
6. Update this handoff and `NEW_FAMILY_RESEARCH_REGISTER.md` with the actual search, rejected alternatives, sources, scores, experiment IDs and one next task. Do not append empty maintenance-only cycles.

## Required verification for any future core-code change

```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```

## Hard constraints

- Never modify published artifacts, prior verdicts, frozen thresholds or certified numbers to make a candidate pass.
- Never use protected-test feedback for discovery, tuning or selection.
- Use free/public data by default. No paid services, subscriptions, paid compute, credentials or live/paper trading.
- Never commit or push additional changes without explicit user authorization. (The current handoff correction is authorized by the user's request to fix blockers on `main`.)

(End of file)
