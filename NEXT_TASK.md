# NEXT_TASK — Cycle 37 discovery / pre-register & execute H123

Cycle 36 completed: **H122 / NF-20261107-07 (SPY realized downside semivariance-ratio stress timing / return-asymmetry risk-off) executed — REJECT 4/8** (`nf_20261107_07_realized_semivariance`, 12.34s). Selected (train-only 4-fold WF) `window=10, entry_z=2.0, exit_z=0.0, vol_target=0.15` (train WF mean 1.734, folds [1.319,1.536,2.146,1.935]; train Sharpe 0.892, 1561 trades). OOS Val+Test (1174 trades, n=1717): Sharpe **0.811** fail, PF **1.173** fail, max DD **-2.92%** pass, trades **1174** pass, WF stability **0.910** pass, worst-regime yearly Sharpe **-0.760** (2022) fail, benchmark p **1.0**/IR **-0.779** fail, perturbation **0.516** pass. Ablations: buy-hold SPY 0.798/1.165/DD -33.72%/1; random-exposure-matched 0.673/1.164/DD -3.38%/1330; inverse/high-semivar-long -0.066/0.978/DD -8.41%/758. Verdict REJECT: bounded DD, ample trades, WF/perturbation stability, directional inverse ablation, but no pre-registered risk-adjusted edge vs buy-hold (fails Sharpe/PF/worst-regime/benchmark). Distinct from H121 Amihud `|ret|/dollar-volume` liquidity stress (H122 uses downside/upside variance ratio; volume unused) and H117/H118 cross-sectional regime families. **Lineage correction:** runner header initially mislabeled mechanism as Amihud — corrected to executed downside/upside variance-ratio mechanism; numbers/verdict unchanged. Artifact `.experiments/nf_runs/nf_20261107_07_realized_semivariance/summary.json`. Runner `run_nf_20261107_07_realized_semivariance.py`; tests `tests/test_nf_20261107_07_realized_semivariance.py` (13 passed), ruff check/format clean. `src/qtr` unchanged.

**Repo hygiene note:** `run_nf_20261107_06_cs_retail_flow.py` is an untracked, incomplete stub (no `__main__`, no focused tests, mislabeled H122, different mechanism). Do **not** treat as evidence. Renumber/remove on next NF-06 use to avoid NF/H-ID collisions.

Next unused H-ID **H123** (H24/H68–H73/H76–H79 unassigned, not recycled). Next session (Cycle 37, directive §4):

1. Reconcile lineage to H122. Propose >=3 repo-new mechanism candidates across >=3 broad categories, checked against root families H1–H122. Explicitly reassess NF-04/05/07/08/10/11/13/15/17/20/21, NF-11r/NF-06-18 (TNX-FVX, **SAME root mechanism as NF-11 — not a new root family**), NF-06-11 (infeasible, no free CBOE PC ratio), NF-20261106-03/23/24/28/30/32/33/35, NF-20261107-05/06 with concrete evidence — no silent drops. NF-20261107-06 (VIX3M term-structure carry) requires full ^VIX3M history/PIT verification and separation from H17/H104 before pre-registration (spot check showed limited recent data available; full 2010+ coverage unverified). NF-20261107-07 (H122) executed/rejected — do not rerun without materially different, pre-registered construction.
2. Score 1–5 (novelty 25%, plausibility 25%, data 20%, falsifiability 15%, execution 10%, independent empirical support 5%) with honest adjacency notes.
3. Pre-register highest-expected-information feasible candidate as **H123** in `HYPOTHESIS_SPEC.md`; record candidates/decisions in `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 37. Specify smallest decisive test, data/splits/protected holdout, costs, gates, rejection/falsifiers, ablations.
4. If decision-ready with free/public data and no `src/qtr` change: implement runner + focused tests, `ruff check/format --check`, focused pytest, execute, record verdict (OOS Val+Test only). Do not weaken gates, modify published/certified artifacts, use holdout for selection, or change `src/qtr` without evidenced defect + pinned 100% coverage suite.
5. If no feasible candidate: document blockers/evidence; do not invent candidates or default to maintenance-only parameter work.

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
