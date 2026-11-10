# NEXT_TASK.md — Cycle 93 (after H178 REJECT 4/8, H179 PRE-REGISTERED)

## Status: Cycle 92 complete (H178 executed REAL; REJECT) — Cycle 93 discovery complete, H179 pre-registered — implementation pending

## H178 result (REAL, not fabricated) — REJECT 4/8
- Runner `run_nf_20261110_03_equity_pc_ratio.py` + tests `tests/test_nf_20261110_03_equity_pc_ratio.py` (**14 passed**). `ruff check/format --check` clean. Artifact `.experiments/nf_runs/nf_20261110_03_equity_pc_ratio_20261110_cycle92/summary.json` (+`grid.csv`, ~29s).
- Data (PIT, free): SPY daily yfinance + CBOE equity put/call ratio CSV aligned 2010-01-04→2026-10-30 (4233 rows). Train 50% (→2018-05-31), Val 25%, Test protected final 25% (~2022→2026). Train-only 4-fold WF selection; gates on OOS Val+Test only.
- Construction (repo-new execution): trailing z-score of CBOE equity P/C ratio, contrarian/momentum modes, hysteresis, vol-targeted SPY exposure, 1-bar delay; long-only, MAX_POS 0.5, Equity CostModel defaults. Grid 108 combos.
- Selected (train-only WF 0.957): `pc_window=20, entry_z=0.5, exit_z=-0.5, vol_target=0.10, mode=momentum`.
- OOS Val+Test (2117 periods, 115 trades): Sharpe **0.557** fail (≥1.0), PF **1.407** pass (≥1.3), max DD **−2.78%** pass (≤15%), trades **115** pass (≥50), WF stability **0.658** fail (≥0.7), worst-regime rolling-252 Sharpe **−1.002** fail (≥0.3), benchmark p **0.983** / IR **−0.731** vs buy-hold SPY 0.819/+85.03% (fail), perturbation min ratio **0.588** pass (≥0.5). → **REJECT 4/8**.
- Ablations OOS: buy-hold SPY 0.819; random-signal **0.835** (outperformed strategy); inverse-mode (contrarian) −0.156.
- **Integrity (honest):** no gate weakening; `src/qtr` unchanged; no published/certified artifact modified. No commit/push.

## Lineage
- H85–H178 all rejected/recorded. H179 pre-registered (NF-20261110-06). Next unused H-ID after H179: **H180** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged. Selection/validation uses no protected-test feedback. Free/public data only.

## Cycle 93 Discovery Complete (Directive §4)
1. ✅ Reconciled lineage/collisions to H178; confirmed H179 next unused; avoided NF-label reuse.
2. ✅ **Discovery scan:** proposed 4 repo-new/decisive candidates across 4 broad mechanism categories with honest 25/25/20/15/10/5 scoring and no silent drops.
3. ✅ **Reassessed deferred pool with evidence:** NF-16 (4.05, microstructure/open-slippage risk), NF-18 (3.70, low freq + external calendar), NF-19 (3.10, no free historical GEX), NF-02 (3.65, no PIT revision history), NF-22 (3.75, relmom adjacency H97), NF-23 (3.55, inception/style adjacency), NF-12 held (4.00), NF-20 deferred, NF-04 blocked, NF-05 deferred, NF-08-16 held, NF-09-03 data-limited, NF-20261110-04 (3.80, curve-family adjacency to H171/H11r), NF-20261110-05 (3.80, higher-moment adjacency to H122/H128/H135) — all carried forward with documented risks; no silent drops.
4. ✅ Verified NF roots against executed H-IDs/artifacts/runners.
5. ✅ Pre-registered highest-expected-information feasible candidate as **H179 (NF-20261110-06: Short Interest / Securities Lending Flow Timing)** before validation outcomes (decision-ready). Weighted score 4.40 (novelty 5, plausibility 4, data 4, falsifiability 5, execution 4, support 4).
6. ⏳ **Next:** Implement runner + focused tests; `ruff check/format --check`; `PYTHONPATH=src pytest -q` focused tests; execute REAL; record verdict/artifacts in `HYPOTHESIS_SPEC.md` §H179, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 93, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. **Do not fabricate results.**

## H179 (NF-20261110-06) — Short Interest / Securities Lending Flow Timing — PRE-REGISTERED
- **Mechanism:** Short-constraint / limits to arbitrage (repo-new root family). FINRA bi-weekly short interest reveals crowded short positioning and securities lending supply constraints. Elevated short interest → overvaluation/crowded shorts → reduce/short exposure; low short interest → complacency → increase long exposure.
- **Data:** FINRA short interest CSV (free/public) + SPY/sector ETFs daily yfinance. 2010-01-01→2026-10-31. PIT: FINRA published ~1 week after settlement; 1-bar delay via engine `signals.shift(1)`.
- **Grid (72 combos):** `si_window {6,12,24} × entry_z {0.5,1.0,1.5} × exit_z {0.0,0.5} × vol_target {0.10,0.15} × universe {{SPY}, {SPY + 10 sector ETFs}}`.
- **Gates (OOS Val+Test, fail-closed):** Sharpe≥1.0, trades≥50, PF≥1.3, maxDD≤15%, WF stability≥0.7, worst-regime rolling-252 Sharpe≥0.3, benchmark p≤0.05 with IR≥0, perturbation min ratio≥0.5.
- **Ablations:** buy-hold SPY; random-short-interest control; inverse signal; OAT perturbation (±20%); worst-regime rolling-252 Sharpe.

## Constraints
- Free/public data only; no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modification; no commit/push unless explicitly authorized.
- `src/qtr` unchanged unless evidenced defect. If `src/qtr` touched, rerun pinned 100% suite: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.
- Selection/validation uses no protected-test feedback. All gates fail-closed on pre-registered OOS Val+Test.

## Approaches that failed / evidence (do not blindly repeat)
- H178: CBOE equity put/call ratio z-score regime timing (SPY, momentum mode selected) REJECT 4/8 (Sharpe 0.557, WF 0.658, worst-regime −1.002, bench p 0.983/IR −0.731). **Random-signal ablation outperformed (0.835)**; inverse −0.156. Sentiment/positioning ratio noisy, train→OOS decay; do not rerun same P/C z-score construction without materially different mechanism/observable.
- H177: Treasury auction supply-pressure timing REJECT 5/8 (Sharpe 0.720, worst-regime −1.133, bench fail). Direction correct but insufficient edge; synthetic auction data limitation.
- H176: Tax-loss harvesting REJECT 3/8 (Sharpe 0.628, trades 8, WF 0.540, worst-regime −1.443, bench fail). Low frequency/power.
- H175: Cross-asset macro regime timing REJECT 7/8; inverse-regime falsifier outperformed.
- H174: ETF premium/discount (NAV approximated) invalid mechanism test without point-in-time NAV.
- H173: Fed model / ERP timing REJECT 7/8; inverse-signal outperformed.
- All H85–H178 rejected on free, point-in-time data. Avoid silent recycling of exhausted construction classes without a *materially different* mechanism/observable and explicit novelty justification.
