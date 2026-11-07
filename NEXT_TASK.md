# NEXT_TASK — Cycle 33 discovery / pre-register & execute H119

Cycle 32 completed: **H118 / NF-20261107-01 (cross-sectional sector return dispersion regime timing SPY) executed — REJECT 4/8** (`exp_2026-11-07T01-16-32-274332Z`, 1.748s). Gates passed: trades 779, max DD -10.19%, WF stability 0.885, perturbation 0.940. Failed: Sharpe 0.868, PF 1.164, worst-regime -1.215, benchmark-p 1.0/IR -0.369. Random-exposure-matched ablation outperformed (1.391/1.289/DD -14.45%). Feasibility: 9 sectors with 2010+ history (XLK,XLF,XLE,XLV,XLI,XLY,XLP,XLU,XLB); XLC/XLRE excluded to preserve sample/splits — documented. Artifact `.experiments/nf_runs/nf_20261107_01_sector_dispersion_regime/summary.json`. H85–H118 all rejected/recorded.

Next unused H-ID **H119** (H24/H68–H73/H76–H79 unassigned, not recycled). Next session (Cycle 33, directive §4):

1. Reconcile lineage to H118. Propose >=3 repo-new mechanism candidates across >=3 broad categories, checked against all root families H1–H118. Explicitly reassess NF-04/05/07/08/10/11/13/15/17/20/21, NF-11r/NF-06-18 (TNX-FVX, **NF-11 data-resolution path, SAME root mechanism — not a new root family**), NF-06-11 (infeasible), NF-20261106-03/21/23/24/28/29/30/32/33/35/36 with concrete evidence — no silent drops.
2. Score 1–5 (novelty 25%, plausibility 25%, data 20%, falsifiability 15%, execution 10%, independent empirical support 5%) with honest adjacency notes.
3. Pre-register highest-expected-information feasible candidate as **H119** in `HYPOTHESIS_SPEC.md`; record candidates/decisions in `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 33. Specify smallest decisive test, data/splits/protected holdout, costs, gates, rejection/falsifiers, ablations.
4. If decision-ready with free/public data and no `src/qtr` change: implement runner + focused tests, `ruff check/format --check`, focused pytest, execute, record verdict (OOS Val+Test only). Do not weaken gates, modify published/certified artifacts, use holdout for selection, or change `src/qtr` without evidenced defect + pinned 100% coverage suite.
5. If no feasible candidate: document blockers/evidence; do not invent candidates or default to maintenance-only parameter work.

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
