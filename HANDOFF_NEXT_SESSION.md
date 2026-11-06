# HANDOFF_NEXT_SESSION.md — Cycle 30 complete (H116 REJECT); prepare Cycle 31 discovery/H117

## State
- H85–H116 all rejected/recorded. H116 (NF-20261106-31, ITA/SPY aerospace-defense fiscal/geopolitical spending-cycle leadership timing SPY) executed and **REJECT 4/8**.
- `src/qtr` unchanged this cycle. H1–H30 exhausted (pre-existing). Next unused H-ID **H117** (H24/H68–H73/H76–H79 unassigned, not recycled).
- New files (uncommitted): `run_nf_20261106_31_ita_spy_defense.py`, `tests/test_nf_20261106_31_ita_spy_defense.py`. Docs/artifacts updated: `HYPOTHESIS_SPEC.md` (H116 pre-reg + outcome), `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 30 + H116 outcome/lineage), `NEXT_TASK.md`. Experiment artifacts: `.experiments/nf_runs/nf_20261106_31_ita_spy_defense/summary.json`, `.experiments/artifacts/exp_2026-11-06T23-40-35-522405Z/`.
- No secrets/credentials added. No published/certified artifact/gate threshold/verdict modified except adding H116 records.

## What changed (this cycle)
- **Cycle 30 discovery (directive §4):** reconciled lineage to H115. Proposed >=3 repo-new mechanism candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops). Candidates: NF-20261106-31 ITA/SPY defense spending-cycle (selected/executed H116, 3.55, sector-ratio adjacency acknowledged — mechanism fiscal/geopolitical spending-cycle reallocation distinct from prior sector families), NF-20261106-32 DBC/SPY commodity-complex (deferred 3.35, ETF roll/flow confounds + adjacency to H101/H98/H88), NF-20261106-33 EWH/SPY China-exposure/capital-flow (deferred 3.35, confounded with USD/risk-appetite themes). Rough 2020+ exploratory sanity only (single arbitrary param set, not holdout-selected, not used for selection): ITA/SPY 1.067 vs BH 0.792, DBC 1.122, EWH 1.006, XME 1.091, IYR 0.996, VNQ 1.031, JNK/LQD 1.073 (n=1717) — recorded in register.
- **H116 pre-registered before validation outcomes:** `HYPOTHESIS_SPEC.md` and `NEW_FAMILY_RESEARCH_REGISTER.md` record mechanism, causal chain, null/falsifiers, splits (Train<=2019, Val 2020-22, protected Test 2023+), train-only 4-fold WF selection, bounded grid (24 combos), costs, gates, ablations. Protected Test used only in pre-registered OOS Val+Test gate evaluation.
- **H116 runner/tests (new):** `run_nf_20261106_31_ita_spy_defense.py`, `tests/test_nf_20261106_31_ita_spy_defense.py` (10 focused tests). Follows existing NF runner pattern; `signals.shift(1)` via engine; long-only vol-targeted SPY timing with continuous exposure scaling, OOS Val+Test gates, buy-hold/random-exposure-matched/inverse-stress ablations.
- **H116 executed (REAL):** `exp_2026-11-06T23-40-35-522405Z` (2.10s). ITA/SPY 4233 rows (train 2516 / val 756 / test 961). Selected `lookback=63,z_window=252,entry_scale=2.0,vol_target=0.15` (WF mean 1.321). OOS Val+Test (779 trades): Sharpe **0.706**, PF **1.131**, max DD **-11.44%**, WF stability **1.011**, worst-regime rolling-252 min **-1.175**, benchmark p **1.0**/IR **-0.501**, perturbation min ratio **0.944**. Gates **4/8 PASS** (trades, maxDD, WF stability, perturbation). Verdict **REJECT**.
- **Ablations (OOS):** buy-hold SPY 0.720/1.148/DD -18.21%/1; random-exposure-matched 0.998/1.193/DD -16.34%/778; inverse-stress-long 0.490/1.202/DD -7.67%/778.

## What was actually verified
- `python -m ruff check run_nf_20261106_31_ita_spy_defense.py tests/test_nf_20261106_31_ita_spy_defense.py` → **All checks passed**.
- `python -m ruff format run_nf_20261106_31_ita_spy_defense.py` (reformatted runner) + `--check` on both files → **2 files already formatted**.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261106_31_ita_spy_defense.py` → **10 passed** (1.89s).
- `PYTHONPATH=src python run_nf_20261106_31_ita_spy_defense.py` → completed, artifact written, verdict REJECT 4/8. Data feasibility verified: ITA/SPY 4233 rows 2010-01-04→2026-10-30, 0 non-positive.

## What remains unresolved
- **Cycle 31 discovery/H117 (NEXT_TASK):** H85–H116 rejected. Need fresh directive §4 cycle: >=3 repo-new mechanism candidates across >=3 broad categories, honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops). Deferred: NF-04 **still blocked** (no free point-in-time term-structure/roll proxy); NF-05 turnover/cost; NF-06-11 CBOE PC ratio infeasible; NF-11r/NF-06-18 TNX-FVX **SAME root as NF-11** — not new root family; NF-07/08/10/11/13/15/17/20/21, NF-20261106-03/21/23/24/28/30/32/33 deferred (see register). NF-32 DBC has ETF roll/flow confounds; NF-33 EWH confounded with USD/risk-appetite themes.
- Baseline full-suite gates were **not rerun** this cycle (`src/qtr` unchanged). Before/after any future `src/qtr` change run pinned gates and preserve 100% coverage / `-W error`.

## Approaches already tried / failed (do not blindly repeat)
- H85–H116 all REJECTED (documented). H116 specifically failed Sharpe/PF/worst-regime/benchmark-p/IR vs buy-hold despite perturbation stability, ample trades, WF stability, and drawdown reduction. Do not re-run H116 without a materially different, pre-registered mechanism/construction.
- NF-04 remains blocked by point-in-time term-structure/roll-proxy data feasibility on free sources. NF-11r is only an NF-11 resolution path (same root mechanism), not a repo-new root family.
- Sector-ratio SPY-timing constructions continue to show honest adjacency risk and weak risk-adjusted OOS edges vs buy-hold; new candidates should score novelty/adjacency honestly and prefer mechanisms with cleaner separation and falsifiers.

## Precise next task (one task)
**Execute Cycle 31 discovery and implement+run H117** per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`: reconcile lineage to H116, propose >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops), pre-register H117 (smallest decisive feasible test) before validation outcomes, add runner+focused tests, run `ruff check/format`, run focused pytest, execute experiment, record verdict in `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md`/`NEXT_TASK.md`/handoff. Free/public data only; no gate weakening; no published artifact changes; no commit/push; do not modify `src/qtr` unless an evidenced defect requires it (then rerun pinned full gates).

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
