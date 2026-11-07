# HANDOFF_CURRENT — Cycle 42 complete (H128 REJECT 2/8); prepare Cycle 43 discovery/H129

## State
- H85–H128 all rejected/recorded. H128 (NF-20261107-28, SPY realized skewness stress timing) executed **REJECT 2/8**. Next unused H-ID **H129** (H24/H68–H73/H76–H79 unassigned, not recycled).
- New/uncommitted (this cycle): `run_nf_20261107_28_realized_skewness_stress.py`, `tests/test_nf_20261107_28_realized_skewness_stress.py` (8 passed), artifact `.experiments/nf_runs/nf_20261107_28_realized_skewness_stress/summary.json` (+ `grid.csv`, `data_meta.json`). Docs updated: `HYPOTHESIS_SPEC.md` (H128 pre-registration executed before validation + outcome), `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 42 discovery/scoring/deferred reassessment + H128 outcome), `NEXT_TASK.md`, `HANDOFF_NEXT.md`, `HANDOFF_CURRENT.md`.
- `src/qtr` unchanged. No secrets. No published/certified artifact, gate threshold, or prior verdict modified except adding H128 records.

## What changed
- **Cycle 42 discovery (directive §4):** >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring:
  - NF-20261107-28 SPY realized skewness stress timing (higher-moment/realized crash-risk) — 3.95, **selected/executed H128**; repo-new realized-skewness observable (SPY's own past returns, third moment), honest adjacency to H89 (implied SKEW tail regime, REJECT) and H122 (semivariance downside risk, REJECT 3/8).
  - NF-20261107-29 Cross-sectional average-beta risk-appetite timing SPY (systematic risk/beta-arb) — 3.75, held (adjacency to H96/H127/H117 correlation-regime class).
  - NF-20261107-30 Cross-sectional average-IVOL regime timing SPY (idiosyncratic-risk/dispersion) — 3.60, held (adjacency to H93 IVOL level).
- **Deferred reassessment (no silent drops):** NF-04 still blocked; NF-05/07/08/10/11/13/15/17/20/21 deferred; NF-11r/NF-06-18 same root as NF-11 (not new root); NF-06-11 infeasible; NF-20261106-03/23/24/28/30/32/33/35 deferred; NF-20261107-05 CPI drift deferred; held NF-20261107-11 (IVOL spread timing, separate from H93), NF-20261107-12 (credit-vs-equity vol divergence, separate from H94/H100/H125), NF-20261107-14 (OVX−VIX, same construction class as H125/H126 — materially different design required). NF-20261107-15/H127 executed/rejected — not rerun.
- **H128 executed (REAL):** artifact `.experiments/nf_runs/nf_20261107_28_realized_skewness_stress/summary.json`. Selected `lookback=63, z_window=63, entry_z=-0.5, exit_z=-1.0, vol_target=0.10`. OOS Val+Test (41 trades, n=1260): Sharpe **0.620** (fail), PF **1.154** (fail), max DD **-22.37%** (fail), trades **41** (fail), WF stability **1.0** (pass), worst-regime yearly **-0.375** (fail), benchmark p **0.949** / IR **-0.734** (fail), perturbation **0.681** (pass) → **REJECT 2/8**. Ablations: buy-hold SPY 0.759, random-exposure-matched 0.171 (strategy beats random but underperforms buy-hold), inverse 0.367.

## What was actually verified
- `python3 -m ruff check run_nf_20261107_28_realized_skewness_stress.py tests/test_nf_20261107_28_realized_skewness_stress.py` → **All checks passed**.
- `python3 -m ruff format --check run_nf_20261107_28_realized_skewness_stress.py tests/test_nf_20261107_28_realized_skewness_stress.py` → **clean**.
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261107_28_realized_skewness_stress.py` → **8 passed**.
- `python3 run_nf_20261107_28_realized_skewness_stress.py` → completed, artifact written, verdict **REJECT 2/8**. Data verified (3776 aligned rows, all positive).
- Baseline full-suite `src/qtr` gates **not rerun** (`src/qtr` unchanged).

## What remains unresolved
- **Cycle 43 discovery/H129:** per `NEXT_TASK.md`. Held/deferred candidates require concrete reassessment (no silent drops).
- Baseline full-suite `src/qtr` gates **not rerun** (`src/qtr` unchanged).

## Approaches already tried / failed (do not blindly repeat)
- H85–H128 all REJECTED. H128: random-exposure does not outperform but strategy fails Sharpe/PF/maxDD/trades/worst-regime/benchmark and underperforms buy-hold; sparse OOS (41 trades). Realized-skewness construction tested — do not rerun same construction class without materially different pre-registered mechanism/design. Correlation-regime class (H96/H127) and cross-asset vol-spread class (H125/H126) heavily tested — require clearly distinct mechanism/design if revisited.

## One precise next task
**Execute Cycle 43 discovery and implement+run H129** per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`: reconcile lineage to H128, propose >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring and concrete deferred/held reassessment (no silent drops), pre-register H129 (smallest decisive feasible test) before validation outcomes, add runner+focused tests, run `ruff check/format`, focused pytest, execute, record verdict in `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md`/`NEXT_TASK.md`/handoff. Free/public data only; no gate weakening; no published/certified artifact changes; no commit/push; do not modify `src/qtr` unless an evidenced defect requires it (then rerun pinned full gates).

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
