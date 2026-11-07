# HANDOFF_NEXT_SESSION.md — Cycle 48 complete (H134 REJECT); prepare Cycle 49 discovery/H135

## State
- **H85–H134 all REJECTED/recorded.** H134 (NF-20261107-43, SPY timing from realized SPY--VIX correlation feedback) executed REAL: artifact `.experiments/nf_runs/nf_20261107_43_spy_vix_corr/summary.json` (1.61s), verdict **REJECT 5/8**. **Next unused H-ID: H135** (H24/H68–H73/H76–H79 unassigned, not recycled).
- **Files (H134):** `run_nf_20261107_43_spy_vix_corr.py`, `tests/test_nf_20261107_43_spy_vix_corr.py` (7 passed). Docs updated: `HYPOTHESIS_SPEC.md` §H134 (pre-registration + outcome), `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 48 discovery/scoring/deferred reassessment + H134 outcome), `NEXT_TASK.md` (Cycle 49), this file. `src/qtr` unchanged. No published/certified artifact/verdict/threshold/frozen number modified except adding H134 records. No secrets/credentials added. No commit/push.

## What changed (Cycle 48 / this session)
- **Directive §4 discovery:** lineage reconciled to H133; >=3 repo-new candidates across >=3 broad categories scored honestly (25/25/20/15/10/5): NF-20261107-43 realized SPY--VIX correlation feedback (volatility-feedback) **3.95, selected/executed H134**; NF-20261107-44 CPI post-announcement drift (macro event/auction) **2.80, deferred** (inflation-surprise consensus not free/PIT); NF-20261107-45 cross-sectional sector IVOL-spread (cross-sectional risk dispersion) **3.40, held** (reassesses held NF-20261107-11; adjacency to H118/H130 REJECTs). Concrete deferred reassessment recorded (no silent drops), including NF-04 blocked, NF-06-11 infeasible, NF-11r/NF-06-18 same root as NF-11. NF-20261107-32 (=H118 executed REJECT) and NF-20261107-36 (=H133 executed REJECT) noted as not repo-new; not rerun.
- **H134 result (REAL, NF-20261107-43):** SPY+^VIX 3776 rows 2010-01-01→2025-01-05 (train 2516/val 505/test 755). Selected `corr_window=126, z_window=126, entry_scale=2, vol_target=0.10` (train WF mean 0.649). OOS Val+Test (1373 trades): Sharpe **1.098** (pass), PF **1.235** (fail), maxDD **-10.53%** (pass), trades **1373** (pass), WF stability **1.367** (pass), worst-regime rolling-252 **-1.226** (fail), benchmark p **0.879**/IR **-0.524** vs buy-hold (fail), perturbation **0.999** (pass) → **REJECT 5/8**. Ablations: random-exposure-matched 0.045 (signal not pure noise), inverse 0.298 (no opposite edge).
- **Honest separation:** realized SPY--VIX *correlation regime* distinct from executed VIX level/shape families (H123/H126/H131/H104) and H127 GLD--TLT corr (different pair/mechanism). Raw Sharpe 1.098 clears 1.0 but not benchmark-significant; no validated edge.

## What was actually verified
- `python3 -m ruff check run_nf_20261107_43_spy_vix_corr.py tests/test_nf_20261107_43_spy_vix_corr.py` → **All checks passed**.
- `python3 -m ruff format --check run_nf_20261107_43_spy_vix_corr.py tests/test_nf_20261107_43_spy_vix_corr.py` → **2 files already formatted** (after formatting).
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261107_43_spy_vix_corr.py` → **7 passed**.
- `PYTHONPATH=src python3 run_nf_20261107_43_spy_vix_corr.py` → completed; verdict **REJECT 5/8**; artifact `.experiments/nf_runs/nf_20261107_43_spy_vix_corr/summary.json` written (`NF-20261107-43`, `H134`, verdict `REJECT`, gates_passed `5`).
- Baseline full-suite pinned gates **not rerun** (`src/qtr` unchanged).

## What remains unresolved
- **Cycle 49 discovery/H135 (NEXT_TASK):** Fresh directive §4 cycle: >=3 repo-new candidates across >=3 broad categories, honest 25/25/20/15/10/5 scoring, concrete deferred reassessment (no silent drops). Deferred highlights (see NEXT_TASK): NF-04 **blocked**; NF-06-11 **infeasible**; NF-11r/NF-06-18 **SAME root as NF-11**; NF-05/07/08/10/11/13/15/17/20/21/NF-20261106-03/23/24/28/30/32/33/35/NF-20261107-05 deferred. Held: NF-20261107-11/12/14/31/40 with separation requirements.
- H85–H134 all rejected; higher-moment (H89/H122/H124/H128/H132), IVOL (H93/H130), VIX-term/cross-asset vol/corr (H86/H113/H123/H125/H126/H127/H131), path-dependence/drawdown-state (H133), return dispersion (H118), volatility-feedback (H134) heavily tested — require clearly distinct mechanism/design if revisited.
- Baseline full-suite pinned gates **not rerun** (`src/qtr` unchanged).

## Approaches already tried / failed (do not blindly repeat)
- H85–H134 all REJECTED. H134: Sharpe 1.098 passes but not significant vs buy-hold (p 0.879, IR -0.524); PF/worst-regime/benchmark fail; worst-regime -1.226. Do not rerun same realized SPY--VIX correlation construction.
- NF-20261107-32/36 are duplicates of executed H118/H133 — do not re-execute as "new" without a materially distinct observable/design.

## Precise next task (one task)
**Execute Cycle 49 discovery and implement+run H135** per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`: reconcile lineage to H134, propose >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops), pre-register H135 (smallest decisive feasible test) before validation outcomes, add runner+focused tests, run `ruff check/format`, focused pytest, execute, record verdict in `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md`/`NEXT_TASK.md`/handoff. Free/public data only; no gate weakening; no published artifact changes; no commit/push; do not modify `src/qtr` unless an evidenced defect requires it (then rerun pinned full gates).

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
