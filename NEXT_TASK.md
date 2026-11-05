# NEXT_TASK.md — H89 resolved (REJECTED 4/9); select next new-family mechanism (H90)

## State
- H89/NF-20261105-07 (CBOE SKEW tail-risk regime equity timing, `^SKEW`/SPY, 2015–2026) executed: **REJECTED (4/9)**, exp `exp_2026-11-05T12-36-06-158635Z`. OOS Val+Test: Sharpe 0.524, PF 1.140, max DD −8.53%, trades 368, WF 1.800, worst-regime −0.623, bench p=1.000/IR −0.634 vs buy-hold SPY; passes trades/DD/WF/perturbation only. Artifact: `.experiments/artifacts/exp_2026-11-05T12-36-06-158635Z/summary.json`. H89 documented in `HYPOTHESIS_SPEC.md` §H89 and `NEW_FAMILY_RESEARCH_REGISTER.md` §13–§14.
- H85–H89 rejected. `src/qtr` unchanged. Next unused H-ID: **H90**.

## Next task (one bounded task)
Run **new-family discovery/selection** per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` and pre-register/prepare **H90**.

1. Reassess NF-20261105-04/NF-20261105-05 only with decisive-risk evidence: NF-04 needs a **pre-registered, point-in-time** free roll/term-structure proxy (current pipeline lacks free deferred series; CL=F continuous has non-positive history) — defer if not evidenced. NF-05 needs explicit pre-registered turnover/net-of-cost construction (daily CS reversal has high turnover risk) — defer if not evidenced.
2. Propose at least **one additional** materially distinct mechanism candidate (target 3 total considered/ranked), e.g. **pre-scheduled macro announcement/event drift** (FOMC dates, ex-ante, point-in-time; event/auction mechanism) if novelty holds vs H18/others, or another free-data category. Rank all candidates (1–5, weights per directive); document missing terms/blockers honestly.
3. Pre-register top decision-ready candidate as **H90** (NF temp ID, mechanism, observables, sample/splits/protected holdout, costs, construction, gates, null/rejection, falsifiers, closest-prior distinction). Implement runner + focused tests; run `python -m ruff check/format --check` and focused tests. If `src/qtr` touched, run pinned full gates: `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` (100%).
4. Execute H90 only if decision-ready and feasible in-session; otherwise leave decision-ready implementation/tests + evidence-based handoff. Record exp ID, gates, OOS metrics, verdict.

## Constraints
- Preserve protected holdout; no protected-test feedback.
- Do not modify published artifacts/thresholds/prior verdicts.
- Do not treat parameter/timeframe/indicator/universe tweaks as new families.
- Free/public data only; never commit without explicit user request.
