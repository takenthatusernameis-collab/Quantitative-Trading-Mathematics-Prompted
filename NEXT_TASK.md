# NEXT_TASK — Cycle 35 discovery / pre-register & execute H121

Cycle 34 completed: **H120 / NF-20261107-03 (GLD/TLT real-asset vs duration relative-strength regime timing SPY) executed — REJECT 4/8** (`exp_2026-11-07T06-30-09-462925Z`, 3.26s). Selected `lookback=63, z_window=252, entry_scale=1.0, vol_target=0.15` (train-only WF mean 1.270, train Sharpe 1.023). OOS Val+Test (857 trades): Sharpe **0.936** fail, PF **1.182** fail, max DD **-7.82%** pass, trades **857** pass, WF stability **0.915** pass, worst-regime rolling-252 min **-0.874** fail, benchmark p **1.0** / IR **-28.956** fail, perturbation **0.997** pass. Ablations: buy-hold SPY 0.791/1.164/DD -17.97%/1; random-exposure-matched 0.474/1.082/DD -13.49%/1226; inverse-stress-long 0.315/1.078/DD -11.30%/858. Verdict: perturbation-stable, lower DD, WF stability/trades pass, but no validated risk-adjusted edge vs buy-hold SPY (fails benchmark/regime/PF/Sharpe gates). Artifact `.experiments/nf_runs/nf_20261107_03_gld_tlt_regime/summary.json`. `src/qtr` unchanged.

H85–H120 all rejected/recorded. Next unused H-ID **H121** (H24/H68–H73/H76–H79 unassigned, not recycled). Next session (Cycle 35, directive §4):

1. Reconcile lineage to H120. Propose >=3 repo-new mechanism candidates across >=3 broad categories, checked against all root families H1–H120. Explicitly reassess NF-04/05/07/08/10/11/13/15/17/20/21, NF-11r/NF-06-18 (TNX-FVX, **same root mechanism as NF-11 — not a new root family**), NF-06-11 (infeasible), NF-20261106-03/21/23/24/28/29/30/32/33/35/36 with concrete evidence — no silent drops.
2. Score 1–5 (novelty 25%, plausibility 25%, data 20%, falsifiability 15%, execution 10%, independent empirical support 5%) with honest adjacency notes.
3. Pre-register highest-expected-information feasible candidate as **H121** in `HYPOTHESIS_SPEC.md`; record candidates/decisions in `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 35. Specify smallest decisive test, data/splits/protected holdout, costs, gates, rejection/falsifiers, ablations.
4. If decision-ready with free/public data and no `src/qtr` change: implement runner + focused tests, `ruff check/format --check`, focused pytest, execute, record verdict (OOS Val+Test only). Do not weaken gates, modify published/certified artifacts, use holdout for selection, or change `src/qtr` without evidenced defect + pinned 100% coverage suite.
5. If no feasible candidate: document blockers/evidence; do not invent candidates or default to maintenance-only parameter work.

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
