# NEXT_TASK.md — Cycle 74 follow-up

## Immediate (bounded, highest value)
H159 (NF-20261108-32: VVIX-vs-VIX implied-vol-of-vol spread SPY timing) is RESOLVED: REAL executed 2026-11-09, **REJECT 4/8**.
OOS Val+Test (n=1252, 3208 trades): Sharpe **0.696** (fail ≥1.0), PF **1.146** (fail ≥1.3), max DD **-3.67%** (pass), trades **3208** (pass), WF stability **0.889** (pass), worst-regime rolling-252 Sharpe **-1.440** (fail ≥0.3), benchmark p **0.950** / IR **-0.733** (fail), perturbation min ratio **0.980** (pass). Train Sharpe 0.783. Ablations: buy-hold SPY 0.754; random-exposure-matched **0.206** (much weaker — structure, no benchmark edge); inverse regime **0.445** (weaker — direction supported, no benchmark edge). Artifact: `.experiments/nf_runs/nf_20261108_32_vvix_vix_spread_spy/summary.json` (+ `grid.csv`, `data_meta.json`, 10.78s). Recorded in `HYPOTHESIS_SPEC.md` §H159 and `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 73. `src/qtr` unchanged; no commit/push.

## Next task: Cycle 74 directive §4 discovery → pre-register **H160**
Reconcile lineage to H159 (**H85–H159 all rejected/recorded**). Propose >=3 repo-new candidates across >=3 broad mechanism categories with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops). Verify NF roots against executed H-IDs/artifacts before selection. Select highest-expected-information feasible candidate; pre-register as **H160** (next unused after H159; H24/H68–H73/H76–H79 unassigned, not recycled) before validation outcomes. Do not recycle unassigned H-IDs. Deferred candidates carried forward for recheck: NF-20261108-29 cross-asset return dispersion (4.10), NF-20261108-31 cross-sectional IVOL dispersion (3.85).

## Steps
1. Read `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4 and current `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md` state.
2. Reconcile lineage to H159; build candidate list across >=3 mechanism categories; score honestly; NF-root integrity check (no H99/H149-style collisions; verify runner/artifact/H-ID mapping).
3. Pre-register H160 in `HYPOTHESIS_SPEC.md` + register (statement, null, gates, data/splits, costs, falsifiers) before any validation/protected-test outcomes.
4. Add runner + focused tests; `ruff check/format`; focused pytest; execute runner; record REAL verdict + artifact; update `HANDOFF.md`/`NEXT_TASK.md`.

## Constraints
Free/public data only. No paid data/compute. No live/paper trading. No gate weakening. No protected-test feedback in selection. No modification of published artifacts/frozen thresholds/certified numbers. No commit/push without explicit authorization. `src/qtr` unchanged unless evidenced defect (then rerun pinned full gates: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`).
