# NEXT_TASK — Cycle 42 complete (H128 REJECT 2/8); prepare Cycle 43 discovery/H129

Cycle 42 completed: H128 **REJECT 2/8** (NF-20261107-28 SPY realized skewness stress timing; `.experiments/nf_runs/nf_20261107_28_realized_skewness_stress/summary.json`). H85–H128 all rejected/recorded. `src/qtr` unchanged.

Cycle 42 discovery executed per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`:
- Reconciled lineage to H127 (H85–H127 all rejected/recorded).
- Proposed >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring:
  - NF-20261107-28 SPY realized skewness stress timing (higher-moment/realized crash-risk) — 3.95, selected/executed H128; repo-new realized-skewness observable, honest adjacency to H89 (implied SKEW) and H122 (semivariance).
  - NF-20261107-29 Cross-sectional average-beta risk-appetite timing SPY (systematic risk/beta-arb) — 3.75, held (adjacency to H96/H127/H117 correlation class).
  - NF-20261107-30 Cross-sectional average-IVOL regime timing SPY (idiosyncratic-risk/dispersion) — 3.60, held (adjacency to H93 IVOL level).
- Reassessed deferred/held candidates NF-04/05/07/08/10/11/13/15/17/20/21, NF-11r/NF-06-18 (same root as NF-11), NF-06-11 (infeasible), NF-20261106-03/23/24/28/30/32/33/35, NF-20261107-05, held NF-20261107-11/12/14 with concrete evidence (no silent drops).
- Pre-registered H128 in `HYPOTHESIS_SPEC.md` before execution; runner + focused tests added; `ruff check/format` clean; focused pytest 8 passed; executed; verdict recorded.

H128 result (REAL, pre-registered gates): artifact `.experiments/nf_runs/nf_20261107_28_realized_skewness_stress/summary.json`. SPY yfinance, 3776 aligned rows 2010-01-04→2025-01-03 (train 2516/val 505/test 755). Selected `lookback=63, z_window=63, entry_z=-0.5, exit_z=-1.0, vol_target=0.10`. OOS Val+Test (41 trades, n=1260): Sharpe **0.620** (fail), PF **1.154** (fail), max DD **-22.37%** (fail), trades **41** (fail), WF stability **1.0** (pass), worst-regime yearly **-0.375** (fail), benchmark p **0.949** / IR **-0.734** (fail), perturbation **0.681** (pass) → **REJECT 2/8**. Ablations: buy-hold SPY 0.759, random-exposure-matched 0.171 (strategy beats random but underperforms buy-hold and fails gates), inverse 0.367. No validated edge; sparse OOS. Honest adjacency to H89/H122.

Cycle 43 required next per directive §4: fresh discovery, reconcile lineage to H128, propose >=3 repo-new candidates across >=3 broad categories, score honestly, reassess deferred/held with concrete evidence, pre-register **H129** (next unused H-ID; H24/H68–H73/H76–H79 unassigned, not recycled) with smallest decisive test. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push; `src/qtr` unchanged unless evidenced defect (then rerun pinned full gates).

Next unused H-ID: **H129**.

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
