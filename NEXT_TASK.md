# NEXT_TASK — Cycle 44 complete (H130 REJECT 3/8); prepare Cycle 45 discovery/H131

Cycle 44 completed: H130 **REJECT 3/8** (NF-20261107-30 cross-sectional average sector IVOL regime timing SPY; `.experiments/nf_runs/nf_20261107_30_avg_ivol_regime/summary.json`). H85–H130 all rejected/recorded. `src/qtr` unchanged.

Cycle 44 discovery executed per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`:
- Reconciled lineage to H129 (H85–H129 all rejected/recorded).
- Proposed >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring:
  - NF-20261107-30 Cross-sectional average sector IVOL regime timing SPY (idiosyncratic-risk/dispersion) — 3.60, **selected/executed H130**. Novelty scored honestly (3): repo-new *aggregate mean IVOL regime* z-score overlay (continuous de-risking), but honest adjacency to H93 (NF-20261105-13, IVOL *level* cross-sectional ranking, REJECT 2/9 — different construction/objective/trade structure) and sector-stat/dispersion class.
  - NF-20261107-31 Sector breadth (% above 200d MA) participation timing SPY (market structure/breadth) — 3.25, **held** (adj H115 RSP/SPY REJECT 1/8; requires materially different observable/construction).
  - NF-20261107-32 Cross-sectional return-dispersion regime timing SPY (dispersion/stock-picking environment) — 3.25, **held** (adj dispersion concepts/sector-stat class).
  - NF-20261107-33 Credit-quality relative momentum (HYG vs LQD) timing SPY (credit risk-appetite) — 3.40 scored but **not selected/executed**: repo contains prior `run_nf_20261107_16_credit_relmom.py`/artifact (OOS Sharpe 0.767, trades 121, DD -17.97%) and mechanism adjacent to H94/H108; not a repo-new root / not a materially different decisive test.
- Reassessed deferred/held NF-04/05/07/08/10/11/13/15/17/20/21, NF-11r/NF-06-18 (same root as NF-11), NF-06-11 (infeasible), NF-20261106-03/23/24/28/30/32/33/35, NF-20261107-05 (CPI drift), held NF-20261107-11/12/14/31/32 with concrete evidence (no silent drops). NF-20261107-16/33 HYG-LQD not selected (adjacent/previously-artifacted).
- Pre-registered H130 in `HYPOTHESIS_SPEC.md` before validation outcomes; runner + focused tests added; `ruff check/format` clean; focused pytest 8 passed; executed; verdict recorded.

H130 result (REAL, pre-registered gates): SPY + 9 SPDR sectors (XLB/XLE/XLF/XLI/XLK/XLP/XLU/XLV/XLY) yfinance, 3776 aligned rows 2010-01-04→2025-01-03 (train 2516/val 505/test 755). Selected `beta_window=21, z_window=126, entry_scale=2, vol_target=0.10`. OOS Val+Test (1549 trades): Sharpe **0.809** (fail), PF **1.163** (fail), max DD **-15.40%** (fail), trades **1549** (pass), WF stability **1.0** (pass), worst-regime rolling-252 **-1.715** (fail), benchmark p **0.770**/IR **-0.331** (fail), perturbation **0.737** (pass) → **REJECT 3/8**. Ablations: buy-hold SPY 0.760, random-exposure-matched 0.796 (comparable; benchmark fails), inverse 0.160. No validated edge. Honest adjacency to H93 (IVOL ranking, REJECT 2/9).

Cycle 45 required next per directive §4: fresh discovery, reconcile lineage to H130, propose >=3 repo-new candidates across >=3 broad categories, score honestly, reassess deferred/held with concrete evidence, pre-register **H131** (next unused H-ID; H24/H68–H73/H76–H79 unassigned, not recycled) with smallest decisive test. Avoid re-running H93/H130 IVOL constructions without a clearly distinct mechanism/design. NF-20261107-29/H129 and NF-20261107-30/H130 executed/rejected — not rerun. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push; `src/qtr` unchanged unless evidenced defect (then rerun pinned full gates).

Next unused H-ID: **H131**.

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
