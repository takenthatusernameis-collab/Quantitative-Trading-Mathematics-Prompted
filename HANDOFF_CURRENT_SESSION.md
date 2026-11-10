# HANDOFF — Current Session (Cycle 93 complete, H179 REJECT 2/8)

## What changed
- **Lineage:** H85–H179 all rejected/recorded. Next unused H-ID **H180** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged.
- **H179 implemented/executed REAL (NF-20261110-06, short interest / securities lending flow timing).** Fixed runner/tests defects (test API/name mismatch for SI alignment; `csv.field_size_limit(sys.maxsize)` for large FINRA CSVs; ruff format). `run_nf_20261110_06_short_interest.py` + `tests/test_nf_20261110_06_short_interest.py` (**8 passed**). `ruff check/format --check` clean. Artifact `.experiments/nf_runs/nf_20261110_06_short_interest_20261110_cycle93/summary.json` (+`grid.csv`, `finra_cache/`, 107.0s).
- **H179 data/splits (real, PIT).** FINRA exchange-listed bi-weekly short interest (145 settlement dates, publication lag applied) + daily yfinance SPY/sector ETFs, 2018-02-07→2026-10-30 (2195 aligned rows). Train→2022-06-16, Val→2024-08-23, Test protected→2026-10-30 (OOS Val+Test 1098). Train-only 4-fold WF selection; OOS gates only.
- **H179 construction.** Trailing z-score of FINRA bi-weekly short interest with hysteresis, vol-targeted exposure, PIT publication lag + engine 1-bar delay; long/short (MAX_POS 0.5), Equity CostModel defaults. Grid 72: `si_window {6,12,24} × entry_z {0.5,1.0,1.5} × exit_z {0.0,0.5} × vol_target {0.10,0.15} × universe {SPY, SPY_SECTORS}`.
- **H179 result (OOS Val+Test).** Selected `si_window=24, entry_z=1.5, exit_z=0.0, vol_target=0.15, universe=SPY_SECTORS` (WF 1.099, train 0.170). Sharpe **−0.449** fail, PF **0.920** fail, maxDD **−16.95%** fail, trades **3437** pass, WF stability **−2.647** fail, worst-regime rolling-252 **−1.970** fail, benchmark p **0.996** / IR **−1.202** vs buy-hold SPY 1.195/+50.07% fail, perturbation min ratio **1.869** pass → **REJECT 2/8**. Return −13.93%. Ablations: random-SI 0.124, inverse-signal 0.382 (both outperformed selected).
- **Docs updated:** `HYPOTHESIS_SPEC.md` §H179, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 93, `NEXT_TASK.md`, `HANDOFF_NEXT.md`, this handoff.

## Actually verified (this session)
- `python -m py_compile run_nf_20261110_06_short_interest.py tests/test_nf_20261110_06_short_interest.py` — OK.
- `python -m ruff check/format --check` on H179 runner/tests — clean.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261110_06_short_interest.py` — **8 passed** (1 third-party DeprecationWarning).
- `PYTHONPATH=src python run_nf_20261110_06_short_interest.py --out .experiments/nf_runs/nf_20261110_06_short_interest_20261110_cycle93` — REAL execution completed (107.0s), REJECT 2/8.
- Artifact present/parsable: `.experiments/nf_runs/nf_20261110_06_short_interest_20261110_cycle93/summary.json` (+`grid.csv`, `finra_cache/`).
- `src/qtr` unchanged; pinned 100% coverage suite **not rerun** (no `src/qtr` change).

## Unresolved / constraints
- H85–H179 all REJECTED/recorded. Gaps H24/H68–H73/H76–H79 unassigned (not recycled). **No commit/push** (not authorized). Published/certified artifacts and thresholds unchanged.
- Cycle 94: directive §4 discovery (≥3 candidates, ≥3 categories, honest scoring, no silent drops, NF-root checks) before selecting H180. Reassess deferred pool with evidence.
- If `src/qtr` touched: rerun pinned 100% suite with `-W error --cov=qtr --cov-branch`.

## Approaches that failed / evidence (do not blindly repeat)
- **H179:** FINRA bi-weekly short-interest z-score timing REJECT 2/8 (Sharpe −0.449, PF 0.920, maxDD −16.95%, WF −2.647, worst-regime −1.970, bench fail). **Inverse-signal 0.382 and random-SI 0.124 outperformed selected mapping**; severe train→OOS collapse. Do not rerun same z-score/hysteresis short-interest construction without materially different mechanism/observable.
- **H178:** CBOE equity P/C z-score REJECT 4/8; random-signal ablation outperformed (0.835).
- **H177:** Treasury auction supply-pressure REJECT 5/8 (Sharpe 0.720, worst-regime −1.133, bench fail).
- **H176:** Tax-loss harvesting REJECT 3/8 (low frequency, WF/worst-regime/bench fail).
- **H175:** Macro regime timing REJECT 7/8; inverse-regime falsifier outperformed.
- **H174:** ETF premium/discount invalid without point-in-time NAV. **H173:** Fed model / ERP timing REJECT 7/8.

## One precise next task (Cycle 94 / H180)
Reconcile lineage to H179; complete directive §4 discovery (≥3 repo-new/decisive candidates across ≥3 broad mechanism categories, honest 25/25/20/15/10/5, concrete deferred reassessment, NF-root checks). Reassess NF-20261110-07, NF-20261109-16, NF-20261110-08, NF-16/18/19/02/22/23/12/20/04/05/08-16/09-03/10-04/10-05 with evidence. Pre-register highest-expected-information feasible candidate as **H180** before validation outcomes. Implement runner + focused tests; `ruff check/format --check`; `PYTHONPATH=src pytest -q` focused tests; execute REAL; record in `HYPOTHESIS_SPEC.md` §H180, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 94, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push unless authorized. `src/qtr` unchanged unless evidenced defect (then rerun pinned 100% suite).
