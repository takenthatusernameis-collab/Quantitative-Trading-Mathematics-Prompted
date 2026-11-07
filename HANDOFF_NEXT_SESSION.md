# HANDOFF_NEXT_SESSION.md — Cycle 49 complete (H135 REJECT); prepare Cycle 50 discovery/H136

## State
- **H85–H135 all REJECTED/recorded.** H135 (NF-20261107-46, SPY timing from realized volatility-of-volatility / std of trailing realized vol) executed REAL: artifact `.experiments/nf_runs/nf_20261107_46_spy_realized_vov/summary.json` (1.46s), verdict **REJECT 5/8**. **Next unused H-ID: H136** (H24/H68–H73/H76–H79 unassigned, not recycled).
- **Files (H135):** `run_nf_20261107_46_spy_realized_vov.py`, `tests/test_nf_20261107_46_spy_realized_vov.py` (7 passed). Docs updated: `HYPOTHESIS_SPEC.md` §H135 (pre-registration + outcome), `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 49 discovery/scoring/deferred reassessment + H135 outcome), `NEXT_TASK.md` (Cycle 50), this file. `src/qtr` unchanged. No published/certified artifact/verdict/threshold/frozen number modified except adding H135 records. No secrets/credentials added. No commit/push.

## What changed (Cycle 49 / this session)
- **Directive §4 discovery:** lineage reconciled to H134; >=3 repo-new candidates across >=3 broad categories scored honestly (25/25/20/15/10/5): NF-20261107-46 realized volatility-of-volatility (realized 2nd-order risk/uncertainty) **3.95, selected/executed H135**; NF-20261107-47 trailing lag-1 return autocorrelation/serial-dependence state (held NF-20261107-40 concept) **3.60, held** (weak plausibility; AR(1) diagnostics exist in repo/H26 is audit, not timing family — decisive separation required); NF-20261107-48 OVX−VIX energy-vs-equity IV spread (held NF-20261107-14 concept) **3.35, held** (same construction class as H125/H126 — **materially different pre-registered design required**, not just reframing); NF-20261107-49 TLT-SPY realized correlation regime **3.60, held** (adj H127/H96). Concrete deferred reassessment recorded (no silent drops): NF-04 blocked; NF-05/07/08/10/11/13/15/17/20/21/NF-20261106-03/23/24/28/30/32/33/35/NF-20261107-05 deferred; NF-11r/NF-06-18 same root as NF-11; NF-06-11 infeasible. NF-20261107-32/36(=39)/43/46 executed — not repo-new/rerun.
- **H135 result (REAL, NF-20261107-46):** SPY 3776 rows 2010-01-04→2025-01-03 (train 2516/val 505/test 755). Selected `rv_window=21, vov_window=63, z_window=126, entry_scale=2, vol_target=0.10` (train WF mean 0.667). OOS Val+Test (1238 trades): Sharpe **1.015** (pass), PF **1.212** (fail), maxDD **-8.89%** (pass), trades **1238** (pass), WF stability **1.270** (pass), worst-regime rolling-252 **-0.647** (fail), benchmark p **1.000**/IR **+0.257** vs buy-hold (fail, p>0.05), perturbation **0.828** (pass) → **REJECT 5/8**. Ablations: random-exposure-matched 0.538 (weaker), inverse 0.112 (no opposite edge). Realized VoV reduces DD vs buy-hold (-8.89% vs -33.72%) but not benchmark-significant.
- **Honest separation:** realized *volatility-of-volatility* (std of trailing realized vol) distinct from H104 *implied* VVIX (options/VIX-surface, REJECT 5/9) — same broad concept, different implied-vs-realized observable. Distinct from realized higher moments of returns (H122 downside semivariance ratio 2nd, H128 skewness 3rd, H132 kurtosis 4th) — VoV is dispersion/instability of realized volatility itself (2nd-order risk uncertainty). Distinct from VIX level/shape families (H86/H113/H123/H126/H131/H134), IVOL (H93/H130), drawdown state (H133), return dispersion (H118). No validated edge.

## What was actually verified
- `python3 -m ruff check run_nf_20261107_46_spy_realized_vov.py tests/test_nf_20261107_46_spy_realized_vov.py` → **All checks passed**.
- `python3 -m ruff format --check run_nf_20261107_46_spy_realized_vov.py tests/test_nf_20261107_46_spy_realized_vov.py` → **2 files already formatted** (after formatting).
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261107_46_spy_realized_vov.py` → **7 passed**.
- `PYTHONPATH=src python3 run_nf_20261107_46_spy_realized_vov.py` → completed; verdict **REJECT 5/8**; artifact `.experiments/nf_runs/nf_20261107_46_spy_realized_vov/summary.json` written (`NF-20261107-46`, `H135`, verdict `REJECT`, gates_passed `5`).
- Baseline full-suite pinned gates **not rerun** (`src/qtr` unchanged).

## What remains unresolved
- **Cycle 50 discovery/H136 (NEXT_TASK):** Fresh directive §4 cycle: >=3 repo-new candidates across >=3 broad categories, honest 25/25/20/15/10/5 scoring, concrete deferred reassessment (no silent drops). Deferred highlights (see `NEXT_TASK.md`): NF-04 **blocked**; NF-06-11 **infeasible**; NF-11r/NF-06-18 **SAME root as NF-11**; NF-05/07/08/10/11/13/15/17/20/21/NF-20261106-03/23/24/28/30/32/33/35/NF-20261107-05 deferred. Held: NF-20261107-11/12/14(48)/31/40(47)/49 with separation/design requirements.
- H85–H135 all rejected; vol-of-vol (H104 implied, H135 realized), higher-moment (H89/H122/H124/H128/H132), VIX-term/cross-asset vol/corr (H86/H113/H123/H125/H126/H127/H131/H134), IVOL (H93/H130), drawdown state (H133), return dispersion (H118) heavily tested — require clearly distinct mechanism/design if revisited.
- Baseline full-suite pinned gates **not rerun** (`src/qtr` unchanged).

## Approaches already tried / failed (do not blindly repeat)
- H85–H135 all REJECTED. H135: Sharpe 1.015 borderline/pass but not significant vs buy-hold (p 1.000, IR +0.257); PF/worst-regime/benchmark fail; worst-regime -0.647. Beats random exposure but no validated edge. Do not rerun same realized VoV construction.
- NF-20261107-32/36(39)/43/46 are duplicates of executed H118/H133/H134/H135 — do not re-execute as "new" without a materially distinct observable/design.
- NF-20261107-14/48 OVX−VIX: same cross-asset IV-spread construction class as H125/H126 — **materially different pre-registered design required** (not reframing).

## Precise next task (one task)
**Execute Cycle 50 discovery and implement+run H136** per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`: reconcile lineage to H135, propose >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops), pre-register H136 (smallest decisive feasible test) before validation outcomes, add runner+focused tests, run `ruff check/format`, focused pytest, execute, record verdict in `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md`/`NEXT_TASK.md`/handoff. Free/public data only; no gate weakening; no published artifact changes; no commit/push; do not modify `src/qtr` unless an evidenced defect requires it (then rerun pinned full gates).

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
