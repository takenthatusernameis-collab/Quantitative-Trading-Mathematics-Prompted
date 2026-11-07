# HANDOFF_NEXT_SESSION.md — Cycle 46 complete (H132 REJECT); prepare Cycle 47 discovery/H133

## State
- **H85–H132 all REJECTED/recorded.** H132 (NF-20261107-35, SPY trailing realized kurtosis 4th-moment stress regime timing) executed REAL in prepared env: artifact `.experiments/nf_runs/nf_20261107_35_spy_realized_kurtosis/summary.json` (1.85s), verdict **REJECT 5/8**. **Next unused H-ID: H133** (H24/H68–H73/H76–H79 unassigned, not recycled).
- **Files (H132):** `run_nf_20261107_35_spy_realized_kurtosis.py`, `tests/test_nf_20261107_35_spy_realized_kurtosis.py`. Docs updated: `HYPOTHESIS_SPEC.md` §H132 outcome, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 46 outcome, `NEXT_TASK.md` (Cycle 47), this handoff.
- **src/qtr unchanged.** No published/certified artifact, verdict, threshold, or frozen number modified. No secrets/credentials added. No commit/push.

## What changed (Cycle 46 close / this session)
- Reconciled docs to executed H132 artifact (evidence existed; spec/register/handoff were stale “not executed”).
- **H132 result (REAL):** SPY 3776 rows 2010-01-01→2025-01-05 (train 2516/val 505/test 755). Selected `kurt_window=126, z_window=126, entry_scale=2, vol_target=0.10` (train WF mean 0.9709). OOS Val+Test (1284 trades): Sharpe **1.248** (pass), PF **1.277** (fail), maxDD **-11.93%** (pass), trades **1284** (pass), WF stability **1.181** (pass), worst-regime rolling-252 Sharpe **-0.486** (fail), benchmark p **0.833**/IR **-0.433** vs buy-hold SPY (fail), perturbation **0.667** (pass). Ablations: buy-hold 0.759/1.155/DD -33.72%/1; random-exposure-matched 0.878/1.324/DD -7.99%/566; inverse -0.145/0.948/DD -17.39%/1285.

## What was actually verified
- `python3 -m ruff check run_nf_20261107_35_spy_realized_kurtosis.py tests/test_nf_20261107_35_spy_realized_kurtosis.py` → **All checks passed**.
- `python3 -m ruff format --check run_nf_20261107_35_spy_realized_kurtosis.py tests/test_nf_20261107_35_spy_realized_kurtosis.py` → **2 files already formatted**.
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261107_35_spy_realized_kurtosis.py` → **7 passed**.
- Artifact read/consistent: `.experiments/nf_runs/nf_20261107_35_spy_realized_kurtosis/summary.json` (verdict REJECT, gates_passed 5).

## What remains unresolved
- **Cycle 47 discovery/H133 (NEXT_TASK):** Fresh directive §4 cycle: >=3 repo-new mechanism candidates across >=3 broad categories, honest 25/25/20/15/10/5 scoring, concrete deferred reassessment (no silent drops). Deferred highlights (see NEXT_TASK): NF-04 **blocked**; NF-06-11 **infeasible**; NF-11r/NF-06-18 **SAME root as NF-11** (not new root); NF-05/07/08/10/11/13/15/17/20/21/NF-06-03/23/24/28/30/32/33/35/NF-07-05 deferred; held NF-07-11/12/14/31/32/36/37 with separation requirements. NF-07-14 same construction class as H125/H126 — materially different design required. NF-07-36 standalone NF timing not pre-registered (drawdown calc exists in `run_h6_vix_ddcv_experiment.py`).
- Higher-moment realized/implied (H89/H122/H124/H128/H132), IVOL (H93/H130), VIX-term/cross-asset vol/corr (H86/H113/H123/H125/H126/H127/H131) heavily tested — require clearly distinct mechanism/design if revisited.
- Baseline full-suite pinned gates **not rerun** (`src/qtr` unchanged).

## Approaches already tried / failed (do not blindly repeat)
- H85–H132 all REJECTED. H132: Sharpe 1.248 passed but not significant vs buy-hold (p 0.833, IR -0.433); random-exposure comparable (0.878); worst-regime -0.486; PF failed. Do not rerun same SPY realized-kurtosis construction.
- Higher-moment family: H89 implied SKEW (REJECT 4/9), H122 downside semivariance ratio (REJECT 3/8), H124 MAX/lottery (REJECT 3/8), H128 realized skewness (REJECT 2/8), H132 realized kurtosis (REJECT 5/8) — require clearly distinct mechanism/design, not another moment variant on same SPY overlay form without separation.

## Precise next task (one task)
**Execute Cycle 47 discovery and implement+run H133** per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`: reconcile lineage to H132, propose >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops), pre-register H133 (smallest decisive feasible test) before validation outcomes, add runner+focused tests, run `ruff check/format`, focused pytest, execute, record verdict in `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md`/`NEXT_TASK.md`/handoff. Free/public data only; no gate weakening; no published artifact changes; no commit/push; do not modify `src/qtr` unless an evidenced defect requires it (then rerun pinned full gates).

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
