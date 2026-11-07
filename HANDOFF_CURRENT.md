# HANDOFF_CURRENT — Cycle 44 complete (H130 REJECT 3/8); prepare Cycle 45 discovery/H131

## State
- H85–H130 all rejected/recorded. H130 (NF-20261107-30, cross-sectional average sector IVOL regime timing SPY) executed **REJECT 3/8**. Next unused H-ID **H131** (H24/H68–H73/H76–H79 unassigned, not recycled).
- New/uncommitted (this cycle): `run_nf_20261107_30_avg_ivol_regime.py`, `tests/test_nf_20261107_30_avg_ivol_regime.py` (8 passed), artifact `.experiments/nf_runs/nf_20261107_30_avg_ivol_regime/summary.json` (+ `grid.csv`, `data_meta.json`). Docs updated: `HYPOTHESIS_SPEC.md` (H130 pre-registration + outcome), `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 44 discovery/scoring/deferred reassessment + H130 outcome), `NEXT_TASK.md`, `HANDOFF_NEXT.md`, `HANDOFF_CURRENT.md`.
- `src/qtr` unchanged. No secrets. No published/certified artifact, gate threshold, or prior verdict modified except adding H130 records.

## What changed
- **Cycle 44 discovery (directive §4):** >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring:
  - NF-20261107-30 Cross-sectional average sector IVOL regime timing SPY (idiosyncratic-risk/dispersion) — 3.60, **selected/executed H130**; repo-new aggregate mean IVOL regime z-score overlay (continuous de-risking), honest adjacency to H93 (IVOL level ranking REJECT 2/9 — different construction/objective/trade structure) and sector-stat/dispersion class.
  - NF-20261107-31 Sector breadth (%>200d MA) participation timing SPY (market structure/participation) — 3.25, held (adj H115 RSP/SPY REJECT 1/8; materially different observable/construction required).
  - NF-20261107-32 Cross-sectional return-dispersion regime timing SPY (dispersion) — 3.25, held.
  - NF-20261107-33 Credit-quality relative momentum HYG vs LQD (credit risk-appetite) — 3.40 scored but **not selected**: repo contains prior `run_nf_20261107_16_credit_relmom.py`/artifact (OOS Sharpe 0.767, trades 121, DD -17.97%) and adjacent to H94/H108; not repo-new root / not materially different decisive test.
- **Deferred reassessment (no silent drops):** NF-04 still blocked (no free PIT term-structure/roll proxy); NF-05/07/08/10/11/13/15/17/20/21 deferred; NF-11r/NF-06-18 same root as NF-11 (not new root); NF-06-11 infeasible; NF-20261106-03/23/24/28/30/32/33/35 deferred; NF-20261107-05 CPI drift deferred (adj H90). Held: NF-20261107-11 (IVOL spread, sep from H93; larger scope), NF-20261107-12 (credit-vs-equity vol divergence, sep from H94/H100/H125), NF-20261107-14 (OVX−VIX, same class as H125/H126 — materially different design required), NF-20261107-31/32. NF-20261107-16/33 HYG-LQD not selected. NF-20261107-29/H130 executed/rejected — not rerun.
- **H130 executed (REAL):** artifact `.experiments/nf_runs/nf_20261107_30_avg_ivol_regime/summary.json`. Selected `beta_window=21, z_window=126, entry_scale=2, vol_target=0.10`. OOS Val+Test (1549 trades, n=1260): Sharpe **0.809** (fail), PF **1.163** (fail), max DD **-15.40%** (fail ≤15%), trades **1549** (pass), WF stability **1.0** (pass), worst-regime rolling-252 **-1.715** (fail), benchmark p **0.770** / IR **-0.331** (fail), perturbation **0.737** (pass) → **REJECT 3/8**. Ablations: buy-hold SPY 0.760, random-exposure-matched 0.796 (comparable; benchmark fails), inverse 0.160.

## What was actually verified
- `python -m ruff check run_nf_20261107_30_avg_ivol_regime.py tests/test_nf_20261107_30_avg_ivol_regime.py` → **All checks passed**.
- `python -m ruff format --check run_nf_20261107_30_avg_ivol_regime.py tests/test_nf_20261107_30_avg_ivol_regime.py` → **clean** (2 files already formatted).
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261107_30_avg_ivol_regime.py` → **8 passed**.
- `PYTHONPATH=src python run_nf_20261107_30_avg_ivol_regime.py` → completed (4.25s), artifact written, verdict **REJECT 3/8**. Data: 3776 aligned rows, all positive.
- Baseline full-suite `src/qtr` gates **not rerun** (`src/qtr` unchanged).

## What remains unresolved
- **Cycle 45 discovery/H131:** per `NEXT_TASK.md`. Held/deferred candidates require concrete reassessment (no silent drops).
- Baseline full-suite `src/qtr` gates **not rerun** (`src/qtr` unchanged).

## Approaches already tried / failed (do not blindly repeat)
- H85–H130 all REJECTED. H130: benchmark/IR fail decisively (p 0.770, IR -0.331) with worst-regime collapse (-1.715) and maxDD breach; random-exposure comparable; no validated edge. H93/H130 IVOL constructions tested (ranking vs aggregate overlay) — do not rerun same IVOL concept without clearly distinct mechanism/design and explicit separation. NF-20261107-16/33 HYG-LQD credit-quality relmom: repo contains prior artifact/runner with REJECT-like OOS evidence and adjacency to H94/H108 — not a repo-new root; do not re-execute without materially different design.

## One precise next task
**Execute Cycle 45 discovery and implement+run H131** per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`: reconcile lineage to H130, propose >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring and concrete deferred/held reassessment (no silent drops), pre-register H131 (smallest decisive feasible test) before validation outcomes, add runner+focused tests, run `ruff check/format`, focused pytest, execute, record verdict in `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md`/`NEXT_TASK.md`/handoff. Free/public data only; no gate weakening; no published/certified artifact changes; no commit/push; do not modify `src/qtr` unless an evidenced defect requires it (then rerun pinned full gates).

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
