# NEXT_TASK.md — H88 resolved (REJECTED, GLD/USO amended); select next new-family mechanism

## State
- H88/NF-20261105-06 re-specified (option b, GLD/USO ETF proxy, 2026-11-05, pre-outcome; material instrument/cost/basis change disclosed) and executed: **REJECTED (1/9)**, exp `exp_2026-11-05T12-24-33-350043Z`. Original GC=F/CL=F attempt blocked by CL=F non-positive 2020-04-21 bar (exp `exp_2026-11-05T12-16-14-717827Z`) — blocker recorded; not a rejection of that universe without re-spec. Summary: `.experiments/artifacts/exp_2026-11-05T12-24-33-350043Z/summary.json`. H88 documented in `HYPOTHESIS_SPEC.md` §H88 and `NEW_FAMILY_RESEARCH_REGISTER.md` §12.
- `src/qtr` unchanged this session. Next unused H-ID: **H89**.

## Next task (one bounded task)
Run a **new-family discovery/selection step** per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` (H1–H30 exhausted; H85–H88 rejected). Do **not** re-run H88 unchanged.

1. Re-evaluate deferred candidates NF-20261105-04 (commodity carry, roll-proxy point-in-time feasibility) and NF-20261105-05 (short-term CS reversal, turnover/net-of-cost decisive risk) against current lineage + H88 evidence; propose at least a third materially distinct mechanism candidate if required to satisfy multi-mechanism search/ranking discipline.
2. Pre-register the top decision-ready candidate as **H89** (with NF temp ID, observables, splits including protected holdout, costs, gates, null/rejection, falsifiers, closest-prior distinction) only if data/feasibility is evidenced. Prefer the smallest decisive, free-data, point-in-time test.
3. Implement runner + focused tests; run focused NF tests + `python -m ruff check/format --check ...`. If `src/qtr` touched, run pinned full gates: `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` (100%).
4. Execute H89 only if decision-ready; record exp ID, gate counts, OOS metrics, selected config, verdict in spec/register and handoff.

## Constraints
- Preserve protected holdout; no protected-test feedback in discovery/selection/implementation.
- Do not modify published artifacts/thresholds/prior verdicts.
- Do not treat parameter/timeframe/indicator/universe tweaks as new families.
- NF-04/NF-05: address their stated decisive risks (point-in-time roll proxy for NF-04; net-of-cost/turnover realism for NF-05) before execution.
- Never commit without explicit user request.
