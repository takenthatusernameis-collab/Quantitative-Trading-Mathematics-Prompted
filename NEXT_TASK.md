# NEXT_TASK — Cycle 34 discovery / pre-register & execute H120

Cycle 33 completed: **H119 / NF-20261107-02 (short-term cross-sectional return reversal among sector ETFs) executed — REJECT 3/8** (`exp_2026-11-07T02-28-32-224963Z`). Selected `lookback=10, vol_target=0.10` (train WF mean 1.1807, train Sharpe 0.7403). OOS Val+Test (1494 trades): Sharpe **0.669** fail, PF **1.123** fail, max DD **-18.84%** fail, trades **1494** pass, WF stability **0.904** pass, worst-regime **-0.436** fail, benchmark p **1.0**/IR **-0.255** fail, perturbation **0.725** pass. Ablations: buy-hold SPY 0.791/1.164/DD -17.97%; equal-weight sectors 0.767/1.165/DD -36.91%; random-side -0.107/0.957/DD -9.69%/686; inverse-momentum-long 0.573/1.109/DD -14.36%/1500. Verdict REJECT: perturbation-stable and trade-rich but no cost-robust edge vs buy-hold SPY. H85–H119 all rejected/recorded. Artifact `.experiments/nf_runs/nf_20261107_02_cs_reversal/summary.json`.

Runner/test fixes made before execution (all green: ruff check/format, 16 pytest passed): fixed `_inverse_signal` double `oos_mask` indexing (runner bug); test harness fixes (row-sum gross cap MAX_LEVERAGE not MAX_POS; signal hold via ffill not fillna(0); read-only bool array `.copy()`; SPY added to test prices). `src/qtr` unchanged.

Next unused H-ID **H120** (H24/H68–H73/H76–H79 unassigned, not recycled). Next session (Cycle 34, directive §4):

1. Reconcile lineage to H119. Propose >=3 repo-new mechanism candidates across >=3 broad categories, checked against all root families H1–H119. Explicitly reassess NF-04/05/07/08/10/11/13/15/17/20/21, NF-11r/NF-06-18 (TNX-FVX, **same root mechanism as NF-11 — not a new root family**), NF-06-11 (infeasible), NF-20261106-03/21/23/24/28/29/30/32/33/35/36 with concrete evidence — no silent drops.
2. Score 1–5 (novelty 25%, plausibility 25%, data 20%, falsifiability 15%, execution 10%, independent empirical support 5%) with honest adjacency notes.
3. Pre-register highest-expected-information feasible candidate as **H120** in `HYPOTHESIS_SPEC.md`; record candidates/decisions in `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 34. Specify smallest decisive test, data/splits/protected holdout, costs, gates, rejection/falsifiers, ablations.
4. If decision-ready with free/public data and no `src/qtr` change: implement runner + focused tests, `ruff check/format --check`, focused pytest, execute, record verdict (OOS Val+Test only). Do not weaken gates, modify published/certified artifacts, use holdout for selection, or change `src/qtr` without evidenced defect + pinned 100% coverage suite.
5. If no feasible candidate: document blockers/evidence; do not invent candidates or default to maintenance-only parameter work.

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
