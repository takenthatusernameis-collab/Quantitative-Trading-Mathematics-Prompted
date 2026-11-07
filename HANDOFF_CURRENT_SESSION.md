# Handoff — Current Session (Cycle 34 complete, H120 REJECT)

## What changed
- **Cycle 34 discovery/execution (directive §4):** Reconciled lineage to H119 (H85–H119 all rejected/recorded). Proposed/scored >=3 repo-new mechanism candidates across >=3 broad categories: NF-20261107-03 SPY short-term time-series return reversal (single-asset overreaction/mean-reversion timing, 4.00, **selected/executed as H120**), NF-20261107-04 Amihud illiquidity-stress regime timing (3.85, deferred — sparse trades/adjacency), NF-20261107-05 CPI release event-drift timing SPY (3.55, deferred — schedule audit + adjacency to H90 event-calendar class). Reassessed all required deferred NFs with concrete evidence (no silent drops): NF-04 still blocked (no free point-in-time term-structure/roll proxy); NF-05 root deferred (turnover/cost; H119 weekly variant already tested REJECT); NF-06-11 CBOE PC ratio infeasible; NF-11r/NF-06-18 TNX-FVX data-resolved but NF-11 resolution path (SAME root, not repo-new); others deferred/executed as recorded in `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 34.
- **H120 pre-registered & executed (NF-20261107-03):** Added `run_nf_20261107_03_spy_ts_reversal.py` and `tests/test_nf_20261107_03_spy_ts_reversal.py` (10 tests). `src/qtr` unchanged. `ruff check/format` clean; focused pytest 10 passed. Executed `exp_2026-11-07T03-28-10-187622Z` → **REJECT 4/8**. Updated `HYPOTHESIS_SPEC.md` §H120 (pre-reg + outcome), `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 34, `NEXT_TASK.md` (Cycle 35 / H121), and handoffs.

## H120 result (REAL, pre-registered gates)
- Mechanism (repo-new vs H119): SPY-only absolute trailing-return contrarian (hysteresis, vol-targeted, 1-bar delay). **Distinct from H119** (cross-sectional relative weakest-tercile sector portfolio, 9 assets, weekly rank).
- Data: SPY 4233 rows 2010-01-04→2026-10-30 (cache), 0 non-positive. Train 2516 / Val 756 / Test 961.
- Selected (train-only 4-fold WF): `lookback=5, entry_thr=-0.005, exit_thr=0.0, vol_target=0.15` (WF mean 1.340). Train Sharpe 0.627 / trades 348.
- OOS Val+Test (277 trades): Sharpe **0.559** fail, PF **1.194** fail, max DD **-13.37%** pass, trades **277** pass, WF stability **0.891** pass, worst-regime yearly **-0.832** (2022) fail, benchmark p **1.0**/IR **-0.783** fail, perturbation **0.518** pass.
- Ablations (OOS): buy-hold SPY 0.798/1.165/DD -33.72%/1; random-exposure-matched **0.601/1.219/DD -13.62%/311** (outperforms strategy); inverse/no-reversal-long 0.396/1.089/DD -7.61%/327.
- Verdict: **REJECT (4/8)**. No validated risk-adjusted edge vs buy-hold SPY; random-exposure ablation outperforms timing. Specific pre-registered construction tested. No gate weakened.

## Verified
- `python -m ruff check run_nf_20261107_03_spy_ts_reversal.py tests/test_nf_20261107_03_spy_ts_reversal.py` — All checks passed.
- `python -m ruff format --check run_nf_20261107_03_spy_ts_reversal.py tests/test_nf_20261107_03_spy_ts_reversal.py` — clean after formatting.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261107_03_spy_ts_reversal.py` — **10 passed**.
- `PYTHONPATH=src python run_nf_20261107_03_spy_ts_reversal.py` — completed; artifact `.experiments/nf_runs/nf_20261107_03_spy_ts_reversal/summary.json` written (and `grid.csv`). Verdict REJECT 4/8.

## Unresolved / constraints
- H85–H120 all REJECTED/recorded. Lineage gaps H24/H68–H73/H76–H79 remain unassigned (not recycled).
- No commit/push performed. Published/certified artifacts and thresholds unchanged. `src/qtr` unchanged. H120 runner/tests/docs and experiment artifacts are uncommitted local changes.
- `src/qtr` pinned full gates were **not rerun** (no `src/qtr` change). If `src/qtr` is touched, run: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.

## Approaches that failed / evidence (do not blindly repeat)
- H120 failed Sharpe/PF/worst-regime/benchmark gates; random-exposure-matched ablation outperformed timing (Sharpe 0.601 vs 0.559). Do not rerun same construction.
- NF-04 blocked (no free point-in-time term-structure/roll proxy). NF-11r is NF-11 resolution path (SAME root), not repo-new. NF-06-11 CBOE PC ratio infeasible.

## One precise next task
**Execute Cycle 35 discovery and implement+run H121** per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`: reconcile lineage to H120, propose >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops), pre-register H121 (smallest decisive feasible test) before validation outcomes, add runner+focused tests, `ruff check/format`, focused pytest, execute, record verdict in `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md`/`NEXT_TASK.md`/handoff. Free/public data only; no gate weakening; no published artifact changes; no commit/push; do not modify `src/qtr` unless evidenced defect requires it (then rerun pinned full gates).
