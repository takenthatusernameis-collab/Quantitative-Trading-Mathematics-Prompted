# HANDOFF — Current Session (Cycle 91 complete, H177 REJECT 5/8)

## What changed
- **Lineage reconciled to H177.** H85–H177 all rejected/recorded. Cycle 91 discovery (directive §4, ≥3 candidates/≥3 categories, honest scoring, no silent drops, NF-root checks) had pre-registered NF-20261110-01 as H177; this session implemented and executed H177 REAL.
- **H177 executed (NF-20261110-01, REAL, REJECT 5/8).** `run_nf_20261110_01_treasury_auction.py` + `tests/test_nf_20261110_01_treasury_auction.py` (17 passed). `ruff check/format --check` clean. Artifact `.experiments/nf_runs/nf_20261110_01_treasury_auction_20261110_050114/summary.json` (+grid.csv).
- **H177 construction.** Treasury auction supply-pressure timing: SPY vol-targeted position scaled by z-score of trailing auction demand composite (bid-to-cover, negative tail, negative dealer take-down); long strong-demand auctions, flat/short weak-demand; hysteresis with exit_z; 1-bar delay; long/short allowed; Equity CostModel defaults; MAX_POS 0.5. Grid 108 combos; train-only 4-fold WF selection.
- **H177 data.** SPY daily yfinance 2010-01-04→2026-10-30 (4233 rows); synthetic 10Y/30Y auction calendar (269 auctions; free Treasury Direct CSV parsing not available; documented limitation). Train 2010-01-04→2018-05-31 (2116), Val 2018-06-01→2022-08-12 (1058), Test protected 2022-08-13→2026-10-30 (1059).
- **H177 result (OOS Val+Test).** Selected `score_window=20, entry_z=1.0, exit_z=0.0, vol_target=0.10, tenor=10Y` (WF train mean 0.436). Sharpe **0.720** fail, PF **1.367** pass, maxDD **−4.51%** pass, trades **98** pass, WF **1.612** pass, worst-regime **−1.133** fail, benchmark-p **0.900**/IR **−0.442** fail, perturbation **0.651** pass → **REJECT 5/8**. Ablations: buy-hold 0.819; random-auction −0.448 (weaker); inverse −0.730 (weaker, direction consistent, no edge). No gate weakened. `src/qtr` unchanged.
- **Docs updated:** `HYPOTHESIS_SPEC.md` §H177, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 91 execution, `NEXT_TASK.md` (Cycle 92), `HANDOFF_NEXT.md`.

## Actually verified (this session)
- `python -m py_compile` runner + tests — OK.
- `python -m ruff check` / `ruff format --check` on H177 files — clean.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261110_01_treasury_auction.py` — **17 passed**.
- `PYTHONPATH=src python run_nf_20261110_01_treasury_auction.py` — REAL execution completed (17.1s), REJECT 5/8.
- Artifact present/parsable: `.experiments/nf_runs/nf_20261110_01_treasury_auction_20261110_050114/summary.json` (+grid.csv).
- `src/qtr` unchanged; pinned 100% coverage suite **not rerun**.

## Unresolved / constraints
- H85–H177 all REJECTED/recorded. Gaps H24/H68–H73/H76–H79 unassigned (not recycled). **No commit/push** (not authorized). Published/certified artifacts and thresholds unchanged.
- Cycle 92: directive §4 discovery (>=3 candidates, >=3 categories, honest scoring, no silent drops, NF-root checks) before selecting H178. Re-assess NF-20261109-16 dividend capture (4.05), NF-20261109-18 S&P 500 inclusion (3.70), NF-20261109-19 options GEX (3.10), NF-20261109-02 earnings revision (3.65), NF-20261109-22 RSP-SPY relmom (3.75), NF-20261109-23 USMV-SPY low-vol relmom (3.55), NF-20261109-12 holiday drift (held), NF-04 blocked, NF-05 deferred, NF-08-16 held, NF-09-03 data-limited alongside >=2 other repo-new mechanisms.
- Deferred/held (no silent drops): NF-16/18/19/02/22/23/12/20/04/05/08-16/09-03. Full list in `NEW_FAMILY_RESEARCH_REGISTER.md`.
- If `src/qtr` touched: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.

## Approaches that failed / evidence (do not blindly repeat)
- H177 failed Sharpe/worst-regime/benchmark; inverse weaker (direction consistent) but no OOS edge. Synthetic auction data limitation (no free point-in-time Treasury Direct CSV); auction-equity transmission weak on daily horizon. Do not rerun same auction composite construction without real auction data or materially different mechanism.
- H176 failed Sharpe/trades/WF stability/worst-regime/benchmark; direction correct but effect size too small; low frequency limits power. Do not rerun same tax-loss harvesting construction.
- H175 failed 7/8 gates; inverse-regime falsifier outperforms; composite macro regime has no OOS edge on free daily data after costs.

## One precise next task (Cycle 92 / H178)
Reconcile lineage to H177; complete directive §4 discovery (>=3 repo-new/decisive candidates across >=3 broad mechanism categories, honest 25/25/20/15/10/5, concrete deferred reassessment, NF-root checks). Re-assess NF-20261109-16/NF-20261109-18/NF-20261109-19/NF-20261109-02/NF-20261109-22/NF-20261109-23/NF-20261109-12 alongside >=2 other repo-new mechanisms. Pre-register highest-expected-information feasible candidate as **H178** before validation outcomes. Implement runner + focused tests; `ruff check/format --check`; `PYTHONPATH=src pytest -q` focused tests; execute REAL; record in `HYPOTHESIS_SPEC.md` §H178, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 92, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push unless authorized. `src/qtr` unchanged unless evidenced defect (then rerun pinned 100% suite).