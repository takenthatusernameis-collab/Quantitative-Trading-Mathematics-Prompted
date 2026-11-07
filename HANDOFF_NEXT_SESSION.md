# HANDOFF_NEXT_SESSION.md — Cycle 33 complete (H119 REJECT); prepare Cycle 34 discovery/H120

## State
- H85–H119 all rejected/recorded. H119 (NF-20261107-02, short-term cross-sectional return reversal among sector ETFs) executed and **REJECT 3/8** (`exp_2026-11-07T02-28-32-224963Z`, ~1s). Next unused H-ID **H120** (H24/H68–H73/H76–H79 unassigned, not recycled).
- New files (uncommitted): `run_nf_20261107_02_cs_reversal.py` (bug fix: `_inverse_signal` double `oos_mask` indexing), `tests/test_nf_20261107_02_cs_reversal.py` (test-harness fixes). Docs/artifacts updated: `HYPOTHESIS_SPEC.md` (H119 pre-reg + outcome), `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 33 + H119 outcome/lineage), `NEXT_TASK.md` (Cycle 34), `HANDOFF_CURRENT_SESSION.md` (Cycle 33). Experiment artifacts: `.experiments/nf_runs/nf_20261107_02_cs_reversal/summary.json` + `grid.csv`.
- No secrets/credentials added. No published/certified artifact/gate threshold/verdict modified except adding H119 records.

## What changed (this cycle)
- **Cycle 33 execution (directive §4):** H119 pre-registered in prior session (NF-20261107-02, short-term cross-sectional return reversal). Runner+tests pre-existed (16 tests after test-harness fixes). Executed `run_nf_20261107_02_cs_reversal.py` → `exp_2026-11-07T02-28-32-224963Z`. Recorded verdict in `HYPOTHESIS_SPEC.md` §H119 and `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 33. Updated `NEXT_TASK.md` for Cycle 34.
- **H119 executed (REAL):** `exp_2026-11-07T02-28-32-224963Z`. 9 sectors + SPY aligned 4233 rows (train 2516 / val 756 / test 961). Selected `lookback=10,vol_target=0.10` (WF mean 1.1807). OOS Val+Test (1494 trades): Sharpe **0.669**, PF **1.123**, max DD **-18.84%**, WF stability **0.904**, worst-regime rolling-252 min **-0.436**, benchmark p **1.0**/IR **-0.255**, perturbation min ratio **0.725**. Gates **3/8 PASS** (trades, WF stability, perturbation). Verdict **REJECT**.
- **Ablations (OOS):** buy-hold SPY 0.791/1.164/DD -17.97%; equal-weight sectors 0.767/1.165/DD -36.91%; random-side -0.107/0.957/DD -9.69%/686; inverse-momentum-long 0.573/1.109/DD -14.36%/1500.

## What was actually verified
- `python -m ruff check run_nf_20261107_02_cs_reversal.py tests/test_nf_20261107_02_cs_reversal.py` → **All checks passed**.
- `python -m ruff format run_nf_20261107_02_cs_reversal.py` + `--check` on both files → **2 files already formatted**.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261107_02_cs_reversal.py` → **16 passed** (~1.5s).
- `PYTHONPATH=src python run_nf_20261107_02_cs_reversal.py` → completed, artifact written, verdict REJECT 3/8. Data feasibility verified: 9 sectors + SPY 4233 rows 2010-01-04→2026-10-30, 0 non-positive.

## What remains unresolved
- **Cycle 34 discovery/H120 (NEXT_TASK):** H85–H119 rejected. Need fresh directive §4 cycle: >=3 repo-new mechanism candidates across >=3 broad categories, honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops). Deferred: NF-04 **still blocked** (no free point-in-time term-structure/roll proxy); NF-05 turnover/cost; NF-06-11 CBOE PC ratio infeasible; NF-11r/NF-06-18 TNX-FVX **SAME root as NF-11** — not new root family; NF-07/08/10/11/13/15/17/20/21, NF-20261106-03/21/23/24/28/29/30/32/33/35/36 deferred (see register). NF-36 executed as H118 REJECT 4/8 (not rerun); NF-02 executed as H119 REJECT 3/8 (not rerun).
- Baseline full-suite gates were **not rerun** this cycle (`src/qtr` unchanged). Before/after any future `src/qtr` change run pinned gates and preserve 100% coverage / `-W error`.

## Approaches already tried / failed (do not blindly repeat)
- H85–H119 all REJECTED (documented). H119 specifically failed Sharpe/PF/DD/worst-regime/benchmark-p/IR vs buy-hold despite perturbation stability, ample trades, WF stability, and random-side below strategy; weakest-tercile reversal underperforms buy-hold SPY (IR -0.255). Do not re-run H119 without a materially different, pre-registered mechanism/construction.
- NF-04 remains blocked by point-in-time term-structure/roll-proxy data feasibility on free sources. NF-11r is only an NF-11 resolution path (same root mechanism), not a repo-new root family.

## Precise next task (one task)
**Execute Cycle 34 discovery and implement+run H120** per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`: reconcile lineage to H119, propose >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops), pre-register H120 (smallest decisive feasible test) before validation outcomes, add runner+focused tests, run `ruff check/format`, run focused pytest, execute experiment, record verdict in `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md`/`NEXT_TASK.md`/handoff. Free/public data only; no gate weakening; no published artifact changes; no commit/push; do not modify `src/qtr` unless an evidenced defect requires it (then rerun pinned full gates).

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
