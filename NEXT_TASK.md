# NEXT_TASK — Cycle 43 complete (H129 REJECT 4/8); prepare Cycle 44 discovery/H130

Cycle 43 completed: H129 **REJECT 4/8** (NF-20261107-29 cross-sectional average sector beta regime timing SPY; `.experiments/nf_runs/nf_20261107_29_avg_beta_regime/summary.json`). H85–H129 all rejected/recorded. `src/qtr` unchanged.

Cycle 43 discovery executed per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`:
- Reconciled lineage to H128 (H85–H128 all rejected/recorded).
- Proposed >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring:
  - NF-20261107-29 Cross-sectional average sector beta regime timing SPY (systematic risk / beta-expansion) — 3.75, **selected/executed H129**. Novelty scored honestly (3): repo-new avg-beta observable, but cross-sectional sector-stat construction adjacent to H117 (sector correlation regime REJECT 2/8).
  - NF-20261107-30 Cross-sectional average IVOL regime timing SPY (idiosyncratic-risk dispersion) — 3.60, held (adjacent H93 IVOL level REJECT).
  - NF-20261107-31 Sector breadth (% above 200d MA) participation timing SPY (market structure/breadth) — 3.25, held (adjacent H115 RSP/SPY REJECT 1/8; requires materially different observable/construction).
  - NF-20261107-32 Cross-sectional beta-dispersion regime timing SPY (factor dispersion) — 3.25, held (adjacent H117/H129 sector-stat construction).
- Reassessed deferred/held NF-04/05/07/08/10/11/13/15/17/20/21, NF-11r/NF-06-18 (same root as NF-11), NF-06-11 (infeasible), NF-20261106-03/23/24/28/30/32/33/35, NF-20261107-05 (CPI drift), held NF-20261107-11/12/14/30/31/32 with concrete evidence (no silent drops).
- Pre-registered H129 in `HYPOTHESIS_SPEC.md` before execution; runner + focused tests added; `ruff check/format` clean; focused pytest 4 passed; executed; verdict recorded.

H129 result (REAL, pre-registered gates): SPY + 9 SPDR sectors (XLB/XLE/XLF/XLI/XLK/XLP/XLU/XLV/XLY) yfinance, 3776 aligned rows 2010-01-04→2025-01-03 (train 2516/val 505/test 755). Selected `beta_window=21, z_window=126, entry_scale=2, vol_target=0.15`. OOS Val+Test (864 trades): Sharpe **0.814** (fail), PF **1.158** (fail), max DD **-2.59%** (pass), trades **864** (pass), WF stability **0.868** (pass), worst-regime rolling-252 **-1.206** (fail), benchmark p **1.0**/IR **-0.694** (fail), perturbation **0.958** (pass) → **REJECT 4/8**. Ablations: buy-hold SPY 0.750, random-exposure-matched **0.955** (outperforms), inverse 0.819. No validated edge. Honest adjacency to H117 (sector correlation REJECT 2/8): repo-new beta observable, same sector-stat construction class.

Cycle 44 required next per directive §4: fresh discovery, reconcile lineage to H129, propose >=3 repo-new candidates across >=3 broad categories, score honestly, reassess deferred/held with concrete evidence, pre-register **H130** (next unused H-ID; H24/H68–H73/H76–H79 unassigned, not recycled) with smallest decisive test. Avoid re-running H117/H129 sector-stat construction without a clearly distinct mechanism/observable. NF-20261107-29/H129 executed/rejected — not rerun. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push; `src/qtr` unchanged unless evidenced defect (then rerun pinned full gates).

Next unused H-ID: **H130**.

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
