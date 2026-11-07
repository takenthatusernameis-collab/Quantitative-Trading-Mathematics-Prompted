# NEXT_TASK — Cycle 45 complete (H131 REJECT 3/8); prepare Cycle 46 discovery/H132

Cycle 45 completed: H131 **REJECT 3/8** (NF-20261107-34 VIX term-structure slope ^VIX3M/^VIX regime timing SPY; `.experiments/nf_runs/nf_20261107_34_vix_termstructure_regime/summary.json`). H85–H131 all rejected/recorded. `src/qtr` unchanged.

Cycle 45 discovery executed per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`:
- Reconciled lineage to H130 (H85–H130 rejected/recorded).
- Proposed >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring:
  - NF-20261107-34 VIX term-structure slope (^VIX3M/^VIX) regime timing SPY (volatility term structure/VRP) — 4.00, **selected/pre-registered/executed H131**. Repo-new observable (distinct from MOVE/GVZ H125/H126, IVOL H93/H130, correlation H127). Free PIT via yfinance (^VIX,^VIX3M).
  - NF-20261107-35 CBOE SKEW (^SKEW) tail-risk regime timing SPY (tail risk/skew) — 3.80, held.
  - NF-20261107-36 TLT-SPY correlation regime timing SPY (rates-equity co-movement) — 3.60, held (adj to H127 GLD–TLT correlation REJECT; different pair).
  - NF-20261107-37 Credit spread slope proxy (HYG/LQD) timing SPY — 3.25, not selected (adjacent to H94/H108/NF-16/33, previously-artifacted/adjacent).
- Pre-registered H131 in `HYPOTHESIS_SPEC.md` §H131; runner + focused tests added; `ruff check/format` clean; focused pytest 7 passed; executed; verdict **REJECT 3/8** recorded in `HYPOTHESIS_SPEC.md` and `NEW_FAMILY_RESEARCH_REGISTER.md`.

H131 result (REAL, pre-registered gates): SPY + ^VIX + ^VIX3M yfinance, aligned ~2010–2025 (train/val/test splits as pre-registered). Selected `z_window=126, entry_scale=2.0, vol_target=0.10`. OOS Val+Test (2220 trades): Sharpe **0.661** (fail), PF **1.147** (fail), max DD **-17.97%** (fail), trades **2220** (pass), WF stability **0.712** (pass), worst-regime rolling-252 Sharpe **-0.813** (fail), benchmark p **1.0**/IR **-0.820** (fail), perturbation **1.000** (pass) → **REJECT 3/8**. No validated edge vs buy-hold.

Cycle 46 required next per directive §4: fresh discovery, reconcile lineage to H131, propose >=3 repo-new candidates across >=3 broad categories, score honestly, reassess deferred/held with concrete evidence, pre-register **H132** (next unused H-ID; H24/H68–H73/H76–H79 unassigned). Avoid re-running tested families without clearly distinct mechanism/design (IVOL H93/H130, VIX term-structure/H125/H126/H127 cross-asset vol/corr). Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push; `src/qtr` unchanged unless evidenced defect (then rerun pinned 100% coverage suite).

Next unused H-ID: **H132**.

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
