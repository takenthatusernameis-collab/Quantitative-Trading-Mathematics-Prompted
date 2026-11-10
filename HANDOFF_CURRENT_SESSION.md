# HANDOFF — Current Session (Cycle 94 complete, H180 REJECT 2/8)

## What changed
- **Lineage:** H85–H180 all rejected/recorded. Next unused H-ID **H181** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged.
- **Directive §4 discovery completed (pre-execution).** Scored ≥3 repo-new/decisive candidates across ≥3 broad mechanism categories with honest 25/25/20/15/10/5: NF-20261109-16 dividend capture / ex-dividend microstructure (corporate action/microstructure, **3.95, selected**), NF-20261110-07 Russell 2000 annual reconstitution flow (structural flow/discrete index event, 4.05, deferred: annual low OOS power/event-alignment complexity; not smallest decisive test), NF-20261110-08 insider Form 4/13F flow (institutional flow/informed trading, 3.80, deferred: PIT parsing/aggregation complexity on free data). Deferred pool reassessed with concrete evidence (no silent drops).
- **NF-label/root check:** unrelated tracked draft `run_nf_20261110_07_es_basis.py` (incomplete/unexecuted, mislabeled NF-20261110-07/H180, no `main`) relabeled to NF-20261110-09/TBD draft and ruff-formatted to prevent NF-20261110-07/H180 collision; not selected/executed.
- **H180 implemented/executed REAL (NF-20261109-16).** `run_nf_20261109_16_dividend_capture.py` + `tests/test_nf_20261109_16_dividend_capture.py` (**10 passed**, 1 third-party DeprecationWarning). `py_compile` ok; `ruff check/format --check` clean. Artifact `.experiments/nf_runs/nf_20261109_16_dividend_capture_test_run/summary.json` (+`grid.csv`, ~8.0s).
- **Data/splits (real, PIT, free).** yfinance raw daily OHLC `auto_adjust=False` (ex-date drop visible) + dividend history for SPY/sector ETFs (XLF,XLE,XLV,XLI,XLB,XLP,XLU,XLY,XLC,XLK). Aligned 2010-01-04→2026-10-30 (4233 rows). Train→2018-12-31, Val→2022-12-31, Test protected→2026-10-30 (OOS Val+Test 1969). Train-only 4-fold WF selection; gates on OOS only.
- **Construction/grid.** Ex-dividend capture with vol-targeted exposure, 1-bar delay + dividend cash credit, Equity CostModel defaults (1bp+1bp), `MAX_POS=0.5`. Grid 12: `hold_days {0,1,2} × vol_target {0.10,0.15} × universe {SPY,SPY_SECTORS}`. Selected (WF −0.675, train −0.620): `hold_days=2, vol_target=0.10, universe=SPY`.
- **H180 result (OOS Val+Test) — REJECT 2/8.** Sharpe **0.194** fail, PF **1.149** fail, maxDD **−3.89%** pass, trades **78** pass, WF stability **−0.313** fail, worst-regime rolling-252 **−1.980** fail, benchmark p **0.992** / IR **−0.899** vs buy-hold SPY 0.911/+90.75% fail, perturbation min ratio **−3.115** fail. Return **+2.11%**. Ablations: random-dates 0.088/PF 1.336 (8 trades), inverse-signal flat.
- **Docs updated:** `HYPOTHESIS_SPEC.md` §H180, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 94, `NEXT_TASK.md`, `HANDOFF_NEXT.md`, this handoff.

## Actually verified (this session)
- `python -m py_compile run_nf_20261109_16_dividend_capture.py tests/test_nf_20261109_16_dividend_capture.py` — OK.
- `python -m ruff check/format --check run_nf_20261109_16_dividend_capture.py tests/test_nf_20261109_16_dividend_capture.py` — clean. `run_nf_20261110_07_es_basis.py` relabeled draft and `ruff check/format --check` clean.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261109_16_dividend_capture.py` — **10 passed** (1 third-party DeprecationWarning).
- `PYTHONPATH=src timeout 180 python run_nf_20261109_16_dividend_capture.py --out .experiments/nf_runs/nf_20261109_16_dividend_capture_test_run` — REAL execution completed (~8.0s), REJECT 2/8.
- Artifact present/parsable: `.experiments/nf_runs/nf_20261109_16_dividend_capture_test_run/summary.json` (+`grid.csv`).
- `src/qtr` unchanged; pinned 100% coverage suite **not rerun** (no `src/qtr` change).

## Unresolved / constraints
- H85–H180 all REJECTED/recorded. Gaps H24/H68–H73/H76–H79 unassigned (not recycled). **No commit/push** (not authorized). Published/certified artifacts and thresholds unchanged.
- Cycle 95: directive §4 discovery (≥3 candidates, ≥3 categories, honest scoring, no silent drops, NF-root checks) before selecting H181. Reassess deferred pool with evidence (NF-20261110-07, NF-20261110-08, NF-18/19/02/22/23/12/20/04/05/08-16/09-03/10-04/10-05). Draft `run_nf_20261110_07_es_basis.py` is NF-20261110-09/TBD incomplete/unexecuted.
- If `src/qtr` touched: rerun pinned 100% suite with `-W error --cov=qtr --cov-branch`.

## Approaches that failed / evidence (do not blindly repeat)
- **H180:** Ex-dividend capture (NF-20261109-16) REJECT 2/8 (Sharpe 0.194, PF 1.149, WF −0.313, worst-regime −1.980, perturb −3.115, bench p 0.992/IR −0.899 vs buy-hold 0.911/+90.75%). Unstable/weak; no certifiable microstructure edge on free daily data. Do not rerun same construction without materially different mechanism/observable.
- **H179:** FINRA short-interest z-score timing REJECT 2/8 (Sharpe −0.449, PF 0.920, WF −2.647, worst-regime −1.970; inverse/random outperformed).
- **H178:** CBOE equity P/C z-score REJECT 4/8; random-signal ablation outperformed (0.835).
- **H177:** Treasury auction supply-pressure REJECT 5/8 (Sharpe 0.720, worst-regime −1.133).
- **H176:** Tax-loss harvesting REJECT 3/8 (low frequency, WF/worst-regime/bench fail).
- **H175:** Macro regime timing REJECT 7/8; inverse-regime falsifier outperformed.
- **H174:** ETF premium/discount invalid without point-in-time NAV. **H173:** Fed model / ERP timing REJECT 7/8.

## One precise next task (Cycle 95 / H181)
Reconcile lineage to H180; complete directive §4 discovery (≥3 repo-new/decisive candidates across ≥3 broad mechanism categories, honest 25/25/20/15/10/5, concrete deferred reassessment, NF-root checks). Reassess NF-20261110-07 (annual reconstitution, low power), NF-20261110-08 (insider 13F/Form 4, PIT complexity), NF-18/19/02/22/23/12/20/04/05/08-16/09-03/10-04/10-05 with evidence. Pre-register highest-expected-information feasible candidate as **H181** before validation outcomes. Implement runner + focused tests; `ruff check/format --check`; `PYTHONPATH=src pytest -q` focused tests; execute REAL; record in `HYPOTHESIS_SPEC.md` §H181, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 95, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push unless authorized. `src/qtr` unchanged unless evidenced defect (then rerun pinned 100% suite).
