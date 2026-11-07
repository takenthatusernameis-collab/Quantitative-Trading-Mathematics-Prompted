# NEXT_TASK — Cycle 36 discovery / pre-register & execute H122

Cycle 35 completed: **H121 / NF-20261107-04 (SPY Amihud illiquidity-stress regime timing / liquidity-deterioration risk-off) executed — REJECT 4/8** (`exp_2026-11-07T04-18-08-373455Z`). Selected (train-only 4-fold WF, 54-combo grid) `window=40, entry_z=1.5, exit_z=1.0, vol_target=0.15` (WF mean 1.655, train Sharpe 0.902, 1178 train trades). OOS Val+Test (971 trades): Sharpe **0.869** fail, PF **1.176** fail, max DD **-3.16%** pass, trades **971** pass, WF stability **0.963** pass, worst-regime rolling-252 Sharpe **-0.919** fail, benchmark p **1.0**/IR **-0.773** fail, perturbation **0.900** pass. Ablations: buy-hold SPY 0.798/1.165/DD -33.72%/1; random-exposure-matched **0.556/1.127/DD -5.12%/1249** (strategy above random exposure but below buy-hold on risk-adjusted gates); inverse/high-illiquidity-long **-0.084/0.966/DD -9.61%/530** (fails). Verdict REJECT: bounded DD and perturbation/WF/trade stability, but no pre-registered risk-adjusted edge vs buy-hold SPY (fails Sharpe/PF/worst-regime/benchmark). Distinct from H117/H118 (cross-sectional correlation/dispersion regime) and generic realized-vol timing: uses Amihud `|return|/dollar-volume` liquidity-stress z-score. H85–H121 all rejected/recorded. Artifact `.experiments/nf_runs/nf_20261107_04_amihud_illiq/summary.json`. Runner+tests committed/clean: `run_nf_20261107_04_amihud_illiq.py`, `tests/test_nf_20261107_04_amihud_illiq.py` (13 passed), ruff check/format clean. `src/qtr` unchanged.

Next unused H-ID **H122** (H24/H68–H73/H76–H79 unassigned, not recycled). Next session (Cycle 36, directive §4):

1. Reconcile lineage to H121. Propose >=3 repo-new mechanism candidates across >=3 broad categories, checked against all root families H1–H121. Explicitly reassess NF-04/05/07/08/10/11/13/15/17/20/21, NF-11r/NF-06-18 (TNX-FVX, **SAME root mechanism as NF-11 — not a new root family**), NF-06-11 (infeasible, no free CBOE PC ratio), NF-20261106-03/21/23/24/28/30/32/33/35, NF-20261107-05/06 with concrete evidence — no silent drops. NF-20261107-04 (H121) executed/rejected — do not rerun without materially different, pre-registered construction. Do not rerun other executed/rejected NF families without a materially different construction.
2. Score 1–5 (novelty 25%, plausibility 25%, data 20%, falsifiability 15%, execution 10%, independent empirical support 5%) with honest adjacency notes.
3. Pre-register highest-expected-information feasible candidate as **H122** in `HYPOTHESIS_SPEC.md`; record candidates/decisions in `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 36. Specify smallest decisive test, data/splits/protected holdout, costs, gates, rejection/falsifiers, ablations.
4. If decision-ready with free/public data and no `src/qtr` change: implement runner + focused tests, `ruff check/format --check`, focused pytest, execute, record verdict (OOS Val+Test only). Do not weaken gates, modify published/certified artifacts, use holdout for selection, or change `src/qtr` without evidenced defect + pinned 100% coverage suite.
5. If no feasible candidate: document blockers/evidence; do not invent candidates or default to maintenance-only parameter work.

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
