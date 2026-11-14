# NEXT_TASK.md

## Latest session (2026-11-14, Cycle 116) — Directive §4 H183 discovery: no feasible repo-new candidate; free-data queue confirmed exhausted

### What changed

- `NEW_FAMILY_RESEARCH_REGISTER.md` — appended **Cycle 116** discovery: ≥3 repo-new candidates across ≥3 broad mechanism categories (carry/term structure, institutional funding/basis, calendar seasonal, volatility/convexity) scored honestly; **no H182/H183 selected**. Concrete evidence: commodity carry blocked (no free per-contract PIT; spliced-continuous 12-1 proxy probed at monthly CS Sharpe −0.17 same-bar / −0.38 lagged); crypto funding data-blocked (no free funding-rate history); OVX/VIX9D/^RVX delisted; day-of-week seasonality has no cross-period-stable edge (probed train 2000–2012 vs test 2013–2026).
- `HYPOTHESIS_SPEC.md` — appended matching **Cycle 116** conclusion.

No `src/qtr`, runner, test, artifact, or frozen number was modified.

### What was actually verified (own evidence)

- `python -m pytest -q --ignore=tests/test_gates_workflow.py` — **3,795 passed / 51 skipped / 0 failed** (439s). The 7 `tests/test_gates_workflow.py` failures are the maintainer-gated workflow-contract block (unchanged, per AGENTS.md); fix is `patches/0001-gates-workflow-contract-fix.patch` (agent-unreachable).
- `python -m pytest tests/test_experiment_artifact_schema.py -q` — **105 passed** (the prior handoff's "2 artifact-schema failures" were already resolved in HEAD commit 16e52d3, which updated the pinned inventory to 108 dirs / 100 summaries / 131 keys).
- Baseline is clean and stable; no defect found. This session is a discovery cycle (no code change), so ruff/coverage gates are unaffected (no `src/qtr` change).

### What remains unresolved

1. **Maintainer-only:** `tests/test_gates_workflow.py` is red on `origin/main` by design; fix is `patches/0001-gates-workflow-contract-fix.patch`. `.github/workflows/**` is agent-unreachable.
2. **Free-data family queue exhausted:** H1–H182 all executed/rejected; every remaining mechanism category is data-blocked, underpowered, or mechanism/calendar-adjacent. No H183 candidate clears the directive's bar.
3. **H183 not pre-registered:** requires a data gap resolved under explicit authorization (futures roll/contango PIT for carry; crypto funding PIT; options PIT for GEX), or a directive §6 shift to auditing/infrastructure/maintenance.

### Approaches already tried and why they should not be repeated

- Do not repeat re-verification-only or discovery-only cycles that re-confirm exhaustion without new data authorization or a §6 shift — this is the second consecutive exhaustion cycle (Cycle 96, Cycle 116).
- Do not treat a spliced-continuous `=F` series as valid per-contract carry data (roll/contango proxy is biased; probed unprofitable).
- Do not edit `.github/workflows/**` or weaken `tests/test_gates_workflow.py` / coverage / frozen contracts.
- Do not treat a delisted free ticker (OVX, VIX9D, ^RVX) as available data.

### One precise next task

Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6, **shift the research program**: either (a) obtain explicit authorization for one paid/PIT data gap (futures roll/contango term-structure for commodity carry; crypto perpetual funding rates; historical options chain for GEX) and run the smallest decisive test, or (b) shift to auditing/infrastructure/maintenance work on the 100%-green suite. Do **not** run another discovery-only cycle that re-confirms exhaustion without new data or a §6 shift.

**Constraints:** no gate weakening; no published/frozen artifact, verdict, threshold, or frozen number modified; no commit/push of `.github/workflows/**`; `src/qtr` changes require 100% coverage.
