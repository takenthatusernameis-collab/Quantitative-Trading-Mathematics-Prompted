# HANDOFF_NEXT_SESSION.md — Cycle 29 complete (H115 REJECT); prepare Cycle 30 discovery/H116

## State
- H85–H115 all rejected/recorded. H115 (NF-20261106-29, RSP/SPY market breadth/participation leadership timing SPY) executed and **REJECT 3/8**.
- `src/qtr` unchanged this cycle. H1–H30 exhausted (pre-existing). Next unused H-ID **H116** (H24/H68–H73/H76–H79 unassigned, not recycled).
- New files (uncommitted): `run_nf_20261106_29_rsp_spy_breadth.py`, `tests/test_nf_20261106_29_rsp_spy_breadth.py`. Docs/artifacts updated: `HYPOTHESIS_SPEC.md` (H115 pre-reg + outcome), `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 29 + §15), `NEXT_TASK.md`. Experiment artifacts: `.experiments/nf_runs/nf_20261106_29_rsp_spy_breadth/summary.json`, `.experiments/artifacts/exp_2026-11-06T23-32-03-009243Z/`. `.cache/cycle29_probe/` created during feasibility probes (untracked; contains parquet cache files used by probes/runs) — do not commit cache junk; include only intentional artifacts if committing later.
- No secrets/credentials added. No published/certified artifact/gate threshold/verdict modified except adding H115 records.

## What changed (this cycle)
- **H115 runner/tests (new):** `run_nf_20261106_29_rsp_spy_breadth.py`, `tests/test_nf_20261106_29_rsp_spy_breadth.py` (10 focused tests). Follows existing NF runner pattern; uses `DataFetcher(DataCache(Path(".cache/data")))`; `walk_forward_splits(len(rets), n_splits=...)`; long-only vol-targeted SPY timing with `signals.shift(1)` (1-bar delay), continuous exposure scaling, ablations (buy-hold SPY, random exposure-matched, inverse stress long), OOS Val+Test gates.
- **Pre-registration recorded before holdout use in selection context:** H115 added to `HYPOTHESIS_SPEC.md` and `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 29 discovery, >=3 candidates across >=3 broad categories, deferred reassessed with concrete evidence, honest scoring 25/25/20/15/10/5). Protected Test used only in pre-registered OOS Val+Test gate evaluation after train-only WF selection.
- **H115 executed (REAL):** `exp_2026-11-06T23-32-03-009243Z` (1.77s). RSP/SPY 4233 rows (train 2516 / val 756 / test 961). Selected `lookback=63,z_window=126,entry_scale=1.0,vol_target=0.15`. OOS Val+Test (900 trades): Sharpe **0.647**, PF **1.127**, max DD **-10.97%**, WF stability **0.733**, worst-regime rolling-252 min **-1.093**, benchmark p **1.0**/IR **-0.388**, perturbation min ratio **0.816**. Gates **3/8 PASS** (maxDD, trades, WF stability, perturbation). Verdict **REJECT**.
- **Ablations (OOS):** buy-hold SPY 0.720/1.148/DD -18.21%/1; random-exposure-matched 0.549/1.129/DD -7.24%/1717; inverse-stress-long 0.514/1.141/DD -17.46%/867.

## What was actually verified
- `python -m ruff format run_nf_20261106_29_rsp_spy_breadth.py tests/test_nf_20261106_29_rsp_spy_breadth.py` → reformatted runner (1 file).
- `python -m ruff check run_nf_20261106_29_rsp_spy_breadth.py tests/test_nf_20261106_29_rsp_spy_breadth.py` → **All checks passed**.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261106_29_rsp_spy_breadth.py` → **10 passed** (1.10s).
- `PYTHONPATH=src python run_nf_20261106_29_rsp_spy_breadth.py` → completed, artifact written, verdict REJECT 3/8. Data feasibility verified via `DataFetcher` (RSP/SPY/JNK/LQD/VNQ/IYR/^TNX/^FVX/XHB/XLU/XBI/XLV 0 non-positive). Rough exploratory sanity (2020+, not holdout-selected) recorded in register; not used for selection.

## What remains unresolved
- **Cycle 30 discovery/H116 (NEXT_TASK):** H85–H115 rejected. Need fresh directive §4 cycle: >=3 repo-new mechanism candidates across >=3 broad categories, honest scoring, reassess deferred candidates with concrete evidence (NF-04 still blocked: no free point-in-time term-structure/roll proxy; NF-05 deferred turnover/cost; NF-06-11 PC ratio infeasible; NF-11r/NF-06-18 TNX-FVX same root as NF-11 — not new root family; NF-07/08/10/11/13/15/17/20/21, NF-20261106-03/21/23/24/28/30 deferred). Pre-register/execute H116 as smallest decisive feasible test.
- Baseline full-suite gates were **not rerun** this cycle (`src/qtr` unchanged). Before/after any future `src/qtr` change run pinned gates and preserve 100% coverage / `-W error`.

## Approaches already tried / failed (do not blindly repeat)
- H85–H115 all REJECTED (documented). H115 specifically failed Sharpe/PF/worst-regime/benchmark-p/IR vs buy-hold despite perturbation stability and drawdown reduction. Do not re-run H115 without a materially different, pre-registered mechanism/construction.
- NF-04 remains blocked by point-in-time term-structure/roll-proxy data feasibility on free sources. NF-11r is only an NF-11 resolution path (same root mechanism), not a repo-new root family.

## Precise next task (one task)
**Execute Cycle 30 discovery and implement+run H116** per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`: reconcile lineage to H115, propose >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops), pre-register H116 (smallest decisive feasible test) before validation outcomes, add runner+focused tests, run `ruff check/format`, run focused pytest, execute experiment, record verdict in `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md`/`NEXT_TASK.md`/handoff. Free/public data only; no gate weakening; no published artifact changes; no commit/push; do not modify `src/qtr` unless an evidenced defect requires it (then rerun pinned full gates).

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
