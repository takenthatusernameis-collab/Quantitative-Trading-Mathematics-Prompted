# NEXT_TASK.md — Cycle 73 follow-up

## Immediate (bounded, highest value)
Execute pre-registered **H159 / NF-20261108-32 (VVIX-VIX implied-vol-of-vol spread SPY timing)** in a dependency-complete environment and record the **REAL** verdict, or record a concrete ^VVIX data blocker.

## Steps
1. Ensure deps available (`numpy,pandas,scipy,pytest,ruff,yfinance`; `qtr` importable via `PYTHONPATH=src` or install). Do not change `src/qtr`.
2. `PYTHONPATH=src python -m ruff check run_nf_20261108_32_vvix_vix_spread_spy.py tests/test_nf_20261108_32_vvix_vix_spread_spy.py`
3. `PYTHONPATH=src python -m ruff format --check run_nf_20261108_32_vvix_vix_spread_spy.py tests/test_nf_20261108_32_vvix_vix_spread_spy.py`
4. `PYTHONPATH=src python -m pytest -q tests/test_nf_20261108_32_vvix_vix_spread_spy.py`
5. `python run_nf_20261108_32_vvix_vix_spread_spy.py` → read `.experiments/nf_runs/nf_20261108_32_vvix_vix_spread_spy/summary.json`.
6. Update `HYPOTHESIS_SPEC.md` §H159, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 73, `HANDOFF.md`. Record REAL numbers only.

## If ^VVIX infeasible
Document concrete evidence (symbol/range/NaNs/rows/error). Mark H159 blocked/infeasible with evidence; do **not** fake pass/reject. Recheck NF roots/adjacency and pre-register/execute **NF-20261108-29 cross-asset return dispersion** (4.10, deferred Cycle 73) as next highest-information candidate only after decision-ready registration.

## After H159 resolved
If REJECT: Cycle 74 directive §4 discovery — reconcile lineage to H159, propose >=3 repo-new candidates across >=3 broad mechanism categories, honest 25/25/20/15/10/5 scoring, NF-root checks, select highest expected-information feasible candidate, pre-register as H160 before validation outcomes. Do not recycle H24/H68–H73/H76–H79.

## Constraints
Free/public data only. No paid data/compute. No live/paper trading. No gate weakening. No protected-test feedback in selection. No modification of published artifacts/frozen thresholds/certified numbers. No commit/push without explicit authorization. `src/qtr` unchanged unless evidenced defect (then rerun pinned 100% coverage + `-W error`).
