# HANDOFF_NEXT_SESSION.md — Cycle 47 complete (H133 REJECT); prepare Cycle 48 discovery/H134

## State
- **H85–H133 all REJECTED/recorded.** H133 (NF-20261107-39, SPY trailing distance-to-N-day-high drawdown-state timing) executed REAL: artifact `.experiments/nf_runs/nf_20261107_39_spy_drawdown_state/summary.json` (1.35s), verdict **REJECT 4/8**. **Next unused H-ID: H134** (H24/H68–H73/H76–H79 unassigned, not recycled).
- **Files (H133):** `run_nf_20261107_39_spy_drawdown_state.py`, `tests/test_nf_20261107_39_spy_drawdown_state.py`. Docs updated: `HYPOTHESIS_SPEC.md` §H133, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 47, `NEXT_TASK.md` (Cycle 48), `HANDOFF_CYCLE46_DISCOVERY.md` reconciled to reflect H132 executed state. `src/qtr` unchanged. No published/certified artifact/verdict/threshold/frozen number modified. No secrets/credentials added. No commit/push.

## What changed (Cycle 47 / this session)
- **Directive §4 discovery:** lineage reconciled to H132; >=3 repo-new candidates across >=3 broad categories scored (NF-20261107-39 path-dependence/drawdown-state 3.95 **selected/executed H133**; NF-20261107-40 AR(1) serial-dependence 3.85 held; NF-20261107-41 EEM/EFA risk-appetite 3.45 held; NF-20261107-42 overnight/intraday 3.15 not repo-new, H18 exists). Concrete deferred reassessment recorded (no silent drops), including NF-04 blocked, NF-06-11 infeasible, NF-11r/NF-06-18 same root as NF-11.
- **H133 result (REAL, NF-20261107-39):** SPY 3776 rows 2010-01-01→2025-01-05 (train 2516/val 505/test 755). Selected `high_window=126, z_window=126, entry_scale=2, vol_target=0.10` (train WF mean 0.446). OOS Val+Test (1305 trades): Sharpe **0.994** (fail), PF **1.201** (fail), maxDD **-11.76%** (pass), trades **1305** (pass), WF stability **1.672** (pass), worst-regime rolling-252 Sharpe **-1.663** (fail), benchmark p **0.891**/IR **-0.552** vs buy-hold (fail), perturbation **0.995** (pass). Ablations: buy-hold 0.759/1.155/DD -33.72%/1; random-exposure-matched 0.215/1.068/DD -26.76%/490; inverse 0.330/1.100/DD -16.63%/1305.
- **Honest separation:** H6 DDCV uses *portfolio equity* drawdown scaling on futures TSMOM base; H133 tests standalone SPY *price* distance-to-trailing-high overlay. No validated edge.

## What was actually verified
- `python3 -m py_compile run_nf_20261107_39_spy_drawdown_state.py` — OK.
- `python3 -m py_compile tests/test_nf_20261107_39_spy_drawdown_state.py` — OK.
- `python3 -m ruff check run_nf_20261107_39_spy_drawdown_state.py tests/test_nf_20261107_39_spy_drawdown_state.py` — **All checks passed**.
- `python3 -m ruff format --check run_nf_20261107_39_spy_drawdown_state.py tests/test_nf_20261107_39_spy_drawdown_state.py` — **2 files already formatted**.
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261107_39_spy_drawdown_state.py` — **7 passed**.
- `PYTHONPATH=src python3 run_nf_20261107_39_spy_drawdown_state.py` — executed; verdict **REJECT 4/8**; artifact `.experiments/nf_runs/nf_20261107_39_spy_drawdown_state/summary.json` written.
- Artifact read consistent (`NF-20261107-39`, `H133`, verdict `REJECT`, gates_passed `4`).

## What remains unresolved
- **Cycle 48 discovery/H134 (NEXT_TASK):** Fresh directive §4 cycle: >=3 repo-new candidates across >=3 broad categories, honest 25/25/20/15/10/5 scoring, concrete deferred reassessment (no silent drops). Deferred highlights (see NEXT_TASK): NF-04 **blocked**; NF-06-11 **infeasible**; NF-11r/NF-06-18 **SAME root as NF-11** (not new root); NF-05/07/08/10/11/13/15/17/20/21/NF-06-03/23/24/28/30/32/33/35/NF-07-05 deferred. Held: NF-07-11/12/14/31/32/37(41)/40 with separation requirements (NF-07-14 same construction class as H125/H126 — materially different design required).
- Higher-moment realized/implied (H89/H122/H124/H128/H132), IVOL (H93/H130), VIX-term/cross-asset vol/corr (H86/H113/H123/H125/H126/H127/H131), path-dependence drawdown-state (H133) heavily tested — require clearly distinct mechanism/design if revisited.
- Baseline full-suite pinned gates **not rerun** (`src/qtr` unchanged).

## Approaches already tried / failed (do not blindly repeat)
- H85–H133 all REJECTED. H133: Sharpe 0.994 (borderline fail) not significant vs buy-hold (p 0.891, IR -0.552); worst-regime -1.663; PF failed. Do not rerun same SPY distance-to-N-day-high construction.
- NF-20261107-42 overnight/intraday not repo-new (H18 REJECT). Do not repackage H18 as NF without materially different mechanism.

## Precise next task (one task)
**Execute Cycle 48 discovery and implement+run H134** per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`: reconcile lineage to H133, propose >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops), pre-register H134 (smallest decisive feasible test) before validation outcomes, add runner+focused tests, run `ruff check/format`, focused pytest, execute, record verdict in `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md`/`NEXT_TASK.md`/handoff. Free/public data only; no gate weakening; no published artifact changes; no commit/push; do not modify `src/qtr` unless an evidenced defect requires it (then rerun pinned full gates).

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
