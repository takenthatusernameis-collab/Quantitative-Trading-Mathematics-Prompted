# NEXT_TASK.md — Cycle 88 (after H173 REJECT 1/8)

## Status: Cycle 87 complete (H173 executed REAL; REJECT) — Cycle 88 discovery complete, H174 pre-registered

## H173 result (REAL, not fabricated) — REJECT 1/8
- Runner `run_nf_20261109_24_equity_risk_premium.py` + tests `tests/test_nf_20261109_24_equity_risk_premium.py` (**10 passed**). `ruff check/format --check` clean. Artifact `.experiments/nf_runs/nf_20261109_24_equity_risk_premium_20261109_223808/summary.json` (+`grid.csv`, 3.93s).
- Data (PIT, free yfinance): SPY + ^TNX + SPY dividends daily, 4231 aligned rows 2010-01-04→2026-10-30. Train 2010-01-01→2018-06-01 (50%), Val →2022-08-12 (25%), Test protected →2026-10-30 (25%). Train-only 4-fold WF selection; gates on OOS Val+Test only.
- Construction (daily, causal, 36-combo grid): `div_lookback ∈ {126,252}` × `z_window ∈ {126,252}` × `entry_z ∈ {0.0,0.5,1.0}` × `vol_target ∈ {0.10,0.15,0.20}`; vol targeting `vol_target/sqrt(252)`; clipped [0,0.5]; 1-bar delay; Equity CostModel defaults (1bp commission+1bp spread), long-only.
- Selected (train-only WF mean Sharpe 1.363; train ref 1.172): `div_lookback=252, z_window=252, entry_z=1.0, vol_target=0.20`.
- OOS Val+Test (2116 periods, 114 trades): Sharpe **0.310** fail (≥1.0), PF **1.170** fail (≥1.3), max DD **−16.89%** fail (≤15%), trades **114** fail (≥200), WF stability **0.264** fail (≥0.7), worst-regime rolling-252 Sharpe **−1.326** fail (≥0.3), benchmark p **0.991** / IR **−0.813** vs buy-hold SPY 0.813 (fail), perturbation min ratio **0.545** pass (≥0.5). → **REJECT 1/8**.
- Ablations OOS: buy-hold SPY 0.813/1.169/-17.97%/1; random-regime 0.112/1.050/-10.74%/617; inverse-signal **0.739**/1.155/-12.61%/55 (outperforms primary direction, indicating possible sign reversal or noise).
- **Integrity (honest):** `ruff check/format` clean; focused pytest 10 passed. No gate/threshold/grid/construction weakened; `src/qtr` unchanged. No published/certified artifact modified.
- Documented in `HYPOTHESIS_SPEC.md` §H173 and `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 87 execution).

## Lineage
**Lineage:** H85–H173 all rejected/recorded. Next unused H-ID: **H174** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged; no published/certified artifact, verdict, threshold, or frozen number modified. Selection/validation uses no protected-test feedback. Free/public data only. No commit/push unless explicitly authorized.

## Cycle 88 Discovery Complete — H174 Pre-registered

Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`:
1. **Reconciled lineage/collisions:** H85–H173 rejected/recorded, H174 next unused. No tracked draft collides with H174. NF-label reuse avoided (NF-20261109-01 collision noted in Cycle 86).
2. **Directive §4 discovery scan completed:** Proposed **5 repo-new candidates across 3 broad mechanism categories** (market structure/short interest, market structure/ETF arbitrage, market structure/dealer positioning, fundamental/analyst revisions, structural flow/discrete event) with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops).
3. **Reassessed carried-forward/deferred pool with evidence:** NF-20261109-15 tax-loss harvesting (4.20), NF-20261109-16 dividend capture (3.95), NF-20261109-12 holiday drift (4.00), NF-20261109-22 RSP-SPY breadth relmom (3.75), NF-20261109-23 USMV-SPY low-vol relmom (3.55), NF-20261109-03 cross-asset macro regime (3.85), NF-20261109-02 earnings revision (3.65), NF-20261109-18/19/20 deferred, NF-04 blocked, NF-05 deferred, NF-08-16 held, NF-09-03 data-limited — all reassessed, none silently dropped.
4. **Verified NF roots** against executed H-IDs/artifacts/runners: NF-20261109-26 verified unused.
5. **Pre-registered highest-expected-information feasible candidate as H174:** **NF-20261109-26 ETF creation/redemption premium-discount mean reversion** (weighted 3.75, market structure/ETF arbitrage — repo-new mechanism category). Decision-ready: mechanism, PIT observable (ETF price + NAV), causal path (creation/redemption arbitrage convergence), null/falsifiers, bounded grid (108 combos), costs, splits, gates.
6. **Next steps (this cycle):**
   - Implement runner `run_nf_20261109_26_etf_nav_arbitrage.py` + focused tests `tests/test_nf_20261109_26_etf_nav_arbitrage.py`
   - Run `python -m ruff check/format --check` on new files and `PYTHONPATH=src python -m pytest -q` focused tests (all pass)
   - Execute REAL; record verdict/artifacts in `HYPOTHESIS_SPEC.md` §H174, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 88, `NEXT_TASK.md`, `HANDOFF_NEXT.md`
   - **Do not fabricate results.** No gate weakening; no published/certified artifact modification.

## Constraints
- Free/public data only; no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modification; no commit/push unless explicitly authorized.
- `src/qtr` unchanged unless evidenced defect. If `src/qtr` touched, rerun pinned 100% suite: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.
- Selection/validation uses no protected-test feedback. All gates fail-closed on pre-registered OOS Val+Test.

## Approaches that failed / evidence (do not blindly repeat)
- H173: Fed model / ERP timing (div yield − 10Y yield) failed 7/8 gates (Sharpe 0.310, PF 1.170, DD −16.89%, trades 114, WF 0.264, worst-regime −1.326, benchmark p 0.991/IR −0.813); inverse-signal outperformed (0.739); train WF 1.363 → OOS 0.310 decay; valuation spread timing not robust on free data.
- H172: SPY 1h intraday seasonality (ET windows) failed Sharpe/PF/WF/worst-regime/benchmark; train WF negative; limited ~2y 1h history (yfinance 730-bar constraint). Do not rerun same hour-window construction without materially different mechanism/data.
- H171: ^TYX-^FVX slope de-risking failed Sharpe/PF/worst-regime/benchmark.
- H170: Leveraged ETF rebalancing flow failed Sharpe/PF/worst-regime/benchmark/perturbation.
- H169: Overnight futures lead-lag failed Sharpe/PF/worst-regime/benchmark.
- H168: Quarterly index-rebalance window de-risking failed; random-window control matched base.
- All H85–H173 rejected on free, point-in-time data. Avoid silent recycling of exhausted construction classes without a *materially different* mechanism/observable and explicit novelty justification.