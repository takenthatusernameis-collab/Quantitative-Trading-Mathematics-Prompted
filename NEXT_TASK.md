# NEXT_TASK.md — Cycle 95 (after H180 REJECT 2/8)

## Status: Cycle 94 complete (H180 executed REAL; REJECT) — Cycle 95 discovery required

## H180 result (REAL, not fabricated) — REJECT 2/8
- Runner `run_nf_20261109_16_dividend_capture.py` (NF-20261109-16, corporate action / ex-dividend microstructure). Tests `tests/test_nf_20261109_16_dividend_capture.py` (**10 passed**, 1 third-party DeprecationWarning). `py_compile` ok; `ruff check/format --check` clean. Artifact `.experiments/nf_runs/nf_20261109_16_dividend_capture_test_run/summary.json` (+`grid.csv`, ~8.0s).
- Data (real, free, PIT): yfinance raw daily OHLC `auto_adjust=False` (ex-date drop visible) + dividend history for SPY/sector ETFs (XLF,XLE,XLV,XLI,XLB,XLP,XLU,XLY,XLC,XLK). Aligned 2010-01-04→2026-10-30 (4233 rows). Train→2018-12-31, Val→2022-12-31, Test protected→2026-10-30 (OOS Val+Test 1969). Train-only 4-fold WF selection; gates on OOS Val+Test only.
- Grid (12): `hold_days {0,1,2} × vol_target {0.10,0.15} × universe {SPY,SPY_SECTORS}`. Equity CostModel defaults (1bp+1bp), `MAX_POS=0.5`, 1-bar delay + dividend cash credit.
- Selected (WF −0.675, train −0.620): `hold_days=2, vol_target=0.10, universe=SPY`.
- OOS Val+Test (1969 periods, 78 trades): Sharpe **0.194** fail, PF **1.149** fail, maxDD **−3.89%** pass, trades **78** pass, WF stability **−0.313** fail, worst-regime rolling-252 **−1.980** fail, benchmark p **0.992** / IR **−0.899** vs buy-hold SPY 0.911/+90.75% fail, perturbation min ratio **−3.115** fail. Return **+2.11%**. → **REJECT 2/8**.
- Ablations: random-dates Sharpe 0.088/PF 1.336 (8 trades); inverse-signal flat.
- **Integrity:** `src/qtr` unchanged; no gate weakening; no published/certified artifact/verdict/threshold/frozen-number modification; no commit/push.

## Lineage
- H85–H180 all rejected/recorded. Next unused H-ID **H181** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged. Selection/validation uses no protected-test feedback. Free/public data only.

## Required next work (Cycle 95 / H181)
1. Reconcile lineage to H180; complete directive §4 discovery (≥3 repo-new/decisive candidates across ≥3 broad mechanism categories, honest 25/25/20/15/10/5 scoring, no silent drops, NF-root checks).
2. Reassess deferred pool with concrete evidence (including NF-20261110-07, NF-20261110-08, NF-18/NF-19/NF-02/NF-22/NF-23/NF-12/NF-20/NF-04/NF-05/NF-08-16/NF-09-03/NF-20261110-04/NF-20261110-05) and verify no NF-label reuse against executed runners/artifacts. Note: tracked draft `run_nf_20261110_07_es_basis.py` is NF-20261110-09/TBD (incomplete/unexecuted, relabeled to avoid NF-20261110-07 collision) — do not treat as executed.
3. Pre-register highest-expected-information feasible candidate as **H181** before validation outcomes (decision-ready: mechanism, PIT observables/availability, causal chain, null/falsifiers, splits, grid, gates, costs, novelty justification).
4. Implement runner + focused tests; `ruff check/format --check`; `PYTHONPATH=src pytest -q` focused tests; execute REAL; record verdict/artifacts in `HYPOTHESIS_SPEC.md` §H181, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 95, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. **Do not fabricate results.**

## Constraints
- Free/public data only; no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modification; no commit/push unless explicitly authorized.
- `src/qtr` unchanged unless evidenced defect. If `src/qtr` touched, rerun pinned 100% suite: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.
- Selection/validation uses no protected-test feedback. All gates fail-closed on pre-registered OOS Val+Test.

## Approaches that failed / evidence (do not blindly repeat)
- **H180 (NF-20261109-16) REJECT 2/8:** Ex-dividend capture (SPY/sector ETFs) — OOS Sharpe 0.194, PF 1.149, WF −0.313, worst-regime −1.980, bench p 0.992/IR −0.899 (buy-hold 0.911/+90.75%), perturbation min ratio −3.115. Unstable train→OOS, no certifiable microstructure edge on free daily data. Do not rerun same ex-date hold construction without materially different observable/mechanism and explicit novelty justification.
- **H179 (NF-20261110-06) REJECT 2/8:** FINRA short-interest z-score timing — Sharpe −0.449, PF 0.920, WF −2.647, worst-regime −1.970; inverse/random ablations outperformed.
- **H178:** CBOE equity P/C z-score REJECT 4/8; random-signal ablation outperformed (0.835).
- **H177:** Treasury auction supply-pressure REJECT 5/8 (Sharpe 0.720, worst-regime −1.133).
- **H176:** Tax-loss harvesting REJECT 3/8 (low frequency, WF/worst-regime/bench fail).
- **H175:** Cross-asset macro regime timing REJECT 7/8; inverse-regime falsifier outperformed.
- **H174:** ETF premium/discount invalid without point-in-time NAV. **H173:** Fed model / ERP timing REJECT 7/8.
- All H85–H180 rejected on free, point-in-time data. Avoid silent recycling of exhausted construction classes without a *materially different* mechanism/observable and explicit novelty justification.
