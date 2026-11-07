# NEXT_TASK — Cycle 35 discovery / pre-register & execute H121

Cycle 34 completed: **H120 / NF-20261107-03 (SPY short-term time-series return reversal / single-asset contrarian overreaction correction) executed — REJECT 4/8** (`exp_2026-11-07T03-28-10-187622Z`). Selected `lookback=5, entry_thr=-0.005, exit_thr=0.0, vol_target=0.15` (train WF mean 1.340, train Sharpe 0.627). OOS Val+Test (277 trades): Sharpe **0.559** fail, PF **1.194** fail, max DD **-13.37%** pass, trades **277** pass, WF stability **0.891** pass, worst-regime yearly Sharpe **-0.832** (2022) fail, benchmark p **1.0**/IR **-0.783** fail, perturbation **0.518** pass. Ablations: buy-hold SPY 0.798/1.165/DD -33.72%; random-exposure-matched **0.601/1.219/DD -13.62%/311** (outperforms strategy); inverse/no-reversal-long 0.396/1.089/DD -7.61%/327. Verdict REJECT: bounded DD and trade/WF/perturbation stability, but no cost-robust edge vs buy-hold SPY; random-exposure ablation outperforms timing. **Distinct from H119** (CS-relative multi-sector weakest-tercile reversal, REJECT 3/8) — H120 is SPY-only absolute trailing-return contrarian. H85–H120 all rejected/recorded. Artifact `.experiments/nf_runs/nf_20261107_03_spy_ts_reversal/summary.json`.

New files (uncommitted): `run_nf_20261107_03_spy_ts_reversal.py`, `tests/test_nf_20261107_03_spy_ts_reversal.py` (10 passed). `ruff check/format` clean. `src/qtr` unchanged.

Next unused H-ID **H121** (H24/H68–H73/H76–H79 unassigned, not recycled). Next session (Cycle 35, directive §4):

1. Reconcile lineage to H120. Propose >=3 repo-new mechanism candidates across >=3 broad categories, checked against all root families H1–H120. Explicitly reassess NF-04/05/07/08/10/11/13/15/17/20/21, NF-11r/NF-06-18 (TNX-FVX, **SAME root mechanism as NF-11 — not a new root family**), NF-06-11 (infeasible, no free CBOE PC ratio), NF-20261106-03/21/23/24/28/30/32/33/35, NF-20261107-04/05 with concrete evidence — no silent drops. Do not rerun executed/rejected NF-20261106-29/31/34/36 (H115/H116/H117/H118) or NF-20261107-01/02/03 (H118/H119/H120) without a materially different, pre-registered construction.
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
