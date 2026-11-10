# NEXT_TASK.md — Cycle 94 (after H179 REJECT 2/8)

## Status: Cycle 93 complete (H179 executed REAL; REJECT) — Cycle 94 discovery required

## H179 result (REAL, not fabricated) — REJECT 2/8
- Runner `run_nf_20261110_06_short_interest.py` (fixed `csv.field_size_limit(sys.maxsize)` for large FINRA CSVs) + tests `tests/test_nf_20261110_06_short_interest.py` (**8 passed**). `ruff check/format --check` clean. Artifact `.experiments/nf_runs/nf_20261110_06_short_interest_20261110_cycle93/summary.json` (+`grid.csv`, `finra_cache/`, 107.0s).
- Data (PIT, free, real): FINRA exchange-listed bi-weekly short interest (145 settlement dates, publication lag applied) + daily yfinance closes for SPY + sector ETFs, 2018-02-07→2026-10-30 (2195 aligned daily rows, SPY SI known). Train 2018-02-07→2022-06-16, Val 2022-06-16→2024-08-23, Test protected 2024-08-23→2026-10-30 (OOS Val+Test 1098). Train-only 4-fold WF selection; gates on OOS Val+Test only.
- Construction: trailing z-score of FINRA bi-weekly short interest with hysteresis/vol-targeted exposure; long/short allowed (MAX_POS 0.5), Equity CostModel defaults, PIT publication lag + engine 1-bar delay. Grid 72: `si_window {6,12,24} × entry_z {0.5,1.0,1.5} × exit_z {0.0,0.5} × vol_target {0.10,0.15} × universe {SPY, SPY_SECTORS}`.
- Selected (train-only WF 1.099, train 0.170): `si_window=24, entry_z=1.5, exit_z=0.0, vol_target=0.15, universe=SPY_SECTORS`.
- OOS Val+Test (1098 periods, 3437 trades): Sharpe **−0.449** fail, PF **0.920** fail, max DD **−16.95%** fail, trades **3437** pass, WF stability **−2.647** fail, worst-regime rolling-252 Sharpe **−1.970** fail, benchmark p **0.996** / IR **−1.202** vs buy-hold SPY 1.195/+50.07% fail, perturbation min ratio **1.869** pass. → **REJECT 2/8**. Total return −13.93%.
- Ablations OOS: buy-hold SPY 1.195; random-SI 0.124/PF 1.022; inverse-signal 0.382/PF 1.073 (both outperformed selected mapping).
- **Integrity (honest):** no gate weakening; `src/qtr` unchanged; no published/certified artifact modified. No commit/push.

## Lineage
- H85–H179 all rejected/recorded. Next unused H-ID **H180** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged. Selection/validation uses no protected-test feedback. Free/public data only.

## Required next work (Cycle 94 / H180)
1. Reconcile lineage to H179; complete directive §4 discovery (≥3 repo-new/decisive candidates across ≥3 broad mechanism categories, honest 25/25/20/15/10/5 scoring, no silent drops, NF-root checks).
2. Reassess deferred pool with concrete evidence (including NF-20261110-07, NF-20261109-16, NF-20261110-08, NF-16/NF-18/NF-19/NF-02/NF-22/NF-23/NF-12/NF-20/NF-04/NF-05/NF-08-16/NF-09-03/NF-20261110-04/NF-20261110-05) and verify no NF-label reuse against executed runners/artifacts.
3. Pre-register highest-expected-information feasible candidate as **H180** before validation outcomes (decision-ready: mechanism, PIT observables/availability, causal chain, null/falsifiers, splits, grid, gates, costs, novelty justification).
4. Implement runner + focused tests; `ruff check/format --check`; `PYTHONPATH=src pytest -q` focused tests; execute REAL; record verdict/artifacts in `HYPOTHESIS_SPEC.md` §H180, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 94, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. **Do not fabricate results.**

## Constraints
- Free/public data only; no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modification; no commit/push unless explicitly authorized.
- `src/qtr` unchanged unless evidenced defect. If `src/qtr` touched, rerun pinned 100% suite: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.
- Selection/validation uses no protected-test feedback. All gates fail-closed on pre-registered OOS Val+Test.

## Approaches that failed / evidence (do not blindly repeat)
- **H179 (NF-20261110-06) REJECT 2/8:** FINRA bi-weekly short-interest z-score timing (SPY+sector ETFs) — OOS Sharpe −0.449, PF 0.920, maxDD −16.95%, WF −2.647, worst-regime −1.970, bench p 0.996/IR −1.202; **inverse-signal 0.382 and random-SI 0.124 outperformed selected mapping**. Severe train→OOS collapse. Do not rerun same short-interest z-score/hysteresis construction without materially different mechanism/observable (e.g. borrow fee/utilization/squeeze dynamics with free PIT data) and explicit novelty justification.
- **H178:** CBOE equity put/call ratio z-score regime timing REJECT 4/8; random-signal ablation outperformed (0.835). Do not rerun same P/C z-score construction.
- **H177:** Treasury auction supply-pressure timing REJECT 5/8 (Sharpe 0.720, worst-regime −1.133, bench fail); synthetic auction data limitation.
- **H176:** Tax-loss harvesting REJECT 3/8 (Sharpe 0.628, trades 8, WF 0.540, worst-regime −1.443).
- **H175:** Cross-asset macro regime timing REJECT 7/8; inverse-regime falsifier outperformed.
- **H174:** ETF premium/discount invalid without point-in-time NAV.
- **H173:** Fed model / ERP timing REJECT 7/8; inverse-signal outperformed.
- All H85–H179 rejected on free, point-in-time data. Avoid silent recycling of exhausted construction classes without a *materially different* mechanism/observable and explicit novelty justification.
