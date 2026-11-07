
---
## Cycle 34 (2026-11-07) — Discovery / Pre-registration & Execution of H120 (NF-20261107-03)

### What changed
- **Discovery (directive §4):** Reconciled lineage to H119 (H85–H119 rejected/recorded). Proposed/scored >=3 candidates across >=3 broad categories: NF-20261107-03 GLD/TLT real-asset vs duration relative-strength regime timing SPY (cross-asset real-asset vs duration transmission, 3.55, selected/executed H120); NF-20261107-04 USMV/SPY min-vol leadership (3.30, deferred — 2011 inception/sample-split constraint, H114 style adjacency); NF-20261107-05 EEM/TLT global risk vs duration (3.25, deferred — global risk/EM confounds). Explicit deferred reassessment (no silent drops): NF-04 still blocked (no free point-in-time term-structure/roll proxy); NF-05 executed as H119 REJECT (net-of-cost decisive risk resolved by weekly cadence); NF-07/08/10/11/13/15/17/20/21 deferred; NF-11r/NF-06-18 TNX-FVX **SAME root mechanism as NF-11 — not new root family**; NF-06-11 infeasible; NF-20261106-03/21/23/24/28/30/32/33/35/36 deferred; NF-20261106-29/H115 and NF-20261106-36/H118 already executed/rejected.
- **H120 pre-registered/executed (NF-20261107-03):** Added `run_nf_20261107_03_gld_tlt_regime.py`, `tests/test_nf_20261107_03_gld_tlt_regime.py` (10 tests), updated `HYPOTHESIS_SPEC.md` §H120 with outcome, appended `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 34, updated `NEXT_TASK.md` for Cycle 35. `src/qtr` unchanged.

### Verified
- `ruff check run_nf_20261107_03_gld_tlt_regime.py tests/test_nf_20261107_03_gld_tlt_regime.py` — All checks passed.
- `ruff format --check ...` — clean.
- `PYTHONPATH=src pytest -q tests/test_nf_20261107_03_gld_tlt_regime.py` — **10 passed**.
- `PYTHONPATH=src python run_nf_20261107_03_gld_tlt_regime.py` — **REJECT 4/8**, `exp_2026-11-07T06-30-09-462925Z`, artifact `.experiments/nf_runs/nf_20261107_03_gld_tlt_regime/summary.json`.
- Data feasibility (DataFetcher/cache): GLD/TLT/SPY 4233 rows, 2010-01-04→2026-10-30, 0 non-positive.

### H120 result (REAL, pre-registered gates)
- Selected (train-only 4-fold WF): `lookback=63, z_window=252, entry_scale=1.0, vol_target=0.15` (WF mean 1.270, train Sharpe 1.023).
- OOS Val+Test (857 trades): Sharpe **0.936** fail, PF **1.182** fail, DD **-7.82%** pass, trades **857** pass, WF **0.915** pass, worst-regime rolling-252 min **-0.874** fail, benchmark-p **1.0**/IR **-28.956** fail, perturbation **0.997** pass.
- Ablations (OOS): buy-hold SPY 0.791/1.164/DD -17.97%/1; random-exposure-matched 0.474/1.082/DD -13.49%/1226; inverse-stress-long 0.315/1.078/DD -11.30%/858.
- Verdict: perturbation-stable, lower DD, WF/trades pass, but no validated risk-adjusted edge vs buy-hold SPY (fails Sharpe/PF/worst-regime/benchmark-p/IR). Specific pre-registered GLD/TLT ratio-momentum mapping tested; honest adjacency to prior GLD/TLT families acknowledged. No gate weakened.

### Unresolved / constraints
- H85–H120 all REJECTED/recorded. Lineage gaps H24/H68–H73/H76–H79 remain unassigned (not recycled).
- No commit/push performed (not requested). Published/certified artifacts and thresholds unchanged. `src/qtr` unchanged.
- Next session: Cycle 35 discovery/H121 per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`.
